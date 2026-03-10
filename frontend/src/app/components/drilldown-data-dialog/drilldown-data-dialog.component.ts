import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { finalize } from 'rxjs/operators';

// Material Components
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';

import { ApiService } from '../../services/api.service';
import { QueryRunResponse, ColumnInfo, DrilldownRequest } from '../../interfaces/api.interfaces';

export interface DrilldownData {
  initialResponse: QueryRunResponse;
  drilldownRequest: Omit<DrilldownRequest, 'page' | 'pageSize'>;
}

@Component({
  selector: 'app-drilldown-data-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatTableModule,
    MatPaginatorModule,
    MatProgressSpinnerModule,
    MatButtonModule
  ],
  templateUrl: './drilldown-data-dialog.component.html',
  styleUrls: ['./drilldown-data-dialog.component.scss']
})
export class DrilldownDataDialogComponent {
  isLoading = false;
  
  // Table properties
  dataSource = new MatTableDataSource<any[]>();
  displayedColumns: string[] = [];
  columns: ColumnInfo[] = [];
  
  // Paginator properties
  totalRows = 0;
  pageSize = 100; // Smaller page size for dialog
  currentPage = 0;
  pageSizeOptions = [50, 100, 200];

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: DrilldownData,
    private apiService: ApiService
  ) {
    // Initialize with the data from the first API call
    this.handleQueryResponse(data.initialResponse);
    this.currentPage = data.initialResponse.pageInfo.page - 1;
  }

  handlePageEvent(event: PageEvent) {
    this.currentPage = event.pageIndex;
    this.pageSize = event.pageSize;
    this.fetchDrilldownData();
  }

  fetchDrilldownData() {
    this.isLoading = true;
    const drilldownReq: DrilldownRequest = {
      ...this.data.drilldownRequest,
      page: this.currentPage + 1,
      pageSize: this.pageSize
    };

    this.apiService.runDrilldownQuery(drilldownReq)
      .pipe(finalize(() => this.isLoading = false))
      .subscribe(response => this.handleQueryResponse(response));
  }

  private handleQueryResponse(response: QueryRunResponse) {
    this.columns = response.columns;
    this.displayedColumns = response.columns.map(c => c.name);
    this.dataSource.data = response.rows;

    const currentResultsLength = response.rows.length;
    if (response.rowCountLimited) {
      this.totalRows = (this.currentPage + 2) * this.pageSize;
    } else {
      this.totalRows = this.currentPage * this.pageSize + currentResultsLength;
    }
  }

  getCellValue(row: any[], index: number): any {
    return row[index];
  }
}
