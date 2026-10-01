import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { I18nService } from '../../core/i18n/i18n.service';
import { LedgerContextService } from '../../core/ledgers/ledger-context.service';
import { AuthenticatedShellService } from '../authenticated-layout/authenticated-shell.service';
import { LedgerLayoutComponent } from './ledger-layout.component';

describe('LedgerLayoutComponent', () => {
  const events = new Subject<NavigationEnd>();
  const router = { events, url: '/ledgers/ledger/home', navigateByUrl: vi.fn().mockResolvedValue(true) };
  const route = { firstChild: { snapshot: { data: { ledgerSection: 'budgets' } } } };
  const context = { load: vi.fn(), ledger: signal(null), loading: signal(false), loadError: signal<string | null>(null) };
  const shell = { currentUserName: signal('alice'), loggingOut: signal(false) };
  let fixture: ComponentFixture<LedgerLayoutComponent>;

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.configureTestingModule({
      imports: [LedgerLayoutComponent],
      providers: [
        { provide: Router, useValue: router },
        { provide: ActivatedRoute, useValue: route },
        { provide: LedgerContextService, useValue: context },
        { provide: AuthenticatedShellService, useValue: shell },
        { provide: I18nService, useValue: { t: vi.fn((key: string) => key) } },
      ],
    });
    TestBed.overrideComponent(LedgerLayoutComponent, { set: { template: '' } });
    fixture = TestBed.createComponent(LedgerLayoutComponent);
    fixture.componentRef.setInput('ledgerUuid', 'ledger');
    fixture.detectChanges();
  });

  it('loads the route ledger and resolves its active section', () => {
    expect(context.load).toHaveBeenCalledWith('ledger');
    expect(fixture.componentInstance.activeSection().key).toBe('budgets');
  });

  it('opens and closes mobile navigation only at mobile widths', () => {
    fixture.componentInstance.isMobile.set(true);
    fixture.componentInstance.openMobileNavigation();
    expect(fixture.componentInstance.mobileSidebarOpen()).toBe(true);

    fixture.componentInstance.onSectionSelected();
    expect(fixture.componentInstance.mobileSidebarOpen()).toBe(false);

    fixture.componentInstance.isMobile.set(false);
    fixture.componentInstance.openMobileNavigation();
    expect(fixture.componentInstance.mobileSidebarOpen()).toBe(false);
  });

  it('closes navigation when opening external access or leaving the ledger', () => {
    fixture.componentInstance.mobileSidebarOpen.set(true);
    fixture.componentInstance.openExternalAccess();
    expect(fixture.componentInstance.mobileSidebarOpen()).toBe(false);
    expect(fixture.componentInstance.externalAccessOpen()).toBe(true);

    fixture.componentInstance.mobileSidebarOpen.set(true);
    fixture.componentInstance.leaveLedger();
    expect(router.navigateByUrl).toHaveBeenCalledWith('/home');
    expect(fixture.componentInstance.mobileSidebarOpen()).toBe(false);
  });
});
