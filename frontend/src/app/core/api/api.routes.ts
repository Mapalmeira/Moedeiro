const ledgerRoot = (ledgerUuid: string) => `/api/ledgers/${encodeURIComponent(ledgerUuid)}`;
const resourceRoot = (ledgerUuid: string, resource: string) => `${ledgerRoot(ledgerUuid)}/${resource}`;
const resourceByUuid = (ledgerUuid: string, resource: string, resourceUuid: string) => `${resourceRoot(ledgerUuid, resource)}/${encodeURIComponent(resourceUuid)}`;

export const API_ROUTES = {
  authentication: {
    login: '/api/authentication/login',
    session: '/api/authentication/session',
    refresh: '/api/authentication/refresh',
    logout: '/api/authentication/logout',
  },
  password: {
    change: '/api/password/change',
    recovery: '/api/password/recovery',
  },
  registration: '/api/registration',
  totp: {
    setup: '/api/totp/setup',
    confirm: '/api/totp/confirm',
    root: '/api/totp',
  },
  userPreferences: '/api/user/preferences',
  ledgers: {
    root: '/api/ledgers',
    byUuid: ledgerRoot,
    accounts: {
      root: (ledgerUuid: string) => resourceRoot(ledgerUuid, 'accounts'),
      byUuid: (ledgerUuid: string, accountUuid: string) => resourceByUuid(ledgerUuid, 'accounts', accountUuid),
      balance: (ledgerUuid: string, accountUuid: string) => `${resourceByUuid(ledgerUuid, 'accounts', accountUuid)}/balance`,
    },
    balances: (ledgerUuid: string) => resourceRoot(ledgerUuid, 'balances'),
    externalAccesses: {
      root: (ledgerUuid: string) => resourceRoot(ledgerUuid, 'external-accesses'),
      byGrantUuid: (ledgerUuid: string, grantUuid: string) => resourceByUuid(ledgerUuid, 'external-accesses', grantUuid),
    },
    currencies: {
      root: (ledgerUuid: string) => resourceRoot(ledgerUuid, 'currencies'),
      byUuid: (ledgerUuid: string, currencyUuid: string) => resourceByUuid(ledgerUuid, 'currencies', currencyUuid),
    },
    categories: {
      root: (ledgerUuid: string) => resourceRoot(ledgerUuid, 'categories'),
      byUuid: (ledgerUuid: string, categoryUuid: string) => resourceByUuid(ledgerUuid, 'categories', categoryUuid),
      tree: (ledgerUuid: string) => `${resourceRoot(ledgerUuid, 'categories')}/tree`,
    },
    events: {
      root: (ledgerUuid: string) => resourceRoot(ledgerUuid, 'events'),
      byUuid: (ledgerUuid: string, eventUuid: string) => resourceByUuid(ledgerUuid, 'events', eventUuid),
    },
    budgets: {
      root: (ledgerUuid: string) => resourceRoot(ledgerUuid, 'budgets'),
      byUuid: (ledgerUuid: string, budgetUuid: string) => resourceByUuid(ledgerUuid, 'budgets', budgetUuid),
      overview: (ledgerUuid: string) => `${resourceRoot(ledgerUuid, 'budgets')}/overview`,
      currencyOverview: (ledgerUuid: string) => `${resourceRoot(ledgerUuid, 'budgets')}/currency-overview`,
    },
    cashFlow: {
      root: (ledgerUuid: string) => resourceRoot(ledgerUuid, 'cash-flow'),
      points: (ledgerUuid: string) => `${resourceRoot(ledgerUuid, 'cash-flow')}/points`,
      sankey: (ledgerUuid: string) => `${resourceRoot(ledgerUuid, 'cash-flow')}/sankey`,
    },
  },
} as const;
