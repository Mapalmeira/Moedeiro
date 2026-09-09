import type { IconName } from '../../shared/ui/icon.component';

export type LedgerSectionKey = 'home' | 'activity' | 'budgets' | 'flows' | 'accounts' | 'categories' | 'currencies';
export type LedgerSectionTone = 'green' | 'yellow' | 'blue' | 'neutral';

export interface LedgerSectionItem {
  key: LedgerSectionKey;
  labelKey: 'ledgerShell.home' | 'ledgerShell.activity' | 'ledgerShell.budgets' | 'ledgerShell.flows' | 'ledgerShell.accounts' | 'ledgerShell.categories' | 'ledgerShell.currencies';
  icon: IconName;
  tone: LedgerSectionTone;
}

export const LEDGER_SECTION_ITEMS: readonly LedgerSectionItem[] = [
  { key: 'home', labelKey: 'ledgerShell.home', icon: 'house', tone: 'green' },
  { key: 'activity', labelKey: 'ledgerShell.activity', icon: 'arrow-left-right', tone: 'green' },
  { key: 'budgets', labelKey: 'ledgerShell.budgets', icon: 'wallet', tone: 'yellow' },
  { key: 'flows', labelKey: 'ledgerShell.flows', icon: 'chart', tone: 'blue' },
  { key: 'accounts', labelKey: 'ledgerShell.accounts', icon: 'building', tone: 'green' },
  { key: 'categories', labelKey: 'ledgerShell.categories', icon: 'layers', tone: 'blue' },
  { key: 'currencies', labelKey: 'ledgerShell.currencies', icon: 'coins', tone: 'yellow' },
];

export const DEFAULT_LEDGER_SECTION = LEDGER_SECTION_ITEMS[0];

export function ledgerSectionRouteData(ledgerSection: LedgerSectionKey): { ledgerSection: LedgerSectionKey } {
  return { ledgerSection };
}

export function ledgerSectionByKey(key: string | undefined): LedgerSectionItem {
  return LEDGER_SECTION_ITEMS.find((item) => item.key === key) ?? DEFAULT_LEDGER_SECTION;
}
