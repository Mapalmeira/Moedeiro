import { describe, expect, it } from 'vitest';
import { routes } from './app.routes';

const LEDGER_SECTION_PATHS = [
  'home',
  'activity',
  'budgets',
  'analytics',
  'accounts',
  'categories',
  'currencies',
];

describe('application routes', () => {
  it('uses a ledger layout with real English child routes', () => {
    const authenticatedShell = routes.find((route) => Array.isArray(route.children));
    const ledgerLayout = authenticatedShell?.children?.find((route) => route.path === 'ledgers/:ledgerUuid');
    const childPaths = ledgerLayout?.children?.map((route) => route.path) ?? [];

    expect(authenticatedShell?.children?.some((route) => route.path === 'home')).toBe(true);
    expect(ledgerLayout).toBeDefined();
    expect(childPaths).toEqual(['', ...LEDGER_SECTION_PATHS, '**']);
    expect(childPaths).not.toContain(':section');
    expect(childPaths).not.toContain('inicio');
  });

  it('lazy-loads every ledger section independently', () => {
    const authenticatedShell = routes.find((route) => Array.isArray(route.children));
    const ledgerLayout = authenticatedShell?.children?.find((route) => route.path === 'ledgers/:ledgerUuid');
    const sectionRoutes = ledgerLayout?.children?.filter((route) => LEDGER_SECTION_PATHS.includes(route.path ?? '')) ?? [];

    expect(sectionRoutes).toHaveLength(LEDGER_SECTION_PATHS.length);
    for (const route of sectionRoutes) {
      expect(route.loadComponent).toBeTypeOf('function');
      expect(route.data?.['ledgerSection']).toBe(route.path);
    }
  });
});
