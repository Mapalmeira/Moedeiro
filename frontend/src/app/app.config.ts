import { ApplicationConfig } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { routes } from './app.routes';
import { sessionRefreshInterceptor } from './core/auth/session-refresh.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(withInterceptors([sessionRefreshInterceptor])),
    provideRouter(routes, withComponentInputBinding()),
  ],
};
