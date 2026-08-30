import os
import wave
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
import pyttsx3
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

import config
from skills import SKILLS_MAP

# --- Configuración de Audio ---
SAMPLE_RATE = 16000
VAD_BLOCK_SIZE = 3200       # 200ms por bloque para detección de voz
VAD_SILENCE_BLOCKS = 8      # Bloques de silencio antes de evaluar (1.6 seg)
VAD_ENERGY_THRESHOLD = 300  # Energía mínima para considerar que hay voz
WAKE_WORD_WINDOW = 2.0      # Segundos de audio a transcribir para buscar la wake word
COMMAND_DURATION = 6        # Segundos de grabación para el comando

class Leon:
    def __init__(self):
        print("⚙️  Inicializando sistemas de LEON...")

        # 1. TTS (Voz)
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 175)

        # 2. STT Liviano: modelo 'tiny' para detección de wake word (rápido)
        print("   📥 Cargando modelo 'tiny' para detección de wake word...")
        self.tiny_model = WhisperModel("tiny", device="cpu", compute_type="int8")

        # 3. STT Completo: modelo 'base' para transcribir comandos (más preciso)
        print("   📥 Cargando modelo 'base' para transcripción de comandos...")
        self.stt_model = WhisperModel("base", device="cpu", compute_type="int8")

        # 4. LLM (Inteligencia - Google Gemini)
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=config.GEMINI_API_KEY
        )
        self.history = [SystemMessage(
            content="Eres LEON, un sistema de IA avanzado estilo JARVIS. "
                    "Eres eficiente, sofisticado y leal. Responde siempre en español."
        )]

        self.wake_word = config.WAKE_WORD.lower()

    def speak(self, text):
        print(f"🤖 LEON: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

    def _save_wav(self, audio_data: np.ndarray, filename: str):
        """Guarda un array numpy de int16 como archivo WAV."""
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16 bits = 2 bytes
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.astype(np.int16).tobytes())

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
        """Graba y transcribe el comando del usuario con el modelo 'base'."""
        print(f"👂 Escuchando tu comando... ({COMMAND_DURATION} segundos)")
        recording = sd.rec(
            int(COMMAND_DURATION * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='int16'
        )
        sd.wait()
        self._save_wav(recording.flatten(), "command.wav")
        segments, _ = self.stt_model.transcribe("command.wav", beam_size=5, language="es")
        text = " ".join([s.text for s in segments]).strip()
        return text

    def execute_logic(self, text: str) -> str:
        """Ejecuta la lógica del asistente: primero skills, luego LLM."""
        print(f"👤 Tú: {text}")
        if not text:
            return "No escuché nada, jefe. Estoy a sus órdenes cuando guste."

        # A. Verificar habilidades modulares
        for keyword, func in SKILLS_MAP.items():
            if keyword in text.lower():
                return func(text)

        # B. Procesar con LLM
        self.history.append(HumanMessage(content=text))
        response = self.llm.invoke(self.history)
        self.history.append(response)
        return response.content

    def start(self):
        self.speak("Sistemas operativos cargados. LEON en espera.")
        print(f"\n👁️  Escuchando... Di '{config.WAKE_WORD}' para activarme.\n")

        wake_word_buffer = []       # Buffer de audio para detectar la wake word
        silence_count = 0           # Contador de bloques de silencio
        voice_detected = False      # ¿Se detectó voz recientemente?

        stream = sd.InputStream(channels=1, samplerate=SAMPLE_RATE, blocksize=VAD_BLOCK_SIZE, dtype='int16')
        stream.start()

        try:
            while True:
                block, _ = stream.read(VAD_BLOCK_SIZE)
                block_flat = block.flatten()
                energy = np.abs(block_flat).mean()

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
                            stream.stop()

                            self.speak("Sí, jefe. ¿En qué puedo ayudarle?")
                            command = self.transcribe_command()
                            result = self.execute_logic(command)
                            self.speak(result)

                            print(f"\n👁️  Escuchando... Di '{config.WAKE_WORD}' para activarme.\n")
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
        finally:
            stream.stop()
            stream.close()

if __name__ == "__main__":
    leon = Leon()
    leon.start()


