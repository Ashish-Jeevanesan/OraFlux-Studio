// frontend/src/app/components/connection-form/connection-form.component.ts
import { Component, EventEmitter, Output, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';
import { CommonModule } from '@angular/common';

// Angular Material Modules
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import { ApiService } from '../../services/api.service';
import { finalize } from 'rxjs/operators';

/**
 * Custom validator to require at least one of two fields.
 */
export const requiredOneOfValidator: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
  const serviceName = control.get('serviceName');
  const sid = control.get('sid');

  return serviceName && sid && !serviceName.value && !sid.value ? { requiredOneOf: true } : null;
};


@Component({
  selector: 'app-connection-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatSlideToggleModule,
  ],
  templateUrl: './connection-form.component.html',
  styleUrls: ['./connection-form.component.scss'],
})
export class ConnectionFormComponent implements OnInit {
  @Output() connectionSuccess = new EventEmitter<void>();
  
  connectForm: FormGroup;
  isLoading = false;
  errorMessage: string | null = null;
  hidePassword = true;

  constructor(private fb: FormBuilder, private apiService: ApiService) {
    this.connectForm = this.fb.group({
      host: ['SL80ORA03-D', Validators.required],
      port: [1522, Validators.required],
      serviceName: [''],
      sid: ['ODCDEV'],
      user: ['GLOBUS_APP', Validators.required],
      password: ['App$74335mig', Validators.required],
      ssl: [false],
    }, { validators: requiredOneOfValidator });
  }

  ngOnInit(): void {
    // Logic to make serviceName/sid mutually exclusive could go here if desired
  }

  onSubmit() {
    if (this.connectForm.invalid) {
      return;
    }

    this.isLoading = true;
    this.errorMessage = null;

    const formValue = this.connectForm.value;

    this.apiService
      .connectToOracle({
        host: formValue.host,
        port: formValue.port,
        serviceName: formValue.serviceName,
        sid: formValue.sid,
        user: formValue.user,
        password: formValue.password,
        ssl: formValue.ssl,
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
