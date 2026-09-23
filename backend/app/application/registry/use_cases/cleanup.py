from collections.abc import Callable

from app.application.registry.unit_of_work import RegistryUnitOfWork


SECONDS_PER_DAY = 86_400


def remove_inactive_records(unit_of_work_factory: Callable[[], RegistryUnitOfWork], timestamp: int, retention_days: int) -> int:
    if retention_days < 0:
        raise ValueError("retention_days must not be negative")
    cutoff_timestamp = timestamp - retention_days * SECONDS_PER_DAY
    with unit_of_work_factory() as unit_of_work:
        deleted_count = sum(
            (
                unit_of_work.user_invitation_repository.delete_inactive_before(cutoff_timestamp),
                unit_of_work.ledger_grant_repository.delete_inactive_before(cutoff_timestamp),
                unit_of_work.recovery_code_repository.delete_inactive_before(cutoff_timestamp),
                unit_of_work.auth_session_repository.delete_inactive_before(cutoff_timestamp),
                unit_of_work.remember_session_repository.delete_inactive_before(cutoff_timestamp),
                unit_of_work.mfa_method_repository.delete_unconfirmed_before(cutoff_timestamp),
            )
        )
        deleted_count += unit_of_work.external_access_repository.delete_ungranted()
        unit_of_work.commit()
    return deleted_count
