# backend/app/models.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any, Literal, Dict
from uuid import UUID
import re

# --- Base Models & Common Structures ---

class StatusResponse(BaseModel):
    ok: bool

class PageInfo(BaseModel):
    page: int
    pageSize: int

class ColumnInfo(BaseModel):
    name: str
    type: str

class Filter(BaseModel):
    column: str
    op: Literal["IN", "NOT IN", "EQ", "=", "NEQ", "!=", "GT", ">", "LT", "<", "GTE", ">=", "LTE", "<="]
    value: Any

    @field_validator('column')
    def validate_column_name(cls, v):
        # Basic validation to prevent SQL injection in column names
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError(f"Invalid column name format: {v}")
        return v

class OrderBy(BaseModel):
    column: str
    dir: Literal["asc", "desc"] = "asc"

    @field_validator('column')
    def validate_column_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v) and v not in ('x', 'y'): # allow 'x', 'y' for aliases
            raise ValueError(f"Invalid column name format for ordering: {v}")
        return v

# --- API Request/Response Models ---

# /session/start
class SessionStartResponse(BaseModel):
    sessionId: UUID

# /oracle/profiles
class OracleProfileSummary(BaseModel):
    alias: str
    label: Optional[str] = None

class OracleProfilesResponse(BaseModel):
    profiles: List[OracleProfileSummary]

# /oracle/connect
class OracleConnectRequest(BaseModel):
    sessionId: UUID
    profileAlias: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = 1521
    serviceName: Optional[str] = None
    sid: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = Field(None, min_length=1)
    ssl: bool = False

    @field_validator('host', 'serviceName', 'sid', 'user', 'profileAlias')
    def disallow_special_chars(cls, v):
        if v and not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError(f"Invalid characters in connection parameter: {v}")
        return v

# /query/run
class QueryRunRequest(BaseModel):
    sessionId: UUID
    sql: str
    page: int = Field(1, ge=1)
    pageSize: int = Field(500, ge=1, le=10000) # Cap at 10k
    timeoutSec: int = Field(60, ge=5, le=300)

class QueryRunResponse(BaseModel):
    columns: List[ColumnInfo]
    rows: List[List[Any]]
    pageInfo: PageInfo
    executionMs: float
    rowCountLimited: bool

# /query/aggregate
class ChartX(BaseModel):
    column: str
    role: Literal["dimension"]

    @field_validator('column')
    def validate_column_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError(f"Invalid column name format: {v}")
        return v

class ChartY(BaseModel):
    column: str
    agg: Literal["SUM", "AVG", "COUNT", "COUNT(DISTINCT)", "MIN", "MAX"]
    role: Literal["measure"]

    @field_validator('column')
    def validate_column_name(cls, v):
        # Allow '*' for COUNT(*)
        if v != '*' and not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError(f"Invalid column name format: {v}")
        return v

class ChartConfig(BaseModel):
    type: Literal["bar", "line", "pie", "histogram"]
    x: ChartX
    y: List[ChartY]
    granularity: Optional[Literal["YYYY", "Q", "MM", "DD"]] = None
    bins: int = Field(20, ge=1, le=100)

class AggregateQueryRequest(BaseModel):
    sessionId: UUID
    baseSql: str
    chart: ChartConfig
    filters: Optional[List[Filter]] = None
    topN: Optional[int] = Field(None, ge=1, le=1000)
    orderBy: Optional[List[OrderBy]] = None
    timeoutSec: int = Field(60, ge=5, le=300)

class AggregateQueryResponse(BaseModel):
    columns: List[ColumnInfo]
    rows: List[List[Any]]
    executionMs: float

# /query/drilldown
class DrilldownRequest(BaseModel):
    originalRequest: AggregateQueryRequest
    clickedValue: Any
    page: int = Field(1, ge=1)
    pageSize: int = Field(500, ge=1, le=10000)

# /session/close
class SessionCloseRequest(BaseModel):
    sessionId: UUID

# /query/intelligent-summary
class IntelligentSummaryRequest(BaseModel):
    sessionId: UUID
    detailSql: str

class SummaryReportResponse(BaseModel):
    detail: QueryRunResponse
    summary: QueryRunResponse
    title: Optional[str] = None

class ReportDetailRequest(BaseModel):
    sessionId: UUID
    baseSql: str
    selectedMonth: str
