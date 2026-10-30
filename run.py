"""SwiftLogic Courier Tracker — local or Render.

On Render, PORT is set and the app must bind 0.0.0.0.
"""
from __future__ import annotations

import os
import socket

import uvicorn


def port_free(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def pick_port() -> int:
    forced = os.getenv("PORT")
    if forced:
        return int(forced)
    for port in (8765, 5050, 8000, 8888, 9000, 18080):
        if port_free(port):
            return port
    raise SystemExit("No free port in 8765, 5050, 8000, 8888, 9000, 18080")


if __name__ == "__main__":
    port = pick_port()
    host = "0.0.0.0" if os.getenv("PORT") else "127.0.0.1"
    print(f"Open http://{host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
