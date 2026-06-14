import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import plotly.express as px

from backend.feedback_store import FeedbackStore

st.set_page_config(page_title="Logbook — SteelGuard", page_icon="📖", layout="wide")

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
.entry-meta {
    display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px;
}
.entry-tag {
    background: #1a2035; border: 1px solid #2d3748; border-radius: 6px;
    padding: 3px 10px; font-size: 11px; color: #94a3b8;
}
.stat-card {
    background: linear-gradient(135deg, #1a2035, #1e2a45);
    border: 1px solid #2d3748; border-radius: 12px;
    padding: 14px 18px; text-align: center;
}
</style>
""", unsafe_allow_html=True)

if "role" not in st.session_state: st.session_state.role = "Engineer"

@st.cache_resource
def get_store(): return FeedbackStore()
store = get_store()

EQUIPMENT_LIST = [
    "Rolling Mill", "Blast Furnace", "Continuous Caster",
    "Hydraulic System", "Ladle Furnace", "Compressor",
]
ACTIVITY_TYPES = [
    "Preventive Maintenance",
    "Corrective Maintenance",
    "Breakdown Repair",
    "Inspection",
    "Lubrication",
    "Calibration",
    "Spare Part Replacement",
    "Cleaning / Housekeeping",
    "Safety Check",
    "Other",
]

with st.sidebar:
    st.session_state.role = st.selectbox(
        "👤 Role", ["Engineer","Supervisor","Admin"],
        index=["Engineer","Supervisor","Admin"].index(st.session_state.role),
    )

st.markdown(
    "<div style='font-size:22px;font-weight:800;color:#e2e8f0;margin-bottom:2px'>"
    "📖 Maintenance Logbook"
    "</div>"
    "<div style='font-size:13px;color:#94a3b8;margin-bottom:16px'>"
    "Record, track &amp; analyse all plant maintenance activities"
    "</div>",
    unsafe_allow_html=True,
)

tab1, tab2, tab3 = st.tabs(["➕ Add Entry", "📋 View Entries", "📊 Analytics"])

with tab1:
    st.markdown("<div class='section-hdr'>NEW LOGBOOK ENTRY</div>", unsafe_allow_html=True)
    with st.form("logbook_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            equipment      = st.selectbox("Equipment *", EQUIPMENT_LIST)
            activity_type  = st.selectbox("Activity Type *", ACTIVITY_TYPES)
            performed_by   = st.text_input("Performed By *", placeholder="Engineer name / ID")
            shift          = st.selectbox("Shift", ["A","B","C","Day","Night"])
        with c2:
            spare_parts    = st.text_input("Spare Parts Used", placeholder="e.g. Bearing SKF 22230, Oil filter")
            outcome        = st.selectbox("Outcome", ["Completed","Partially Completed","Pending","Escalated"])
            follow_up      = st.text_input("Follow-up Required", placeholder="Any follow-up action...")

        description = st.text_area("Description *", placeholder="Describe the work performed in detail...", height=120)

        submitted = st.form_submit_button("💾 Save Entry", type="primary")
        if submitted:
            if not description.strip() or not performed_by.strip():
                st.error("Description and Performed By fields are required.")
            else:
                entry_id = store.add_logbook_entry(
                    equipment, activity_type, description,
                    performed_by, shift, spare_parts, outcome, follow_up,
                )
                st.success(f"✅ Logbook entry saved (ID: {entry_id})")

with tab2:
    st.markdown("<div class='section-hdr'>LOGBOOK ENTRIES</div>", unsafe_allow_html=True)
    filter_eq = st.selectbox("Filter by Equipment", ["All"] + EQUIPMENT_LIST, key="view_eq")
    entries   = store.get_logbook(filter_eq if filter_eq != "All" else None)
    if not entries:
        st.markdown(
            "<div style='background:#1a2035;border:1px solid #2d3748;border-radius:10px;"
            "padding:20px;text-align:center;color:#64748b;font-size:13px'>"
            "📭 &nbsp; No entries yet. Add one in the first tab.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='font-size:12px;color:#64748b;margin-bottom:10px'>"
            f"{len(entries)} entr{'y' if len(entries)==1 else 'ies'} found</div>",
            unsafe_allow_html=True,
        )
        OUTCOME_COLORS = {
            "Completed": "#22c55e", "Partially Completed": "#eab308",
            "Pending": "#f97316", "Escalated": "#ef4444",
        }
        for e in entries:
            oc = OUTCOME_COLORS.get(e.get("outcome", ""), "#94a3b8")
            with st.expander(
                f"#{e['id']}  ·  {e['equipment']}  ·  {e['activity_type']}  ·  {e['timestamp'][:16]}"
            ):
                st.markdown(
                    f"<div class='entry-meta'>"
                    f"<span class='entry-tag'>🏭 {e['equipment']}</span>"
                    f"<span class='entry-tag'>🔧 {e['activity_type']}</span>"
                    f"<span class='entry-tag'>👤 {e['performed_by']}</span>"
                    f"<span class='entry-tag'>🕑 Shift {e['shift']}</span>"
                    f"<span style='background:#1a2035;border:1px solid {oc};"
                    f"border-radius:6px;padding:3px 10px;font-size:11px;color:{oc}'>"
                    f"{e.get('outcome','')}</span>"
                    f"</div>"
                    f"<div style='background:#0f172a;border:1px solid #2d3748;border-radius:8px;"
                    f"padding:10px 14px;font-size:13px;color:#cbd5e1;margin-bottom:6px'>"
                    f"{e['description']}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if e.get("spare_parts_used"):
                    st.markdown(
                        f"<div style='font-size:12px;color:#94a3b8;margin-top:4px'>"
                        f"🔧 <b>Parts used:</b> {e['spare_parts_used']}</div>",
                        unsafe_allow_html=True,
                    )
                if e.get("follow_up"):
                    st.markdown(
                        f"<div style='font-size:12px;color:#f97316;margin-top:4px'>"
                        f"⚠️ <b>Follow-up:</b> {e['follow_up']}</div>",
                        unsafe_allow_html=True,
                    )

with tab3:
    st.markdown("<div class='section-hdr'>LOGBOOK ANALYTICS</div>", unsafe_allow_html=True)
    all_entries = store.get_logbook()
    if not all_entries:
        st.markdown(
            "<div style='background:#1a2035;border:1px solid #2d3748;border-radius:10px;"
            "padding:20px;text-align:center;color:#64748b;font-size:13px'>"
            "📭 &nbsp; No data yet for analytics.</div>",
            unsafe_allow_html=True,
        )
    else:
        df = pd.DataFrame(all_entries)
        df["date"] = pd.to_datetime(df["timestamp"]).dt.date

        k1, k2, k3 = st.columns(3)
        for col, label, value, color in [
            (k1, "Total Entries",      len(df),                        "#3b82f6"),
            (k2, "Equipment Types",    df["equipment"].nunique(),       "#22c55e"),
            (k3, "Unique Performers",  df["performed_by"].nunique(),    "#eab308"),
        ]:
            col.markdown(
                f"<div class='stat-card'>"
                f"<div style='font-size:10px;font-weight:700;letter-spacing:1.2px;"
                f"text-transform:uppercase;color:#8898aa;margin-bottom:4px'>{label}</div>"
                f"<div style='font-size:28px;font-weight:800;color:{color}'>{value}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            fig1 = px.histogram(df, x="equipment", title="Entries by Equipment", color="equipment")
            fig1.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = px.pie(df, names="activity_type", title="Activity Type Distribution")
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)

        outcome_counts = df["outcome"].value_counts().reset_index()
        outcome_counts.columns = ["Outcome","Count"]
        fig3 = px.bar(outcome_counts, x="Outcome", y="Count", title="Outcomes", color="Outcome")
        fig3.update_layout(height=280, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)
