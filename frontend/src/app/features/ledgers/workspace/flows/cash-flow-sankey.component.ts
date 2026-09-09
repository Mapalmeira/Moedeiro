import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { CashFlowSankey, CashFlowSankeyLink, CashFlowSankeyNode } from '../../../../core/ledgers/cash-flow.models';
import { formatCurrencyAmount } from '../../../../core/ledgers/currency-format';
import { LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import { NumberFormat } from '../../../../core/preferences/preferences.models';

type SankeySide = CashFlowSankeyNode['side'] | 'surplus';
type SankeyKind = CashFlowSankeyNode['kind'] | 'surplus';
type SankeyTone = 'income' | 'expense' | 'account' | 'surplus';

interface SankeySourceNode {
  id: string;
  kind: SankeyKind;
  side: SankeySide;
  label: string;
  column: number;
  order: number;
  value: number;
  category_uuid: string | null;
}

interface SankeyNodeView extends SankeySourceNode {
  x: number;
  y: number;
  width: number;
  height: number;
  shortLabel: string;
  labelX: number;
  labelY: number;
  labelAnchor: 'start' | 'middle' | 'end';
  tone: SankeyTone;
}

interface SankeyLinkView extends CashFlowSankeyLink {
  path: string;
  width: number;
  tone: SankeyTone;
}

interface SankeyLayout {
  width: number;
  height: number;
  nodes: SankeyNodeView[];
  links: SankeyLinkView[];
}

interface SankeyTooltip {
  value: string;
  x: number;
  y: number;
}

const NODE_WIDTH = 18;
const COLUMN_GAP = 188;
const NODE_GAP = 14;
const CHART_PADDING_INLINE = 130;
const CHART_PADDING_BLOCK = 44;
const CHART_MIN_HEIGHT = 480;
const CHART_MIN_WIDTH = 900;
const LABEL_GAP = 9;
const LABEL_MAX_LENGTH = 18;
const SURPLUS_NODE_ID = 'surplus';

@Component({
  selector: 'app-cash-flow-sankey',
  standalone: true,
  template: `
    <div class="sankey-shell">
      <div class="sankey-viewport">
        <div class="sankey-canvas">
        <svg class="sankey" [attr.viewBox]="'0 0 ' + layout().width + ' ' + layout().height"
          [style.width.px]="layout().width" [style.height.px]="layout().height" role="img" [attr.aria-label]="ariaLabel()">
          <g class="sankey__links">
            @for (link of layout().links; track link.source + '>' + link.target) {
              <path class="sankey__link"
                [class.sankey__link--income]="link.tone === 'income'"
                [class.sankey__link--expense]="link.tone === 'expense'"
                [class.sankey__link--surplus]="link.tone === 'surplus'"
                [attr.d]="link.path" [attr.stroke-width]="link.width"
                [attr.aria-label]="formatValue(link.value)"
                (pointerenter)="showValue($event, link.value)" (pointermove)="showValue($event, link.value)" (pointerleave)="hideValue()" />
            }
          </g>
          <g class="sankey__nodes">
            @for (node of layout().nodes; track node.id) {
              <g class="sankey__node-group" [attr.aria-label]="node.label + ': ' + formatValue(node.value)"
                (pointerenter)="showValue($event, node.value)" (pointermove)="showValue($event, node.value)" (pointerleave)="hideValue()">
                <rect class="sankey__node"
                  [class.sankey__node--income]="node.tone === 'income'"
                  [class.sankey__node--expense]="node.tone === 'expense'"
                  [class.sankey__node--account]="node.tone === 'account'"
                  [class.sankey__node--surplus]="node.tone === 'surplus'"
                  [attr.x]="node.x" [attr.y]="node.y" [attr.width]="node.width" [attr.height]="node.height" rx="4" ry="4" />
                <text class="sankey__label" [attr.x]="node.labelX" [attr.y]="node.labelY" [attr.text-anchor]="node.labelAnchor">
                  {{ node.shortLabel }}
                </text>
              </g>
            }
          </g>
          </svg>
        </div>
      </div>
      @if (tooltip(); as currentTooltip) {
        <div class="sankey__tooltip" [style.left.px]="currentTooltip.x" [style.top.px]="currentTooltip.y">
          {{ currentTooltip.value }}
        </div>
      }
    </div>
  `,
  styles: `
    :host { display: block; min-width: 0; min-height: 0; }
    .sankey-shell {
      position: relative;
      width: 100%;
      height: 100%;
      min-width: 0;
      min-height: 0;
    }
    .sankey-viewport {
      position: relative;
      width: 100%;
      height: 100%;
      min-width: 0;
      min-height: 0;
      overflow: auto;
      overscroll-behavior: contain;
      scrollbar-gutter: stable;
    }
    .sankey-canvas {
      width: max-content;
      height: max-content;
      min-width: 100%;
      min-height: 100%;
      display: grid;
      place-items: center;
    }
    .sankey { display: block; flex: 0 0 auto; }
    .sankey__link {
      fill: none;
      stroke-opacity: .42;
      stroke-linecap: butt;
      transition: stroke-opacity var(--motion-selection) ease;
    }
    .sankey__link--income { stroke: var(--green-strong); }
    .sankey__link--expense { stroke: var(--danger); }
    .sankey__link--surplus { stroke: var(--blue-strong); }
    .sankey__link:hover { stroke-opacity: .72; }
    .sankey__node {
      stroke: var(--line-strong);
      stroke-width: var(--border-width);
    }
    .sankey__node--income { fill: var(--green-strong); }
    .sankey__node--expense { fill: var(--danger); }
    .sankey__node--account { fill: var(--orange); }
    .sankey__node--surplus { fill: var(--blue-strong); }
    .sankey__label {
      fill: var(--text);
      font-size: var(--control-font-size);
      font-weight: var(--control-font-weight);
      dominant-baseline: middle;
    }
    .sankey__tooltip {
      position: fixed;
      z-index: var(--layer-toast);
      width: max-content;
      max-width: calc(100vw - (2 * var(--space-4)));
      padding: var(--space-1) var(--space-2);
      border: var(--border-width) solid var(--line-strong);
      border-radius: var(--radius-sm);
      background: var(--surface);
      box-shadow: var(--compact-shadow);
      color: var(--text);
      font-size: var(--control-detail-font-size);
      font-weight: var(--control-font-weight);
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
      pointer-events: none;
      transform: translate(var(--space-3), var(--space-3));
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CashFlowSankeyComponent {
  private readonly i18n = inject(I18nService);

  readonly graph = input.required<CashFlowSankey>();
  readonly currency = input.required<LedgerCurrency>();
  readonly numberFormat = input.required<NumberFormat>();
  readonly ariaLabel = input('');

  readonly layout = computed<SankeyLayout>(() => this.buildLayout(this.graph()));
  readonly tooltip = signal<SankeyTooltip | null>(null);

  showValue(event: PointerEvent, value: number): void {
    this.tooltip.set({ value: this.formatValue(value), x: event.clientX, y: event.clientY });
  }

  hideValue(): void {
    this.tooltip.set(null);
  }

  formatValue(value: number): string {
    return formatCurrencyAmount(value, this.currency(), this.numberFormat());
  }

  private buildLayout(graph: CashFlowSankey): SankeyLayout {
    if (!graph.nodes.length) return { width: CHART_MIN_WIDTH, height: CHART_MIN_HEIGHT, nodes: [], links: [] };

    const sourceNodes: SankeySourceNode[] = graph.nodes.map(node => ({
      id: node.id,
      kind: node.kind,
      side: node.side,
      label: node.label,
      column: node.column,
      order: node.order,
      value: node.value,
      category_uuid: node.category_uuid,
    }));
    const sourceLinks: CashFlowSankeyLink[] = [...graph.links];
    const accountNode = sourceNodes.find(node => node.side === 'account');
    const surplus = Math.max(0, graph.income - graph.expense);
    if (accountNode && surplus > 0) {
      sourceNodes.push({
        id: SURPLUS_NODE_ID,
        kind: 'surplus',
        side: 'surplus',
        label: this.i18n.t('flows.surplus'),
        column: accountNode.column + 1,
        order: Number.MAX_SAFE_INTEGER,
        value: surplus,
        category_uuid: null,
      });
      sourceLinks.push({ source: accountNode.id, target: SURPLUS_NODE_ID, value: surplus });
    }

    const maxColumn = Math.max(...sourceNodes.map(node => node.column));
    const width = Math.max(CHART_MIN_WIDTH, (2 * CHART_PADDING_INLINE) + (maxColumn * COLUMN_GAP) + NODE_WIDTH);
    const columns = new Map<number, SankeySourceNode[]>();
    for (const node of sourceNodes) {
      const column = columns.get(node.column) ?? [];
      column.push(node);
      columns.set(node.column, column);
    }
    for (const nodes of columns.values()) nodes.sort((a, b) => a.order - b.order || a.label.localeCompare(b.label));

    const maxColumnSize = Math.max(...[...columns.values()].map(nodes => nodes.length));
    const height = Math.max(CHART_MIN_HEIGHT, (2 * CHART_PADDING_BLOCK) + maxColumnSize * 42 + Math.max(0, maxColumnSize - 1) * NODE_GAP);
    const availableHeight = height - (2 * CHART_PADDING_BLOCK);
    const scaleCandidates = [...columns.values()].flatMap(nodes => {
      const total = nodes.reduce((sum, node) => sum + node.value, 0);
      if (total <= 0) return [];
      const gapHeight = Math.max(0, nodes.length - 1) * NODE_GAP;
      return [(availableHeight - gapHeight) / total];
    });
    const scale = scaleCandidates.length ? Math.max(0, Math.min(...scaleCandidates)) : 0;

    const views: SankeyNodeView[] = [];
    for (const [column, nodes] of columns) {
      const renderedHeight = nodes.reduce((sum, node) => sum + node.value * scale, 0) + Math.max(0, nodes.length - 1) * NODE_GAP;
      let y = CHART_PADDING_BLOCK + Math.max(0, (availableHeight - renderedHeight) / 2);
      const x = CHART_PADDING_INLINE + column * COLUMN_GAP;
      for (const node of nodes) {
        const nodeHeight = Math.max(2, node.value * scale);
        const label = this.truncateLabel(node.label);
        const account = node.side === 'account';
        const income = node.side === 'income';
        views.push({
          ...node,
          x,
          y,
          width: NODE_WIDTH,
          height: nodeHeight,
          shortLabel: label,
          labelX: account ? x + NODE_WIDTH / 2 : income ? x - LABEL_GAP : x + NODE_WIDTH + LABEL_GAP,
          labelY: account ? y - LABEL_GAP - 2 : y + nodeHeight / 2,
          labelAnchor: account ? 'middle' : income ? 'end' : 'start',
          tone: this.nodeTone(node.side),
        });
        y += nodeHeight + NODE_GAP;
      }
    }

    const nodeById = new Map(views.map(node => [node.id, node] as const));
    const outgoing = new Map<string, CashFlowSankeyLink[]>();
    const incoming = new Map<string, CashFlowSankeyLink[]>();
    for (const link of sourceLinks) {
      const sourceLinksForNode = outgoing.get(link.source) ?? [];
      sourceLinksForNode.push(link);
      outgoing.set(link.source, sourceLinksForNode);
      const targetLinksForNode = incoming.get(link.target) ?? [];
      targetLinksForNode.push(link);
      incoming.set(link.target, targetLinksForNode);
    }
    for (const links of outgoing.values()) links.sort((a, b) => (nodeById.get(a.target)?.y ?? 0) - (nodeById.get(b.target)?.y ?? 0));
    for (const links of incoming.values()) links.sort((a, b) => (nodeById.get(a.source)?.y ?? 0) - (nodeById.get(b.source)?.y ?? 0));

    const sourceY = new Map<CashFlowSankeyLink, number>();
    const targetY = new Map<CashFlowSankeyLink, number>();
    for (const node of views) {
      const out = outgoing.get(node.id) ?? [];
      const outHeight = out.reduce((sum, link) => sum + link.value * scale, 0);
      let offset = node.y + Math.max(0, (node.height - outHeight) / 2);
      for (const link of out) {
        const linkHeight = link.value * scale;
        sourceY.set(link, offset + linkHeight / 2);
        offset += linkHeight;
      }

      const inc = incoming.get(node.id) ?? [];
      const inHeight = inc.reduce((sum, link) => sum + link.value * scale, 0);
      offset = node.y + Math.max(0, (node.height - inHeight) / 2);
      for (const link of inc) {
        const linkHeight = link.value * scale;
        targetY.set(link, offset + linkHeight / 2);
        offset += linkHeight;
      }
    }

    const links: SankeyLinkView[] = [];
    for (const link of sourceLinks) {
      const source = nodeById.get(link.source);
      const target = nodeById.get(link.target);
      if (!source || !target || link.value <= 0) continue;
      const startX = source.x + source.width;
      const endX = target.x;
      const startY = sourceY.get(link) ?? source.y + source.height / 2;
      const endY = targetY.get(link) ?? target.y + target.height / 2;
      const curve = (endX - startX) * .46;
      links.push({
        ...link,
        path: `M ${startX} ${startY} C ${startX + curve} ${startY}, ${endX - curve} ${endY}, ${endX} ${endY}`,
        width: Math.max(1.5, link.value * scale),
        tone: target.side === 'surplus' ? 'surplus' : source.side === 'income' ? 'income' : 'expense',
      });
    }
    links.sort((a, b) => b.width - a.width);

    return { width, height, nodes: views, links };
  }

  private nodeTone(side: SankeySide): SankeyTone {
    return side;
  }

  private truncateLabel(value: string): string {
    return value.length <= LABEL_MAX_LENGTH ? value : `${value.slice(0, LABEL_MAX_LENGTH - 1)}…`;
  }
}
