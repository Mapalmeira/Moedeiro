from app.domain.ledger.model.transaction_event_filter import TransactionEventFilter


def build_transaction_event_filter(filters: TransactionEventFilter) -> tuple[str, list[str | int]]:
    clauses: list[str] = []
    parameters: list[str | int] = []

    if filters.from_timestamp is not None:
        clauses.append("event.occurred_at >= ?")
        parameters.append(filters.from_timestamp)
    if filters.to_timestamp is not None:
        clauses.append("event.occurred_at < ?")
        parameters.append(filters.to_timestamp)
    if filters.account_uuid is not None:
        clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM financial_movement AS account_movement
                WHERE account_movement.transaction_event_uuid = event.uuid
                  AND account_movement.account_uuid = ?
            )
            """
        )
        parameters.append(str(filters.account_uuid))
    if filters.category_uuids:
        placeholders = ", ".join("?" for _ in filters.category_uuids)
        clauses.append(
            f"""
            EXISTS (
                SELECT 1
                FROM financial_movement AS category_movement
                WHERE category_movement.transaction_event_uuid = event.uuid
                  AND category_movement.category_uuid IN ({placeholders})
            )
            """
        )
        parameters.extend(sorted(str(uuid) for uuid in filters.category_uuids))
    if filters.tag_uuids:
        placeholders = ", ".join("?" for _ in filters.tag_uuids)
        clauses.append(
            f"""
            EXISTS (
                SELECT 1
                FROM transaction_tag
                WHERE transaction_tag.transaction_event_uuid = event.uuid
                  AND transaction_tag.tag_uuid IN ({placeholders})
            )
            """
        )
        parameters.extend(sorted(str(uuid) for uuid in filters.tag_uuids))
    if filters.event_types:
        placeholders = ", ".join("?" for _ in filters.event_types)
        clauses.append(f"event.type IN ({placeholders})")
        parameters.extend(sorted(filters.event_types))

    if not clauses:
        return "", parameters
    return "WHERE " + " AND ".join(clauses), parameters
