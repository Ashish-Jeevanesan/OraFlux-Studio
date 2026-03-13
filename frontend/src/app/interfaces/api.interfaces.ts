// frontend/src/app/interfaces/api.interfaces.ts

// Represents the structure of a column's metadata from the backend
export interface ColumnInfo {
  name: string;
  type: string;
}

// Represents pagination information from the backend
export interface PageInfo {
  page: number;
  pageSize: number;
}

// --- API Request Payloads ---

export interface OracleConnectRequest {
  profileAlias?: string;
  host?: string;
  port?: number;
  serviceName?: string;
  sid?: string;
  user?: string;
  password?: string;
  ssl: boolean;
  sessionId: string;
}

export interface OracleProfileSummary {
  alias: string;
  label?: string;
}

export interface OracleProfilesResponse {
  profiles: OracleProfileSummary[];
}

export interface QueryRunRequest {
  sql: string;
  page?: number;
  pageSize?: number;
  timeoutSec?: number;
  sessionId: string;
}

export interface ChartX {
    column: string;
    role: "dimension";
}

export interface ChartY {
    column: string;
    agg: "SUM" | "AVG" | "COUNT" | "COUNT(DISTINCT)" | "MIN" | "MAX";
    role: "measure";
}

export interface ChartConfig {
    type: "bar" | "line" | "pie" | "histogram";
    x: ChartX;
    y: ChartY[];
    granularity?: "YYYY" | "Q" | "MM" | "DD";
    bins?: number;
}

export interface Filter {
    column: string;
    op: "IN" | "NOT IN" | "=" | "!=" | ">" | "<" | ">=" | "<=";
    value: any;
}

export interface OrderBy {
    column: string;
    dir: "asc" | "desc";
}

export interface AggregateQueryRequest {
    baseSql: string;
    chart: ChartConfig;
    filters?: Filter[];
    topN?: number;
    orderBy?: OrderBy[];
    timeoutSec?: number;
    sessionId: string;
}

export interface DrilldownRequest {
    originalRequest: Omit<AggregateQueryRequest, 'sessionId'>;
    clickedValue: any;
    page: number;
    pageSize: number;
}

export interface IntelligentSummaryRequest {
  sessionId: string;
  detailSql: string;
  granularity?: 'month' | 'week' | 'year';
}

export interface ReportDetailRequest {
  sessionId: string;
  baseSql: string;
  selectedValue: string;
  granularity: 'month' | 'week' | 'year';
}

export interface AnalyticsRequest {
  sessionId: string;
  baseSql: string;
  filterLast5Years?: boolean;
}


// --- API Response Payloads ---

export interface StatusResponse {
  ok: boolean;
  detail?: string; // Error detail from backend
}

export interface QueryRunResponse {
  columns: ColumnInfo[];
  rows: any[][];
  pageInfo: PageInfo;
  executionMs: number;
  rowCountLimited: boolean;
}

export interface AggregateQueryResponse {
  columns: {name: 'X' | 'Y'}[];
  rows: (string | number)[][];
  executionMs: number;
}

export interface SummaryReportResponse {
  detail: QueryRunResponse;
  summary: QueryRunResponse;
  title?: string;
}

export interface AnalyticsResponse {
  title: string;
  kpis: any[];
  charts: any[];
}

export interface NlGenerateSqlRequest {
  sessionId: string;
  text: string;
}

export interface NlGenerateSqlResponse {
  sql: string;
}
