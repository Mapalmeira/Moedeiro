import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { IconComponent, IconName } from './icon.component';

@Component({
  selector: 'app-auth-card',
  standalone: true,
  imports: [IconComponent],
  host: { '[class]': '"auth-card auth-card--" + accent()' },
  template: `
    <header class="auth-card__header">
      <span class="auth-card__icon"><app-icon [name]="icon()" [size]="25" /></span>
      <h2>{{ title() }}</h2>
    </header>
    <div class="auth-card__divider"></div>
    <ng-content />
  `,
  styles: `
    :host { display: flex; flex-direction: column; min-width: 0; padding: clamp(22px, 3vw, 30px); border: 2px solid var(--line-strong); border-radius: var(--radius-card); background: var(--surface); box-shadow: var(--shadow-hard); }
    .auth-card__header { display: flex; align-items: center; gap: var(--title-icon-gap); }
    .auth-card__header h2 { margin: 0; font-size: clamp(1.08rem, 1.7vw, 1.28rem); line-height: 1.2; }
    .auth-card__icon { display: inline-grid; place-items: center; width: 46px; height: 46px; flex: 0 0 46px; border: 2px solid var(--line-strong); border-radius: 5px; background: var(--card-accent); color: #060606; box-shadow: 2px 2px 0 var(--shadow-color); }
    .auth-card__divider { height: 1px; margin: var(--section-gap) 0 var(--space-6); background: var(--line-strong); opacity: .8; }
    :host(.auth-card--green) { --card-accent: var(--green); --token-accent: var(--green); --token-accent-strong: var(--green-strong); --focus-accent: var(--green); }
    :host(.auth-card--yellow) { --card-accent: var(--yellow); --token-accent: var(--yellow); --token-accent-strong: var(--yellow-strong); --focus-accent: var(--yellow); }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthCardComponent {
  readonly title = input.required<string>();
  readonly icon = input.required<IconName>();
  readonly accent = input<'green' | 'yellow'>('green');
}
