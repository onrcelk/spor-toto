"""Gerçek veriyle leak-free eğitim + walk-forward (time-ordered) doğrulama.

- ELO'yu SADECE o maçtan önceki maçların 1X2 sonucundan hesaplar (leak yok).
- Walk-forward: zaman sırasına göre ilk %train train, kalanı test (asla shuffle yok).
- Baseline = train setteki majority-class (her zaman ev sahibi galibiyeti) oranı.
- Ship yalnızca lift = acc - baseline > 0 ise.

Kullanım:
  uv run python scripts/train_real_walkforward.py --parquet data/real_training.parquet \
      --out data/models/real_superlig_wf.joblib --tag superlig
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_COLS = [
    "home_goals_avg", "away_goals_avg", "home_conceded_avg", "away_conceded_avg",
    "home_form_points", "away_form_points", "h2h_home_win_rate", "h2h_draw_rate",
    "h2h_away_win_rate", "home_xg_avg", "away_xg_avg", "is_derby",
    "rest_days_home", "rest_days_away", "elo_diff",
]
TRANSFER_FEATURE_COLS = [
    "home_transfer_in_count_365", "home_transfer_out_count_365", "home_transfer_net_fee_365",
    "away_transfer_in_count_365", "away_transfer_out_count_365", "away_transfer_net_fee_365",
]


def load_and_enrich(parquet: str, transfer_csv: str | None = None) -> pd.DataFrame:
    df = pd.read_parquet(parquet)
    # Timestamp: datasets contain ISO, DD.MM.YYYY HH:MM and DD/MM/YYYY.
    # Parse mixed formats in one pass; the previous fallback only ran when
    # *all* first-pass values failed, silently leaving mixed-format rows as NaT.
    ko = pd.to_datetime(
        df["kickoff_iso"].astype(str),
        format="mixed",
        dayfirst=True,
        utc=True,
        errors="coerce",
    )
    if ko.isna().any():
        bad = int(ko.isna().sum())
        raise ValueError(f"HATA: {bad} kickoff_iso değeri parse edilemedi")
    df = df.assign(_ko=ko).sort_values("_ko").reset_index(drop=True)

    if transfer_csv:
        from sportoto.transfer_features import build_transfer_features
        df = build_transfer_features(transfer_csv, df)

    # Leak-free ELO: sadece önceki maçların 1X2 sonucu (gol değil)
    elo: dict[str, float] = {}
    elo_diff = []
    for _, r in df.iterrows():
        h, a = r["home_team"], r["away_team"]
        eh = elo.get(h, 1500.0)
        ea = elo.get(a, 1500.0)
        elo_diff.append(eh - ea)
        res = int(r["actual_1x2"])
        res_h = 1.0 if res == 0 else (0.5 if res == 1 else 0.0)
        exp_h = 1.0 / (1.0 + 10 ** ((ea - eh) / 400.0))
        elo[h] = eh + 32 * (res_h - exp_h)
        elo[a] = ea + 32 * ((1 - res_h) - (1 - exp_h))
    df["elo_diff"] = elo_diff
    return df


def walk_forward(df: pd.DataFrame, train_frac: float, feature_cols: list[str] = FEATURE_COLS):
    n = len(df)
    k = int(n * train_frac)
    train = df.iloc[:k]
    test = df.iloc[k:]
    Xtr = train[feature_cols].to_numpy(float)
    ytr = train["actual_1x2"].to_numpy(int)
    Xte = test[feature_cols].to_numpy(float)
    yte = test["actual_1x2"].to_numpy(int)

    # Baseline: train setteki majority class
    counts = np.bincount(ytr, minlength=3).astype(float)
    baseline = float(counts.argmax())  # çoğunluk sınıfı etiketi
    baseline_rate = float(counts.max() / counts.sum())

    clf = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(loss="log_loss", n_estimators=180,
                                           max_depth=3, learning_rate=0.05,
                                           random_state=42)),
    ])
    clf.fit(Xtr, ytr)
    pred = clf.predict(Xte)
    acc = float((pred == yte).mean())
    return clf, {
        "n_total": n, "n_train": len(train), "n_test": len(test),
        "train_window": [str(train["_ko"].min()), str(train["_ko"].max())],
        "test_window": [str(test["_ko"].min()), str(test["_ko"].max())],
        "baseline_class": int(baseline),
        "baseline_rate": round(baseline_rate, 4),
        "test_accuracy": round(acc, 4),
        "lift": round(acc - baseline_rate, 4),
        "test_1x2_dist": {int(k_): int(v_) for k_, v_ in pd.Series(yte).value_counts().items()},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--transfer-csv", default=None)
    ap.add_argument("--train-frac", type=float, default=0.7)
    ap.add_argument("--report", default="data/models/walkforward_report.json")
    args = ap.parse_args()

    df = load_and_enrich(args.parquet, args.transfer_csv)
    if df["_ko"].isna().all():
        raise SystemExit("HATA: veri setinde timestamp yok -> walk-forward yapılamaz. "
                         "Bu set yalnızca fit edilebilir (zaman sırası bilinmiyor).")

    feature_cols = FEATURE_COLS + (TRANSFER_FEATURE_COLS if args.transfer_csv else [])
    clf, metrics = walk_forward(df, args.train_frac, feature_cols)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, args.out)

    ship = metrics["lift"] > 0
    metrics.update({"tag": args.tag, "model_out": args.out, "ship": ship,
                    "features": feature_cols, "transfer_csv": args.transfer_csv})

    # Raporu biriktir
    rep_path = Path(args.report)
    rep = json.loads(rep_path.read_text()) if rep_path.exists() else {"runs": []}
    rep["runs"].append(metrics)
    rep_path.write_text(json.dumps(rep, indent=2, ensure_ascii=False))

    print(f"\n=== {args.tag} ===")
    print(f"  satır: {metrics['n_total']} (train {metrics['n_train']} / test {metrics['n_test']})")
    print(f"  train pencere: {metrics['train_window']}")
    print(f"  test  pencere: {metrics['test_window']}")
    print(f"  baseline (çoğunluk sınıfı {metrics['baseline_class']}): {metrics['baseline_rate']}")
    print(f"  test accuracy: {metrics['test_accuracy']}")
    print(f"  LIFT: {metrics['lift']}  -> {'SHIP ✅' if ship else 'REJECT ❌ (lift<=0)'}")
    print(f"  model: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
