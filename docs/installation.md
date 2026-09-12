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

The key encrypts TOTP seeds stored in the registry. If the key is lost, the stored TOTP seeds can no longer be decrypted. In that case, an administrator must revoke the affected users' TOTP enrollments, after which those users may enroll TOTP again.

## Container installation

### Prepare persistent container storage

Choose a host directory for persistent registry and ledger data. The examples in this documentation use `/srv/moedeiro` but you may use a different host path.

```sh
mkdir -p /srv/moedeiro/registry
mkdir -p /srv/moedeiro/ledgers
```

### Container image

A prebuilt container image is available at `docker.io/mapalmeira/moedeiro:latest`. The Compose and Quadlet examples below use this image, so building it locally is not required.

If you prefer to build the image yourself using your container runtime of choice, you can do so from the repository root. First, install the locked frontend dependencies and build it:

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

Otherwise, with Podman:

```sh
podman build \
  --file Containerfile \
  --tag moedeiro:local \
  .
```

### Container engine

Moedeiro can be installed with either Docker Compose or Podman Quadlet. Choose one container runtime and follow the corresponding section below.

#### Docker Compose installation

1. Copy `compose.yaml` to the host where Moedeiro will run.
2. Ensure `TOTP_ENCRYPTION_KEY` is available in the environment.
3. Start Moedeiro:

```sh
docker compose up --detach
```

4. Check the container status:

```sh
docker compose ps moedeiro
```

#### Podman Quadlet installation

1. Ensure `TOTP_ENCRYPTION_KEY` is available in the environment.
2. Create a Podman secret directly from the `TOTP_ENCRYPTION_KEY` environment variable:

```sh
printf '%s' "$TOTP_ENCRYPTION_KEY" | podman secret create moedeiro_totp_encryption_key -
```

3. Create `~/.config/containers/systemd/moedeiro.container`:

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

4. Load the unit and start Moedeiro:

```sh
systemctl --user daemon-reload
systemctl --user start moedeiro
```

5. Check the service status:

```sh
systemctl --user status moedeiro
```

## Native installation

It is also possible to install Moedeiro natively. A native installation runs Moedeiro directly on the host. 

This installation method requires a Node.js version supported by Angular 22 and Python 3.10 or later.

1. Create a virtual environment and install the backend python package from the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --constraint ./backend/requirements.lock --editable ./backend
```

This installs the backend dependencies and the `moedeiro` command.

2. Install the frontend dependencies and build the frontend:

```sh
(cd frontend && npm ci && npm run build:production)
```

3. Ensure the TOTP encryption key is available as `TOTP_ENCRYPTION_KEY` in the process environment.

4. Start Moedeiro:

```sh
moedeiro start
```

5. The native default is `127.0.0.1:8000`. To select another address or port:

```sh
moedeiro start --host 127.0.0.1 --port 8080
```

## Application settings

Moedeiro provides built-in defaults for its optional settings. Any installation method can override them through environment variables when different behavior is required.

Configure environment variables according to the installation method:

* **Docker Compose:** under `environment` in `compose.yaml`.
* **Podman Quadlet:** with `Environment=` entries in the `[Container]` section of `moedeiro.container`.
* **Native installation:** export them in the environment before starting Moedeiro.

See [Environment settings](environment.md) for the available settings, their defaults, and their effects.

## Next steps

Use the [Command line interface](cli.md) for operator tasks such as creating invitations, managing users, and cleaning inactive records.

If Moedeiro will be exposed through an HTTPS reverse proxy, continue with [Reverse proxy](reverse-proxy.md).
