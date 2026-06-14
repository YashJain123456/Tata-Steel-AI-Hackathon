import os
import pickle
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

# Suppress sklearn feature-name warning (scaler is fitted on DataFrame, predicted with DataFrame too)
warnings.filterwarnings("ignore", message="X does not have valid feature names")

THRESHOLDS: dict[str, dict[str, tuple[float, float]]] = {
    "Rolling Mill": {
        "temperature_c":    (60.0,  150.0),
        "vibration_mms":    (0.0,   8.0),
        "pressure_bar":     (100.0, 250.0),
        "motor_current_a":  (200.0, 500.0),
        "roll_speed_rpm":   (800.0, 1500.0),
    },
    "Blast Furnace": {
        "hot_blast_temp_c":       (900.0,  1300.0),
        "top_pressure_bar":       (1.5,    4.5),
        "burden_descent_mm_min":  (40.0,   120.0),
        "oxygen_enrichment_pct":  (2.0,    8.0),
    },
    "Continuous Caster": {
        "tundish_temp_c":        (1480.0, 1560.0),
        "casting_speed_mpm":     (0.8,    2.5),
        "mold_water_flow_lpm":   (1200.0, 2000.0),
        "vibration_mms":         (0.0,    5.0),
    },
    "Hydraulic System": {
        "system_pressure_bar": (150.0, 300.0),
        "oil_temperature_c":   (30.0,  70.0),
        "flow_rate_lpm":       (20.0,  100.0),
        "oil_level_pct":       (60.0,  100.0),
    },
    "Ladle Furnace": {
        "steel_temp_c":    (1500.0, 1650.0),
        "arc_current_ka":  (20.0,   50.0),
        "argon_flow_nlpm": (300.0,  1200.0),
        "power_mw":        (10.0,   40.0),
    },
    "Compressor": {
        "discharge_pressure_bar": (6.0,    10.0),
        "discharge_temp_c":       (30.0,   100.0),
        "vibration_mms":          (0.0,    5.0),
        "motor_current_a":        (50.0,   150.0),
        "speed_rpm":              (2940.0, 3060.0),
    },
}

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "models")


class AnomalyDetector:
    def __init__(self):
        os.makedirs(MODEL_DIR, exist_ok=True)
        self.models:  dict[str, IsolationForest] = {}
        self.scalers: dict[str, StandardScaler]  = {}
        for eq in THRESHOLDS:
            self._load_or_train(eq)

    def detect(self, equipment: str, readings: dict) -> dict:
        thresholds  = THRESHOLDS.get(equipment, {})
        alerts      = self._threshold_checks(readings, thresholds)
        ml_score, is_anomaly = self._ml_score(equipment, readings, thresholds)
        risk_level  = self._classify_risk(alerts, ml_score, is_anomaly)
        return {
            "is_anomaly":    is_anomaly or bool(alerts),
            "anomaly_score": round(ml_score, 3),
            "alerts":        alerts,
            "risk_level":    risk_level,
            "timestamp":     datetime.now().isoformat(),
        }

    def get_thresholds(self, equipment: str) -> dict:
        return THRESHOLDS.get(equipment, {})

    @staticmethod
    def get_equipment_list() -> list[str]:
        return list(THRESHOLDS.keys())

    @staticmethod
    def _threshold_checks(readings: dict, thresholds: dict) -> list[dict]:
        alerts = []
        for param, value in readings.items():
            if param not in thresholds:
                continue
            low, high = thresholds[param]
            if value < low:
                severity = "CRITICAL" if value < low * 0.85 else "HIGH"
                alerts.append({"parameter": param, "value": round(value, 2),
                                "range": f"{low}–{high}", "type": "LOW", "severity": severity,
                                "message": f"{param} below normal: {value:.2f} (min {low})"})
            elif value > high:
                severity = "CRITICAL" if value > high * 1.15 else "HIGH"
                alerts.append({"parameter": param, "value": round(value, 2),
                                "range": f"{low}–{high}", "type": "HIGH", "severity": severity,
                                "message": f"{param} above normal: {value:.2f} (max {high})"})
        return alerts

    def _ml_score(self, equipment: str, readings: dict, thresholds: dict) -> tuple[float, bool]:
        if equipment not in self.models:
            return 0.0, False
        params = list(thresholds.keys())
        vals   = [readings.get(p, (thresholds[p][0] + thresholds[p][1]) / 2) for p in params]
        try:
            # Pass DataFrame with feature names to match how scaler was fitted
            X_df  = pd.DataFrame([vals], columns=params)
            X     = self.scalers[equipment].transform(X_df)
            score = float(self.models[equipment].decision_function(X)[0])
            pred  = int(self.models[equipment].predict(X)[0])
            normalised = max(0.0, min(1.0, 0.5 - score))
            return normalised, pred == -1
        except Exception:
            return 0.0, False

    @staticmethod
    def _classify_risk(alerts: list, ml_score: float, is_anomaly: bool) -> str:
        has_critical = any(a["severity"] == "CRITICAL" for a in alerts)
        has_high     = any(a["severity"] == "HIGH"     for a in alerts)
        if has_critical or ml_score > 0.75: return "CRITICAL"
        if has_high     or ml_score > 0.55: return "HIGH"
        if alerts       or ml_score > 0.35: return "MEDIUM"
        if is_anomaly   or ml_score > 0.20: return "LOW"
        return "NORMAL"

    def _load_or_train(self, equipment: str):
        safe  = equipment.replace(" ", "_")
        mpath = os.path.join(MODEL_DIR, f"{safe}_model.pkl")
        spath = os.path.join(MODEL_DIR, f"{safe}_scaler.pkl")
        if os.path.exists(mpath) and os.path.exists(spath):
            with open(mpath, "rb") as f: self.models[equipment]  = pickle.load(f)
            with open(spath, "rb") as f: self.scalers[equipment] = pickle.load(f)
        else:
            self._train(equipment)

    def _train(self, equipment: str):
        params = list(THRESHOLDS[equipment].keys())
        n      = 1200
        data   = {}
        for p in params:
            lo, hi = THRESHOLDS[equipment][p]
            mid, std = (lo + hi) / 2, (hi - lo) / 7
            data[p] = np.random.normal(mid, std, n).clip(lo, hi)
        df     = pd.DataFrame(data)
        scaler = StandardScaler()
        X      = scaler.fit_transform(df)
        model  = IsolationForest(n_estimators=150, contamination=0.04, random_state=42)
        model.fit(X)
        self.models[equipment]  = model
        self.scalers[equipment] = scaler
        safe = equipment.replace(" ", "_")
        with open(os.path.join(MODEL_DIR, f"{safe}_model.pkl"),  "wb") as f: pickle.dump(model,  f)
        with open(os.path.join(MODEL_DIR, f"{safe}_scaler.pkl"), "wb") as f: pickle.dump(scaler, f)
