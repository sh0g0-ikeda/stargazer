"""Serve the dependency-free CastorOps local demo UI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.bootstrap import build_demo_facade
from app.web.demo_server import create_demo_server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the CastorOps local demo UI.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind.")
    parser.add_argument("--target-project-id", default="demo-gcp-project", help="Target GCP project id.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = create_demo_server(
        host=args.host,
        port=args.port,
        facade=build_demo_facade(),
        target_project_id=args.target_project_id,
    )
    url = f"http://{args.host}:{args.port}"
    print(f"CastorOps demo UI listening on {url}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping CastorOps demo UI.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
