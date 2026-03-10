# backend/app/main.py
import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from .services.session_manager import SessionManager
from .services.oracle_service import OracleService
from .services.sql_builder import (
    build_aggregate_sql,
    build_paginated_sql,
    is_select_only_query
)
from .models import (
    SessionStartResponse,
    OracleConnectRequest,
    QueryRunRequest,
    QueryRunResponse,
    AggregateQueryRequest,
    AggregateQueryResponse,
    SessionCloseRequest,
    StatusResponse,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/oraflux.log"),
        logging.StreamHandler() # To also log to console
    ]
)
logger = logging.getLogger(__name__)

# In-memory stores
session_manager = SessionManager()
oracle_service = OracleService(session_manager)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the idle session sweeper
    task = asyncio.create_task(session_manager.idle_sweeper())
    logger.info("Idle session sweeper started.")
    yield
    # Shutdown: Stop the sweeper
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Idle session sweeper stopped.")
    # Close all remaining Oracle pools
    await session_manager.close_all_sessions()
    logger.info("All Oracle connection pools closed.")


app = FastAPI(
    title="Ephemeral Oracle Report Viewer API",
    description="An API to run ad-hoc, ephemeral SELECT queries on Oracle.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Angular dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/session/start", response_model=SessionStartResponse)
async def start_session():
    """Starts a new ephemeral session and returns a unique session ID."""
    session_id = session_manager.create_session()
    return SessionStartResponse(sessionId=session_id)


@app.post("/oracle/connect", response_model=StatusResponse)
async def connect_to_oracle(req: OracleConnectRequest):
    """Creates a connection pool for the given session and credentials."""
    try:
        await oracle_service.create_pool(req)
        return StatusResponse(ok=True)
    except Exception as e:
        logger.error(f"[{req.sessionId}] Connection failed: {e}")
        raise HTTPException(status_code=400, detail=f"Oracle connection failed: {e}")


@app.post("/query/run", response_model=QueryRunResponse)
async def run_query(req: QueryRunRequest):
    """Runs a SELECT query with server-side pagination."""
    if not is_select_only_query(req.sql):
        raise HTTPException(status_code=403, detail="Only SELECT queries are allowed.")

    paginated_sql, bind_vars = build_paginated_sql(req)

    try:
        result = await oracle_service.execute_query(
            session_id=req.sessionId,
            sql=paginated_sql,
            binds=bind_vars,
            timeout_sec=req.timeoutSec,
        )
        return QueryRunResponse(**result)
    except Exception as e:
        logger.error(f"[{req.sessionId}] Query failed: {e}")
        raise HTTPException(status_code=400, detail=f"Query execution failed: {e}")


@app.post("/query/aggregate", response_model=AggregateQueryResponse)
async def run_aggregate_query(req: AggregateQueryRequest):
    """Runs an aggregation query to generate chart data."""
    if not is_select_only_query(req.baseSql):
        raise HTTPException(
            status_code=403, detail="Only SELECT queries are allowed in the base SQL."
        )

    try:
        agg_sql, bind_vars = build_aggregate_sql(req)
        result = await oracle_service.execute_query(
            session_id=req.sessionId,
            sql=agg_sql,
            binds=bind_vars,
            timeout_sec=req.timeoutSec,
            is_aggregation=True,
        )
        return AggregateQueryResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[{req.sessionId}] Aggregation query failed: {e}")
        raise HTTPException(status_code=400, detail=f"Aggregation failed: {e}")


@app.post("/session/close", response_model=StatusResponse)
async def close_session(req: SessionCloseRequest, background_tasks: BackgroundTasks):
    """Closes the connection pool for a session."""
    background_tasks.add_task(session_manager.close_session, req.sessionId)
    return StatusResponse(ok=True)
