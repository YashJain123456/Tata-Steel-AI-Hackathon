import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL_NAME = "google/gemma-4-31b-it:free"

_OPENROUTER_AVAIL = False
try:
    import requests
    if os.getenv("OPENROUTER_API_KEY"):
        _OPENROUTER_AVAIL = True
except ImportError:
    pass

SYSTEM_PROMPT = """You are SteelGuard AI, an expert maintenance engineer assistant for an integrated steel plant.
You specialise in: Rolling Mills, Blast Furnaces, Continuous Casters, Hydraulic Systems, Ladle Furnaces, and Compressors.

When answering questions or diagnosing faults:
1. Prioritise using the provided sensor data and knowledge base context.
2. IMPORTANT: If the answer is NOT found in the provided knowledge base context, you MUST use your general engineering knowledge to provide a helpful answer. However, you must explicitly add a warning stating that your answer is based on general industry advice and not the plant's official SOPs.

When diagnosing faults, always structure your response as follows:

## 🔍 Probable Fault Diagnosis
[Your diagnosis here]

## 🧪 Root Cause Analysis
[Detailed root cause explanation]

## ⚠️ Risk Level
[CRITICAL / HIGH / MEDIUM / LOW — with brief justification]

## 🚦 Immediate Actions
[Step-by-step immediate corrective actions]

## 📅 Long-term Recommendations
[Preventive maintenance recommendations]

## 🔩 Spare Parts Required
[List required spare parts with part numbers if possible]

Be precise, cite sensor values when provided, and always prioritise worker safety."""


class MaintenanceLLM:
    def __init__(self):
        self._available   = False
        self.client       = None
        # chat_sessions stores full message history per session_id
        self.chat_sessions: dict[str, list[dict]] = {}

        if _OPENROUTER_AVAIL:
            self.api_key = os.getenv("OPENROUTER_API_KEY")
            self._available = True
            print(f"[LLM] OpenRouter ready — model: {MODEL_NAME}")
        else:
            print("[LLM] OPENROUTER_API_KEY not found or requests package not installed — running in demo mode")

    def is_available(self) -> bool:
        return self._available

    # ── Single-shot completion (analysis, reports) ────────────────────────────
    def _complete(self, messages: list[dict], max_tokens: int = 2000) -> str:
        import requests
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8501", # Required by OpenRouter for some free models
            "X-Title": "SteelGuard AI",
        }
        data = {
            "model": MODEL_NAME,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        try:
            resp = requests.post(
                url=f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=data,
            )
            resp.raise_for_status()
            resp_json = resp.json()
            if "choices" in resp_json and len(resp_json["choices"]) > 0:
                return resp_json["choices"][0]["message"]["content"]
            else:
                return f"Error: Unexpected response format from OpenRouter: {resp_json}"
        except Exception as e:
            print(f"[LLM] API call failed: {e}")
            return f"Error: Failed to connect to OpenRouter ({e})"

    # ── Equipment analysis (one-shot) ─────────────────────────────────────────
    def analyze_equipment(self, equipment: str, readings: dict, alerts: list,
                          rul_result: dict, rag_context: str = "") -> str:
        if not self._available:
            return self._fallback_response(equipment, alerts, rul_result)
        try:
            prompt = self._build_analysis_prompt(equipment, readings, alerts, rul_result, rag_context)
            return self._complete([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ])
        except Exception as e:
            print(f"[LLM] analyze_equipment error: {e}")
            return self._fallback_response(equipment, alerts, rul_result)

    # ── Multi-turn chat ───────────────────────────────────────────────────────
    def chat(self, session_id: str, message: str, context: str = "") -> str:
        if not self._available:
            return self._fallback_chat(message)
        try:
            if session_id not in self.chat_sessions:
                self.chat_sessions[session_id] = [
                    {"role": "system", "content": SYSTEM_PROMPT}
                ]
            history  = self.chat_sessions[session_id]
            user_msg = f"Optional Context (ignore if irrelevant):\n{context}\n\nUser question: {message}\n\nCRITICAL INSTRUCTION: Read the user's question carefully. If the optional context above does NOT contain the specific answer, DO NOT say the information is missing. You MUST IGNORE the context and answer the question in full using your own general engineering knowledge. Start your answer with: '⚠️ *General Industry Advice (Not from plant SOPs):*' and then provide the full emergency shutdown steps." if context else message
            history.append({"role": "user", "content": user_msg})
            reply = self._complete(history, max_tokens=1500)
            history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            print(f"[LLM] chat error: {e}")
            return self._fallback_chat(message)

    # ── Report generation (one-shot) ──────────────────────────────────────────
    def generate_report(self, equipment: str, fault_description: str,
                        readings: dict, role: str, rag_context: str = "") -> str:
        if not self._available:
            return self._fallback_report(equipment, fault_description, readings)
        try:
            prompt = f"""Generate a formal Maintenance Report for the following:

Equipment: {equipment}
Prepared By (Role): {role}
Fault / Issue: {fault_description}
Sensor Readings: {readings}

Knowledge Base Context:
{rag_context if rag_context else 'N/A'}

Format the report with these sections:
1. Executive Summary
2. Equipment Details & Sensor Readings
3. Fault Analysis
4. Root Cause
5. Actions Taken / Recommended
6. Spare Parts Required
7. Follow-up Schedule
8. Safety Considerations

Use professional technical language appropriate for a steel plant maintenance report."""
            return self._complete([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ], max_tokens=2500)
        except Exception as e:
            print(f"[LLM] generate_report error: {e}")
            return self._fallback_report(equipment, fault_description, readings)

    def clear_session(self, session_id: str):
        self.chat_sessions.pop(session_id, None)

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _build_analysis_prompt(equipment, readings, alerts, rul_result, rag_context):
        alert_txt   = "\n".join(f"  - {a['message']}" for a in alerts) if alerts else "  None"
        reading_txt = "\n".join(f"  {k}: {v:.2f}" for k, v in readings.items())
        return f"""Analyse the following equipment condition for {equipment}:

SENSOR READINGS:
{reading_txt}

ACTIVE ALERTS:
{alert_txt}

REMAINING USEFUL LIFE:
  RUL: {rul_result.get('rul_hours','N/A')} hours ({rul_result.get('rul_days','N/A')} days)
  Health: {rul_result.get('health_pct','N/A')}%
  Status: {rul_result.get('status','N/A')}
  Limiting Parameter: {rul_result.get('limiting_parameter','N/A')}

KNOWLEDGE BASE CONTEXT:
{rag_context if rag_context else 'No context retrieved.'}

Provide a complete maintenance analysis following the structured format."""

    @staticmethod
    def _fallback_response(equipment: str, alerts: list, rul_result: dict) -> str:
        alert_lines = "\n".join(f"- {a['message']}" for a in alerts) if alerts else "- No alerts detected"
        crit = any(a.get("severity") == "CRITICAL" for a in alerts)
        return f"""## 🔍 Probable Fault Diagnosis
*(Demo Mode — OpenRouter API key not configured.)*

Based on sensor data for **{equipment}**:
{alert_lines}

## 🧪 Root Cause Analysis
Anomalies detected. Review thresholds and recent maintenance history.

## ⚠️ Risk Level
{"CRITICAL — Immediate action required" if crit else "MEDIUM — Schedule inspection"}

## 🚦 Immediate Actions
1. Verify sensor readings with local gauges
2. Notify shift supervisor
3. Prepare for potential shutdown if readings worsen

## 📅 Long-term Recommendations
- Review PM schedule for {equipment}
- Calibrate sensors; analyse 30-day trend data

## 🔩 Spare Parts Required
- Check inventory for {equipment}
- Estimated RUL: {rul_result.get('rul_hours','N/A')} hours"""

    @staticmethod
    def _fallback_chat(message: str) -> str:
        return (
            "**Demo Mode** — OpenRouter is not authenticated.\n\n"
            "Set `OPENROUTER_API_KEY` in your `.env` file and then restart the app to enable AI responses.\n\n"
            f"Your question: *{message[:200]}*"
        )

    @staticmethod
    def _fallback_report(equipment: str, fault: str, readings: dict) -> str:
        reading_lines = "\n".join(f"- {k}: {v:.2f}" for k, v in readings.items())
        return f"""# Maintenance Report — {equipment}
*(Demo Mode — OpenRouter not authenticated)*

## 1. Executive Summary
Maintenance event logged for {equipment}. AI analysis unavailable — set OPENROUTER_API_KEY to enable.

## 2. Equipment Details & Sensor Readings
{reading_lines}

## 3. Fault Analysis
Reported Issue: {fault}

## 4. Root Cause
Manual investigation required.

## 5. Actions Taken / Recommended
- Inspect equipment per SOP
- Document findings in logbook
- Order required spare parts

## 6. Spare Parts Required
- To be determined during inspection

## 7. Follow-up Schedule
- Next inspection: within 48 hours

## 8. Safety Considerations
- Follow LOTO procedures before any hands-on work
- Wear appropriate PPE"""
