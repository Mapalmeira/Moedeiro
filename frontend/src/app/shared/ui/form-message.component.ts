import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { IconComponent, IconName } from './icon.component';

@Component({
  selector: 'app-form-message',
  standalone: true,
  imports: [IconComponent],
  template: `
    <div class="message" [class.message--success]="kind() === 'success'" [class.message--info]="kind() === 'info'" [class.message--warning]="kind() === 'warning'" [class.message--compact]="compact()" role="status">
      <app-icon [name]="icon() ?? (kind() === 'success' ? 'LucideCheck' : 'LucideInfo')" size="control" />
      <span>{{ text() }}</span>
    </div>
  `,
  styles: `
    :host { display: block; min-width: 0; }
    .message { --message-accent: var(--danger); display: flex; gap: var(--inline-gap); align-items: center; margin: 0; padding: var(--space-3); border: var(--border-width) solid var(--message-accent); border-radius: var(--radius-sm); background: var(--danger-soft); color: var(--message-accent); font-size: var(--control-font-size); font-weight: 650; line-height: 1.4; }
    .message--success { --message-accent: var(--green-strong); background: var(--green-soft); }
    .message--info { --message-accent: var(--blue-strong); background: var(--blue-soft); }
    .message--warning { --message-accent: var(--warning-text); background: var(--warning-soft); }
    .message--compact { min-height: var(--message-compact-min-height, var(--control-height)); padding: var(--space-1) var(--space-3); font-size: var(--control-detail-font-size); line-height: 1.25; }
    app-icon { flex: 0 0 auto; color: var(--message-accent); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FormMessageComponent {
  readonly text = input.required<string>();
  readonly kind = input<'error' | 'success' | 'info' | 'warning'>('error');
  readonly icon = input<IconName | null>(null);
  readonly compact = input(false);
}
