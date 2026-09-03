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
