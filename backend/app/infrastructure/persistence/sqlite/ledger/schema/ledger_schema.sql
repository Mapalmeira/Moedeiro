CREATE TABLE ledger_metadata (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),

    ledger_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    schema_version INTEGER NOT NULL CHECK (schema_version >= 1),
    created_at INTEGER NOT NULL
) STRICT;

CREATE TABLE currency (
    id TEXT PRIMARY KEY,
    currency_name TEXT NOT NULL,
    suffix TEXT,
    prefix TEXT,
    decimal_places INTEGER NOT NULL CHECK (decimal_places >= 0)
) STRICT;

CREATE TABLE account (
    id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL UNIQUE,
    note TEXT NOT NULL,
    currency_id TEXT NOT NULL,

    -- needed for FK in budget_accounts.
    UNIQUE (id, currency_id),

    FOREIGN KEY (currency_id) REFERENCES currency(id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE category (
    id TEXT PRIMARY KEY,
    category_name TEXT NOT NULL,
    parent_id TEXT,

    FOREIGN KEY (parent_id) REFERENCES category(id) ON DELETE CASCADE
) STRICT;

CREATE TABLE transaction_event (
    id TEXT PRIMARY KEY,
    occurred_at INTEGER NOT NULL,
    description TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('TRANSACTION', 'ACCOUNT_TRANSFER', 'SHOPPING_LIST'))
) STRICT;


CREATE TABLE tag (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
) STRICT;

CREATE TABLE transaction_tag (
    transaction_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,

    PRIMARY KEY (transaction_id, tag_id),

    FOREIGN KEY (transaction_id) REFERENCES transaction_event(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tag(id) ON DELETE CASCADE
) STRICT;

CREATE TABLE movement (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    value INTEGER NOT NULL,
    item_name TEXT,
    account_id TEXT NOT NULL,
    category_id TEXT NOT NULL,

    FOREIGN KEY (event_id)
        REFERENCES transaction_event(id)
        ON DELETE CASCADE,

    FOREIGN KEY (account_id)
        REFERENCES account(id)
        ON DELETE RESTRICT,

    FOREIGN KEY (category_id)
        REFERENCES category(id)
        ON DELETE RESTRICT
) STRICT;

CREATE TABLE budget (
    id TEXT PRIMARY KEY,
    from_timestamp INTEGER NOT NULL,
    to_timestamp INTEGER NOT NULL,
    budget_name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,

    amount INTEGER NOT NULL CHECK (amount >= 0),

    category_id TEXT NOT NULL,
    currency_id TEXT NOT NULL,

    CHECK (from_timestamp < to_timestamp),

    -- needed for FK in budget_accounts.
    UNIQUE (id, currency_id),


    FOREIGN KEY (category_id)
        REFERENCES category(id)
        ON DELETE RESTRICT,

    FOREIGN KEY (currency_id)
        REFERENCES currency(id)
        ON DELETE RESTRICT
) STRICT;

CREATE TABLE budget_accounts (
    budget_id TEXT NOT NULL,
    account_id TEXT NOT NULL,

    -- intentional redundancy to allow for ensuring every budget account
    -- has the same currency
    currency_id TEXT NOT NULL,

    PRIMARY KEY (budget_id, account_id),

    FOREIGN KEY (budget_id, currency_id)
        REFERENCES budget(id, currency_id)
        ON DELETE CASCADE,

    FOREIGN KEY (account_id, currency_id)
        REFERENCES account(id, currency_id)
        ON DELETE RESTRICT
) STRICT;
