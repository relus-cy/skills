"""Regression tests: a successful-looking result must not hide missing or partial data.

Each test pins a defect where the CLI reported ok=true with empty or incomplete
data while the server conversation had actually failed or gone unanswered.
Run: python3 -m unittest discover -s tests -v
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_attachments import IMAPHandler, LoopbackServer, SMTPHandler

SCRIPT = Path(os.environ.get("MAIL_CLI_SCRIPT", str(Path(__file__).parents[1] / "scripts" / "mail_cli.py")))


class ResultIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mail-cli-integrity-")
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        # Deliberately do not inherit real credential/provider/network variables.
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("MAIL_", "IMAP_", "SMTP_", "EMAIL_"))}
        self.env.update(MAIL_USERNAME="reader@example.test", MAIL_PASSWORD="dummy-test-password",
                        EMAIL_AUTH_ROOT=str(self.root / "isolated-auth"))

    def cli(self, command, server, *args, success=True):
        protocol = "smtp" if command.startswith("smtp-") else "imap"
        process = subprocess.run(
            [sys.executable, str(SCRIPT), "--timeout", "3", command,
             f"--{protocol}-host", "127.0.0.1", f"--{protocol}-port", str(server.port),
             f"--{protocol}-security", "plain", *map(str, args)],
            env=self.env, input="", capture_output=True, text=True, timeout=10)
        self.assertEqual(process.returncode == 0, success,
                         f"returncode={process.returncode}\nstdout={process.stdout}\nstderr={process.stderr}")
        result = json.loads(process.stdout)
        self.assertIs(result["ok"], success)
        self.assertNotIn("dummy-test-password", process.stdout + process.stderr)
        return result

    def test_smtp_send_reports_each_refused_recipient(self):
        with LoopbackServer(SMTPHandler) as server:
            server.refuse_rcpt = ("refused@example.test",)
            result = self.cli("smtp-send", server,
                              "--to", "accepted@example.test", "--to", "refused@example.test",
                              "--subject", "partial delivery", "--text", "body", "--confirm-send", "yes")
            sent = result["sent"]
            self.assertEqual(sent["to"], ["accepted@example.test", "refused@example.test"])
            self.assertEqual(list(sent["refused"]), ["refused@example.test"])
            self.assertEqual(sent["refused"]["refused@example.test"]["code"], 550)
            # The accepted recipient still received the message.
            self.assertEqual(len(server.messages), 1)

    def test_imap_test_fails_when_list_fails(self):
        with LoopbackServer(IMAPHandler) as server:
            server.fail_list = True
            result = self.cli("imap-test", server, success=False)
            self.assertIn("LIST", result["error"])

    def test_imap_search_fails_when_a_header_fetch_fails(self):
        with LoopbackServer(IMAPHandler) as server:
            server.fail_uid_fetch = True
            result = self.cli("imap-search", server, "--criteria", "ALL", success=False)
            self.assertIn("FETCH", result["error"])

    def test_imap_fetch_fails_when_the_response_has_no_message_data(self):
        with LoopbackServer(IMAPHandler) as server:
            server.fetch_without_literal = True
            result = self.cli("imap-fetch", server, "--uid", "42", "--body", success=False)
            self.assertIn("no message data", result["error"])


if __name__ == "__main__":
    unittest.main()
