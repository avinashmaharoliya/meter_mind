from __future__ import annotations

from pathlib import Path
from typing import Iterable

import joblib
import pandas as pd

from features import FEATURE_NAMES, extract_features


ACTION_LOOKUP = {
    "Phase Bypass": {
        "recommended_action": "Check LT line connections before meter entry point.",
        "equipment": "Wire detection device, phase tester",
        "legal_form": "Form 47B - Theft Notice",
    },
    "Meter Tamper": {
        "recommended_action": "Inspect meter body for magnets, foreign devices, seal damage, and physical tampering.",
        "equipment": "Magnet detector, seal inspection kit",
        "legal_form": "Form 47B + tamper report",
    },
    "Billing Freeze": {
        "recommended_action": "Check whether the meter display is active and readings are advancing.",
        "equipment": "Meter replacement unit",
        "legal_form": "Meter replacement order",
    },
    "Ghost Load": {
        "recommended_action": "Night inspection between 10 PM and 2 AM. Check for commercial equipment running off-hours.",
        "equipment": "Load testing kit, night inspection authority letter",
        "legal_form": "Form 47B - Commercial Fraud",
    },
    "Slow Bleed": {
        "recommended_action": "Full physical line inspection from service pole to meter.",
        "equipment": "Wire tracing equipment",
        "legal_form": "Form 47B - Chronic Theft",
    },
    "Normal": {
        "recommended_action": "No field action required.",
        "equipment": "None",
        "legal_form": "None",
    },
}


def load_model(model_path: str | Path = "artifacts/fingerprint_model.joblib"):
    bundle = joblib.load(model_path)
    return bundle["model"], bundle.get("feature_names", FEATURE_NAMES)


def predict_fingerprint(
    timeseries_array: Iterable[float],
    monthly_history: Iterable[float] | None = None,
    peer_average: Iterable[float] | None = None,
    model_path: str | Path = "artifacts/fingerprint_model.joblib",
) -> dict:
    model, feature_names = load_model(model_path)
    features = extract_features(timeseries_array, monthly_history, peer_average)
    X = pd.DataFrame([[features[name] for name in feature_names]], columns=feature_names)
    probabilities = model.predict_proba(X)[0]
    best_idx = int(probabilities.argmax())
    label = str(model.classes_[best_idx])
    confidence = float(probabilities[best_idx])
    response = {
        "fingerprint": label,
        "confidence": round(confidence, 4),
        "confidence_percent": round(confidence * 100, 2),
        "features": features,
        "class_probabilities": {
            str(cls): round(float(prob), 4) for cls, prob in zip(model.classes_, probabilities)
        },
    }
    response.update(ACTION_LOOKUP[label])
    return response


if __name__ == "__main__":
    sample = [0.05] * 24 + [0.001] * 64 + [0.7] * 8
    print(predict_fingerprint(sample))
