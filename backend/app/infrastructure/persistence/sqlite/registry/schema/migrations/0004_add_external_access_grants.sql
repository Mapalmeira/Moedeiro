CREATE TABLE ledger_grant_v4 (
    uuid BLOB PRIMARY KEY,
    user_uuid BLOB NOT NULL,
    ledger_uuid BLOB NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('OWNER', 'EXTERNAL_ACCESS')),
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    revoked_at INTEGER CHECK (revoked_at IS NULL OR revoked_at >= created_at),

    UNIQUE (uuid, type),
    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE,
    FOREIGN KEY (ledger_uuid) REFERENCES ledger(uuid) ON DELETE CASCADE
) STRICT;

INSERT INTO ledger_grant_v4(uuid, user_uuid, ledger_uuid, type, created_at, revoked_at)
SELECT uuid, user_uuid, ledger_uuid, role, created_at, revoked_at
FROM ledger_grant;

DROP TABLE ledger_grant;
ALTER TABLE ledger_grant_v4 RENAME TO ledger_grant;

CREATE TABLE ledger_token_grant (
    uuid BLOB PRIMARY KEY,
    type TEXT NOT NULL CHECK (type = 'EXTERNAL_ACCESS'),
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 50),
    token_hash BLOB NOT NULL UNIQUE CHECK (length(token_hash) = 32),

    FOREIGN KEY (uuid, type) REFERENCES ledger_grant(uuid, type) ON DELETE CASCADE
) STRICT;

CREATE UNIQUE INDEX ledger_grant_active_ledger_owner_idx ON ledger_grant(ledger_uuid) WHERE revoked_at IS NULL AND type = 'OWNER';
CREATE INDEX ledger_grant_user_idx ON ledger_grant(user_uuid);
CREATE INDEX ledger_grant_ledger_idx ON ledger_grant(ledger_uuid);
CREATE INDEX ledger_grant_revoked_idx ON ledger_grant(revoked_at) WHERE revoked_at IS NOT NULL;
