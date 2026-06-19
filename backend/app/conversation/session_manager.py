import time
import threading
from dataclasses import dataclass, field
from typing import Optional

SESSION_TTL = 30 * 60
MAX_HISTORY = 10
CLEANUP_INTERVAL = 5 * 60

@dataclass 
class Message:
    role : str
    content : str
    timestamp : float = field(default_factory=time.time)

@dataclass 
class Session:
    session_id : str
    history : list[Message] = field(default_factory=list)
    created_at : float = field(default_factory=time.time)
    last_active : float = field(default_factory=time.time)

    def add_message(self, role: str, content: str):
        self.history.append(Message(role=role, content=content))
        self.last_active = time.time()
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]
    
    def is_expired(self) -> bool:
        return(time.time() - self.last_active) > SESSION_TTL
    
    def get_history_text(self) -> str:
        if not self.history:
            return ""
        lines = []
        for msg in self.history:
            prefix = "Khach" if msg.role == "user" else "Bot"
            lines.append(f"{prefix}: {msg.content}")
        return "\n".join(lines)
    def summary(self) -> dict:
        return {
            "session_id": self.session_id,
            "message_count": len(self.history),
            "created_at": self.created_at,
            "last_active": self.last_active
        }

    def sumary(self) -> dict:
        return self.summary()

class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()
        self._start_cleanup_thread()

    def get_or_create(self, session_id: str) -> Session:
        with self._lock:
            if session_id not in self._sessions or self._sessions[session_id].is_expired():
                self._sessions[session_id] = Session(session_id=session_id)
            return self._sessions[session_id]
    
    def get(self, session_id: str) -> Optional[Session]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session and session.is_expired():
                del self._sessions[session_id]
                return None
            return session
        
    def delete(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)

    def clear_expired(self):
        with self._lock:
            expired = [sid for sid, s in self._sessions.items() if s.is_expired()]
            for sid in expired:
                del self._sessions[sid]
            if expired:
                print(f"[SessionManager] Đã xoá {len(expired)} session hết hạn.")

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for s in self._sessions.values() if not s.is_expired())

    def _start_cleanup_thread(self):
        def _loop():
            while True:
                time.sleep(CLEANUP_INTERVAL)
                self.clear_expired()
        t = threading.Thread(target=_loop, daemon=True)
        t.start()


session_manager = SessionManager()


 


