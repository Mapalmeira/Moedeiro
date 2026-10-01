import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../core/api/api-error';
import { I18nService } from '../../core/i18n/i18n.service';
import { Ledger } from '../../core/ledgers/ledger.models';
import { LedgerService } from '../../core/ledgers/ledger.service';
import { LedgerDeleteDialogComponent } from './ledger-delete-dialog.component';

const ledger: Ledger = { uuid: 'ledger', name: 'Personal', icon: 'lucide:Wallet', color_code: '#21E683', last_accessed_at: 10 };

describe('LedgerDeleteDialogComponent', () => {
  const ledgers = { delete: vi.fn(() => of(void 0)) };
  let fixture: ComponentFixture<LedgerDeleteDialogComponent>;

  beforeEach(() => {
    vi.clearAllMocks();
    ledgers.delete.mockReturnValue(of(void 0));
    TestBed.configureTestingModule({
      imports: [LedgerDeleteDialogComponent],
      providers: [
        { provide: LedgerService, useValue: ledgers },
        { provide: ApiErrorService, useValue: { message: vi.fn(() => 'delete failed') } },
        { provide: I18nService, useValue: { t: vi.fn((key: string) => key) } },
      ],
    });
    fixture = TestBed.createComponent(LedgerDeleteDialogComponent);
    fixture.componentRef.setInput('ledger', ledger);
    fixture.componentRef.setInput('open', true);
    fixture.detectChanges();
  });

  it('requires an exact ledger name before deletion', () => {
    fixture.componentInstance.confirmation.set('personal');
    fixture.componentInstance.deleteLedger();
    expect(ledgers.delete).not.toHaveBeenCalled();
  });

  it('emits deletion and close only after the request succeeds', () => {
    const deleted = vi.fn();
    const closed = vi.fn();
    fixture.componentInstance.deleted.subscribe(deleted);
    fixture.componentInstance.close.subscribe(closed);
    fixture.componentInstance.confirmation.set('Personal');

    fixture.componentInstance.deleteLedger();

    expect(ledgers.delete).toHaveBeenCalledWith('ledger');
    expect(deleted).toHaveBeenCalledWith('ledger');
    expect(closed).toHaveBeenCalledOnce();
  });

  it('keeps the dialog open and unlocks it after a failure', () => {
    ledgers.delete.mockReturnValue(throwError(() => new Error('offline')));
    const closed = vi.fn();
    fixture.componentInstance.close.subscribe(closed);
    fixture.componentInstance.confirmation.set('Personal');

    fixture.componentInstance.deleteLedger();

    expect(fixture.componentInstance.errorMessage()).toBe('delete failed');
    expect(fixture.componentInstance.deleting()).toBe(false);
    expect(closed).not.toHaveBeenCalled();
  });
});
