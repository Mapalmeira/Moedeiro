import { HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { I18nService, TranslationKey } from '../i18n/i18n.service';

interface ValidationIssue {
  loc?: Array<string | number>;
}

@Injectable({ providedIn: 'root' })
export class ApiErrorService {
  private readonly i18n = inject(I18nService);

  message(error: unknown, fallbackKey: TranslationKey = 'errors.generic'): string {
    const fallback = this.i18n.t(fallbackKey);
    if (!(error instanceof HttpErrorResponse)) return fallback;

    if (error.status === 0) return this.i18n.t('errors.serverUnreachable');
    if (error.status === 429) return this.i18n.t('errors.tooManyRequests');
    if (error.status === 503) return this.i18n.t('errors.temporarilyUnavailable');

    const detail = error.error?.detail as string | ValidationIssue[] | undefined;
    if (typeof detail === 'string') return this.knownDetail(detail, fallback);

    if (Array.isArray(detail) && detail.length > 0) {
      const field = detail[0]?.loc?.at(-1);
      return field ? this.i18n.t('errors.invalidField', { field: String(field) }) : fallback;
    }

    return fallback;
  }

  private knownDetail(detail: string, fallback: string): string {
    const pointLimit = /^Point count cannot exceed (\d+)$/.exec(detail);
    if (pointLimit) return this.i18n.t('errors.queryPointLimit', { limit: pointLimit[1] });

    const known: Partial<Record<string, TranslationKey>> = {
      'Invalid session': 'errors.sessionExpired',
      'TOTP required': 'errors.totpRequired',
      'TOTP code already used': 'errors.totpAlreadyUsed',
      'Invitation not available': 'errors.invitationUnavailable',
      'User name not available': 'errors.usernameUnavailable',
      'Password update conflict': 'errors.passwordConflict',
      'Invalid current password': 'errors.invalidCurrentPassword',
      'TOTP already enabled': 'errors.totpAlreadyEnabled',
      'TOTP not enabled': 'errors.totpNotEnabled',
      'Invalid or expired TOTP setup': 'errors.invalidTotpSetup',
      'Ledger not found': 'errors.ledgerNotFound',
      'Ledger limit reached': 'errors.ledgerLimitReached',
      'Budget limit reached': 'errors.budgetLimitReached',
      'Budget name unavailable': 'errors.budgetNameUnavailable',
      'Budget not found': 'errors.budgetNotFound',
      'Financial event limit reached': 'errors.financialEventLimitReached',
      'Financial event not found': 'errors.financialEventNotFound',
      'Invalid financial event': 'errors.invalidFinancialEvent',
      'Account limit reached': 'workspace.limit',
      'Currency limit reached': 'workspace.limit',
      'Account is in use': 'errors.accountInUse',
      'Currency is in use': 'errors.currencyInUse',
      'Account name unavailable': 'errors.accountNameUnavailable',
      'Currency name unavailable': 'errors.currencyNameUnavailable',
      'Account not found': 'errors.accountNotFound',
      'Currency not found': 'errors.currencyNotFound',
      'Category is in use': 'errors.categoryInUse',
      'Category not found': 'errors.categoryNotFound',
      'Category name unavailable': 'errors.categoryNameUnavailable',
      'Category limit exceeded': 'errors.categoryLimitReached',
      'Category depth limit exceeded': 'errors.categoryDepthExceeded',
      'Invalid category hierarchy': 'errors.categoryHierarchyInvalid',
    };

    if (detail === 'Invalid credentials') return fallback;
    const key = known[detail];
    return key ? this.i18n.t(key) : fallback;
  }
}
