import argparse
import getpass
import time
from collections.abc import Sequence
from uuid import UUID

from app.application.registry.exceptions import LedgerGrantNotFoundError, LedgerLimitReachedError, LedgerNotFoundError, LedgerOwnershipAlreadyExistsError, UserNameUnavailableError, UserNotFoundError
from app.application.registry.use_cases.cleanup import remove_inactive_records
from app.application.registry.use_cases.grant import list_ledger_grants, revoke_ledger_grant, set_ledger_owner
from app.application.registry.use_cases.mfa import disable_mfa
from app.application.registry.use_cases.password import create_recovery_code
from app.application.registry.use_cases.user import create_user, delete_user, list_users
from app.application.registry.use_cases.user_invitation import create_user_invitation, list_user_invitations, revoke_user_invitation
from app.domain.registry.model.recovery_code import DEFAULT_EXPIRATION_TIMEOUT_SECONDS as DEFAULT_RECOVERY_CODE_EXPIRATION_TIMEOUT_SECONDS
from app.domain.registry.model.user_invitation import DEFAULT_EXPIRATION_TIMEOUT_SECONDS, UserInvitation
from app.infrastructure.security.password_hasher import Argon2PasswordHasher
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.server import DEFAULT_HOST, DEFAULT_PORT, start as start_server
from app.settings import Settings


def main(arguments: Sequence[str] | None = None, settings: Settings | None = None) -> int:
    parser = _create_parser()
    parsed = parser.parse_args(arguments)
    selected_settings = Settings.from_environment() if settings is None else settings
    if parsed.resource == "start":
        return start_server(
            selected_settings,
            parsed.host,
            parsed.port,
            mount_frontend=not parsed.api_only,
        )

    databases = SqliteDatabases(
        selected_settings.registry_db_path,
        selected_settings.registry_schema_path,
        selected_settings.ledger_dbs_dir,
        selected_settings.ledger_schema_path,
    )
    databases.initialize()
    if parsed.resource == "invitation":
        return _handle_invitation(parsed, databases, int(time.time()))
    if parsed.resource == "cleanup":
        return _remove_inactive_records(databases, parsed.days, int(time.time()))
    if parsed.resource == "user":
        return _handle_user(parsed, databases)
    if parsed.resource == "grant":
        return _handle_grant(parsed, databases, int(time.time()))
    parser.error(f"Unsupported resource: {parsed.resource}")


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="moedeiro")
    resources = parser.add_subparsers(dest="resource", required=True)
    start = resources.add_parser("start", help="Start the Moedeiro service")
    start.add_argument("--host", default=DEFAULT_HOST)
    start.add_argument("--port", type=_port, default=DEFAULT_PORT)
    start.add_argument(
        "--api-only",
        action="store_true",
        help="Serve the API without mounting the compiled frontend",
    )
    invitation = resources.add_parser("invitation", help="Manage user invitations")
    _add_invitation_actions(invitation)
    cleanup = resources.add_parser("cleanup", help="Remove inactive registry records")
    cleanup.add_argument("--days", type=_nonnegative_int, required=True)
    user = resources.add_parser("user", help="Manage users")
    _add_user_actions(user)
    grant = resources.add_parser("grant", help="Manage ledger grants")
    _add_grant_actions(grant)
    return parser


def _add_invitation_actions(parser: argparse.ArgumentParser) -> None:
    actions = parser.add_subparsers(dest="action", required=True)
    create = actions.add_parser("create")
    create.add_argument("--expiration-seconds", type=_positive_int, default=DEFAULT_EXPIRATION_TIMEOUT_SECONDS)
    actions.add_parser("list")
    revoke = actions.add_parser("revoke")
    revoke.add_argument("uuid", type=UUID)


def _add_user_actions(parser: argparse.ArgumentParser) -> None:
    actions = parser.add_subparsers(dest="action", required=True)
    create = actions.add_parser("create")
    create.add_argument("name")
    actions.add_parser("list")
    recover_password = actions.add_parser("recover-password")
    recover_password.add_argument("uuid", type=UUID)
    recover_password.add_argument("--expiration-seconds", type=_positive_int, default=DEFAULT_RECOVERY_CODE_EXPIRATION_TIMEOUT_SECONDS)
    disable_mfa = actions.add_parser("disable-mfa")
    disable_mfa.add_argument("uuid", type=UUID)
    delete = actions.add_parser("delete")
    delete.add_argument("uuid", type=UUID)


def _add_grant_actions(parser: argparse.ArgumentParser) -> None:
    actions = parser.add_subparsers(dest="action", required=True)
    list_grants = actions.add_parser("list")
    list_grants.add_argument("user_uuid", type=UUID, nargs="?")
    list_grants.add_argument("ledger_uuid", type=UUID, nargs="?")
    set_owner = actions.add_parser("set-owner")
    set_owner.add_argument("user_uuid", type=UUID)
    set_owner.add_argument("ledger_uuid", type=UUID)
    revoke = actions.add_parser("revoke")
    revoke.add_argument("grant_uuid", type=UUID)


def _handle_invitation(arguments: argparse.Namespace, databases: SqliteDatabases, timestamp: int) -> int:
    if arguments.action == "create":
        return _create_invitation(databases, timestamp, arguments.expiration_seconds)
    if arguments.action == "list":
        return _list_invitations(databases, timestamp)
    if arguments.action == "revoke":
        return _revoke_invitation(databases, arguments.uuid)
    raise ValueError(f"Unsupported invitation action: {arguments.action}")


def _create_invitation(databases: SqliteDatabases, timestamp: int, expiration_seconds: int) -> int:
    code = create_user_invitation(databases.open_registry, timestamp, expiration_seconds)
    print(code)
    return 0


def _list_invitations(databases: SqliteDatabases, timestamp: int) -> int:
    for invitation in list_user_invitations(databases.open_registry, "created_at", True):
        print(f"{invitation.uuid}\t{_status(invitation, timestamp)}\t{invitation.created_at}\t{invitation.expires_at}")
    return 0


def _revoke_invitation(databases: SqliteDatabases, invitation_uuid: UUID) -> int:
    if not revoke_user_invitation(databases.open_registry, invitation_uuid):
        print("Invitation not available")
        return 1
    print(f"Revoked invitation {invitation_uuid}")
    return 0


def _create_recovery_code(databases: SqliteDatabases, timestamp: int, user_uuid: UUID, expiration_seconds: int) -> int:
    try:
        code = create_recovery_code(databases.open_registry, user_uuid, timestamp, expiration_seconds)
    except UserNotFoundError:
        print("User not found")
        return 1
    print(code)
    return 0


def _remove_inactive_records(databases: SqliteDatabases, retention_days: int, timestamp: int) -> int:
    deleted_count = remove_inactive_records(databases.open_registry, timestamp, retention_days)
    print(f"Removed {deleted_count} inactive records")
    return 0


def _handle_user(arguments: argparse.Namespace, databases: SqliteDatabases) -> int:
    if arguments.action == "create":
        return _create_user(databases, arguments.name, int(time.time()))
    if arguments.action == "list":
        return _list_users(databases)
    if arguments.action == "recover-password":
        return _create_recovery_code(databases, int(time.time()), arguments.uuid, arguments.expiration_seconds)
    if arguments.action == "disable-mfa":
        return _disable_mfa(databases, arguments.uuid)
    if arguments.action == "delete":
        return _delete_user(databases, arguments.uuid)
    raise ValueError(f"Unsupported user action: {arguments.action}")


def _handle_grant(arguments: argparse.Namespace, databases: SqliteDatabases, timestamp: int) -> int:
    if arguments.action == "list":
        return _list_grants(databases, arguments.user_uuid, arguments.ledger_uuid)
    if arguments.action == "set-owner":
        return _set_ledger_owner(databases, arguments.user_uuid, arguments.ledger_uuid, timestamp)
    if arguments.action == "revoke":
        return _revoke_ledger_grant(databases, arguments.grant_uuid, timestamp)
    raise ValueError(f"Unsupported grant action: {arguments.action}")


def _create_user(databases: SqliteDatabases, name: str, timestamp: int) -> int:
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Confirm password: "):
        print("Passwords do not match")
        return 1
    try:
        user = create_user(databases.open_registry, Argon2PasswordHasher(), name, password, timestamp)
    except UserNameUnavailableError:
        print("User name unavailable")
        return 1
    print(f"Created user {user.uuid}")
    return 0


def _list_users(databases: SqliteDatabases) -> int:
    for user in list_users(databases.open_registry, "name", True):
        print(f"{user.uuid}\t{user.name}\t{user.created_at}")
    return 0


def _list_grants(databases: SqliteDatabases, user_uuid: UUID | None, ledger_uuid: UUID | None) -> int:
    for grant in list_ledger_grants(databases.open_registry, user_uuid, ledger_uuid):
        revoked_at = "" if grant.revoked_at is None else grant.revoked_at
        print(f"{grant.uuid}\t{grant.user_uuid}\t{grant.ledger_uuid}\t{grant.role}\t{grant.created_at}\t{revoked_at}")
    return 0


def _set_ledger_owner(databases: SqliteDatabases, user_uuid: UUID, ledger_uuid: UUID, timestamp: int) -> int:
    try:
        set_ledger_owner(databases.open_registry, user_uuid, ledger_uuid, timestamp)
    except UserNotFoundError:
        print("User not found")
        return 1
    except LedgerNotFoundError:
        print("Ledger not found")
        return 1
    except LedgerOwnershipAlreadyExistsError:
        print("User already owns ledger")
        return 1
    except LedgerLimitReachedError:
        print("Ledger limit reached")
        return 1
    print(f"Set user {user_uuid} as owner of ledger {ledger_uuid}")
    return 0


def _revoke_ledger_grant(databases: SqliteDatabases, grant_uuid: UUID, timestamp: int) -> int:
    try:
        revoke_ledger_grant(databases.open_registry, grant_uuid, timestamp)
    except LedgerGrantNotFoundError:
        print("Active ledger grant not found")
        return 1
    print(f"Revoked ledger grant {grant_uuid}")
    return 0


def _delete_user(databases: SqliteDatabases, user_uuid: UUID) -> int:
    try:
        ledgers = delete_user(databases.open_registry, user_uuid)
    except UserNotFoundError:
        print("User not found")
        return 1
    for ledger in ledgers:
        databases.delete_ledger_database(ledger.path)
    print(f"Deleted user {user_uuid} and {len(ledgers)} owned ledgers")
    return 0


def _disable_mfa(databases: SqliteDatabases, user_uuid: UUID) -> int:
    try:
        disabled_count = disable_mfa(databases.open_registry, user_uuid)
    except UserNotFoundError:
        print("User not found")
        return 1
    if disabled_count == 0:
        print("MFA not enabled")
        return 1
    print(f"Disabled MFA for user {user_uuid}")
    return 0


def _status(invitation: UserInvitation, timestamp: int) -> str:
    if invitation.consumed_at is not None:
        return "CONSUMED"
    if invitation.expires_at <= timestamp:
        return "EXPIRED"
    return "ACTIVE"



def _port(value: str) -> int:
    parsed = int(value)
    if not 1 <= parsed <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return parsed

def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must not be negative")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
