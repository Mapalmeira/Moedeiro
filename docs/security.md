# Security and concurrency

## Credentials and sessions

Passwords are stored as Argon2 hashes. Argon2 is intentionally costly so that a stolen hash is expensive to guess. Successful login creates an opaque random session token. SQLite stores only its hash, while the browser receives the token in a cookie that is `Secure` by default. A normal session expires after 12 hours and also becomes invalid after 30 minutes without activity. A remembered login may last 30 days, and its token is rotated when used to refresh a session.

TOTP is an optional second factor. When enabled for a user, a valid TOTP code is required to log in, change the password, recover the password, and disable TOTP. Its seed must remain available to the server so that submitted codes can be verified, which is why it is encrypted rather than hashed. The encryption key is kept outside SQLite. Verification accepts the adjacent time window for clock tolerance and records the last accepted counter so the same code cannot be replayed.

Users can disable TOTP by confirming their current password and a valid TOTP code. An administrator can also revoke a user's MFA enrollment through the administrative CLI when the user no longer has access to the authenticator. Administrative revocation also invalidates that user's active and remembered sessions.

Registration requires a one-time invitation. Password recovery likewise uses a time-limited, one-time code created by an operator. For users with TOTP enabled, password recovery also requires a valid TOTP code. A successful password recovery invalidates all active and remembered sessions for the user.

Authentication responses avoid distinguishing a missing user from an invalid password, recovery code, or TOTP code, reducing the information exposed to account-enumeration attempts. Password hashing is also performed for missing users so that invalid-user and invalid-password paths incur similar computational cost, reducing timing differences that could reveal whether an account exists.

## Rate limiting

Rate limits slow repeated attempts before password hashing becomes the only line of defense. Registration, login, password recovery, TOTP setup, and session refresh have separate limits keyed by effective client IP. Once authenticated, requests share another limit keyed by the user UUID. Exceeding a limit returns HTTP `429` and a `Retry-After` header.

The limiter lives in process memory. Its counters disappear when the service restarts and are not shared with another worker or replica. This is sufficient for the current single-process self-hosted deployment and preserves simplicity.

IP-based limits effectiveness depends on seeing the real client rather than the proxy. Configure that boundary as described in [Reverse proxy](reverse-proxy.md); an incorrect setup can group all users under the proxy IP, allowing an attacker to exhaust the shared rate limit and block legitimate users from authentication and recovery operations.

## Concurrency limits

Most API handlers are synchronous because SQLite work is synchronous. FastAPI runs them in AnyIO's shared thread pool, and `SYNC_ROUTE_CONCURRENCY` controls how many may run at once. Its default of 40 leaves enough room for ordinary ledger operations.

Credential workflows use a separate executor. Login, registration, password changes, recovery, and TOTP setup can invoke expensive cryptography, so `CREDENTIAL_OPERATION_CONCURRENCY` limits them to 8 concurrent workers by default. Keeping credential work in a separate pool also isolates public authentication traffic from ordinary application work. A burst or attack against login and recovery endpoints can saturate the credential pool without consuming the threads used by authenticated users for ledger operations.

Inside those workflows, `PASSWORD_HASH_CONCURRENCY` places a tighter limit of 2 on simultaneous Argon2 hashes or verifications. This specifically protects CPU and memory from the most expensive credential operation. In empirical testing, a limit of 2 provided the best tradeoff, sustaining the highest request throughput before CPU usage began to increase disproportionately.
