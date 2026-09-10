import os
import json
import threading
from typing import List, Dict, Any

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
HISTORY_FILE = os.path.join(DATA_DIR, "chat_sessions.json")

class ChatHistoryService:
    def __init__(self):
        self._lock = threading.Lock()
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(HISTORY_FILE):
            self._save_to_file([])

    def _read_from_file(self) -> List[Dict[str, Any]]:
        with self._lock:
            if not os.path.exists(HISTORY_FILE):
                return []
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ChatHistoryService] Error reading chat sessions: {e}")
                return []

    def _save_to_file(self, sessions: List[Dict[str, Any]]) -> bool:
        with self._lock:
            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(sessions, f, ensure_ascii=False, indent=2)
                return True
            except Exception as e:
                print(f"[ChatHistoryService] Error saving chat sessions: {e}")
                return False

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        return self._read_from_file()

    def save_sessions(self, sessions: List[Dict[str, Any]]) -> bool:
        return self._save_to_file(sessions)

    def delete_session(self, session_id: str) -> bool:
        sessions = self._read_from_file()
        new_sessions = [s for s in sessions if s.get("id") != session_id]
        if len(new_sessions) != len(sessions):
            return self._save_to_file(new_sessions)
        return True
