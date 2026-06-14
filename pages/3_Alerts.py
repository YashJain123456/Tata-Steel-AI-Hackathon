import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
import streamlit as st

from backend.anomaly_detector import AnomalyDetector
from backend.rul_predictor    import RULPredictor
from backend.risk_scorer      import RiskScorer
from backend.feedback_store   import FeedbackStore
from utils.sensor_simulator   import all_equipment_snapshot, health_score

st.set_page_config(page_title="Alerts — SteelGuard", page_icon="🚨", layout="wide")

st.markdown("""
<style>
/* Compact sidebar */
section[data-testid="stSidebarNav"] a {
    padding: 3px 12px !important; font-size: 13px !important; line-height: 1.5 !important;
}
section[data-testid="stSidebarNav"] svg { width: 15px !important; height: 15px !important; }
section[data-testid="stSidebar"] > div:first-child { padding-top: 0.4rem !important; }
section[data-testid="stSidebar"] hr { margin: 0.3rem 0 !important; }
section[data-testid="stSidebar"] .stSelectbox  { margin-bottom: 2px !important; }
section[data-testid="stSidebar"] .stButton button { padding: 4px 12px !important; font-size: 13px !important; }
.block-container { padding-top: 3.5rem !important; }

/* Summary KPI cards */
.sum-card {
    background: linear-gradient(135deg, #1a2035 0%, #1e2a45 100%);
    border: 1px solid #2d3748;
    border-radius: 12px;
    padding: 14px 18px;
    text-align: center;
}
.sum-label { font-size: 10px; font-weight: 700; letter-spacing: 1.2px;
             text-transform: uppercase; color: #8898aa; margin-bottom: 4px; }
.sum-value { font-size: 28px; font-weight: 800; line-height: 1.1; }
.sum-sub   { font-size: 11px; color: #8898aa; margin-top: 2px; }

/* Alert cards */
.alert-card {
    border-radius: 12px;
    border: 1px solid;
    margin-bottom: 4px;
    overflow: hidden;
}
.alert-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 18px;
    flex-wrap: wrap;
    gap: 8px;
}
.alert-card-title { font-size: 15px; font-weight: 700; color: #e2e8f0; }
.alert-card-sub   { font-size: 12px; color: #94a3b8; margin-top: 1px; }

.risk-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    white-space: nowrap;
}

/* Metric mini-grid inside card */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-bottom: 10px;
}
.metric-cell {
    background: #0f172a;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 9px 12px;
}
.metric-cell-label { font-size: 10px; color: #64748b; font-weight: 600;
                     text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 3px; }
.metric-cell-value { font-size: 17px; font-weight: 800; }

/* Sensor alert pill */
.sensor-pill {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 12px;
    border-radius: 8px;
    margin-bottom: 5px;
    font-size: 12px;
    border: 1px solid;
}

/* Section header */
.section-hdr {
    font-size: 11px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: #8898aa;
    margin: 18px 0 10px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #2d3748;
}
</style>
""", unsafe_allow_html=True)

if "role" not in st.session_state: st.session_state.role = "Engineer"

# ── Cached back-end objects ───────────────────────────────────────────────────
@st.cache_resource
def get_detector(): return AnomalyDetector()
@st.cache_resource
def get_rul():      return RULPredictor()
@st.cache_resource
def get_scorer():   return RiskScorer()
@st.cache_resource
def get_store():    return FeedbackStore()

detector = get_detector()
rul      = get_rul()
scorer   = get_scorer()
store    = get_store()

RISK_COLORS = {
    "CRITICAL": "#ef4444", "HIGH": "#f97316",
    "MEDIUM":   "#eab308", "LOW":  "#3b82f6", "NORMAL": "#22c55e",
}
RISK_BG = {
    "CRITICAL": "#450a0a", "HIGH":   "#431407",
    "MEDIUM":   "#422006", "LOW":    "#172554", "NORMAL": "#052e16",
}
RISK_BORDER = {
    "CRITICAL": "#7f1d1d", "HIGH":   "#7c2d12",
    "MEDIUM":   "#713f12", "LOW":    "#1e3a8a", "NORMAL": "#14532d",
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚨 Alert Controls")
    st.divider()
    st.session_state.role = st.selectbox(
        "👤 Role", ["Engineer", "Supervisor", "Admin"],
        index=["Engineer", "Supervisor", "Admin"].index(st.session_state.role),
    )
    severity_filter = st.multiselect(
        "🔍 Filter Severity",
        ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NORMAL"],
        default=["CRITICAL", "HIGH", "MEDIUM"],
    )
    st.divider()
    if st.button("🔄 Refresh Scan", use_container_width=True):
        st.rerun()
    st.caption(f"Last scan: {datetime.now().strftime('%H:%M:%S')}")

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    "<div style='font-size:22px;font-weight:800;color:#e2e8f0;margin-bottom:2px'>"
    "🚨 Equipment Alerts &amp; Risk Monitor"
    "</div>"
    "<div style='font-size:13px;color:#94a3b8;margin-bottom:16px'>"
    "Real-time anomaly detection across all plant equipment"
    "</div>",
    unsafe_allow_html=True,
)

# ── Scan all equipment ────────────────────────────────────────────────────────
with st.spinner("Scanning all equipment..."):
    snapshots  = all_equipment_snapshot()
    alert_data = []
    for eq, readings in snapshots.items():
        result     = detector.detect(eq, readings)
        thresholds = detector.get_thresholds(eq)
        rul_result = rul.predict(eq, readings, thresholds)
        risk       = scorer.calculate(eq, result, rul_result)
        h          = health_score(eq, readings)
        alert_data.append({
            "equipment": eq, "readings": readings, "result": result,
            "rul_result": rul_result, "risk": risk, "health": h,
        })

alert_data.sort(key=lambda x: x["risk"].total_score, reverse=True)
filtered = [a for a in alert_data if a["risk"].risk_level in severity_filter]

# ── Summary KPI strip ─────────────────────────────────────────────────────────
total     = len(alert_data)
n_crit    = sum(1 for a in alert_data if a["risk"].risk_level == "CRITICAL")
n_high    = sum(1 for a in alert_data if a["risk"].risk_level == "HIGH")
n_med     = sum(1 for a in alert_data if a["risk"].risk_level == "MEDIUM")
n_ok      = sum(1 for a in alert_data if a["risk"].risk_level in ("LOW", "NORMAL"))
avg_score = sum(a["risk"].total_score for a in alert_data) / max(total, 1)

ks = st.columns(5)
def sum_kpi(col, label, value, sub, color="#e2e8f0"):
    col.markdown(
        f"<div class='sum-card'>"
        f"<div class='sum-label'>{label}</div>"
        f"<div class='sum-value' style='color:{color}'>{value}</div>"
        f"<div class='sum-sub'>{sub}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

sum_kpi(ks[0], "Equipment",    total,            "monitored",        "#94a3b8")
sum_kpi(ks[1], "Critical",     n_crit,           "immediate action", "#ef4444")
sum_kpi(ks[2], "High Risk",    n_high,           "attention needed", "#f97316")
sum_kpi(ks[3], "Med / Low",    f"{n_med}/{n_ok}","medium / healthy", "#eab308")
sum_kpi(ks[4], "Avg Risk",     f"{avg_score:.1f}","out of 10",
        "#ef4444" if avg_score >= 6 else "#f97316" if avg_score >= 4 else "#22c55e")

st.markdown("<br>", unsafe_allow_html=True)

# ── Equipment alert cards ─────────────────────────────────────────────────────
st.markdown(
    f"<div class='section-hdr'>LIVE EQUIPMENT STATUS — {len(filtered)} matching filter</div>",
    unsafe_allow_html=True,
)

if not filtered:
    st.markdown(
        "<div style='background:#052e16;border:1px solid #166534;border-radius:12px;"
        "padding:20px;text-align:center;color:#86efac;font-size:15px;font-weight:600'>"
        "✅ &nbsp; All monitored equipment within acceptable risk thresholds</div>",
        unsafe_allow_html=True,
    )

for a in filtered:
    eq     = a["equipment"]
    risk   = a["risk"]
    rul_r  = a["rul_result"]
    result = a["result"]
    rc     = RISK_COLORS.get(risk.risk_level, "#22c55e")
    rbg    = RISK_BG.get(risk.risk_level, "#052e16")
    rbrd   = RISK_BORDER.get(risk.risk_level, "#14532d")

    # Coloured card header
    st.markdown(
        f"<div class='alert-card' style='background:{rbg};border-color:{rbrd}'>"
        f"<div class='alert-card-header' style='border-bottom:1px solid {rbrd}'>"
        f"<div>"
        f"<div class='alert-card-title'>{eq}</div>"
        f"<div class='alert-card-sub'>Score: {risk.total_score:.1f}/10 &nbsp;·&nbsp; "
        f"Health: {a['health']:.0f}% &nbsp;·&nbsp; "
        f"RUL: {rul_r['rul_hours']:.0f} h ({rul_r['rul_days']:.1f} days)</div>"
        f"</div>"
        f"<span class='risk-badge' style='background:{rbg};color:{rc};border:1px solid {rc}'>"
        f"● &nbsp;{risk.risk_level}</span>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    with st.expander("▾ View Details", expanded=(risk.risk_level == "CRITICAL")):
        # Metric mini-grid
        st.markdown(
            f"<div class='metric-grid'>"
            f"<div class='metric-cell'><div class='metric-cell-label'>Risk Score</div>"
            f"<div class='metric-cell-value' style='color:{rc}'>{risk.total_score:.2f}/10</div></div>"
            f"<div class='metric-cell'><div class='metric-cell-label'>RUL Status</div>"
            f"<div class='metric-cell-value' style='color:{rc}'>{rul_r['status']}</div></div>"
            f"<div class='metric-cell'><div class='metric-cell-label'>Confidence</div>"
            f"<div class='metric-cell-value' style='color:#e2e8f0'>{rul_r['confidence']}</div></div>"
            f"<div class='metric-cell'><div class='metric-cell-label'>Urgency</div>"
            f"<div class='metric-cell-value' style='font-size:12px;color:{rc};margin-top:4px'>"
            f"{risk.urgency[:40]}{'…' if len(risk.urgency)>40 else ''}</div></div>"
            f"<div class='metric-cell'><div class='metric-cell-label'>Action Window</div>"
            f"<div class='metric-cell-value' style='font-size:12px;color:#e2e8f0;margin-top:4px'>"
            f"{risk.action_window[:30]}</div></div>"
            f"<div class='metric-cell'><div class='metric-cell-label'>Anomaly Score</div>"
            f"<div class='metric-cell-value' style='color:#e2e8f0'>{result['anomaly_score']:.2f}</div></div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Sensor alerts
        if result["alerts"]:
            st.markdown(
                "<div style='font-size:11px;font-weight:700;letter-spacing:1px;"
                "text-transform:uppercase;color:#8898aa;margin-bottom:6px'>"
                "Active Sensor Violations</div>",
                unsafe_allow_html=True,
            )
            for al in result["alerts"]:
                pill_bg  = "#450a0a" if al["severity"] == "CRITICAL" else "#431407"
                pill_brd = "#ef4444" if al["severity"] == "CRITICAL" else "#f97316"
                pill_col = "#ef4444" if al["severity"] == "CRITICAL" else "#f97316"
                icon     = "🚨" if al["severity"] == "CRITICAL" else "⚠️"
                st.markdown(
                    f"<div class='sensor-pill' style='background:{pill_bg};border-color:{pill_brd}'>"
                    f"<span style='font-size:16px'>{icon}</span>"
                    f"<span style='font-weight:700;color:{pill_col};font-size:12px'>{al['severity']}</span>"
                    f"<span style='color:#e2e8f0;flex:1'>{al['message']}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<div style='background:#052e16;border:1px solid #166534;border-radius:8px;"
                "padding:8px 14px;font-size:12px;color:#86efac'>"
                "✅ No sensor threshold violations</div>",
                unsafe_allow_html=True,
            )

        # Save button
        if risk.risk_level in ("CRITICAL", "HIGH"):
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
            if st.button("💾 Save to Alert Database", key=f"save_{eq}",
                         use_container_width=True):
                msg = "; ".join(al["message"] for al in result["alerts"]) or "High risk score detected"
                store.save_alert(eq, risk.risk_level, msg, a["readings"])
                st.success("✅ Alert saved to database.")

st.markdown("---")

# ── Alert History ─────────────────────────────────────────────────────────────
st.markdown("<div class='section-hdr'>ALERT DATABASE HISTORY</div>", unsafe_allow_html=True)

db_alerts = store.get_alerts()
if not db_alerts:
    st.markdown(
        "<div style='background:#1a2035;border:1px solid #2d3748;border-radius:10px;"
        "padding:20px;text-align:center;color:#64748b;font-size:13px'>"
        "📭 &nbsp; No alerts saved to database yet.</div>",
        unsafe_allow_html=True,
    )
else:
    open_cnt = sum(1 for al in db_alerts if not al.get("acknowledged"))
    ack_cnt  = len(db_alerts) - open_cnt
    h1, h2, h3 = st.columns(3)
    h1.markdown(
        f"<div class='sum-card'><div class='sum-label'>Total Saved</div>"
        f"<div class='sum-value' style='color:#94a3b8'>{len(db_alerts)}</div></div>",
        unsafe_allow_html=True,
    )
    h2.markdown(
        f"<div class='sum-card'><div class='sum-label'>Open</div>"
        f"<div class='sum-value' style='color:#ef4444'>{open_cnt}</div></div>",
        unsafe_allow_html=True,
    )
    h3.markdown(
        f"<div class='sum-card'><div class='sum-label'>Acknowledged</div>"
        f"<div class='sum-value' style='color:#22c55e'>{ack_cnt}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    for al in db_alerts[:30]:
        ack      = bool(al.get("acknowledged"))
        sev      = al.get("severity", "HIGH")
        rc_h     = RISK_COLORS.get(sev, "#94a3b8")
        rbg_h    = RISK_BG.get(sev, "#1a2035")
        s_bg     = "#052e16" if ack else "#450a0a"
        s_brd    = "#166534" if ack else "#7f1d1d"
        s_col    = "#86efac" if ack else "#fca5a5"
        s_lbl    = "✅ ACKNOWLEDGED" if ack else "🔴 OPEN"

        with st.expander(
            f"{'✅' if ack else '🔴'}  {al['equipment']}  ·  {sev}  ·  {al['timestamp'][:16]}"
        ):
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"margin-bottom:10px;flex-wrap:wrap;gap:8px'>"
                f"<div>"
                f"<div style='font-size:15px;font-weight:700;color:#e2e8f0'>{al['equipment']}</div>"
                f"<div style='font-size:11px;color:#64748b;margin-top:2px'>"
                f"{al['timestamp'][:19].replace('T',' ')}</div>"
                f"</div>"
                f"<div style='display:flex;gap:8px;align-items:center'>"
                f"<span style='background:{rbg_h};color:{rc_h};border:1px solid {rc_h};"
                f"border-radius:20px;padding:3px 12px;font-size:11px;font-weight:700'>{sev}</span>"
                f"<span style='background:{s_bg};color:{s_col};border:1px solid {s_brd};"
                f"border-radius:20px;padding:3px 12px;font-size:11px;font-weight:700'>{s_lbl}</span>"
                f"</div></div>"
                f"<div style='background:#0f172a;border:1px solid #2d3748;border-radius:8px;"
                f"padding:10px 14px;font-size:13px;color:#cbd5e1;margin-bottom:10px'>"
                f"{al['message']}</div>",
                unsafe_allow_html=True,
            )
            if not ack and st.session_state.role in ("Supervisor", "Admin"):
                if st.button("✅ Acknowledge Alert", key=f"ack_{al['id']}",
                             use_container_width=True):
                    store.acknowledge_alert(al["id"], st.session_state.role)
                    st.success("Alert acknowledged.")
                    st.rerun()
            elif ack:
                st.markdown(
                    "<div style='text-align:center;font-size:12px;color:#86efac;padding:4px'>"
                    "✅ This alert has been acknowledged and resolved.</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='text-align:center;font-size:12px;color:#94a3b8;padding:4px'>"
                    "⚠️ Supervisor or Admin role required to acknowledge.</div>",
                    unsafe_allow_html=True,
                )
