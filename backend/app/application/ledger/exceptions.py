class LedgerNotFoundError(Exception):
    pass


class CurrencyNotFoundError(Exception):
    pass


class CurrencyInUseError(Exception):
    pass


class AccountNotFoundError(Exception):
    pass


class AccountNameUnavailableError(Exception):
    pass


class AccountInUseError(Exception):
    pass


class CategoryNotFoundError(Exception):
    pass


class CategoryInUseError(Exception):
    pass


class BudgetNotFoundError(Exception):
    pass


class BudgetNameUnavailableError(Exception):
    pass


class BudgetAccountCurrencyMismatchError(Exception):
    pass


class BudgetNotActiveError(Exception):
    pass


class FinancialEventNotFoundError(Exception):
    pass


class FinancialEventTypeMismatchError(Exception):
    pass


class InvalidFinancialEventStructureError(Exception):
    pass


class FinancialMovementNotFoundError(Exception):
    pass
