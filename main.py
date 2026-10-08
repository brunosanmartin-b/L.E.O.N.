import queue
import random
import wave
import webbrowser

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

import config
from skills import SKILLS_MAP
from ui_server import EventBus, start_ui_server
from voice import Voice

# --- Configuración de Audio ---
SAMPLE_RATE = 16000
VAD_BLOCK_SIZE = 3200       # 200ms por bloque para detección de voz
VAD_SILENCE_BLOCKS = 8      # Bloques de silencio antes de evaluar (1.6 seg)
VAD_ENERGY_THRESHOLD = 300  # Energía mínima para considerar que hay voz
WAKE_WORD_WINDOW = 2.0      # Segundos de audio a transcribir para buscar la wake word
COMMAND_MAX_DURATION = 10   # Máximo de segundos de grabación para el comando
COMMAND_END_SILENCE = 6     # Bloques de silencio (1.2 seg) que dan por terminado el comando
COMMAND_START_TIMEOUT = 25  # Bloques (5 seg) esperando a que empieces a hablar

SYSTEM_PROMPT = (
    "Eres LEON, un asistente de IA estilo JARVIS: sofisticado, cálido, leal y con un toque de humor sutil. "
    "Todo lo que escribes se convertirá en voz, así que habla como una persona real en una conversación: "
    "frases naturales y fluidas, normalmente de una a tres oraciones. "
    "Nunca uses markdown, listas, viñetas, emojis ni URLs. "
    "Escribe los números y símbolos como se pronuncian cuando ayude a la lectura. "
    "Llama al usuario 'jefe' de vez en cuando, no en cada frase. Responde siempre en español."
)

WAKE_REPLIES = [
    "Dígame, jefe.",
    "Aquí estoy. ¿Qué necesita?",
    "A sus órdenes.",
    "Le escucho.",
    "¿Sí, jefe?",
]


class Leon:
    def __init__(self):
        print("⚙️  Inicializando sistemas de LEON...")

        # 0. Interfaz web en tiempo real
        self.bus = EventBus()
        self.ui_commands: queue.Queue = queue.Queue()
        self.bus.info = {
            "wakeWord": config.WAKE_WORD,
            "voice": config.VOICE_NAME,
            "model": config.GEMINI_MODEL,
            "skills": list(SKILLS_MAP.keys()),
        }
        start_ui_server(self.bus, self.ui_commands, config.UI_PORT)
        self.ui_url = f"http://127.0.0.1:{config.UI_PORT}"
        print(f"   🖥️  Interfaz disponible en {self.ui_url}")
        if config.OPEN_UI:
            webbrowser.open(self.ui_url)

        # 1. TTS (Voz neuronal natural)
        self.voice = Voice(
            config.VOICE_NAME,
            rate=config.VOICE_RATE,
            pitch=config.VOICE_PITCH,
            on_level=lambda level: self.bus.emit("level", source="voice", value=round(level, 3)),
        )

        # 2. STT Liviano: modelo 'tiny' para detección de wake word (rápido)
        self.log("Cargando modelo 'tiny' para la wake word...")
        self.tiny_model = WhisperModel("tiny", device="cpu", compute_type="int8")

        # 3. STT Completo: modelo 'base' para transcribir comandos (más preciso)
        self.log("Cargando modelo 'base' para transcripción...")
        self.stt_model = WhisperModel("base", device="cpu", compute_type="int8")

        # 4. LLM (Inteligencia - Google Gemini)
        self.llm = ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL,
            google_api_key=config.GEMINI_API_KEY
        )
        self.history = [SystemMessage(content=SYSTEM_PROMPT)]

        self.wake_word = config.WAKE_WORD.lower()

    # --- Comunicación con la interfaz ---
    def log(self, msg: str, level: str = "system"):
        print(f"   {msg}")
        self.bus.emit("log", level=level, msg=msg)

    def set_state(self, state: str, detail: str = ""):
        self.bus.emit("state", state=state, detail=detail)

    def speak(self, text):
        print(f"🤖 LEON: {text}")
        self.bus.emit("message", role="assistant", text=text)
        self.set_state("speaking")
        self.voice.speak(text)

    # --- Audio ---
    def _save_wav(self, audio_data: np.ndarray, filename: str):
        """Guarda un array numpy de int16 como archivo WAV."""
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16 bits = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.astype(np.int16).tobytes())

    def _emit_mic_level(self, energy: float):
        self.bus.emit("level", source="mic", value=round(min(1.0, energy / 3000), 3))

    def _contains_wake_word(self, audio_data: np.ndarray) -> bool:
        """Transcribe un fragmento corto con el modelo 'tiny' y verifica si contiene la wake word."""
        self._save_wav(audio_data, "wake_check.wav")
        segments, _ = self.tiny_model.transcribe(
            "wake_check.wav",
            beam_size=1,
            language="es",  # Forzar español
            condition_on_previous_text=False
        )
        transcribed = " ".join([s.text for s in segments]).lower()
        if transcribed.strip():
            print(f"   🔍 Escuché: '{transcribed.strip()}'")
        return self.wake_word in transcribed

    def transcribe_command(self) -> str:
        """Graba hasta que el usuario deja de hablar y transcribe con el modelo 'base'."""
        print(f"👂 Escuchando tu comando... (máx. {COMMAND_MAX_DURATION} s)")
        self.set_state("listening", "Le escucho...")
        blocks, speech_started, silence = [], False, 0
        max_blocks = int(COMMAND_MAX_DURATION * SAMPLE_RATE / VAD_BLOCK_SIZE)

        with sd.InputStream(channels=1, samplerate=SAMPLE_RATE, blocksize=VAD_BLOCK_SIZE, dtype='int16') as stream:
            for i in range(max_blocks):
                block, _ = stream.read(VAD_BLOCK_SIZE)
                block = block.flatten()
                blocks.append(block)
                energy = np.abs(block).mean()
                self._emit_mic_level(energy)

                if energy > VAD_ENERGY_THRESHOLD:
                    speech_started, silence = True, 0
                elif speech_started:
                    silence += 1
                    if silence >= COMMAND_END_SILENCE:
                        break
                elif i >= COMMAND_START_TIMEOUT:
                    break
        self._emit_mic_level(0)

        if not speech_started:
            return ""
        self.set_state("thinking", "Transcribiendo...")
        self._save_wav(np.concatenate(blocks), "command.wav")
        segments, _ = self.stt_model.transcribe("command.wav", beam_size=5, language="es")
        return " ".join([s.text for s in segments]).strip()

    # --- Lógica ---
    def execute_logic(self, text: str) -> str:
        """Ejecuta la lógica del asistente: primero skills, luego LLM."""
        print(f"👤 Tú: {text}")
        if not text:
            return "No llegué a escucharle, jefe. Cuando quiera, aquí estoy."

        self.bus.emit("message", role="user", text=text)
        self.set_state("thinking", "Procesando...")

        # A. Verificar habilidades modulares
        for keyword, func in SKILLS_MAP.items():
            if keyword in text.lower():
                self.log(f"Habilidad ejecutada: {keyword}", "info")
                return func(text)

        # B. Procesar con LLM
        self.history.append(HumanMessage(content=text))
        try:
            response = self.llm.invoke(self.history)
        except Exception as e:
            self.history.pop()
            self.log(f"Error del LLM: {e.__class__.__name__}", "error")
            return "Perdone, jefe, he perdido la conexión con mi núcleo de razonamiento. Inténtelo de nuevo en un momento."
        self.history.append(response)
        content = response.content
        if isinstance(content, list):  # algunos modelos devuelven bloques
            content = " ".join(c.get("text", "") if isinstance(c, dict) else str(c) for c in content)
        return content

    def handle(self, command: str):
        """Ciclo completo: ejecutar y responder en voz alta."""
        result = self.execute_logic(command)
        self.speak(result)

    def _idle(self):
        print(f"\n👁️  Escuchando... Di '{config.WAKE_WORD}' para activarme.\n")
        self.set_state("idle", f'Di "{config.WAKE_WORD.capitalize()}" para activarme')

    def start(self):
        self.log("Sistemas en línea", "success")
        self.speak("Sistemas en línea. Cuando me necesite, solo diga mi nombre.")
        self._idle()

        wake_word_buffer = []       # Buffer de audio para detectar la wake word
        silence_count = 0           # Contador de bloques de silencio
        voice_detected = False      # ¿Se detectó voz recientemente?

        stream = sd.InputStream(channels=1, samplerate=SAMPLE_RATE, blocksize=VAD_BLOCK_SIZE, dtype='int16')
        stream.start()

        try:
            while True:
                # Comandos escritos desde la interfaz web
                try:
                    typed = self.ui_commands.get_nowait()
                except queue.Empty:
                    typed = None
                if typed:
                    stream.stop()
                    self.handle(typed)
                    self._idle()
                    voice_detected, silence_count, wake_word_buffer = False, 0, []
                    stream.start()
                    continue

                block, _ = stream.read(VAD_BLOCK_SIZE)
                block_flat = block.flatten()
                energy = np.abs(block_flat).mean()
                self._emit_mic_level(energy)

                if energy > VAD_ENERGY_THRESHOLD:
                    # Hay voz: acumular en el buffer
                    voice_detected = True
                    silence_count = 0
                    wake_word_buffer.append(block_flat)
                elif voice_detected:
                    # Hubo voz pero ahora hay silencio
                    silence_count += 1
                    wake_word_buffer.append(block_flat)

                    if silence_count >= VAD_SILENCE_BLOCKS:
                        # Tomar los últimos N segundos de audio acumulado
                        all_audio = np.concatenate(wake_word_buffer)
                        max_samples = int(WAKE_WORD_WINDOW * SAMPLE_RATE)
                        chunk_to_check = all_audio[-max_samples:] if len(all_audio) > max_samples else all_audio

                        if self._contains_wake_word(chunk_to_check):
                            print("\n🚨 ¡LEON DETECTADO!")
                            self.log("Wake word detectada", "info")
                            stream.stop()

                            self.speak(random.choice(WAKE_REPLIES))
                            self.handle(self.transcribe_command())

                            self._idle()
                            stream.start()

                        # Reiniciar estado
                        voice_detected = False
                        silence_count = 0
                        wake_word_buffer = []

                    # Limitar tamaño del buffer para no consumir demasiada memoria
                    if len(wake_word_buffer) > int(SAMPLE_RATE / VAD_BLOCK_SIZE * 5):
                        wake_word_buffer = wake_word_buffer[-int(SAMPLE_RATE / VAD_BLOCK_SIZE * 3):]

        except KeyboardInterrupt:
            print("\n\n🔴 Apagando sistemas de LEON...")
            self.set_state("offline", "Sistemas apagados")
        finally:
            stream.stop()
            stream.close()


if __name__ == "__main__":
    leon = Leon()
    leon.start()
