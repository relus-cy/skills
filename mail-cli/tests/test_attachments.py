"""Public CLI acceptance tests, using real localhost IMAP/SMTP conversations.

Run: python3 -m unittest discover -s tests -v
Baseline: MAIL_CLI_SCRIPT=/path/to/mail_cli.py.txt python3 -m unittest discover -s tests -v
No real mailbox, credential store, or Internet connection is used.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import socketserver
import subprocess
import sys
import tempfile
import threading
import unittest
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser


SCRIPT = Path(os.environ.get("MAIL_CLI_SCRIPT", str(Path(__file__).parents[1] / "scripts" / "mail_cli.py")))
BINARY = b"\x00\xff\x80\r\n\x01binary attachment\x00"


def message_with_attachments() -> bytes:
    message = EmailMessage()
    message["From"] = "sender@example.test"
    message["To"] = "reader@example.test"
    message["Subject"] = "attachment fixture"
    message.set_content("VISIBLE_BODY")
    message.add_attachment(BINARY, maintype="application", subtype="octet-stream", filename="数据.bin")
    message.add_attachment(b"ATTACHED_TEXT_SECRET", maintype="text", subtype="plain", filename="notes.txt")
    message.add_attachment(b"\x89PNG\r\n", maintype="image", subtype="png", filename="inline.png", disposition="inline", cid="<image@example.test>")
    forwarded = EmailMessage()
    forwarded["From"] = "nested@example.test"
    forwarded["Subject"] = "forwarded message"
    forwarded.set_content("NESTED_BODY_SECRET")
    forwarded.add_attachment(b"NESTED_ATTACHMENT_SECRET", maintype="application", subtype="octet-stream", filename="inner.bin")
    message.add_attachment(forwarded, filename="forwarded.eml")
    return message.as_bytes(policy=policy.SMTP)


def named_message(names: list[str | None], payloads: list[bytes]) -> bytes:
    message = EmailMessage()
    message.set_content("BODY")
    for name, payload in zip(names, payloads):
        message.add_attachment(payload, maintype="application", subtype="octet-stream", filename=name)
    return message.as_bytes(policy=policy.SMTP)


class LoopbackServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, handler, raw=b"", advertised_size=None):
        super().__init__(("127.0.0.1", 0), handler)
        self.raw = raw
        self.advertised_size = len(raw) if advertised_size is None else advertised_size
        self.commands: list[str] = []
        self.messages: list[bytes] = []
        self.connections = 0
        self.thread = threading.Thread(target=self.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.shutdown()
        self.server_close()
        self.thread.join(timeout=2)

    @property
    def port(self):
        return self.server_address[1]


class IMAPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.server.connections += 1
        self.wfile.write(b"* OK fixture IMAP4rev1 ready\r\n")
        while line := self.rfile.readline():
            text = line.decode("ascii", "replace").strip()
            self.server.commands.append(text)
            tag, command, *rest = text.split(" ", 2)
            command = command.upper()
            argument = rest[0] if rest else ""
            if command == "CAPABILITY":
                self.wfile.write(b"* CAPABILITY IMAP4rev1\r\n")
            elif command == "LOGIN":
                pass
            elif command in ("EXAMINE", "SELECT"):
                self.wfile.write(b"* 1 EXISTS\r\n* FLAGS (\\Seen)\r\n")
            elif command == "UID" and argument.upper().startswith("FETCH "):
                if "BODY.PEEK[" in argument.upper():
                    raw = self.server.raw
                    self.wfile.write(f"* 1 FETCH (UID 42 BODY[] {{{len(raw)}}}\r\n".encode())
                    self.wfile.write(raw + b")\r\n")
                elif "RFC822.SIZE" in argument.upper():
                    self.wfile.write(f"* 1 FETCH (UID 42 RFC822.SIZE {self.server.advertised_size})\r\n".encode())
                else:
                    self.wfile.write(f"{tag} BAD unsupported FETCH\r\n".encode())
                    continue
            elif command == "LOGOUT":
                self.wfile.write(b"* BYE fixture logout\r\n")
                self.wfile.write(f"{tag} OK LOGOUT completed\r\n".encode())
                break
            else:
                self.wfile.write(f"{tag} BAD unsupported command\r\n".encode())
                continue
            self.wfile.write(f"{tag} OK {command} completed\r\n".encode())


class SMTPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self.server.connections += 1
        self.wfile.write(b"220 fixture ESMTP ready\r\n")
        while line := self.rfile.readline():
            text = line.decode("ascii", "replace").strip()
            self.server.commands.append(text)
            command = text.split(" ", 1)[0].upper()
            if command in ("EHLO", "HELO"):
                self.wfile.write(b"250-fixture\r\n250-AUTH PLAIN\r\n250 SIZE 104857600\r\n")
            elif command == "AUTH":
                self.wfile.write(b"235 authenticated\r\n")
            elif command in ("MAIL", "RCPT", "RSET", "NOOP"):
                self.wfile.write(b"250 accepted\r\n")
            elif command == "DATA":
                self.wfile.write(b"354 end with dot\r\n")
                chunks = []
                while data := self.rfile.readline():
                    if data == b".\r\n":
                        break
                    chunks.append(data[1:] if data.startswith(b"..") else data)
                self.server.messages.append(b"".join(chunks))
                self.wfile.write(b"250 queued\r\n")
            elif command == "QUIT":
                self.wfile.write(b"221 bye\r\n")
                break
            else:
                self.wfile.write(b"500 unsupported command\r\n")


class AttachmentAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mail-cli-acceptance-")
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
        try:
            result = json.loads(process.stdout)
        except json.JSONDecodeError:
            self.fail(f"Expected JSON output; stdout={process.stdout!r}, stderr={process.stderr!r}")
        self.assertIs(result["ok"], success)
        self.assertNotIn("dummy-test-password", process.stdout + process.stderr)
        return result

    def assert_readonly(self, server):
        commands = "\n".join(server.commands).upper()
        self.assertIn(" EXAMINE INBOX", commands)
        self.assertIn("RFC822.SIZE", commands)
        self.assertIn("BODY.PEEK[]", commands)
        self.assertNotIn(" SELECT ", commands)
        self.assertNotIn(" STORE ", commands)
        self.assertNotIn("BODY[]", commands)

    def send_args(self):
        return ["--to", "recipient@example.test", "--subject", "附件测试", "--text", "hello body", "--confirm-send", "yes"]

    def test_smtp_sends_multiple_base64_attachments_with_exact_bytes(self):
        first = self.root / "数据.bin"
        second = self.root / "notes.txt"
        first.write_bytes(BINARY)
        second.write_bytes("你好\n".encode())
        with LoopbackServer(SMTPHandler) as server:
            self.cli("smtp-send", server, *self.send_args(), "--attach", first, "--attach", second)
            self.assertEqual(len(server.messages), 1)
            sent = BytesParser(policy=policy.default).parsebytes(server.messages[0])
            attachments = list(sent.iter_attachments())
            self.assertEqual(sent["Subject"], "附件测试")
            self.assertEqual(sent.get_body(preferencelist=("plain",)).get_content(), "hello body\r\n")
            self.assertEqual([part.get_filename() for part in attachments], ["数据.bin", "notes.txt"])
            self.assertEqual([part.get_content_type() for part in attachments], ["application/octet-stream", "text/plain"])
            self.assertEqual([part.get_payload(decode=True) for part in attachments], [BINARY, "你好\n".encode()])
            self.assertEqual([part["Content-Transfer-Encoding"] for part in attachments], ["base64", "base64"])

    def test_smtp_rejects_missing_file_directory_and_total_limit_before_connect(self):
        first = self.root / "a.bin"
        second = self.root / "b.bin"
        first.write_bytes(b"123")
        second.write_bytes(b"456")
        scenarios = [(["--attach", self.root / "missing"], "missing"),
                     (["--attach", self.root], "directory"),
                     (["--attach", first, "--attach", second, "--max-attachment-bytes", "5"], "total limit")]
        for options, label in scenarios:
            with self.subTest(label=label), LoopbackServer(SMTPHandler) as server:
                self.cli("smtp-send", server, *self.send_args(), *options, success=False)
                self.assertEqual(server.connections, 0)
                self.assertEqual(server.messages, [])

    def test_smtp_requires_explicit_confirmation_with_attachments(self):
        attachment = self.root / "a.bin"
        attachment.write_bytes(BINARY)
        with LoopbackServer(SMTPHandler) as server:
            self.cli("smtp-send", server, "--to", "recipient@example.test", "--subject", "test",
                     "--text", "body", "--attach", attachment, success=False)
            self.assertEqual(server.connections, 0)

    def test_smtp_default_attachment_limit_rejects_before_connect(self):
        attachment = self.root / "oversized.bin"
        with attachment.open("wb") as stream:
            stream.truncate(25 * 1024 * 1024 + 1)
        with LoopbackServer(SMTPHandler) as server:
            self.cli("smtp-send", server, *self.send_args(), "--attach", attachment, success=False)
            self.assertEqual(server.connections, 0)
            self.assertEqual(server.messages, [])

    def test_imap_lists_decoded_metadata_inline_and_atomic_eml(self):
        with LoopbackServer(IMAPHandler, message_with_attachments()) as server:
            result = self.cli("imap-attachments", server, "--uid", "42")
            self.assertEqual(str(result["uid"]), "42")
            items = result["attachments"]
            self.assertEqual([item["id"] for item in items], [1, 2, 3, 4])
            self.assertEqual([item["filename"] for item in items], ["数据.bin", "notes.txt", "inline.png", "forwarded.eml"])
            self.assertEqual([item["content_type"] for item in items], ["application/octet-stream", "text/plain", "image/png", "message/rfc822"])
            self.assertEqual([item["size"] for item in items[:3]], [len(BINARY), 20, 6])
            self.assertEqual([item["disposition"] for item in items], ["attachment", "attachment", "inline", "attachment"])
            self.assertEqual(items[2]["content_id"], "<image@example.test>")
            self.assertGreater(items[3]["size"], 100)
            self.assert_readonly(server)

    def test_imap_downloads_selected_binary_without_other_files(self):
        output = self.root / "output"
        with LoopbackServer(IMAPHandler, message_with_attachments()) as server:
            result = self.cli("imap-download", server, "--uid", "42", "--output-dir", output, "--attachment-id", "1")
            self.assertEqual([item["id"] for item in result["saved"]], [1])
            self.assertEqual(result["saved"][0]["filename"], "数据.bin")
            self.assertEqual(result["saved"][0]["content_type"], "application/octet-stream")
            self.assertEqual(result["saved"][0]["size"], len(BINARY))
            saved = Path(result["saved"][0]["path"])
            self.assertEqual(saved.resolve(), (output / "数据.bin").resolve())
            self.assertEqual(saved.read_bytes(), BINARY)
            self.assertEqual([path.name for path in output.iterdir()], ["数据.bin"])
            self.assert_readonly(server)

    def test_imap_all_download_preserves_eml_as_one_attachment(self):
        output = self.root / "output"
        with LoopbackServer(IMAPHandler, message_with_attachments()) as server:
            result = self.cli("imap-download", server, "--uid", "42", "--output-dir", output)
            self.assertEqual([item["id"] for item in result["saved"]], [1, 2, 3, 4])
            self.assertEqual(sorted(path.name for path in output.iterdir()), ["forwarded.eml", "inline.png", "notes.txt", "数据.bin"])
            self.assertEqual((output / "notes.txt").read_bytes(), b"ATTACHED_TEXT_SECRET")
            self.assertEqual((output / "inline.png").read_bytes(), b"\x89PNG\r\n")
            nested = BytesParser(policy=policy.default).parsebytes((output / "forwarded.eml").read_bytes())
            self.assertEqual(nested["Subject"], "forwarded message")
            self.assertEqual(nested.get_body().get_content().strip(), "NESTED_BODY_SECRET")
            self.assertEqual(list(nested.iter_attachments())[0].get_payload(decode=True), b"NESTED_ATTACHMENT_SECRET")

    def test_imap_repeated_ids_follow_listing_order(self):
        output = self.root / "output"
        with LoopbackServer(IMAPHandler, message_with_attachments()) as server:
            result = self.cli("imap-download", server, "--uid", "42", "--output-dir", output,
                              "--attachment-id", "3", "--attachment-id", "1")
            self.assertEqual([item["id"] for item in result["saved"]], [1, 3])
            self.assertEqual(sorted(path.name for path in output.iterdir()), ["inline.png", "数据.bin"])

    def test_imap_safe_names_duplicates_and_unnamed_attachment(self):
        raw = named_message(["../../report.txt", r"C:\outside\report.txt", None, "bad\tname.bin"], [b"ONE", b"TWO", b"THREE", b"FOUR"])
        output = self.root / "output"
        with LoopbackServer(IMAPHandler, raw) as server:
            result = self.cli("imap-download", server, "--uid", "42", "--output-dir", output)
            names = [item["filename"] for item in result["saved"]]
            self.assertEqual(names[:2], ["report.txt", "report-2.txt"])
            self.assertRegex(names[2], r"^attachment-3(?:\.[A-Za-z0-9]+)?$")
            for item in result["saved"]:
                self.assertFalse(re.search(r"[\\/\x00-\x1f\x7f]", item["filename"]))
                self.assertEqual(Path(item["path"]).resolve().parent, output.resolve())
            self.assertEqual([Path(item["path"]).read_bytes() for item in result["saved"]], [b"ONE", b"TWO", b"THREE", b"FOUR"])

    def test_imap_preflight_prevents_partial_writes_and_preserves_symlinks(self):
        raw = named_message(["first.bin", "blocked.bin"], [b"FIRST", b"SECOND"])
        for existing_kind in ("file", "symlink"):
            with self.subTest(existing_kind=existing_kind):
                output = self.root / existing_kind
                output.mkdir()
                outside = self.root / (existing_kind + "-outside")
                outside.write_bytes(b"DO NOT OVERWRITE")
                blocked = output / "blocked.bin"
                if existing_kind == "file":
                    blocked.write_bytes(b"DO NOT OVERWRITE")
                else:
                    blocked.symlink_to(outside)
                with LoopbackServer(IMAPHandler, raw) as server:
                    self.cli("imap-download", server, "--uid", "42", "--output-dir", output, success=False)
                self.assertFalse((output / "first.bin").exists())
                self.assertEqual(blocked.read_bytes(), b"DO NOT OVERWRITE")
                self.assertEqual(outside.read_bytes(), b"DO NOT OVERWRITE")
                self.assertEqual(blocked.is_symlink(), existing_kind == "symlink")

    def test_imap_total_limit_and_invalid_id_write_nothing(self):
        raw = named_message(["a.bin", "b.bin"], [b"123", b"456"])
        for options in (["--max-attachment-bytes", "5"], ["--attachment-id", "99"]):
            with self.subTest(options=options), LoopbackServer(IMAPHandler, raw) as server:
                output = self.root / "output"
                self.cli("imap-download", server, "--uid", "42", "--output-dir", output, *options, success=False)
                self.assertFalse(output.exists() and list(output.iterdir()))
        with LoopbackServer(IMAPHandler, raw) as server:
            self.cli("imap-attachments", server, "--uid", "42", "--max-attachment-bytes", "5", success=False)

    def test_imap_selected_download_limit_ignores_unselected_attachment(self):
        raw = named_message(["small.bin", "large.bin"], [b"123", b"12345678"])
        output = self.root / "output"
        with LoopbackServer(IMAPHandler, raw) as server:
            result = self.cli("imap-download", server, "--uid", "42", "--output-dir", output,
                              "--attachment-id", "1", "--max-attachment-bytes", "5")
            self.assertEqual([item["id"] for item in result["saved"]], [1])
            self.assertEqual((output / "small.bin").read_bytes(), b"123")
            self.assertFalse((output / "large.bin").exists())

    def test_imap_default_message_limit_rejects_before_body_fetch(self):
        with LoopbackServer(IMAPHandler, b"small actual message", advertised_size=50 * 1024 * 1024 + 1) as server:
            self.cli("imap-attachments", server, "--uid", "42", success=False)
            self.assertIn("RFC822.SIZE", "\n".join(server.commands).upper())
            self.assertNotIn("BODY.PEEK[", "\n".join(server.commands).upper())

    def test_imap_rejects_advertised_oversize_without_fetching_body(self):
        for command in ("imap-attachments", "imap-download"):
            with self.subTest(command=command), LoopbackServer(IMAPHandler, message_with_attachments()) as server:
                options = ["--output-dir", self.root / "output"] if command == "imap-download" else []
                self.cli(command, server, "--uid", "42", "--max-message-bytes", "100", *options, success=False)
                commands = "\n".join(server.commands).upper()
                self.assertIn("RFC822.SIZE", commands)
                self.assertNotIn("BODY.PEEK[", commands)
                self.assertFalse((self.root / "output").exists())

    def test_imap_checks_actual_size_when_server_underreports(self):
        with LoopbackServer(IMAPHandler, message_with_attachments(), advertised_size=1) as server:
            self.cli("imap-download", server, "--uid", "42", "--output-dir", self.root / "output",
                     "--max-message-bytes", "100", success=False)
            self.assertIn("BODY.PEEK[]", "\n".join(server.commands).upper())
            self.assertFalse((self.root / "output").exists())

    def test_existing_body_fetch_excludes_attached_text_and_nested_eml(self):
        message = BytesParser(policy=policy.default).parsebytes(message_with_attachments())
        message.add_attachment(b"INLINE_TEXT_SECRET", maintype="text", subtype="plain",
                               filename="inline.txt", disposition="inline")
        with LoopbackServer(IMAPHandler, message.as_bytes(policy=policy.SMTP)) as server:
            result = self.cli("imap-fetch", server, "--uid", "42", "--body")
            self.assertEqual(result["text"].strip(), "VISIBLE_BODY")


if __name__ == "__main__":
    unittest.main()
