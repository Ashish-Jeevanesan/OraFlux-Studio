# backend/app/services/session_manager.py
import asyncio
import logging
import time
from uuid import UUID, uuid4
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

import oracledb

logger = logging.getLogger(__name__)
IDLE_TIMEOUT_MIN = 15  # Minutes

@dataclass
class Session:
    """Represents an in-memory user session."""
    session_id: UUID
    pool: Optional[oracledb.AsyncConnectionPool] = None
    last_accessed: float = field(default_factory=time.time)

class SessionManager:
    """
    Manages the lifecycle of all user sessions in the application.

    This class is the core of the application's state management. Since the app is
    ephemeral, no session data is persisted to disk. The SessionManager holds an
    in-memory dictionary mapping a unique `sessionId` (UUID) to a `Session` object.
    Each `Session` object contains the Oracle connection pool created for that user,
    allowing subsequent API calls to reuse the same pool.

    It is also responsible for running a background "sweeper" task that periodically
    cleans up and closes connection pools for sessions that have been idle for too long.
    """
    def __init__(self):
        self._sessions: Dict[UUID, Session] = {}

    def create_session(self) -> UUID:
        """Creates a new session and returns its ID."""
        session_id = uuid4()
        self._sessions[session_id] = Session(session_id=session_id)
        logger.info(f"[{session_id}] Session created.")
        return session_id

    def get_session(self, session_id: UUID) -> Optional[Session]:
        """Retrieves a session, updating its last access time."""
        session = self._sessions.get(session_id)
        if session:
            session.last_accessed = time.time()
        else:
            logger.warning(f"[{session_id}] Attempted to access non-existent session.")
        return session

    def set_pool_for_session(self, session_id: UUID, pool: oracledb.AsyncConnectionPool):
        """Attaches a connection pool to a session."""
        session = self.get_session(session_id)
        if session:
            session.pool = pool
            logger.info(f"[{session_id}] Connection pool attached.")
        else:
            # This case might happen in a race condition. Close the orphaned pool.
            asyncio.create_task(pool.close())
            raise ValueError("Session not found. Cannot attach pool.")

    async def close_session(self, session_id: UUID):
        """Closes a session and its associated connection pool."""
        session = self._sessions.pop(session_id, None)
        if session and session.pool:
            try:
                await session.pool.close()
                logger.info(f"[{session_id}] Session and connection pool closed.")
            except Exception as e:
                logger.error(f"[{session_id}] Error closing pool: {e}")
        elif session:
            logger.info(f"[{session_id}] Session closed (no pool attached).")

    async def close_all_sessions(self):
        """Closes all active sessions and pools. (For application shutdown)."""
        session_ids = list(self._sessions.keys())
        tasks = [self.close_session(sid) for sid in session_ids]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("All sessions have been closed.")

    async def idle_sweeper(self):
        """Periodically checks for and closes idle sessions."""
        while True:
            await asyncio.sleep(60)  # Check every minute
            now = time.time()
            idle_threshold = IDLE_TIMEOUT_MIN * 60
            idle_sessions = [
                sid for sid, s in self._sessions.items()
                if (now - s.last_accessed) > idle_threshold
            ]

            if idle_sessions:
                logger.info(f"Sweeper found {len(idle_sessions)} idle session(s): {idle_sessions}")
                tasks = [self.close_session(sid) for sid in idle_sessions]
                await asyncio.gather(*tasks, return_exceptions=True)
