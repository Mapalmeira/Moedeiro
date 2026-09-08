class LedgerLimitReachedError(Exception):
    pass


class LedgerNotFoundError(Exception):
    pass


class LedgerOwnershipAlreadyExistsError(Exception):
    pass


class LedgerGrantNotFoundError(Exception):
    pass


class InvitationNotAvailableError(Exception):
    pass


class UserNameUnavailableError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class TotpRequiredError(Exception):
    pass


class InvalidSessionError(Exception):
    pass


class InvalidCurrentPasswordError(Exception):
    pass


class PasswordUpdateConflictError(Exception):
    pass


class RecoveryCodeNotAvailableError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class TotpAlreadyEnabledError(Exception):
    pass


class TotpNotEnabledError(Exception):
    pass


class InvalidTotpCodeError(Exception):
    pass


class TotpCodeAlreadyUsedError(Exception):
    pass


class InvalidTotpSetupError(Exception):
    pass

class UserPreferencesNotFoundError(Exception):
    pass
