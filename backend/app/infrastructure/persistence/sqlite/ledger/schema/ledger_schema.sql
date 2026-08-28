CREATE TABLE ledger_metadata (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),

    ledger_uuid TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    schema_version INTEGER NOT NULL CHECK (schema_version >= 1),
    created_at INTEGER NOT NULL
) STRICT;

CREATE TABLE currency (
    uuid TEXT PRIMARY KEY,
    currency_name TEXT NOT NULL,
    suffix TEXT,
    prefix TEXT,
    decimal_places INTEGER NOT NULL CHECK (decimal_places >= 0)
) STRICT;

CREATE TABLE account (
    uuid TEXT PRIMARY KEY,
    account_name TEXT NOT NULL UNIQUE,
    note TEXT,
    currency_uuid TEXT NOT NULL,

    -- needed for FK in budget_accounts.
    UNIQUE (uuid, currency_uuid),

    FOREIGN KEY (currency_uuid) REFERENCES currency(uuid) ON DELETE RESTRICT
) STRICT;

CREATE TABLE category (
    uuid TEXT PRIMARY KEY,
    category_name TEXT NOT NULL,
    parent_uuid TEXT,

    FOREIGN KEY (parent_uuid) REFERENCES category(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE transaction_event (
    uuid TEXT PRIMARY KEY,
    occurred_at INTEGER NOT NULL,
    description TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('TRANSACTION', 'ACCOUNT_TRANSFER', 'SHOPPING_LIST'))
) STRICT;


CREATE TABLE tag (
    uuid TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
) STRICT;

CREATE TABLE transaction_tag (
    transaction_event_uuid TEXT NOT NULL,
    tag_uuid TEXT NOT NULL,

    PRIMARY KEY (transaction_event_uuid, tag_uuid),

    FOREIGN KEY (transaction_event_uuid) REFERENCES transaction_event(uuid) ON DELETE CASCADE,
    FOREIGN KEY (tag_uuid) REFERENCES tag(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE financial_movement (
    uuid TEXT PRIMARY KEY,
    transaction_event_uuid TEXT NOT NULL,
    value INTEGER NOT NULL,
    item_name TEXT,
    account_uuid TEXT NOT NULL,
    category_uuid TEXT NOT NULL,

    FOREIGN KEY (transaction_event_uuid)
        REFERENCES transaction_event(uuid)
        ON DELETE CASCADE,

    FOREIGN KEY (account_uuid)
        REFERENCES account(uuid)
        ON DELETE RESTRICT,

    FOREIGN KEY (category_uuid)
        REFERENCES category(uuid)
        ON DELETE RESTRICT
) STRICT;

CREATE TABLE budget (
    uuid TEXT PRIMARY KEY,
    from_timestamp INTEGER NOT NULL,
    to_timestamp INTEGER NOT NULL,
    budget_name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,

    amount INTEGER NOT NULL CHECK (amount >= 0),

    category_uuid TEXT NOT NULL,
    currency_uuid TEXT NOT NULL,

    CHECK (from_timestamp < to_timestamp),

    -- needed for FK in budget_accounts.
    UNIQUE (uuid, currency_uuid),


    FOREIGN KEY (category_uuid)
        REFERENCES category(uuid)
        ON DELETE RESTRICT,

    FOREIGN KEY (currency_uuid)
        REFERENCES currency(uuid)
        ON DELETE RESTRICT
) STRICT;

CREATE TABLE budget_accounts (
    budget_uuid TEXT NOT NULL,
    account_uuid TEXT NOT NULL,

    -- intentional redundancy to allow for ensuring every budget account
    -- has the same currency
    currency_uuid TEXT NOT NULL,

    PRIMARY KEY (budget_uuid, account_uuid),

    FOREIGN KEY (budget_uuid, currency_uuid)
        REFERENCES budget(uuid, currency_uuid)
        ON DELETE CASCADE,

    FOREIGN KEY (account_uuid, currency_uuid)
        REFERENCES account(uuid, currency_uuid)
        ON DELETE RESTRICT
) STRICT;
