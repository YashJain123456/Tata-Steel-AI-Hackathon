from datetime import datetime
from collections import deque
import numpy as np

DEGRADATION_RATES: dict[str, dict[str, float]] = {
    "Rolling Mill":      {"temperature_c": 0.0015, "vibration_mms": 0.006, "pressure_bar": 0.001, "motor_current_a": 0.002, "roll_speed_rpm": 0.0008},
    "Blast Furnace":     {"hot_blast_temp_c": 0.0006, "top_pressure_bar": 0.002, "burden_descent_mm_min": 0.003},
    "Continuous Caster": {"tundish_temp_c": 0.001, "casting_speed_mpm": 0.004, "vibration_mms": 0.005},
    "Hydraulic System":  {"system_pressure_bar": 0.003, "oil_temperature_c": 0.002, "oil_level_pct": 0.012},
    "Ladle Furnace":     {"steel_temp_c": 0.0008, "arc_current_ka": 0.0015, "power_mw": 0.002},
    "Compressor":        {"vibration_mms": 0.007, "discharge_temp_c": 0.003, "discharge_pressure_bar": 0.002},
}

BASE_RUL: dict[str, float] = {
    "Rolling Mill":      2160,
    "Blast Furnace":     8760,
    "Continuous Caster": 1440,
    "Hydraulic System":  4320,
    "Ladle Furnace":     720,
    "Compressor":        4320,
}


class RULPredictor:
    def __init__(self, history_size: int = 50):
        self.history:      dict[str, deque] = {}
        self.history_size: int = history_size

    def update(self, equipment: str, readings: dict):
        if equipment not in self.history:
            self.history[equipment] = deque(maxlen=self.history_size)
        self.history[equipment].append({"ts": datetime.now(), **readings})

    def predict(self, equipment: str, readings: dict, thresholds: dict) -> dict:
        self.update(equipment, readings)
        base_rul = BASE_RUL.get(equipment, 1000.0)
        rates    = DEGRADATION_RATES.get(equipment, {})

        deductions: list[tuple[str, float]] = []
        for param, value in readings.items():
            if param not in thresholds or param not in rates:
                continue
            lo, hi  = thresholds[param]
            mid     = (lo + hi) / 2
            span    = hi - lo
            stress  = (value - mid) / (span / 2) if value > mid else (mid - value) / (span / 2)
            stress  = max(0.0, min(stress, 2.0))
            trend   = self._trend_factor(equipment, param)
            eff_rate = rates[param] * (1 + stress) * trend
            rul_est  = base_rul * (1 - stress * eff_rate * 10)
            deductions.append((param, rul_est))

        if not deductions:
            rul_hours, limiting = base_rul, "N/A"
        else:
            worst     = min(deductions, key=lambda x: x[1])
            rul_hours = max(0.0, worst[1])
            limiting  = worst[0]

        health_pct = min(100, max(5, int((rul_hours / base_rul) * 100)))

        if rul_hours < 24:   status = "CRITICAL"
        elif rul_hours < 96: status = "WARNING"
        elif rul_hours < 336:status = "CAUTION"
        else:                status = "HEALTHY"

        hist_len   = len(self.history.get(equipment, []))
        confidence = "HIGH" if hist_len >= 20 else ("MEDIUM" if hist_len >= 5 else "LOW")

        return {
            "rul_hours":          round(rul_hours, 1),
            "rul_days":           round(rul_hours / 24, 1),
            "health_pct":         health_pct,
            "status":             status,
            "limiting_parameter": limiting,
            "confidence":         confidence,
        }

    def _trend_factor(self, equipment: str, param: str) -> float:
        hist = self.history.get(equipment)
        if not hist or len(hist) < 4:
            return 1.0
        recent = list(hist)[-5:]
        vals   = [r.get(param) for r in recent if r.get(param) is not None]
        if len(vals) < 2:
            return 1.0
        slope = np.polyfit(range(len(vals)), vals, 1)[0]
        return max(0.5, 1.0 + abs(slope) * 0.01)
