from collections.abc import Callable, Sequence
from uuid import UUID

from app.application.ledger.exceptions import AccountNotFoundError, CategoryNotFoundError, FinancialEventNotFoundError, FinancialEventTypeMismatchError, FinancialMovementNotFoundError, InvalidFinancialEventError, InvalidFinancialEventStructureError
from app.application.ledger.unit_of_work import LedgerUnitOfWork
from app.domain.ledger.model.financial_event import MAX_SHOPPING_LIST_MOVEMENTS, FinancialEvent, FinancialEventDescription, FinancialEventType
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter
from app.domain.ledger.model.financial_movement import FinancialMovement, FinancialMovementItemName, FinancialMovementQuantity


ShoppingListMovement = tuple[UUID, int, FinancialMovementQuantity, FinancialMovementItemName | None]
UpdatedShoppingListMovement = tuple[UUID | None, UUID, int, FinancialMovementQuantity, FinancialMovementItemName | None]
TransferFee = tuple[UUID, int]
_Movement = tuple[UUID, UUID, int, FinancialMovementQuantity, FinancialMovementItemName | None]


def create_simple_financial_event(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    occurred_at: int,
    description: FinancialEventDescription,
    account_uuid: UUID,
    category_uuid: UUID,
    value: int,
    quantity: FinancialMovementQuantity,
    item_name: FinancialMovementItemName | None,
) -> FinancialEvent:
    if value == 0:
        raise InvalidFinancialEventError
    return _create_financial_event(unit_of_work_factory, occurred_at, description, "TRANSACTION", [(account_uuid, category_uuid, value, quantity, item_name)])


def create_shopping_list_financial_event(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    occurred_at: int,
    description: FinancialEventDescription,
    account_uuid: UUID,
    movements: Sequence[ShoppingListMovement],
) -> FinancialEvent:
    if not movements:
        raise InvalidFinancialEventError
    if len(movements) > MAX_SHOPPING_LIST_MOVEMENTS:
        raise InvalidFinancialEventError
    if any(value >= 0 for _, value, _, _ in movements):
        raise InvalidFinancialEventError
    return _create_financial_event(
        unit_of_work_factory,
        occurred_at,
        description,
        "SHOPPING_LIST",
        [(account_uuid, category_uuid, value, quantity, item_name) for category_uuid, value, quantity, item_name in movements],
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
    fee: TransferFee | None,
) -> FinancialEvent:
    if source_account_uuid == destination_account_uuid:
        raise InvalidFinancialEventError
    if source_value >= 0:
        raise InvalidFinancialEventError
    if destination_value <= 0:
        raise InvalidFinancialEventError
    if fee is not None and fee[1] >= 0:
        raise InvalidFinancialEventError
    movements: list[_Movement] = [
        (source_account_uuid, source_category_uuid, source_value, 1, None),
        (destination_account_uuid, destination_category_uuid, destination_value, 1, None),
    ]
    if fee is not None:
        movements.append((destination_account_uuid, fee[0], fee[1], 1, None))
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
        return unit_of_work.financial_event_repository.list_after(page_size + 1, ascending, filters, occurred_at, uuid)


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
) -> FinancialEvent:
    if value == 0:
        raise InvalidFinancialEventError
    with unit_of_work_factory() as unit_of_work:
        event = _get_event_of_type(unit_of_work, event_uuid, "TRANSACTION")
        if len(event.movements) != 1:
            raise InvalidFinancialEventStructureError
        _require_accounts(unit_of_work, [account_uuid])
        _require_categories(unit_of_work, [category_uuid])
        movement = _update_movement(unit_of_work, event.movements[0], account_uuid, category_uuid, value, quantity, item_name)
        updated_event = _update_event(unit_of_work, event, occurred_at, description, [movement])
        unit_of_work.commit()
    return updated_event


def update_shopping_list_financial_event(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    event_uuid: UUID,
    occurred_at: int,
    description: FinancialEventDescription,
    account_uuid: UUID,
    movements: Sequence[UpdatedShoppingListMovement],
) -> FinancialEvent:
    if not movements:
        raise InvalidFinancialEventError
    if len(movements) > MAX_SHOPPING_LIST_MOVEMENTS:
        raise InvalidFinancialEventError
    if any(value >= 0 for _, _, value, _, _ in movements):
        raise InvalidFinancialEventError
    supplied_uuids = [movement_uuid for movement_uuid, _, _, _, _ in movements if movement_uuid is not None]
    if len(supplied_uuids) != len(set(supplied_uuids)):
        raise InvalidFinancialEventError
    with unit_of_work_factory() as unit_of_work:
        event = _get_event_of_type(unit_of_work, event_uuid, "SHOPPING_LIST")
        if not event.movements or any(movement.value >= 0 for movement in event.movements):
            raise InvalidFinancialEventStructureError
        if len({movement.account_uuid for movement in event.movements}) != 1:
            raise InvalidFinancialEventStructureError
        existing_by_uuid = {movement.uuid: movement for movement in event.movements}
        if any(movement_uuid not in existing_by_uuid for movement_uuid in supplied_uuids):
            raise FinancialMovementNotFoundError
        _require_accounts(unit_of_work, [account_uuid])
        _require_categories(unit_of_work, [category_uuid for _, category_uuid, _, _, _ in movements])
        updated_movements: list[FinancialMovement] = []
        for movement_uuid, category_uuid, value, quantity, item_name in movements:
            if movement_uuid is None:
                updated_movements.append(unit_of_work.financial_movement_repository.create(event.uuid, account_uuid, category_uuid, value, item_name, quantity))
            else:
                updated_movements.append(_update_movement(unit_of_work, existing_by_uuid[movement_uuid], account_uuid, category_uuid, value, quantity, item_name))
        for movement_uuid in existing_by_uuid.keys() - set(supplied_uuids):
            unit_of_work.financial_movement_repository.delete(movement_uuid)
        updated_movements.sort(key=lambda movement: movement.uuid.bytes)
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
    fee: TransferFee | None,
) -> FinancialEvent:
    if source_account_uuid == destination_account_uuid:
        raise InvalidFinancialEventError
    if source_value >= 0:
        raise InvalidFinancialEventError
    if destination_value <= 0:
        raise InvalidFinancialEventError
    if fee is not None and fee[1] >= 0:
        raise InvalidFinancialEventError
    with unit_of_work_factory() as unit_of_work:
        event = _get_event_of_type(unit_of_work, event_uuid, "ACCOUNT_TRANSFER")
        source, destination, existing_fee = _transfer_movements(event)
        _require_accounts(unit_of_work, [source_account_uuid, destination_account_uuid])
        category_uuids = [source_category_uuid, destination_category_uuid]
        if fee is not None:
            category_uuids.append(fee[0])
        _require_categories(unit_of_work, category_uuids)
        updated_movements = [
            _update_movement(unit_of_work, source, source_account_uuid, source_category_uuid, source_value, 1, None),
            _update_movement(unit_of_work, destination, destination_account_uuid, destination_category_uuid, destination_value, 1, None),
        ]
        if fee is None:
            if existing_fee is not None:
                unit_of_work.financial_movement_repository.delete(existing_fee.uuid)
        elif existing_fee is None:
            updated_movements.append(unit_of_work.financial_movement_repository.create(event.uuid, destination_account_uuid, fee[0], fee[1], None, 1))
        else:
            updated_movements.append(_update_movement(unit_of_work, existing_fee, destination_account_uuid, fee[0], fee[1], 1, None))
        updated_movements.sort(key=lambda movement: movement.uuid.bytes)
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
    movements: Sequence[_Movement],
) -> FinancialEvent:
    with unit_of_work_factory() as unit_of_work:
        _require_accounts(unit_of_work, [movement[0] for movement in movements])
        _require_categories(unit_of_work, [movement[1] for movement in movements])
        event = unit_of_work.financial_event_repository.create(occurred_at, description, event_type)
        created_movements = [
            unit_of_work.financial_movement_repository.create(event.uuid, account_uuid, category_uuid, value, item_name, quantity)
            for account_uuid, category_uuid, value, quantity, item_name in movements
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
    updated_movement = FinancialMovement.model_validate({**movement.model_dump(), "account_uuid": account_uuid, "category_uuid": category_uuid, "value": value, "quantity": quantity, "item_name": item_name})
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


def _transfer_movements(event: FinancialEvent) -> tuple[FinancialMovement, FinancialMovement, FinancialMovement | None]:
    if len(event.movements) not in (2, 3):
        raise InvalidFinancialEventStructureError
    income_movements = [movement for movement in event.movements if movement.value > 0]
    if len(income_movements) != 1:
        raise InvalidFinancialEventStructureError
    destination = income_movements[0]
    source_movements = [movement for movement in event.movements if movement.value < 0 and movement.account_uuid != destination.account_uuid]
    fee_movements = [movement for movement in event.movements if movement.value < 0 and movement.account_uuid == destination.account_uuid]
    if len(source_movements) != 1 or len(fee_movements) > 1 or len(income_movements) + len(source_movements) + len(fee_movements) != len(event.movements):
        raise InvalidFinancialEventStructureError
    return source_movements[0], destination, fee_movements[0] if fee_movements else None
