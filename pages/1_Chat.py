import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uuid
import streamlit as st

from backend.llm_engine    import MaintenanceLLM
from backend.rag_pipeline  import RAGPipeline
from backend.feedback_store import FeedbackStore
from utils.sensor_simulator import current_readings

st.set_page_config(page_title="AI Chat — SteelGuard", page_icon="💬", layout="wide")

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
/* Chat-specific */
.chat-empty {
    background: linear-gradient(135deg, #1a2035 0%, #1e2a45 100%);
    border: 1px solid #2d3748; border-radius: 14px;
    padding: 32px; text-align: center; margin: 8px 0 20px 0;
}
</style>
""", unsafe_allow_html=True)

if "role"        not in st.session_state: st.session_state.role        = "Engineer"
if "session_id"  not in st.session_state: st.session_state.session_id  = str(uuid.uuid4())
if "messages"    not in st.session_state: st.session_state.messages    = []
if "conv_ids"    not in st.session_state: st.session_state.conv_ids    = {}
if "use_sensors" not in st.session_state: st.session_state.use_sensors = True
if "use_rag"     not in st.session_state: st.session_state.use_rag     = True
if "selected_eq" not in st.session_state: st.session_state.selected_eq = "None"

@st.cache_resource
def get_llm():    return MaintenanceLLM()
@st.cache_resource
def get_rag():    return RAGPipeline()
@st.cache_resource
def get_store():  return FeedbackStore()

llm   = get_llm()
rag   = get_rag()
store = get_store()

EQUIPMENT_LIST = [
    "Rolling Mill", "Blast Furnace", "Continuous Caster",
    "Hydraulic System", "Ladle Furnace", "Compressor",
]

SAMPLE_QUESTIONS = [
    "What are the symptoms of bearing failure in Rolling Mill?",
    "How do I perform LOTO on the Hydraulic System?",
    "Blast Furnace top pressure is high — what should I do?",
    "List spare parts needed for Continuous Caster roll change",
    "What is the SOP for emergency shutdown of Ladle Furnace?",
    "Compressor vibration is above 4.5 mm/s — diagnose",
]

with st.sidebar:
    st.markdown("## 💬 AI Chat Settings")
    st.divider()
    st.session_state.role = st.selectbox(
        "👤 Role", ["Engineer", "Supervisor", "Admin"],
        index=["Engineer", "Supervisor", "Admin"].index(st.session_state.role),
    )
    st.session_state.selected_eq = st.selectbox(
        "🔧 Equipment Context", ["None"] + EQUIPMENT_LIST,
        index=(["None"] + EQUIPMENT_LIST).index(st.session_state.selected_eq),
    )
    st.checkbox(
        "📡 Include live sensor data", key="use_sensors"
    )
    st.checkbox(
        "📚 Use Knowledge Base (RAG)", key="use_rag"
    )
    if st.button("🗑️ Clear Conversation"):
        st.session_state.messages = []
        st.session_state.conv_ids = {}
        llm.clear_session(st.session_state.session_id)
        st.rerun()
    st.divider()
    st.markdown(
        "<div style='font-size:11px;font-weight:700;color:#8898aa;text-transform:uppercase;"
        "letter-spacing:1px;margin-bottom:3px'>Quick Questions</div>",
        unsafe_allow_html=True,
    )
    sel_q = st.selectbox(
        "quick_q", ["\u2014 pick a question —"] + SAMPLE_QUESTIONS,
        label_visibility="collapsed",
    )
    if st.button("📨 Ask this", use_container_width=True):
        if sel_q != "\u2014 pick a question —":
            st.session_state["_pending_query"] = sel_q
    if not llm.is_available():
        st.markdown(
            "<div style='background:#422006;border:1px solid #f97316;border-radius:6px;"
            "padding:5px 8px;font-size:11px;color:#fb923c;margin-top:4px'>"
            "⚠️ Demo Mode — add OpenRouter key in .env</div>",
            unsafe_allow_html=True,
        )

st.markdown(
    "<div style='font-size:22px;font-weight:800;color:#e2e8f0;margin-bottom:2px'>"
    "💬 AI Maintenance Assistant"
    "</div>"
    "<div style='font-size:13px;color:#94a3b8;margin-bottom:16px'>"
    "Multi-turn AI chat &nbsp;·&nbsp; Live sensor context &nbsp;·&nbsp; Knowledge base RAG"
    "</div>",
    unsafe_allow_html=True,
)

if not st.session_state.messages:
    st.markdown(
        "<div class='chat-empty'>"
        "<div style='font-size:40px;margin-bottom:12px'>💬</div>"
        "<div style='font-size:17px;font-weight:700;color:#e2e8f0;margin-bottom:8px'>"
        "Start a conversation</div>"
        "<div style='font-size:13px;color:#94a3b8'>"
        "Pick a quick question from the sidebar, or type your own query below."
        "</div></div>",
        unsafe_allow_html=True,
    )

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            conv_key = f"msg_{i}"
            conv_id  = st.session_state.conv_ids.get(conv_key)
            if conv_id:
                c1, c2 = st.columns([1, 20])
                with c1:
                    if st.button("👍", key=f"up_{i}"):
                        store.save_feedback(conv_id, "positive")
                        st.toast("Thanks for the feedback!")
                with c2:
                    if st.button("👎", key=f"dn_{i}"):
                        store.save_feedback(conv_id, "negative")
                        st.toast("Feedback noted — we'll improve!")

pending = st.session_state.pop("_pending_query", None)
user_input = st.chat_input("Ask about equipment, faults, SOPs, spare parts...") or pending

if user_input:
    # Add user message to history and display it
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Build context from enabled options
    context_parts = []
    eq = st.session_state.get("selected_eq", "None")
    if eq != "None" and st.session_state.get("use_sensors", True):
        try:
            readings   = current_readings(eq)
            sensor_txt = "\n".join(f"  {k}: {v}" for k, v in readings.items())
            context_parts.append(f"Current sensor readings for {eq}:\n{sensor_txt}")
        except Exception:
            pass
    if st.session_state.get("use_rag", True):
        try:
            rag_ctx = rag.query(user_input, n_results=4)
            if rag_ctx:
                context_parts.append(f"Relevant knowledge base information:\n{rag_ctx}")
        except Exception:
            pass
    context = "\n\n".join(context_parts)

    # Get AI response and display it
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = llm.chat(st.session_state.session_id, user_input, context)
            except Exception as e:
                response = f"⚠️ Error: {e}"
        st.markdown(response)
        # Save to DB
        try:
            msg_idx = len(st.session_state.messages)
            conv_id = store.save_conversation(
                st.session_state.session_id,
                eq if eq != "None" else "General",
                user_input, response,
            )
            st.session_state.conv_ids[f"msg_{msg_idx}"] = conv_id
        except Exception:
            pass

    # Append assistant response — no st.rerun() needed
    st.session_state.messages.append({"role": "assistant", "content": response})
