from __future__ import annotations

import math
from typing import Iterable

import numpy as np


FEATURE_NAMES = [
    "daily_total",
    "daily_mean",
    "daily_std",
    "daily_cv",
    "daily_min",
    "daily_max",
    "max_to_mean_ratio",
    "load_factor",
    "night_ratio",
    "day_ratio",
    "evening_ratio",
    "peak_hour",
    "peak_is_night",
    "zero_fraction",
    "max_zero_run",
    "daily_slope",
    "daily_entropy",
    "baseline_ratio",
    "recent_drop_ratio",
    "monthly_slope",
    "decline_variance",
    "monthly_cv",
    "near_zero_months",
    "consecutive_zero_delta_count",
    "flatline_score",
    "peer_group_ratio",
    "peer_gap_ratio",
]


def _clean(values: Iterable[float], length: int | None = None) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        arr = np.zeros(length or 1, dtype=float)
    arr = np.nan_to_num(arr, nan=np.nanmedian(arr) if np.isfinite(arr).any() else 0.0)
    arr = np.clip(arr, 0.0, None)
    if length and arr.size != length:
        old_x = np.linspace(0, 1, arr.size)
        new_x = np.linspace(0, 1, length)
        arr = np.interp(new_x, old_x, arr)
    return arr


def _safe_div(num: float, den: float) -> float:
    return float(num / den) if abs(den) > 1e-9 else 0.0


def _max_run(mask: np.ndarray) -> int:
    best = 0
    current = 0
    for item in mask:
        current = current + 1 if item else 0
        best = max(best, current)
    return int(best)


def _entropy(values: np.ndarray) -> float:
    total = float(values.sum())
    if total <= 1e-9:
        return 0.0
    p = values / total
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum() / math.log2(max(values.size, 2)))


def extract_features(
    timeseries_array: Iterable[float],
    monthly_history: Iterable[float] | None = None,
    peer_average: Iterable[float] | None = None,
) -> dict[str, float]:
    """Extract stable MVP features from a daily curve and optional history.

    Parameters
    ----------
    timeseries_array:
        One day of smart-meter readings. The backend can pass 96 values
        directly. If 48 half-hourly values are passed, they are resampled to 96.
    monthly_history:
        Optional 12 monthly consumption values. This makes Phase Bypass, Meter
        Tamper, Billing Freeze, and Slow Bleed much stronger.
    peer_average:
        Optional peer-group monthly average values, used for Slow Bleed.
    """
    daily = _clean(timeseries_array, length=96)
    total = float(daily.sum())
    mean = float(daily.mean())
    std = float(daily.std())
    max_value = float(daily.max())
    min_value = float(daily.min())

    night = np.r_[daily[:16], daily[88:96]]  # 10 PM-4 AM at 15-min resolution
    day = daily[24:88]  # 6 AM-10 PM
    evening = daily[68:88]  # 5 PM-10 PM

    x_daily = np.arange(daily.size)
    daily_slope = float(np.polyfit(x_daily, daily, 1)[0]) if daily.size > 1 else 0.0
    peak_index = int(np.argmax(daily))
    peak_hour = float(peak_index / 4.0)
    peak_is_night = 1.0 if peak_hour >= 22.0 or peak_hour < 4.0 else 0.0
    zero_threshold = max(mean * 0.03, 1e-6)
    zero_mask = daily <= zero_threshold

    monthly_is_missing = monthly_history is None
    if monthly_is_missing:
        monthly = np.full(12, mean * 30.0)
    else:
        monthly = _clean(monthly_history, length=12)

    baseline = float(monthly[:6].mean()) if monthly.size >= 6 else float(monthly.mean())
    recent = float(monthly[-3:].mean()) if monthly.size >= 3 else float(monthly.mean())
    prev_recent = float(monthly[-6:-3].mean()) if monthly.size >= 6 else baseline
    month_x = np.arange(monthly.size)
    monthly_slope = float(np.polyfit(month_x, monthly, 1)[0]) if monthly.size > 1 else 0.0
    month_changes = np.diff(monthly)
    decline_variance = float(np.std(month_changes))
    zero_month_threshold = max(baseline * 0.03, 1e-6)
    near_zero_months = float((monthly <= zero_month_threshold).sum())
    zero_delta_mask = np.abs(month_changes) <= zero_month_threshold

    peer_is_missing = peer_average is None
    if peer_is_missing:
        peers = monthly.copy()
    else:
        peers = _clean(peer_average, length=monthly.size)
    peer_mean = float(peers[-3:].mean()) if peers.size >= 3 else float(peers.mean())

    features = {
        "daily_total": total,
        "daily_mean": mean,
        "daily_std": std,
        "daily_cv": _safe_div(std, mean),
        "daily_min": min_value,
        "daily_max": max_value,
        "max_to_mean_ratio": _safe_div(max_value, mean),
        "load_factor": _safe_div(mean, max_value),
        "night_ratio": _safe_div(float(night.sum()), total),
        "day_ratio": _safe_div(float(day.sum()), total),
        "evening_ratio": _safe_div(float(evening.sum()), total),
        "peak_hour": peak_hour,
        "peak_is_night": peak_is_night,
        "zero_fraction": float(zero_mask.mean()),
        "max_zero_run": float(_max_run(zero_mask)),
        "daily_slope": daily_slope,
        "daily_entropy": _entropy(daily),
        "baseline_ratio": _safe_div(recent, baseline),
        "recent_drop_ratio": _safe_div(recent, prev_recent),
        "monthly_slope": monthly_slope,
        "decline_variance": decline_variance,
        "monthly_cv": _safe_div(float(monthly.std()), float(monthly.mean())),
        "near_zero_months": near_zero_months,
        "consecutive_zero_delta_count": float(_max_run(zero_delta_mask)),
        "flatline_score": 1.0 - min(_safe_div(decline_variance, max(float(monthly.mean()), 1e-6)), 1.0),
        "peer_group_ratio": _safe_div(recent, peer_mean),
        "peer_gap_ratio": _safe_div(peer_mean - recent, peer_mean),
    }
    if monthly_is_missing:
        features.update(
            {
                "baseline_ratio": 1.0,
                "recent_drop_ratio": 1.0,
                "monthly_slope": 0.0,
                "decline_variance": 0.0,
                "monthly_cv": 0.0,
                "near_zero_months": 0.0,
                "consecutive_zero_delta_count": 0.0,
                "flatline_score": 0.0,
            }
        )
    if peer_is_missing:
        features.update({"peer_group_ratio": 1.0, "peer_gap_ratio": 0.0})
    return {name: float(features.get(name, 0.0)) for name in FEATURE_NAMES}


def feature_vector(*args, **kwargs) -> list[float]:
    features = extract_features(*args, **kwargs)
    return [features[name] for name in FEATURE_NAMES]
