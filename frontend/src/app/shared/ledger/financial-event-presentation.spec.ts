import { financialEventPresentation } from './financial-event-presentation';

describe('financialEventPresentation', () => {
  it('keeps one presentation contract per event type', () => {
    expect(financialEventPresentation('TRANSACTION')).toEqual({ icon: 'wallet', tone: 'green' });
    expect(financialEventPresentation('SHOPPING_LIST')).toEqual({ icon: 'shopping-cart', tone: 'yellow' });
    expect(financialEventPresentation('ACCOUNT_TRANSFER')).toEqual({ icon: 'arrow-left-right', tone: 'blue' });
  });
});
