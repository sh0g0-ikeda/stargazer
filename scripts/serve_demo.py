"""Serve the dependency-free CastorOps local demo UI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.bootstrap import build_demo_facade
from app.web.demo_server import create_demo_server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the CastorOps local demo UI.")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"), help="Host to bind.")
    parser.add_argument("--port", type=int, default=_default_port(), help="Port to bind.")
    parser.add_argument(
        "--target-project-id",
        default=os.environ.get("TARGET_PROJECT_ID", "demo-gcp-project"),
        help="Target GCP project id.",
    )
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


def _default_port() -> int:
    raw_port = os.environ.get("PORT", "8080")
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise SystemExit("PORT must be an integer") from exc
    if port <= 0 or port > 65535:
        raise SystemExit("PORT must be between 1 and 65535")
    return port


if __name__ == "__main__":
    main()
