"""Sportoto CLI.

Commands:
- predict-next-week
- train
- refresh-matches
- refresh-news
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .dataset import evaluate_next_week, refresh_news_memory, refresh_sportoto_memory
from .model import MatchModel
from .train import generate_synthetic_training_records, train_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sportoto", description="Spor toto prediction CLI")
    subparsers = parser.add_subparsers(dest="command")

    predict_parser = subparsers.add_parser("predict-next-week", help="Evaluate next week scenario")
    predict_parser.add_argument("--raw-dir", default="~/.sportoto/raw")

    refresh_parser = subparsers.add_parser("refresh-matches", help="Refresh match list from Spor Toto")
    refresh_parser.add_argument("--output", default="~/.sportoto/raw/sportoto_list_latest.json")

    refresh_news_parser = subparsers.add_parser("refresh-news", help="Refresh news memory")
    refresh_news_parser.add_argument("--output", default="~/.sportoto/raw/news_latest.jsonl")
    refresh_news_parser.add_argument("--limit", type=int, default=20)

    train_parser = subparsers.add_parser("train", help="Train prediction model")
    train_parser.add_argument("--model-path", default="~/.sportoto/models/match_model.joblib")
    train_parser.add_argument("--synthetic-count", type=int, default=120)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "predict-next-week":
        result = evaluate_next_week()
        print(f"Evaluated at: {result['evaluated_at']}")
        print(f"Matches: {result['match_count']}")
        print(f"News items: {result['news_count']}")
        return 0
    if args.command == "refresh-matches":
        rows = refresh_sportoto_memory(Path(args.output).expanduser())
        print(f"Refreshed matches: {len(rows)}")
        return 0
    if args.command == "refresh-news":
        items = refresh_news_memory(Path(args.output).expanduser(), limit=args.limit)
        print(f"Refreshed news: {len(items)}")
        return 0
    if args.command == "train":
        records = generate_synthetic_training_records(args.synthetic_count)
        model = train_model(records, Path(args.model_path).expanduser())
        print(f"Trained model saved to: {args.model_path}")
        return 0
    print("No command provided", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
