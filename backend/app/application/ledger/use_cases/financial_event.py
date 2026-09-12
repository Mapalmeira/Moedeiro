from collections.abc import Callable, Sequence
from dataclasses import dataclass
from uuid import UUID

from app.application.ledger.exceptions import AccountNotFoundError, CategoryNotFoundError, CurrencyNotFoundError, FinancialEventLimitReachedError, FinancialEventNotFoundError, FinancialEventTypeMismatchError, FinancialMovementNotFoundError, InvalidFinancialEventError, InvalidFinancialEventStructureError
from app.application.ledger.unit_of_work import LedgerUnitOfWork
from app.domain.ledger.limits import MAXIMUM_FINANCIAL_EVENTS
from app.domain.ledger.model.financial_event import MAX_SHOPPING_LIST_MOVEMENTS, FinancialEvent, FinancialEventDescription, FinancialEventType
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter
from app.domain.ledger.model.financial_movement import FinancialMovement, FinancialMovementItemName, FinancialMovementQuantity, FinancialMovementSpecialType


@dataclass(frozen=True, slots=True)
class ShoppingListMovementInput:
    category_uuid: UUID
    value: int
    quantity: FinancialMovementQuantity
    item_name: FinancialMovementItemName | None
    uuid: UUID | None = None


@dataclass(frozen=True, slots=True)
class FinancialEventFee:
    category_uuid: UUID
    value: int


@dataclass(frozen=True, slots=True, kw_only=True)
class _MovementInput:
    account_uuid: UUID
    category_uuid: UUID
    value: int
    quantity: FinancialMovementQuantity = 1
    item_name: FinancialMovementItemName | None = None
    special_type: FinancialMovementSpecialType | None = None


def create_simple_financial_event(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    occurred_at: int,
    description: FinancialEventDescription,
    account_uuid: UUID,
    category_uuid: UUID,
    value: int,
    quantity: FinancialMovementQuantity,
    item_name: FinancialMovementItemName | None,
    fee: FinancialEventFee | None = None,
) -> FinancialEvent:
    if value == 0:
        raise InvalidFinancialEventError
    if fee is not None and (value >= 0 or fee.value >= 0):
        raise InvalidFinancialEventError
    movements = [
        _MovementInput(
            account_uuid=account_uuid,
            category_uuid=category_uuid,
            value=value,
            quantity=quantity,
            item_name=item_name,
        )
    ]
    if fee is not None:
        movements.append(
            _MovementInput(
                account_uuid=account_uuid,
                category_uuid=fee.category_uuid,
                value=fee.value,
                special_type="FEE",
            )
        )
    return _create_financial_event(unit_of_work_factory, occurred_at, description, "TRANSACTION", movements)


def create_shopping_list_financial_event(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    occurred_at: int,
    description: FinancialEventDescription,
    account_uuid: UUID,
    movements: Sequence[ShoppingListMovementInput],
) -> FinancialEvent:
    if not movements:
        raise InvalidFinancialEventError
    if len(movements) > MAX_SHOPPING_LIST_MOVEMENTS:
        raise InvalidFinancialEventError
    if any(movement.value >= 0 for movement in movements):
        raise InvalidFinancialEventError
    return _create_financial_event(
        unit_of_work_factory,
        occurred_at,
        description,
        "SHOPPING_LIST",
        [
            _MovementInput(
                account_uuid=account_uuid,
                category_uuid=movement.category_uuid,
                value=movement.value,
                quantity=movement.quantity,
                item_name=movement.item_name,
            )
            for movement in movements
        ],
    )


def create_account_transfer_financial_event(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    occurred_at: int,
    description: FinancialEventDescription,
    source_account_uuid: UUID,
    source_category_uuid: UUID,
    source_value: int,
    destination_account_uuid: UUID,
    destination_category_uuid: UUID,
    destination_value: int,
    fee: FinancialEventFee | None,
) -> FinancialEvent:
    if source_account_uuid == destination_account_uuid:
        raise InvalidFinancialEventError
    if source_value >= 0:
        raise InvalidFinancialEventError
    if destination_value <= 0:
        raise InvalidFinancialEventError
    if fee is not None and fee.value >= 0:
        raise InvalidFinancialEventError
    movements = [
        _MovementInput(account_uuid=source_account_uuid, category_uuid=source_category_uuid, value=source_value),
        _MovementInput(account_uuid=destination_account_uuid, category_uuid=destination_category_uuid, value=destination_value),
    ]
    if fee is not None:
        movements.append(
            _MovementInput(
                account_uuid=destination_account_uuid,
                category_uuid=fee.category_uuid,
                value=fee.value,
                special_type="FEE",
            )
        )
    return _create_financial_event(unit_of_work_factory, occurred_at, description, "ACCOUNT_TRANSFER", movements)


def get_financial_event(unit_of_work_factory: Callable[[], LedgerUnitOfWork], event_uuid: UUID) -> FinancialEvent:
    with unit_of_work_factory() as unit_of_work:
        event = unit_of_work.financial_event_repository.get(event_uuid)
        if event is None:
            raise FinancialEventNotFoundError
        return event


def list_financial_events_after(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    page_size: int,
    ascending: bool,
    filters: FinancialEventFilter,
    occurred_at: int | None,
    uuid: UUID | None,
) -> list[FinancialEvent]:
    with unit_of_work_factory() as unit_of_work:
        if filters.currency_uuid is not None and unit_of_work.currency_repository.get(filters.currency_uuid) is None:
            raise CurrencyNotFoundError
        return unit_of_work.financial_event_repository.list_after(page_size + 1, ascending, filters, occurred_at, uuid)


def count_financial_events(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    filters: FinancialEventFilter,
) -> int:
    with unit_of_work_factory() as unit_of_work:
        if filters.currency_uuid is not None and unit_of_work.currency_repository.get(filters.currency_uuid) is None:
            raise CurrencyNotFoundError
        return unit_of_work.financial_event_repository.count_matching(filters)


def update_simple_financial_event(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    event_uuid: UUID,
    occurred_at: int,
    description: FinancialEventDescription,
    account_uuid: UUID,
    category_uuid: UUID,
    value: int,
    quantity: FinancialMovementQuantity,
    item_name: FinancialMovementItemName | None,
    fee: FinancialEventFee | None = None,
) -> FinancialEvent:
    if value == 0:
        raise InvalidFinancialEventError
    if fee is not None and (value >= 0 or fee.value >= 0):
        raise InvalidFinancialEventError
    with unit_of_work_factory() as unit_of_work:
        event = _get_event_of_type(unit_of_work, event_uuid, "TRANSACTION")
        movement, existing_fee = _simple_movements(event)
        _require_accounts(unit_of_work, [account_uuid])
        category_uuids = [category_uuid]
        if fee is not None:
            category_uuids.append(fee.category_uuid)
        _require_categories(unit_of_work, category_uuids)
        updated_movements = [
            _update_movement(unit_of_work, movement, account_uuid, category_uuid, value, quantity, item_name),
        ]
        if fee is None:
            if existing_fee is not None:
                unit_of_work.financial_movement_repository.delete(existing_fee.uuid)
        elif existing_fee is None:
            updated_movements.append(
                unit_of_work.financial_movement_repository.create(
                    event.uuid,
                    account_uuid,
                    fee.category_uuid,
                    fee.value,
                    None,
                    1,
                    special_type="FEE",
                )
            )
        else:
            updated_movements.append(_update_movement(unit_of_work, existing_fee, account_uuid, fee.category_uuid, fee.value, 1, None))
        updated_movements.sort(key=lambda financial_movement: financial_movement.uuid.bytes)
        updated_event = _update_event(unit_of_work, event, occurred_at, description, updated_movements)
        unit_of_work.commit()
    return updated_event


def update_shopping_list_financial_event(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    event_uuid: UUID,
    occurred_at: int,
    description: FinancialEventDescription,
    account_uuid: UUID,
    movements: Sequence[ShoppingListMovementInput],
) -> FinancialEvent:
    if not movements:
        raise InvalidFinancialEventError
    if len(movements) > MAX_SHOPPING_LIST_MOVEMENTS:
        raise InvalidFinancialEventError
    if any(movement.value >= 0 for movement in movements):
        raise InvalidFinancialEventError
    supplied_uuids = [movement.uuid for movement in movements if movement.uuid is not None]
    if len(supplied_uuids) != len(set(supplied_uuids)):
        raise InvalidFinancialEventError
    with unit_of_work_factory() as unit_of_work:
        event = _get_event_of_type(unit_of_work, event_uuid, "SHOPPING_LIST")
        if not event.movements or any(movement.value >= 0 or movement.special_type is not None for movement in event.movements):
            raise InvalidFinancialEventStructureError
        if len({movement.account_uuid for movement in event.movements}) != 1:
            raise InvalidFinancialEventStructureError
        existing_by_uuid = {movement.uuid: movement for movement in event.movements}
        if any(movement_uuid not in existing_by_uuid for movement_uuid in supplied_uuids):
            raise FinancialMovementNotFoundError
        _require_accounts(unit_of_work, [account_uuid])
        _require_categories(unit_of_work, [movement.category_uuid for movement in movements])
        updated_movements: list[FinancialMovement] = []
        for movement in movements:
            if movement.uuid is None:
                updated_movements.append(
                    unit_of_work.financial_movement_repository.create(
                        event.uuid,
                        account_uuid,
                        movement.category_uuid,
                        movement.value,
                        movement.item_name,
                        movement.quantity,
                    )
                )
            else:
                updated_movements.append(
                    _update_movement(
                        unit_of_work,
                        existing_by_uuid[movement.uuid],
                        account_uuid,
                        movement.category_uuid,
                        movement.value,
                        movement.quantity,
                        movement.item_name,
                    )
                )
        for movement_uuid in existing_by_uuid.keys() - set(supplied_uuids):
            unit_of_work.financial_movement_repository.delete(movement_uuid)
        updated_movements.sort(key=lambda financial_movement: financial_movement.uuid.bytes)
        updated_event = _update_event(unit_of_work, event, occurred_at, description, updated_movements)
        unit_of_work.commit()
    return updated_event


def update_account_transfer_financial_event(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    event_uuid: UUID,
    occurred_at: int,
    description: FinancialEventDescription,
    source_account_uuid: UUID,
    source_category_uuid: UUID,
    source_value: int,
    destination_account_uuid: UUID,
    destination_category_uuid: UUID,
    destination_value: int,
    fee: FinancialEventFee | None,
) -> FinancialEvent:
    if source_account_uuid == destination_account_uuid:
        raise InvalidFinancialEventError
    if source_value >= 0:
        raise InvalidFinancialEventError
    if destination_value <= 0:
        raise InvalidFinancialEventError
    if fee is not None and fee.value >= 0:
        raise InvalidFinancialEventError
    with unit_of_work_factory() as unit_of_work:
        event = _get_event_of_type(unit_of_work, event_uuid, "ACCOUNT_TRANSFER")
        source, destination, existing_fee = _transfer_movements(event)
        _require_accounts(unit_of_work, [source_account_uuid, destination_account_uuid])
        category_uuids = [source_category_uuid, destination_category_uuid]
        if fee is not None:
            category_uuids.append(fee.category_uuid)
        _require_categories(unit_of_work, category_uuids)
        updated_movements = [
            _update_movement(unit_of_work, source, source_account_uuid, source_category_uuid, source_value, 1, None),
            _update_movement(unit_of_work, destination, destination_account_uuid, destination_category_uuid, destination_value, 1, None),
        ]
        if fee is None:
            if existing_fee is not None:
                unit_of_work.financial_movement_repository.delete(existing_fee.uuid)
        elif existing_fee is None:
            updated_movements.append(
                unit_of_work.financial_movement_repository.create(
                    event.uuid,
                    destination_account_uuid,
                    fee.category_uuid,
                    fee.value,
                    None,
                    1,
                    special_type="FEE",
                )
            )
        else:
            updated_movements.append(_update_movement(unit_of_work, existing_fee, destination_account_uuid, fee.category_uuid, fee.value, 1, None))
        updated_movements.sort(key=lambda financial_movement: financial_movement.uuid.bytes)
        updated_event = _update_event(unit_of_work, event, occurred_at, description, updated_movements)
        unit_of_work.commit()
    return updated_event


def delete_financial_event(unit_of_work_factory: Callable[[], LedgerUnitOfWork], event_uuid: UUID) -> None:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.financial_event_repository.get(event_uuid) is None:
            raise FinancialEventNotFoundError
        unit_of_work.financial_event_repository.delete(event_uuid)
        unit_of_work.commit()


def _create_financial_event(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    occurred_at: int,
    description: FinancialEventDescription,
    event_type: FinancialEventType,
    movements: Sequence[_MovementInput],
) -> FinancialEvent:
    with unit_of_work_factory() as unit_of_work:
        if unit_of_work.financial_event_repository.count() >= MAXIMUM_FINANCIAL_EVENTS:
            raise FinancialEventLimitReachedError
        _require_accounts(unit_of_work, [movement.account_uuid for movement in movements])
        _require_categories(unit_of_work, [movement.category_uuid for movement in movements])
        event = unit_of_work.financial_event_repository.create(occurred_at, description, event_type)
        created_movements = [
            unit_of_work.financial_movement_repository.create(
                event.uuid,
                movement.account_uuid,
                movement.category_uuid,
                movement.value,
                movement.item_name,
                movement.quantity,
                special_type=movement.special_type,
            )
            for movement in movements
        ]
        created_movements.sort(key=lambda movement: movement.uuid.bytes)
        event = FinancialEvent.model_validate({**event.model_dump(), "movements": created_movements})
        unit_of_work.commit()
    return event


def _get_event_of_type(unit_of_work: LedgerUnitOfWork, event_uuid: UUID, expected_type: FinancialEventType) -> FinancialEvent:
    event = unit_of_work.financial_event_repository.get(event_uuid)
    if event is None:
        raise FinancialEventNotFoundError
    if event.type != expected_type:
        raise FinancialEventTypeMismatchError
    return event


def _require_categories(unit_of_work: LedgerUnitOfWork, category_uuids: Sequence[UUID]) -> None:
    selected_category_uuids = set(category_uuids)
    if len(unit_of_work.category_repository.get_many(selected_category_uuids)) != len(selected_category_uuids):
        raise CategoryNotFoundError


def _require_accounts(unit_of_work: LedgerUnitOfWork, account_uuids: Sequence[UUID]) -> None:
    selected_account_uuids = set(account_uuids)
    if len(unit_of_work.account_repository.get_many(selected_account_uuids)) != len(selected_account_uuids):
        raise AccountNotFoundError


def _update_movement(
    unit_of_work: LedgerUnitOfWork,
    movement: FinancialMovement,
    account_uuid: UUID,
    category_uuid: UUID,
    value: int,
    quantity: FinancialMovementQuantity,
    item_name: FinancialMovementItemName | None,
) -> FinancialMovement:
    updated_movement = FinancialMovement.model_validate(
        {
            **movement.model_dump(),
            "account_uuid": account_uuid,
            "category_uuid": category_uuid,
            "value": value,
            "quantity": quantity,
            "item_name": item_name,
        }
    )
    unit_of_work.financial_movement_repository.update(updated_movement)
    return updated_movement


def _update_event(
    unit_of_work: LedgerUnitOfWork,
    event: FinancialEvent,
    occurred_at: int,
    description: FinancialEventDescription,
    movements: Sequence[FinancialMovement],
) -> FinancialEvent:
    updated_event = FinancialEvent.model_validate({**event.model_dump(), "occurred_at": occurred_at, "description": description, "movements": movements})
    unit_of_work.financial_event_repository.update_occurred_at(event.uuid, updated_event.occurred_at)
    unit_of_work.financial_event_repository.update_description(event.uuid, updated_event.description)
    return updated_event


def _simple_movements(event: FinancialEvent) -> tuple[FinancialMovement, FinancialMovement | None]:
    main_movements = [movement for movement in event.movements if movement.special_type is None]
    fee_movements = [movement for movement in event.movements if movement.special_type == "FEE"]
    if len(main_movements) != 1 or len(fee_movements) > 1 or len(main_movements) + len(fee_movements) != len(event.movements):
        raise InvalidFinancialEventStructureError
    movement = main_movements[0]
    fee = fee_movements[0] if fee_movements else None
    if fee is not None and (movement.value >= 0 or fee.value >= 0 or fee.account_uuid != movement.account_uuid or fee.quantity != 1 or fee.item_name is not None):
        raise InvalidFinancialEventStructureError
    return movement, fee


def _transfer_movements(event: FinancialEvent) -> tuple[FinancialMovement, FinancialMovement, FinancialMovement | None]:
    main_movements = [movement for movement in event.movements if movement.special_type is None]
    fee_movements = [movement for movement in event.movements if movement.special_type == "FEE"]
    if len(main_movements) != 2 or len(fee_movements) > 1 or len(main_movements) + len(fee_movements) != len(event.movements):
        raise InvalidFinancialEventStructureError
    income_movements = [movement for movement in main_movements if movement.value > 0]
    if len(income_movements) != 1:
        raise InvalidFinancialEventStructureError
    destination = income_movements[0]
    source_movements = [movement for movement in main_movements if movement.value < 0 and movement.account_uuid != destination.account_uuid]
    if len(source_movements) != 1:
        raise InvalidFinancialEventStructureError
    fee = fee_movements[0] if fee_movements else None
    if fee is not None and (fee.value >= 0 or fee.account_uuid != destination.account_uuid or fee.quantity != 1 or fee.item_name is not None):
        raise InvalidFinancialEventStructureError
    return source_movements[0], destination, fee
