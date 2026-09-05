# Environment variables

Moedeiro provides built-in defaults for most settings. Environment variables are overrides for installations that use different storage locations, container paths, concurrency limits, request rate limits, query limits, proxy handling, or HTTP behavior.

## Storage and frontend paths


| Variable               | Native default                                                                  | When to set it                                      |
| ---------------------- | ------------------------------------------------------------------------------- | --------------------------------------------------- |
| `REGISTRY_SCHEMA_PATH` | `<project>/backend/app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql` | Only when the registry schema is installed elsewhere. |
| `LEDGER_SCHEMA_PATH`   | `<project>/backend/app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql`     | Only when the ledger schema is installed elsewhere.   |
| `REGISTRY_DB_PATH`     | `<project>/data/registry/registry.sqlite`                                        | To store the registry database somewhere else.     |
| `LEDGER_DBS_DIR`       | `<project>/data/ledgers`                                                        | To store ledger databases somewhere else.          |
| `FRONTEND_DIST_PATH`   | `<project>/frontend/dist/moedeiro/browser`                                      | Only when the built frontend is installed elsewhere. |

A native installation from the repository does not need to set any of these variables when it uses the standard layout. The container image intentionally overrides these paths to match its filesystem layout:

| Variable               | Container value                                                                 |
| ---------------------- | ------------------------------------------------------------------------------- |
| `REGISTRY_SCHEMA_PATH` | `/app/backend/app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql` |
| `LEDGER_SCHEMA_PATH`   | `/app/backend/app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql`     |
| `REGISTRY_DB_PATH`     | `/data/registry/registry.sqlite`                                                |
| `LEDGER_DBS_DIR`       | `/data/ledgers`                                                                |
| `FRONTEND_DIST_PATH`   | `/app/frontend`                                                                |

## Security

| Variable              | Default | Purpose                                                                 |
| --------------------- | ------- | ----------------------------------------------------------------------- |
| `TOTP_ENCRYPTION_KEY` | unset   | Fernet-compatible key used to encrypt and decrypt enrolled TOTP secrets. |

`TOTP_ENCRYPTION_KEY` is required for normal service operation and intentionally has no generated or built-in default. Key generation and storage are covered in [Installation](installation.md).

## Concurrency limits

These values bound the amount of work one process accepts at a time. The defaults were chosen from empirical tests. Higher values may increase resource pressure.

| Variable                           | Default | When to change it                                                    |
| ---------------------------------- | ------- | -------------------------------------------------------------------- |
| `SYNC_ROUTE_CONCURRENCY`           | `40`    | Limit concurrent synchronous work.                                   |
| `CREDENTIAL_OPERATION_CONCURRENCY` | `8`     | Limit concurrent login, registration, password, and TOTP operations. |
| `PASSWORD_HASH_CONCURRENCY`        | `2`     | Limit simultaneous Argon2 hashes and verifications.                  |

[Security and concurrency](security.md) explains why request work, credential work, and password hashing are limited independently.

## Query limits

These values limit the size of data queries and responses.

| Variable           | Default | When to change it                              |
| ------------------ | ------- | ---------------------------------------------- |
| `MAX_PAGE_SIZE`    | `200`   | Limit the largest accepted paginated response. |
| `MAX_QUERY_POINTS` | `500`   | Limit the largest temporal series queried.     |

## Rate limits

These values use the `limits` rate syntax, such as `5/minute` or `5/hour`. Each limit applies independently, so activity against one operation does not consume the budget of another.

| Variable                                   | Default     | Protects                                       |
| ------------------------------------------ | ----------- | ---------------------------------------------- |
| `REGISTRATION_IP_ATTEMPTS_RATE_LIMIT`      | `5/hour`    | Registration attempts from one client IP.      |
| `LOGIN_IP_ATTEMPTS_RATE_LIMIT`             | `5/minute`  | Login attempts from one client IP.             |
| `PASSWORD_RECOVERY_IP_ATTEMPTS_RATE_LIMIT` | `5/hour`    | Password recovery attempts from one client IP. |
| `TOTP_SETUP_IP_ATTEMPTS_RATE_LIMIT`        | `5/hour`    | TOTP setup attempts from one client IP.        |
| `REFRESH_IP_ATTEMPTS_RATE_LIMIT`           | `10/minute` | Session refresh attempts from one client IP.   |
| `AUTHENTICATED_USER_OPERATIONS_RATE_LIMIT` | `50/minute` | Requests made by one authenticated user.       |

IP-based limits depend on Moedeiro receiving the real client address. See [Reverse proxy](reverse-proxy.md) for proxied installations.

## HTTP and proxy settings

These variables describe how Moedeiro is reached.

| Variable              | Default | When to set it                                                                                                                                         |
| --------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `TRUSTED_PROXY_IP`    | unset   | Set this to the exact IPv4 or IPv6 address of the reverse proxy when the proxy connects directly to Moedeiro and forwards the original client address. |
| `ALLOW_INSECURE_HTTP` | `false` | Set to `true` when Moedeiro is accessed over HTTP and authentication cookies must work without the `Secure` attribute.                                 |

When `TRUSTED_PROXY_IP` is set, Moedeiro accepts forwarded client information only from that address. This allows client-IP rate limits to use the original client address instead of the proxy address.

Leave `TRUSTED_PROXY_IP` unset when clients connect directly to Moedeiro or when the original client address is already visible from within the container, such as with Podman's `pasta` networking.

`ALLOW_INSECURE_HTTP` removes the `Secure` attribute from authentication cookies.

See [Reverse proxy](reverse-proxy.md) for proxied installations.
