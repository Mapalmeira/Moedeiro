import { describe, expect, it } from 'vitest';
import { routes } from './app.routes';

describe('application routes', () => {
  it('keeps ledger section URL segments in English', () => {
    const authenticatedShell = routes.find((route) => Array.isArray(route.children));
    const paths = authenticatedShell?.children?.map((route) => route.path) ?? [];

    expect(paths).toContain('home');
    expect(paths).toContain('ledgers/:ledgerUuid/:section');
    expect(paths).toContain('ledgers/:ledgerUuid');
    expect(paths).not.toContain('inicio');
    expect(paths).not.toContain('ledgers/:ledgerUuid/inicio');
  });
});
