MAXIMUM_ACCOUNTS = 300
MAXIMUM_CURRENCIES = 300


class AccountLimitReachedError(Exception):
    pass


class CurrencyLimitReachedError(Exception):
    pass
