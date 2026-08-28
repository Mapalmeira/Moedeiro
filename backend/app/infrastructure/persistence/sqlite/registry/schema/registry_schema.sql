CREATE TABLE ledger (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL UNIQUE
) STRICT;

CREATE TABLE ledger_token (
    id TEXT PRIMARY KEY,
    ledger_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    label TEXT,
    created_at INTEGER NOT NULL,
    revoked_at INTEGER,

    FOREIGN KEY (ledger_id)
        REFERENCES ledger(id)
        ON DELETE CASCADE
) STRICT;