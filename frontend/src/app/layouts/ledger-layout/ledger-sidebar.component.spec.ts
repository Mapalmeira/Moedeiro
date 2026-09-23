import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nService } from '../../core/i18n/i18n.service';
import { LedgerSidebarComponent } from './ledger-sidebar.component';

describe('LedgerSidebarComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [{ provide: I18nService, useValue: { t: vi.fn((key: string) => key) } }],
    });
  });

  it('opens external access management from the current-ledger menu', () => {
    const component = TestBed.runInInjectionContext(() => new LedgerSidebarComponent());
    const openExternalAccess = vi.fn();
    component.externalAccess.subscribe(openExternalAccess);
    component.ledgerMenuOpen.set(true);

    component.openExternalAccess();

    expect(component.ledgerMenuOpen()).toBe(false);
    expect(openExternalAccess).toHaveBeenCalledOnce();
  });
});
