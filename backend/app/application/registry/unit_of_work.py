"""Transactional wrapper exposing repositories for one registry operation."""

from app.application.unit_of_work import UnitOfWork
from app.domain.registry.repository.auth_session import AuthSessionRepository
from app.domain.registry.repository.ledger import LedgerRepository
from app.domain.registry.repository.ledger_grant import LedgerGrantRepository
from app.domain.registry.repository.external_access import ExternalAccessRepository
from app.domain.registry.repository.mfa_method import MfaMethodRepository
from app.domain.registry.repository.recovery_code import RecoveryCodeRepository
from app.domain.registry.repository.registry_metadata import RegistryMetadataRepository
from app.domain.registry.repository.remember_session import RememberSessionRepository
from app.domain.registry.repository.user import UserRepository
from app.domain.registry.repository.user_invitation import UserInvitationRepository
from app.domain.registry.repository.user_preferences import UserPreferencesRepository


class RegistryUnitOfWork(UnitOfWork):
    registry_metadata_repository: RegistryMetadataRepository
    ledger_repository: LedgerRepository
    user_repository: UserRepository
    user_invitation_repository: UserInvitationRepository
    ledger_grant_repository: LedgerGrantRepository
    external_access_repository: ExternalAccessRepository
    mfa_method_repository: MfaMethodRepository
    recovery_code_repository: RecoveryCodeRepository
    user_preferences_repository: UserPreferencesRepository
    auth_session_repository: AuthSessionRepository
    remember_session_repository: RememberSessionRepository
