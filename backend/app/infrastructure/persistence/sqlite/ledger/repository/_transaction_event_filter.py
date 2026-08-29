from app.domain.ledger.model.transaction_event_filter import TransactionEventFilter


def build_transaction_event_filter(filters: TransactionEventFilter) -> tuple[str, list[str | int]]:
    clauses = ["event.occurred_at >= ?", "event.occurred_at < ?"]
    parameters: list[str | int] = [filters.from_timestamp, filters.to_timestamp]

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
                  AND category_movement.category_uuid IN (
                      WITH RECURSIVE category_descendants(uuid) AS (
                          SELECT uuid
                          FROM category
                          WHERE uuid IN ({placeholders})

                          UNION

                          SELECT child.uuid
                          FROM category AS child
                          JOIN category_descendants AS parent ON child.parent_uuid = parent.uuid
                      )
                      SELECT uuid FROM category_descendants
                  )
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

    return "WHERE " + " AND ".join(clauses), parameters
