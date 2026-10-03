"""Start the tracker on a free localhost port (avoids WinError 10013 on 8080)."""

from __future__ import annotations

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
    for port in (8765, 5050, 8000, 8888, 9000, 18080):
        if port_free(port):
            return port
    raise SystemExit("No free port in 8765, 5050, 8000, 8888, 9000, 18080")


if __name__ == "__main__":
    port = pick_port()
    print(f"Open http://127.0.0.1:{port}")
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False)
