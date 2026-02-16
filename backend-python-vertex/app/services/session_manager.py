"""In-memory session manager (demo purpose)."""

import uuid
from datetime import datetime
from typing import Dict, Optional

from app.models.schemas import SessionData, TravelConditions, TravelPlan, Message


class SessionManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionData] = {}

    def create_session(self, user_id: str) -> SessionData:
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        session = SessionData(
            session_id=session_id,
            user_id=user_id,
            conditions=TravelConditions(),
            plans=[],
            messages=[],
            created_at=now,
            updated_at=now,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[SessionData]:
        return self._sessions.get(session_id)

    def get_or_create_session(self, session_id: Optional[str], user_id: str) -> SessionData:
        if session_id:
            s = self._sessions.get(session_id)
            if s:
                return s
        return self.create_session(user_id)

    def update_session(
        self,
        session_id: str,
        conditions: Optional[TravelConditions] = None,
        plans: Optional[list] = None,
        add_message: Optional[Message] = None,
    ) -> Optional[SessionData]:
        session = self._sessions.get(session_id)
        if not session:
            return None

        if conditions:
            session.conditions = conditions
        if plans is not None:
            session.plans = plans
        if add_message:
            session.messages.append(add_message)

        session.updated_at = datetime.now().isoformat()
        self._sessions[session_id] = session
        return session

    def add_plans(self, session_id: str, plans: list) -> Optional[SessionData]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        session.plans = plans
        session.updated_at = datetime.now().isoformat()
        self._sessions[session_id] = session
        return session

    def get_plan(self, session_id: str, plan_id: str) -> Optional[TravelPlan]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        for plan in session.plans:
            if plan.plan_id == plan_id:
                return plan
        return None


session_manager = SessionManager()

