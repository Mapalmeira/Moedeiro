export function normalizeSearchText(value: string): string {
  return value.toLowerCase().normalize('NFD').replace(/\p{M}/gu, '');
}
