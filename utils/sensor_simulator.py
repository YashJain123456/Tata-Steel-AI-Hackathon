import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from backend.anomaly_detector import THRESHOLDS


def current_readings(equipment: str, anomaly_mode: bool = False) -> dict:
    """Generate a single sensor snapshot for an equipment."""
    thresholds = THRESHOLDS.get(equipment, {})
    readings: dict[str, float] = {}
    for param, (lo, hi) in thresholds.items():
        mid, std = (lo + hi) / 2, (hi - lo) / 7
        val = random.gauss(mid, std)
        if anomaly_mode and random.random() < 0.35:
            # Push beyond range
            if random.random() < 0.5:
                val = hi + random.uniform(0.05 * (hi - lo), 0.25 * (hi - lo))
            else:
                val = lo - random.uniform(0.05 * (hi - lo), 0.25 * (hi - lo))
        readings[param] = round(float(np.clip(val, lo * 0.6, hi * 1.4)), 2)
    return readings


def generate_timeseries(
    equipment: str,
    n_points: int = 60,
    interval_minutes: int = 5,
    anomaly_fraction: float = 0.08,
) -> pd.DataFrame:
    """Generate a time-series DataFrame for trending charts."""
    thresholds = THRESHOLDS.get(equipment, {})
    rows = []
    base = datetime.now() - timedelta(minutes=n_points * interval_minutes)
    for i in range(n_points):
        ts           = base + timedelta(minutes=i * interval_minutes)
        anomaly_mode = random.random() < anomaly_fraction
        r            = current_readings(equipment, anomaly_mode=anomaly_mode)
        r["timestamp"]  = ts
        r["is_anomaly"] = anomaly_mode
        rows.append(r)
    return pd.DataFrame(rows)


def health_score(equipment: str, readings: dict) -> float:
    """Return 0–100 health based on how centred readings are within their normal range."""
    thresholds = THRESHOLDS.get(equipment, {})
    if not thresholds:
        return 100.0
    scores = []
    for param, (lo, hi) in thresholds.items():
        val  = readings.get(param)
        if val is None:
            continue
        mid  = (lo + hi) / 2
        half = (hi - lo) / 2
        if half == 0:
            scores.append(100.0)
            continue
        dev  = abs(val - mid) / half          # 0 = centre, 1 = at limit, >1 = outside
        h    = max(0.0, 100.0 * (1 - dev))
        scores.append(h)
    return round(float(np.mean(scores)) if scores else 100.0, 1)


def all_equipment_snapshot(anomaly_equipment: str | None = None) -> dict[str, dict]:
    """Return current readings for all equipment, optionally forcing anomaly on one."""
    return {
        eq: current_readings(eq, anomaly_mode=(eq == anomaly_equipment))
        for eq in THRESHOLDS
    }
