"""Sportoto CLI.

Commands:
- predict-next-week
- train
- refresh-matches
- refresh-news
- make-coupon
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .dataset import evaluate_next_week, refresh_news_memory, refresh_sportoto_memory
from .model import MatchModel
from .train import generate_synthetic_training_records, train_model
from .real_training import build_training_frame, fetch_football_data
from .current_list import save_current_list
from .coupon import CouponRules, CouponResult, MatchPref, format_coupon, generate_coupon, apply_filter_by_surprise, apply_filter_by_draws, apply_filter_by_streak, filter_segment
from .live_monitor import collect_live
from .next_week import build_next_week_report


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

    current_parser = subparsers.add_parser("refresh-current-list", help="Fetch the current 15-match Spor Toto list")
    current_parser.add_argument("--output", default="data/current_sportoto_list.json")

    live_parser = subparsers.add_parser("collect-live", help="Read-only match-day snapshots")
    live_parser.add_argument("--output-dir", default="data/live")
    live_parser.add_argument("--no-tff", action="store_true", help="Skip TFF result snapshot")

    next_parser = subparsers.add_parser("analyze-next-week", help="Build recent team-form report")
    next_parser.add_argument("--matches", default="data/current_sportoto_list.json")
    next_parser.add_argument("--history", default="data/sportoto_master_training.parquet")
    next_parser.add_argument("--output", default="data/next_week_analysis.json")
    next_parser.add_argument("--last-n", type=int, default=5)

    train_parser = subparsers.add_parser("train", help="Train prediction model")
    train_parser.add_argument("--model-path", default="~/.sportoto/models/match_model.joblib")
    train_parser.add_argument("--synthetic-count", type=int, default=120)
    train_parser.add_argument("--real", action="store_true", help="Train from football-data.co.uk historical results")
    train_parser.add_argument("--data-path", default="data/real_training.parquet")

    coupon_parser = subparsers.add_parser("make-coupon", help="Generate 9-col coupon from predictions")
    coupon_parser.add_argument("--predictions", default="data/latest_predictions.json")
    coupon_parser.add_argument("--guarantee", type=int, default=14, choices=[12, 13, 14])
    coupon_parser.add_argument("--closed", type=int, default=None)
    coupon_parser.add_argument("--doubles", type=int, default=0)
    coupon_parser.add_argument("--bankos", type=int, default=0)
    coupon_parser.add_argument("--max-surprise", type=int, default=None)
    coupon_parser.add_argument("--max-draws", type=int, default=None)
    coupon_parser.add_argument("--max-home-streak", type=int, default=None)
    coupon_parser.add_argument("--max-draw-streak", type=int, default=None)
    coupon_parser.add_argument("--max-away-streak", type=int, default=None)
    coupon_parser.add_argument("--segment-1-9-max-draws", type=int, default=None)
    coupon_parser.add_argument("--segment-10-15-max-draws", type=int, default=None)
    coupon_parser.add_argument("--segment-1-9-max-surprise", type=int, default=None)
    coupon_parser.add_argument("--segment-10-15-max-surprise", type=int, default=None)
    return parser


def _load_predictions(path: str) -> list[dict]:
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"Predictions file not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("predictions", data.get("matches", []))
    if not isinstance(data, list):
        raise ValueError("Predictions JSON must be a list or contain a list under 'predictions'/'matches'")
    return data


def _normalize_predictions(predictions: list[dict]) -> list[dict]:
    normalized = []
    for idx, item in enumerate(predictions[:15]):
        pick = str(item.get("predicted_1x2", item.get("pick", "1"))).upper()
        if pick not in {"1", "X", "2"}:
            pick = "1"
        normalized.append({
            "match_id": str(item.get("match_id", f"M{idx+1:02d}")),
            "home_team": item.get("home_team", f"Home{idx+1}"),
            "away_team": item.get("away_team", f"Away{idx+1}"),
            "predicted_1x2": pick,
            "confidence": float(item.get("confidence", 0.5)),
            "pred_home_win": float(item.get("pred_home_win", 0.33)),
            "pred_draw": float(item.get("pred_draw", 0.34)),
            "pred_away_win": float(item.get("pred_away_win", 0.33)),
        })
    # Pad to 15 if fewer predictions provided
    if len(normalized) < 15:
        for idx in range(len(normalized) + 1, 16):
            normalized.append({
                "match_id": f"M{idx:02d}",
                "home_team": f"Home{idx}",
                "away_team": f"Away{idx}",
                "predicted_1x2": "1",
                "confidence": 0.5,
                "pred_home_win": 0.33,
                "pred_draw": 0.34,
                "pred_away_win": 0.33,
            })
    return normalized[:15]


def _prefs_from_predictions(predictions: list[dict], doubles: int, bankos: int, max_surprise: int | None) -> list[MatchPref]:
    prefs: list[MatchPref] = []
    closed_assigned = 0
    double_assigned = 0
    banko_assigned = 0

    for idx, item in enumerate(predictions[:15]):
        pick = str(item.get("prediction_1x2", item.get("pick", "1"))).upper()
        if pick not in {"1", "X", "2"}:
            pick = "1"
        is_banko = False
        is_double = False
        is_closed = False
        if banko_assigned < bankos and idx % 3 == 0:
            is_banko = True
            banko_assigned += 1
        elif double_assigned < doubles and idx % 3 == 1:
            is_double = True
            double_assigned += 1
        elif closed_assigned < 15:
            # closed distribution: prefer lower indexes unless limited later
            pass
        tags: tuple[str, ...] = ()
        if max_surprise is not None and item.get("is_surprise"):
            tags = ("surprise",)
        prefs.append(MatchPref(match_id=str(item.get("match_id", f"M{idx+1:02d}")), pick=pick, is_banko=is_banko, is_double=is_double, is_closed=is_closed, tags=tags))
    # Assign closed matches up to needed counts based on guarantee default minimums
    return prefs


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
    if args.command == "refresh-current-list":
        rows = save_current_list(args.output)
        print(f"Current Spor Toto matches: {len(rows)}")
        return 0
    if args.command == "collect-live":
        result = collect_live(Path(args.output_dir).expanduser(), include_tff=not args.no_tff)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if any("error" not in value for value in result["sources"].values()) else 1
    if args.command == "analyze-next-week":
        result = build_next_week_report(args.matches, args.history, args.output, args.last_n)
        print(f"Next-week report: {args.output}")
        print(f"Matches: {result['match_count']}")
        return 0
    if args.command == "train":
        if args.real:
            frame = build_training_frame(fetch_football_data())
            Path(args.data_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
            frame.to_parquet(Path(args.data_path).expanduser(), index=False)
            from .train import load_records_from_store
            records = load_records_from_store(args.data_path)
            print(f"Real records loaded: {len(records)}")
        else:
            records = generate_synthetic_training_records(args.synthetic_count)
        model = train_model(records, Path(args.model_path).expanduser())
        print(f"Trained model saved to: {args.model_path}")
        return 0
    if args.command == "make-coupon":
        raw_predictions = _load_predictions(args.predictions)
        predictions = _normalize_predictions(raw_predictions)
        prefs = _prefs_from_predictions(predictions, args.doubles, args.bankos, args.max_surprise)
        # Assign closed matches BEFORE filtering so filters can operate on real data
        min_closed = {14: 4, 13: 5, 12: 6}.get(args.guarantee, 6)
        closed_needed = min_closed - sum(1 for p in prefs if p.is_closed)
        if closed_needed > 0:
            candidates = [i for i, p in enumerate(prefs) if not p.is_closed and not p.is_double and not p.is_banko]
            for idx in candidates[:closed_needed]:
                prefs[idx] = MatchPref(match_id=prefs[idx].match_id, pick=prefs[idx].pick, is_banko=prefs[idx].is_banko, is_double=prefs[idx].is_double, is_closed=True, tags=prefs[idx].tags)
        if args.max_draws is not None:
            prefs = apply_filter_by_draws(prefs, args.max_draws)
        if all(v is not None for v in [args.max_home_streak, args.max_draw_streak, args.max_away_streak]):
            prefs = apply_filter_by_streak(prefs, args.max_home_streak, args.max_draw_streak, args.max_away_streak)
        # If filtering reduced closed count, try to assign more closed matches from remaining non-closed items
        current_closed = sum(1 for p in prefs if p.is_closed)
        closed_needed = min_closed - current_closed
        if closed_needed > 0:
            candidates = [i for i, p in enumerate(prefs) if not p.is_closed and not p.is_double and not p.is_banko]
            for idx in candidates[:closed_needed]:
                prefs[idx] = MatchPref(match_id=prefs[idx].match_id, pick=prefs[idx].pick, is_banko=prefs[idx].is_banko, is_double=prefs[idx].is_double, is_closed=True, tags=prefs[idx].tags)
        if args.segment_1_9_max_draws is not None:
            prefs = filter_segment(prefs, 1, 9, max_draws=args.segment_1_9_max_draws)
        if args.segment_10_15_max_draws is not None:
            prefs = filter_segment(prefs, 10, 15, max_draws=args.segment_10_15_max_draws)
        if args.segment_1_9_max_surprise is not None:
            prefs = filter_segment(prefs, 1, 9, max_surprise=args.segment_1_9_max_surprise)
        if args.segment_10_15_max_surprise is not None:
            prefs = filter_segment(prefs, 10, 15, max_surprise=args.segment_10_15_max_surprise)
        rules = CouponRules(guarantee=args.guarantee, columns=9)
        if args.closed is not None:
            rules = CouponRules(guarantee=args.guarantee, columns=9, min_closed_for_14=args.closed, min_closed_for_13=args.closed, min_closed_for_12=args.closed)
        result = generate_coupon(prefs, guarantee=args.guarantee, rules=rules)
        print(format_coupon(result, prefs))
        return 0
    print("No command provided", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
