# Domain model

## Registry

* **User** is an account that can authenticate. User names contain only URI-safe ASCII characters and are unique using a normalized form produced with NFKC normalization, trimming, and case folding. A user has a password hash and creation/password-change timestamps.

* **Ledger** is a named financial dataset with its own SQLite database. The registry records its storage path, appearance, and most recent access time; it does not contain its financial records. A user may own up to 10 ledgers.

* **External access** is a named API identity created by a ledger owner to grant external applications access to that ledger. It is authenticated by a random token whose hash is stored in the registry.

* **Ledger grant** records access to a ledger with role `OWNER` or `GUEST`; grants can be revoked while retaining their history. A grantee can have at most one active grant for a ledger, and a ledger has at most one active owner. An owner must be a user. External accesses are granted ledger access with the `GUEST` role.

* **User preferences** hold the selected language (`pt-BR` or `en`) and theme (`LIGHT` or `DARK`).

* **Auth session** is the server-side, short-lived authenticated session.

* **Remember session** is a separately stored, longer-lived token used to create a new authenticated session. The token is rotated when used.

* **MFA method** represents a TOTP factor. Its secret is encrypted, and confirmation and last-used counter state are tracked.

* **Recovery code** is a one-time, expiring credential used to reset an account's password.

* **User invitation** is an expiring, single-use credential that authorizes user registration.

## Shared value objects

* **Color** represents an RGB color used to customize the appearance of ledgers and ledger entities.

* **Icon** represents an icon used to customize appearance. Its value is prefixed with its type: `lucide:IconName` for a Lucide icon or `unicode:...` for one to three Unicode characters. The complete value, including the prefix, must contain between 1 and 100 characters.

## Ledger entities

* **Currency** defines how integer amounts are displayed: name, optional prefix/suffix, and decimal places. Amounts are stored as integers in the currency's smallest configured unit; Moedeiro does not perform automatic currency conversion.

* **Account** is a place where money is held. It belongs to exactly one currency and has a unique name within the ledger. Its balance is derived from financial movements.

* **Category** classifies movements. Categories form a tree: a category may have one parent, with a maximum depth of five and up to 1,000 nodes. Financial-event and cash-flow filters over a category include its descendants, as do budget calculations for that category.

* **Financial event** is an occurrence at `occurred_at`, with a description and one or more movements. A ledger may contain up to 1,000,000 financial events. It has one of three types:

  * `TRANSACTION` has one non-zero main movement and represents a simple income (positive value) or expense (negative value). An expense may contain one additional negative fee movement on the same account, identified by special type `FEE`.
  * `SHOPPING_LIST` has one or more negative movements from a single account, allowing a purchase to be itemized across categories. It supports up to 300 movements.
  * `ACCOUNT_TRANSFER` has a negative movement from one account and a positive movement into another account; the accounts must differ. It may contain one additional negative fee movement on the destination account, identified by special type `FEE`.

* **Financial movement** is the accounting entry within an event. It links one account and one category, and contains a non-zero signed `value`, a positive `quantity`, an optional item name, and an optional `special_type`. Its economic impact is `value × quantity`.

* **Budget** sets a non-negative spending limit for exactly one account, one category, and a time period. The account determines the budget currency and cannot be changed after creation. Spending in descendant categories is included. Budget descriptions are optional. Budgets do not have their own icon or color; account and category appearance identify their scope. Budget names are unique within the ledger. A ledger may contain up to 1,000 budgets.
