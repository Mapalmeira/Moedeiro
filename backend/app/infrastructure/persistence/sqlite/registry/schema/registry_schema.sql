CREATE TABLE ledger (
    uuid BLOB PRIMARY KEY CHECK (length(uuid) = 16),
    path TEXT NOT NULL UNIQUE CHECK (length(path) >= 1)
) STRICT;

CREATE TABLE access_invitation (
    uuid BLOB PRIMARY KEY CHECK (length(uuid) = 16),
    ledger_uuid BLOB NOT NULL CHECK (length(ledger_uuid) = 16),
    grant_uuid BLOB NOT NULL UNIQUE CHECK (length(grant_uuid) = 16),
    secret_hash BLOB NOT NULL UNIQUE CHECK (length(secret_hash) = 32),
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    expires_at INTEGER NOT NULL CHECK (expires_at > created_at),
    consumed_at INTEGER CHECK (consumed_at IS NULL OR (consumed_at >= created_at AND consumed_at < expires_at)),
    revoked_at INTEGER CHECK (revoked_at IS NULL OR revoked_at >= created_at),

    CHECK (consumed_at IS NULL OR revoked_at IS NULL),

    FOREIGN KEY (ledger_uuid)
        REFERENCES ledger(uuid)
        ON DELETE CASCADE
) STRICT;

CREATE TABLE access_grant (
    uuid BLOB PRIMARY KEY CHECK (length(uuid) = 16),
    ledger_uuid BLOB NOT NULL CHECK (length(ledger_uuid) = 16),
    authentication_method TEXT NOT NULL CHECK (authentication_method IN ('WEBCRYPTO', 'WEBAUTHN')),
    label TEXT CHECK (label IS NULL OR length(label) <= 30),
    public_key BLOB NOT NULL CHECK (length(public_key) BETWEEN 1 AND 4096),
    algorithm TEXT NOT NULL CHECK (algorithm = 'ES256'),
    credential_id BLOB CHECK (credential_id IS NULL OR length(credential_id) BETWEEN 1 AND 1023),
    signature_counter INTEGER CHECK (signature_counter IS NULL OR signature_counter >= 0),
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    revoked_at INTEGER CHECK (revoked_at IS NULL OR revoked_at >= created_at),

    CHECK (
        (authentication_method = 'WEBCRYPTO'
         AND credential_id IS NULL
         AND signature_counter IS NULL)
        OR
        (authentication_method = 'WEBAUTHN'
         AND credential_id IS NOT NULL
         AND signature_counter IS NOT NULL)
    ),

    FOREIGN KEY (ledger_uuid)
        REFERENCES ledger(uuid)
        ON DELETE CASCADE
) STRICT;

CREATE TABLE auth_session (
    uuid BLOB PRIMARY KEY CHECK (length(uuid) = 16),
    grant_uuid BLOB NOT NULL CHECK (length(grant_uuid) = 16),
    token_hash BLOB NOT NULL UNIQUE CHECK (length(token_hash) = 32),
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    inactivity_timeout_seconds INTEGER NOT NULL DEFAULT 1800 CHECK (inactivity_timeout_seconds > 0),
    absolute_timeout_seconds INTEGER NOT NULL DEFAULT 43200 CHECK (absolute_timeout_seconds > 0),
    last_activity_at INTEGER CHECK (last_activity_at IS NULL OR (last_activity_at >= created_at AND last_activity_at < created_at + absolute_timeout_seconds)),
    revoked_at INTEGER CHECK (revoked_at IS NULL OR revoked_at >= created_at),

    CHECK (inactivity_timeout_seconds <= absolute_timeout_seconds),

    FOREIGN KEY (grant_uuid)
        REFERENCES access_grant(uuid)
        ON DELETE CASCADE
) STRICT;

CREATE INDEX access_invitation_ledger_idx ON access_invitation(ledger_uuid);
CREATE INDEX access_invitation_expires_at_idx ON access_invitation(expires_at);
CREATE INDEX access_grant_ledger_idx ON access_grant(ledger_uuid);
CREATE UNIQUE INDEX access_grant_credential_id_idx ON access_grant(credential_id) WHERE credential_id IS NOT NULL;
CREATE INDEX auth_session_grant_idx ON auth_session(grant_uuid);
CREATE INDEX auth_session_created_at_idx ON auth_session(created_at);
CREATE INDEX auth_session_last_activity_at_idx ON auth_session(last_activity_at);
