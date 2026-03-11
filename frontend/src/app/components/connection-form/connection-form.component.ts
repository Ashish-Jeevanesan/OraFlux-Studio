// frontend/src/app/components/connection-form/connection-form.component.ts
import { Component, EventEmitter, Output, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

// Angular Material Modules
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';

import { ApiService } from '../../services/api.service';
import { finalize } from 'rxjs/operators';
import { OracleProfileSummary } from '../../interfaces/api.interfaces';


@Component({
  selector: 'app-connection-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSelectModule,
  ],
  templateUrl: './connection-form.component.html',
  styleUrls: ['./connection-form.component.scss'],
})
export class ConnectionFormComponent implements OnInit {
  @Output() connectionSuccess = new EventEmitter<void>();
  
  connectForm: FormGroup;
  isLoading = false;
  isProfilesLoading = false;
  errorMessage: string | null = null;
  profiles: OracleProfileSummary[] = [];

  constructor(
    private fb: FormBuilder, 
    private apiService: ApiService
  ) {
    this.connectForm = this.fb.group({
      profileAlias: ['', Validators.required],
    });
  }

  ngOnInit(): void {
    this.loadProfiles();
  }

  private loadProfiles() {
    this.isProfilesLoading = true;
    this.errorMessage = null;

    this.apiService
      .getOracleProfiles()
      .pipe(
        finalize(() => {
          this.isProfilesLoading = false;
        })
      )
      .subscribe({
        next: (response) => {
          this.profiles = response.profiles || [];
          if (this.profiles.length > 0) {
            this.connectForm.patchValue({ profileAlias: this.profiles[0].alias });
          } else {
            this.errorMessage = 'No database profiles found in backend configuration.';
          }
        },
        error: (err) => {
          this.errorMessage = err.message;
        },
      });
  }

  onSubmit() {
    if (this.connectForm.invalid || this.isProfilesLoading) {
      return;
    }

    this.isLoading = true;
    this.errorMessage = null;

    const formValue = this.connectForm.value;

    this.apiService
      .connectToOracle({
        profileAlias: formValue.profileAlias,
        ssl: false,
      })
      .pipe(
        finalize(() => {
          this.isLoading = false;
        })
      )
      .subscribe({
        next: (response) => {
          if (response.ok) {
            this.connectionSuccess.emit();
          } else {
            this.errorMessage = response.detail || 'Connection failed for an unknown reason.';
          }
        },
        error: (err) => {
          this.errorMessage = err.message;
        },
      });
  }
}
