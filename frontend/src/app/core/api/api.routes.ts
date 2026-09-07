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
    one: (ledgerUuid: string) => `/api/ledgers/${encodeURIComponent(ledgerUuid)}`,
  },
  ledgerAccounts: (ledgerUuid: string) => `/api/ledgers/${encodeURIComponent(ledgerUuid)}/accounts`,
  ledgerCurrencies: (ledgerUuid: string) => `/api/ledgers/${encodeURIComponent(ledgerUuid)}/currencies`,
  ledgerCategories: (ledgerUuid: string) => `/api/ledgers/${encodeURIComponent(ledgerUuid)}/categories`,
} as const;
