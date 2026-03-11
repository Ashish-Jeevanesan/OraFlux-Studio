import { Component, Input, Output, EventEmitter, OnInit, ViewChild, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatSort, MatSortModule } from '@angular/material/sort';

import { ApiService } from '../../services/api.service';
import { ColumnInfo } from '../../interfaces/api.interfaces';

@Component({
  selector: 'app-summary-report',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatTableModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatSortModule,
  ],
  templateUrl: './summary-report.component.html',
  styleUrls: ['./summary-report.component.scss']
})
export class SummaryReportComponent implements OnInit, AfterViewInit {
  @Input({ required: true }) baseSql!: string;
  @Output() back = new EventEmitter<void>();

  @ViewChild(MatSort) sort!: MatSort;

  isLoadingSummary = true;
  isLoadingDetail = false;
  errorMessage: string | null = null;
  
  reportTitle = "Summary Report";

  // Summary Table
  summaryDataSource = new MatTableDataSource<any>();
  summaryColumns: ColumnInfo[] = [];
  summaryDisplayedColumns: string[] = [];

  // Detail Table
  detailDataSource = new MatTableDataSource<any>();
  detailColumns: ColumnInfo[] = [];
  detailDisplayedColumns: string[] = [];
  selectedMonth: string | null = null;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.generateSummary();
  }

  ngAfterViewInit() {
    this.detailDataSource.sort = this.sort;
  }

  generateSummary() {
    this.isLoadingSummary = true;
    this.errorMessage = null;
    this.detailDataSource.data = []; // Clear detail data
    this.selectedMonth = null;

    this.apiService.getIntelligentSummaryReport(this.baseSql).subscribe({
      next: (response) => {
        if (response.title) {
          this.reportTitle = response.title;
        }

        // --- Summary Data ---
        this.summaryColumns = response.summary.columns;
        this.summaryDisplayedColumns = response.summary.columns.map(c => c.name);
        this.summaryDataSource.data = response.summary.rows.map(rowArray => {
          const rowObject: { [key: string]: any } = {};
          this.summaryDisplayedColumns.forEach((colName, index) => {
            rowObject[colName] = rowArray[index];
          });
          return rowObject;
        });

        // We also get the detail columns from the initial call
        this.detailColumns = response.detail.columns;
        this.detailDisplayedColumns = response.detail.columns.map(c => c.name);

        this.isLoadingSummary = false;
      },
      error: (err) => {
        this.errorMessage = err.message;
        this.isLoadingSummary = false;
      },
    });
  }

  onMonthClick(monthRow: any) {
    const month = monthRow[this.summaryDisplayedColumns[0]];
    this.selectedMonth = month;
    this.isLoadingDetail = true;
    this.errorMessage = null;

    this.apiService.getReportDetailForMonth(this.baseSql, month).subscribe({
      next: (response) => {
        this.detailDataSource.data = response.rows.map(rowArray => {
          const rowObject: { [key: string]: any } = {};
          this.detailDisplayedColumns.forEach((colName, index) => {
            rowObject[colName] = rowArray[index];
          });
          return rowObject;
        });
        // Set the sort after the data is loaded
        this.detailDataSource.sort = this.sort;
        const dateColumn = this.detailColumns.find(c => c.type === 'DATE' || c.type === 'TIMESTAMP');
        if (this.sort && dateColumn) {
          this.sort.sort({ id: dateColumn.name, start: 'desc', disableClear: false });
        }

        this.isLoadingDetail = false;
      },
      error: (err) => {
        this.errorMessage = err.message;
        this.isLoadingDetail = false;
      },
    });
  }
}
