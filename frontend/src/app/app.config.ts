import { ApplicationConfig } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { routes } from './app.routes';
import { apiCredentialsInterceptor } from './core/api/api-credentials.interceptor';
import { sessionRefreshInterceptor } from './core/auth/session-refresh.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(withInterceptors([apiCredentialsInterceptor, sessionRefreshInterceptor])),
    provideRouter(routes, withComponentInputBinding()),
  ],
};
