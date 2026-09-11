import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { IconComponent, IconName } from './icon.component';

@Component({
  selector: 'app-auth-card',
  standalone: true,
  imports: [IconComponent],
  host: { '[class]': '"auth-card auth-card--" + accent() + " ui-projected-surface ui-projection--hard"' },
  template: `
    <header class="auth-card__header ui-heading-with-icon">
      <span class="auth-card__icon ui-icon-badge ui-icon-badge--title ui-projected-icon"><app-icon [name]="icon()" size="card-title" /></span>
      <h2>{{ title() }}</h2>
    </header>
    <div class="auth-card__body"><ng-content /></div>
  `,
  styles: `
    :host { --auth-card-padding: clamp(22px, 3vw, 30px); display: flex; flex-direction: column; min-width: 0; margin-inline-end: var(--hard-shadow-offset); margin-block-end: var(--hard-shadow-offset); border: var(--border-width) solid var(--line-strong); border-radius: var(--radius-card); background: var(--surface); overflow: hidden; }
    .auth-card__header { padding: var(--auth-card-padding); border-bottom: var(--border-width) solid var(--line); }
    .auth-card__header h2 { margin: 0; font-size: clamp(1.08rem, 1.7vw, 1.28rem); line-height: 1.2; }
    .auth-card__icon { background: var(--card-accent); color: var(--card-on-accent); }
    .auth-card__body { flex: 1 1 auto; min-height: 0; display: flex; flex-direction: column; padding: var(--space-6) var(--auth-card-padding) var(--auth-card-padding); }
    :host(.auth-card--green) { --card-accent: var(--green); --card-on-accent: var(--on-green); --ui-accent: var(--green); --ui-accent-strong: var(--green-strong); }
    :host(.auth-card--yellow) { --card-accent: var(--yellow); --card-on-accent: var(--on-yellow); --ui-accent: var(--yellow); --ui-accent-strong: var(--yellow-strong); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthCardComponent {
  readonly title = input.required<string>();
  readonly icon = input.required<IconName>();
  readonly accent = input<'green' | 'yellow'>('green');
}
