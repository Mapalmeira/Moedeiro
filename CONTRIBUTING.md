# Contributing to Moedeiro

Thank you for helping improve Moedeiro. Bug fixes, tests, documentation, accessibility improvements, performance work, and translations are all welcome.

## Before you start

Every pull request must be associated with an issue. Open the issue before starting the change so its motivation, scope, and proposed approach can be discussed and recorded. Reference the issue in the pull request description when the pull request resolves it.

## Development setup

Moedeiro has an Angular frontend and a Python backend. The supported tool versions are defined in [`frontend/package.json`](frontend/package.json) and [`backend/pyproject.toml`](backend/pyproject.toml).

### 1. Frontend

Install the locked dependencies and start the development server:

```sh
cd frontend
npm ci
npm start
```

### 2. Backend

From the repository root, create a virtual environment and install the backend with its dependencies:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --constraint ./backend/requirements.lock --editable './backend[test]'
```

### Running the complete application locally

1. See the [installation guide](docs/installation.md) for the TOTP key and storage configuration.

2. Start the backend without requiring a compiled frontend:

```sh
moedeiro start --api-only
```

3. Keep it running in one terminal, run `npm start` from `frontend` in another, and open `http://127.0.0.1:4200`.


## Testing changes

### Frontend tests

Frontend tests use Vitest through Angular's test runner and live beside the source as `*.spec.ts` files.

Run the complete frontend suite:

```sh
cd frontend
npm test
```

### Backend tests

Backend tests use Python's built-in `unittest` runner and are split into unit and integration tests.

Run the complete backend suite:

```sh
cd backend
python -m unittest discover -s tests
```

## Help translate Moedeiro

Contributions that make Moedeiro available in more languages are especially welcome. Native speakers can improve existing wording or add a complete new language.

The current frontend languages are defined in [`frontend/src/app/core/i18n/i18n.service.ts`](frontend/src/app/core/i18n/i18n.service.ts). To add a language:

1. Add its locale to `AppLanguage` and create a dictionary containing every `TranslationKey`.
2. Add the language name and option to [`frontend/src/app/shared/ui/language-selector.component.ts`](frontend/src/app/shared/ui/language-selector.component.ts).
3. If the language selector uses a flag, add its type and asset mapping in [`frontend/src/app/shared/ui/twemoji-flag.component.ts`](frontend/src/app/shared/ui/twemoji-flag.component.ts), then expose the corresponding Twemoji SVG in [`frontend/angular.json`](frontend/angular.json). Remember that a language is not always represented by a single country; use a clear alternative when a flag would be misleading.
4. Inspect the entire frontend with the new language selected. Check both desktop and mobile widths for missing translations and truncated text.

Language preferences and the labels preloaded into new ledgers are also validated by the backend. Update these files as part of a complete translation:

- [`backend/app/domain/registry/model/user_preferences.py`](backend/app/domain/registry/model/user_preferences.py) for the accepted language value.
- [`backend/app/infrastructure/persistence/sqlite/ledger/default_labels.py`](backend/app/infrastructure/persistence/sqlite/ledger/default_labels.py) for category and currency labels.
- Select the new language in the account preferences, create a new ledger, and confirm that all seeded objects have the correct translated labels.

If you would like to help with a language but cannot complete every layer at once, open an issue or a draft pull request. That makes it easier for other speakers to review terminology and finish the remaining coverage together.
