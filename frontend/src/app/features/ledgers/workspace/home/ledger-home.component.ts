import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'app-ledger-home',
  standalone: true,
  template: ``,
  styles: `:host { display: block; }`,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LedgerHomeComponent {}
