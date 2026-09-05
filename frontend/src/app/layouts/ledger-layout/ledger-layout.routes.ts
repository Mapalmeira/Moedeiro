import { Routes } from '@angular/router';
import { ledgerSectionRouteData } from './ledger-sections';

export const LEDGER_LAYOUT_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'home',
  },
  {
    path: 'home',
    data: ledgerSectionRouteData('home'),
    loadComponent: () => import('../../features/ledgers/workspace/home/ledger-home.component').then((m) => m.LedgerHomeComponent),
  },
  {
    path: 'activity',
    data: ledgerSectionRouteData('activity'),
    loadComponent: () => import('../../features/ledgers/workspace/activity/ledger-activity.component').then((m) => m.LedgerActivityComponent),
  },
  {
    path: 'budgets',
    data: ledgerSectionRouteData('budgets'),
    loadComponent: () => import('../../features/ledgers/workspace/budgets/ledger-budgets.component').then((m) => m.LedgerBudgetsComponent),
  },
  {
    path: 'analytics',
    data: ledgerSectionRouteData('analytics'),
    loadComponent: () => import('../../features/ledgers/workspace/analytics/ledger-analytics.component').then((m) => m.LedgerAnalyticsComponent),
  },
  {
    path: 'accounts',
    data: ledgerSectionRouteData('accounts'),
    loadComponent: () => import('../../features/ledgers/workspace/accounts/ledger-accounts.component').then((m) => m.LedgerAccountsComponent),
  },
  {
    path: 'categories',
    data: ledgerSectionRouteData('categories'),
    loadComponent: () => import('../../features/ledgers/workspace/categories/ledger-categories.component').then((m) => m.LedgerCategoriesComponent),
  },
  {
    path: 'currencies',
    data: ledgerSectionRouteData('currencies'),
    loadComponent: () => import('../../features/ledgers/workspace/currencies/ledger-currencies.component').then((m) => m.LedgerCurrenciesComponent),
  },
  {
    path: '**',
    redirectTo: 'home',
  },
];
