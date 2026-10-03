"""CLI validation must reject local attachment errors before connecting."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from email import policy
from email.parser import BytesParser

from test_attachments import IMAPHandler, LoopbackServer, SMTPHandler


SCRIPT = Path(os.environ.get("MAIL_CLI_SCRIPT", Path(__file__).parents[1] / "scripts" / "mail_cli.py"))


class AttachmentValidationTests(unittest.TestCase):
    def test_excessively_nested_email_returns_json_error_without_download(self):
        raw = (b"MIME-Version: 1.0\r\nContent-Type: message/rfc822\r\n\r\n" * 300
               + b"Subject: innermost\r\nContent-Type: text/plain\r\n\r\nBODY\r\n")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            with LoopbackServer(IMAPHandler, raw) as server:
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--username", "test@example.invalid",
                     "imap-download", "--imap-host", "127.0.0.1", "--imap-port", str(server.port),
                     "--imap-security", "plain", "--uid", "42", "--output-dir", str(output)],
                    env={**os.environ, "MAIL_PASSWORD": "test-only-password",
                         "EMAIL_AUTH_ROOT": str(Path(directory) / "auth")},
                    text=True, capture_output=True, timeout=10,
                )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertIs(json.loads(result.stdout)["ok"], False)
            self.assertFalse(output.exists())

    def test_corrupt_base64_download_fails_without_saving_repaired_or_encoded_bytes(self):
        for encoded in (b"QUJD?REVGRw==", b"QUJDREVGRw", b"QUJDREVGR"):
            with self.subTest(encoded=encoded), tempfile.TemporaryDirectory() as directory:
                raw = (
                    b"MIME-Version: 1.0\r\nContent-Type: multipart/mixed; boundary=b\r\n\r\n"
                    b"--b\r\nContent-Type: text/plain\r\n\r\nBODY\r\n"
                    b"--b\r\nContent-Type: application/octet-stream\r\n"
                    b"Content-Disposition: attachment; filename=broken.bin\r\n"
                    b"Content-Transfer-Encoding: base64\r\n\r\n" + encoded + b"\r\n--b--\r\n"
                )
                output = Path(directory) / "output"
                with LoopbackServer(IMAPHandler, raw) as server:
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), "--username", "test@example.invalid",
                         "imap-download", "--imap-host", "127.0.0.1", "--imap-port", str(server.port),
                         "--imap-security", "plain", "--uid", "42", "--output-dir", str(output)],
                        env={**os.environ, "MAIL_PASSWORD": "test-only-password",
                             "EMAIL_AUTH_ROOT": str(Path(directory) / "auth")},
                        text=True, capture_output=True, timeout=10,
                    )
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertIs(json.loads(result.stdout)["ok"], False)
                self.assertFalse(output.exists())

    def test_eml_send_uses_valid_message_encoding_and_preserves_embedded_content(self):
        with tempfile.TemporaryDirectory() as directory:
            attachment = Path(directory) / "forwarded.eml"
            attachment.write_bytes(
                b"From: nested@example.invalid\r\nSubject: nested subject\r\n"
                b"Content-Type: text/plain; charset=utf-8\r\n\r\nEMBEDDED BODY\r\n"
            )
            with LoopbackServer(SMTPHandler) as server:
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--username", "test@example.invalid",
                     "smtp-send", "--smtp-host", "127.0.0.1", "--smtp-port", str(server.port),
                     "--smtp-security", "plain", "--to", "other@example.invalid",
                     "--subject", "test", "--text", "body", "--attach", str(attachment),
                     "--confirm-send", "yes"],
                    env={**os.environ, "MAIL_PASSWORD": "test-only-password",
                         "EMAIL_AUTH_ROOT": str(Path(directory) / "auth")},
                    text=True, capture_output=True, timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(len(server.messages), 1)
                sent = BytesParser(policy=policy.default).parsebytes(server.messages[0])
                part = list(sent.iter_attachments())[0]
                self.assertEqual(part.get_filename(), "forwarded.eml")
                self.assertEqual(part.get_content_type(), "message/rfc822")
                self.assertIn(part["Content-Transfer-Encoding"], (None, "7bit", "8bit", "binary"))
                nested = part.get_payload()[0]
                self.assertEqual(nested["Subject"], "nested subject")
                self.assertEqual(nested.get_content().strip(), "EMBEDDED BODY")

    def test_missing_send_attachment_is_a_json_error_before_smtp(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.pdf"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--username", "test@example.invalid",
                 "smtp-send", "--smtp-host", "127.0.0.1", "--smtp-port", "9",
                 "--smtp-security", "plain", "--to", "other@example.invalid",
                 "--subject", "test", "--text", "body", "--attach", str(missing),
                 "--confirm-send", "yes"],
                env={**os.environ, "MAIL_PASSWORD": "test-only-password",
                     "EMAIL_AUTH_ROOT": str(Path(directory) / "auth")},
                text=True, capture_output=True, timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            payload = json.loads(result.stdout)
            self.assertIs(payload["ok"], False)
            self.assertIn("missing.pdf", payload["error"])
            self.assertFalse((Path(directory) / "auth").exists())


if __name__ == "__main__":
    unittest.main()
