import { ChangeDetectionStrategy, Component } from '@angular/core';
import { LedgerSelectorComponent } from '../ledgers/selector/ledger-selector.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [LedgerSelectorComponent],
  template: `<app-ledger-selector />`,
  styles: `:host { display: block; width: 100%; }`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HomeComponent {}
