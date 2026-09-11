import { financialEventPresentation } from './financial-event-presentation';

describe('financialEventPresentation', () => {
  it('keeps one presentation contract per event type', () => {
    expect(financialEventPresentation('TRANSACTION')).toEqual({ icon: 'LucideWallet', tone: 'green' });
    expect(financialEventPresentation('SHOPPING_LIST')).toEqual({ icon: 'LucideShoppingCart', tone: 'yellow' });
    expect(financialEventPresentation('ACCOUNT_TRANSFER')).toEqual({ icon: 'LucideArrowLeftRight', tone: 'blue' });
  });
});
