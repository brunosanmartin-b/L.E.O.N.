"""
Servidor local de la interfaz de LEON.

- Sirve la carpeta ui/ en http://127.0.0.1:<puerto>
- /events     -> Server-Sent Events con el estado del asistente en tiempo real
- /api/command -> POST {"text": "..."} para enviar comandos escritos desde la web
"""
import json
import queue
import threading
import time
from collections import deque
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UI_DIR = Path(__file__).parent / "ui"


class EventBus:
    """Difunde eventos a todos los navegadores conectados y guarda un historial reciente."""

    def __init__(self):
        self._subscribers: list[queue.Queue] = []
        self._lock = threading.Lock()
        self.recent = deque(maxlen=60)   # logs y mensajes para quien se conecte tarde
        self.state = "idle"
        self.detail = "Iniciando sistemas..."
        self.info: dict = {}
        self.started_at = time.time()

    def subscribe(self) -> queue.Queue:
        q = queue.Queue(maxsize=200)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def emit(self, type_: str, **data):
        event = {"type": type_, "ts": time.time(), **data}
        if type_ == "state":
            self.state = data["state"]
            self.detail = data.get("detail", "")
        elif type_ in ("log", "message"):
            self.recent.append(event)
        with self._lock:
            subscribers = list(self._subscribers)
        for q in subscribers:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass  # navegador lento: descartar en vez de bloquear al asistente

    def snapshot(self) -> dict:
        return {
            "type": "hello",
            "state": self.state,
            "detail": self.detail,
            "info": self.info,
            "startedAt": self.started_at,
            "recent": list(self.recent),
        }


class _Handler(SimpleHTTPRequestHandler):
    bus: EventBus
    commands: queue.Queue
    # El registro de Windows a veces mapea .js a text/plain
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript", ".css": "text/css", ".html": "text/html; charset=utf-8",
    }

    def log_message(self, *args):
        pass  # silenciar el log HTTP en la consola

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if self.path == "/events":
            return self._stream_events()
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/command":
            return self.send_error(404)
        try:
            length = int(self.headers.get("Content-Length", 0))
            text = str(json.loads(self.rfile.read(length) or b"{}").get("text", "")).strip()
        except (ValueError, json.JSONDecodeError):
            return self.send_error(400)
        if not text:
            return self.send_error(400)
        self.commands.put(text[:500])
        self.send_response(204)
        self.end_headers()

    def _stream_events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q = self.bus.subscribe()
        try:
            self._send(self.bus.snapshot())
            while True:
                try:
                    self._send(q.get(timeout=15))
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            self.bus.unsubscribe(q)

    def _send(self, event: dict):
        self.wfile.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8"))
        self.wfile.flush()


def start_ui_server(bus: EventBus, commands: queue.Queue, port: int) -> ThreadingHTTPServer:
    handler = type("LeonHandler", (_Handler,), {"bus": bus, "commands": commands})
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(handler, directory=str(UI_DIR)))
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
