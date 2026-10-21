"""
PLAYFy TV - Production Desktop Launcher
Launches the high-performance Core Engine server and opens the React UI in the browser.
"""

import sys
import os
import webbrowser
import threading
import time
import uvicorn
import server

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    print("=" * 65)
    print("  PLAYFy TV - Production React Application & Core Engine")
    print("=" * 65)
    print("Local UI URL:  http://127.0.0.1:8000")
    print("API Endpoint:  http://127.0.0.1:8000/api/status")
    print("Starting background launcher...")
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(server.app, host="127.0.0.1", port=8000)
