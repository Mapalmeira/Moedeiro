import type { FinancialEventType } from '../../core/ledgers/financial-events.models';
import type { IconName } from '../ui/icon.component';

export type FinancialEventTone = 'green' | 'yellow' | 'blue';

export interface FinancialEventPresentation {
  icon: IconName;
  tone: FinancialEventTone;
}

export function financialEventPresentation(type: FinancialEventType): FinancialEventPresentation {
  if (type === 'SHOPPING_LIST') return { icon: 'shopping-cart', tone: 'yellow' };
  if (type === 'ACCOUNT_TRANSFER') return { icon: 'arrow-left-right', tone: 'blue' };
  return { icon: 'wallet', tone: 'green' };
}
