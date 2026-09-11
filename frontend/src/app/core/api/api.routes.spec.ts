import { describe, expect, it } from 'vitest';
import { API_ROUTES } from './api.routes';

describe('API_ROUTES', () => {
  it('encodes ledger and resource identifiers in nested routes', () => {
    expect(API_ROUTES.ledgers.accounts.byUuid('ledger/1', 'account 1')).toBe('/api/ledgers/ledger%2F1/accounts/account%201');
    expect(API_ROUTES.ledgers.budgets.byUuid('ledger/1', 'budget?1')).toBe('/api/ledgers/ledger%2F1/budgets/budget%3F1');
  });

  it('keeps derived endpoints on their resource roots', () => {
    expect(API_ROUTES.ledgers.categories.tree('ledger')).toBe('/api/ledgers/ledger/categories/tree');
    expect(API_ROUTES.ledgers.budgets.currencyOverview('ledger')).toBe('/api/ledgers/ledger/budgets/currency-overview');
    expect(API_ROUTES.ledgers.cashFlow.sankey('ledger')).toBe('/api/ledgers/ledger/cash-flow/sankey');
  });
});
