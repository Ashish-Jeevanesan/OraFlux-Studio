// frontend/src/app/app.component.ts
import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';

// Angular Material Modules
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

// App Components and Services
import { ConnectionFormComponent } from './components/connection-form/connection-form.component';
import { SqlRunnerComponent } from './components/sql-runner/sql-runner.component';
import { ReportBuilderComponent } from './components/report-builder/report-builder.component';
import { SessionService } from './services/session.service';
import { ColumnInfo } from './interfaces/api.interfaces';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    MatToolbarModule,
    MatButtonModule,
    MatSnackBarModule,
    ConnectionFormComponent,
    SqlRunnerComponent,
    ReportBuilderComponent,
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements OnInit, OnDestroy {
  // App state
  isConnected = false;
  
  // Data passed between components
  lastSuccessfulSql = '';
  lastQueryColumns: ColumnInfo[] = [];

  private sessionSub?: Subscription;

  constructor(private sessionService: SessionService, private snackBar: MatSnackBar) {}

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
  }
}
