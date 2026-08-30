# skills/system_skills.py
import datetime
import webbrowser

def get_time(args):
    return f"Son las {datetime.datetime.now().strftime('%H:%M')}, jefe."

def open_spotify(args):
    webbrowser.open("https://open.spotify.com")
    return "Iniciando Spotify. Que fluya la música."

# Diccionario de mapeo para el orquestador
SKILLS_MAP = {
    "hora": get_time,
    "spotify": open_spotify,
}
