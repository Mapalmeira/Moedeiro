import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../../core/api/api-error';
import { I18nService } from '../../../core/i18n/i18n.service';
import { LedgerAccount, LedgerCurrency } from '../../../core/ledgers/ledger-entities.models';
import { LedgerEntitiesService } from '../../../core/ledgers/ledger-entities.service';
import { EntityEditorComponent } from './entity-editor.component';

const currency: LedgerCurrency = { uuid: 'currency', name: 'Real', prefix: 'R$ ', suffix: null, decimal_places: 2, icon: 'lucide:Coins', color_code: '#FFD51A' };
const account: LedgerAccount = { uuid: 'account', name: 'Checking', note: null, currency_uuid: currency.uuid, icon: 'lucide:Wallet', color_code: '#21E683' };

describe('EntityEditorComponent', () => {
  const entities = {
    createAccount: vi.fn(() => of(account)), updateAccount: vi.fn(() => of(account)),
    createCurrency: vi.fn(() => of(currency)), updateCurrency: vi.fn(() => of(currency)),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    entities.createAccount.mockReturnValue(of(account));
    entities.updateAccount.mockReturnValue(of(account));
    entities.createCurrency.mockReturnValue(of(currency));
    entities.updateCurrency.mockReturnValue(of(currency));
    TestBed.configureTestingModule({
      imports: [EntityEditorComponent],
      providers: [
        { provide: LedgerEntitiesService, useValue: entities },
        { provide: ApiErrorService, useValue: { message: vi.fn(() => 'save failed') } },
        { provide: I18nService, useValue: { t: vi.fn((key: string) => key) } },
      ],
    });
  });

  function createEditor(kind: 'account' | 'currency', entity: LedgerAccount | LedgerCurrency | null = null): ComponentFixture<EntityEditorComponent> {
    const fixture = TestBed.createComponent(EntityEditorComponent);
    fixture.componentRef.setInput('kind', kind);
    fixture.componentRef.setInput('ledgerUuid', 'ledger');
    fixture.componentRef.setInput('currencies', [currency]);
    fixture.componentRef.setInput('entity', entity);
    fixture.detectChanges();
    return fixture;
  }

  it('creates an account with its currency and normalized optional note', () => {
    const fixture = createEditor('account');
    fixture.componentInstance.form.patchValue({
      name: '  Checking  ', note: '', currency_uuid: 'currency', icon: 'lucide:Wallet', color_code: '#21e683',
    });

    fixture.componentInstance.save();

    expect(entities.createAccount).toHaveBeenCalledWith('ledger', {
      name: 'Checking', note: null, currency_uuid: 'currency', icon: 'lucide:Wallet', color_code: '#21E683',
    });
  });

  it('updates an account without allowing its currency to change', () => {
    const fixture = createEditor('account', account);
    fixture.componentInstance.form.patchValue({ name: 'Updated', currency_uuid: 'other' });

    fixture.componentInstance.save();

    expect(entities.updateAccount).toHaveBeenCalledWith('ledger', 'account', expect.not.objectContaining({ currency_uuid: expect.anything() }));
  });

  it('creates a currency with decimal places but omits them from updates', () => {
    const fixture = createEditor('currency');
    fixture.componentInstance.form.patchValue({
      name: 'Real', prefix: 'R$ ', suffix: '', decimal_places: 2, icon: 'lucide:Coins', color_code: '#ffd51a',
    });
    fixture.componentInstance.save();
    expect(entities.createCurrency).toHaveBeenCalledWith('ledger', {
      name: 'Real', prefix: 'R$ ', suffix: null, decimal_places: 2, icon: 'lucide:Coins', color_code: '#FFD51A',
    });

    const editing = createEditor('currency', currency);
    editing.componentInstance.form.patchValue({ name: 'BRL', decimal_places: 6 });
    editing.componentInstance.save();
    expect(entities.updateCurrency).toHaveBeenCalledWith('ledger', 'currency', expect.not.objectContaining({ decimal_places: expect.anything() }));
  });

  it('publishes save failures and unlocks the editor', () => {
    entities.createAccount.mockReturnValue(throwError(() => new Error('offline')));
    const fixture = createEditor('account');
    fixture.componentInstance.form.patchValue({ name: 'Checking', currency_uuid: 'currency' });

    fixture.componentInstance.save();

    expect(fixture.componentInstance.error()).toBe('save failed');
    expect(fixture.componentInstance.saving()).toBe(false);
  });
});
