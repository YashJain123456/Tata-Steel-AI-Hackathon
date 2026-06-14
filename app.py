import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

st.set_page_config(
    page_title="Tata Steel | SteelGuard AI",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Compact sidebar CSS (applied globally via every page) ─────────────────────
st.markdown("""
<style>
/* Nav links — tighter padding & smaller font */
section[data-testid="stSidebarNav"] a {
    padding: 3px 12px !important;
    font-size: 13px !important;
    line-height: 1.5 !important;
}
section[data-testid="stSidebarNav"] svg {
    width: 15px !important; height: 15px !important;
}
/* Reduce sidebar top gap */
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 0.4rem !important;
}
/* Tighten vertical spacing between all sidebar widgets */
section[data-testid="stSidebar"] .block-container {
    padding: 0.5rem 0.75rem !important;
}
section[data-testid="stSidebar"] hr {
    margin: 0.3rem 0 !important;
}
section[data-testid="stSidebar"] .stCheckbox {
    padding: 1px 0 !important;
    margin-bottom: 0 !important;
}
section[data-testid="stSidebar"] .stSelectbox {
    margin-bottom: 2px !important;
}
section[data-testid="stSidebar"] .stButton button {
    padding: 4px 12px !important;
    font-size: 13px !important;
}
.block-container { padding-top: 3.5rem !important; }
.section-hdr {
    font-size: 11px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: #8898aa;
    margin: 18px 0 10px 0; padding-bottom: 6px;
    border-bottom: 1px solid #2d3748;
}
.kpi-home {
    background: linear-gradient(135deg, #1a2035 0%, #1e2a45 100%);
    border: 1px solid #2d3748; border-radius: 12px;
    padding: 14px 18px; text-align: center;
}
.kpi-home-lbl { font-size: 10px; font-weight: 700; letter-spacing: 1.2px;
                text-transform: uppercase; color: #8898aa; margin-bottom: 4px; }
.kpi-home-val { font-size: 28px; font-weight: 800; line-height: 1.1; }
.kpi-home-sub { font-size: 11px; color: #8898aa; margin-top: 2px; }
.nav-card {
    background: linear-gradient(135deg, #1a2035, #1e2a45);
    border: 1px solid #2d3748; border-radius: 12px;
    padding: 18px 14px; text-align: center; cursor: pointer;
    transition: border-color 0.2s;
}
.nav-card:hover { border-color: #3b82f6; }
.nav-icon { font-size: 26px; margin-bottom: 6px; }
.nav-label { font-size: 13px; font-weight: 700; color: #e2e8f0; }
.nav-sub { font-size: 11px; color: #64748b; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

if "role" not in st.session_state:
    st.session_state.role = "Engineer"
if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())
if "kb_ready" not in st.session_state:
    st.session_state.kb_ready = False

import base64
try:
    with open("Tata-Steel-logo.png", "rb") as img_file:
        tata_logo_b64 = base64.b64encode(img_file.read()).decode()
    tata_logo_src = f"data:image/png;base64,{tata_logo_b64}"
except Exception:
    tata_logo_src = ""

with st.sidebar:
    st.markdown(
        f"<div style='display:flex; align-items:center; gap:8px; margin-bottom:12px;'>"
        f"<img src='{tata_logo_src}' width='120'>"
        f"</div>"
        f"<div style='font-size:15px;font-weight:800;color:#e2e8f0;letter-spacing:0.3px'>🏭 SteelGuard AI</div>"
        f"<div style='font-size:10px;color:#64748b;margin-bottom:2px'>Intelligent Maintenance Wizard</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    st.session_state.role = st.selectbox(
        "👤 Role",
        ["Engineer", "Supervisor", "Admin"],
        index=["Engineer", "Supervisor", "Admin"].index(st.session_state.role),
    )

    from backend.rag_pipeline import RAGPipeline
    @st.cache_resource
    def get_rag():
        return RAGPipeline()

    rag = get_rag()
    stats = rag.get_stats()
    total_chunks = sum(stats.values())

    if total_chunks > 0:
        st.markdown(
            f"<div style='background:#052e16;border:1px solid #166534;border-radius:7px;"
            f"padding:5px 10px;font-size:12px;color:#22c55e;margin:3px 0'>"
            f"✅ KB Ready &nbsp;·&nbsp; {total_chunks} chunks</div>",
            unsafe_allow_html=True,
        )
        st.session_state.kb_ready = True
    else:
        st.markdown(
            "<div style='background:#422006;border:1px solid #f97316;border-radius:7px;"
            "padding:5px 10px;font-size:12px;color:#fb923c;margin:3px 0'>"
            "⚠️ Knowledge Base empty</div>",
            unsafe_allow_html=True,
        )
        if st.button("🔄 Init Knowledge Base", use_container_width=True):
            with st.spinner("Loading..."):
                from setup_kb import initialize_kb
                initialize_kb(rag)
            st.rerun()

    from backend.feedback_store import FeedbackStore
    @st.cache_resource
    def get_store():
        return FeedbackStore()

    store = get_store()
    unack = store.unack_count()
    fb    = store.get_feedback_summary()

    st.divider()

    if unack > 0:
        st.markdown(
            f"<div style='background:#450a0a;border:1px solid #ef4444;border-radius:7px;"
            f"padding:5px 10px;font-size:12px;color:#ef4444;margin-bottom:4px'>"
            f"🚨 {unack} unacknowledged alert{'s' if unack>1 else ''}</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div style='display:flex;gap:5px'>"
        f"<div style='flex:1;background:#1a2035;border:1px solid #2d3748;border-radius:8px;"
        f"padding:7px 6px;text-align:center'>"
        f"<div style='font-size:9px;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:0.5px'>Interactions</div>"
        f"<div style='font-size:17px;font-weight:800;color:#3b82f6'>{fb['total']}</div>"
        f"</div>"
        f"<div style='flex:1;background:#1a2035;border:1px solid #2d3748;border-radius:8px;"
        f"padding:7px 6px;text-align:center'>"
        f"<div style='font-size:9px;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:0.5px'>Satisfaction</div>"
        f"<div style='font-size:17px;font-weight:800;color:#22c55e'>{fb['satisfaction']}</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown(
    f"<div style='font-size:24px;font-weight:800;color:#e2e8f0;margin-bottom:2px'>"
    f"<img src='{tata_logo_src}' width='130' style='vertical-align:middle; margin-right:12px; padding-bottom:5px;'>"
    f"SteelGuard AI &mdash; Maintenance Wizard"
    f"</div>"
    f"<div style='font-size:13px;color:#94a3b8;margin-bottom:16px'>"
    f"Role: <b style='color:#e2e8f0'>{st.session_state.role}</b> &nbsp;·&nbsp; "
    f"Session: <code>{st.session_state.session_id[:8]}</code> &nbsp;·&nbsp; "
    f"Integrated Steel Plant"
    f"</div>",
    unsafe_allow_html=True,
)

from utils.sensor_simulator import current_readings, health_score, all_equipment_snapshot
from backend.anomaly_detector import AnomalyDetector

@st.cache_resource
def get_detector():
    return AnomalyDetector()

detector = get_detector()

snapshots = all_equipment_snapshot()
equipment_list = list(snapshots.keys())

health_data = []
for eq, readings in snapshots.items():
    result = detector.detect(eq, readings)
    h = health_score(eq, readings)
    health_data.append({
        "Equipment": eq,
        "Health (%)": h,
        "Risk": result["risk_level"],
        "Anomalies": len(result["alerts"]),
    })

df = pd.DataFrame(health_data)

col1, col2, col3, col4, col5 = st.columns(5)
critical_count = (df["Risk"] == "CRITICAL").sum()
high_count     = (df["Risk"] == "HIGH").sum()
normal_count   = (df["Risk"] == "NORMAL").sum()
avg_health     = df["Health (%)"].mean()

def home_kpi(col, label, value, sub, color="#e2e8f0"):
    col.markdown(
        f"<div class='kpi-home'>"
        f"<div class='kpi-home-lbl'>{label}</div>"
        f"<div class='kpi-home-val' style='color:{color}'>{value}</div>"
        f"<div class='kpi-home-sub'>{sub}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

home_kpi(col1, "Equipment",     len(equipment_list),        "monitored",          "#94a3b8")
home_kpi(col2, "Avg Health",    f"{avg_health:.0f}%",        "plant-wide",
         "#ef4444" if avg_health < 50 else "#f97316" if avg_health < 70 else "#22c55e")
home_kpi(col3, "Critical",      int(critical_count),        "immediate action",   "#ef4444")
home_kpi(col4, "High Risk",     int(high_count),            "attention needed",   "#f97316")
home_kpi(col5, "Normal",        int(normal_count),          "operating well",     "#22c55e")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<div class='section-hdr'>EQUIPMENT HEALTH OVERVIEW</div>", unsafe_allow_html=True)

RISK_COLORS = {
    "CRITICAL": "#ef4444", "HIGH": "#f97316",
    "MEDIUM":   "#eab308", "LOW":  "#3b82f6", "NORMAL": "#22c55e",
}
RISK_BG = {
    "CRITICAL": "#450a0a", "HIGH": "#431407",
    "MEDIUM":   "#422006", "LOW":  "#172554", "NORMAL": "#052e16",
}

cols = st.columns(3)
for i, row in df.iterrows():
    col   = cols[i % 3]
    risk  = row["Risk"]
    color = RISK_COLORS.get(risk, "#22c55e")
    bg    = RISK_BG.get(risk, "#052e16")
    with col:
        st.markdown(
            f"<div style='background:linear-gradient(135deg,{bg},{bg}cc);"
            f"border:1px solid {color}44;border-left:4px solid {color};"
            f"border-radius:12px;padding:16px;margin-bottom:10px'>"
            f"<div style='font-size:14px;font-weight:700;color:#e2e8f0;margin-bottom:8px'>"
            f"{row['Equipment']}</div>"
            f"<div style='font-size:32px;font-weight:800;color:{color};line-height:1'>"
            f"{row['Health (%)']:.0f}%</div>"
            f"<div style='font-size:11px;color:#8898aa;margin-top:2px'>health index</div>"
            f"<div style='margin-top:8px;display:flex;justify-content:space-between;"
            f"align-items:center'>"
            f"<span style='background:{color}22;color:{color};border:1px solid {color}55;"
            f"border-radius:12px;padding:2px 10px;font-size:11px;font-weight:700'>{risk}</span>"
            f"<span style='font-size:11px;color:#64748b'>{row['Anomalies']} alert(s)</span>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

st.markdown("<div class='section-hdr'>PLANT-WIDE HEALTH DISTRIBUTION</div>", unsafe_allow_html=True)

fig_bar = px.bar(
    df.sort_values("Health (%)", ascending=True),
    x="Health (%)", y="Equipment", orientation="h",
    color="Risk", color_discrete_map=RISK_COLORS,
    text="Health (%)", height=300,
)
fig_bar.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
fig_bar.update_layout(
    margin=dict(l=10, r=50, t=10, b=10),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#0f172a",
    font_color="#94a3b8",
    xaxis=dict(gridcolor="#2d3748", color="#64748b"),
    yaxis=dict(gridcolor="#2d3748", color="#e2e8f0"),
)
st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("<div class='section-hdr'>QUICK NAVIGATION</div>", unsafe_allow_html=True)

nav_items = [
    ("pages/1_Chat.py",      "💬", "AI Chat Assistant",    "Ask maintenance questions"),
    ("pages/2_Dashboard.py", "📊", "Sensor Dashboard",     "Live equipment monitoring"),
    ("pages/3_Alerts.py",    "🚨", "Alerts & Risk",        "Anomaly detection"),
    ("pages/4_Reports.py",   "📋", "Report Generator",    "AI-powered reports"),
    ("pages/5_Logbook.py",   "📖", "Maintenance Logbook",  "Record & track activities"),
]
nc = st.columns(5)
for i, (page, icon, label, sub) in enumerate(nav_items):
    with nc[i]:
        st.markdown(
            f"<div class='nav-card'>"
            f"<div class='nav-icon'>{icon}</div>"
            f"<div class='nav-label'>{label}</div>"
            f"<div class='nav-sub'>{sub}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.page_link(page, label=f"Open {label}", use_container_width=True)

st.markdown(
    "<div style='text-align:center;font-size:11px;color:#374151;margin-top:20px;padding-top:12px;"
    "border-top:1px solid #1f2937'>"
    "SteelGuard AI &nbsp;·&nbsp; OpenRouter (Gemma-4) &nbsp;·&nbsp; ChromaDB RAG "
    "&nbsp;·&nbsp; Isolation Forest &nbsp;·&nbsp; Industrial Maintenance Hackathon 2026"
    "</div>",
    unsafe_allow_html=True,
)
