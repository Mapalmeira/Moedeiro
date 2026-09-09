# Installation

Moedeiro can run as a container or directly in a Python environment. Docker Compose and Podman Quadlet are the recommended installation methods.

Every installation has three persistent elements:

* the registry directory, which contains users and ledger ownership;
* the ledgers directory, which contains the financial data;
* the TOTP encryption key, which allows Moedeiro to read enrolled MFA secrets.

## Preparation

### Generate the TOTP encryption key

Generate a key once:

```sh
export TOTP_ENCRYPTION_KEY="$(openssl rand -base64 32 | tr '+/' '-_')"
```

Store the generated value in your chosen secret store before closing the shell. It can be a password manager, a platform secret manager, a systemd credential, a protected environment file, or a Podman secret. The same value must be supplied as `TOTP_ENCRYPTION_KEY` whenever the service starts.

The key encrypts TOTP seeds stored in the registry. If the key is lost, the stored TOTP seeds can no longer be decrypted. An administrator must revoke the affected users' TOTP enrollments, after which those users may enroll TOTP again. Do not put the key in the image, the registry database, or source control.

## Container installation

Moedeiro can be installed with either Docker Compose or Podman Quadlet. Choose one container runtime and follow the corresponding section below.

### Prepare persistent container storage

Choose a host directory for persistent registry and ledger data. The examples in this documentation use `/srv/moedeiro`:

```sh
mkdir -p /srv/moedeiro/registry
mkdir -p /srv/moedeiro/ledgers
```

These directories are mounted into the container's `/data` paths and must remain available throughout Moedeiro's lifecycle.

You may use a different host path by changing the corresponding volume mounts in the container configuration.

### Container image

The published image is `docker.io/mapalmeira/moedeiro:latest`. Both the Compose and Quadlet examples below use it, so a local image build is not required.

But you may build the image locally with your chosen container runtime if you wish. From the repository's root, first install the locked frontend dependencies and create the production bundle:

```sh
(cd frontend && npm ci && npm run build:production)
```

Then build the image for your local architecture:

With Docker:

```sh
docker build \
  --file Containerfile \
  --tag moedeiro:local \
  .
```

With Podman:

```sh
podman build \
  --file Containerfile \
  --tag moedeiro:local \
  .
```

### Docker Compose installation

Copy `compose.yaml` to the host where Moedeiro will run.

Set the host port:

```yaml
ports:
  - "8080:8000"
```

A host address can also be specified:

```yaml
ports:
  - "127.0.0.1:8080:8000"
```

Ensure `TOTP_ENCRYPTION_KEY` is available in the environment from your chosen secret store, then start Moedeiro:

```sh
docker compose up --detach
```

Check the container status:

```sh
docker compose ps moedeiro
```

### Podman Quadlet installation

Quadlet runs Moedeiro as a systemd-managed Podman container.

Create a Podman secret directly from the environment variable:

```sh
printf '%s' "$TOTP_ENCRYPTION_KEY" | podman secret create moedeiro_totp_encryption_key -
```

Create `~/.config/containers/systemd/moedeiro.container`:

```ini
[Unit]
Description=Moedeiro personal finance service

[Container]
ContainerName=moedeiro
Image=docker.io/mapalmeira/moedeiro:latest
Volume=/srv/moedeiro/registry:/data/registry:Z
Volume=/srv/moedeiro/ledgers:/data/ledgers:Z
PublishPort=8080:8000
Secret=moedeiro_totp_encryption_key,type=env,target=TOTP_ENCRYPTION_KEY

[Service]
Restart=on-failure

[Install]
WantedBy=default.target
```

Set the host port:

```ini
PublishPort=8080:8000
```

A host address can also be specified:

```ini
PublishPort=127.0.0.1:8080:8000
```

Load the unit and start Moedeiro:

```sh
systemctl --user daemon-reload
systemctl --user start moedeiro
```

Check the service status:

```sh
systemctl --user status moedeiro
```

## Native installation

A native installation runs Moedeiro directly on the host. Building the web interface requires Node.js 24 with npm 11, while the service itself requires Python 3.14.

Create a virtual environment and install the backend package in editable mode from the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --constraint ./backend/requirements.lock --editable ./backend
```

This installs the backend dependencies and the `moedeiro` command while keeping the installed package linked to the repository checkout. The native storage and frontend defaults therefore resolve against the standard repository layout.

Install the locked frontend dependencies and create the production bundle:

```sh
(cd frontend && npm ci && npm run build:production)
```

The bundle is written to `frontend/dist/moedeiro/browser`.

Ensure the TOTP encryption key is available as `TOTP_ENCRYPTION_KEY` in the process environment, loading it from your chosen secret store.

Start Moedeiro:

```sh
moedeiro start
```

The service remains attached to the current process. The native default is `127.0.0.1:8000`. To select another address or port:

```sh
moedeiro start --host 127.0.0.1 --port 8080
```

## Database migrations

Moedeiro checks the schema version of the registry and ledger databases when it starts. Supported older schemas are migrated automatically.

Before modifying a database, Moedeiro creates a backup of its current state in a `backups` directory alongside the persistent data. This provides a recovery point if a schema migration fails or an upgrade needs to be rolled back.

Databases created by a newer, incompatible version of Moedeiro are rejected during startup.

## Application settings

Moedeiro provides built-in defaults for its optional settings. Any installation method can override them through environment variables when different behavior is required.

Configure environment variables according to the installation method:

* **Docker Compose:** under `environment` in `compose.yaml`.
* **Podman Quadlet:** with `Environment=` entries in the `[Container]` section of `moedeiro.container`.
* **Native installation:** export them in the environment before starting Moedeiro.

See [Environment settings](environment.md) for the available settings, their defaults, and their effects.

## Next steps

Use the [Command line interface](cli.md) for operator tasks such as creating invitations, managing users, and cleaning inactive records.

FastAPI's interactive API reference is available from the running service at `/docs`.

If Moedeiro will be exposed through an HTTPS reverse proxy, continue with [Reverse proxy](reverse-proxy.md).

## Backend dependency updates and tests

Direct dependency versions in `backend/pyproject.toml` were checked against
[PyPI](https://pypi.org/) on 2026-09-05. `backend/requirements.lock` also pins
transitive dependencies and the optional HTTP test client.

To install the test dependencies and run the backend suite from the repository root:

```sh
python -m pip install --constraint ./backend/requirements.lock --editable './backend[test]'
(cd backend && python -m unittest discover -s tests)
```

To refresh the lock after updating the exact versions in `pyproject.toml`:

```sh
(cd backend && uv pip compile --upgrade --universal --extra test pyproject.toml --output-file requirements.lock)
```

Review the resolved versions and rerun the backend suite before committing an update.
