type ListboxNavigationKey = 'ArrowDown' | 'ArrowUp' | 'Home' | 'End';

export function nextListboxIndex(current: number, length: number, key: ListboxNavigationKey): number {
  if (length <= 0) return -1;
  if (key === 'Home') return 0;
  if (key === 'End') return length - 1;
  if (current < 0 || current >= length) return key === 'ArrowUp' ? length - 1 : 0;
  return key === 'ArrowDown' ? (current + 1) % length : (current - 1 + length) % length;
}

export function isListboxNavigationKey(key: string): key is ListboxNavigationKey {
  return key === 'ArrowDown' || key === 'ArrowUp' || key === 'Home' || key === 'End';
}
