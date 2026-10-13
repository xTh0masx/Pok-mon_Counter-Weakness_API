"""Double-click Start-Pokemon.bat, or run this file with Python 3.12.

Only the standard library is needed to bootstrap the project environment.
"""

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"
PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
REQUIREMENTS = ROOT / "requirements.txt"


def dependencies_ready():
    if not PYTHON.is_file():
        return False
    # Check actual installed versions as well as imports, rather than a stale marker.
    code = (
        "import importlib.metadata as m; import json,sys; "
        "import fastapi,uvicorn,httpx,pydantic,dotenv; "
        "expected=json.loads(sys.argv[1]); "
        "sys.exit(0 if all(m.version(k)==v for k,v in expected.items()) else 1)"
    )
    expected = {}
    for line in REQUIREMENTS.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            name, version = line.split("==", 1)
            expected[name.split("[")[0]] = version
    return subprocess.run([str(PYTHON), "-c", code, json.dumps(expected)],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def setup():
    if not PYTHON.is_file():
        if VENV.exists():
            raise RuntimeError("An incomplete .venv exists. Rename it to .venv-backup and launch again.")
        print("Creating the project's Python environment...", flush=True)
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    if not dependencies_ready():
        print("Installing project packages (internet required)...", flush=True)
        subprocess.run([str(PYTHON), "-m", "pip", "install", "-r", str(REQUIREMENTS)], check=True)
    if not (ROOT / ".env").exists():
        # Exclusive creation preserves existing user configuration.
        try:
            with (ROOT / ".env").open("x", encoding="utf-8") as output:
                output.write((ROOT / ".env.example").read_text(encoding="utf-8"))
        except FileExistsError:
            pass


def is_pokemon_app(port):
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{port}/", timeout=1) as response:
            return b"<title>Pok\xc3\xa9mon Counter Lab</title>" in response.read(65536)
    except (OSError, urllib.error.URLError):
        return False


def choose_port(preferred):
    for port in range(preferred, min(preferred + 11, 65536)):
        with socket.socket() as listener:
            try:
                listener.bind(("127.0.0.1", port))
            except OSError:
                if is_pokemon_app(port):
                    return port, True
            else:
                return port, False
    raise RuntimeError("No available port found. Try: Start-Pokemon.bat --port 8100")


def open_when_ready(process, port):
    for _ in range(60):
        if process.poll() is not None:
            return
        if is_pokemon_app(port):
            webbrowser.open(f"http://127.0.0.1:{port}/")
            return
        time.sleep(0.5)
    print("Browser did not open automatically. Use the address printed above.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    # Keep a separate browser origin from other projects and their offline caches.
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="Start without opening a browser")
    parser.add_argument("--check", action="store_true", help="Check setup without installing or starting anything")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Port must be between 1024 and 65535")
    if sys.version_info < (3, 12):
        raise RuntimeError("Python 3.12 or later is required; Python 3.12 is recommended.")
    os.chdir(ROOT)
    print("Pokemon Counter Lab\n" + str(ROOT), flush=True)
    if args.check:
        ready = dependencies_ready()
        port, existing = choose_port(args.port)
        print(f"Dependencies: {'ready' if ready else 'setup needed'}")
        print(f"Port: {port} ({'Pokemon app already running' if existing else 'available'})")
        return 0 if ready else 1
    setup()
    port, existing = choose_port(args.port)
    url = f"http://127.0.0.1:{port}/"
    print(f"\nOpen: {url}", flush=True)
    if existing:
        print("The Pokemon app is already running. Reusing it; no duplicate server started.")
        print("Stop it from the terminal or process that originally started it.")
        if not args.no_browser:
            webbrowser.open(url)
        return 0
    if port != args.port:
        print(f"Port {args.port} belongs to another app; using {port} instead.")
    print("Keep this window open. Press Ctrl+C here to stop the server.\n", flush=True)
    process = subprocess.Popen([
        str(PYTHON), "-m", "uvicorn", "App.main:app", "--host", "127.0.0.1",
        "--port", str(port), "--no-access-log",
    ], cwd=ROOT)
    if not args.no_browser:
        threading.Thread(target=open_when_ready, args=(process, port), daemon=True).start()
    try:
        return process.wait()
    except KeyboardInterrupt:
        print("\nStopping Pokemon Counter Lab...")
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"\nCould not start: {error}\nFix the issue above and launch again.", file=sys.stderr)
        raise SystemExit(1)
