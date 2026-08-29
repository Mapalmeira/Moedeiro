"""Transactional wrapper exposing repositories for one registry operation."""

from app.application.unit_of_work import UnitOfWork
from app.domain.registry.repository.access_grant import AccessGrantRepository
from app.domain.registry.repository.access_invitation import AccessInvitationRepository
from app.domain.registry.repository.auth_session import AuthSessionRepository
from app.domain.registry.repository.ledger import LedgerRepository


class RegistryUnitOfWork(UnitOfWork):
    ledger_repository: LedgerRepository
    access_invitation_repository: AccessInvitationRepository
    access_grant_repository: AccessGrantRepository
    auth_session_repository: AuthSessionRepository
