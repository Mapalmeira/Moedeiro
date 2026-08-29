from app.domain.ledger.model.financial_event_filter import FinancialEventFilter


def build_financial_event_filter(filters: FinancialEventFilter) -> tuple[str, list[bytes | str | int]]:
    clauses = ["event.occurred_at >= ?", "event.occurred_at < ?"]
    parameters: list[bytes | str | int] = [filters.from_timestamp, filters.to_timestamp]

    if filters.account_uuid is not None:
        clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM financial_movement AS account_movement
                WHERE account_movement.financial_event_uuid = event.uuid
                  AND account_movement.account_uuid = ?
            )
            """
        )
        parameters.append(filters.account_uuid.bytes)
    if filters.category_uuid is not None:
        clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM financial_movement AS category_movement
                WHERE category_movement.financial_event_uuid = event.uuid
                  AND category_movement.category_uuid IN (
                      WITH RECURSIVE category_descendants(uuid) AS (
                          SELECT uuid
                          FROM category
                          WHERE uuid = ?

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
        parameters.append(filters.category_uuid.bytes)
    if filters.tag_uuid is not None:
        clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM financial_event_tag
                WHERE financial_event_tag.financial_event_uuid = event.uuid
                  AND financial_event_tag.tag_uuid = ?
            )
            """
        )
        parameters.append(filters.tag_uuid.bytes)
    if filters.event_type is not None:
        clauses.append("event.type = ?")
        parameters.append(filters.event_type)

    return "WHERE " + " AND ".join(clauses), parameters
