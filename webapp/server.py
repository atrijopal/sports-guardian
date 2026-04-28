"""Tiny static server for the Sentinel webapp. Run: python server.py"""
import http.server, webbrowser, threading, sys
from pathlib import Path

PORT = 8003

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(Path(__file__).parent), **kw)
    def log_message(self, fmt, *args):
        print(f"  {args[0]} {args[1]}")

def open_browser():
    import time; time.sleep(0.5)
    webbrowser.open(f"http://localhost:{PORT}")

print(f"\n  Sentinel — http://localhost:{PORT}\n")
print("  Required backends:")
print("    Module 1  →  cd module1-fingerprinting && uvicorn app:app --reload --port 8000")
print("    Module 2  →  cd module2-threat-intel   && uvicorn app:app --reload --port 8002")
print("    Module 3  →  cd module3-watermarking   && uvicorn app:app --reload --port 8001")
print()

threading.Thread(target=open_browser, daemon=True).start()
with http.server.HTTPServer(("", PORT), Handler) as srv:
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
