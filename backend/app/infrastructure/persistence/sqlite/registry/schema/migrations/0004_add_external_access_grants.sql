CREATE TEMP TABLE user_account_v3 AS SELECT * FROM user_account;
CREATE TEMP TABLE ledger_grant_v3 AS SELECT * FROM ledger_grant;
CREATE TEMP TABLE mfa_method_v3 AS SELECT * FROM mfa_method;
CREATE TEMP TABLE recovery_code_v3 AS SELECT * FROM recovery_code;
CREATE TEMP TABLE user_preferences_v3 AS SELECT * FROM user_preferences;
CREATE TEMP TABLE auth_session_v3 AS SELECT * FROM auth_session;
CREATE TEMP TABLE remember_session_v3 AS SELECT * FROM remember_session;

DROP TABLE ledger_grant;
DROP TABLE mfa_method;
DROP TABLE recovery_code;
DROP TABLE user_preferences;
DROP TABLE auth_session;
DROP TABLE remember_session;
DROP TABLE user_account;

CREATE TABLE ledger_grantee (
    uuid BLOB PRIMARY KEY
) STRICT;

INSERT INTO ledger_grantee(uuid)
SELECT uuid FROM user_account_v3;

CREATE TABLE user_account (
    uuid BLOB PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 50),
    normalized_name TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    password_changed_at INTEGER NOT NULL CHECK (password_changed_at >= created_at),

    FOREIGN KEY (uuid) REFERENCES ledger_grantee(uuid) ON DELETE CASCADE
) STRICT;

INSERT INTO user_account(uuid, name, normalized_name, password_hash, created_at, password_changed_at)
SELECT uuid, name, normalized_name, password_hash, created_at, password_changed_at
FROM user_account_v3;

CREATE TABLE external_access (
    uuid BLOB PRIMARY KEY,
    user_uuid BLOB NOT NULL,
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 50),
    token_hash BLOB NOT NULL UNIQUE CHECK (length(token_hash) = 32),

    FOREIGN KEY (uuid) REFERENCES ledger_grantee(uuid) ON DELETE CASCADE,
    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

CREATE TABLE ledger_grant (
    uuid BLOB PRIMARY KEY,
    grantee_uuid BLOB NOT NULL,
    ledger_uuid BLOB NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('OWNER', 'GUEST')),
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    revoked_at INTEGER CHECK (revoked_at IS NULL OR revoked_at >= created_at),

    FOREIGN KEY (grantee_uuid) REFERENCES ledger_grantee(uuid) ON DELETE CASCADE,
    FOREIGN KEY (ledger_uuid) REFERENCES ledger(uuid) ON DELETE CASCADE
) STRICT;

INSERT INTO ledger_grant(uuid, grantee_uuid, ledger_uuid, role, created_at, revoked_at)
SELECT uuid, user_uuid, ledger_uuid, role, created_at, revoked_at
FROM ledger_grant_v3;

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

INSERT INTO mfa_method
SELECT * FROM mfa_method_v3;

CREATE TABLE recovery_code (
    uuid BLOB PRIMARY KEY,
    user_uuid BLOB NOT NULL,
    code_hash BLOB NOT NULL UNIQUE,
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    expires_at INTEGER NOT NULL CHECK (expires_at > created_at),
    used_at INTEGER CHECK (used_at IS NULL OR (used_at >= created_at AND used_at < expires_at)),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

INSERT INTO recovery_code
SELECT * FROM recovery_code_v3;

CREATE TABLE user_preferences (
    user_uuid BLOB PRIMARY KEY,
    language TEXT NOT NULL,
    theme TEXT NOT NULL CHECK (theme IN ('LIGHT', 'DARK')),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

INSERT INTO user_preferences
SELECT * FROM user_preferences_v3;

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

INSERT INTO auth_session
SELECT * FROM auth_session_v3;

CREATE TABLE remember_session (
    uuid BLOB PRIMARY KEY,
    user_uuid BLOB NOT NULL,
    token_hash BLOB NOT NULL UNIQUE,
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    expires_at INTEGER NOT NULL CHECK (expires_at > created_at),
    last_used_at INTEGER CHECK (last_used_at IS NULL OR (last_used_at >= created_at AND last_used_at < expires_at)),

    FOREIGN KEY (user_uuid) REFERENCES user_account(uuid) ON DELETE CASCADE
) STRICT;

INSERT INTO remember_session
SELECT * FROM remember_session_v3;

DROP TABLE user_account_v3;
DROP TABLE ledger_grant_v3;
DROP TABLE mfa_method_v3;
DROP TABLE recovery_code_v3;
DROP TABLE user_preferences_v3;
DROP TABLE auth_session_v3;
DROP TABLE remember_session_v3;

CREATE UNIQUE INDEX ledger_grant_active_ledger_owner_idx ON ledger_grant(ledger_uuid) WHERE revoked_at IS NULL AND role = 'OWNER';
CREATE INDEX external_access_user_idx ON external_access(user_uuid);
CREATE INDEX ledger_grant_grantee_idx ON ledger_grant(grantee_uuid);
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
CREATE INDEX mfa_method_unconfirmed_idx ON mfa_method(expires_unconfirmed_at) WHERE confirmed_at IS NULL;
