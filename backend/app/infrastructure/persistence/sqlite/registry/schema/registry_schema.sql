CREATE TABLE ledger (
    uuid BLOB PRIMARY KEY CHECK (length(uuid) = 16),
    path TEXT NOT NULL UNIQUE CHECK (length(path) >= 1)
) STRICT;

CREATE TABLE ledger_token (
    uuid BLOB PRIMARY KEY CHECK (length(uuid) = 16),
    ledger_uuid BLOB NOT NULL CHECK (length(ledger_uuid) = 16),
    token_hash TEXT NOT NULL UNIQUE CHECK (length(token_hash) BETWEEN 1 AND 255),
    label TEXT CHECK (label IS NULL OR length(label) <= 30),
    created_at INTEGER NOT NULL,
    revoked_at INTEGER,

    FOREIGN KEY (ledger_uuid)
        REFERENCES ledger(uuid)
        ON DELETE CASCADE
) STRICT;
