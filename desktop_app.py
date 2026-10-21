"""
PLAYFy TV - Standalone Windows Desktop Application Launcher
Launches the high-performance Core Engine server and displays the application in a native Edge WebView2 window.
"""

import sys
import os
import time
import threading
import urllib.request
import webview

# Configure frozen paths for PyInstaller bundle
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

if BUNDLE_DIR not in sys.path:
    sys.path.insert(0, BUNDLE_DIR)

APP_DIR = os.path.join(BUNDLE_DIR, "windows_app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import server
import uvicorn

import socket

def find_available_port(preferred=8000):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', preferred))
            return preferred
    except OSError:
        pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

PORT = find_available_port(8000)

def start_backend():
    config = uvicorn.Config(server.app, host="127.0.0.1", port=PORT, log_level="warning")
    uv_server = uvicorn.Server(config)
    uv_server.run()

def wait_for_server():
    for _ in range(40):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/status", timeout=0.5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False

def main():
    global PORT
    PORT = find_available_port(8000)

    # Start backend FastAPI server in background
    thread = threading.Thread(target=start_backend, daemon=True)
    thread.start()

    # Wait until FastAPI server is responding
    wait_for_server()

    # Create native desktop application window
    window = webview.create_window(
        title="PLAYFy TV - Real Live Sports",
        url=f"http://127.0.0.1:{PORT}",
        width=1280,
        height=820,
        min_size=(960, 600),
        background_color="#050505",
        text_select=False
    )
    webview.start(debug=False)

if __name__ == "__main__":
    main()
