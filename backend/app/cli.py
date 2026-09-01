import argparse
import time
from collections.abc import Sequence
from uuid import UUID

from app.application.registry.use_cases.user_invitation import create_user_invitation, list_user_invitations, revoke_user_invitation
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
    parser.error(f"Unsupported resource: {parsed.resource}")


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="moedeiro")
    resources = parser.add_subparsers(dest="resource", required=True)
    invitation = resources.add_parser("invitation")
    _add_invitation_actions(invitation)
    return parser


def _add_invitation_actions(parser: argparse.ArgumentParser) -> None:
    actions = parser.add_subparsers(dest="action", required=True)
    create = actions.add_parser("create")
    create.add_argument("--expiration-seconds", type=_positive_int, default=DEFAULT_EXPIRATION_TIMEOUT_SECONDS)
    actions.add_parser("list")
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


def _status(invitation: UserInvitation, timestamp: int) -> str:
    if invitation.consumed_at is not None:
        return "CONSUMED"
    if invitation.revoked_at is not None:
        return "REVOKED"
    if invitation.expires_at <= timestamp:
        return "EXPIRED"
    return "ACTIVE"


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
