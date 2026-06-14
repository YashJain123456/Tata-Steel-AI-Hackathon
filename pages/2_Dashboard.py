import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
from datetime import datetime
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from backend.anomaly_detector  import AnomalyDetector
from backend.rul_predictor     import RULPredictor
from backend.risk_scorer       import RiskScorer
from backend.llm_engine        import MaintenanceLLM
from backend.rag_pipeline      import RAGPipeline
from backend.feedback_store    import FeedbackStore
from utils.sensor_simulator    import current_readings, generate_timeseries, health_score

st.set_page_config(page_title="Dashboard — SteelGuard AI", page_icon="📊", layout="wide")

# ── Global CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Compact sidebar nav links */
section[data-testid="stSidebarNav"] a {
    padding: 3px 12px !important; font-size: 13px !important; line-height: 1.5 !important;
}
section[data-testid="stSidebarNav"] svg { width: 15px !important; height: 15px !important; }
section[data-testid="stSidebar"] > div:first-child { padding-top: 0.4rem !important; }
section[data-testid="stSidebar"] hr { margin: 0.3rem 0 !important; }
section[data-testid="stSidebar"] .stCheckbox { padding: 1px 0 !important; margin-bottom: 0 !important; }
section[data-testid="stSidebar"] .stSelectbox { margin-bottom: 2px !important; }
section[data-testid="stSidebar"] .stButton button { padding: 4px 12px !important; font-size: 13px !important; }

/* Ensure content clears Streamlit's fixed top bar */
.block-container { padding-top: 3.5rem !important; }

/* Section header style */
.section-header {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #8898aa;
    margin: 0 0 10px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #2d3748;
}

/* KPI card */
.kpi-card {
    background: linear-gradient(135deg, #1a2035 0%, #1e2a45 100%);
    border: 1px solid #2d3748;
    border-radius: 12px;
    padding: 16px 20px;
    text-align: center;
    margin-bottom: 8px;
}
.kpi-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #8898aa;
    margin-bottom: 4px;
}
.kpi-value {
    font-size: 26px;
    font-weight: 800;
    line-height: 1.1;
}
.kpi-sub {
    font-size: 11px;
    color: #8898aa;
    margin-top: 2px;
}

/* Alert banner */
.alert-critical {
    background: linear-gradient(90deg, #7f1d1d 0%, #1a0505 100%);
    border-left: 4px solid #ef4444;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 4px 0;
    font-size: 13px;
}
.alert-high {
    background: linear-gradient(90deg, #78350f 0%, #1a0d00 100%);
    border-left: 4px solid #f97316;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 4px 0;
    font-size: 13px;
}
.alert-ok {
    background: linear-gradient(90deg, #14532d 0%, #022c22 100%);
    border-left: 4px solid #22c55e;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 4px 0;
    font-size: 13px;
}

/* Sensor row */
.sensor-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    border-radius: 8px;
    margin-bottom: 5px;
    background: #1a2035;
    border: 1px solid #2d3748;
}
.sensor-name { font-size: 12px; color: #94a3b8; font-weight: 500; }
.sensor-val  { font-size: 15px; font-weight: 700; }
.sensor-range{ font-size: 10px; color: #64748b; }

/* Tab styling */
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] {
    background: #1a2035;
    border-radius: 8px 8px 0 0;
    border: 1px solid #2d3748;
    padding: 6px 18px;
    font-size: 13px;
}

/* Equipment badge */
.eq-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────────────────────────
if "role"        not in st.session_state: st.session_state.role = "Engineer"
if "ai_analysis" not in st.session_state: st.session_state.ai_analysis = ""

# ── Cached resources ─────────────────────────────────────────────────────────
@st.cache_resource
def get_detector(): return AnomalyDetector()
@st.cache_resource
def get_rul():      return RULPredictor()
@st.cache_resource
def get_scorer():   return RiskScorer()
@st.cache_resource
def get_llm():      return MaintenanceLLM()
@st.cache_resource
def get_rag():      return RAGPipeline()
@st.cache_resource
def get_store():    return FeedbackStore()

detector = get_detector()
rul      = get_rul()
scorer   = get_scorer()
llm      = get_llm()
rag      = get_rag()
store    = get_store()

EQUIPMENT_LIST = [
    "Rolling Mill", "Blast Furnace", "Continuous Caster",
    "Hydraulic System", "Ladle Furnace", "Compressor",
]
RISK_COLORS = {
    "CRITICAL": "#ef4444",
    "HIGH":     "#f97316",
    "MEDIUM":   "#eab308",
    "LOW":      "#3b82f6",
    "NORMAL":   "#22c55e",
}
RISK_BG = {
    "CRITICAL": "#450a0a",
    "HIGH":     "#431407",
    "MEDIUM":   "#422006",
    "LOW":      "#172554",
    "NORMAL":   "#052e16",
}

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Controls")
    st.divider()
    st.session_state.role = st.selectbox(
        "👤 Role", ["Engineer", "Supervisor", "Admin"],
        index=["Engineer", "Supervisor", "Admin"].index(st.session_state.role),
    )
    selected_eq    = st.selectbox("🏭 Equipment", EQUIPMENT_LIST)
    auto_refresh   = st.checkbox("🔄 Auto-refresh (15 s)", value=False)
    inject_anomaly = st.checkbox("⚠️ Simulate Fault (Demo)", value=False)
    st.divider()
    col_r, col_a = st.columns(2)
    with col_r:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.ai_analysis = ""
            st.rerun()
    with col_a:
        if st.button("🤖 AI Analyse", use_container_width=True):
            with st.spinner("Running AI analysis..."):
                rag_ctx = rag.query(f"{selected_eq} maintenance fault diagnosis", n_results=4)
                # will be rendered below after data is computed

    st.divider()
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    st.caption(f"Role: **{st.session_state.role}**")

# ── Compute data ─────────────────────────────────────────────────────────────
readings   = current_readings(selected_eq, anomaly_mode=inject_anomaly)
result     = detector.detect(selected_eq, readings)
thresholds = detector.get_thresholds(selected_eq)
rul_result = rul.predict(selected_eq, readings, thresholds)
risk       = scorer.calculate(selected_eq, result, rul_result)
h_score    = health_score(selected_eq, readings)

rc  = RISK_COLORS.get(risk.risk_level, "#22c55e")
rbg = RISK_BG.get(risk.risk_level, "#052e16")

# ── Page header ──────────────────────────────────────────────────────────────
st.markdown(
    f"""<div style='display:flex;align-items:center;justify-content:space-between;
        flex-wrap:nowrap;gap:12px;margin-bottom:4px'>
      <div style='min-width:0'>
        <div style='font-size:22px;font-weight:800;color:#e2e8f0;white-space:nowrap'>
          📊 Equipment Dashboard
        </div>
        <div style='color:#94a3b8;font-size:13px;margin-top:2px'>
          Integrated Steel Plant &nbsp;›&nbsp;
          <b style='color:#e2e8f0'>{selected_eq}</b>
        </div>
      </div>
      <div style='flex-shrink:0'>
        <span style='background:{rbg};color:{rc};border:1px solid {rc};
          border-radius:20px;padding:6px 18px;font-size:13px;font-weight:700;
          letter-spacing:0.5px;white-space:nowrap'>
          ● &nbsp;{risk.risk_level}
        </span>
      </div>
    </div>""",
    unsafe_allow_html=True,
)

st.markdown("---")

# ── ROW 1: KPI Strip ─────────────────────────────────────────────────────────
rul_status_colors = {"CRITICAL":"#ef4444","WARNING":"#f97316","CAUTION":"#eab308","HEALTHY":"#22c55e"}
rsc = rul_status_colors.get(rul_result["status"], "#22c55e")

k1, k2, k3, k4, k5 = st.columns(5)
def kpi(col, label, value, sub="", color="#e2e8f0"):
    col.markdown(
        f"""<div class='kpi-card'>
        <div class='kpi-label'>{label}</div>
        <div class='kpi-value' style='color:{color}'>{value}</div>
        <div class='kpi-sub'>{sub}</div>
        </div>""",
        unsafe_allow_html=True,
    )

kpi(k1, "Equipment Health",  f"{h_score:.0f}%",                    "Overall condition",      rc)
kpi(k2, "Risk Score",        f"{risk.total_score:.1f} / 10",       risk.urgency[:25] + "…" if len(risk.urgency) > 25 else risk.urgency, rc)
kpi(k3, "Remaining Life",    f"{rul_result['rul_hours']:.0f} h",   f"{rul_result['rul_days']:.1f} days", rsc)
kpi(k4, "RUL Status",        rul_result["status"],                 f"Confidence: {rul_result['confidence']}", rsc)
kpi(k5, "Active Alerts",     str(len(result["alerts"])),           f"Anomaly score: {result['anomaly_score']:.2f}",
    "#ef4444" if result["alerts"] else "#22c55e")

st.markdown("<br>", unsafe_allow_html=True)

# ── ROW 2: Health Gauge + Sensors + Risk Panel ───────────────────────────────
gauge_col, sensor_col, risk_col = st.columns([1.2, 1.6, 1.2])

with gauge_col:
    st.markdown("<div class='section-header'>Health Gauge</div>", unsafe_allow_html=True)
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=h_score,
        delta={"reference": 75, "suffix": "%", "increasing": {"color": "#22c55e"}, "decreasing": {"color": "#ef4444"}},
        number={"suffix": "%", "font": {"size": 38, "color": rc}},
        title={"text": "Health Index", "font": {"size": 13, "color": "#8898aa"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#4a5568",
                     "tickfont": {"color": "#8898aa", "size": 10}},
            "bar":  {"color": rc, "thickness": 0.25},
            "bgcolor": "#1a2035",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  30], "color": "#2d1515"},
                {"range": [30, 60], "color": "#2d2215"},
                {"range": [60, 100],"color": "#152d1f"},
            ],
            "threshold": {
                "line":  {"color": "#ffffff", "width": 2},
                "thickness": 0.75,
                "value": h_score,
            },
        },
    ))
    fig_gauge.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#e2e8f0",
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

    # Limiting parameter badge
    lp = rul_result["limiting_parameter"]
    st.markdown(
        f"<div style='text-align:center;font-size:11px;color:#8898aa;margin-top:-10px'>"
        f"Limiting: <b style='color:{rsc}'>{lp}</b></div>",
        unsafe_allow_html=True,
    )

with sensor_col:
    st.markdown("<div class='section-header'>Live Sensor Readings</div>", unsafe_allow_html=True)
    for param, val in readings.items():
        lo, hi = thresholds.get(param, (None, None))
        if lo is not None:
            pct = min(max((val - lo) / (hi - lo), 0), 1)
            if val < lo or val > hi:
                dot, bar_color = "🔴", "#ef4444"
            elif val < lo + 0.12*(hi-lo) or val > hi - 0.12*(hi-lo):
                dot, bar_color = "🟡", "#eab308"
            else:
                dot, bar_color = "🟢", "#22c55e"
            range_txt = f"{lo} – {hi}"
        else:
            pct, bar_color, dot, range_txt = 0.5, "#3b82f6", "⚪", "N/A"

        param_label = param.replace("_", " ").title()
        st.markdown(
            f"""<div class='sensor-row'>
            <div>
              <div class='sensor-name'>{dot} &nbsp;{param_label}</div>
              <div class='sensor-range'>Normal: {range_txt}</div>
            </div>
            <div style='text-align:right'>
              <div class='sensor-val' style='color:{bar_color}'>{val:.2f}</div>
            </div>
            </div>""",
            unsafe_allow_html=True,
        )
        # mini progress bar showing position within range
        st.progress(float(pct))

with risk_col:
    st.markdown("<div class='section-header'>Risk Assessment</div>", unsafe_allow_html=True)

    def risk_row(label, value, color="#e2e8f0"):
        st.markdown(
            f"""<div style='display:flex;justify-content:space-between;align-items:center;
            padding:9px 12px;background:#1a2035;border:1px solid #2d3748;
            border-radius:8px;margin-bottom:5px'>
            <span style='font-size:11px;color:#8898aa;font-weight:600;text-transform:uppercase;letter-spacing:0.5px'>{label}</span>
            <span style='font-size:13px;font-weight:700;color:{color}'>{value}</span>
            </div>""",
            unsafe_allow_html=True,
        )

    risk_row("Risk Level",       risk.risk_level,                     rc)
    risk_row("Total Score",      f"{risk.total_score:.2f} / 10",      rc)
    risk_row("Process Priority", f"{risk.process_criticality} / 10",  "#e2e8f0")
    risk_row("Anomaly Severity", f"{risk.anomaly_severity:.1f} / 10", "#e2e8f0")
    risk_row("Spare Parts Risk", f"{risk.spare_score:.1f} / 10",      "#e2e8f0")
    risk_row("Action Window",    risk.action_window[:30],              "#94a3b8")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='background:{rbg};border:1px solid {rc};border-radius:10px;"
        f"padding:12px;text-align:center'>"
        f"<div style='font-size:11px;color:{rc};font-weight:700;letter-spacing:1px;text-transform:uppercase'>Urgency</div>"
        f"<div style='font-size:13px;color:#e2e8f0;font-weight:600;margin-top:4px'>{risk.urgency}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── ROW 3: Alert Banner ──────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Active Alerts</div>", unsafe_allow_html=True)

if result["alerts"]:
    for a in result["alerts"]:
        css_class = "alert-critical" if a["severity"] == "CRITICAL" else "alert-high"
        icon = "🚨" if a["severity"] == "CRITICAL" else "⚠️"
        st.markdown(
            f"<div class='{css_class}'>{icon} &nbsp;<b>{a['severity']}</b> &nbsp;|&nbsp; "
            f"{a['parameter'].replace('_',' ').title()} = <b>{a['value']}</b> "
            f"(Normal: {a['range']})</div>",
            unsafe_allow_html=True,
        )
    if risk.risk_level in ("CRITICAL", "HIGH"):
        msg = "; ".join(a["message"] for a in result["alerts"])
        store.save_alert(selected_eq, risk.risk_level, msg, readings)
else:
    st.markdown(
        "<div class='alert-ok'>✅ &nbsp;<b>All Clear</b> &nbsp;|&nbsp; "
        "All sensor parameters within normal operating range.</div>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── ROW 4: Trend Charts ──────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Historical Trend Analysis</div>", unsafe_allow_html=True)

ts_df           = generate_timeseries(selected_eq, n_points=60, anomaly_fraction=0.08 if not inject_anomaly else 0.30)
params_available = [c for c in ts_df.columns if c not in ("timestamp", "is_anomaly")]
selected_params  = st.multiselect(
    "Select parameters to chart",
    params_available,
    default=params_available[:min(2, len(params_available))],
)

if selected_params:
    chart_cols = st.columns(min(2, len(selected_params)))
    for i, param in enumerate(selected_params):
        with chart_cols[i % 2]:
            lo, hi   = thresholds.get(param, (None, None))
            label    = param.replace("_", " ").title()
            fig = go.Figure()

            # Normal line
            fig.add_trace(go.Scatter(
                x=ts_df["timestamp"], y=ts_df[param],
                mode="lines",
                name=label,
                line=dict(color="#3b82f6", width=2),
                fill="tozeroy",
                fillcolor="rgba(59,130,246,0.05)",
            ))

            # Anomaly markers
            adf = ts_df[ts_df["is_anomaly"] == True]
            if not adf.empty:
                fig.add_trace(go.Scatter(
                    x=adf["timestamp"], y=adf[param],
                    mode="markers",
                    name="Anomaly",
                    marker=dict(color="#ef4444", size=9, symbol="x-thin-open", line=dict(width=2)),
                ))

            # Threshold lines
            if lo is not None:
                fig.add_hline(y=lo, line_dash="dot", line_color="#f97316",
                              annotation_text="Min", annotation_font_color="#f97316",
                              annotation_font_size=10)
                fig.add_hline(y=hi, line_dash="dot", line_color="#ef4444",
                              annotation_text="Max", annotation_font_color="#ef4444",
                              annotation_font_size=10)

            fig.update_layout(
                title=dict(text=label, font=dict(size=13, color="#e2e8f0")),
                height=240,
                margin=dict(l=10, r=10, t=40, b=30),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#0f172a",
                font=dict(color="#94a3b8", size=10),
                legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
                xaxis=dict(gridcolor="#1e293b", zeroline=False),
                yaxis=dict(gridcolor="#1e293b", zeroline=False),
                showlegend=True,
            )
            st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── ROW 5: Spare Parts ───────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Spare Parts Inventory</div>", unsafe_allow_html=True)

parts = RiskScorer.get_spare_parts(selected_eq)
if parts:
    AVAIL_COLOR = {
        "In Stock":   ("#22c55e", "#052e16"),
        "Low Stock":  ("#eab308", "#422006"),
        "Out of Stock":("#ef4444", "#450a0a"),
    }
    CRIT_COLOR = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308"}

    header_html = """
    <div style='display:grid;grid-template-columns:2fr 1.5fr 1fr 1fr;
    padding:8px 14px;background:#0f172a;border-radius:8px 8px 0 0;
    border:1px solid #2d3748;border-bottom:0;margin-bottom:0'>
    <span style='font-size:11px;font-weight:700;color:#8898aa;text-transform:uppercase;letter-spacing:1px'>Part Name</span>
    <span style='font-size:11px;font-weight:700;color:#8898aa;text-transform:uppercase;letter-spacing:1px'>Availability</span>
    <span style='font-size:11px;font-weight:700;color:#8898aa;text-transform:uppercase;letter-spacing:1px'>Lead Time</span>
    <span style='font-size:11px;font-weight:700;color:#8898aa;text-transform:uppercase;letter-spacing:1px'>Criticality</span>
    </div>"""
    st.markdown(header_html, unsafe_allow_html=True)

    for part_name, meta in parts.items():
        avail = meta["avail"]
        lead  = meta["lead_days"]
        crit  = meta["criticality"]

        # pick color based on availability keyword
        avail_key = next((k for k in AVAIL_COLOR if k in avail), "In Stock")
        atxt, abg = AVAIL_COLOR[avail_key]
        ctxt = CRIT_COLOR.get(crit, "#94a3b8")
        lead_txt  = f"{lead} days" if lead > 0 else "In stock"
        lead_color= "#ef4444" if lead > 30 else ("#eab308" if lead > 7 else "#22c55e")

        st.markdown(
            f"""<div style='display:grid;grid-template-columns:2fr 1.5fr 1fr 1fr;
            padding:9px 14px;background:#1a2035;border:1px solid #2d3748;
            border-top:0;align-items:center'>
            <span style='font-size:13px;color:#e2e8f0;font-weight:500'>{part_name}</span>
            <span style='font-size:12px'>
              <span style='background:{abg};color:{atxt};padding:2px 10px;
              border-radius:20px;font-size:11px;font-weight:600'>{avail}</span>
            </span>
            <span style='font-size:13px;color:{lead_color};font-weight:600'>{lead_txt}</span>
            <span style='font-size:13px;color:{ctxt};font-weight:600'>{crit}</span>
            </div>""",
            unsafe_allow_html=True,
        )

st.markdown("---")

# ── ROW 6: AI Analysis Panel ─────────────────────────────────────────────────
st.markdown("<div class='section-header'>AI Diagnostic Analysis</div>", unsafe_allow_html=True)

ai_col1, ai_col2 = st.columns([1, 3])
with ai_col1:
    if st.button("🤖 Generate AI Analysis", type="primary", use_container_width=True):
        with st.spinner("Consulting AI..."):
            rag_ctx = rag.query(f"{selected_eq} maintenance fault diagnosis", n_results=4)
            st.session_state.ai_analysis = llm.analyze_equipment(
                selected_eq, readings, result["alerts"], rul_result, rag_ctx
            )


with ai_col2:
    if st.session_state.ai_analysis:
        st.markdown(
            f"<div style='background:#1a2035;border:1px solid #2d3748;border-radius:10px;"
            f"padding:20px;font-size:14px;line-height:1.7'>{st.session_state.ai_analysis}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='background:#1a2035;border:1px dashed #2d3748;border-radius:10px;"
            "padding:30px;text-align:center;color:#64748b'>"
            "Click <b style='color:#3b82f6'>Generate AI Analysis</b> to get a full diagnostic report.</div>",
            unsafe_allow_html=True,
        )



# ── Auto-refresh ──────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(15)
    st.rerun()
