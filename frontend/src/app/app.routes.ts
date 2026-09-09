import { Routes } from '@angular/router';
import { authGuard, guestGuard } from './core/auth/auth.guard';
import { LedgerContextService } from './core/ledgers/ledger-context.service';
import { LedgerWorkspaceStateService } from './core/ledgers/ledger-workspace-state.service';
import { AuthenticatedShellService } from './layouts/authenticated-layout/authenticated-shell.service';
import { LEDGER_LAYOUT_ROUTES } from './layouts/ledger-layout/ledger-layout.routes';

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
    providers: [AuthenticatedShellService],
    loadComponent: () => import('./layouts/authenticated-layout/authenticated-layout.component').then((m) => m.AuthenticatedLayoutComponent),
    children: [
      {
        path: 'home',
        loadComponent: () => import('./features/home/home.component').then((m) => m.HomeComponent),
      },
      {
        path: 'ledgers/:ledgerUuid',
        providers: [LedgerContextService, LedgerWorkspaceStateService],
        loadComponent: () => import('./layouts/ledger-layout/ledger-layout.component').then((m) => m.LedgerLayoutComponent),
        children: LEDGER_LAYOUT_ROUTES,
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
