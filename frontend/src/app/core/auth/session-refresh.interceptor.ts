import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, from, switchMap, throwError } from 'rxjs';
import { API_ROUTES } from '../api/api.routes';
import { AuthService } from './auth.service';

export const sessionRefreshInterceptor: HttpInterceptorFn = (request, next) => {
  const auth = inject(AuthService);

  return next(request).pipe(
    catchError((error: unknown) => {
      if (!isExpiredSessionResponse(request.url, error)) return throwError(() => error);

      return auth.refreshSession().pipe(
        switchMap((valid) => {
          if (!valid) {
            return from(auth.finishLogout()).pipe(
              switchMap(() => throwError(() => error)),
            );
          }

          return next(request).pipe(
            catchError((retryError: unknown) => {
              if (!(retryError instanceof HttpErrorResponse) || retryError.status !== 401) {
                return throwError(() => retryError);
              }
              return from(auth.finishLogout()).pipe(
                switchMap(() => throwError(() => retryError)),
              );
            }),
          );
        }),
      );
    }),
  );
};

function isExpiredSessionResponse(url: string, error: unknown): boolean {
  if (!(error instanceof HttpErrorResponse) || error.status !== 401 || error.error?.detail !== 'Invalid session') return false;
  return url !== API_ROUTES.authentication.login
    && url !== API_ROUTES.authentication.session
    && url !== API_ROUTES.authentication.refresh
    && url !== API_ROUTES.authentication.logout;
}
