import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "maintenance.db")


class FeedbackStore:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(DB_PATH, check_same_thread=False)

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   TEXT,
                equipment    TEXT,
                user_message TEXT,
                ai_response  TEXT,
                timestamp    TEXT,
                feedback     TEXT DEFAULT NULL,
                feedback_note TEXT DEFAULT NULL
            );
            CREATE TABLE IF NOT EXISTS logbook (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment      TEXT,
                activity_type  TEXT,
                description    TEXT,
                performed_by   TEXT,
                shift          TEXT,
                spare_parts_used TEXT,
                outcome        TEXT,
                follow_up      TEXT,
                timestamp      TEXT
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment       TEXT,
                severity        TEXT,
                message         TEXT,
                sensor_snapshot TEXT,
                acknowledged    INTEGER DEFAULT 0,
                ack_by          TEXT DEFAULT NULL,
                timestamp       TEXT
            );
            CREATE TABLE IF NOT EXISTS reports (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment  TEXT,
                report_type TEXT,
                content    TEXT,
                generated_by TEXT,
                timestamp  TEXT
            );
            """)

    def save_conversation(self, session_id, equipment, user_msg, ai_response) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO conversations (session_id,equipment,user_message,ai_response,timestamp) VALUES (?,?,?,?,?)",
                (session_id, equipment, user_msg, ai_response, datetime.now().isoformat())
            )
            return cur.lastrowid

    def save_feedback(self, conv_id: int, feedback: str, note: str = ""):
        with self._conn() as conn:
            conn.execute(
                "UPDATE conversations SET feedback=?,feedback_note=? WHERE id=?",
                (feedback, note, conv_id)
            )

    def get_feedback_summary(self) -> dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            pos   = conn.execute("SELECT COUNT(*) FROM conversations WHERE feedback='positive'").fetchone()[0]
            neg   = conn.execute("SELECT COUNT(*) FROM conversations WHERE feedback='negative'").fetchone()[0]
        if total == 0:
            sat = "N/A"
        else:
            pct = int(pos / total * 100) if total else 0
            sat = f"{pct}% 👍"
        return {"total": total, "positive": pos, "negative": neg, "satisfaction": sat}

    def add_logbook_entry(self, equipment, activity_type, description, performed_by,
                          shift, spare_parts_used="", outcome="", follow_up="") -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO logbook (equipment,activity_type,description,performed_by,shift,spare_parts_used,outcome,follow_up,timestamp) VALUES (?,?,?,?,?,?,?,?,?)",
                (equipment, activity_type, description, performed_by, shift,
                 spare_parts_used, outcome, follow_up, datetime.now().isoformat())
            )
            return cur.lastrowid

    def get_logbook(self, equipment: str | None = None) -> list[dict]:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            if equipment:
                rows = conn.execute("SELECT * FROM logbook WHERE equipment=? ORDER BY timestamp DESC", (equipment,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM logbook ORDER BY timestamp DESC").fetchall()
            return [dict(r) for r in rows]

    def save_alert(self, equipment, severity, message, sensor_snapshot: dict | None = None) -> int:
        snap = json.dumps(sensor_snapshot or {})
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO alerts (equipment,severity,message,sensor_snapshot,timestamp) VALUES (?,?,?,?,?)",
                (equipment, severity, message, snap, datetime.now().isoformat())
            )
            return cur.lastrowid

    def get_alerts(self, acknowledged: bool | None = None) -> list[dict]:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            if acknowledged is None:
                rows = conn.execute("SELECT * FROM alerts ORDER BY timestamp DESC").fetchall()
            else:
                rows = conn.execute("SELECT * FROM alerts WHERE acknowledged=? ORDER BY timestamp DESC", (int(acknowledged),)).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["sensor_snapshot"] = json.loads(d.get("sensor_snapshot") or "{}")
                result.append(d)
            return result

    def acknowledge_alert(self, alert_id: int, ack_by: str):
        with self._conn() as conn:
            conn.execute("UPDATE alerts SET acknowledged=1,ack_by=? WHERE id=?", (ack_by, alert_id))

    def unack_count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM alerts WHERE acknowledged=0").fetchone()[0]

    def save_report(self, equipment, report_type, content, generated_by) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO reports (equipment,report_type,content,generated_by,timestamp) VALUES (?,?,?,?,?)",
                (equipment, report_type, content, generated_by, datetime.now().isoformat())
            )
            return cur.lastrowid

    def get_reports(self, equipment: str | None = None) -> list[dict]:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            if equipment:
                rows = conn.execute("SELECT * FROM reports WHERE equipment=? ORDER BY timestamp DESC", (equipment,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM reports ORDER BY timestamp DESC").fetchall()
            return [dict(r) for r in rows]
