import { AbstractControl } from '@angular/forms';
import { decodeLucideLedgerIcon, decodeUnicodeLedgerIcon, isEncodedLucideLedgerIcon, isEncodedUnicodeLedgerIcon } from './ledger-icon-value';
import { resolveLucideIcon } from './lucide-icon-catalog';

export function entityIconValidator(control: AbstractControl): { icon: true } | null {
  const value = String(control.value);
  if (isEncodedLucideLedgerIcon(value) && resolveLucideIcon(decodeLucideLedgerIcon(value))) return null;
  const length = Array.from(decodeUnicodeLedgerIcon(value)).length;
  return isEncodedUnicodeLedgerIcon(value) && length >= 1 && length <= 3 ? null : { icon: true };
}
