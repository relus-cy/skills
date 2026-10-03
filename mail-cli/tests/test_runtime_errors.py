"""Exercise operational failures through the public CLI with isolated inputs."""

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(os.environ.get("MAIL_CLI_SCRIPT", Path(__file__).parents[1] / "scripts" / "mail_cli.py"))


class RuntimeErrorTests(unittest.TestCase):
    def invoke(self, protocol, port, timeout="2"):
        with tempfile.TemporaryDirectory(prefix="mail-errors-") as directory:
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith(("MAIL_", "IMAP_", "SMTP_", "EMAIL_"))}
            environment.update(MAIL_USERNAME="test@example.invalid", MAIL_PASSWORD="dummy-private-password",
                               EMAIL_AUTH_ROOT=str(Path(directory) / "auth"))
            environment.update({f"{protocol.upper()}_HOST": "127.0.0.1",
                                f"{protocol.upper()}_PORT": str(port),
                                f"{protocol.upper()}_SECURITY": "plain"})
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--timeout", timeout, f"{protocol}-test"],
                env=environment, text=True, capture_output=True, timeout=5,
            )
            self.assertFalse((Path(directory) / "auth").exists())
            return result

    def assert_json_error(self, result, prefix):
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        self.assertNotIn("dummy-private-password", result.stdout + result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual(set(response), {"ok", "error"})
        self.assertIs(response["ok"], False)
        self.assertTrue(response["error"].startswith(prefix), response)
        return response

    def test_refused_imap_connection_returns_json(self):
        with socket.socket() as endpoint:
            endpoint.bind(("127.0.0.1", 0))
            port = endpoint.getsockname()[1]
        self.assert_json_error(self.invoke("imap", port), "I/O error:")

    def test_refused_smtp_connection_returns_json(self):
        with socket.socket() as endpoint:
            endpoint.bind(("127.0.0.1", 0))
            port = endpoint.getsockname()[1]
        self.assert_json_error(self.invoke("smtp", port), "I/O error:")

    def test_invalid_imap_port_returns_json(self):
        self.assert_json_error(self.invoke("imap", "invalid-port"), "Invalid configuration or input:")

    def test_invalid_smtp_port_returns_json(self):
        self.assert_json_error(self.invoke("smtp", "invalid-port"), "Invalid configuration or input:")

    def test_out_of_range_imap_port_returns_configuration_error(self):
        for port in (-1, 65536):
            with self.subTest(port=port):
                self.assert_json_error(self.invoke("imap", port), "Invalid configuration or input:")

    def test_out_of_range_smtp_port_returns_configuration_error(self):
        for port in (-1, 65536):
            with self.subTest(port=port):
                self.assert_json_error(self.invoke("smtp", port), "Invalid configuration or input:")

    def test_infinite_timeout_returns_configuration_error(self):
        for protocol in ("imap", "smtp"):
            with self.subTest(protocol=protocol):
                self.assert_json_error(self.invoke(protocol, 1, timeout="inf"),
                                       "Invalid configuration or input:")


if __name__ == "__main__":
    unittest.main()
