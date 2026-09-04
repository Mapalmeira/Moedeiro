import asyncio
from ipaddress import IPv4Address
import unittest

from app.infrastructure.http.trusted_proxy import TrustedProxyMiddleware


class TrustedProxyMiddlewareTest(unittest.TestCase):
    def test_uses_forwarded_headers_only_from_the_configured_proxy(self) -> None:
        received_scope = {}

        async def application(scope, receive, send) -> None:
            received_scope.update(scope)

        scope = {
            "type": "http",
            "client": ("192.0.2.10", 8000),
            "scheme": "http",
            "headers": [(b"x-forwarded-for", b"203.0.113.2"), (b"x-forwarded-proto", b"https")],
        }

        asyncio.run(TrustedProxyMiddleware(application, IPv4Address("192.0.2.10"))(scope, None, None))

        self.assertEqual(received_scope["client"], ("203.0.113.2", 8000))
        self.assertEqual(received_scope["scheme"], "https")

    def test_does_not_interpret_a_forwarded_for_chain(self) -> None:
        received_scope = {}

        async def application(scope, receive, send) -> None:
            received_scope.update(scope)

        scope = {
            "type": "http",
            "client": ("192.0.2.10", 8000),
            "scheme": "http",
            "headers": [(b"x-forwarded-for", b"198.51.100.8, 203.0.113.2")],
        }

        asyncio.run(TrustedProxyMiddleware(application, IPv4Address("192.0.2.10"))(scope, None, None))

        self.assertEqual(received_scope["client"], ("192.0.2.10", 8000))

    def test_ignores_forwarded_headers_from_an_untrusted_client(self) -> None:
        received_scope = {}

        async def application(scope, receive, send) -> None:
            received_scope.update(scope)

        scope = {
            "type": "http",
            "client": ("198.51.100.8", 8000),
            "scheme": "http",
            "headers": [(b"x-forwarded-for", b"203.0.113.2"), (b"x-forwarded-proto", b"https")],
        }

        asyncio.run(TrustedProxyMiddleware(application, IPv4Address("192.0.2.10"))(scope, None, None))

        self.assertEqual(received_scope["client"], ("198.51.100.8", 8000))
        self.assertEqual(received_scope["scheme"], "http")
