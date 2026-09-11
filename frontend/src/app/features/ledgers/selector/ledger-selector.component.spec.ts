import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorService } from '../../../core/api/api-error';
import { I18nService } from '../../../core/i18n/i18n.service';
import { Ledger } from '../../../core/ledgers/ledger.models';
import { LedgerService } from '../../../core/ledgers/ledger.service';
import { LedgerSelectorComponent } from './ledger-selector.component';

const ledger: Ledger = {
  uuid: '11111111-1111-1111-1111-111111111111',
  name: 'Personal',
  icon: 'unicode:R$',
  color_code: '#21E683',
  last_accessed_at: 1,
};

describe('LedgerSelectorComponent', () => {
  const ledgerState = signal<Ledger[]>([ledger]);
  const ledgerService = {
    ledgers: ledgerState.asReadonly(),
    list: vi.fn(() => of(ledgerState())),
  };
  const router = {
    navigate: vi.fn(() => Promise.resolve(true)),
  };

  beforeEach(() => {
    ledgerState.set([ledger]);
    vi.clearAllMocks();
    ledgerService.list.mockImplementation(() => of(ledgerState()));

    TestBed.configureTestingModule({
      providers: [
        { provide: LedgerService, useValue: ledgerService },
        { provide: Router, useValue: router },
        { provide: ApiErrorService, useValue: { message: vi.fn(() => 'error') } },
        { provide: I18nService, useValue: { t: vi.fn((key: string) => key) } },
      ],
    });
  });

  function createComponent(): LedgerSelectorComponent {
    return TestBed.runInInjectionContext(() => new LedgerSelectorComponent());
  }

  it('navigates to the English home section for the selected ledger', async () => {
    const component = createComponent();
    component.selectLedger(ledger.uuid);

    component.enterSelected();

    expect(router.navigate).toHaveBeenCalledWith(['/ledgers', ledger.uuid, 'home']);
    expect(component.entering()).toBe(true);
    await Promise.resolve();
    expect(component.entering()).toBe(false);
  });

  it('clears selection when search filters the selected ledger out', () => {
    const component = createComponent();
    component.selectLedger(ledger.uuid);

    const input = document.createElement('input');
    input.value = 'company';
    component.setSearchFromEvent({ target: input } as unknown as Event);

    expect(component.selectedUuid()).toBeNull();
  });


  it('moves selection through the listbox with arrow keys', () => {
    const secondLedger: Ledger = { ...ledger, uuid: '22222222-2222-2222-2222-222222222222', name: 'Company' };
    ledgerState.set([ledger, secondLedger]);
    const component = createComponent();
    const list = document.createElement('div');
    list.className = 'ledger-list';
    const first = document.createElement('div');
    first.className = 'ledger-row';
    first.dataset['ledgerUuid'] = ledger.uuid;
    const second = document.createElement('div');
    second.className = 'ledger-row';
    second.dataset['ledgerUuid'] = secondLedger.uuid;
    list.append(first, second);
    document.body.append(list);
    list.addEventListener('keydown', event => component.navigateList(event));

    first.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true, cancelable: true }));

    expect(component.selectedUuid()).toBe(secondLedger.uuid);
    list.remove();
  });

  it('does not enter a ledger when nothing is selected', () => {
    const component = createComponent();

    component.enterSelected();

    expect(router.navigate).not.toHaveBeenCalled();
  });
});
