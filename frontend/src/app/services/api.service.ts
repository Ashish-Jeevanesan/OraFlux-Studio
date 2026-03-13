// frontend/src/app/services/api.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../environments/environment';
import { SessionService } from './session.service';
import {
  OracleConnectRequest,
  OracleProfilesResponse,
  QueryRunRequest,
  AggregateQueryRequest,
  DrilldownRequest,
  IntelligentSummaryRequest,
  ReportDetailRequest,
  AnalyticsRequest,
  NlGenerateSqlRequest,
  StatusResponse,
  QueryRunResponse,
  AggregateQueryResponse,
  SummaryReportResponse,
  AnalyticsResponse,
  NlGenerateSqlResponse,
} from '../interfaces/api.interfaces';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient, private sessionService: SessionService) {}

  /**
   * Connects to the Oracle database.
   * @param connectDetails - The connection details.
   */
  connectToOracle(connectDetails: Omit<OracleConnectRequest, 'sessionId'>): Observable<StatusResponse> {
    const payload: OracleConnectRequest = {
      ...connectDetails,
      sessionId: this.sessionService.getSessionId(),
    };
    return this.http
      .post<StatusResponse>(`${this.apiUrl}/oracle/connect`, payload)
      .pipe(catchError(this.handleError));
  }

  /**
   * Gets available backend-managed Oracle profile aliases.
   */
  getOracleProfiles(): Observable<OracleProfilesResponse> {
    return this.http
      .get<OracleProfilesResponse>(`${this.apiUrl}/oracle/profiles`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Runs a SQL query.
   * @param queryDetails - The query details.
   */
  runQuery(queryDetails: Omit<QueryRunRequest, 'sessionId'>): Observable<QueryRunResponse> {
    const payload: QueryRunRequest = {
      ...queryDetails,
      sessionId: this.sessionService.getSessionId(),
    };
    return this.http
      .post<QueryRunResponse>(`${this.apiUrl}/query/run`, payload)
      .pipe(catchError(this.handleError));
  }

  /**
   * Runs an aggregate query for chart data.
   * @param aggDetails - The aggregation details.
   */
  runAggregateQuery(aggDetails: Omit<AggregateQueryRequest, 'sessionId'>): Observable<AggregateQueryResponse> {
    const payload: AggregateQueryRequest = {
      ...aggDetails,
      sessionId: this.sessionService.getSessionId(),
    };
    return this.http
      .post<AggregateQueryResponse>(`${this.apiUrl}/query/aggregate`, payload)
      .pipe(catchError(this.handleError));
  }

  /**
   * Runs a drilldown query to get raw data for a chart segment.
   * @param drilldownDetails - The drilldown details.
   */
  runDrilldownQuery(drilldownDetails: DrilldownRequest): Observable<QueryRunResponse> {
    // The sessionId is already inside the originalRequest object in the payload
    return this.http
      .post<QueryRunResponse>(`${this.apiUrl}/query/drilldown`, drilldownDetails)
      .pipe(catchError(this.handleError));
  }

  /**
   * Gets data for an intelligent summary/detail report.
   */
  getIntelligentSummaryReport(detailSql: string, granularity: 'month' | 'week' | 'year' = 'month'): Observable<SummaryReportResponse> {
    const payload: IntelligentSummaryRequest = {
      detailSql,
      granularity,
      sessionId: this.sessionService.getSessionId(),
    };
    return this.http
      .post<SummaryReportResponse>(`${this.apiUrl}/query/intelligent-summary`, payload)
      .pipe(catchError(this.handleError));
  }

  getReportDetail(baseSql: string, selectedValue: string, granularity: 'month' | 'week' | 'year'): Observable<QueryRunResponse> {
    const payload: ReportDetailRequest = {
      baseSql,
      selectedValue,
      granularity,
      sessionId: this.sessionService.getSessionId(),
    };
    return this.http
      .post<QueryRunResponse>(`${this.apiUrl}/query/report-detail`, payload)
      .pipe(catchError(this.handleError));
  }

  generateAnalyticsDashboard(baseSql: string, filterLast5Years: boolean): Observable<AnalyticsResponse> {
    const payload: AnalyticsRequest = {
      baseSql,
      filterLast5Years,
      sessionId: this.sessionService.getSessionId(),
    };
    return this.http
      .post<AnalyticsResponse>(`${this.apiUrl}/analytics/generate`, payload)
      .pipe(catchError(this.handleError));
  }

  generateSqlFromNl(text: string): Observable<NlGenerateSqlResponse> {
    const payload: NlGenerateSqlRequest = {
      text,
      sessionId: this.sessionService.getSessionId(),
    };
    return this.http
      .post<NlGenerateSqlResponse>(`${this.apiUrl}/query/generate-from-nl`, payload)
      .pipe(catchError(this.handleError));
  }

  /**
   * Centralized error handler for API calls.
   */
  private handleError(error: HttpErrorResponse) {
    let errorMessage = 'An unknown error occurred!';
    if (error.error instanceof ErrorEvent) {
      // A client-side or network error occurred.
      errorMessage = `Error: ${error.error.message}`;
    } else {
      // The backend returned an unsuccessful response code.
      // The response body may contain clues as to what went wrong.
      if (error.error && error.error.detail) {
        errorMessage = `Error: ${error.error.detail}`;
      } else {
        errorMessage = `Error Code: ${error.status}
Message: ${error.message}`;
      }
    }
    console.error(errorMessage);
    return throwError(() => new Error(errorMessage));
  }
}
