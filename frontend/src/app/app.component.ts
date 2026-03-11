// frontend/src/app/app.component.ts
import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';

// Angular Material Modules
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatIconModule, MatIconRegistry } from '@angular/material/icon';
import { DomSanitizer } from '@angular/platform-browser';

// App Components and Services
import { ConnectionFormComponent } from './components/connection-form/connection-form.component';
import { SqlRunnerComponent } from './components/sql-runner/sql-runner.component';
import { ReportBuilderComponent } from './components/report-builder/report-builder.component';
import { ChartSuggestionsComponent } from './components/chart-suggestions/chart-suggestions.component';
import { SummaryReportComponent } from './components/summary-report/summary-report.component';
import { SessionService } from './services/session.service';
import { ColumnInfo, ChartConfig } from './interfaces/api.interfaces';

const GITHUB_ICON = `
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.91 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
  </svg>
`;

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    MatToolbarModule,
    MatButtonModule,
    MatSnackBarModule,
    MatIconModule,
    ConnectionFormComponent,
    SqlRunnerComponent,
    ReportBuilderComponent,
    ChartSuggestionsComponent,
    SummaryReportComponent,
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements OnInit, OnDestroy {
  // App state
  isConnected = false;
  showSummaryReport = false;
  
  // Data passed between components
  lastSuccessfulSql = '';
  lastQueryColumns: ColumnInfo[] = [];
  activeSuggestion: ChartConfig | null = null;

  private sessionSub?: Subscription;

  constructor(
    private sessionService: SessionService, 
    private snackBar: MatSnackBar,
    private matIconRegistry: MatIconRegistry,
    private domSanitizer: DomSanitizer
  ) {
    this.matIconRegistry.addSvgIconLiteral('github-logo', this.domSanitizer.bypassSecurityTrustHtml(GITHUB_ICON));
  }

  ngOnInit() {
    this.sessionSub = this.sessionService.startSession().subscribe({
      next: () => {
        this.snackBar.open('New session started!', 'Close', { duration: 2000 });
      },
      error: (err) => {
        this.snackBar.open(`Failed to start session: ${err.message}`, 'Error', {
          panelClass: ['error-snackbar'],
        });
      },
    });
  }

  ngOnDestroy() {
    this.sessionSub?.unsubscribe();
    // The browser closing will trigger the backend sweeper, but we can also be explicit
    if (this.sessionService.getSessionId()) {
      this.sessionService.closeSession().subscribe();
    }
  }

  onConnectionSuccess() {
    this.isConnected = true;
    this.snackBar.open('Successfully connected to Oracle!', 'Close', {
      duration: 3000,
      panelClass: ['success-snackbar'],
    });
  }
  
  onQuerySuccess(event: { sql: string, columns: ColumnInfo[] }) {
    this.lastSuccessfulSql = event.sql;
    this.lastQueryColumns = event.columns;
    this.activeSuggestion = null; // Reset suggestion on new query
  }

  onSuggestionClicked(config: ChartConfig) {
    this.activeSuggestion = config;
  }

  onGenerateReport() {
    this.showSummaryReport = true;
  }

  onBackToQuery() {
    this.showSummaryReport = false;
  }
}
