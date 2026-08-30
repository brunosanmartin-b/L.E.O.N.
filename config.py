# config.py
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Credenciales y configuraciones
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
WAKE_WORD = os.getenv("WAKE_WORD", "leon")

if not GEMINI_API_KEY:
    print("⚠️  ADVERTENCIA: No se encontró GEMINI_API_KEY configurada en el archivo .env")

