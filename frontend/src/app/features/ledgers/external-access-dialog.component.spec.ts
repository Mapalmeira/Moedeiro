import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import type { Observable } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../core/api/api-error';
import { I18nService } from '../../core/i18n/i18n.service';
import { CreatedExternalAccessGrant, ExternalAccessGrant } from '../../core/ledgers/external-access.models';
import { ExternalAccessService } from '../../core/ledgers/external-access.service';
import { Ledger } from '../../core/ledgers/ledger.models';
import type { TotpResponse } from '../../core/security/security.models';
import { SecurityService } from '../../core/security/security.service';
import { ExternalAccessDialogComponent } from './external-access-dialog.component';

const ledger: Ledger = {
  uuid: '11111111-1111-1111-1111-111111111111',
  name: 'Personal',
  icon: 'unicode:R$',
  color_code: '#21E683',
  last_accessed_at: 1,
};

const access: ExternalAccessGrant = {
  grant_uuid: '22222222-2222-2222-2222-222222222222',
  external_access_uuid: '33333333-3333-3333-3333-333333333333',
  name: 'Sync plugin',
  created_at: 1_700_000_000,
};

const created: CreatedExternalAccessGrant = {
  ...access,
  token: 'one-time-token',
};

describe('ExternalAccessDialogComponent', () => {
  const totpStatus = signal<'unknown' | 'ENABLED' | 'DISABLED' | 'PENDING'>('DISABLED');
  const externalAccessService = {
    list: vi.fn(() => of([access])),
    create: vi.fn(() => of(created)),
    revoke: vi.fn(() => of(void 0)),
  };
  const securityService = {
    totpStatus,
    getTotpStatus: vi.fn<() => Observable<TotpResponse>>(() => {
      totpStatus.set('DISABLED');
      return of<TotpResponse>({ state: 'DISABLED', provisioning_uri: null, expires_at: null });
    }),
  };
  const apiErrors = { message: vi.fn(() => 'fallback error') };
  const i18n = { t: vi.fn((key: string) => key) };

  beforeEach(() => {
    vi.clearAllMocks();
    totpStatus.set('DISABLED');
    externalAccessService.list.mockImplementation(() => of([access]));
    externalAccessService.create.mockImplementation(() => of(created));
    externalAccessService.revoke.mockImplementation(() => of(void 0));
    securityService.getTotpStatus.mockImplementation(() => {
      totpStatus.set('DISABLED');
      return of<TotpResponse>({ state: 'DISABLED', provisioning_uri: null, expires_at: null });
    });

    TestBed.configureTestingModule({
      imports: [ExternalAccessDialogComponent],
      providers: [
        { provide: ExternalAccessService, useValue: externalAccessService },
        { provide: SecurityService, useValue: securityService },
        { provide: ApiErrorService, useValue: apiErrors },
        { provide: I18nService, useValue: i18n },
      ],
    });
  });

  function openDialog() {
    const fixture = TestBed.createComponent(ExternalAccessDialogComponent);
    fixture.componentRef.setInput('ledger', ledger);
    fixture.componentRef.setInput('open', true);
    fixture.detectChanges();
    return fixture;
  }

  it('loads the ledger accesses and TOTP status when opened', () => {
    const fixture = openDialog();
    const component = fixture.componentInstance;

    expect(externalAccessService.list).toHaveBeenCalledWith(ledger.uuid);
    expect(securityService.getTotpStatus).toHaveBeenCalledOnce();
    expect(component.accesses()).toEqual([access]);
    expect(component.view()).toBe('list');
  });

  it('blocks credential actions while the TOTP status is unknown and allows retrying the status request', () => {
    securityService.getTotpStatus.mockImplementation(() => {
      totpStatus.set('unknown');
      return throwError(() => new HttpErrorResponse({ status: 503 }));
    });
    const fixture = openDialog();
    const component = fixture.componentInstance;

    expect(component.totpStatusReady()).toBe(false);
    component.showCreate();
    expect(component.view()).toBe('list');

    securityService.getTotpStatus.mockImplementation(() => {
      totpStatus.set('DISABLED');
      return of<TotpResponse>({ state: 'DISABLED', provisioning_uri: null, expires_at: null });
    });
    component.loadTotpStatus();

    expect(component.totpStatusReady()).toBe(true);
    expect(component.totpStatusErrorMessage()).toBeNull();
  });

  it('keeps the created plaintext token only in the dialog state and clears it when leaving the created view', () => {
    const fixture = openDialog();
    const component = fixture.componentInstance;
    component.showCreate();
    component.createForm.setValue({ name: 'Sync plugin', current_password: 'password123', totp_code: '' });

    component.createAccess();

    expect(externalAccessService.create).toHaveBeenCalledWith(ledger.uuid, {
      name: 'Sync plugin',
      current_password: 'password123',
      totp_code: null,
    });
    expect(component.view()).toBe('created');
    expect(component.createdToken()).toBe('one-time-token');
    expect(component.accesses()[0]).toEqual(access);

    component.finishCreated();
    expect(component.createdToken()).toBe('');
    expect(component.view()).toBe('list');
  });

  it('requires a TOTP code in credential forms when TOTP is enabled', () => {
    securityService.getTotpStatus.mockImplementation(() => {
      totpStatus.set('ENABLED');
      return of<TotpResponse>({ state: 'ENABLED', provisioning_uri: null, expires_at: null });
    });
    const fixture = openDialog();
    const component = fixture.componentInstance;
    component.showCreate();
    component.createForm.patchValue({ name: 'Sync plugin', current_password: 'password123', totp_code: '' });
    fixture.detectChanges();

    expect(component.requiresTotp()).toBe(true);
    expect(component.createForm.controls.totp_code.hasError('required')).toBe(true);

    component.createForm.controls.totp_code.setValue('123456');
    expect(component.createForm.controls.totp_code.valid).toBe(true);
  });

  it('removes a revoked access from the local list after the request succeeds', () => {
    const fixture = openDialog();
    const component = fixture.componentInstance;
    component.showRevoke(access);
    component.revokeForm.setValue({ current_password: 'password123', totp_code: '' });

    component.revokeAccess();

    expect(externalAccessService.revoke).toHaveBeenCalledWith(ledger.uuid, access.grant_uuid, {
      current_password: 'password123',
      totp_code: null,
    });
    expect(component.accesses()).toEqual([]);
    expect(component.view()).toBe('list');
  });

  it('turns a stale TOTP status into a required TOTP field when the backend requires it', () => {
    externalAccessService.create.mockImplementation(() => throwError(() => new HttpErrorResponse({
      status: 401,
      error: { detail: 'TOTP required' },
    })));
    const fixture = openDialog();
    const component = fixture.componentInstance;
    component.showCreate();
    component.createForm.setValue({ name: 'Sync plugin', current_password: 'password123', totp_code: '' });

    component.createAccess();
    fixture.detectChanges();

    expect(component.requiresTotp()).toBe(true);
    expect(component.createForm.controls.totp_code.hasError('required')).toBe(true);
    expect(component.actionError()).toBe('errors.totpRequired');
  });

  it('clears a one-time token before emitting close', () => {
    const fixture = openDialog();
    const component = fixture.componentInstance;
    const closed = vi.fn();
    component.close.subscribe(closed);
    component.createdToken.set('secret');
    component.view.set('created');

    component.requestClose();

    expect(component.createdToken()).toBe('');
    expect(closed).toHaveBeenCalledOnce();
  });
});
