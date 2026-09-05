# Installation

Moedeiro can run as a container or directly in a Python environment. Docker Compose and Podman Quadlet are the recommended installation methods.

Every installation has three persistent elements:

* the registry directory, which contains users and ledger ownership;
* the ledgers directory, which contains the financial data;
* the TOTP encryption key, which allows Moedeiro to read enrolled MFA secrets.

## Preparation

### 1. Create the data directories

Create directories for the registry and ledger data:

```sh
mkdir -p /srv/moedeiro/registry
mkdir -p /srv/moedeiro/ledgers
```

These directories hold the persistent application data and must remain available despite Moedeiro's lifecycle.

### 2. Generate the TOTP encryption key

Create a directory for the key and generate it:

```sh
mkdir -p /etc/moedeiro
openssl rand -base64 32 | tr '+/' '-_' > /etc/moedeiro/totp.key
chmod 600 /etc/moedeiro/totp.key
```

The key encrypts TOTP seeds stored in the registry. If the key is lost, the stored TOTP seeds can no longer be decrypted. An administrator must revoke the affected users' TOTP enrollments, after which those users may enroll TOTP again.

## Container installation

Moedeiro container can be installed with either Docker Compose or Podman Quadlet. Choose one container runtime for the installation and follow only the corresponding section below.

### Container image

A pre-built image is available on Docker Hub as `mapalmeira/moedeiro`.

Build the image locally with Docker or Podman if you wish:

```sh
docker build \
  --file backend/app/Containerfile \
  --tag moedeiro:local \
  .
```

```sh
podman build \
  --file backend/app/Containerfile \
  --tag moedeiro:local \
  .
```

### Docker Compose Installation

Edit `compose.yaml` for the host where Moedeiro will run.

Set the image:

```yaml
image: mapalmeira/moedeiro:VERSION
```

Set the host port and/or host address:

```yaml
ports:
  - "8080:8000"
```

```yaml
ports:
  - "127.0.0.1:8080:8000"
```

Start Moedeiro while supplying the TOTP encryption key:

```sh
TOTP_ENCRYPTION_KEY="$(cat /etc/moedeiro/totp.key)" docker compose up --detach
```

Check the container status with:

```sh
docker compose ps moedeiro
```

### Podman Quadlet Installation

Quadlet runs Moedeiro as a systemd-managed Podman container.

First, add the TOTP encryption key to Podman:

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

Set the host port and/or host address:

```ini
PublishPort=127.0.0.1:8080:8000
```

Load the unit and start Moedeiro:

```sh
systemctl --user daemon-reload
systemctl --user start moedeiro
```

Check the service status with:

```sh
systemctl --user status moedeiro.service
```

## Native installation

A native installation runs Moedeiro directly in a Python environment. The host provides Python dependencies and process supervision.

Create a virtual environment and install the requirements:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/app/requirements.txt
```

Set the application environment:

```sh
export PYTHONPATH="$PWD/backend"

export REGISTRY_SCHEMA_PATH="$PWD/backend/app/infrastructure/persistence/sqlite/registry/schema/registry_schema.sql"
export LEDGER_SCHEMA_PATH="$PWD/backend/app/infrastructure/persistence/sqlite/ledger/schema/ledger_schema.sql"

export REGISTRY_DB_PATH=/srv/moedeiro/registry/registry.sqlite
export LEDGER_DBS_DIR=/srv/moedeiro/ledgers

export TOTP_ENCRYPTION_KEY="$(cat /etc/moedeiro/totp.key)"
```

Start Uvicorn on the desired host address and port:

```sh
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Application settings

Moedeiro provides built-in defaults for its optional settings. Any installation method can override them through the environment when different behavior is required.

See [Environment settings](environment.md) for the available settings, their defaults, and their effects.

## Verify the installation and next steps

Request the health endpoint using the host address and port selected for the installation:

```sh
curl --include http://127.0.0.1:8080/health
```

The expected response is HTTP `204`.

Moedeiro is then ready for the rest of the host networking configuration. See [Reverse proxy](reverse-proxy.md) for an HTTPS deployment through a reverse proxy.
