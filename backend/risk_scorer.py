from dataclasses import dataclass, asdict

CRITICALITY: dict[str, int] = {
    "Blast Furnace":     10,
    "Continuous Caster": 9,
    "Rolling Mill":      8,
    "Ladle Furnace":     8,
    "Hydraulic System":  7,
    "Compressor":        6,
}

SPARE_PARTS: dict[str, dict[str, dict]] = {
    "Rolling Mill": {
        "Work Roll":               {"avail": "Out of Stock",        "lead_days": 45, "criticality": "CRITICAL"},
        "Back-up Roll":            {"avail": "Out of Stock",        "lead_days": 60, "criticality": "CRITICAL"},
        "Drive Shaft":             {"avail": "Low Stock (2 units)", "lead_days": 7,  "criticality": "CRITICAL"},
        "Bearing SKF 22230 E/C3": {"avail": "In Stock",            "lead_days": 0,  "criticality": "HIGH"},
        "Gear Box Oil Seal":       {"avail": "In Stock",            "lead_days": 0,  "criticality": "MEDIUM"},
        "Mill Housing Liner":      {"avail": "Low Stock (1 unit)",  "lead_days": 30, "criticality": "HIGH"},
    },
    "Blast Furnace": {
        "Tuyere Assembly":        {"avail": "In Stock",            "lead_days": 0,  "criticality": "CRITICAL"},
        "Cooler Panel (copper)":  {"avail": "Low Stock (1 unit)", "lead_days": 30, "criticality": "CRITICAL"},
        "Tap Hole Clay Gun Tip":  {"avail": "In Stock",            "lead_days": 0,  "criticality": "HIGH"},
        "Blowpipe Assembly":      {"avail": "In Stock",            "lead_days": 0,  "criticality": "HIGH"},
        "Blast Valve Seat":       {"avail": "Out of Stock",        "lead_days": 21, "criticality": "HIGH"},
    },
    "Continuous Caster": {
        "Mold Copper Plate":         {"avail": "Low Stock (2 units)", "lead_days": 21, "criticality": "CRITICAL"},
        "Segment Roll":              {"avail": "Out of Stock",        "lead_days": 45, "criticality": "CRITICAL"},
        "Nozzle (SEN)":              {"avail": "In Stock",            "lead_days": 0,  "criticality": "HIGH"},
        "Strand Guide Roll Bearing": {"avail": "In Stock",            "lead_days": 0,  "criticality": "HIGH"},
        "Mold Oscillation Pin":      {"avail": "In Stock",            "lead_days": 0,  "criticality": "MEDIUM"},
    },
    "Hydraulic System": {
        "Hydraulic Pump HPR-130":  {"avail": "In Stock",            "lead_days": 0,  "criticality": "CRITICAL"},
        "Proportional Valve":      {"avail": "Low Stock (1 unit)", "lead_days": 21, "criticality": "HIGH"},
        "Cylinder Seal Kit":       {"avail": "In Stock",            "lead_days": 0,  "criticality": "MEDIUM"},
        "Pressure Relief Valve":   {"avail": "In Stock",            "lead_days": 0,  "criticality": "MEDIUM"},
        "Hydraulic Filter Element":{"avail": "In Stock",            "lead_days": 0,  "criticality": "MEDIUM"},
    },
    "Ladle Furnace": {
        "Electrode (graphite)":  {"avail": "Low Stock (3 units)", "lead_days": 14, "criticality": "CRITICAL"},
        "Electrode Holder":      {"avail": "In Stock",            "lead_days": 0,  "criticality": "HIGH"},
        "Electrode Arm Bushing": {"avail": "Out of Stock",        "lead_days": 30, "criticality": "HIGH"},
        "Argon Lance":           {"avail": "In Stock",            "lead_days": 0,  "criticality": "MEDIUM"},
        "Slide Gate Plate":      {"avail": "In Stock",            "lead_days": 0,  "criticality": "HIGH"},
    },
    "Compressor": {
        "Air Filter Element":   {"avail": "In Stock",            "lead_days": 0,  "criticality": "MEDIUM"},
        "Compressor Valve":     {"avail": "Low Stock (2 units)", "lead_days": 14, "criticality": "HIGH"},
        "Oil Separator Element":{"avail": "In Stock",            "lead_days": 0,  "criticality": "MEDIUM"},
        "Coupling Element":     {"avail": "In Stock",            "lead_days": 0,  "criticality": "HIGH"},
        "Unloader Valve":       {"avail": "Out of Stock",        "lead_days": 10, "criticality": "HIGH"},
    },
}


@dataclass
class RiskScore:
    total_score:          float
    risk_level:           str
    process_criticality:  int
    anomaly_severity:     float
    spare_score:          float
    lead_time_score:      float
    urgency:              str
    action_window:        str

    def to_dict(self) -> dict:
        return asdict(self)


class RiskScorer:
    def calculate(
        self,
        equipment:      str,
        anomaly_result: dict,
        rul_result:     dict,
        delay_hours:    float = 0.0,
    ) -> RiskScore:
        crit    = CRITICALITY.get(equipment, 5)
        sev_map = {"CRITICAL": 10, "HIGH": 7, "MEDIUM": 4, "LOW": 2, "NORMAL": 0}
        sev     = float(sev_map.get(anomaly_result.get("risk_level", "NORMAL"), 0))
        rul_h   = rul_result.get("rul_hours", 720)
        if rul_h < 24:  sev = min(10.0, sev + 3.0)
        elif rul_h < 72: sev = min(10.0, sev + 1.5)

        spare_score = self._spare_score(equipment)
        max_lead    = self._max_lead(equipment)
        lead_score  = min(10.0, max_lead / 6.0)
        delay_score = min(10.0, delay_hours / 2.0)

        total = (
            crit        * 0.30
            + sev       * 0.35
            + spare_score * 0.15
            + lead_score  * 0.10
            + delay_score * 0.10
        )

        if total >= 7.5:
            level, urgency, window = "CRITICAL", "IMMEDIATE — within 1 hour",   "Shutdown now, isolate equipment"
        elif total >= 5.5:
            level, urgency, window = "HIGH",     "URGENT — within 4 hours",     "Plan intervention today"
        elif total >= 3.5:
            level, urgency, window = "MEDIUM",   "SCHEDULE — within 48 hours",  "Schedule planned maintenance"
        elif total >= 1.5:
            level, urgency, window = "LOW",      "MONITOR — next weekly PM",    "Include in next PM cycle"
        else:
            level, urgency, window = "NORMAL",   "ROUTINE",                     "Continue normal monitoring"

        return RiskScore(
            total_score=round(total, 2), risk_level=level,
            process_criticality=crit, anomaly_severity=sev,
            spare_score=spare_score, lead_time_score=lead_score,
            urgency=urgency, action_window=window,
        )

    def _spare_score(self, equipment: str) -> float:
        parts = SPARE_PARTS.get(equipment, {})
        if not parts:
            return 3.0
        critical = [p for p in parts.values() if p["criticality"] == "CRITICAL"]
        if not critical:
            return 2.0
        out  = sum(1 for p in critical if "Out of Stock" in p["avail"])
        low  = sum(1 for p in critical if "Low Stock"    in p["avail"])
        return min(10.0, (out * 3.0 + low * 1.5) / len(critical))

    def _max_lead(self, equipment: str) -> int:
        parts = SPARE_PARTS.get(equipment, {})
        if not parts:
            return 0
        return max(p["lead_days"] for p in parts.values())

    @staticmethod
    def get_spare_parts(equipment: str) -> dict:
        return SPARE_PARTS.get(equipment, {})
