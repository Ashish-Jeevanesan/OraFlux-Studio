# backend/app/services/oracle_service.py
import asyncio
import logging
import time
from uuid import UUID
from typing import Dict, Any

import oracledb
from oracledb import AsyncConnectionPool

from .session_manager import SessionManager
from ..models import OracleConnectRequest, ColumnInfo, PageInfo

logger = logging.getLogger(__name__)

# Fetch formatting for different Oracle types
def _output_type_handler(cursor, name, default_type, size, precision, scale):
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

    def __init__(self, session_manager: SessionManager):
        self._session_manager = session_manager

    async def create_pool(self, req: OracleConnectRequest):
        """Creates and registers an Oracle connection pool for a session."""
        session = self._session_manager.get_session(req.sessionId)
        if not session:
            raise ValueError("Session not found.")
        if session.pool:
            logger.warning(f"[{req.sessionId}] Pool already exists. Closing old pool.")
            await session.pool.close()

        # Construct a full TNS-style DSN to be explicit
        if req.sid:
            dsn = f"""(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST={req.host})(PORT={req.port}))(CONNECT_DATA=(SID={req.sid})))"""
        elif req.serviceName:
            dsn = f"""(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST={req.host})(PORT={req.port}))(CONNECT_DATA=(SERVICE_NAME={req.serviceName})))"""
        else:
            raise ValueError("Either serviceName or sid must be provided.")

        logger.info(f"[{req.sessionId}] Attempting to create Oracle pool with DSN='{dsn}', User='{req.user}', SSL={req.ssl}")

        try:
            pool: AsyncConnectionPool = oracledb.create_pool_async(
                user=req.user,
                password=req.password,
                dsn=dsn,
                min=1,
                max=4,
                # Thin mode is default, but explicitly state for clarity
                disable_oob=True,
                # Set SSL params if req.ssl is True (requires wallet files)
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
            async with session.pool.acquire() as conn:
                conn.outputtypehandler = _output_type_handler
                async with conn.cursor() as cursor:
                    # Set a timeout on the connection for this specific execution
                    # call_timeout is in milliseconds
                    conn.call_timeout = timeout_sec * 1000

                    await cursor.execute(sql, binds)
                    
                    if is_aggregation:
                        rows = await cursor.fetchall()
                    else:
                        # Fetch one more than pageSize to check if there are more rows
                        rows = await cursor.fetchmany(cursor.arraysize)

                    columns = [
                        ColumnInfo(name=col[0], type=col[1].name.replace('DB_TYPE_', ''))
                        for col in cursor.description
                    ]

                    # Log the first 5 rows for inspection
                    logger.info(f"Query returned {len(rows)} rows. First 5: {rows[:5]}")

        except oracledb.DatabaseError as e:
            error, = e.args
            # ORA-01013: user requested cancel of current operation (timeout)
            if "ORA-01013" in error.message:
                raise asyncio.TimeoutError(f"Query timed out after {timeout_sec} seconds.")
            raise
        except Exception as e:
            logger.error(f"[{session_id}] Query execution error: {e}")
            logger.error(f"SQL: {sql}")
            logger.error(f"Binds: {binds}")
            raise

        execution_ms = (time.time() - start_time) * 1000

        result = {
            "columns": columns,
            "rows": rows,
            "executionMs": round(execution_ms, 2),
        }

        if not is_aggregation:
            page_size = binds.get('lim', 500)
            result["rowCountLimited"] = len(rows) > page_size
            if result["rowCountLimited"]:
                 result["rows"] = rows[:page_size] # Trim the extra row
            result["pageInfo"] = PageInfo(page=binds.get('page', 1), pageSize=page_size)


        return result
