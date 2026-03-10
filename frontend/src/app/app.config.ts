// frontend/src/app/app.config.ts
import { ApplicationConfig, importProvidersFrom } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideClientHydration } from '@angular/platform-browser';
import { provideHttpClient, withFetch } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';

import { NgxEchartsModule } from 'ngx-echarts';
import * as echarts from 'echarts';

export const appConfig: ApplicationConfig = {
  providers: [
    provideClientHydration(),
    provideHttpClient(withFetch()),
    provideAnimations(),
    importProvidersFrom(NgxEchartsModule.forRoot({ echarts })),
  ],
};
