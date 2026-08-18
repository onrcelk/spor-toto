"""CLI for the deterministic research runner."""
from __future__ import annotations

import argparse
import json

from sportoto.research_runner import run


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", required=True)
    ap.add_argument("--odds", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    print(json.dumps(run(args.journal, args.odds, args.output), ensure_ascii=False))
