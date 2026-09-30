import importlib
import sys
import unittest
from unittest.mock import patch


class MainTest(unittest.TestCase):
    def test_asgi_entrypoint_creates_the_application_with_the_frontend(self) -> None:
        with patch("app.factory.create_app") as create_app:
            sys.modules.pop("app.main", None)
            module = importlib.import_module("app.main")

        create_app.assert_called_once_with(mount_frontend=True)
        self.assertIs(module.app, create_app.return_value)
