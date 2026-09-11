import type { FinancialEventType } from '../../core/ledgers/financial-events.models';
import type { IconName } from '../ui/icon.component';

export type FinancialEventTone = 'green' | 'yellow' | 'blue';

interface FinancialEventPresentation {
  icon: IconName;
  tone: FinancialEventTone;
}

export function financialEventPresentation(type: FinancialEventType): FinancialEventPresentation {
  if (type === 'SHOPPING_LIST') return { icon: 'LucideShoppingCart', tone: 'yellow' };
  if (type === 'ACCOUNT_TRANSFER') return { icon: 'LucideArrowLeftRight', tone: 'blue' };
  return { icon: 'LucideWallet', tone: 'green' };
}
