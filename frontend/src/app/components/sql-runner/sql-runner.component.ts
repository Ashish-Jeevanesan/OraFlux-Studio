// frontend/src/app/components/sql-runner/sql-runner.component.ts
import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { finalize } from 'rxjs/operators';

// Angular Material Modules
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatCheckboxModule } from '@angular/material/checkbox';

import { ApiService } from '../../services/api.service';
import { QueryRunResponse, ColumnInfo } from '../../interfaces/api.interfaces';

@Component({
  selector: 'app-sql-runner',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatTableModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatCheckboxModule,
  ],
  templateUrl: './sql-runner.component.html',
  styleUrls: ['./sql-runner.component.scss'],
})
export class SqlRunnerComponent {
  @Output() querySuccess = new EventEmitter<{ sql: string, columns: ColumnInfo[] }>();
  @Output() generateReport = new EventEmitter<void>();

  sqlQuery = 'SELECT * FROM t501_order';
  filterLast5Years = true;
  isLoading = false;
  errorMessage: string | null = null;
  
  // Table properties
  dataSource = new MatTableDataSource<any[]>();
  displayedColumns: string[] = [];
  columns: ColumnInfo[] = [];
  
  // Paginator properties
  totalRows = 0;
  pageSize = 500;
  currentPage = 0;
  pageSizeOptions = [50, 100, 500, 1000];
  executionTime = 0;
  rowCountLimited = false;

  constructor(private apiService: ApiService, private snackBar: MatSnackBar) {}

  runQuery() {
    if (!this.sqlQuery) return;

    this.isLoading = true;
    this.errorMessage = null;

    const finalQuery = this.getTransformedQuery();

    this.apiService
      .runQuery({
        sql: finalQuery,
        page: this.currentPage + 1,
        pageSize: this.pageSize,
      })
      .pipe(finalize(() => (this.isLoading = false)))
      .subscribe({
        next: (response) => this.handleQueryResponse(response),
        error: (err) => {
          this.errorMessage = err.message;
          this.dataSource.data = [];
          this.displayedColumns = [];
        },
      });
  }

  private getTransformedQuery(): string {
    if (!this.filterLast5Years) {
      return this.sqlQuery;
    }

    const query = this.sqlQuery.trim();
    const upperCaseQuery = query.toUpperCase();

    // Heuristic: Find a suitable date column from a prioritized list
    const dateColumnCandidates = [
      'C501_ORDER_DATE', 
      'C501_LAST_UPDATED_DATE', 
      'CREATED_DATE', 
      'UPDATE_DATE',
      'LAST_UPDATED'
    ];
    
    let dateColumn: string | null = null;
    for (const candidate of dateColumnCandidates) {
      if (upperCaseQuery.includes(candidate)) {
        dateColumn = candidate;
        break;
      }
    }

    if (!dateColumn) {
      this.snackBar.open("Could not automatically determine a date column for the 5-year filter.", "Warning", { duration: 3000 });
      return query; // Return original query if no suitable column is found
    }

    const fiveYearsAgo = new Date();
    fiveYearsAgo.setFullYear(fiveYearsAgo.getFullYear() - 5);
    const dateString = fiveYearsAgo.toISOString().split('T')[0];

    const dateCondition = `${dateColumn} >= TO_DATE('${dateString}', 'YYYY-MM-DD')`;

    // Very basic check to see if there's a WHERE clause
    const whereIndex = upperCaseQuery.lastIndexOf('WHERE');
    const orderByIndex = upperCaseQuery.lastIndexOf('ORDER BY');

    let modifiedQuery = query;

    if (whereIndex > -1) {
      // Append with AND
      if (orderByIndex > whereIndex) {
        modifiedQuery = query.slice(0, orderByIndex) + ` AND ${dateCondition} ` + query.slice(orderByIndex);
      } else {
        modifiedQuery = query + ` AND ${dateCondition}`;
      }
    } else {
      // Add a new WHERE clause
       if (orderByIndex > -1) {
        modifiedQuery = query.slice(0, orderByIndex) + ` WHERE ${dateCondition} ` + query.slice(orderByIndex);
      } else {
        modifiedQuery = query + ` WHERE ${dateCondition}`;
      }
    }
    
    return modifiedQuery;
  }

  handlePageEvent(event: PageEvent) {
    this.currentPage = event.pageIndex;
    this.pageSize = event.pageSize;
    this.runQuery();
  }

  private handleQueryResponse(response: QueryRunResponse) {
    this.executionTime = response.executionMs;
    this.rowCountLimited = response.rowCountLimited;
    
    this.columns = response.columns;
    this.displayedColumns = response.columns.map((c) => c.name);
    this.dataSource.data = response.rows;
    
    // The backend doesn't know the total count for performance reasons.
    // We simulate it for the paginator.
    const currentResultsLength = response.rows.length;
    if (response.rowCountLimited) {
      // There are more pages
      this.totalRows = (this.currentPage + 2) * this.pageSize;
    } else {
      // This is the last page
      this.totalRows = this.currentPage * this.pageSize + currentResultsLength;
    }

    if (currentResultsLength > 0) {
      this.querySuccess.emit({ sql: this.sqlQuery, columns: this.columns });
    }

    this.snackBar.open(
      `Query executed in ${this.executionTime}ms.`,
      'Close',
      { duration: 3000 }
    );
  }

  // Helper to get a value from a row based on column index
  getCellValue(row: any[], index: number): any {
    return row[index];
  }
}
