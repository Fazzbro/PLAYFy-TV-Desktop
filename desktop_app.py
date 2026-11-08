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

class DesktopBridge:
    """
    Direct JavaScript <-> Python native window bridge.
    Exposed as window.pywebview.api in the Edge WebView2 environment.
    """
    def __init__(self):
        self._window = None

    def set_window(self, win):
        self._window = win

    def toggle_fullscreen(self):
        if self._window:
            self._window.toggle_fullscreen()
            return bool(self._window.fullscreen)
        return False

    def set_fullscreen(self, value: bool):
        if self._window:
            if bool(self._window.fullscreen) != bool(value):
                self._window.toggle_fullscreen()
            return bool(self._window.fullscreen)
        return False

    def is_fullscreen(self):
        if self._window:
            return bool(self._window.fullscreen)
        return False


def setup_fullscreen_listener(win):
    """
    Hooks into CoreWebView2's ContainsFullScreenElementChanged event.
    Automatically toggles the native WinForms host window to borderless
    fullscreen whenever HTML5 requestFullscreen() or exitFullscreen() is called.
    """
    def on_shown():
        try:
            form = win.native
            if not form:
                return

            def on_fs_change(sender, args):
                try:
                    wants_fs = bool(sender.ContainsFullScreenElement)
                    if wants_fs != bool(win.fullscreen):
                        win.toggle_fullscreen()
                except Exception:
                    pass

            def attach_core(core_wv2):
                try:
                    core_wv2.ContainsFullScreenElementChanged += on_fs_change
                except Exception:
                    pass

            if hasattr(form, 'webview') and form.webview:
                wv = form.webview
                if getattr(wv, 'CoreWebView2', None) is not None:
                    attach_core(wv.CoreWebView2)
                else:
                    def on_init(sender, args):
                        try:
                            if getattr(args, 'IsSuccess', False) and getattr(sender, 'CoreWebView2', None) is not None:
                                attach_core(sender.CoreWebView2)
                        except Exception:
                            pass
                    wv.CoreWebView2InitializationCompleted += on_init
        except Exception:
            pass

    win.events.shown += on_shown


def main():
    global PORT
    PORT = find_available_port(8000)

    # Start backend FastAPI server in background
    thread = threading.Thread(target=start_backend, daemon=True)
    thread.start()

    # Wait until FastAPI server is responding
    wait_for_server()

    # Create native desktop application window with JS Bridge
    bridge = DesktopBridge()

    window = webview.create_window(
        title="PLAYFy TV - Real Live Sports",
        url=f"http://127.0.0.1:{PORT}",
        width=1280,
        height=820,
        min_size=(960, 600),
        background_color="#050505",
        text_select=False,
        js_api=bridge
    )
    bridge.set_window(window)
    server.DESKTOP_WINDOW = window

    # Enable native taskbar & borderless fullscreen synchronization
    setup_fullscreen_listener(window)

    webview.start(debug=False)

if __name__ == "__main__":
    main()
