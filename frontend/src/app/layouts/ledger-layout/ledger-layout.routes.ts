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
    path: 'flows',
    data: ledgerSectionRouteData('flows'),
    loadComponent: () => import('../../features/ledgers/workspace/flows/ledger-flows.component').then((m) => m.LedgerFlowsComponent),
  },
  {
    path: 'analytics',
    redirectTo: 'flows',
  },
  {
    path: 'accounts',
    data: { ...ledgerSectionRouteData('accounts'), kind: 'account' },
    loadComponent: () => import('../../features/ledgers/workspace/ledger-entity-manager.component').then((m) => m.LedgerEntityManagerComponent),
  },
  {
    path: 'categories',
    data: ledgerSectionRouteData('categories'),
    loadComponent: () => import('../../features/ledgers/workspace/categories/ledger-categories.component').then((m) => m.LedgerCategoriesComponent),
  },
  {
    path: 'currencies',
    data: { ...ledgerSectionRouteData('currencies'), kind: 'currency' },
    loadComponent: () => import('../../features/ledgers/workspace/ledger-entity-manager.component').then((m) => m.LedgerEntityManagerComponent),
  },
  {
    path: '**',
    redirectTo: 'home',
  },
];
