import { ChangeDetectionStrategy, Component, HostListener, computed, inject, input, signal } from '@angular/core';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { CashFlowPoint } from '../../../../core/ledgers/cash-flow.models';
import { formatCurrencyAmount } from '../../../../core/ledgers/currency-format';
import { LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import type { PeriodMode } from '../../../../shared/period-selection';

export type HomeFlowMode = 'instant' | 'cumulative';
interface HomeFlowRange { from: number; to: number; }

type ChartDateLabelDetail = 'day' | 'month' | 'year';
interface ChartPointView {
  index: number; x: number; xPercent: number; barWidth: number; incomeX: number; expenseX: number;
  incomeY: number; incomeHeight: number; expenseHeight: number; cumulativeY: number; label: string;
  showLabel: boolean; date: string; income: string; expense: string; net: string; cumulative: string;
}
interface ChartTickView { y: number; label: string; }

const DAY_SECONDS = 86_400;
const CHART_WIDTH = 1000;
const CHART_HEIGHT = 300;
const CHART_LEFT = 118;
const CHART_RIGHT = 28;
const CHART_TOP = 20;
const CHART_BOTTOM = 48;
const CHART_PLOT_WIDTH = CHART_WIDTH - CHART_LEFT - CHART_RIGHT;
const CHART_PLOT_HEIGHT = CHART_HEIGHT - CHART_TOP - CHART_BOTTOM;
const CHART_ZERO_Y = CHART_TOP + CHART_PLOT_HEIGHT / 2;
const CHART_X_LABEL_TARGET_COUNT = 10;
const CHART_X_LABEL_WITH_YEAR_TARGET_COUNT = 6;
const CHART_MAX_POINTS = 100;
const CHART_BAR_WIDTH_RATIO = .38;
const CHART_MIN_BAR_WIDTH = .25;
const CHART_MAX_BAR_WIDTH = 16;

export function homeChartPointWidth(range: HomeFlowRange): number {
  const days = (range.to - range.from) / DAY_SECONDS;
  return Math.max(1, Math.ceil(days / CHART_MAX_POINTS)) * DAY_SECONDS;
}

@Component({
  selector: 'app-home-flow-chart',
  standalone: true,
  template: `
    <div class="flow-chart" [attr.aria-label]="i18n.t('home.flowInPeriod')" (pointerdown)="keepSelection($event)">
      <svg [attr.viewBox]="'0 0 ' + chartWidth + ' ' + chartHeight" preserveAspectRatio="xMidYMid meet" role="img" tabindex="0"
        (pointermove)="hover($event)" (pointerleave)="leave()" (pointerup)="pin($event)"
        (keydown.arrowleft)="moveSelection(-1, $event)" (keydown.arrowright)="moveSelection(1, $event)" (keydown.escape)="clearSelection()">
        @for (tick of chartTicks(); track tick.y) {
          <line class="flow-chart__grid" [attr.x1]="chartLeft" [attr.y1]="tick.y" [attr.x2]="chartRight" [attr.y2]="tick.y" />
          <text class="flow-chart__y-label" [attr.x]="chartLeft - 12" [attr.y]="tick.y + 5" text-anchor="end">{{ tick.label }}</text>
        }
        <line class="flow-chart__y-axis" [attr.x1]="chartLeft" [attr.y1]="chartTop" [attr.x2]="chartLeft" [attr.y2]="chartBottom" />
        <line class="flow-chart__axis" [attr.x1]="chartLeft" [attr.y1]="chartZeroY" [attr.x2]="chartRight" [attr.y2]="chartZeroY" />
        @if (flowMode() === 'instant') {
          @for (point of chartPoints(); track point.index) {
            <rect class="flow-chart__income" [attr.x]="point.incomeX" [attr.y]="point.incomeY" [attr.width]="point.barWidth" [attr.height]="point.incomeHeight" />
            <rect class="flow-chart__expense" [attr.x]="point.expenseX" [attr.y]="chartZeroY" [attr.width]="point.barWidth" [attr.height]="point.expenseHeight" />
            @if (point.showLabel) { <text class="flow-chart__label" [attr.x]="point.x" [attr.y]="chartHeight - 12" text-anchor="middle">{{ point.label }}</text> }
          }
        } @else {
          <polyline class="flow-chart__cumulative" [attr.points]="cumulativePolyline()" />
          @for (point of chartPoints(); track point.index) {
            <circle class="flow-chart__point" [attr.cx]="point.x" [attr.cy]="point.cumulativeY" r="4" />
            @if (point.showLabel) { <text class="flow-chart__label" [attr.x]="point.x" [attr.y]="chartHeight - 12" text-anchor="middle">{{ point.label }}</text> }
          }
        }
        @if (activePoint(); as point) { <line class="flow-chart__cursor" [attr.x1]="point.x" [attr.y1]="chartTop" [attr.x2]="point.x" [attr.y2]="chartBottom" /> }
      </svg>
      @if (activePoint(); as point) {
        <div class="flow-chart__tooltip" [style.left.%]="point.xPercent">
          <strong>{{ point.date }}</strong>
          @if (flowMode() === 'instant') {
            <span>{{ i18n.t('home.income') }} <b>{{ point.income }}</b></span>
            <span>{{ i18n.t('home.expense') }} <b>{{ point.expense }}</b></span>
            <span>{{ i18n.t('home.netFlow') }} <b>{{ point.net }}</b></span>
          } @else { <span>{{ i18n.t('home.cumulative') }} <b>{{ point.cumulative }}</b></span> }
        </div>
      }
      @if (totalIncome() === 0 && totalExpense() === 0) { <span class="flow-chart__empty">{{ i18n.t('home.noFlow') }}</span> }
    </div>
    <footer class="flow-legend">
      @if (flowMode() === 'instant') {
        <span><i class="flow-legend__dot flow-legend__dot--income"></i>{{ i18n.t('home.income') }}</span>
        <span><i class="flow-legend__dot flow-legend__dot--expense"></i>{{ i18n.t('home.expense') }}</span>
      } @else { <span><i class="flow-legend__dot flow-legend__dot--cumulative"></i>{{ i18n.t('home.cumulative') }}</span> }
    </footer>
  `,
  styles: `
    :host { min-width: 0; min-height: 0; display: grid; grid-template-rows: minmax(0, 1fr) auto; }
    .flow-chart { position: relative; min-width: 0; min-height: 0; height: 100%; padding: var(--space-2) var(--space-3) 0; overflow: hidden; }
    .flow-chart svg { display: block; width: 100%; height: 100%; min-height: 200px; cursor: crosshair; }
    .flow-chart__grid { stroke: var(--line); stroke-width: 1; stroke-dasharray: 5 5; }
    .flow-chart__axis, .flow-chart__y-axis { stroke: var(--line-strong); stroke-width: 1.5; }
    .flow-chart__income { fill: var(--green); stroke: var(--line-strong); stroke-width: 1.5; }
    .flow-chart__expense { fill: var(--yellow); stroke: var(--line-strong); stroke-width: 1.5; }
    .flow-chart__cumulative { fill: none; stroke: var(--blue); stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; }
    .flow-chart__point { fill: var(--blue); stroke: var(--line-strong); stroke-width: 1.5; }
    .flow-chart__cursor { stroke: var(--blue-strong); stroke-width: 2; stroke-dasharray: 6 5; pointer-events: none; }
    .flow-chart__label, .flow-chart__y-label { fill: var(--text-muted); font-weight: 650; pointer-events: none; }
    .flow-chart__label { font-size: var(--chart-x-label-font-size); }
    .flow-chart__y-label { font-size: 22px; font-variant-numeric: tabular-nums; }
    .flow-chart__tooltip { position: absolute; top: var(--space-3); z-index: 2; min-width: 180px; display: grid; gap: var(--space-1); padding: var(--space-2) var(--space-3); transform: translateX(-50%); border: var(--border-width) solid var(--line-strong); border-radius: var(--radius-sm); background: var(--surface); box-shadow: var(--compact-shadow); font-size: var(--control-detail-font-size); pointer-events: none; }
    .flow-chart__tooltip strong { font-weight: 800; }
    .flow-chart__tooltip span { display: flex; justify-content: space-between; gap: var(--space-3); color: var(--text-muted); }
    .flow-chart__tooltip b { color: var(--text); font-weight: 780; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .flow-chart__empty { position: absolute; inset: 0; display: grid; place-items: center; color: var(--text-muted); font-size: var(--control-font-size); pointer-events: none; }
    .flow-legend { min-width: 0; display: flex; flex-wrap: wrap; justify-content: center; gap: var(--space-4); padding: 0 var(--space-4) var(--space-4); color: var(--text-muted); font-size: var(--control-detail-font-size); font-weight: 650; }
    .flow-legend span { display: inline-flex; align-items: center; gap: var(--space-2); }
    .flow-legend__dot { width: var(--space-3); height: var(--space-3); border: 1px solid var(--line-strong); border-radius: var(--radius-icon); }
    .flow-legend__dot--income { background: var(--green); } .flow-legend__dot--expense { background: var(--yellow); } .flow-legend__dot--cumulative { background: var(--blue); }
    @container (max-width: 620px) { .flow-chart svg { min-height: 0; } }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HomeFlowChartComponent {
  readonly i18n = inject(I18nService);
  readonly points = input.required<readonly CashFlowPoint[]>();
  readonly currency = input.required<LedgerCurrency | null>();
  readonly range = input.required<HomeFlowRange | null>();
  readonly periodMode = input.required<PeriodMode>();
  readonly flowMode = input.required<HomeFlowMode>();
  readonly hoveredIndex = signal<number | null>(null);
  readonly pinnedIndex = signal<number | null>(null);
  readonly chartWidth = CHART_WIDTH; readonly chartHeight = CHART_HEIGHT; readonly chartLeft = CHART_LEFT;
  readonly chartRight = CHART_WIDTH - CHART_RIGHT; readonly chartTop = CHART_TOP; readonly chartBottom = CHART_HEIGHT - CHART_BOTTOM; readonly chartZeroY = CHART_ZERO_Y;
  private readonly dateFormatter = new Intl.DateTimeFormat(undefined, { year: 'numeric', month: '2-digit', day: '2-digit' });
  private readonly chartDateFormatters: Record<ChartDateLabelDetail, Intl.DateTimeFormat> = {
    day: new Intl.DateTimeFormat(undefined, { day: 'numeric' }), month: new Intl.DateTimeFormat(undefined, { day: '2-digit', month: '2-digit' }), year: new Intl.DateTimeFormat(undefined, { day: '2-digit', month: '2-digit', year: 'numeric' }),
  };
  readonly totalIncome = computed(() => this.points().reduce((sum, point) => sum + point.income, 0));
  readonly totalExpense = computed(() => this.points().reduce((sum, point) => sum + point.expense, 0));
  readonly cumulativeValues = computed(() => { let running = 0; return this.points().map(point => running += point.income - point.expense); });
  readonly chartScale = computed(() => Math.max(1, ...(this.flowMode() === 'instant' ? this.points().flatMap(point => [point.income, point.expense]) : this.cumulativeValues().map(Math.abs))));
  readonly chartTicks = computed<ChartTickView[]>(() => [1, .5, 0, -.5, -1].map(factor => ({ y: CHART_ZERO_Y - factor * (CHART_PLOT_HEIGHT / 2), label: this.formatTick(this.chartScale() * factor) })));
  readonly chartPoints = computed<ChartPointView[]>(() => {
    const range = this.range(); const currency = this.currency(); const points = this.points(); if (!range || !currency) return [];
    const cumulative = this.cumulativeValues(); const scale = (CHART_PLOT_HEIGHT / 2) / this.chartScale(); const slot = CHART_PLOT_WIDTH / Math.max(1, points.length);
    const barWidth = Math.max(CHART_MIN_BAR_WIDTH, Math.min(CHART_MAX_BAR_WIDTH, slot * CHART_BAR_WIDTH_RATIO));
    const detail = this.periodMode() === 'range' ? this.labelDetail(range) : 'day'; const target = detail === 'year' ? CHART_X_LABEL_WITH_YEAR_TARGET_COUNT : CHART_X_LABEL_TARGET_COUNT;
    const stride = Math.max(1, Math.ceil(points.length / target)); const offset = Math.floor(stride / 2); const pointWidth = homeChartPointWidth(range);
    return points.map((point, index) => { const x = CHART_LEFT + slot * index + slot / 2; const cumulativeValue = cumulative[index] ?? 0; const timestamp = range.from + index * pointWidth; const incomeHeight = point.income * scale; return {
      index, x, xPercent: Math.min(86, Math.max(14, x / CHART_WIDTH * 100)), barWidth, incomeX: x - barWidth / 2, expenseX: x - barWidth / 2,
      incomeY: CHART_ZERO_Y - incomeHeight, incomeHeight, expenseHeight: point.expense * scale, cumulativeY: CHART_ZERO_Y - cumulativeValue * scale,
      label: this.chartDateFormatters[detail].format(new Date(timestamp * 1000)), showLabel: index % stride === offset, date: this.dateFormatter.format(new Date(timestamp * 1000)),
      income: formatCurrencyAmount(point.income, currency), expense: formatCurrencyAmount(point.expense, currency), net: formatCurrencyAmount(point.income - point.expense, currency), cumulative: formatCurrencyAmount(cumulativeValue, currency),
    }; });
  });
  readonly cumulativePolyline = computed(() => this.chartPoints().map(point => `${point.x},${point.cumulativeY}`).join(' '));
  readonly activePoint = computed(() => { const index = this.pinnedIndex() ?? this.hoveredIndex(); return index === null ? null : this.chartPoints()[index] ?? null; });
  hover(event: PointerEvent): void { if (event.pointerType && event.pointerType !== 'mouse') return; this.pinnedIndex.set(null); this.hoveredIndex.set(this.indexAt(event)); }
  leave(): void { this.hoveredIndex.set(null); }
  pin(event: PointerEvent): void { if (event.pointerType === 'mouse') return; const index = this.indexAt(event); if (index !== null) this.pinnedIndex.update(current => current === index ? null : index); }
  keepSelection(event: PointerEvent): void { event.stopPropagation(); }
  @HostListener('document:pointerdown') clearSelection(): void { this.hoveredIndex.set(null); this.pinnedIndex.set(null); }
  moveSelection(delta: number, event: Event): void { const points = this.chartPoints(); if (!points.length) return; event.preventDefault(); const current = this.pinnedIndex() ?? this.hoveredIndex() ?? (delta > 0 ? -1 : points.length); this.pinnedIndex.set(Math.max(0, Math.min(points.length - 1, current + delta))); this.hoveredIndex.set(null); }
  private indexAt(event: MouseEvent | PointerEvent): number | null { const target = event.currentTarget; if (!(target instanceof SVGSVGElement)) return null; const points = this.chartPoints(); const bounds = target.getBoundingClientRect(); if (!points.length || bounds.width <= 0) return null; const x = (event.clientX - bounds.left) / bounds.width * CHART_WIDTH; const slot = CHART_PLOT_WIDTH / points.length; return Math.max(0, Math.min(points.length - 1, Math.round((x - CHART_LEFT - slot / 2) / slot))); }
  private labelDetail(range: HomeFlowRange): ChartDateLabelDetail { const from = new Date(range.from * 1000); const to = new Date((range.to - 1) * 1000); if (from.getFullYear() !== to.getFullYear()) return 'year'; if (from.getMonth() !== to.getMonth()) return 'month'; return 'day'; }
  private formatTick(value: number): string { const currency = this.currency(); if (!currency) return String(value); const major = value / 10 ** currency.decimal_places; return Math.abs(major) >= 1000 ? new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(major) : new Intl.NumberFormat(undefined, { maximumSignificantDigits: 4 }).format(major); }
}
