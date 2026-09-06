import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { IconComponent, IconName } from './icon.component';

@Component({
  selector: 'app-auth-card',
  standalone: true,
  imports: [IconComponent],
  host: { '[class]': '"auth-card auth-card--" + accent() + " ui-projected-surface ui-projection--hard"' },
  template: `
    <header class="auth-card__header ui-heading-with-icon">
      <span class="auth-card__icon ui-icon-badge ui-icon-badge--title ui-projected-icon"><app-icon [name]="icon()" [size]="25" /></span>
      <h2>{{ title() }}</h2>
    </header>
    <div class="auth-card__divider"></div>
    <ng-content />
  `,
  styles: `
    :host { display: flex; flex-direction: column; min-width: 0; margin-inline-end: var(--hard-shadow-offset); margin-block-end: var(--hard-shadow-offset); padding: clamp(22px, 3vw, 30px); border: var(--border-width) solid var(--line-strong); border-radius: var(--radius-card); background: var(--surface); }
    .auth-card__header h2 { margin: 0; font-size: clamp(1.08rem, 1.7vw, 1.28rem); line-height: 1.2; }
    .auth-card__icon { background: var(--card-accent); color: var(--card-on-accent); }
    .auth-card__divider { height: 1px; margin: var(--section-gap) 0 var(--space-6); background: var(--line-strong); opacity: .8; }
    :host(.auth-card--green) { --card-accent: var(--green); --card-on-accent: var(--on-green); --token-accent: var(--green); --token-accent-strong: var(--green-strong); --focus-accent: var(--green); }
    :host(.auth-card--yellow) { --card-accent: var(--yellow); --card-on-accent: var(--on-yellow); --token-accent: var(--yellow); --token-accent-strong: var(--yellow-strong); --focus-accent: var(--yellow); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthCardComponent {
  readonly title = input.required<string>();
  readonly icon = input.required<IconName>();
  readonly accent = input<'green' | 'yellow'>('green');
}
