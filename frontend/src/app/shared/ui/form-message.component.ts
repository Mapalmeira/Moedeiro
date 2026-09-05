import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { IconComponent } from './icon.component';

@Component({
  selector: 'app-form-message',
  standalone: true,
  imports: [IconComponent],
  template: `
    <div class="message" [class.message--success]="kind() === 'success'" [class.message--info]="kind() === 'info'" role="status">
      <app-icon [name]="kind() === 'success' ? 'check' : 'info'" [size]="19" />
      <span>{{ text() }}</span>
    </div>
  `,
  styles: `
    :host { display: block; min-width: 0; }
    .message { display: flex; gap: var(--space-2); align-items: flex-start; margin: 0; padding: var(--space-3); border: 1px solid var(--danger); border-radius: var(--radius-sm); background: var(--danger-soft); color: var(--text); font-size: .9rem; }
    .message--success { border-color: var(--green-strong); background: var(--green-soft); }
    .message--info { border-color: var(--blue-strong); background: var(--blue-soft); }
    app-icon { flex: 0 0 auto; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FormMessageComponent {
  readonly text = input.required<string>();
  readonly kind = input<'error' | 'success' | 'info'>('error');
}
