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
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from .dataset import evaluate_next_week, refresh_news_memory, refresh_sportoto_memory
from .model import MatchModel
from .train import generate_synthetic_training_records, train_model
from .real_training import build_training_frame, fetch_football_data
from .current_list import save_current_list
from .advanced_analytics import fetch_statsbomb_events, parse_statsbomb_events
from .advanced_pipeline import poisson_backtest
from .coupon import CouponRules, CouponResult, MatchPref, format_coupon, generate_coupon, apply_filter_by_surprise, apply_filter_by_draws, apply_filter_by_streak, filter_segment
from .live_monitor import collect_live
from .next_week import build_next_week_report
from .predict_week import build_predictions
from .audit import run_audit
from .multi_source import fetch_api_sports, fetch_football_data as fetch_football_data_source, fetch_openfootball
from .odds import fetch_api_sports_odds, load_local_odds, market_vs_model, fetch_fdccouk, fetch_theodds
from .value_backtest import run_value_backtest


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

    sources_parser = subparsers.add_parser("refresh-sources", help="Refresh configured football data sources")
    sources_parser.add_argument("--date", default=date.today().isoformat())
    sources_parser.add_argument("--output", default="data/live/multi_source/latest.json")
    sources_parser.add_argument("--openfootball-url", default=None)
    sources_parser.add_argument("--no-api-sports", action="store_true")
    sources_parser.add_argument("--no-football-data", action="store_true")

    odds_parser = subparsers.add_parser("fetch-odds", help="Fetch/compare live+closing odds vs model (EV)")
    odds_parser.add_argument("--date", default=date.today().isoformat())
    odds_parser.add_argument("--predictions", default="data/predictions/2026-08-21-predictions_HYBRID.json")
    odds_parser.add_argument("--local-odds", default=None, help="Optional local odds JSON (fixture/cache)")
    odds_parser.add_argument("--source", default="fdccouk", choices=["fdccouk", "api-sports", "local", "the-odds"],
                              help="Odds source: fdccouk=football-data.co.uk (FREE,no key), the-odds=The Odds API (free 500/mo key), api-sports (paid), local")
    odds_parser.add_argument("--season", default="2324", help="football-data.co.uk season (e.g. 2324)")
    odds_parser.add_argument("--league", default="T1", help="football-data.co.uk league (T1=Turkey, E0=EPL, SP1, D1, I1, F1)")
    odds_parser.add_argument("--bookmaker", default="B365", help="bookmaker column prefix (B365, PS, Avg...)")
    odds_parser.add_argument("--output", default="data/live/odds_latest.json")
    odds_parser.add_argument("--no-api", action="store_true", help="Skip API-Sports (use --local-odds)")

    value_parser = subparsers.add_parser("value-backtest", help="Same-season +EV backtest vs real closing odds")
    value_parser.add_argument("--season", default="2324")
    value_parser.add_argument("--league", default="T1", help="T1=Turkey, E0=EPL, SP1, D1, I1, F1")
    value_parser.add_argument("--bookmaker", default="B365")
    value_parser.add_argument("--stake", type=float, default=1.0)
    value_parser.add_argument("--all-bets", action="store_true", help="Bet every pick (not only +EV)")

    advanced_parser = subparsers.add_parser("advanced-statsbomb", help="Parse StatsBomb Open Data event JSON")
    advanced_parser.add_argument("--url", required=True)
    advanced_parser.add_argument("--output", default="data/analysis/statsbomb_metrics.json")

    backtest_parser = subparsers.add_parser("advanced-backtest", help="Run leakage-safe xG Poisson backtest")
    backtest_parser.add_argument("--input", required=True, help="JSON list of dated match rows")
    backtest_parser.add_argument("--output", default="data/analysis/advanced-backtest.json")
    backtest_parser.add_argument("--min-history", type=int, default=3)

    next_parser = subparsers.add_parser("analyze-next-week", help="Build recent team-form report")
    next_parser.add_argument("--matches", default="data/current_sportoto_list.json")
    next_parser.add_argument("--history", default="data/sportoto_master_training.parquet")
    next_parser.add_argument("--output", default="data/next_week_analysis.json")
    next_parser.add_argument("--last-n", type=int, default=5)

    week_parser = subparsers.add_parser("predict-week", help="Predict the current 15-match Spor Toto list from historical training data")
    week_parser.add_argument("--list", default="data/current_sportoto_list_2026-08-21.json")
    week_parser.add_argument("--history", default="data/sportoto_master_training.parquet")
    week_parser.add_argument("--model", default="data/models/sportoto_master_model.joblib")
    week_parser.add_argument("--output", default="data/predictions/2026-08-21-predictions.json")
    week_parser.add_argument("--last-n", type=int, default=8)

    audit_parser = subparsers.add_parser("audit-results", help="Match saved predictions against real results (hit/miss + O/U)")
    audit_parser.add_argument("--predictions", default="data/predictions/2026-08-21-predictions.json")
    audit_parser.add_argument("--date", default=None, help="API-Sports date filter YYYY-MM-DD")
    audit_parser.add_argument("--no-api", action="store_true", help="Skip API-Sports")
    audit_parser.add_argument("--use-fdccouk", action="store_true",
                               help="Use football-data.co.uk real results (FREE, no key) as results source")
    audit_parser.add_argument("--fdccouk-season", default="2324")
    audit_parser.add_argument("--fdccouk-league", default="T1")
    audit_parser.add_argument("--output-dir", default="data/live/audit")

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


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


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
    if args.command == "refresh-sources":
        _load_dotenv()
        report = {"fetched_at": datetime.now(timezone.utc).isoformat(), "date": args.date, "sources": {}}
        if not args.no_api_sports:
            try:
                rows = fetch_api_sports(args.date)
                report["sources"]["api-sports"] = {"count": len(rows), "matches": [row.to_dict() for row in rows]}
            except Exception as exc:
                report["sources"]["api-sports"] = {"error": str(exc), "count": 0}
        if not args.no_football_data:
            try:
                rows = fetch_football_data_source()
                report["sources"]["football-data.org"] = {"count": len(rows), "matches": [row.to_dict() for row in rows]}
            except Exception as exc:
                report["sources"]["football-data.org"] = {"error": str(exc), "count": 0}
        if args.openfootball_url:
            try:
                rows = fetch_openfootball(args.openfootball_url)
                report["sources"]["openfootball"] = {"count": len(rows), "matches": [row.to_dict() for row in rows]}
            except Exception as exc:
                report["sources"]["openfootball"] = {"error": str(exc), "count": 0}
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(output), "sources": {k: v.get("count", 0) for k, v in report["sources"].items()}}, ensure_ascii=False))
        return 0 if any(v.get("count", 0) > 0 for v in report["sources"].values()) else 1
    if args.command == "advanced-statsbomb":
        events = fetch_statsbomb_events(args.url)
        metrics = parse_statsbomb_events(events)
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "source": "StatsBomb Open Data",
            "url": args.url,
            "event_count": metrics.event_count,
            "xg_by_team": metrics.xg_by_team,
            "xa_by_team": metrics.xa_by_team,
            "ppda_by_team": metrics.ppda_by_team,
            "key_passes_by_team": metrics.key_passes_by_team,
            "defensive_actions_by_team": metrics.defensive_actions_by_team,
            "shots": [shot.__dict__ for shot in metrics.shots],
        }
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(output), "events": metrics.event_count, "shots": len(metrics.shots), "xg": metrics.xg_by_team}, ensure_ascii=False))
        return 0
    if args.command == "advanced-backtest":
        input_path = Path(args.input).expanduser()
        rows = json.loads(input_path.read_text(encoding="utf-8"))
        if isinstance(rows, dict):
            rows = rows.get("matches", rows.get("rows", []))
        if not isinstance(rows, list):
            raise ValueError("advanced-backtest input must be a JSON list or contain matches/rows")
        result = poisson_backtest(rows, min_history=args.min_history)
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(output), **result}, ensure_ascii=False))
        return 0
    if args.command == "analyze-next-week":
        result = build_next_week_report(args.matches, args.history, args.output, args.last_n)
        print(f"Next-week report: {args.output}")
        print(f"Matches: {result['match_count']}")
        return 0
    if args.command == "predict-week":
        payload = build_predictions(args.list, args.history, args.model, args.output, args.last_n)
        print(f"Predictions: {payload['match_count']} matches -> {args.output}")
        for p in payload["predictions"]:
            print(f"  M{p['match_index']:>2} {p['home_team'][:20]:20} - {p['away_team'][:20]:20} "
                  f"=> {p['predicted_1x2']} (conf {p['confidence']}) | O/U {p['predicted_ou']} "
                  f"(O {p['pred_over_2_5']})")
        return 0
    if args.command == "fetch-odds":
        _load_dotenv()
        preds = json.loads(Path(args.predictions).expanduser().read_text(encoding="utf-8"))
        preds = preds["predictions"] if isinstance(preds, dict) else preds
        odds = []
        if args.source == "local" or args.local_odds:
            odds = load_local_odds(args.local_odds)
            src_note = f"local:{args.local_odds}"
        elif args.source == "fdccouk":
            try:
                odds = fetch_fdccouk(args.season, args.league, args.bookmaker)
                src_note = f"fdccouk:{args.league}-{args.season}-{args.bookmaker}"
            except Exception as exc:
                print(f"football-data.co.uk erişilemedi: {exc}", file=sys.stderr)
                return 1
        elif args.source == "api-sports" and not args.no_api:
            try:
                odds = fetch_api_sports_odds(args.date)
                src_note = "api-sports"
            except Exception as exc:
                print(f"API-Sports odds erişilemedi (muhtemelen Free plan): {exc}", file=sys.stderr)
                return 1
        elif args.source == "the-odds":
            try:
                sport = {"T1": "soccer_turkey_super_league", "E0": "soccer_epl",
                         "SP1": "soccer_spain_la_liga", "D1": "soccer_germany_bundesliga",
                         "I1": "soccer_italy_serie_a", "F1": "soccer_france_ligue_one"}.get(
                            args.league, "soccer_turkey_super_league")
                odds = fetch_theodds(sport, bookmaker=args.bookmaker if args.bookmaker != "B365" else None)
                src_note = f"the-odds:{sport}"
            except Exception as exc:
                print(f"The Odds API erişilemedi: {exc}", file=sys.stderr)
                print("Ücretsiz key için: https://the-odds-api.com/#get-access (500 kredi/ay)", file=sys.stderr)
                return 1
        else:
            print("Oran kaynağı belirtin: --source fdccouk|local|api-sports", file=sys.stderr)
            return 2
        joined = market_vs_model(odds, preds)
        out = Path(args.output).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"source": src_note, "compared": joined}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Oran karşılaştırması: {len(joined)} maç -> {out} (kaynak: {src_note})")
        for r in joined:
            ev = r["ev"]
            print(f"  {r['home_team'][:16]:16} - {r['away_team'][:16]:16} pick={r['predicted_1x2']} "
                  f"model={r['model_prob']} odds={r['odds']} EV={ev}")
        return 0
    if args.command == "value-backtest":
        res = run_value_backtest(season=args.season, league=args.league,
                                 bookmaker=args.bookmaker, stake=args.stake,
                                 only_positive_ev=not args.all_bets)
        print(f"Value backtest ({res['season']} {res['league']} {res['bookmaker']}):")
        print(f"  Pencere maç: {res['window_matches']} | Oran eşleşen: {res['odds_matched']}")
        print(f"  Bahis: {res['bets_placed']} | PnL: {res['pnl']} | ROI: {res['roi_pct']}% | Kazanma: {res['win_rate']}")
        print(f"  Not: {res['note']}")
        return 0
    if args.command == "audit-results":
        summary = run_audit(args.predictions, args.output_dir, api_date=args.date,
                           use_api_sports=not args.no_api,
                           use_fdccouk=args.use_fdccouk,
                           fdccouk_season=args.fdccouk_season,
                           fdccouk_league=args.fdccouk_league)
        print(f"Audit: {summary['matches_with_result']}/{summary['matches_total']} maçta sonuç var")
        print(f"1X2 isabet: {summary['hit_1x2']}/{summary['matches_with_result']} = {summary['accuracy_1x2']}")
        if summary["matches_with_ou"]:
            print(f"Alt/Üst isabet: {summary['hit_ou']}/{summary['matches_with_ou']} = {summary['accuracy_ou']}")
        print("Kaynaklar:", summary["sources_used"])
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
