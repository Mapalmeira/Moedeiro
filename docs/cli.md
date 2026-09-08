# Command line interface

Installing the backend provides one `moedeiro` command. It controls the native service and also exposes operator-only administrative operations against the same registry and ledger storage.

## Running the command

For a native installation, activate the virtual environment first:

```sh
source .venv/bin/activate
moedeiro --help
```

Because the backend is installed as a Python package, `moedeiro` can be run from the repository root or any other working directory.

Inside a Docker Compose deployment:

```sh
docker compose exec moedeiro moedeiro --help
```

With Podman:

```sh
podman exec moedeiro moedeiro --help
```

If a native installation intentionally overrides `REGISTRY_DB_PATH` or `LEDGER_DBS_DIR`, those overrides must also be present when running administrative subcommands so that they operate on the same databases as the service.

## Inviting users

User registration requires an invitation issued by an operator:

```text
moedeiro invitation create [--expiration-seconds SECONDS]
moedeiro invitation list
moedeiro invitation revoke UUID
```

`invitation create` prints a one-time invitation code that can be sent to the intended user. Invitations expire after one hour by default and can be consumed once. A different lifetime can be specified with `--expiration-seconds`.

`invitation list` shows each invitation's UUID, state, creation time, and expiration time. The state is reported as `ACTIVE`, `EXPIRED`, or `CONSUMED`.

`invitation revoke` removes an available invitation identified by its UUID.

Treat invitation codes as temporary credentials and share them through an appropriate private channel.

## Managing users

Administrative user operations are available under `moedeiro user`:

```text
moedeiro user create NAME
moedeiro user list
moedeiro user recover-password UUID [--expiration-seconds SECONDS]
moedeiro user disable-mfa UUID
moedeiro user delete UUID
```

`user create` creates an account directly and prompts for the password and its confirmation without placing the password on the command line.

`user list` shows the UUID, name, and creation time of each user.

`user recover-password` prints a one-time recovery code for the selected user. Recovery codes expire after one hour by default, and a different lifetime can be specified with `--expiration-seconds`. Issuing a new recovery code replaces any active recovery code previously issued for that user.

`user disable-mfa` removes all MFA methods configured for the user and invalidates all active and remembered sessions. It is intended for account recovery when a user no longer has access to an enrolled authenticator. Existing recovery codes are preserved.

`user delete` permanently deletes the user and the database files for ledgers currently owned by that user. Related registry records, including sessions, remembered sessions, MFA methods, recovery codes, preferences, and ledger grants, are removed with the account.

## Managing ledger grants

Administrative ledger-grant operations are available under `moedeiro grant`:

```text
moedeiro grant list [USER_UUID] [LEDGER_UUID]
moedeiro grant set-owner USER_UUID LEDGER_UUID
moedeiro grant revoke GRANT_UUID
```

`grant list` shows each grant's UUID, user UUID, ledger UUID, role, creation time, and revocation time. Supply a user UUID, and optionally a ledger UUID, to filter the result.

`grant set-owner USER_UUID LEDGER_UUID` transfers ownership of an existing ledger to the selected user. The prior owner's grant is revoked, so a ledger never has more than one active owner. The selected user can own at most 10 ledgers.

`grant revoke GRANT_UUID` revokes an active grant.

## Removing inactive records

Inactive registry records can be removed with:

```text
moedeiro cleanup --days DAYS
```

For example:

```sh
moedeiro cleanup --days 30
```

removes records that have been inactive for at least 30 days.

Cleanup applies to expired or inactive authentication sessions, remembered sessions, consumed or expired invitations, used or expired recovery codes, revoked ledger grants, and unconfirmed MFA enrollments.

A retention period of `0` removes records that are inactive when the command runs.
