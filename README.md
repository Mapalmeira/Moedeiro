# Moedeiro

Moedeiro is a self-hosted application for keeping personal financial records. It manages accounts, currencies, categories, financial events, budgets, balances, and cash-flow queries. Access is private: users are created by invitation, authenticate with server-side sessions, and may protect their accounts with TOTP.

The service is deliberately small to operate. It runs as one FastAPI process and persists everything in SQLite. User accounts, sessions, preferences, and ledger ownership live in a registry database; every ledger has a separate database of its own. This separation keeps each financial dataset self-contained while the registry remains the authority that decides who may open it.

Start with [Installation](docs/installation.md). The remaining guides explain the operational decisions that matter after the service is running:

* [Environment variables](docs/environment.md) explains additional runtime configuration.
* [Reverse proxy](docs/reverse-proxy.md) explains HTTPS and trustworthy client addresses for rate limiting.
* [Administrative CLI](docs/cli.md) covers invitations, users, recovery, MFA, and maintenance.
* [Security and concurrency](docs/security.md) describes the protection model and why the service has separate resource limits.
* [Backups](docs/backups.md) describes the small set of files required for a complete recovery.

`GET /health` returns HTTP `204` while the service is available. FastAPI's interactive API reference is available from the running service at `/docs`.
