# Domain model

## Registry

* **User** is an account that can authenticate. User names contain only URI-safe ASCII characters and are unique using a normalized form produced with NFKC normalization, trimming, and case folding. A user has a password hash and creation/password-change timestamps.

* **Ledger** is a named financial dataset with its own SQLite database. The registry records its storage path, appearance, and most recent access time; it does not contain its financial records.

* **Ledger grant** links a user to a ledger. The current role is `OWNER`; grants can be revoked while retaining their history.

* **User preferences** hold optional presentation settings: language (`pt-BR` or `en`), date, time, and number formats, theme, and IANA timezone.

* **Auth session** is the server-side, short-lived authenticated session.

* **Remember session** is a separately stored, longer-lived token used to create a new authenticated session. The token is rotated when used.

* **MFA method** represents a TOTP factor. Its secret is encrypted, and confirmation and last-used counter state are tracked.

* **Recovery code** is a one-time, expiring credential used to reset an account's password.

* **User invitation** is an expiring, single-use credential that authorizes user registration.

## Ledger entities

* **Currency** defines how integer amounts are displayed: name, optional prefix/suffix, and decimal places. Amounts are stored as integers in the currency's smallest configured unit; Moedeiro does not perform automatic currency conversion.

* **Account** is a place where money is held. It belongs to exactly one currency and has a unique name within the ledger. Its balance is derived from financial movements.

* **Category** classifies movements. Categories form a tree: a category may have one parent, with a maximum depth of five and up to 1,000 nodes. Financial-event and cash-flow filters over a category include its descendants, as do budget calculations for that category.

* **Financial event** is an occurrence at `occurred_at`, with a description and one or more movements. It has one of three types:

  * `TRANSACTION` has one non-zero movement and represents a simple income (positive value) or expense (negative value).
  * `SHOPPING_LIST` has one or more negative movements from a single account, allowing a purchase to be itemized across categories. It supports up to 300 movements.
  * `ACCOUNT_TRANSFER` has a negative movement from one account and a positive movement into another account; the accounts must differ. It may contain one additional negative fee movement on the destination account.

* **Financial movement** is the accounting entry within an event. It links one account and one category, and contains a non-zero signed `value`, a positive `quantity`, and an optional item name. Its economic impact is `value × quantity`.

* **Budget** sets a non-negative amount for a category, currency, and time period. Spending in descendant categories is included. A budget may optionally restrict spending to up to 50 accounts, all of which must use the budget currency. Budget names are unique within the ledger.
