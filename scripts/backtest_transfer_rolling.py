"""Rolling, leakage-safe backtest for transfer-enhanced 1/X/2 models."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from train_real_walkforward import FEATURE_COLS, TRANSFER_FEATURE_COLS, load_and_enrich
from sportoto.transfer_features import COUNT_FEATURE_COLUMNS


def _classifier() -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(
            loss="log_loss", n_estimators=180, max_depth=3,
            learning_rate=0.05, random_state=42,
        )),
    ])


def rolling_backtest(df, feature_cols: list[str], min_train: int = 500, test_size: int = 200, step: int = 200):
    df = df.sort_values("_ko").reset_index(drop=True)
    folds = []
    for train_end in range(min_train, len(df) - 1, step):
        test_end = min(train_end + test_size, len(df))
        train = df.iloc[:train_end]
        test = df.iloc[train_end:test_end]
        if len(test) == 0 or train["actual_1x2"].nunique() < 3:
            continue
        clf = _classifier()
        x_train = train[feature_cols].to_numpy(float)
        y_train = train["actual_1x2"].to_numpy(int)
        x_test = test[feature_cols].to_numpy(float)
        y_test = test["actual_1x2"].to_numpy(int)
        clf.fit(x_train, y_train)
        pred = clf.predict(x_test)
        probs = clf.predict_proba(x_test)
        classes = clf.named_steps["clf"].classes_
        aligned = np.zeros((len(test), 3), dtype=float)
        for i, cls in enumerate(classes):
            aligned[:, int(cls)] = probs[:, i]
        baseline = float(np.bincount(y_train, minlength=3).max() / len(y_train))
        folds.append({
            "train_end": int(train_end), "test_size": int(len(test)),
            "train_window": [str(train["_ko"].min()), str(train["_ko"].max())],
            "test_window": [str(test["_ko"].min()), str(test["_ko"].max())],
            "accuracy": round(float(accuracy_score(y_test, pred)), 4),
            "baseline": round(baseline, 4),
            "lift": round(float(accuracy_score(y_test, pred) - baseline), 4),
            "brier": round(float(np.mean([
                brier_score_loss((y_test == cls).astype(int), aligned[:, cls])
                for cls in range(3)
            ])), 4),
            "log_loss": round(float(log_loss(y_test, aligned, labels=[0, 1, 2])), 4),
        })
    if not folds:
        raise ValueError("Rolling backtest için yeterli ve üç sınıflı veri yok")
    total_test = sum(f["test_size"] for f in folds)
    return {
        "folds": folds,
        "fold_count": len(folds),
        "evaluated_matches": total_test,
        "mean_accuracy": round(float(np.mean([f["accuracy"] for f in folds])), 4),
        "mean_baseline": round(float(np.mean([f["baseline"] for f in folds])), 4),
        "mean_lift": round(float(np.mean([f["lift"] for f in folds])), 4),
        "mean_brier": round(float(np.mean([f["brier"] for f in folds])), 4),
        "mean_log_loss": round(float(np.mean([f["log_loss"] for f in folds])), 4),
        "all_folds_positive_lift": all(f["lift"] > 0 for f in folds),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--transfer-csv", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--model-out", required=True)
    ap.add_argument("--transfer-mode", choices=["all", "counts"], default="counts")
    args = ap.parse_args()
    df = load_and_enrich(args.parquet, args.transfer_csv)
    feature_cols = FEATURE_COLS + (COUNT_FEATURE_COLUMNS if args.transfer_mode == "counts" else TRANSFER_FEATURE_COLS)
    metrics = rolling_backtest(df, feature_cols)
    final = _classifier()
    final.fit(df[feature_cols].to_numpy(float), df["actual_1x2"].to_numpy(int))
    Path(args.model_out).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final, args.model_out)
    report = {
        "model": "transfer_enhanced_rolling",
        "input": args.parquet,
        "transfer_csv": args.transfer_csv,
        "transfer_mode": args.transfer_mode,
        "features": feature_cols,
        "metrics": metrics,
        "model_out": args.model_out,
        "ship": metrics["all_folds_positive_lift"] and metrics["mean_lift"] > 0,
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
