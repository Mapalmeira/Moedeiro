from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from app.application.ledger.exceptions import AccountNotFoundError, CategoryNotFoundError, CurrencyNotFoundError, InvalidQueryParameterError, QueryPointLimitExceededError
from app.application.ledger.unit_of_work import LedgerUnitOfWork
from app.domain.ledger.model.cash_flow import CashFlow
from app.domain.ledger.model.cash_flow_sankey import CashFlowSankey, CashFlowSankeyLink, CashFlowSankeyNode
from app.domain.ledger.model.category import MAX_CATEGORY_DEPTH, MAX_CATEGORY_TREE_SIZE, Category
from app.domain.ledger.model.category_tree_node import CategoryTreeNode
from app.domain.ledger.model.financial_event_filter import FinancialEventFilter


def get_cash_flow_summary(unit_of_work_factory: Callable[[], LedgerUnitOfWork], currency_uuid: UUID, filters: FinancialEventFilter) -> CashFlow:
    with unit_of_work_factory() as unit_of_work:
        _require_filter_relations(unit_of_work, currency_uuid, filters)
        return unit_of_work.cash_flow_query_repository.get_summary(currency_uuid, filters)


def list_cash_flow_points(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    currency_uuid: UUID,
    filters: FinancialEventFilter,
    point_width: int,
    max_points: int,
) -> list[CashFlow]:
    if point_width < 1:
        raise InvalidQueryParameterError
    point_count = (filters.to_timestamp - filters.from_timestamp + point_width - 1) // point_width
    if point_count > max_points:
        raise QueryPointLimitExceededError
    with unit_of_work_factory() as unit_of_work:
        _require_filter_relations(unit_of_work, currency_uuid, filters)
        return unit_of_work.cash_flow_query_repository.list_points(currency_uuid, filters, point_width)


def _require_filter_relations(unit_of_work: LedgerUnitOfWork, currency_uuid: UUID, filters: FinancialEventFilter) -> None:
    if unit_of_work.currency_repository.get(currency_uuid) is None:
        raise CurrencyNotFoundError
    if filters.account_uuid is not None and unit_of_work.account_repository.get(filters.account_uuid) is None:
        raise AccountNotFoundError
    if filters.category_uuid is not None and unit_of_work.category_repository.get(filters.category_uuid) is None:
        raise CategoryNotFoundError


def get_cash_flow_sankey(
    unit_of_work_factory: Callable[[], LedgerUnitOfWork],
    account_uuid: UUID,
    filters: FinancialEventFilter,
    detail_level: int,
) -> CashFlowSankey:
    if not 1 <= detail_level <= MAX_CATEGORY_DEPTH:
        raise InvalidQueryParameterError

    with unit_of_work_factory() as unit_of_work:
        account = unit_of_work.account_repository.get(account_uuid)
        if account is None:
            raise AccountNotFoundError
        category_totals = unit_of_work.cash_flow_query_repository.list_category_totals(account_uuid, filters)
        category_tree = unit_of_work.category_repository.get_tree(MAX_CATEGORY_TREE_SIZE)

    paths, order_by_uuid = _category_paths(category_tree)
    displayed_depth = max(
        (min(detail_level, len(path)) for total in category_totals if (total.income or total.expense) and (path := paths.get(total.category_uuid))),
        default=1,
    )
    nodes: dict[str, CashFlowSankeyNode] = {}
    node_values: dict[str, int] = {}
    link_values: dict[tuple[str, str], int] = {}
    income = 0
    expense = 0
    account_id = f"account:{account.uuid}"

    def add_category_path(side: str, path: list[Category], amount: int) -> None:
        if amount <= 0 or not path:
            return
        truncated = path[:detail_level]
        ids = [f"{side}:{category.uuid}" for category in truncated]
        for level, (node_id, category) in enumerate(zip(ids, truncated, strict=True)):
            if node_id not in nodes:
                nodes[node_id] = CashFlowSankeyNode(
                    id=node_id,
                    kind="category",
                    side=side,
                    label=category.name,
                    color_code=category.color_code,
                    column=level if side == "income" else displayed_depth + 1 + level,
                    order=order_by_uuid[category.uuid],
                    value=0,
                    category_uuid=category.uuid,
                )
            node_values[node_id] = node_values.get(node_id, 0) + amount

        if side == "income":
            chain = [*ids, account_id]
        else:
            chain = [account_id, *ids]
        for source, target in zip(chain, chain[1:], strict=False):
            link_values[(source, target)] = link_values.get((source, target), 0) + amount

    for total in category_totals:
        path = paths.get(total.category_uuid)
        if path is None:
            continue
        if total.income:
            income += total.income
            add_category_path("income", path, total.income)
        if total.expense:
            expense += total.expense
            add_category_path("expense", path, total.expense)

    if income or expense:
        nodes[account_id] = CashFlowSankeyNode(
            id=account_id,
            kind="account",
            side="account",
            label=account.name,
            color_code=account.color_code,
            column=displayed_depth,
            order=0,
            value=max(income, expense),
        )

    resolved_nodes = [
        node.model_copy(update={"value": node_values.get(node.id, node.value)})
        for node in nodes.values()
    ]
    resolved_nodes.sort(key=lambda node: (node.column, node.order, node.label.casefold(), node.id))
    links = [
        CashFlowSankeyLink(source=source, target=target, value=value)
        for (source, target), value in sorted(link_values.items())
        if value > 0
    ]
    return CashFlowSankey(
        account_uuid=account.uuid,
        currency_uuid=account.currency_uuid,
        from_timestamp=filters.from_timestamp,
        to_timestamp=filters.to_timestamp,
        detail_level=detail_level,
        income=income,
        expense=expense,
        nodes=resolved_nodes,
        links=links,
    )


def _category_paths(tree: list[CategoryTreeNode]) -> tuple[dict[UUID, list[Category]], dict[UUID, int]]:
    paths: dict[UUID, list[Category]] = {}
    order_by_uuid: dict[UUID, int] = {}
    order = 0

    def visit(node: CategoryTreeNode, ancestors: list[Category]) -> None:
        nonlocal order
        path = [*ancestors, node.category]
        paths[node.category.uuid] = path
        order_by_uuid[node.category.uuid] = order
        order += 1
        for child in node.children:
            visit(child, path)

    for root in tree:
        visit(root, [])
    return paths, order_by_uuid
