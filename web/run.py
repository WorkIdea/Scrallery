"""
Ponto de entrada da aplicação web.

Desenvolvimento:
  python run.py

Produção (via Docker):
  gunicorn "app:create_app()" --bind 0.0.0.0:5000 --workers 2
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app

app = create_app()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    print(f"\n🌐 HQ Crawler Web → http://{args.host}:{args.port}\n")
    app.run(host=args.host, port=args.port, debug=args.debug)
