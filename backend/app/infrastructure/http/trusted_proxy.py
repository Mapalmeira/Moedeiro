from ipaddress import IPv4Address, IPv6Address


class TrustedProxyMiddleware:
    def __init__(self, app, trusted_proxy_ip: IPv4Address | IPv6Address | None):
        self.app = app
        self.trusted_proxy_ip = trusted_proxy_ip

    async def __call__(self, scope, receive, send) -> None:
        if self.trusted_proxy_ip is not None and scope["type"] == "http":
            client = scope.get("client")
            if client is not None and client[0] == str(self.trusted_proxy_ip):
                headers = dict(scope["headers"])
                forwarded_for = headers.get(b"x-forwarded-for")
                if forwarded_for is not None and b"," not in forwarded_for:
                    scope["client"] = (forwarded_for.decode("ascii"), client[1])
                forwarded_proto = headers.get(b"x-forwarded-proto")
                if forwarded_proto in (b"http", b"https"):
                    scope["scheme"] = forwarded_proto.decode("ascii")
        await self.app(scope, receive, send)
