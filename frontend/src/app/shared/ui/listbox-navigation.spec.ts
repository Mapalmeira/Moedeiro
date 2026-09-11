import { nextListboxIndex } from './listbox-navigation';

describe('nextListboxIndex', () => {
  it('wraps arrow navigation and supports boundaries', () => {
    expect(nextListboxIndex(-1, 3, 'ArrowDown')).toBe(0);
    expect(nextListboxIndex(2, 3, 'ArrowDown')).toBe(0);
    expect(nextListboxIndex(0, 3, 'ArrowUp')).toBe(2);
    expect(nextListboxIndex(1, 3, 'Home')).toBe(0);
    expect(nextListboxIndex(1, 3, 'End')).toBe(2);
  });
});
