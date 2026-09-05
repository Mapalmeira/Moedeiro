export interface ContrastResult {
  foreground: '#000000' | '#FFFFFF';
  ratio: number;
}

function linearize(value: number): number {
  const channel = value / 255;
  return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
}

function luminance(hex: string): number {
  const normalized = /^#[0-9A-Fa-f]{6}$/.test(hex) ? hex : '#FFFFFF';
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

export function bestContrastingForeground(background: string): ContrastResult {
  const backgroundLuminance = luminance(background);
  const blackRatio = contrastRatio(backgroundLuminance, 0);
  const whiteRatio = contrastRatio(backgroundLuminance, 1);

  return whiteRatio > blackRatio
    ? { foreground: '#FFFFFF', ratio: whiteRatio }
    : { foreground: '#000000', ratio: blackRatio };
}
