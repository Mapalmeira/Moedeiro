class InvitationNotAvailableError(Exception):
    pass


class UserNameUnavailableError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InvalidSessionError(Exception):
    pass


class InvalidCurrentPasswordError(Exception):
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


class InvalidTotpSetupError(Exception):
    pass
