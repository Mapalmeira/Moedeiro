import { Routes } from '@angular/router';
import { authGuard, guestGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/auth/landing/auth-landing.component').then((m) => m.AuthLandingComponent),
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./layouts/authenticated-layout/authenticated-layout.component').then((m) => m.AuthenticatedLayoutComponent),
    children: [
      {
        path: 'home',
        loadComponent: () => import('./features/ledgers/ledger-home.component').then((m) => m.LedgerHomeComponent),
      },
      {
        path: 'ledgers/:ledgerUuid/:section',
        loadComponent: () => import('./features/ledgers/ledger-page.component').then((m) => m.LedgerPageComponent),
      },
      {
        path: 'ledgers/:ledgerUuid',
        loadComponent: () => import('./features/ledgers/ledger-page.component').then((m) => m.LedgerPageComponent),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
