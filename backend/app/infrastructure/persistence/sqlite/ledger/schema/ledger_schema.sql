CREATE TABLE ledger_metadata (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),

    ledger_uuid BLOB NOT NULL UNIQUE,
    schema_version INTEGER NOT NULL CHECK (schema_version >= 1),
    revision INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
    created_at INTEGER NOT NULL CHECK (created_at >= 0)
) STRICT;

CREATE TABLE currency (
    uuid BLOB PRIMARY KEY,
    currency_name TEXT NOT NULL CHECK (length(currency_name) BETWEEN 1 AND 30),
    suffix TEXT CHECK (suffix IS NULL OR length(suffix) <= 10),
    prefix TEXT CHECK (prefix IS NULL OR length(prefix) <= 10),
    decimal_places INTEGER NOT NULL CHECK (decimal_places BETWEEN 0 AND 20),
    icon TEXT NOT NULL CHECK (length(icon) BETWEEN 1 AND 50),
    color_code BLOB NOT NULL CHECK (length(color_code) = 3)
) STRICT;

CREATE TABLE account (
    uuid BLOB PRIMARY KEY,
    account_name TEXT NOT NULL UNIQUE CHECK (length(account_name) BETWEEN 1 AND 50),
    note TEXT CHECK (note IS NULL OR length(note) <= 300),
    currency_uuid BLOB NOT NULL,
    icon TEXT NOT NULL CHECK (length(icon) BETWEEN 1 AND 50),
    color_code BLOB NOT NULL CHECK (length(color_code) = 3),

    -- needed for FK in budget_accounts.
    UNIQUE (uuid, currency_uuid),

    FOREIGN KEY (currency_uuid) REFERENCES currency(uuid) ON DELETE RESTRICT
) STRICT;

CREATE TABLE category (
    uuid BLOB PRIMARY KEY,
    category_name TEXT NOT NULL CHECK (length(category_name) BETWEEN 1 AND 30),
    icon TEXT NOT NULL CHECK (length(icon) BETWEEN 1 AND 50),
    color_code BLOB NOT NULL CHECK (length(color_code) = 3),
    parent_uuid BLOB,

    FOREIGN KEY (parent_uuid) REFERENCES category(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE financial_event (
    uuid BLOB PRIMARY KEY,
    occurred_at INTEGER NOT NULL,
    description TEXT NOT NULL CHECK (length(description) BETWEEN 1 AND 300),
    type TEXT NOT NULL CHECK (type IN ('TRANSACTION', 'ACCOUNT_TRANSFER', 'SHOPPING_LIST'))
) STRICT;


CREATE TABLE financial_movement (
    uuid BLOB PRIMARY KEY,
    financial_event_uuid BLOB NOT NULL,
    value INTEGER NOT NULL CHECK (value <> 0),
    item_name TEXT CHECK (item_name IS NULL OR length(item_name) <= 50),
    account_uuid BLOB NOT NULL,
    category_uuid BLOB NOT NULL,

    FOREIGN KEY (financial_event_uuid)
        REFERENCES financial_event(uuid)
        ON DELETE CASCADE,

    FOREIGN KEY (account_uuid)
        REFERENCES account(uuid)
        ON DELETE RESTRICT,

    FOREIGN KEY (category_uuid)
        REFERENCES category(uuid)
        ON DELETE RESTRICT
) STRICT;

CREATE TABLE budget (
    uuid BLOB PRIMARY KEY,
    from_timestamp INTEGER NOT NULL,
    to_timestamp INTEGER NOT NULL,
    budget_name TEXT NOT NULL UNIQUE CHECK (length(budget_name) BETWEEN 1 AND 50),
    description TEXT NOT NULL CHECK (length(description) BETWEEN 1 AND 300),

    amount INTEGER NOT NULL CHECK (amount >= 0),
    icon TEXT NOT NULL CHECK (length(icon) BETWEEN 1 AND 50),
    color_code BLOB NOT NULL CHECK (length(color_code) = 3),

    category_uuid BLOB NOT NULL,
    currency_uuid BLOB NOT NULL,

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
    budget_uuid BLOB NOT NULL,
    account_uuid BLOB NOT NULL,

    -- intentional redundancy to allow for ensuring every budget account
    -- has the same currency
    currency_uuid BLOB NOT NULL,

    PRIMARY KEY (budget_uuid, account_uuid),

    FOREIGN KEY (budget_uuid, currency_uuid)
        REFERENCES budget(uuid, currency_uuid)
        ON DELETE CASCADE,

    FOREIGN KEY (account_uuid, currency_uuid)
        REFERENCES account(uuid, currency_uuid)
        ON DELETE RESTRICT
) STRICT;

CREATE INDEX category_name_idx
ON category(category_name);

CREATE INDEX category_parent_idx
ON category(parent_uuid);

CREATE INDEX financial_event_occurred_at_idx
ON financial_event(occurred_at);

CREATE INDEX financial_movement_financial_event_idx
ON financial_movement(financial_event_uuid);

CREATE INDEX financial_movement_account_event_idx
ON financial_movement(account_uuid, financial_event_uuid);

CREATE INDEX financial_movement_category_event_idx
ON financial_movement(category_uuid, financial_event_uuid);
