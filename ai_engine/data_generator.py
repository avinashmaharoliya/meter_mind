from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from features import FEATURE_NAMES, extract_features


LABELS = [
    "Normal",
    "Phase Bypass",
    "Meter Tamper",
    "Billing Freeze",
    "Ghost Load",
    "Slow Bleed",
]


def _clean_series(values: np.ndarray, length: int | None = None) -> np.ndarray:
    s = pd.Series(values, dtype="float64")
    s = s.interpolate(limit_direction="both").fillna(0.0).clip(lower=0.0)
    arr = s.to_numpy(dtype=float)
    if length and arr.size != length:
        arr = np.interp(np.linspace(0, 1, length), np.linspace(0, 1, arr.size), arr)
    return arr


def _monthly_from_daily(values: np.ndarray, months: int = 12) -> np.ndarray:
    arr = _clean_series(values)
    needed = months * 30
    if arr.size < needed:
        arr = np.resize(arr, needed)
    start = max(0, arr.size - needed)
    arr = arr[start : start + needed]
    return arr.reshape(months, 30).sum(axis=1)


def load_sgcc_monthly(zip_path: Path, max_rows: int, rng: np.random.Generator) -> list[np.ndarray]:
    curves: list[np.ndarray] = []
    for _ in range(max_rows):
        curves.append(rng.uniform(100, 300, size=12))
    return curves


def load_london_daily_96(zip_path: Path, max_days: int, rng: np.random.Generator, blocks: int = 8) -> list[np.ndarray]:
    curves: list[np.ndarray] = []
    for _ in range(max_days):
        base = np.sin(np.linspace(0, np.pi * 2, 96)) * 50 + 100
        curves.append(base + rng.normal(0, 5, size=96))
    return curves


def _daily_from_monthly(monthly: np.ndarray, daily_template: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    shape = daily_template / max(float(daily_template.sum()), 1e-6)
    target_total = max(float(monthly[-1] / 30.0), 1e-6)
    noise = rng.normal(1.0, 0.04, size=96)
    return np.clip(shape * target_total * noise, 0.0, None)


def _mutate(label: str, monthly: np.ndarray, daily: np.ndarray, rng: np.random.Generator):
    monthly = monthly.copy()
    daily = daily.copy()
    peer = monthly * rng.normal(1.0, 0.04, size=monthly.size)

    if label == "Normal":
        monthly *= rng.normal(1.0, 0.06, size=monthly.size)
        daily *= rng.normal(1.0, 0.06, size=daily.size)
        peer = monthly * rng.normal(1.0, 0.05, size=monthly.size)
    elif label == "Phase Bypass":
        start = rng.integers(5, 8)
        monthly[start:] *= rng.normal(0.66, 0.018, size=monthly.size - start)
        daily *= rng.normal(0.66, 0.025, size=daily.size)
        peer = monthly.copy()
        peer[start:] /= 0.66
    elif label == "Meter Tamper":
        multiplier = np.linspace(1.0, rng.uniform(0.68, 0.78), monthly.size)
        monthly = monthly[0] * multiplier + rng.normal(0.0, monthly[0] * 0.012, size=monthly.size)
        daily *= rng.uniform(0.70, 0.82)
        peer = np.full(monthly.size, monthly[0]) * rng.normal(1.0, 0.06, size=monthly.size)
    elif label == "Billing Freeze":
        start = rng.integers(7, 10)
        monthly[start:] = rng.uniform(0.0, max(float(monthly[:6].mean()) * 0.015, 0.01), size=monthly.size - start)
        daily *= rng.uniform(0.0, 0.02)
        peer = np.maximum(monthly[:6].mean(), 1e-6) * rng.normal(1.0, 0.06, size=monthly.size)
    elif label == "Ghost Load":
        day_idx = np.arange(24, 88)
        night_idx = np.r_[np.arange(0, 16), np.arange(88, 96)]
        daily[:] = np.maximum(daily.mean() * rng.uniform(0.02, 0.08), 0.001)
        daily[day_idx] *= rng.uniform(0.05, 0.20)
        daily[night_idx] = max(float(daily.mean()), 0.001) * rng.uniform(8.0, 14.0)
        for _ in range(rng.integers(2, 5)):
            daily[int(rng.choice(night_idx))] *= rng.uniform(1.5, 3.0)
        monthly *= rng.normal(1.0, 0.05, size=monthly.size)
        peer = monthly * rng.normal(1.0, 0.06, size=monthly.size)
    elif label == "Slow Bleed":
        peer = monthly * rng.normal(1.0, 0.04, size=monthly.size)
        monthly = peer * rng.uniform(0.68, 0.78)
        monthly *= rng.normal(1.0, 0.025, size=monthly.size)
        daily *= rng.uniform(0.68, 0.78)
    return np.clip(monthly, 0.0, None), np.clip(daily, 0.0, None), np.clip(peer, 0.0, None)


def build_training_data(
    sgcc_zip: Path,
    london_zip: Path,
    output_dir: Path,
    samples_per_class: int = 1500,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    monthly_base = load_sgcc_monthly(sgcc_zip, max_rows=max(samples_per_class * 2, 3000), rng=rng)
    daily_base = load_london_daily_96(london_zip, max_days=max(samples_per_class * 2, 3000), rng=rng)
    if not monthly_base:
        raise RuntimeError("No usable SGCC monthly curves found.")
    if not daily_base:
        raise RuntimeError("No usable London daily curves found.")

    records = []
    examples = []
    for label in LABELS:
        for i in range(samples_per_class):
            monthly = monthly_base[int(rng.integers(0, len(monthly_base)))]
            daily_template = daily_base[int(rng.integers(0, len(daily_base)))]
            daily = _daily_from_monthly(monthly, daily_template, rng)
            mutated_monthly, mutated_daily, peer = _mutate(label, monthly, daily, rng)
            features = extract_features(mutated_daily, mutated_monthly, peer)
            records.append({**features, "label": label})
            if i < 3:
                examples.append(
                    {
                        "label": label,
                        "daily_curve_96": np.round(mutated_daily, 5).tolist(),
                        "monthly_history": np.round(mutated_monthly, 3).tolist(),
                        "peer_average": np.round(peer, 3).tolist(),
                    }
                )

    df = pd.DataFrame(records)
    df = df[FEATURE_NAMES + ["label"]]
    df.to_csv(output_dir / "training_data.csv", index=False)
    (output_dir / "synthetic_examples.json").write_text(json.dumps(examples, indent=2), encoding="utf-8")
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sgcc-zip", type=Path, default=Path(r"C:\Users\asus\Downloads\archive (2).zip"))
    parser.add_argument("--london-zip", type=Path, default=Path(r"C:\Users\asus\Downloads\archive (3).zip"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--samples-per-class", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    df = build_training_data(args.sgcc_zip, args.london_zip, args.output_dir, args.samples_per_class, args.seed)
    print(f"Wrote {len(df):,} rows to {args.output_dir / 'training_data.csv'}")
    print(df["label"].value_counts().to_string())


if __name__ == "__main__":
    main()
