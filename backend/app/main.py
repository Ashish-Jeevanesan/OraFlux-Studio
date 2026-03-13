# backend/app/main.py
import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from .services.session_manager import SessionManager
from .services.oracle_driver import initialize_oracle_client
from .services.oracle_service import OracleService
from .services.db_profile_service import DbProfileService
from .services import intelligent_summary_service
from .services.analytics_service import AnalyticsService
from .services.nl_to_sql_service import NlToSqlService
from .services.sql_builder import (
    build_aggregate_sql,
    build_paginated_sql,
    build_drilldown_sql,
    is_select_only_query
)
from .models import (
    SessionStartResponse,
    OracleConnectRequest,
    OracleProfilesResponse,
    OracleProfileSummary,
    QueryRunRequest,
    QueryRunResponse,
    AggregateQueryRequest,
    AggregateQueryResponse,
    DrilldownRequest,
    SessionCloseRequest,
    StatusResponse,
    IntelligentSummaryRequest,
    SummaryReportResponse,
    ReportDetailRequest,
    AnalyticsRequest,
    AnalyticsResponse,
    NlGenerateSqlRequest,
    NlGenerateSqlResponse,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/oraflux.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("OraFlux Studio API starting up...")
initialize_oracle_client()

# In-memory stores
session_manager = SessionManager()
db_profile_service = DbProfileService()
oracle_service = OracleService(session_manager, db_profile_service)
analytics_service = AnalyticsService(oracle_service)
nl_to_sql_service = NlToSqlService(oracle_service)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(session_manager.idle_sweeper())
    logger.info("Idle session sweeper started.")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Idle session sweeper stopped.")
    await session_manager.close_all_sessions()
    logger.info("All Oracle connection pools closed.")


app = FastAPI(
    title="OraFlux Studio API",
    description="An API to run ad-hoc, ephemeral SELECT queries on Oracle.",
    version="1.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "https://ora-flux-studio.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Health Check"])
async def read_root():
    return {"message": "Welcome to OraFlux Studio API"}

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok"}

@app.post("/session/start", response_model=SessionStartResponse, tags=["Session"])
async def start_session():
    logger.info("Received request for /session/start")
    session_id = session_manager.create_session()
    return SessionStartResponse(sessionId=session_id)

@app.post("/oracle/connect", response_model=StatusResponse, tags=["Session"])
async def connect_to_oracle(req: OracleConnectRequest):
    logger.info(f"[{req.sessionId}] Received request for /oracle/connect")
    try:
        await oracle_service.create_pool(req)
        return StatusResponse(ok=True)
    except Exception as e:
        logger.error(f"[{req.sessionId}] Connection failed: {e}")
        raise HTTPException(status_code=400, detail=f"Oracle connection failed: {e}")

@app.get("/oracle/profiles", response_model=OracleProfilesResponse, tags=["Session"])
async def list_oracle_profiles():
    profiles = [
        OracleProfileSummary(alias=p.alias, label=p.label)
        for p in db_profile_service.list_profiles()
    ]
    return OracleProfilesResponse(profiles=profiles)

@app.post("/query/generate-from-nl", response_model=NlGenerateSqlResponse, tags=["Query"])
async def generate_sql_from_natural_language(req: NlGenerateSqlRequest):
    """
    Takes a natural language text prompt and uses an LLM to generate a SQL query.
    """
    logger.info(f"[{req.sessionId}] Received request for /query/generate-from-nl")
    try:
        generated_sql = await nl_to_sql_service.generate_sql_from_text(req.text, req.sessionId)
        return NlGenerateSqlResponse(sql=generated_sql)
    except Exception as e:
        logger.error(f"[{req.sessionId}] NL-to-SQL generation failed: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to generate SQL from text: {e}")

@app.post("/query/run", response_model=QueryRunResponse, tags=["Query"])
async def run_query(req: QueryRunRequest):
    logger.info(f"[{req.sessionId}] Received request for /query/run")
    if not is_select_only_query(req.sql):
        raise HTTPException(status_code=403, detail="Only SELECT queries are allowed.")
    paginated_sql, bind_vars = build_paginated_sql(req)
    logger.info(f"[{req.sessionId}] Executing paginated query: {paginated_sql}")
    try:
        result = await oracle_service.execute_query(
            session_id=req.sessionId,
            sql=paginated_sql,
            binds=bind_vars,
            timeout_sec=req.timeoutSec,
        )
        num_rows = len(result.get('rows', []))
        logger.info(f"[{req.sessionId}] Query returned {num_rows} rows.")
        return QueryRunResponse(**result)
    except Exception as e:
        logger.error(f"[{req.sessionId}] Query failed: {e}")
        raise HTTPException(status_code=400, detail=f"Query execution failed: {e}")

@app.post("/query/aggregate", response_model=AggregateQueryResponse, tags=["Query"])
async def run_aggregate_query(req: AggregateQueryRequest):
    logger.info(f"[{req.sessionId}] Received request for /query/aggregate")
    if not is_select_only_query(req.baseSql):
        raise HTTPException(status_code=403, detail="Only SELECT queries are allowed.")
    try:
        agg_sql, bind_vars = build_aggregate_sql(req)
        logger.info(f"[{req.sessionId}] Executing aggregate query: {agg_sql}")
        result = await oracle_service.execute_query(
            session_id=req.sessionId,
            sql=agg_sql,
            binds=bind_vars,
            timeout_sec=req.timeoutSec,
            is_aggregation=True,
        )
        num_rows = len(result.get('rows', []))
        logger.info(f"[{req.sessionId}] Aggregation query returned {num_rows} rows.")
        return AggregateQueryResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[{req.sessionId}] Aggregation query failed: {e}")
        raise HTTPException(status_code=400, detail=f"Aggregation failed: {e}")

@app.post("/query/drilldown", response_model=QueryRunResponse, tags=["Query"])
async def run_drilldown_query(req: DrilldownRequest):
    logger.info(f"[{req.originalRequest.sessionId}] Received request for /query/drilldown")
    if not is_select_only_query(req.originalRequest.baseSql):
        raise HTTPException(status_code=403, detail="Only SELECT queries are allowed.")
    try:
        drilldown_sql, bind_vars = build_drilldown_sql(req)
        logger.info(f"[{req.originalRequest.sessionId}] Executing drilldown query: {drilldown_sql}")
        result = await oracle_service.execute_query(
            session_id=req.originalRequest.sessionId,
            sql=drilldown_sql,
            binds=bind_vars,
            timeout_sec=req.originalRequest.timeoutSec,
        )
        num_rows = len(result.get('rows', []))
        logger.info(f"[{req.originalRequest.sessionId}] Drilldown query returned {num_rows} rows.")
        result['pageInfo']['page'] = req.page
        return QueryRunResponse(**result)
    except Exception as e:
        logger.error(f"[{req.originalRequest.sessionId}] Drilldown query failed: {e}")
        raise HTTPException(status_code=400, detail=f"Drilldown query execution failed: {e}")

@app.post("/query/intelligent-summary", response_model=SummaryReportResponse, tags=["Query"])
async def run_intelligent_summary(req: IntelligentSummaryRequest):
    logger.info(f"[{req.sessionId}] Received request for /query/intelligent-summary with granularity '{req.granularity}'")
    if not is_select_only_query(req.detailSql):
        raise HTTPException(status_code=403, detail="Only SELECT queries are allowed.")
    try:
        table_names = intelligent_summary_service.extract_table_names(req.detailSql)
        schemas = await oracle_service.get_table_schemas(req.sessionId, table_names)
        summary_sql, report_title = intelligent_summary_service.generate_summary_sql(req.detailSql, schemas, req.granularity)
        logger.info(f"[{req.sessionId}] Generated Summary SQL: {summary_sql}")
        detail_result, summary_result = await asyncio.gather(
            oracle_service.execute_query(session_id=req.sessionId, sql=req.detailSql, binds={}, timeout_sec=120),
            oracle_service.execute_query(session_id=req.sessionId, sql=summary_sql, binds={}, timeout_sec=120)
        )
        return SummaryReportResponse(
            detail=QueryRunResponse(**detail_result),
            summary=QueryRunResponse(**summary_result),
            title=report_title
        )
    except Exception as e:
        logger.error(f"[{req.sessionId}] Intelligent summary failed: {e}")
        raise HTTPException(status_code=400, detail=f"Intelligent summary failed: {e}")

@app.post("/query/report-detail", response_model=QueryRunResponse, tags=["Query"])
async def get_report_detail(req: ReportDetailRequest):
    logger.info(f"[{req.sessionId}] Received request for report detail for {req.granularity}: {req.selectedValue}")
    if not is_select_only_query(req.baseSql):
        raise HTTPException(status_code=403, detail="Only SELECT queries are allowed.")
    try:
        table_names = intelligent_summary_service.extract_table_names(req.baseSql)
        schemas = await oracle_service.get_table_schemas(req.sessionId, table_names)
        date_col = intelligent_summary_service._find_primary_date_column(schemas)
        if not date_col:
            raise HTTPException(status_code=400, detail="Could not determine date column for filtering.")
        granularity_map = {
            "month": {"trunc": "MM", "format": "Mon YYYY"},
            "week": {"trunc": "IW", "format": 'YYYY - "WW"'},
            "year": {"trunc": "YYYY", "format": "YYYY"},
        }
        if req.granularity not in granularity_map:
            raise ValueError(f"Unsupported granularity: {req.granularity}")
        trunc_format = granularity_map[req.granularity]["trunc"]
        char_format = granularity_map[req.granularity]["format"]
        filtered_sql = f"""
            SELECT * FROM (
                {req.baseSql}
            )
            WHERE TO_CHAR(TRUNC({date_col}, '{trunc_format}'), '{char_format}') = :selected_value
        """
        binds = {"selected_value": req.selectedValue}
        logger.info(f"[{req.sessionId}] Executing detail for month query: {filtered_sql}")
        result = await oracle_service.execute_query(
            session_id=req.sessionId,
            sql=filtered_sql,
            binds=binds,
            timeout_sec=120,
        )
        return QueryRunResponse(**result)
    except Exception as e:
        logger.error(f"[{req.sessionId}] Report detail query failed: {e}")
        raise HTTPException(status_code=400, detail=f"Report detail query failed: {e}")

@app.post("/analytics/generate", response_model=AnalyticsResponse, tags=["Analytics"])
async def generate_analytics_dashboard(req: AnalyticsRequest):
    logger.info(f"[{req.sessionId}] Received request for /analytics/generate")
    if not is_select_only_query(req.baseSql):
        raise HTTPException(status_code=403, detail="Only SELECT queries are allowed.")
    try:
        dashboard_data = await analytics_service.generate_dashboard(req.baseSql, req.sessionId, req.filterLast5Years)
        return AnalyticsResponse(**dashboard_data)
    except Exception as e:
        logger.error(f"[{req.sessionId}] Analytics dashboard generation failed: {e}")
        raise HTTPException(status_code=400, detail=f"Analytics generation failed: {e}")

@app.post("/session/close", response_model=StatusResponse, tags=["Session"])
async def close_session(req: SessionCloseRequest, background_tasks: BackgroundTasks):
    logger.info(f"[{req.sessionId}] Received request for /session/close")
    background_tasks.add_task(session_manager.close_session, req.sessionId)
    return StatusResponse(ok=True)
