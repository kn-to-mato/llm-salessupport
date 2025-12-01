"""セッション管理サービス"""
import uuid
from datetime import datetime
from typing import Dict, Optional

from app.models.schemas import SessionData, TravelConditions, TravelPlan, Message
from app.logging_config import get_logger

logger = get_logger(__name__)


class SessionManager:
    """インメモリセッション管理（デモ用）"""
    
    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}
        logger.info("session_manager_initialized")
    
    def create_session(self, user_id: str) -> SessionData:
        """新規セッションを作成"""
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
        
        logger.info(
            "session_created",
            session_id=session_id,
            user_id=user_id,
            total_sessions=len(self._sessions),
        )
        
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """セッションを取得"""
        session = self._sessions.get(session_id)
        
        if session:
            logger.debug(
                "session_get_hit",
                session_id=session_id,
                message_count=len(session.messages),
                plan_count=len(session.plans),
            )
        else:
            logger.debug(
                "session_get_miss",
                session_id=session_id,
            )
        
        return session
    
    def get_or_create_session(self, session_id: Optional[str], user_id: str) -> SessionData:
        """セッションを取得または作成"""
        logger.debug(
            "get_or_create_session",
            session_id=session_id,
            user_id=user_id,
        )
        
        if session_id:
            session = self.get_session(session_id)
            if session:
                logger.debug(
                    "existing_session_found",
                    session_id=session_id,
                )
                return session
            else:
                logger.debug(
                    "session_id_provided_but_not_found",
                    session_id=session_id,
                )
        
        return self.create_session(user_id)
    
    def update_session(
        self,
        session_id: str,
        conditions: Optional[TravelConditions] = None,
        plans: Optional[list] = None,
        add_message: Optional[Message] = None,
    ) -> Optional[SessionData]:
        """セッションを更新"""
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(
                "session_update_failed_not_found",
                session_id=session_id,
            )
            return None
        
        updates = []
        
        if conditions:
            session.conditions = conditions
            updates.append("conditions")
        
        if plans is not None:
            session.plans = plans
            updates.append(f"plans({len(plans)})")
        
        if add_message:
            session.messages.append(add_message)
            updates.append(f"message({add_message.role})")
        
        session.updated_at = datetime.now().isoformat()
        self._sessions[session_id] = session
        
        logger.debug(
            "session_updated",
            session_id=session_id,
            updates=updates,
            total_messages=len(session.messages),
            total_plans=len(session.plans),
        )
        
        return session
    
    def add_plans(self, session_id: str, plans: list) -> Optional[SessionData]:
        """プランを追加"""
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(
                "add_plans_failed_session_not_found",
                session_id=session_id,
            )
            return None
        
        session.plans = plans
        session.updated_at = datetime.now().isoformat()
        self._sessions[session_id] = session
        
        logger.info(
            "plans_added",
            session_id=session_id,
            plan_count=len(plans),
            plan_ids=[p.plan_id for p in plans],
        )
        
        return session
    
    def get_plan(self, session_id: str, plan_id: str) -> Optional[TravelPlan]:
        """特定のプランを取得"""
        session = self.get_session(session_id)
        if not session:
            logger.debug(
                "get_plan_session_not_found",
                session_id=session_id,
                plan_id=plan_id,
            )
            return None
        
        for plan in session.plans:
            if plan.plan_id == plan_id:
                logger.debug(
                    "plan_found",
                    session_id=session_id,
                    plan_id=plan_id,
                    label=plan.label,
                )
                return plan
        
        logger.debug(
            "plan_not_found",
            session_id=session_id,
            plan_id=plan_id,
            available_plans=[p.plan_id for p in session.plans],
        )
        
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """セッションを削除"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(
                "session_deleted",
                session_id=session_id,
                remaining_sessions=len(self._sessions),
            )
            return True
        
        logger.warning(
            "session_delete_not_found",
            session_id=session_id,
        )
        return False


# グローバルインスタンス
session_manager = SessionManager()
