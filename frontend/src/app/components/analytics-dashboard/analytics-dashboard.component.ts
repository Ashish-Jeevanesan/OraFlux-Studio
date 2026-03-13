import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';

import { ApiService } from '../../services/api.service';
import { AnalyticsResponse } from '../../interfaces/api.interfaces';
import { KpiCardComponent } from '../kpi-card/kpi-card.component';
import { AnalyticsChartComponent } from '../analytics-chart/analytics-chart.component';

@Component({
  selector: 'app-analytics-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatIconModule,
    KpiCardComponent,
    AnalyticsChartComponent,
  ],
  templateUrl: './analytics-dashboard.component.html',
  styleUrls: ['./analytics-dashboard.component.scss']
})
export class AnalyticsDashboardComponent implements OnInit {
  @Input({ required: true }) baseSql!: string;
  @Input() filterLast5Years = true;
  @Output() back = new EventEmitter<void>();

  isLoading = true;
  error: string | null = null;
  dashboardData: AnalyticsResponse | null = null;

  constructor(private apiService: ApiService) { }

  ngOnInit(): void {
    this.apiService.generateAnalyticsDashboard(this.baseSql, this.filterLast5Years).subscribe({
      next: (data) => {
        this.dashboardData = data;
        this.isLoading = false;
      },
      error: (err) => {
        this.error = err.message;
        this.isLoading = false;
      }
    });
  }
}
