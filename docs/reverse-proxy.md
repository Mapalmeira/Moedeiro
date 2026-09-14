# Reverse proxy and HTTPS

Moedeiro serves plain HTTP. When exposing Moedeiro outside the host, a reverse proxy should provide the public HTTPS endpoint.

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