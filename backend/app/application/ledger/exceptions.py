class AccountLimitReachedError(Exception):
    pass


class CurrencyLimitReachedError(Exception):
    pass


class BudgetLimitReachedError(Exception):
    pass


class FinancialEventLimitReachedError(Exception):
    pass

class LedgerNotFoundError(Exception):
    pass


class CurrencyNotFoundError(Exception):
    pass


class CurrencyInUseError(Exception):
    pass


class CurrencyNameUnavailableError(Exception):
    pass


class AccountNotFoundError(Exception):
    pass


class AccountNameUnavailableError(Exception):
    pass


class AccountInUseError(Exception):
    pass


class CategoryNotFoundError(Exception):
    pass


class CategoryNameUnavailableError(Exception):
    pass


class CategoryInUseError(Exception):
    pass


class CategoryTreeSizeExceededError(Exception):
    pass


class CategoryDepthExceededError(Exception):
    pass


class InvalidCategoryHierarchyError(Exception):
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


class InvalidFinancialEventError(Exception):
    pass


class QueryPointLimitExceededError(Exception):
    pass


class InvalidQueryParameterError(Exception):
    pass


class QueryResultOverflowError(Exception):
    pass


class FinancialMovementNotFoundError(Exception):
    pass
