# Installation

Moedeiro can run as a container or directly in a Python environment. Docker Compose and Podman Quadlet are the recommended installation methods.

Every installation has three persistent elements:

* the registry directory, which contains users and ledger ownership;
* the ledgers directory, which contains the financial data;
* the TOTP encryption key, which allows Moedeiro to read enrolled MFA secrets.

## Preparation

### 1. Generate the TOTP encryption key

Create a directory for the key and generate it:

```sh
mkdir -p /etc/moedeiro
openssl rand -base64 32 | tr '+/' '-_' > /etc/moedeiro/totp.key
chmod 600 /etc/moedeiro/totp.key
```

The key encrypts TOTP seeds stored in the registry. If the key is lost, the stored TOTP seeds can no longer be decrypted. An administrator must revoke the affected users' TOTP enrollments, after which those users may enroll TOTP again.

### 2. Prepare persistent container storage

Choose a host directory for persistent registry and ledger data. The examples in this documentation use `/srv/moedeiro`:

```sh
mkdir -p /srv/moedeiro/registry
mkdir -p /srv/moedeiro/ledgers
```

These directories are mounted into the container's `/data` paths and must remain available throughout Moedeiro's lifecycle.

You may use a different host path by changing the corresponding volume mounts in the container configuration.

## Container installation

Moedeiro can be installed with either Docker Compose or Podman Quadlet. Choose one container runtime and follow the corresponding section below.

### Container image

A pre-built image is available on Docker Hub as `mapalmeira/moedeiro`.

Build the image locally with your chosen container runtime if you wish.

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

Edit `compose.yaml` for the host where Moedeiro will run.

Set the image:

```yaml
image: mapalmeira/moedeiro:VERSION
```

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

Start Moedeiro while supplying the TOTP encryption key:

```sh
TOTP_ENCRYPTION_KEY="$(cat /etc/moedeiro/totp.key)" docker compose up --detach
```

Check the container status:

```sh
docker compose ps moedeiro
```

### Podman Quadlet installation

Quadlet runs Moedeiro as a systemd-managed Podman container.

Add the TOTP encryption key to Podman:

```sh
podman secret create moedeiro_totp_encryption_key /etc/moedeiro/totp.key
```

Create `~/.config/containers/systemd/moedeiro.container`:

```ini
[Unit]
Description=Moedeiro personal finance service

[Container]
ContainerName=moedeiro
Image=mapalmeira/moedeiro:VERSION
Volume=/srv/moedeiro/registry:/data/registry:Z
Volume=/srv/moedeiro/ledgers:/data/ledgers:Z
PublishPort=8080:8000
Secret=moedeiro_totp_encryption_key,type=env,target=TOTP_ENCRYPTION_KEY

[Service]
Restart=on-failure

[Install]
WantedBy=default.target
```

Set the image:

```ini
Image=mapalmeira/moedeiro:VERSION
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

A native installation runs Moedeiro directly on the host. Building the web interface requires Node.js 24 with npm 11, while the service itself requires Python 3.14 and the Python dependencies listed by the backend.

Create a virtual environment and install the backend requirements:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/app/requirements.txt
```

Install the locked frontend dependencies and create the production bundle:

```sh
(cd frontend && npm ci && npm run build:production)
```

The bundle is written to `frontend/dist/moedeiro/browser`. Rebuild it after changing the frontend before restarting the service.

Set the TOTP encryption key:

```sh
export TOTP_ENCRYPTION_KEY="$(cat /etc/moedeiro/totp.key)"
```

If a native installation should keep its databases outside the repository, override the storage paths. For example:

```sh
export REGISTRY_DB_PATH=/srv/moedeiro/registry/registry.sqlite
export LEDGER_DBS_DIR=/srv/moedeiro/ledgers
```

Start Uvicorn on the desired host address and port:

```sh
python -B -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

## Database migrations

Moedeiro checks the schema version of the registry and ledger databases when it starts. Supported older schemas are migrated automatically.

Before modifying a database, Moedeiro creates a backup of its current state in a `backups` directory alongside the persistent data. This provides a recovery point if a schema migration fails or an upgrade needs to be rolled back.

Databases created by a newer, incompatible version of Moedeiro are rejected during startup.

## Application settings

Moedeiro provides built-in defaults for its optional settings. Any installation method can override them through the environment when different behavior is required.

See [Environment settings](environment.md) for the available settings, their defaults, and their effects.

## Verify the installation and next steps

Request the health endpoint using the host address and port selected for the installation. For example:

```sh
curl --include http://127.0.0.1:8080/health
```

The expected response is HTTP `204`.

FastAPI's interactive API reference is available from the running service at `/docs`.

Moedeiro is then ready for the rest of the host networking configuration. See [Reverse proxy](reverse-proxy.md) for an HTTPS deployment through a reverse proxy.
