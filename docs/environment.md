# Optional environment variables

Moedeiro runs with conservative defaults. Change these values only when different behavior is required.

## Capacity and result limits

These values bound the work one process accepts at a time. Values were chosen from empiral tests. Higher values are not automatically better as they may increase resource pressure.

| Variable | Default | When to change it |
| --- | --- | --- |
| `SYNC_ROUTE_CONCURRENCY` | `40` | Limit concurrent synchronous work. |
| `CREDENTIAL_OPERATION_CONCURRENCY` | `8` | Limit concurrent login, registration, password, and TOTP operations. |
| `PASSWORD_HASH_CONCURRENCY` | `2` | Limit simultaneous Argon2 hashes and verifications. |
| `MAX_PAGE_SIZE` | `200` | Limit the largest accepted paginated response. |
| `MAX_QUERY_POINTS` | `500` | Limit the largest temporal series queried. |

[Security and concurrency](security.md) explains why request work, credential work, and password hashing are limited independently.

## Rate limits

These values use the `limits` rate syntax, such as `5/minute` or `5/hour`. They
apply independently so a burst of refresh attempts does not consume the login
budget, for example. Every value must have a positive amount.

| Variable | Default | Protects |
| --- | --- | --- |
| `REGISTRATION_IP_ATTEMPTS_RATE_LIMIT` | `5/hour` | Registration attempts from one client IP. |
| `LOGIN_IP_ATTEMPTS_RATE_LIMIT` | `5/minute` | Login attempts from one client IP. |
| `PASSWORD_RECOVERY_IP_ATTEMPTS_RATE_LIMIT` | `5/hour` | Password recovery attempts from one client IP. |
| `TOTP_SETUP_IP_ATTEMPTS_RATE_LIMIT` | `5/hour` | TOTP setup attempts from one client IP. |
| `REFRESH_IP_ATTEMPTS_RATE_LIMIT` | `10/minute` | Session refresh attempts from one client IP. |
| `AUTHENTICATED_USER_OPERATIONS_RATE_LIMIT` | `50/minute` | Requests made by one authenticated user. |

IP limits only work as intended when the service can distinguish the real client
from a reverse proxy. See [Reverse proxy](reverse-proxy.md) before changing
these values in a proxied installation.

## HTTP and proxy settings

These variables describe how Moedeiro is reached. The defaults are appropriate
when the service is bound to localhost or a private container network.

| Variable | Default | When to set it |
| --- | --- | --- |
| `TRUSTED_PROXY_IP` | unset | Set the exact IPv4 or IPv6 address of the reverse proxy that connects to Moedeiro. It then becomes the only peer allowed to provide forwarded client information. |
| `ALLOW_INSECURE_HTTP` | `false` | Set to `true` only for local HTTP when the client cannot retain secure cookies. Leave it false for a reverse proxy or any shared network. |

`ALLOW_INSECURE_HTTP` removes the `Secure` attribute from authentication cookies;
it does not add any protection to HTTP. It is usually unnecessary on
`localhost`. [Reverse proxy](reverse-proxy.md) explains how `TRUSTED_PROXY_IP`
keeps client-IP rate limits accurate.
