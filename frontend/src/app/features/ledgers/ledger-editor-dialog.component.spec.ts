import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../core/api/api-error';
import { I18nService } from '../../core/i18n/i18n.service';
import { Ledger } from '../../core/ledgers/ledger.models';
import { LedgerService } from '../../core/ledgers/ledger.service';
import { LedgerEditorDialogComponent } from './ledger-editor-dialog.component';

const ledger: Ledger = { uuid: 'ledger', name: 'Personal', icon: 'lucide:Wallet', color_code: '#21E683', last_accessed_at: 10 };

describe('LedgerEditorDialogComponent', () => {
  const ledgers = { create: vi.fn(() => of(ledger)), update: vi.fn(() => of(ledger)) };
  const apiErrors = { message: vi.fn(() => 'save failed') };
  let fixture: ComponentFixture<LedgerEditorDialogComponent>;

  beforeEach(() => {
    vi.clearAllMocks();
    ledgers.create.mockReturnValue(of(ledger));
    ledgers.update.mockReturnValue(of(ledger));
    TestBed.configureTestingModule({
      imports: [LedgerEditorDialogComponent],
      providers: [
        { provide: LedgerService, useValue: ledgers },
        { provide: ApiErrorService, useValue: apiErrors },
        { provide: I18nService, useValue: { t: vi.fn((key: string) => key) } },
      ],
    });
    fixture = TestBed.createComponent(LedgerEditorDialogComponent);
    fixture.componentRef.setInput('open', true);
    fixture.detectChanges();
  });

  it('creates a ledger with normalized name and color and emits the saved result', () => {
    const saved = vi.fn();
    const closed = vi.fn();
    fixture.componentInstance.saved.subscribe(saved);
    fixture.componentInstance.close.subscribe(closed);
    fixture.componentInstance.form.setValue({ name: '  Personal  ', icon: 'lucide:Wallet', color_code: '#21e683' });

    fixture.componentInstance.save();

    expect(ledgers.create).toHaveBeenCalledWith({ name: 'Personal', icon: 'lucide:Wallet', color_code: '#21E683' });
    expect(saved).toHaveBeenCalledWith(ledger);
    expect(closed).toHaveBeenCalledOnce();
  });

  it('updates the current ledger instead of creating another one', () => {
    fixture.componentRef.setInput('ledger', ledger);
    fixture.detectChanges();
    fixture.componentInstance.form.patchValue({ name: 'Updated' });

    fixture.componentInstance.save();

    expect(ledgers.update).toHaveBeenCalledWith('ledger', expect.objectContaining({ name: 'Updated' }));
    expect(ledgers.create).not.toHaveBeenCalled();
  });

  it('rejects a whitespace-only name before calling the service', () => {
    fixture.componentInstance.form.patchValue({ name: '   ' });
    fixture.componentInstance.save();

    expect(ledgers.create).not.toHaveBeenCalled();
    expect(fixture.componentInstance.form.controls.name.hasError('required')).toBe(true);
  });

  it('keeps the dialog open and exposes failures', () => {
    ledgers.create.mockReturnValue(throwError(() => new Error('offline')));
    const closed = vi.fn();
    fixture.componentInstance.close.subscribe(closed);
    fixture.componentInstance.form.setValue({ name: 'Personal', icon: 'lucide:Wallet', color_code: '#21E683' });

    fixture.componentInstance.save();

    expect(fixture.componentInstance.errorMessage()).toBe('save failed');
    expect(fixture.componentInstance.saving()).toBe(false);
    expect(closed).not.toHaveBeenCalled();
  });
});
