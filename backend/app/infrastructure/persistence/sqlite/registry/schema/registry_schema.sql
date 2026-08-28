CREATE TABLE ledger (
    uuid TEXT PRIMARY KEY,
    path TEXT NOT NULL UNIQUE
) STRICT;

CREATE TABLE ledger_token (
    uuid TEXT PRIMARY KEY,
    ledger_uuid TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    label TEXT,
    created_at INTEGER NOT NULL,
    revoked_at INTEGER,

    FOREIGN KEY (ledger_uuid)
        REFERENCES ledger(uuid)
        ON DELETE CASCADE
) STRICT;
