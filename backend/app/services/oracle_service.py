# backend/app/services/oracle_service.py
import asyncio
import logging
import time
from uuid import UUID
from typing import Dict, Any

import oracledb

from .session_manager import SessionManager
from .db_profile_service import DbProfileService
from ..models import OracleConnectRequest, ColumnInfo, PageInfo

logger = logging.getLogger(__name__)

# Fetch formatting for different Oracle types
def _output_type_handler(cursor, name, default_type, size, precision, scale):
    """
    An output type handler for the python-oracledb driver.
    
    This function is called for each column in a query result and can be used
    to change how data is converted from Oracle types to Python types.
    
    Here, we use it to ensure data is "JSON safe" for the frontend:
    - CLOB/BLOB: Fetched as strings/bytes.
    - NUMBER: Converted to a string to avoid potential float precision errors in JavaScript.
    - DATE/TIMESTAMP: Converted to a standard ISO 8601 string format.
    """
    if default_type == oracledb.DB_TYPE_CLOB:
        return cursor.var(str, arraysize=cursor.arraysize)
    if default_type == oracledb.DB_TYPE_BLOB:
        return cursor.var(bytes, arraysize=cursor.arraysize)
    # Convert all numbers to string to avoid float precision issues in JSON
    if default_type == oracledb.DB_TYPE_NUMBER:
        return cursor.var(str, arraysize=cursor.arraysize)
    # Ensure DATE, TIMESTAMP, etc. are returned as strings in a consistent format
    if default_type in (oracledb.DB_TYPE_DATE, oracledb.DB_TYPE_TIMESTAMP, oracledb.DB_TYPE_TIMESTAMP_TZ):
         def converter(v):
            if hasattr(v, 'isoformat'):
                return v.isoformat()
            return v # Return as-is if not a date object
         return cursor.var(str, arraysize=cursor.arraysize, outconverter=converter)


class OracleService:
    """Handles Oracle database operations for sessions."""

    def __init__(self, session_manager: SessionManager, db_profile_service: DbProfileService):
        self._session_manager = session_manager
        self._db_profile_service = db_profile_service

    async def create_pool(self, req: OracleConnectRequest):
        """Creates and registers an Oracle connection pool for a session."""
        session = self._session_manager.get_session(req.sessionId)
        if not session:
            raise ValueError("Session not found.")
        if session.pool:
            logger.warning(f"[{req.sessionId}] Pool already exists. Closing old pool.")
            await asyncio.to_thread(session.pool.close)

        if req.profileAlias:
            profile = self._db_profile_service.get_profile(req.profileAlias)
            host = profile.host
            port = profile.port
            sid = profile.sid
            service_name = profile.service_name
            user = profile.user
            password = profile.password
            ssl = profile.ssl
        else:
            host = req.host
            port = req.port or 1521
            sid = req.sid
            service_name = req.serviceName
            user = req.user
            password = req.password
            ssl = req.ssl

            if not host or not user or not password:
                raise ValueError("host, user, and password are required when profileAlias is not provided.")

        # Construct a full TNS-style DSN to be explicit
        if sid:
            dsn = f"""(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={port}))(CONNECT_DATA=(SID={sid})))"""
        elif service_name:
            dsn = f"""(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={port}))(CONNECT_DATA=(SERVICE_NAME={service_name})))"""
        else:
            raise ValueError("Either serviceName or sid must be provided.")

        logger.info(
            f"[{req.sessionId}] Attempting to create Oracle pool with DSN='{dsn}', "
            f"User='{user}', SSL={ssl}, ThinMode={oracledb.is_thin_mode()}"
        )

        try:
            pool = await asyncio.to_thread(
                oracledb.create_pool,
                user=user,
                password=password,
                dsn=dsn,
                min=1,
                max=4,
                increment=1,
                timeout=300,
                disable_oob=True,
            )
            self._session_manager.set_pool_for_session(req.sessionId, pool)
            logger.info(f"[{req.sessionId}] Oracle connection pool created for DSN: {dsn}")
        except Exception as e:
            logger.error(f"[{req.sessionId}] Failed to create Oracle pool: {e}")
            raise

    async def execute_query(
        self,
        session_id: UUID,
        sql: str,
        binds: Dict[str, Any],
        timeout_sec: int,
        is_aggregation: bool = False,
    ) -> Dict[str, Any]:
        """Executes a query using the session's pool with a timeout."""
        session = self._session_manager.get_session(session_id)
        if not (session and session.pool):
            raise ValueError("Connection not established for this session.")

        start_time = time.time()
        try:
            result = await asyncio.to_thread(
                self._execute_query_sync,
                session.pool,
                sql,
                binds,
                timeout_sec,
                is_aggregation,
            )

        except oracledb.DatabaseError as e:
            error, = e.args
            # ORA-01013: user requested cancel of current operation (timeout)
            if "ORA-01013" in error.message:
                raise asyncio.TimeoutError(f"Query timed out after {timeout_sec} seconds.")
            if "DPY-3001" in error.message:
                raise RuntimeError(
                    "This Oracle database requires Native Network Encryption/Data Integrity, "
                    "which needs python-oracledb Thick mode. Configure ORACLE_CLIENT_LIB_DIR "
                    "for Oracle Instant Client and restart the backend."
                ) from e
            raise
        except Exception as e:
            logger.error(f"[{session_id}] Query execution error: {e}")
            logger.error(f"SQL: {sql}")
            logger.error(f"Binds: {binds}")
            raise

        execution_ms = (time.time() - start_time) * 1000

        result["executionMs"] = round(execution_ms, 2)

        if not is_aggregation:
            rows = result["rows"]
            page_size = binds.get("lim", 500)
            result["rowCountLimited"] = len(rows) > page_size
            if result["rowCountLimited"]:
                result["rows"] = rows[:page_size]
            result["pageInfo"] = PageInfo(page=binds.get("page", 1), pageSize=page_size)

        return result

    def _execute_query_sync(
        self,
        pool: Any,
        sql: str,
        binds: Dict[str, Any],
        timeout_sec: int,
        is_aggregation: bool,
    ) -> Dict[str, Any]:
        with pool.acquire() as conn:
            conn.outputtypehandler = _output_type_handler
            conn.call_timeout = timeout_sec * 1000

            with conn.cursor() as cursor:
                cursor.execute(sql, binds)

                if is_aggregation:
                    rows = cursor.fetchall()
                else:
                    rows = cursor.fetchmany(cursor.arraysize)

                columns = [
                    ColumnInfo(name=col[0], type=col[1].name.replace("DB_TYPE_", ""))
                    for col in cursor.description
                ]

        logger.info(f"Query returned {len(rows)} rows. First 5: {rows[:5]}")
        return {
            "columns": columns,
            "rows": rows,
        }
