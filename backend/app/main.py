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
    build_drilldown_sql,
    is_select_only_query
)
from .models import (
    SessionStartResponse,
    OracleConnectRequest,
    QueryRunRequest,
    QueryRunResponse,
    AggregateQueryRequest,
    AggregateQueryResponse,
    DrilldownRequest,
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

logger.info("OraFlux Studio API starting up...")

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
    title="OraFlux Studio API",
    description="An API to run ad-hoc, ephemeral SELECT queries on Oracle.",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "https://ora-flux-studio.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Health Check Endpoints ---
@app.get("/", tags=["Health Check"])
async def read_root():
    """A welcome message for the API root."""
    return {"message": "Welcome to OraFlux Studio API"}

@app.get("/health", tags=["Health Check"])
async def health_check():
    """A simple health check endpoint to verify the service is running."""
    return {"status": "ok"}


# --- API Endpoints ---
@app.post("/session/start", response_model=SessionStartResponse, tags=["Session"])
async def start_session():
    """Starts a new ephemeral session and returns a unique session ID."""
    logger.info("Received request for /session/start")
    session_id = session_manager.create_session()
    return SessionStartResponse(sessionId=session_id)


@app.post("/oracle/connect", response_model=StatusResponse, tags=["Session"])
async def connect_to_oracle(req: OracleConnectRequest):
    """Creates a connection pool for the given session and credentials."""
    logger.info(f"[{req.sessionId}] Received request for /oracle/connect")
    try:
        await oracle_service.create_pool(req)
        return StatusResponse(ok=True)
    except Exception as e:
        logger.error(f"[{req.sessionId}] Connection failed: {e}")
        raise HTTPException(status_code=400, detail=f"Oracle connection failed: {e}")


@app.post("/query/run", response_model=QueryRunResponse, tags=["Query"])
async def run_query(req: QueryRunRequest):
    """Runs a SELECT query with server-side pagination."""
    logger.info(f"[{req.sessionId}] Received request for /query/run")
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


@app.post("/query/aggregate", response_model=AggregateQueryResponse, tags=["Query"])
async def run_aggregate_query(req: AggregateQueryRequest):
    """Runs an aggregation query to generate chart data."""
    logger.info(f"[{req.sessionId}] Received request for /query/aggregate")
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


@app.post("/query/drilldown", response_model=QueryRunResponse, tags=["Query"])
async def run_drilldown_query(req: DrilldownRequest):
    """Runs a paginated query to get the raw data for a chart segment."""
    logger.info(f"[{req.originalRequest.sessionId}] Received request for /query/drilldown")
    if not is_select_only_query(req.originalRequest.baseSql):
        raise HTTPException(
            status_code=403, detail="Only SELECT queries are allowed in the base SQL."
        )

    try:
        drilldown_sql, bind_vars = build_drilldown_sql(req)
        
        result = await oracle_service.execute_query(
            session_id=req.originalRequest.sessionId,
            sql=drilldown_sql,
            binds=bind_vars,
            timeout_sec=req.originalRequest.timeoutSec,
        )
        # We need to manually add the page to the result for the dialog paginator
        result['pageInfo']['page'] = req.page
        return QueryRunResponse(**result)
    except Exception as e:
        logger.error(f"[{req.originalRequest.sessionId}] Drilldown query failed: {e}")
        raise HTTPException(status_code=400, detail=f"Drilldown query execution failed: {e}")


@app.post("/session/close", response_model=StatusResponse, tags=["Session"])
async def close_session(req: SessionCloseRequest, background_tasks: BackgroundTasks):
    """Closes the connection pool for a session."""
    logger.info(f"[{req.sessionId}] Received request for /session/close")
    background_tasks.add_task(session_manager.close_session, req.sessionId)
    return StatusResponse(ok=True)
