import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

from backend.llm_engine        import MaintenanceLLM
from backend.rag_pipeline      import RAGPipeline
from backend.feedback_store    import FeedbackStore
from utils.sensor_simulator    import current_readings

st.set_page_config(page_title="Reports — SteelGuard", page_icon="📋", layout="wide")

st.markdown("""
<style>
section[data-testid="stSidebarNav"] a {
    padding: 3px 12px !important; font-size: 13px !important; line-height: 1.5 !important;
}
section[data-testid="stSidebarNav"] svg { width: 15px !important; height: 15px !important; }
section[data-testid="stSidebar"] > div:first-child { padding-top: 0.4rem !important; }
section[data-testid="stSidebar"] hr { margin: 0.3rem 0 !important; }
section[data-testid="stSidebar"] .stCheckbox { padding: 1px 0 !important; margin-bottom: 0 !important; }
section[data-testid="stSidebar"] .stSelectbox { margin-bottom: 2px !important; }
section[data-testid="stSidebar"] .stButton button { padding: 4px 12px !important; font-size: 13px !important; }
.block-container { padding-top: 3.5rem !important; }
.section-hdr {
    font-size: 11px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: #8898aa;
    margin: 14px 0 10px 0; padding-bottom: 6px;
    border-bottom: 1px solid #2d3748;
}
.sensor-kpi {
    background: #1a2035; border: 1px solid #2d3748;
    border-radius: 8px; padding: 10px 14px; margin-bottom: 6px;
}
</style>
""", unsafe_allow_html=True)

if "role" not in st.session_state: st.session_state.role = "Engineer"

@st.cache_resource
def get_llm():   return MaintenanceLLM()
@st.cache_resource
def get_rag():   return RAGPipeline()
@st.cache_resource
def get_store(): return FeedbackStore()

llm   = get_llm()
rag   = get_rag()
store = get_store()

EQUIPMENT_LIST = [
    "Rolling Mill", "Blast Furnace", "Continuous Caster",
    "Hydraulic System", "Ladle Furnace", "Compressor",
]
REPORT_TYPES = [
    "Fault Investigation Report",
    "Preventive Maintenance Report",
    "Breakdown Analysis Report",
    "Spare Parts Requisition Report",
    "Shift Handover Report",
    "Risk Assessment Report",
]

with st.sidebar:
    st.session_state.role = st.selectbox(
        "👤 Role", ["Engineer","Supervisor","Admin"],
        index=["Engineer","Supervisor","Admin"].index(st.session_state.role),
    )
    if not llm.is_available():
        st.warning("⚠️ Demo Mode — AI reports limited")

st.markdown(
    "<div style='font-size:22px;font-weight:800;color:#e2e8f0;margin-bottom:2px'>"
    "📋 Maintenance Report Generator"
    "</div>"
    "<div style='font-size:13px;color:#94a3b8;margin-bottom:16px'>"
    "AI-powered reports with live sensor data &amp; knowledge base context"
    "</div>",
    unsafe_allow_html=True,
)

tab1, tab2 = st.tabs(["📝 Generate Report", "📁 Report History"])

with tab1:
    st.markdown("<div class='section-hdr'>REPORT CONFIGURATION</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        selected_eq  = st.selectbox("Equipment", EQUIPMENT_LIST)
        report_type  = st.selectbox("Report Type", REPORT_TYPES)
    with col2:
        auto_populate = st.checkbox("Auto-populate live sensor data", value=True)

    fault_desc = st.text_area(
        "Fault / Issue Description",
        placeholder="Describe the fault, observations, or reason for the report...",
        height=120,
    )

    readings = {}
    if auto_populate:
        readings = current_readings(selected_eq)
        st.markdown("<div class='section-hdr'>LIVE SENSOR SNAPSHOT</div>", unsafe_allow_html=True)
        cols = st.columns(3)
        for i, (k, v) in enumerate(readings.items()):
            with cols[i % 3]:
                st.markdown(
                    f"<div class='sensor-kpi'>"
                    f"<div style='font-size:10px;color:#64748b;font-weight:700;text-transform:uppercase;"
                    f"letter-spacing:0.8px;margin-bottom:3px'>{k.replace('_',' ').title()}</div>"
                    f"<div style='font-size:18px;font-weight:800;color:#3b82f6'>{v:.2f}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    if st.button("🤖 Generate Report", type="primary", disabled=not fault_desc.strip()):
        with st.spinner("Generating AI-powered report..."):
            rag_ctx  = rag.query(f"{selected_eq} {report_type} {fault_desc}", n_results=4)
            content  = llm.generate_report(selected_eq, fault_desc, readings, st.session_state.role, rag_ctx)
            rep_id   = store.save_report(selected_eq, report_type, content, st.session_state.role)
        st.markdown(
            f"<div style='background:#052e16;border:1px solid #166534;border-radius:10px;"
            f"padding:10px 16px;margin:10px 0;font-size:13px;color:#86efac'>"
            f"✅ Report generated and saved &nbsp;·&nbsp; ID: <b>{rep_id}</b></div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='section-hdr'>GENERATED REPORT</div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='background:#0f172a;border:1px solid #2d3748;border-radius:12px;"
            "padding:4px 20px;margin-bottom:10px'>",
            unsafe_allow_html=True,
        )
        st.markdown(content)
        st.markdown("</div>", unsafe_allow_html=True)
        st.download_button(
            "⬇️ Download Report (.txt)",
            data=content,
            file_name=f"{selected_eq.replace(' ','_')}_{report_type.replace(' ','_')}.txt",
            mime="text/plain",
        )

with tab2:
    st.markdown("<div class='section-hdr'>SAVED REPORTS</div>", unsafe_allow_html=True)
    filter_eq = st.selectbox("Filter by Equipment", ["All"] + EQUIPMENT_LIST, key="hist_eq")
    reports   = store.get_reports(filter_eq if filter_eq != "All" else None)
    if not reports:
        st.markdown(
            "<div style='background:#1a2035;border:1px solid #2d3748;border-radius:10px;"
            "padding:20px;text-align:center;color:#64748b;font-size:13px'>"
            "📭 &nbsp; No reports saved yet. Generate one in the first tab.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='font-size:12px;color:#64748b;margin-bottom:10px'>"
            f"{len(reports)} report(s) found</div>",
            unsafe_allow_html=True,
        )
        for rep in reports:
            with st.expander(
                f"#{rep['id']}  ·  {rep['equipment']}  ·  {rep['report_type']}  ·  {rep['timestamp'][:16]}"
            ):
                st.markdown(
                    f"<div style='display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap'>"
                    f"<span style='background:#1a2035;border:1px solid #2d3748;border-radius:6px;"
                    f"padding:3px 10px;font-size:11px;color:#94a3b8'>🏭 {rep['equipment']}</span>"
                    f"<span style='background:#1a2035;border:1px solid #2d3748;border-radius:6px;"
                    f"padding:3px 10px;font-size:11px;color:#94a3b8'>📋 {rep['report_type']}</span>"
                    f"<span style='background:#1a2035;border:1px solid #2d3748;border-radius:6px;"
                    f"padding:3px 10px;font-size:11px;color:#94a3b8'>👤 {rep['generated_by']}</span>"
                    f"<span style='background:#1a2035;border:1px solid #2d3748;border-radius:6px;"
                    f"padding:3px 10px;font-size:11px;color:#64748b'>🕒 {rep['timestamp'][:16]}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<div style='background:#0f172a;border:1px solid #2d3748;border-radius:10px;"
                    "padding:4px 20px;margin-bottom:8px'>",
                    unsafe_allow_html=True,
                )
                st.markdown(rep["content"])
                st.markdown("</div>", unsafe_allow_html=True)
                st.download_button(
                    "⬇️ Download Report (.txt)",
                    data=rep["content"],
                    file_name=f"report_{rep['id']}.txt",
                    mime="text/plain",
                    key=f"dl_{rep['id']}",
                )
