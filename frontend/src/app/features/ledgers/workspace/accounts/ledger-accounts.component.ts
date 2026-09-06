import { ChangeDetectionStrategy, Component } from '@angular/core';
import { LedgerEntityManagerComponent } from '../ledger-entity-manager.component';

@Component({
  selector: 'app-ledger-accounts',
  standalone: true,
  imports: [LedgerEntityManagerComponent],
  template: `<app-ledger-entity-manager kind="account" />`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerAccountsComponent {}
