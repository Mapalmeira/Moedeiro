# Reverse proxy and HTTPS

Moedeiro serves plain HTTP. When exposing Moedeiro outside the host, Uvicorn should listen on localhost or a private container network, while a reverse proxy provides the public HTTPS endpoint.

Because the TCP connection seen by Moedeiro may come from a reverse proxy, IP-based rate limits need the proxy to forward the original client address. Moedeiro accepts forwarded client information only from the address configured through the `TRUSTED_PROXY_IP` environment variable, which must match the source address that Moedeiro actually sees for connections from proxies.

For example, if a reverse proxy and Moedeiro run directly on the same host, Moedeiro sees the connection from Caddy as coming from `127.0.0.1`. In that case, set the environment variable in the environment used to start Moedeiro as `TRUSTED_PROXY_IP=127.0.0.1`.

Forwarded headers cannot be trusted from arbitrary peers because they are supplied by the requester. If Moedeiro accepted X-Forwarded-For from any connection, a client could provide a different address on each request and bypass IP-based rate limits. Restricting forwarded client information to one trusted proxy makes that proxy responsible for determining the client address before passing it to Moedeiro.

## Caddy configuration example

The following Caddy configuration terminates HTTPS, limits request bodies to 256 KiB, and forwards requests to Moedeiro listening on the same host:

```caddyfile
moedeiro.example.com {
    request_body {
        max_size 256KiB
    }

    reverse_proxy 127.0.0.1:8080
}
```

Caddy automatically provisions and renews the TLS certificate for the configured hostname. Its reverse proxy also supplies the forwarded client address and scheme required by Moedeiro.

## Podman pasta networking

Podman's rootless pasta networking can preserve the original source IP address when forwarding a connection from the host to the Moedeiro container. In such a setup, Moedeiro may already see the original client address directly as the network peer, even when the request passed through a reverse proxy on the host.

When this happens, TRUSTED_PROXY_IP can remain unset. Moedeiro uses the peer address provided by the connection and ignores forwarded headers.
