# Administrative CLI

Moedeiro provides an administrative CLI for operations that require operator access, such as issuing invitations, creating users directly, recovering accounts, revoking MFA, deleting users, and removing inactive records. The CLI operates on the same registry and ledger storage as the running service.

## Running the CLI

The `moedeiro-cli` command is included in the container image.

With Docker Compose:

```sh
docker compose exec moedeiro moedeiro-cli --help
```

With Podman:

```sh
podman exec moedeiro moedeiro-cli --help
```

For a native installation, activate the same Python environment and provide the same application settings used by the service:

```sh
source .venv/bin/activate

export REGISTRY_SCHEMA_PATH="$PWD/backend/app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
export LEDGER_SCHEMA_PATH="$PWD/backend/app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"
export REGISTRY_DB_PATH=/srv/moedeiro/registry/registry.sqlite
export LEDGER_DBS_DIR=/srv/moedeiro/ledgers
export TOTP_ENCRYPTION_KEY="$(cat /etc/moedeiro/totp.key)"

python -m app.cli --help
```

## Inviting users

User registration requires an invitation issued by an operator:

```text
moedeiro-cli invitation create [--expiration-seconds SECONDS]
moedeiro-cli invitation list
moedeiro-cli invitation revoke UUID
```

`invitation create` prints a one-time invitation code that can be sent to the intended user. Invitations expire after one hour by default and can be consumed once. A different lifetime can be specified with `--expiration-seconds`.

`invitation list` shows each invitation's UUID, state, creation time, and expiration time. The state is reported as `ACTIVE`, `EXPIRED`, or `CONSUMED`.

`invitation revoke` removes an available invitation identified by its UUID.

Treat invitation codes as temporary credentials and share them through an appropriate private channel.

## Managing users

Administrative user operations are available under `moedeiro-cli user`:

```text
moedeiro-cli user create NAME
moedeiro-cli user list
moedeiro-cli user recover-password UUID [--expiration-seconds SECONDS]
moedeiro-cli user disable-mfa UUID
moedeiro-cli user delete UUID
```

`user create` creates an account directly and prompts for the password and its confirmation without placing the password on the command line.

`user list` shows the UUID, name, and creation time of each user.

`user recover-password` prints a one-time recovery code for the selected user. Recovery codes expire after one hour by default, and a different lifetime can be specified with `--expiration-seconds`. Issuing a new recovery code replaces any active recovery code previously issued for that user.

`user disable-mfa` removes all MFA methods configured for the user and invalidates all active and remembered sessions. It is intended for account recovery when a user no longer has access to an enrolled authenticator. Existing recovery codes are preserved.

`user delete` permanently deletes the user and the database files for ledgers currently owned by that user. Related registry records, including sessions, remembered sessions, MFA methods, recovery codes, preferences, and ledger grants, are removed with the account.

## Removing inactive records

Inactive registry records can be removed with:

```text
moedeiro-cli cleanup --days DAYS
```

The retention period determines how long inactive records remain in the registry. For example:

```sh
moedeiro-cli cleanup --days 30
```

removes records that have been inactive for at least 30 days.

Cleanup applies to expired or inactive authentication sessions, remembered sessions, consumed or expired invitations, used or expired recovery codes, revoked ledger grants, and unconfirmed MFA enrollments.

A retention period of `0` removes records that are inactive when the command runs.