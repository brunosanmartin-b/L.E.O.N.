# config.py
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Credenciales y configuraciones
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
WAKE_WORD = os.getenv("WAKE_WORD", "leon")

# Voz neuronal (Edge TTS). Otras voces: es-MX-JorgeNeural, es-ES-AlvaroNeural,
# es-CO-GonzaloNeural, es-AR-TomasNeural, es-ES-ElviraNeural (femenina)...
VOICE_NAME = os.getenv("LEON_VOICE", "es-ES-AlvaroNeural")
VOICE_RATE = os.getenv("LEON_VOICE_RATE", "+4%")     # velocidad: -20% .. +30%
VOICE_PITCH = os.getenv("LEON_VOICE_PITCH", "-2Hz")  # tono: -10Hz .. +10Hz

# Interfaz web
UI_PORT = int(os.getenv("LEON_UI_PORT", "8765"))
OPEN_UI = os.getenv("LEON_OPEN_UI", "1") == "1"

if not GEMINI_API_KEY:
    print("⚠️  ADVERTENCIA: No se encontró GEMINI_API_KEY configurada en el archivo .env")
