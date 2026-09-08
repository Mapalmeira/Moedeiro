CREATE TABLE registry_metadata (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    schema_version INTEGER NOT NULL CHECK (schema_version >= 1)
) STRICT;

CREATE TABLE user_invitation (
    uuid BLOB PRIMARY KEY,
    secret_hash BLOB NOT NULL UNIQUE,
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    expires_at INTEGER NOT NULL CHECK (expires_at > created_at),
    consumed_at INTEGER CHECK (consumed_at IS NULL OR (consumed_at >= created_at AND consumed_at < expires_at))
) STRICT;

CREATE TABLE user_account (
    uuid BLOB PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 50),
    normalized_name TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    password_changed_at INTEGER NOT NULL CHECK (password_changed_at >= created_at)
) STRICT;

CREATE TABLE ledger (
    uuid BLOB PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 50),
    path TEXT NOT NULL UNIQUE,
    icon TEXT NOT NULL CHECK (length(icon) BETWEEN 1 AND 100),
    color_code BLOB NOT NULL CHECK (length(color_code) = 3),
    last_accessed_at INTEGER NOT NULL CHECK (last_accessed_at >= 0)
) STRICT;

CREATE TABLE ledger_grant (
    uuid BLOB PRIMARY KEY,
    user_uuid BLOB NOT NULL,
    ledger_uuid BLOB NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('OWNER')),
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    revoked_at INTEGER CHECK (revoked_at IS NULL OR revoked_at >= created_at),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE,
    FOREIGN KEY (ledger_uuid) REFERENCES ledger(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE mfa_method (
    uuid BLOB PRIMARY KEY,
    user_uuid BLOB NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('TOTP')),
    secret_encrypted BLOB NOT NULL,
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    expires_unconfirmed_at INTEGER NOT NULL CHECK (expires_unconfirmed_at > created_at),
    confirmed_at INTEGER CHECK (confirmed_at IS NULL OR confirmed_at >= created_at),
    last_used_counter INTEGER,

    UNIQUE (user_uuid, type),
    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE recovery_code (
    uuid BLOB PRIMARY KEY,
    user_uuid BLOB NOT NULL,
    code_hash BLOB NOT NULL UNIQUE,
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    expires_at INTEGER NOT NULL CHECK (expires_at > created_at),
    used_at INTEGER CHECK (used_at IS NULL OR (used_at >= created_at AND used_at < expires_at)),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE user_preferences (
    user_uuid BLOB PRIMARY KEY,
    language TEXT NOT NULL CHECK (language IN ('pt-BR', 'en')),
    date_format TEXT NOT NULL CHECK (date_format IN ('DMY', 'MDY', 'YMD')),
    time_format TEXT NOT NULL CHECK (time_format IN ('H12', 'H24')),
    number_format TEXT NOT NULL CHECK (number_format IN ('COMMA', 'DOT')),
    theme TEXT NOT NULL CHECK (theme IN ('LIGHT', 'DARK')),
    timezone TEXT NOT NULL CHECK (length(timezone) BETWEEN 1 AND 50),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE auth_session (
    uuid BLOB PRIMARY KEY,
    user_uuid BLOB NOT NULL,
    token_hash BLOB NOT NULL UNIQUE,
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    expires_at INTEGER NOT NULL CHECK (expires_at > created_at),
    inactivity_timeout_seconds INTEGER NOT NULL CHECK (inactivity_timeout_seconds > 0),
    last_activity_at INTEGER CHECK (last_activity_at IS NULL OR (last_activity_at >= created_at AND last_activity_at < expires_at)),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE remember_session (
    uuid BLOB PRIMARY KEY,
    user_uuid BLOB NOT NULL,
    token_hash BLOB NOT NULL UNIQUE,
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    expires_at INTEGER NOT NULL CHECK (expires_at > created_at),
    last_used_at INTEGER CHECK (last_used_at IS NULL OR (last_used_at >= created_at AND last_used_at < expires_at)),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

CREATE UNIQUE INDEX ledger_grant_active_user_ledger_idx ON ledger_grant(user_uuid, ledger_uuid) WHERE revoked_at IS NULL;
CREATE UNIQUE INDEX ledger_grant_active_ledger_owner_idx ON ledger_grant(ledger_uuid) WHERE revoked_at IS NULL AND role = 'OWNER';
CREATE INDEX ledger_grant_user_idx ON ledger_grant(user_uuid);
CREATE INDEX ledger_grant_ledger_idx ON ledger_grant(ledger_uuid);
CREATE INDEX ledger_grant_revoked_idx ON ledger_grant(revoked_at) WHERE revoked_at IS NOT NULL;
CREATE INDEX recovery_code_user_idx ON recovery_code(user_uuid);
CREATE UNIQUE INDEX recovery_code_active_user_idx ON recovery_code(user_uuid) WHERE used_at IS NULL;
CREATE INDEX recovery_code_used_idx ON recovery_code(used_at) WHERE used_at IS NOT NULL;
CREATE INDEX recovery_code_expires_idx ON recovery_code(expires_at);
CREATE INDEX auth_session_user_idx ON auth_session(user_uuid);
CREATE INDEX auth_session_expires_idx ON auth_session(expires_at);
CREATE INDEX auth_session_inactive_idx ON auth_session(COALESCE(last_activity_at, created_at) + inactivity_timeout_seconds);
CREATE INDEX remember_session_user_idx ON remember_session(user_uuid);
CREATE INDEX remember_session_expires_idx ON remember_session(expires_at);
CREATE INDEX user_invitation_consumed_idx ON user_invitation(consumed_at) WHERE consumed_at IS NOT NULL;
CREATE INDEX user_invitation_expires_idx ON user_invitation(expires_at);
CREATE INDEX mfa_method_unconfirmed_idx ON mfa_method(expires_unconfirmed_at) WHERE confirmed_at IS NULL;
