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
    path: 'home',
    canActivate: [authGuard],
    loadComponent: () => import('./layouts/authenticated-layout/authenticated-layout.component').then((m) => m.AuthenticatedLayoutComponent),
  },
  { path: '**', redirectTo: '' },
];
