"""
Voz de LEON: síntesis neuronal con Microsoft Edge TTS (gratuita, sin API key).

- Limpia el texto del LLM (markdown, emojis, URLs) para que suene natural.
- Divide la respuesta en frases y sintetiza la siguiente mientras reproduce la actual,
  así empieza a hablar antes y sin pausas largas.
- Si no hay internet, cae automáticamente a pyttsx3 (voz local de Windows).
"""
import asyncio
import io
import queue
import re
import threading
import time

import av
import edge_tts
import numpy as np
import sounddevice as sd

OUTPUT_RATE = 24000

_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF‍️]+"
)


def clean_for_speech(text: str) -> str:
    """Convierte la salida del LLM en texto apto para leerse en voz alta."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)           # bloques de código
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)         # [texto](url) -> texto
    text = re.sub(r"https?://\S+", "el enlace", text)
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.M)         # encabezados
    text = re.sub(r"^\s*[-*•]\s+", "", text, flags=re.M)          # viñetas
    text = re.sub(r"^\s*(\d+)\.\s+", r"\1, ", text, flags=re.M)   # listas numeradas
    text = re.sub(r"[*_`~|>]", "", text)
    text = _EMOJI_RE.sub("", text)
    text = re.sub(r"\s*\n+\s*", ". ", text)
    text = re.sub(r"\.\s*\.", ".", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def split_sentences(text: str, max_chunk: int = 220) -> list[str]:
    """Primera frase sola (para empezar rápido), el resto agrupado en bloques fluidos."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?¡¿…;:])\s+", text) if s.strip()]
    if not sentences:
        return []
    chunks = [sentences[0]]
    current = ""
    for s in sentences[1:]:
        if current and len(current) + len(s) > max_chunk:
            chunks.append(current)
            current = s
        else:
            current = f"{current} {s}".strip()
    if current:
        chunks.append(current)
    return chunks


class Voice:
    def __init__(self, voice: str, rate: str = "+0%", pitch: str = "+0Hz", on_level=None):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.on_level = on_level or (lambda level: None)
        self._fallback_engine = None

    # --- Síntesis ---
    async def _synthesize_async(self, text: str) -> bytes:
        audio = bytearray()
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, pitch=self.pitch)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
        return bytes(audio)

    def _synthesize(self, text: str) -> np.ndarray:
        mp3 = asyncio.run(self._synthesize_async(text))
        container = av.open(io.BytesIO(mp3))
        resampler = av.AudioResampler(format="s16", layout="mono", rate=OUTPUT_RATE)
        frames = [
            f.to_ndarray().flatten()
            for packet in container.decode(audio=0)
            for f in resampler.resample(packet)
        ]
        container.close()
        return np.concatenate(frames) if frames else np.zeros(0, dtype=np.int16)

    # --- Reproducción ---
    def _play(self, pcm: np.ndarray):
        if pcm.size == 0:
            return
        sd.play(pcm, OUTPUT_RATE)
        duration = len(pcm) / OUTPUT_RATE
        window = int(OUTPUT_RATE * 0.05)
        start = time.monotonic()
        while (elapsed := time.monotonic() - start) < duration:
            i = int(elapsed * OUTPUT_RATE)
            chunk = pcm[i:i + window].astype(np.float32)
            if chunk.size:
                rms = float(np.sqrt(np.mean(chunk ** 2))) / 32768
                self.on_level(min(1.0, rms * 4))
            time.sleep(0.05)
        sd.wait()
        self.on_level(0.0)

    def _speak_offline(self, text: str):
        if self._fallback_engine is None:
            import pyttsx3
            self._fallback_engine = pyttsx3.init()
            self._fallback_engine.setProperty("rate", 175)
        self._fallback_engine.say(text)
        self._fallback_engine.runAndWait()

    def speak(self, text: str):
        """Habla el texto. Bloquea hasta terminar."""
        chunks = split_sentences(clean_for_speech(text))
        if not chunks:
            return

        # Productor: sintetiza por adelantado mientras se reproduce el bloque anterior
        pending: queue.Queue = queue.Queue(maxsize=2)

        def producer():
            online = True
            for chunk in chunks:
                pcm = None
                if online:
                    try:
                        pcm = self._synthesize(chunk)
                    except Exception as e:
                        print(f"   ⚠️  Voz neuronal no disponible ({e.__class__.__name__}); usando voz local.")
                        online = False
                pending.put((chunk, pcm))
            pending.put(None)

        threading.Thread(target=producer, daemon=True).start()

        while (item := pending.get()) is not None:
            chunk, pcm = item
            if pcm is not None:
                self._play(pcm)
            else:
                self._speak_offline(chunk)
