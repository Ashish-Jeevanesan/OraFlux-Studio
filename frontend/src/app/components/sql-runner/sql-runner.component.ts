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
  ],
  templateUrl: './sql-runner.component.html',
  styleUrls: ['./sql-runner.component.scss'],
})
export class SqlRunnerComponent {
  @Output() querySuccess = new EventEmitter<{ sql: string, columns: ColumnInfo[] }>();

  sqlQuery = 'SELECT * FROM employees';
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

    this.apiService
      .runQuery({
        sql: this.sqlQuery,
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
