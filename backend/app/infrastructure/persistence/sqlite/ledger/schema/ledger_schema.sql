CREATE TABLE ledger_metadata (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),

    ledger_uuid BLOB NOT NULL UNIQUE CHECK (length(ledger_uuid) = 16),
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 50),
    schema_version INTEGER NOT NULL CHECK (schema_version >= 1),
    created_at INTEGER NOT NULL
) STRICT;

CREATE TABLE currency (
    uuid BLOB PRIMARY KEY CHECK (length(uuid) = 16),
    currency_name TEXT NOT NULL CHECK (length(currency_name) BETWEEN 1 AND 30),
    suffix TEXT CHECK (suffix IS NULL OR length(suffix) <= 10),
    prefix TEXT CHECK (prefix IS NULL OR length(prefix) <= 10),
    decimal_places INTEGER NOT NULL CHECK (decimal_places BETWEEN 0 AND 20)
) STRICT;

CREATE TABLE account (
    uuid BLOB PRIMARY KEY CHECK (length(uuid) = 16),
    account_name TEXT NOT NULL UNIQUE CHECK (length(account_name) BETWEEN 1 AND 50),
    note TEXT CHECK (note IS NULL OR length(note) <= 300),
    currency_uuid BLOB NOT NULL CHECK (length(currency_uuid) = 16),

    -- needed for FK in budget_accounts.
    UNIQUE (uuid, currency_uuid),

    FOREIGN KEY (currency_uuid) REFERENCES currency(uuid) ON DELETE RESTRICT
) STRICT;

CREATE TABLE category (
    uuid BLOB PRIMARY KEY CHECK (length(uuid) = 16),
    category_name TEXT NOT NULL CHECK (length(category_name) BETWEEN 1 AND 30),
    parent_uuid BLOB CHECK (parent_uuid IS NULL OR length(parent_uuid) = 16),

    FOREIGN KEY (parent_uuid) REFERENCES category(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE financial_event (
    uuid BLOB PRIMARY KEY CHECK (length(uuid) = 16),
    occurred_at INTEGER NOT NULL,
    description TEXT NOT NULL CHECK (length(description) BETWEEN 1 AND 1000),
    type TEXT NOT NULL CHECK (type IN ('TRANSACTION', 'ACCOUNT_TRANSFER', 'SHOPPING_LIST'))
) STRICT;


CREATE TABLE tag (
    uuid BLOB PRIMARY KEY CHECK (length(uuid) = 16),
    name TEXT NOT NULL UNIQUE CHECK (length(name) BETWEEN 1 AND 30)
) STRICT;

CREATE TABLE financial_event_tag (
    financial_event_uuid BLOB NOT NULL CHECK (length(financial_event_uuid) = 16),
    tag_uuid BLOB NOT NULL CHECK (length(tag_uuid) = 16),

    PRIMARY KEY (financial_event_uuid, tag_uuid),

    FOREIGN KEY (financial_event_uuid) REFERENCES financial_event(uuid) ON DELETE CASCADE,
    FOREIGN KEY (tag_uuid) REFERENCES tag(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE financial_movement (
    uuid BLOB PRIMARY KEY CHECK (length(uuid) = 16),
    financial_event_uuid BLOB NOT NULL CHECK (length(financial_event_uuid) = 16),
    value INTEGER NOT NULL CHECK (value <> 0),
    item_name TEXT CHECK (item_name IS NULL OR length(item_name) <= 50),
    account_uuid BLOB NOT NULL CHECK (length(account_uuid) = 16),
    category_uuid BLOB NOT NULL CHECK (length(category_uuid) = 16),

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
    uuid BLOB PRIMARY KEY CHECK (length(uuid) = 16),
    from_timestamp INTEGER NOT NULL,
    to_timestamp INTEGER NOT NULL,
    budget_name TEXT NOT NULL UNIQUE CHECK (length(budget_name) BETWEEN 1 AND 50),
    description TEXT NOT NULL CHECK (length(description) BETWEEN 1 AND 300),

    amount INTEGER NOT NULL CHECK (amount >= 0),

    category_uuid BLOB NOT NULL CHECK (length(category_uuid) = 16),
    currency_uuid BLOB NOT NULL CHECK (length(currency_uuid) = 16),

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
    budget_uuid BLOB NOT NULL CHECK (length(budget_uuid) = 16),
    account_uuid BLOB NOT NULL CHECK (length(account_uuid) = 16),

    -- intentional redundancy to allow for ensuring every budget account
    -- has the same currency
    currency_uuid BLOB NOT NULL CHECK (length(currency_uuid) = 16),

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

CREATE INDEX financial_event_tag_tag_event_idx
ON financial_event_tag(tag_uuid, financial_event_uuid);

CREATE INDEX financial_movement_financial_event_idx
ON financial_movement(financial_event_uuid);

CREATE INDEX financial_movement_account_event_idx
ON financial_movement(account_uuid, financial_event_uuid);

CREATE INDEX financial_movement_category_event_idx
ON financial_movement(category_uuid, financial_event_uuid);
