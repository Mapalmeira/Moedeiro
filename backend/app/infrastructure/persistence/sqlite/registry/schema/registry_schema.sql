CREATE TABLE user_invitation (
    uuid BLOB PRIMARY KEY,
    secret_hash BLOB NOT NULL UNIQUE,
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    expiration_timeout_seconds INTEGER NOT NULL DEFAULT 3600 CHECK (expiration_timeout_seconds > 0),
    consumed_at INTEGER CHECK (consumed_at IS NULL OR (consumed_at >= created_at AND consumed_at < created_at + expiration_timeout_seconds)),
    revoked_at INTEGER CHECK (revoked_at IS NULL OR revoked_at >= created_at),

    CHECK (consumed_at IS NULL OR revoked_at IS NULL)
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
    icon TEXT NOT NULL CHECK (length(icon) BETWEEN 1 AND 50),
    color_code BLOB NOT NULL CHECK (length(color_code) = 3)
) STRICT;

CREATE TABLE ledger_grant (
    uuid BLOB PRIMARY KEY,
    user_uuid BLOB NOT NULL,
    ledger_uuid BLOB NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('OWNER', 'EDITOR', 'READER')),
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    revoked_at INTEGER CHECK (revoked_at IS NULL OR revoked_at >= created_at),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE,
    FOREIGN KEY (ledger_uuid) REFERENCES ledger(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE webauthn_credential (
    uuid BLOB PRIMARY KEY,
    user_uuid BLOB NOT NULL,
    credential_id BLOB NOT NULL UNIQUE,
    public_key BLOB NOT NULL,
    sign_count INTEGER NOT NULL CHECK (sign_count >= 0),
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    last_used_at INTEGER CHECK (last_used_at IS NULL OR last_used_at >= created_at),
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 50),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE mfa_method (
    uuid BLOB PRIMARY KEY,
    user_uuid BLOB NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('TOTP')),
    secret_encrypted BLOB NOT NULL,
    created_at INTEGER NOT NULL CHECK (created_at >= 0),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE recovery_code (
    uuid BLOB PRIMARY KEY,
    user_uuid BLOB NOT NULL,
    code_hash BLOB NOT NULL UNIQUE,
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    used_at INTEGER CHECK (used_at IS NULL OR used_at >= created_at),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE user_preferences (
    user_uuid BLOB PRIMARY KEY,
    date_format TEXT CHECK (date_format IS NULL OR length(date_format) >= 1),
    time_format TEXT CHECK (time_format IS NULL OR length(time_format) >= 1),
    number_format TEXT CHECK (number_format IS NULL OR length(number_format) >= 1),
    theme TEXT CHECK (theme IS NULL OR theme IN ('LIGHT', 'DARK')),
    timezone TEXT CHECK (timezone IS NULL OR length(timezone) >= 1),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE auth_session (
    uuid BLOB PRIMARY KEY,
    user_uuid BLOB NOT NULL,
    token_hash BLOB NOT NULL UNIQUE,
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    last_activity_at INTEGER CHECK (last_activity_at IS NULL OR last_activity_at >= created_at),
    revoked_at INTEGER CHECK (revoked_at IS NULL OR revoked_at >= created_at),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE remember_session (
    uuid BLOB PRIMARY KEY,
    user_uuid BLOB NOT NULL,
    token_hash BLOB NOT NULL UNIQUE,
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    expiration_timeout_seconds INTEGER NOT NULL DEFAULT 2592000 CHECK (expiration_timeout_seconds > 0),
    last_used_at INTEGER CHECK (last_used_at IS NULL OR (last_used_at >= created_at AND last_used_at < created_at + expiration_timeout_seconds)),
    revoked_at INTEGER CHECK (revoked_at IS NULL OR revoked_at >= created_at),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

CREATE INDEX user_invitation_created_at_idx ON user_invitation(created_at);
CREATE UNIQUE INDEX ledger_grant_active_user_ledger_idx ON ledger_grant(user_uuid, ledger_uuid) WHERE revoked_at IS NULL;
CREATE INDEX ledger_grant_user_idx ON ledger_grant(user_uuid);
CREATE INDEX ledger_grant_ledger_idx ON ledger_grant(ledger_uuid);
CREATE INDEX webauthn_credential_user_idx ON webauthn_credential(user_uuid);
CREATE INDEX mfa_method_user_idx ON mfa_method(user_uuid);
CREATE INDEX recovery_code_user_idx ON recovery_code(user_uuid);
CREATE INDEX auth_session_user_idx ON auth_session(user_uuid);
CREATE INDEX auth_session_created_at_idx ON auth_session(created_at);
CREATE INDEX auth_session_last_activity_at_idx ON auth_session(last_activity_at);
CREATE INDEX remember_session_user_idx ON remember_session(user_uuid);
CREATE INDEX remember_session_created_at_idx ON remember_session(created_at);
CREATE INDEX remember_session_last_used_at_idx ON remember_session(last_used_at);
