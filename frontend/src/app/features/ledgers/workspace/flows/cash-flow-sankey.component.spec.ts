import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it } from 'vitest';
import { I18nService } from '../../../../core/i18n/i18n.service';
import { CashFlowSankey } from '../../../../core/ledgers/cash-flow.models';
import { LedgerCurrency } from '../../../../core/ledgers/ledger-entities.models';
import { CashFlowSankeyComponent } from './cash-flow-sankey.component';

const currency: LedgerCurrency = {
  uuid: 'currency',
  name: 'Real',
  prefix: 'R$ ',
  suffix: null,
  decimal_places: 2,
  icon: 'unicode:R$',
  color_code: '#21E683',
};

function graph(nodes: CashFlowSankey['nodes'] = [], links: CashFlowSankey['links'] = []): CashFlowSankey {
  return {
    account_uuid: 'account',
    currency_uuid: currency.uuid,
    from_timestamp: 1,
    to_timestamp: 2,
    detail_level: 3,
    income: 100_00,
    expense: 60_00,
    nodes,
    links,
  };
}

describe('CashFlowSankeyComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [CashFlowSankeyComponent],
      providers: [{ provide: I18nService, useValue: { t: (key: string) => key === 'flows.surplus' ? 'Excedente' : key } }],
    });
  });

  it('renders a stable empty layout', () => {
    const fixture = TestBed.createComponent(CashFlowSankeyComponent);
    fixture.componentRef.setInput('graph', graph());
    fixture.componentRef.setInput('currency', currency);
    fixture.detectChanges();

    expect(fixture.componentInstance.layout()).toMatchObject({ width: 900, height: 480, nodes: [], links: [] });
    expect(fixture.nativeElement.querySelectorAll('.sankey__node')).toHaveLength(0);
  });

  it('builds finite nodes and links and represents positive surplus', () => {
    const fixture = TestBed.createComponent(CashFlowSankeyComponent);
    const value = graph(
      [
        { id: 'income', kind: 'category', side: 'income', label: 'Salário', color_code: '#21E683', column: 0, order: 0, value: 100_00, category_uuid: 'income-category' },
        { id: 'account', kind: 'account', side: 'account', label: 'Principal', color_code: '#FFD51A', column: 1, order: 0, value: 100_00, category_uuid: null },
        { id: 'expense', kind: 'category', side: 'expense', label: 'Moradia', color_code: '#FF6B6B', column: 2, order: 0, value: 60_00, category_uuid: 'expense-category' },
      ],
      [
        { source: 'income', target: 'account', value: 100_00 },
        { source: 'account', target: 'expense', value: 60_00 },
      ],
    );
    fixture.componentRef.setInput('graph', value);
    fixture.componentRef.setInput('currency', currency);
    fixture.componentRef.setInput('ariaLabel', 'Fluxos da conta Principal');
    fixture.detectChanges();

    const layout = fixture.componentInstance.layout();
    const surplus = layout.nodes.find(node => node.id === 'surplus');
    expect(surplus).toMatchObject({ label: 'Excedente', value: 40_00, tone: 'surplus' });
    expect(layout.links).toHaveLength(3);
    expect(layout.nodes.every(node => Number.isFinite(node.x) && Number.isFinite(node.y) && node.height >= 2)).toBe(true);
    expect(layout.links.every(link => Number.isFinite(link.width) && link.path.startsWith('M '))).toBe(true);
    expect(fixture.nativeElement.querySelector('svg')?.getAttribute('aria-label')).toBe('Fluxos da conta Principal');
  });

  it('formats tooltip values with the browser locale', () => {
    const fixture = TestBed.createComponent(CashFlowSankeyComponent);
    fixture.componentRef.setInput('graph', graph());
    fixture.componentRef.setInput('currency', currency);
    fixture.detectChanges();

    fixture.componentInstance.showValue({ clientX: 10, clientY: 20 } as PointerEvent, 12_34);

    const amount = new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(12.34);
    expect(fixture.componentInstance.tooltip()).toEqual({ value: `R$ ${amount}`, x: 10, y: 20 });
    fixture.componentInstance.hideValue();
    expect(fixture.componentInstance.tooltip()).toBeNull();
  });
});
