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
import { MatIconModule, MatIconRegistry } from '@angular/material/icon';
import { DomSanitizer } from '@angular/platform-browser';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import { ApiService } from '../../services/api.service';
import { finalize } from 'rxjs/operators';

const VISIBILITY_ICON = `
  <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px" fill="#000000">
    <path d="M0 0h24v24H0V0z" fill="none"/>
    <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5C21.27 7.61 17 4.5 12 4.5zm0 13c-2.48 0-4.5-2.02-4.5-4.5S9.52 8.5 12 8.5s4.5 2.02 4.5 4.5-2.02 4.5-4.5 4.5zm0-7c-1.38 0-2.5 1.12-2.5 2.5s1.12 2.5 2.5 2.5 2.5-1.12 2.5-2.5-1.12-2.5-2.5-2.5z"/>
  </svg>
`;

const VISIBILITY_OFF_ICON = `
  <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px" fill="#000000">
    <path d="M0 0h24v24H0V0z" fill="none"/>
    <path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.38 1.12 2.5 2.5 2.5.22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.48 0-4.5-2.02-4.5-4.5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.38-1.12-2.5-2.5-2.5-.05 0-.1.01-.16.02z"/>
  </svg>
`;

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

  constructor(
    private fb: FormBuilder, 
    private apiService: ApiService,
    private matIconRegistry: MatIconRegistry,
    private domSanitizer: DomSanitizer
  ) {
    this.matIconRegistry.addSvgIconLiteral('visibility', this.domSanitizer.bypassSecurityTrustHtml(VISIBILITY_ICON));
    this.matIconRegistry.addSvgIconLiteral('visibility_off', this.domSanitizer.bypassSecurityTrustHtml(VISIBILITY_OFF_ICON));

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
