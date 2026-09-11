export const HEX_COLOR_PATTERN = /^#[0-9A-Fa-f]{6}$/;

export interface LedgerAppearanceDefaults {
  readonly icon: string;
  readonly color: string;
}

export const DEFAULT_LEDGER_APPEARANCE: LedgerAppearanceDefaults = { icon: 'lucide:WalletCards', color: '#21E683' };
export const DEFAULT_ACCOUNT_APPEARANCE: LedgerAppearanceDefaults = DEFAULT_LEDGER_APPEARANCE;
export const DEFAULT_CURRENCY_APPEARANCE: LedgerAppearanceDefaults = { icon: 'lucide:Coins', color: '#FFD51A' };
export const DEFAULT_CATEGORY_APPEARANCE: LedgerAppearanceDefaults = { icon: 'lucide:Folder', color: '#488DFC' };

export function isHexColor(value: string): boolean {
  return HEX_COLOR_PATTERN.test(value);
}

function linearize(value: number): number {
  const channel = value / 255;
  return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  const normalized = isHexColor(hex) ? hex : '#FFFFFF';
  const red = Number.parseInt(normalized.slice(1, 3), 16);
  const green = Number.parseInt(normalized.slice(3, 5), 16);
  const blue = Number.parseInt(normalized.slice(5, 7), 16);
  return 0.2126 * linearize(red) + 0.7152 * linearize(green) + 0.0722 * linearize(blue);
}

function contrastRatio(first: number, second: number): number {
  const lighter = Math.max(first, second);
  const darker = Math.min(first, second);
  return (lighter + 0.05) / (darker + 0.05);
}

export function bestContrastingForeground(background: string): '#000000' | '#FFFFFF' {
  const backgroundLuminance = luminance(background);
  const blackRatio = contrastRatio(backgroundLuminance, 0);
  const whiteRatio = contrastRatio(backgroundLuminance, 1);
  return whiteRatio > blackRatio ? '#FFFFFF' : '#000000';
}
