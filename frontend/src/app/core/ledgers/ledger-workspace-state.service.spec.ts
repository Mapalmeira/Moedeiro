import { describe, expect, it } from 'vitest';
import { LedgerWorkspaceStateService } from './ledger-workspace-state.service';

describe('LedgerWorkspaceStateService', () => {
  it('keeps independent filter snapshots for each ledger', () => {
    const service = new LedgerWorkspaceStateService();
    const filters = {
      from_date: '2026-09-01',
      to_date: '2026-09-09',
      account_uuid: 'account',
      category_uuid: 'category',
      event_type: 'TRANSACTION' as const,
    };

    service.setActivity('ledger-a', filters);

    expect(service.getActivity('ledger-a')).toEqual(filters);
    expect(service.getActivity('ledger-b')).toBeNull();
  });

  it('keeps each workspace section without exposing snapshots for mutation', () => {
    const service = new LedgerWorkspaceStateService();
    service.setHome('ledger', {
      currency_uuid: 'currency',
      flow_account_uuid: 'account',
      month: '2026-09',
      period_mode: 'month',
      range_from_date: '',
      range_to_date: '',
      flow_mode: 'instant',
    });
    service.setBudgets('ledger', {
      states: ['ACTIVE'],
      category_uuid: 'category',
      search: 'food',
    });

    const restored = service.getBudgets('ledger')!;
    restored.states = [];

    expect(service.getHome('ledger')!.currency_uuid).toBe('currency');
    expect(service.getBudgets('ledger')).toEqual({
      states: ['ACTIVE'],
      category_uuid: 'category',
      search: 'food',
    });
  });
});
