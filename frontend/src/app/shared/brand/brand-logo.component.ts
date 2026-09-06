import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-brand-logo',
  standalone: true,
  template: `
    <span class="brand" [class.brand--sidebar]="variant() === 'sidebar'" role="img" aria-label="Moedeiro">
      <img class="brand__icon" src="/MoedeiroIcon.svg" alt="" aria-hidden="true" draggable="false" />
      <span class="brand__wordmark" aria-hidden="true">Moedeiro</span>
    </span>
  `,
  styles: `
    :host { display: inline-flex; align-items: center; justify-content: center; min-width: 0; }
    .brand { display: inline-flex; align-items: center; gap: clamp(11px, 1.5vw, 16px); color: var(--text); line-height: 1; user-select: none; }
    .brand__icon { display: block; width: clamp(62px, 6.2vw, 78px); height: clamp(62px, 6.2vw, 78px); flex: 0 0 auto; }
    .brand__wordmark { font-size: clamp(3rem, 5.4vw, 4.5rem); font-weight: 850; letter-spacing: -.055em; line-height: .95; white-space: nowrap; }

    .brand--sidebar { gap: var(--space-3); }
    .brand--sidebar .brand__icon { width: var(--sidebar-control-height); height: var(--sidebar-control-height); }
    .brand--sidebar .brand__wordmark { font-size: var(--sidebar-brand-font-size); letter-spacing: -.045em; line-height: .95; }

    @media (max-width: 480px) {
      .brand:not(.brand--sidebar) .brand__icon { width: 56px; height: 56px; }
      .brand:not(.brand--sidebar) .brand__wordmark { font-size: 2.8rem; }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BrandLogoComponent {
  readonly variant = input<'default' | 'sidebar'>('default');
}
