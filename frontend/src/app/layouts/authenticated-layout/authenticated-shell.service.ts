import { Injectable, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { ApiErrorService } from '../../core/api/api-error';
import { AuthService } from '../../core/auth/auth.service';

@Injectable()
export class AuthenticatedShellService {
  private readonly auth = inject(AuthService);
  private readonly apiErrors = inject(ApiErrorService);

  readonly preferencesOpen = signal(false);
  readonly securityOpen = signal(false);
  readonly loggingOut = signal(false);
  readonly logoutError = signal<string | null>(null);
  readonly currentUserName = this.auth.currentUserName.asReadonly();

  openPreferences(): void {
    this.preferencesOpen.set(true);
  }

  closePreferences(): void {
    this.preferencesOpen.set(false);
  }

  openSecurity(): void {
    this.securityOpen.set(true);
  }

  closeSecurity(): void {
    this.securityOpen.set(false);
  }

  logout(): void {
    if (this.loggingOut()) return;

    this.loggingOut.set(true);
    this.logoutError.set(null);
    this.auth.logout().pipe(finalize(() => this.loggingOut.set(false))).subscribe({
      next: () => void this.auth.finishLogout(),
      error: (error: unknown) => this.logoutError.set(this.apiErrors.message(error, 'errors.logoutFailed')),
    });
  }
}
