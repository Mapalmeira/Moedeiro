import argparse
import time
from collections.abc import Sequence
from uuid import UUID

from app.application.registry.exceptions import UserNotFoundError
from app.application.registry.use_cases.password import create_recovery_code, list_recovery_codes, revoke_recovery_code
from app.application.registry.use_cases.user_invitation import create_user_invitation, list_user_invitations, revoke_user_invitation
from app.domain.registry.model.recovery_code import RecoveryCode
from app.domain.registry.model.user_invitation import DEFAULT_EXPIRATION_TIMEOUT_SECONDS, UserInvitation
from app.infrastructure.persistence.sqlite.databases import SqliteDatabases
from app.settings import Settings


def main(arguments: Sequence[str] | None = None, settings: Settings | None = None) -> int:
    parser = _create_parser()
    parsed = parser.parse_args(arguments)
    selected_settings = Settings.from_environment() if settings is None else settings
    databases = SqliteDatabases(
        selected_settings.registry_db_path,
        selected_settings.registry_schema_path,
        selected_settings.ledger_dbs_dir,
        selected_settings.ledger_schema_path,
    )
    databases.initialize()
    if parsed.resource == "invitation":
        return _handle_invitation(parsed, databases, int(time.time()))
    if parsed.resource == "recovery-code":
        return _handle_recovery_code(parsed, databases, int(time.time()))
    parser.error(f"Unsupported resource: {parsed.resource}")


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="moedeiro")
    resources = parser.add_subparsers(dest="resource", required=True)
    invitation = resources.add_parser("invitation")
    _add_invitation_actions(invitation)
    recovery_code = resources.add_parser("recovery-code")
    _add_recovery_code_actions(recovery_code)
    return parser


def _add_invitation_actions(parser: argparse.ArgumentParser) -> None:
    actions = parser.add_subparsers(dest="action", required=True)
    create = actions.add_parser("create")
    create.add_argument("--expiration-seconds", type=_positive_int, default=DEFAULT_EXPIRATION_TIMEOUT_SECONDS)
    actions.add_parser("list")
    revoke = actions.add_parser("revoke")
    revoke.add_argument("uuid", type=UUID)


def _add_recovery_code_actions(parser: argparse.ArgumentParser) -> None:
    actions = parser.add_subparsers(dest="action", required=True)
    create = actions.add_parser("create")
    create.add_argument("user_uuid", type=UUID)
    list_codes = actions.add_parser("list")
    list_codes.add_argument("user_uuid", type=UUID)
    revoke = actions.add_parser("revoke")
    revoke.add_argument("uuid", type=UUID)


def _handle_invitation(arguments: argparse.Namespace, databases: SqliteDatabases, timestamp: int) -> int:
    if arguments.action == "create":
        return _create_invitation(databases, timestamp, arguments.expiration_seconds)
    if arguments.action == "list":
        return _list_invitations(databases, timestamp)
    if arguments.action == "revoke":
        return _revoke_invitation(databases, timestamp, arguments.uuid)
    raise ValueError(f"Unsupported invitation action: {arguments.action}")


def _create_invitation(databases: SqliteDatabases, timestamp: int, expiration_seconds: int) -> int:
    code = create_user_invitation(databases.open_registry, timestamp, expiration_seconds)
    print(f"/registration#invite={code}")
    return 0


def _list_invitations(databases: SqliteDatabases, timestamp: int) -> int:
    for invitation in list_user_invitations(databases.open_registry):
        print(f"{invitation.uuid}\t{_status(invitation, timestamp)}\t{invitation.created_at}\t{invitation.expires_at}")
    return 0


def _revoke_invitation(databases: SqliteDatabases, timestamp: int, invitation_uuid: UUID) -> int:
    if not revoke_user_invitation(databases.open_registry, invitation_uuid, timestamp):
        print("Invitation not available")
        return 1
    print(f"Revoked invitation {invitation_uuid}")
    return 0


def _handle_recovery_code(arguments: argparse.Namespace, databases: SqliteDatabases, timestamp: int) -> int:
    if arguments.action == "create":
        return _create_recovery_code(databases, timestamp, arguments.user_uuid)
    if arguments.action == "list":
        return _list_recovery_codes(databases, arguments.user_uuid)
    if arguments.action == "revoke":
        return _revoke_recovery_code(databases, timestamp, arguments.uuid)
    raise ValueError(f"Unsupported recovery-code action: {arguments.action}")


def _create_recovery_code(databases: SqliteDatabases, timestamp: int, user_uuid: UUID) -> int:
    try:
        code = create_recovery_code(databases.open_registry, user_uuid, timestamp)
    except UserNotFoundError:
        print("User not found")
        return 1
    print(f"/recover#code={code}")
    return 0


def _list_recovery_codes(databases: SqliteDatabases, user_uuid: UUID) -> int:
    for recovery_code in list_recovery_codes(databases.open_registry, user_uuid):
        print(f"{recovery_code.uuid}\t{_recovery_code_status(recovery_code)}\t{recovery_code.created_at}")
    return 0


def _revoke_recovery_code(databases: SqliteDatabases, timestamp: int, recovery_code_uuid: UUID) -> int:
    if not revoke_recovery_code(databases.open_registry, recovery_code_uuid, timestamp):
        print("Recovery code not available")
        return 1
    print(f"Revoked recovery code {recovery_code_uuid}")
    return 0


def _status(invitation: UserInvitation, timestamp: int) -> str:
    if invitation.consumed_at is not None:
        return "CONSUMED"
    if invitation.revoked_at is not None:
        return "REVOKED"
    if invitation.expires_at <= timestamp:
        return "EXPIRED"
    return "ACTIVE"


def _recovery_code_status(recovery_code: RecoveryCode) -> str:
    if recovery_code.used_at is not None:
        return "USED"
    if recovery_code.revoked_at is not None:
        return "REVOKED"
    return "ACTIVE"


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
