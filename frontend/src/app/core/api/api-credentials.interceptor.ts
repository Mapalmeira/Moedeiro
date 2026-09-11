import { HttpInterceptorFn } from '@angular/common/http';

/** Sends same-origin API requests with the session cookie expected by the backend. */
export const apiCredentialsInterceptor: HttpInterceptorFn = (request, next) => {
  if (!request.url.startsWith('/api/')) return next(request);
  return next(request.clone({ withCredentials: true }));
};
