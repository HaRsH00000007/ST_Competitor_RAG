"""
run.py — Browser launcher for ST Competitive Intelligence RAG (v5)
"""

import sys
import os
import time
import threading
import webbrowser
import multiprocessing
import socket


def find_free_port(preferred: int = 8000) -> int:
    """Try preferred port first, then find any free port."""
    for port in range(preferred, preferred + 10):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


HOST = "127.0.0.1"
PORT = find_free_port(8000)
URL  = f"http://{HOST}:{PORT}"


def start_server():
    import uvicorn
    from app.main import app
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def wait_for_server(timeout: int = 30) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{URL}/docs", timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))

    print(f"[run.py] Starting server at {URL} ...")
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    if not wait_for_server():
        print("[run.py] ERROR: Server did not start in time.")
        input("Press Enter to exit...")
        sys.exit(1)

    print(f"[run.py] Server ready. Opening browser...")
    webbrowser.open(URL)
    print(f"[run.py] App running at {URL}")
    print("[run.py] Keep this window open. Close it to stop the app.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[run.py] Shutting down.")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()