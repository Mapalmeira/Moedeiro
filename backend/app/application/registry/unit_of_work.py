"""Transactional wrapper exposing repositories for one registry operation."""

from app.application.unit_of_work import UnitOfWork
from app.domain.registry.repository.ledger import LedgerRepository
from app.domain.registry.repository.ledger_token import LedgerTokenRepository


class RegistryUnitOfWork(UnitOfWork):
    ledger_repository: LedgerRepository
    ledger_token_repository: LedgerTokenRepository
