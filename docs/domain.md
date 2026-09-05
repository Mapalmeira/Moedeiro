# Domain model

## Registry

* **User** is an account that can authenticate. User names are unique after NFKC normalization, trimming, and case folding. A user has a password hash and creation/password-change timestamps.
* **Ledger** is a named financial dataset with its own SQLite database. The registry records its storage path, appearance, and most recent access time; it does not contain its financial records.
* **Ledger grant** links a user to a ledger. The current role is `OWNER`; grants can be revoked without deleting their history.
* **User preferences** hold optional presentation settings: language (`pt-BR` or `en`), date, time, and number formats, theme, and IANA timezone.
* **Auth session** is the server-side, short-lived authenticated session.
* **Remember session** is a separately stored, longer-lived token used to restore a session.
* **MFA method** represents a TOTP factor. Its secret is encrypted, and confirmation and last-used state are tracked.
* **Recovery code** is a one-time, expiring credential used to reset an account's password.
* **User invitation** is an expiring, single-use credential required to create a user.

## Ledger entities

* **Currency** defines how integer amounts are displayed: name, optional prefix/suffix, and decimal places. Amounts are always stored as integers in the currency's smallest configured unit; Moedeiro does not perform automatic currency conversion.
* **Account** is a place where money is held. It belongs to exactly one currency and has a unique name within the ledger. Its balance is derived from financial movements.
* **Category** classifies movements. Categories form a tree: a category may have one parent, with a maximum depth of five and up to 1,000 nodes. Queries selecting a category include its descendants.
* **Financial event** is an occurrence at `occurred_at`, with a description and one or more movements. It has one of three types:
  * `TRANSACTION` has one non-zero movement and represents a simple income (positive value) or expense (negative value).
  * `SHOPPING_LIST` has one or more negative movements from a single account, allowing a purchase to be itemized across categories. It supports up to 300 movements.
  * `ACCOUNT_TRANSFER` moves a negative amount from one account to a positive amount in another account; the accounts must differ. It may contain one additional negative fee movement on the destination account.
* **Financial movement** is the accounting entry within an event. It links one account and one category, and contains a non-zero signed `value`, a positive `quantity`, and an optional item name. Its economic impact is `value × quantity`.
* **Budget** sets a non-negative amount for a category, currency, and time period. It may optionally restrict spending to up to 50 accounts; those accounts must use the budget currency. Budget names are unique in a ledger.
