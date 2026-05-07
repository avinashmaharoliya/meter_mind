from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from features import FEATURE_NAMES


def train(training_csv: Path, output_dir: Path, seed: int = 42):
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(training_csv)
    X = df[FEATURE_NAMES]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.22, random_state=seed, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=350,
        max_depth=12,
        min_samples_leaf=4,
        class_weight="balanced_subsample",
        random_state=seed,
        n_jobs=1,
    )
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    report_text = classification_report(y_test, preds, digits=3)
    report_dict = classification_report(y_test, preds, digits=3, output_dict=True)
    matrix = confusion_matrix(y_test, preds, labels=list(model.classes_))

    joblib.dump({"model": model, "feature_names": FEATURE_NAMES, "classes": list(model.classes_)}, output_dir / "fingerprint_model.joblib")
    (output_dir / "classification_report.txt").write_text(report_text, encoding="utf-8")
    (output_dir / "metrics.json").write_text(
        json.dumps(
            {
                "classification_report": report_dict,
                "labels": list(model.classes_),
                "confusion_matrix": matrix.tolist(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    importances = pd.DataFrame({"feature": FEATURE_NAMES, "importance": model.feature_importances_})
    importances.sort_values("importance", ascending=False).to_csv(output_dir / "feature_importance.csv", index=False)
    print(report_text)
    print(f"Saved model to {output_dir / 'fingerprint_model.joblib'}")
    return model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-csv", type=Path, default=Path("artifacts/training_data.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    train(args.training_csv, args.output_dir, args.seed)


if __name__ == "__main__":
    main()
