import { ChangeDetectionStrategy, Component } from '@angular/core';
import { LedgerEntityManagerComponent } from '../ledger-entity-manager.component';

@Component({
  selector: 'app-ledger-currencies',
  standalone: true,
  imports: [LedgerEntityManagerComponent],
  template: `<app-ledger-entity-manager kind="currency" />`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerCurrenciesComponent {}
