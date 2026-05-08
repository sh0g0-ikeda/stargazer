"""Run the local end-to-end Star Gazer workflow demo."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.workflows.demo import build_full_demo_response


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Star Gazer local E2E workflow demo.")
    parser.add_argument("--idea", required=True, help="Project idea text.")
    parser.add_argument("--owner-uid", default="local-user", help="Owner user id.")
    parser.add_argument("--target-project-id", default="demo-gcp-project", help="Target GCP project id.")
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    response = await build_full_demo_response(
        idea=args.idea,
        owner_uid=args.owner_uid,
        target_project_id=args.target_project_id,
    )
    print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(run())
