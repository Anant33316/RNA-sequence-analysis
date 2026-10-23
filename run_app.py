"""
Launch the web application.

    python run_app.py                 # http://127.0.0.1:8000
    python run_app.py --port 9000
    python run_app.py --open          # also open the browser

The command-line scripts (main_module1_2.py, main.py, every module's
__main__) keep working independently of the web app.
"""

from __future__ import annotations

import argparse
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="RNA × Theory of Computation web app")
    parser.add_argument("--host", default="127.0.0.1", help="interface to bind (default: 127.0.0.1, local only)")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--open", action="store_true", help="open the app in the default browser")
    parser.add_argument("--reload", action="store_true", help="auto-reload on code changes (development)")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        sys.exit("uvicorn is not installed. Run:  pip install -r requirements.txt")

    url = f"http://{args.host}:{args.port}"
    print(f"RNA × Theory of Computation — serving on {url}  (Ctrl+C to stop)")
    if args.open:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    uvicorn.run("api.app:app", host=args.host, port=args.port, reload=args.reload,
                app_dir=str(ROOT), log_level="info")


if __name__ == "__main__":
    main()
