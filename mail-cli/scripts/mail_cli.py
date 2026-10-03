#!/usr/bin/env python3
"""Small IMAP/SMTP CLI for mailbox onboarding and agent operations."""

from __future__ import annotations

import argparse
import base64
import binascii
import email
import errno
import fcntl
import hashlib
import imaplib
import json
import mimetypes
import os
import quopri
import re
import secrets
import shutil
import smtplib
import ssl
import stat
import subprocess
import sys
import time
import unicodedata
from contextlib import contextmanager
from datetime import date, datetime, timezone, timedelta
from email import policy
from email.errors import InvalidBase64CharactersDefect, InvalidBase64LengthDefect, InvalidBase64PaddingDefect
from email.header import decode_header, make_header
from email.message import EmailMessage, Message
from email.parser import BytesParser
from pathlib import Path
from typing import Any, Iterator


HEADER_FIELDS = ("From", "To", "Cc", "Subject", "Date", "Message-ID")
PLUGIN_AUTH_NAME = "email"
SANDBOX_AUTH_ROOT = Path("/mnt/agents/.user/auth")
LOCAL_AUTH_ROOT = Path.home() / ".kimi-work" / "auth"
AUTH_STORE_ENV = "EMAIL_AUTH_ROOT"
AUTH_LOCK_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
DEFAULT_MAX_MESSAGE_BYTES = 50 * 1024 * 1024

PROVIDER_PROFILES: dict[str, dict[str, Any]] = {
    "qq": {
        "name": "QQ Mail",
        "domains": ["qq.com", "foxmail.com"],
        "imap_host": "imap.qq.com",
        "imap_port": 993,
        "imap_security": "ssl",
        "smtp_host": "smtp.qq.com",
        "smtp_port": 465,
        "smtp_security": "ssl",
        "credential": "QQ authorization code",
        "setup_url": "https://wx.mail.qq.com/account",
    },
    "163": {
        "name": "NetEase 163 Mail",
        "domains": ["163.com"],
        "imap_host": "imap.163.com",
        "imap_port": 993,
        "imap_security": "ssl",
        "smtp_host": "smtp.163.com",
        "smtp_port": 465,
        "smtp_security": "ssl",
        "credential": "NetEase authorization code",
        "setup_url": "https://mail.163.com/",
    },
    "126": {
        "name": "NetEase 126 Mail",
        "domains": ["126.com"],
        "imap_host": "imap.126.com",
        "imap_port": 993,
        "imap_security": "ssl",
        "smtp_host": "smtp.126.com",
        "smtp_port": 465,
        "smtp_security": "ssl",
        "credential": "NetEase authorization code",
        "setup_url": "https://mail.126.com/",
    },
    "yeah": {
        "name": "NetEase yeah.net",
        "domains": ["yeah.net"],
        "imap_host": "imap.yeah.net",
        "imap_port": 993,
        "imap_security": "ssl",
        "smtp_host": "smtp.yeah.net",
        "smtp_port": 465,
        "smtp_security": "ssl",
        "credential": "NetEase authorization code",
        "setup_url": "https://www.yeah.net/",
    },
    "netease_enterprise": {
        "name": "NetEase Enterprise Mail / PKU student mail",
        "domains": ["stu.pku.edu.cn"],
        "imap_host": "mail.stu.pku.edu.cn",
        "imap_port": 993,
        "imap_security": "ssl",
        "smtp_host": "mail.stu.pku.edu.cn",
        "smtp_port": 465,
        "smtp_security": "ssl",
        "credential": "NetEase enterprise client authorization password",
        "setup_url": "https://mailshz.qiye.163.com/",
    },
    "gmail": {
        "name": "Gmail",
        "domains": ["gmail.com", "googlemail.com"],
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "imap_security": "ssl",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 465,
        "smtp_security": "ssl",
        "credential": "Google app password or OAuth-backed credential",
        "setup_url": "https://myaccount.google.com/security",
    },
    "outlook": {
        "name": "Outlook.com / Microsoft 365",
        "domains": ["outlook.com", "hotmail.com", "live.com", "msn.com"],
        "imap_host": "outlook.office365.com",
        "imap_port": 993,
        "imap_security": "ssl",
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
        "smtp_security": "starttls",
        "credential": "OAuth-backed credential or app password when allowed",
        "setup_url": "https://outlook.live.com/mail/",
    },
    "yahoo": {
        "name": "Yahoo Mail",
        "domains": ["yahoo.com", "ymail.com", "rocketmail.com"],
        "imap_host": "imap.mail.yahoo.com",
        "imap_port": 993,
        "imap_security": "ssl",
        "smtp_host": "smtp.mail.yahoo.com",
        "smtp_port": 465,
        "smtp_security": "ssl",
        "credential": "Yahoo app password",
        "setup_url": "https://login.yahoo.com/account/security",
    },
    "icloud": {
        "name": "iCloud Mail",
        "domains": ["icloud.com", "me.com", "mac.com"],
        "imap_host": "imap.mail.me.com",
        "imap_port": 993,
        "imap_security": "ssl",
        "smtp_host": "smtp.mail.me.com",
        "smtp_port": 587,
        "smtp_security": "starttls",
        "credential": "Apple app-specific password",
        "setup_url": "https://account.apple.com/",
    },
    "exmail": {
        "name": "Tencent Exmail",
        "domains": [],
        "imap_host": "imap.exmail.qq.com",
        "imap_port": 993,
        "imap_security": "ssl",
        "smtp_host": "smtp.exmail.qq.com",
        "smtp_port": 465,
        "smtp_security": "ssl",
        "credential": "enterprise client password or authorization code",
        "setup_url": "https://exmail.qq.com/",
    },
    "zoho": {
        "name": "Zoho Mail",
        "domains": ["zoho.com"],
        "imap_host": "imap.zoho.com",
        "imap_port": 993,
        "imap_security": "ssl",
        "smtp_host": "smtp.zoho.com",
        "smtp_port": 465,
        "smtp_security": "ssl",
        "credential": "Zoho app password when MFA is enabled",
        "setup_url": "https://mail.zoho.com/",
    },
    "fastmail": {
        "name": "Fastmail",
        "domains": ["fastmail.com"],
        "imap_host": "imap.fastmail.com",
        "imap_port": 993,
        "imap_security": "ssl",
        "smtp_host": "smtp.fastmail.com",
        "smtp_port": 465,
        "smtp_security": "ssl",
        "credential": "Fastmail app password",
        "setup_url": "https://app.fastmail.com/settings/security",
    },
}


def fail(message: str, code: int = 2) -> None:
    emit({"ok": False, "error": message})
    raise SystemExit(code)


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def env_first(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def require(value: str | None, name: str) -> str:
    if not value:
        fail(f"Missing {name}. Pass an option or set the matching environment variable.")
    return value


def auth_root() -> tuple[Path, str]:
    env_value = os.environ.get(AUTH_STORE_ENV)
    if env_value:
        return Path(env_value).expanduser(), "env"
    if SANDBOX_AUTH_ROOT.exists():
        return SANDBOX_AUTH_ROOT, "sandbox"
    return LOCAL_AUTH_ROOT, "local"


def auth_paths(create: bool = False) -> dict[str, Any]:
    root, mode = auth_root()
    auth_dir = root / PLUGIN_AUTH_NAME
    secrets_dir = auth_dir / "secrets"
    if create:
        try:
            auth_dir.mkdir(parents=True, exist_ok=True)
            secrets_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(auth_dir, 0o700)
            os.chmod(secrets_dir, 0o700)
        except OSError as exc:
            fail(f"Could not create auth directory {auth_dir}: {exc}")
    return {
        "mode": mode,
        "root": root,
        "auth_dir": auth_dir,
        "store_file": auth_dir / "accounts.json",
        "secrets_dir": secrets_dir,
        "master_key_file": auth_dir / "master.key",
        "legacy_master_key_file": auth_dir / ".key",
    }


@contextmanager
def auth_store_lock(create: bool = True):
    paths = auth_paths(create=create)
    auth_store_root: Path = paths["root"]
    lock_path = auth_store_root / f".{PLUGIN_AUTH_NAME}.accounts.lock"
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    lock_fh = os.fdopen(fd, "a+", encoding="utf-8")
    try:
        os.chmod(lock_path, 0o600)
        started_at = time.monotonic()
        while True:
            try:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    raise
                if time.monotonic() - started_at >= AUTH_LOCK_TIMEOUT_SECONDS:
                    fail("Timed out waiting for Email auth store lock. Try again.")
                time.sleep(0.05)
        try:
            yield paths
        finally:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
    finally:
        lock_fh.close()


def require_openssl() -> str:
    openssl = shutil.which("openssl")
    if not openssl:
        fail("Missing openssl. Use MAIL_PASSWORD for a one-off run, or install openssl before auth-save.")
    return openssl


def ensure_master_key(paths: dict[str, Any]) -> Path:
    key_file: Path = paths["master_key_file"]
    if key_file.exists():
        return key_file
    legacy_key_file: Path = paths["legacy_master_key_file"]
    if legacy_key_file.exists():
        try:
            key_file.write_text(legacy_key_file.read_text(encoding="utf-8"), encoding="utf-8")
            os.chmod(key_file, 0o600)
            return key_file
        except OSError as exc:
            fail(f"Could not migrate auth encryption key {legacy_key_file}: {exc}")
    try:
        fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(secrets.token_hex(32))
            fh.write("\n")
        os.chmod(key_file, 0o600)
    except FileExistsError:
        pass
    except OSError as exc:
        fail(f"Could not create auth encryption key {key_file}: {exc}")
    return key_file


def secret_relpath(email_address: str) -> str:
    digest = hashlib.sha256(normalize_email(email_address).encode("utf-8")).hexdigest()
    return f"secrets/{digest}.enc"


def legacy_secret_relpath(email_address: str) -> str:
    digest = hashlib.sha256(normalize_email(email_address).encode("utf-8")).hexdigest()
    return f"secrets/{digest[:16]}.enc"


def secret_path(relpath: str, create: bool = False) -> Path:
    rel = Path(relpath)
    if rel.is_absolute() or ".." in rel.parts:
        fail("Invalid secret path in auth store.")
    paths = auth_paths(create=create)
    auth_dir: Path = paths["auth_dir"]
    return auth_dir / rel


def existing_secret_relpath(email_address: str, account: dict[str, Any] | None = None) -> str | None:
    account = account or {}
    candidates = [
        account.get("secret_file"),
        secret_relpath(email_address),
        legacy_secret_relpath(email_address),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        relpath = str(candidate)
        if secret_path(relpath, create=False).exists():
            return relpath
    return None


def is_missing(value: Any) -> bool:
    return value is None or value == ""


def normalize_security_from_legacy(account: dict[str, Any]) -> bool:
    changed = False
    if "tls" in account:
        tls_value = account.get("tls")
        if is_missing(account.get("imap_security")) and tls_value is not None:
            account["imap_security"] = "ssl" if tls_value else "plain"
            changed = True
        if is_missing(account.get("smtp_security")) and tls_value is not None:
            smtp_port = int(account.get("smtp_port") or 0)
            account["smtp_security"] = "starttls" if smtp_port == 587 and tls_value else ("ssl" if tls_value else "plain")
            changed = True
        account.pop("tls", None)
        changed = True
    return changed


def repair_account_defaults(email_key: str, account: dict[str, Any]) -> bool:
    changed = False
    email_address = str(account.get("email") or email_key).strip().lower()
    if email_address and account.get("email") != email_address:
        account["email"] = email_address
        changed = True

    changed = normalize_security_from_legacy(account) or changed

    current_provider = account.get("provider")
    provider = current_provider if current_provider in PROVIDER_PROFILES else None
    if not provider and not current_provider:
        inferred = detect_provider(email_address)
        if inferred:
            account["provider"] = inferred
            provider = inferred
            changed = True

    profile = PROVIDER_PROFILES.get(provider or "")
    if profile:
        for field in (
            "credential",
            "imap_host",
            "imap_port",
            "imap_security",
            "smtp_host",
            "smtp_port",
            "smtp_security",
            "setup_url",
        ):
            if (
                (is_missing(account.get(field)) or account.get(field) == "app password or authorization code")
                and not is_missing(profile.get(field))
            ):
                account[field] = profile[field]
                changed = True

    if is_missing(account.get("secret_file")):
        relpath = existing_secret_relpath(email_address, account)
        if relpath:
            account["secret_file"] = relpath
            changed = True

    return changed


def run_openssl(args: list[str], input_text: str) -> str:
    result = subprocess.run(
        args,
        input=input_text.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        fail(f"openssl failed: {detail or 'unknown error'}")
    return result.stdout.decode("utf-8", errors="replace")


def encrypt_secret(email_address: str, secret_value: str) -> str:
    paths = auth_paths(create=True)
    key_file = ensure_master_key(paths)
    relpath = secret_relpath(email_address)
    out_path = secret_path(relpath, create=True)
    tmp_path = out_path.with_name(f"{out_path.name}.tmp-{os.getpid()}")
    openssl = require_openssl()
    cipher_text = run_openssl(
        [
            openssl,
            "enc",
            "-aes-256-cbc",
            "-pbkdf2",
            "-iter",
            "100000",
            "-salt",
            "-base64",
            "-A",
            "-pass",
            f"file:{key_file}",
        ],
        secret_value,
    ).strip()
    if not cipher_text:
        fail("openssl returned an empty encrypted secret.")
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(f"v1:{int(datetime.now(timezone.utc).timestamp())}:{cipher_text}\n")
        os.replace(tmp_path, out_path)
        os.chmod(out_path, 0o600)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
    return relpath


def decrypt_secret(relpath: str) -> str:
    paths = auth_paths(create=False)
    key_file: Path = paths["master_key_file"]
    in_path = secret_path(relpath, create=False)
    if not in_path.exists():
        fail("Stored mailbox secret is missing. Re-save the authorization code.")
    if not key_file.exists():
        fail("Stored mailbox encryption key is missing. Re-save the authorization code.")
    try:
        text = in_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        fail(f"Could not read stored mailbox secret: {exc}")
    parts = text.split(":", 2)
    if len(parts) != 3 or parts[0] != "v1" or not parts[1].isdigit() or not parts[2]:
        fail("Stored mailbox secret has an unsupported format. Re-save the authorization code.")
    openssl = require_openssl()
    return run_openssl(
        [
            openssl,
            "enc",
            "-d",
            "-aes-256-cbc",
            "-pbkdf2",
            "-iter",
            "100000",
            "-base64",
            "-A",
            "-pass",
            f"file:{key_file}",
        ],
        parts[2],
    )


def delete_secret_file(account: dict[str, Any]) -> bool:
    relpath = account.get("secret_file")
    if not relpath:
        return False
    path = secret_path(str(relpath), create=False)
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        fail(f"Could not delete stored mailbox secret: {exc}")


def load_auth_store_unlocked(create: bool = False) -> dict[str, Any]:
    paths = auth_paths(create=create)
    store_file: Path = paths["store_file"]
    if not store_file.exists():
        return {"version": 1, "accounts": {}}
    try:
        with store_file.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        fail(f"Could not read auth store {store_file}: {exc}")
    if isinstance(data, list):
        accounts: dict[str, Any] = {}
        for raw_account in data:
            if not isinstance(raw_account, dict):
                continue
            raw_email = raw_account.get("email")
            if not raw_email:
                continue
            email_address = normalize_email(str(raw_email))
            account = dict(raw_account)
            account["email"] = email_address
            relpath = existing_secret_relpath(email_address, account)
            if relpath:
                account["secret_file"] = relpath
            repair_account_defaults(email_address, account)
            accounts[email_address] = account
        data = {"version": 1, "accounts": accounts}
        ensure_master_key(paths)
        save_auth_store_unlocked(data)
        return data
    if not isinstance(data, dict):
        fail(f"Invalid auth store format: {store_file}")
    accounts = data.setdefault("accounts", {})
    if not isinstance(accounts, dict):
        fail(f"Invalid auth store accounts format: {store_file}")
    data.setdefault("version", 1)
    changed = False
    for email_address, account in list(accounts.items()):
        if not isinstance(account, dict):
            continue
        changed = repair_account_defaults(str(email_address), account) or changed
    if changed:
        save_auth_store_unlocked(data)
    return data


def load_auth_store(create: bool = False) -> dict[str, Any]:
    paths = auth_paths(create=create)
    store_file: Path = paths["store_file"]
    if not create and not store_file.exists():
        return {"version": 1, "accounts": {}}
    with auth_store_lock(create=create):
        return load_auth_store_unlocked(create=create)


def save_auth_store_unlocked(data: dict[str, Any]) -> None:
    paths = auth_paths(create=True)
    store_file: Path = paths["store_file"]
    tmp_file = store_file.with_name(f"{store_file.name}.tmp-{os.getpid()}")
    encoded = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    fd = os.open(tmp_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(encoded)
            fh.write(b"\n")
        os.replace(tmp_file, store_file)
        os.chmod(store_file, 0o600)
    finally:
        try:
            if tmp_file.exists():
                tmp_file.unlink()
        except OSError:
            pass


def save_auth_store(data: dict[str, Any]) -> None:
    with auth_store_lock(create=True):
        save_auth_store_unlocked(data)


def normalize_email(address: str | None) -> str:
    if not address:
        fail("Missing email address. Pass --email or set MAIL_USERNAME.")
    value = address.strip().lower()
    if "@" not in value:
        fail("Email address must include @.")
    return value


def stored_account(email_address: str | None) -> dict[str, Any]:
    if not email_address:
        return {}
    key = normalize_email(email_address)
    data = load_auth_store(create=False)
    account = data.get("accounts", {}).get(key, {})
    return account if isinstance(account, dict) else {}


def account_secret_status(account: dict[str, Any], verify_decrypt: bool = False, metadata_only: bool = False) -> str:
    if account.get("password") and not account.get("secret_file"):
        return "legacy_plaintext"
    relpath = account.get("secret_file")
    if not relpath:
        return "missing"
    rel = Path(str(relpath))
    if rel.is_absolute() or ".." in rel.parts:
        return "invalid_path"
    paths = auth_paths(create=False)
    key_file: Path = paths["master_key_file"]
    secret_file: Path = paths["auth_dir"] / rel
    if not key_file.exists():
        return "missing_key"
    if not secret_file.exists():
        return "missing_secret"
    if metadata_only:
        return "encrypted_unverified"
    try:
        text = secret_file.read_text(encoding="utf-8").strip()
    except OSError:
        return "unreadable_secret"
    parts = text.split(":", 2)
    if len(parts) != 3 or parts[0] != "v1" or not parts[1].isdigit() or not parts[2]:
        return "invalid_secret_format"
    if not verify_decrypt:
        return "encrypted"
    openssl = shutil.which("openssl")
    if not openssl:
        return "missing_openssl"
    result = subprocess.run(
        [
            openssl,
            "enc",
            "-d",
            "-aes-256-cbc",
            "-pbkdf2",
            "-iter",
            "100000",
            "-base64",
            "-A",
            "-pass",
            f"file:{key_file}",
        ],
        input=parts[2].encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return "encrypted" if result.returncode == 0 else "decrypt_failed"


def account_public(account: dict[str, Any], verify_secret: bool = False, metadata_only: bool = False) -> dict[str, Any]:
    secret_status = account_secret_status(account, verify_decrypt=verify_secret, metadata_only=metadata_only)
    return {
        "email": account.get("email"),
        "provider": account.get("provider"),
        "credential": account.get("credential"),
        "has_password": secret_status in ("encrypted", "encrypted_unverified", "legacy_plaintext"),
        "secret_storage": secret_status,
        "imap_host": account.get("imap_host"),
        "imap_port": account.get("imap_port"),
        "imap_security": account.get("imap_security"),
        "smtp_host": account.get("smtp_host"),
        "smtp_port": account.get("smtp_port"),
        "smtp_security": account.get("smtp_security"),
        "created_at": account.get("created_at"),
        "updated_at": account.get("updated_at"),
    }


def secret_store_summary(accounts: dict[str, Any]) -> dict[str, Any]:
    paths = auth_paths(create=False)
    secrets_dir: Path = paths["secrets_dir"]
    secret_files: set[str] = set()
    if secrets_dir.exists():
        for path in secrets_dir.iterdir():
            if path.is_file() and path.suffix == ".enc":
                secret_files.add(f"secrets/{path.name}")

    referenced: set[str] = set()
    for account in accounts.values():
        if not isinstance(account, dict):
            continue
        relpath = account.get("secret_file")
        if not relpath:
            continue
        rel = Path(str(relpath))
        if rel.is_absolute() or ".." in rel.parts:
            continue
        referenced.add(str(rel))

    orphan_count = len(secret_files - referenced)
    return {
        "secret_file_count": len(secret_files),
        "referenced_secret_count": len(secret_files & referenced),
        "orphan_secret_count": orphan_count,
        "store_drift": orphan_count > 0,
    }


def load_auth_store_readonly() -> tuple[dict[str, Any], dict[str, Any]]:
    paths = auth_paths(create=False)
    store_file: Path = paths["store_file"]
    notes: dict[str, Any] = {
        "legacy_list_format": False,
        "repaired_in_memory": 0,
        "store_exists": store_file.exists(),
    }
    if not store_file.exists():
        return {"version": 1, "accounts": {}}, notes
    try:
        with store_file.open("r", encoding="utf-8") as fh:
            raw_data = json.load(fh)
    except Exception as exc:
        fail(f"Could not read auth store {store_file}: {exc}")

    if isinstance(raw_data, list):
        notes["legacy_list_format"] = True
        accounts: dict[str, Any] = {}
        for raw_account in raw_data:
            if not isinstance(raw_account, dict):
                continue
            raw_email = raw_account.get("email")
            if not raw_email:
                continue
            email_address = normalize_email(str(raw_email))
            account = dict(raw_account)
            account["email"] = email_address
            before = json.dumps(account, ensure_ascii=False, sort_keys=True, default=str)
            relpath = existing_secret_relpath(email_address, account)
            if relpath:
                account["secret_file"] = relpath
            repair_account_defaults(email_address, account)
            after = json.dumps(account, ensure_ascii=False, sort_keys=True, default=str)
            if after != before:
                notes["repaired_in_memory"] += 1
            accounts[email_address] = account
        return {"version": 1, "accounts": accounts}, notes

    if not isinstance(raw_data, dict):
        fail(f"Invalid auth store format: {store_file}")
    accounts = raw_data.setdefault("accounts", {})
    if not isinstance(accounts, dict):
        fail(f"Invalid auth store accounts format: {store_file}")
    data = json.loads(json.dumps(raw_data, ensure_ascii=False, default=str))
    repaired = 0
    for email_address, account in list(data.get("accounts", {}).items()):
        if not isinstance(account, dict):
            continue
        before = json.dumps(account, ensure_ascii=False, sort_keys=True, default=str)
        repair_account_defaults(str(email_address), account)
        after = json.dumps(account, ensure_ascii=False, sort_keys=True, default=str)
        if after != before:
            repaired += 1
    notes["repaired_in_memory"] = repaired
    data.setdefault("version", 1)
    return data, notes


def password_value(args: argparse.Namespace) -> str:
    env_value = os.environ.get(args.password_env)
    if env_value:
        return env_value
    account = stored_account(mailbox_username(args))
    if account.get("secret_file"):
        return decrypt_secret(str(account["secret_file"]))
    if account.get("password"):
        return str(account["password"])
    fail(
        f"Missing secret. Put the app password/authorization code in ${args.password_env}, "
        "or save it with the auth-save command."
    )


def mailbox_username(args: argparse.Namespace) -> str | None:
    return getattr(args, "username", None) or env_first("MAIL_USERNAME", "MAIL_EMAIL")


def email_domain(address: str | None) -> str:
    if not address or "@" not in address:
        return ""
    return address.rsplit("@", 1)[1].strip().lower()


def detect_provider(email_address: str | None, provider_hint: str | None = None) -> str | None:
    hint = (provider_hint or env_first("MAIL_PROVIDER") or "auto").strip().lower()
    if hint and hint != "auto":
        return hint if hint in PROVIDER_PROFILES else None

    domain = email_domain(email_address)
    for key, profile in PROVIDER_PROFILES.items():
        if domain in profile.get("domains", []):
            return key
    return None


def provider_profile(args: argparse.Namespace) -> tuple[str | None, dict[str, Any]]:
    username = mailbox_username(args)
    provider = detect_provider(username, getattr(args, "provider", None))
    if not provider:
        return None, {}
    return provider, PROVIDER_PROFILES.get(provider, {})


def connection_value(args: argparse.Namespace, attr: str, env_name: str, profile_key: str, fallback: Any = None) -> Any:
    value = getattr(args, attr, None)
    if value is not None:
        return value
    env_value = os.environ.get(env_name)
    if env_value:
        return env_value
    account = stored_account(mailbox_username(args))
    if account.get(profile_key) not in (None, ""):
        return account.get(profile_key)
    _, profile = provider_profile(args)
    return profile.get(profile_key, fallback)


def decode_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    try:
        return str(make_header(decode_header(str(value))))
    except Exception:
        return str(value)


def message_headers(raw: bytes) -> dict[str, str]:
    msg = BytesParser(policy=policy.default).parsebytes(raw)
    return {field.lower(): decode_text(msg.get(field)) for field in HEADER_FIELDS}


def first_literal(data: list[Any]) -> bytes:
    for item in data:
        if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], bytes):
            return item[1]
    return b""


def is_attachment_part(part: Message) -> bool:
    return (
        part.get_content_disposition() == "attachment"
        or part.get_filename() is not None
        or part.get_content_maintype() not in ("text", "multipart")
    )


def content_parts(msg: Message) -> Iterator[Message]:
    """Walk MIME containers, keeping attached messages/containers intact."""
    pending = [msg]
    while pending:
        part = pending.pop()
        if is_attachment_part(part) or not part.is_multipart():
            yield part
        else:
            pending.extend(reversed(part.get_payload()))


def extract_text(msg: Message, max_bytes: int) -> str:
    chunks: list[str] = []
    for part in content_parts(msg):
        content_type = part.get_content_type()
        if content_type != "text/plain" or is_attachment_part(part):
            continue
        try:
            text = part.get_content()
        except Exception:
            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
        chunks.append(str(text))
        if sum(len(c.encode("utf-8")) for c in chunks) >= max_bytes:
            break
    text = "\n".join(chunks)
    return text.encode("utf-8")[:max_bytes].decode("utf-8", errors="replace")


def safe_attachment_name(filename: str | None, attachment_id: int) -> str:
    name = unicodedata.normalize("NFC", decode_text(filename))
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(
        "_" if unicodedata.category(char).startswith("C") or char in '<>:"|?*' else char
        for char in name
    ).strip().strip(". ")
    # Leave room for collision suffixes within common filesystem name limits.
    while len(name.encode("utf-8")) > 200:
        name = name[:-1]
    if not name:
        name = f"attachment-{attachment_id}"
    if name.split(".", 1)[0].upper() in {
        "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }:
        name = "_" + name
    return name


def attachment_bytes(part: Message) -> bytes:
    data = part.get_payload(decode=True)
    if any(isinstance(defect, (InvalidBase64CharactersDefect, InvalidBase64LengthDefect,
                              InvalidBase64PaddingDefect)) for defect in part.defects):
        fail("Corrupt Base64 attachment; refusing to save repaired or undecoded data.")
    if data is not None:
        return data
    children = part.get_payload()
    if part.get_content_type() == "message/rfc822" and isinstance(children, list):
        if len(children) != 1:
            fail("Invalid attached email: expected one embedded message.")
        transfer_encoding = str(part.get("Content-Transfer-Encoding", "")).lower().strip()
        if transfer_encoding in ("base64", "quoted-printable"):
            encoded = children[0].get_payload()
            if not isinstance(encoded, str) or children[0].items():
                fail("Invalid transfer-encoded email attachment.")
            try:
                raw = encoded.encode("ascii", errors="surrogateescape")
                if transfer_encoding == "base64":
                    return base64.b64decode(b"".join(raw.split()), validate=True)
                return quopri.decodestring(raw)
            except (UnicodeError, binascii.Error):
                fail("Invalid transfer-encoded email attachment.")
        # Preserve the complete embedded MIME structure; line endings become CRLF.
        return children[0].as_bytes(policy=policy.SMTP.clone(refold_source="none"))
    if part.is_multipart():
        return part.as_bytes(policy=policy.SMTP.clone(refold_source="none"))
    return b""


def message_attachments(msg: Message) -> list[tuple[dict[str, Any], bytes]]:
    attachments = []
    used_names: set[str] = set()
    for part in content_parts(msg):
        if not is_attachment_part(part):
            continue
        attachment_id = len(attachments) + 1
        name = safe_attachment_name(part.get_filename(), attachment_id)
        original = Path(name)
        sequence = 2
        while name.casefold() in used_names:
            name = f"{original.stem}-{sequence}{original.suffix}"
            sequence += 1
        used_names.add(name.casefold())
        data = attachment_bytes(part)
        metadata = {
            "id": attachment_id,
            "filename": name,
            "content_type": part.get_content_type(),
            "size": len(data),
            "disposition": part.get_content_disposition() or "attachment",
            "content_id": decode_text(part.get("Content-ID")) or None,
        }
        attachments.append((metadata, data))
    return attachments


def check_attachment_limit(attachments: list[tuple[dict[str, Any], bytes]], limit: int) -> None:
    if sum(len(data) for _, data in attachments) > limit:
        fail(f"Attachments exceed --max-attachment-bytes ({limit}).")


def fetch_attachment_message(args: argparse.Namespace) -> Message:
    if not re.fullmatch(r"[1-9][0-9]*", args.uid):
        fail("--uid must be one positive numeric message UID.")
    client = imap_connect(args)
    try:
        select_folder(client, args.folder, readonly=True)
        status, data = client.uid("FETCH", args.uid, "(RFC822.SIZE)")
        response = b" ".join(item for item in (data or []) if isinstance(item, bytes))
        size_match = re.search(rb"\bRFC822\.SIZE\s+([0-9]+)", response, re.IGNORECASE)
        if status != "OK" or not size_match:
            fail("Could not read message size. Check the UID and folder.")
        expected_size = int(size_match.group(1))
        if expected_size > args.max_message_bytes:
            fail(f"Message exceeds --max-message-bytes ({args.max_message_bytes}).")
        # Request a bounded partial body even if the server misreports its size.
        status, data = client.uid("FETCH", args.uid,
                                  f"(BODY.PEEK[]<0.{args.max_message_bytes + 1}>)")
        if status != "OK":
            fail("IMAP attachment FETCH failed.")
        raw = first_literal(data or [])
        if not raw:
            fail("Message was not found or its body is empty.")
        if len(raw) > args.max_message_bytes:
            fail(f"Message exceeds --max-message-bytes ({args.max_message_bytes}).")
        if len(raw) != expected_size:
            fail("Fetched message size does not match RFC822.SIZE; refusing incomplete data.")
        return BytesParser(policy=policy.default).parsebytes(raw)
    finally:
        client.logout()


def cmd_imap_attachments(args: argparse.Namespace) -> None:
    attachments = message_attachments(fetch_attachment_message(args))
    check_attachment_limit(attachments, args.max_attachment_bytes)
    emit({"ok": True, "uid": args.uid,
          "attachments": [metadata for metadata, _ in attachments]})


def cmd_imap_download(args: argparse.Namespace) -> None:
    attachments = message_attachments(fetch_attachment_message(args))
    if args.attachment_id:
        requested = set(args.attachment_id)
        unknown = requested - {metadata["id"] for metadata, _ in attachments}
        if unknown:
            fail(f"Unknown attachment IDs: {', '.join(map(str, sorted(unknown)))}.")
        attachments = [(metadata, data) for metadata, data in attachments
                       if metadata["id"] in requested]
    check_attachment_limit(attachments, args.max_attachment_bytes)
    if not attachments:
        emit({"ok": True, "uid": args.uid, "saved": []})
        return
    output = Path(args.output_dir).expanduser().resolve()
    created: list[tuple[str, int]] = []
    directory_fd = None
    try:
        output.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
        # Preflight all destinations before writing any file, including dangling symlinks.
        for metadata, _ in attachments:
            try:
                os.stat(metadata["filename"], dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            fail(f"Refusing to overwrite existing path: {output / metadata['filename']}")
        saved = []
        for metadata, data in attachments:
            fd = os.open(metadata["filename"], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=directory_fd)
            created.append((metadata["filename"], os.fstat(fd).st_ino))
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
            saved.append({**metadata, "path": str(output / metadata["filename"])})
    except OSError as exc:
        # Roll back only the files this invocation created, never somebody else's replacement.
        for name, inode in created:
            try:
                if os.stat(name, dir_fd=directory_fd, follow_symlinks=False).st_ino == inode:
                    os.unlink(name, dir_fd=directory_fd)
            except OSError:
                pass
        fail(f"Could not save attachments: {exc}")
    finally:
        if directory_fd is not None:
            os.close(directory_fd)
    emit({"ok": True, "uid": args.uid, "saved": saved})


def imap_connect(args: argparse.Namespace) -> imaplib.IMAP4:
    host = require(connection_value(args, "imap_host", "IMAP_HOST", "imap_host"), "IMAP host")
    port = int(connection_value(args, "imap_port", "IMAP_PORT", "imap_port", 993))
    if not 1 <= port <= 65535:
        raise ValueError("IMAP port must be between 1 and 65535.")
    username = require(mailbox_username(args), "username")
    password = password_value(args)
    security = connection_value(args, "imap_security", "IMAP_SECURITY", "imap_security", "ssl")
    context = ssl.create_default_context()

    if security == "ssl":
        client: imaplib.IMAP4 = imaplib.IMAP4_SSL(host, port, ssl_context=context, timeout=args.timeout)
    else:
        client = imaplib.IMAP4(host, port, timeout=args.timeout)
        if security == "starttls":
            client.starttls(ssl_context=context)

    status, _ = client.login(username, password)
    if status != "OK":
        fail("IMAP login failed.")
    return client


def smtp_connect(args: argparse.Namespace) -> smtplib.SMTP:
    host = require(connection_value(args, "smtp_host", "SMTP_HOST", "smtp_host"), "SMTP host")
    port = int(connection_value(args, "smtp_port", "SMTP_PORT", "smtp_port", 465))
    if not 1 <= port <= 65535:
        raise ValueError("SMTP port must be between 1 and 65535.")
    username = require(mailbox_username(args), "username")
    password = password_value(args)
    security = connection_value(args, "smtp_security", "SMTP_SECURITY", "smtp_security", "auto")
    context = ssl.create_default_context()

    if security == "auto":
        security = "ssl" if port == 465 else "starttls"

    if security == "ssl":
        client: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=args.timeout, context=context)
    else:
        client = smtplib.SMTP(host, port, timeout=args.timeout)
        if security == "starttls":
            client.starttls(context=context)

    client.login(username, password)
    return client


def cmd_providers(args: argparse.Namespace) -> None:
    providers = []
    for key, profile in sorted(PROVIDER_PROFILES.items()):
        providers.append({
            "provider": key,
            "name": profile["name"],
            "domains": profile.get("domains", []),
            "imap": {
                "host": profile.get("imap_host"),
                "port": profile.get("imap_port"),
                "security": profile.get("imap_security"),
            },
            "smtp": {
                "host": profile.get("smtp_host"),
                "port": profile.get("smtp_port"),
                "security": profile.get("smtp_security"),
            },
            "setup_url": profile.get("setup_url"),
            "credential": profile.get("credential"),
        })
    emit({"ok": True, "providers": providers})


def shell_quote(value: Any) -> str:
    text = str(value)
    return "'" + text.replace("'", "'\"'\"'") + "'"


def cmd_profile(args: argparse.Namespace) -> None:
    email_address = args.email or mailbox_username(args)
    provider = detect_provider(email_address, getattr(args, "provider", None))
    if not provider:
        fail("Could not infer provider. Pass --provider or set MAIL_PROVIDER.")
    profile = PROVIDER_PROFILES[provider]
    payload = {
        "ok": True,
        "provider": provider,
        "email": email_address,
        "name": profile["name"],
        "setup_url": profile.get("setup_url"),
        "credential": profile.get("credential"),
        "env": {
            "MAIL_USERNAME": email_address,
            "MAIL_PROVIDER": provider,
            "IMAP_HOST": profile.get("imap_host"),
            "IMAP_PORT": str(profile.get("imap_port")),
            "IMAP_SECURITY": profile.get("imap_security"),
            "SMTP_HOST": profile.get("smtp_host"),
            "SMTP_PORT": str(profile.get("smtp_port")),
            "SMTP_SECURITY": profile.get("smtp_security"),
        },
    }
    if args.shell:
        lines = []
        for key, value in payload["env"].items():
            if value:
                lines.append(f"export {key}={shell_quote(value)}")
        payload["shell"] = "\n".join(lines)
    emit(payload)


def read_password_for_save(args: argparse.Namespace) -> str:
    if args.password_stdin:
        value = sys.stdin.read()
        value = value.rstrip("\r\n")
    else:
        value = os.environ.get(args.password_env, "")
    if not value:
        fail(
            f"Missing secret. Set ${args.password_env} before auth-save, "
            "or pass --password-stdin and provide the secret on stdin."
        )
    return value


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def auth_arg_value(args: argparse.Namespace, attr: str, env_name: str, profile: dict[str, Any], profile_key: str) -> Any:
    value = getattr(args, attr, None)
    if value not in (None, ""):
        return value
    env_value = os.environ.get(env_name)
    if env_value not in (None, ""):
        return env_value
    return profile.get(profile_key)


def auth_save_value(
    args: argparse.Namespace,
    attr: str,
    env_name: str,
    previous: dict[str, Any],
    profile: dict[str, Any],
    profile_key: str,
) -> Any:
    value = getattr(args, attr, None)
    if value not in (None, ""):
        return value
    env_value = os.environ.get(env_name)
    if env_value not in (None, ""):
        return env_value
    if previous.get(profile_key) not in (None, ""):
        return previous.get(profile_key)
    return profile.get(profile_key)


def cmd_auth_path(args: argparse.Namespace) -> None:
    paths = auth_paths(create=args.create)
    emit({
        "ok": True,
        "mode": paths["mode"],
        "auth_root_env": AUTH_STORE_ENV,
        "root": str(paths["root"]),
        "auth_dir": str(paths["auth_dir"]),
        "store_file": str(paths["store_file"]),
        "secrets_dir": str(paths["secrets_dir"]),
        "encryption": "openssl aes-256-cbc pbkdf2",
        "store_exists": paths["store_file"].exists(),
    })


def cmd_auth_list(args: argparse.Namespace) -> None:
    paths = auth_paths(create=False)
    data = load_auth_store(create=False)
    accounts = [account_public(account) for account in data.get("accounts", {}).values()]
    accounts.sort(key=lambda item: str(item.get("email") or ""))
    emit({
        "ok": True,
        "mode": paths["mode"],
        "auth_dir": str(paths["auth_dir"]),
        "count": len(accounts),
        "accounts": accounts,
    })


def cmd_auth_check(args: argparse.Namespace) -> None:
    paths = auth_paths(create=False)
    data, notes = load_auth_store_readonly()
    summary = secret_store_summary(data.get("accounts", {}))
    accounts = [
        account_public(account, metadata_only=True)
        for account in data.get("accounts", {}).values()
        if isinstance(account, dict)
    ]
    accounts.sort(key=lambda item: str(item.get("email") or ""))
    broken_accounts = [
        item for item in accounts
        if (
            item.get("secret_storage") not in ("encrypted", "encrypted_unverified", "legacy_plaintext")
            or not item.get("imap_host")
            or not item.get("imap_port")
            or not item.get("smtp_host")
            or not item.get("smtp_port")
        )
    ]
    emit({
        "ok": not broken_accounts,
        "mode": paths["mode"],
        "auth_dir": str(paths["auth_dir"]),
        "store_exists": notes["store_exists"],
        "count": len(accounts),
        "usable_count": len(accounts) - len(broken_accounts),
        "requires_attention": bool(broken_accounts),
        "read_only": True,
        "decrypted": False,
        "wrote_files": False,
        "legacy_list_format": notes["legacy_list_format"],
        "repaired_in_memory": notes["repaired_in_memory"],
        "secret_file_count": summary["secret_file_count"],
        "referenced_secret_count": summary["referenced_secret_count"],
        "orphan_secret_count": summary["orphan_secret_count"],
        "store_drift": summary["store_drift"],
        "accounts": accounts,
    })


def cmd_auth_save(args: argparse.Namespace) -> None:
    email_address = normalize_email(args.email or mailbox_username(args))
    password = read_password_for_save(args)
    with auth_store_lock(create=True):
        data = load_auth_store_unlocked(create=True)
        accounts = data.setdefault("accounts", {})
        previous = accounts.get(email_address, {}) if isinstance(accounts.get(email_address, {}), dict) else {}
        provider_hint = getattr(args, "provider", None)
        provider = (
            detect_provider(email_address, provider_hint)
            or (provider_hint if provider_hint != "auto" else None)
            or previous.get("provider")
        )
        profile = PROVIDER_PROFILES.get(provider or "", {})
        created_at = previous.get("created_at") or now_iso()
        credential = args.credential or profile.get("credential") or "app password or authorization code"
        secret_file = encrypt_secret(email_address, password)

        account = {
            "email": email_address,
            "provider": provider,
            "credential": credential,
            "secret_file": secret_file,
            "imap_host": auth_save_value(args, "imap_host", "IMAP_HOST", previous, profile, "imap_host"),
            "imap_port": auth_save_value(args, "imap_port", "IMAP_PORT", previous, profile, "imap_port"),
            "imap_security": auth_save_value(args, "imap_security", "IMAP_SECURITY", previous, profile, "imap_security"),
            "smtp_host": auth_save_value(args, "smtp_host", "SMTP_HOST", previous, profile, "smtp_host"),
            "smtp_port": auth_save_value(args, "smtp_port", "SMTP_PORT", previous, profile, "smtp_port"),
            "smtp_security": auth_save_value(args, "smtp_security", "SMTP_SECURITY", previous, profile, "smtp_security"),
            "setup_url": profile.get("setup_url") or previous.get("setup_url"),
            "created_at": created_at,
            "updated_at": now_iso(),
        }
        accounts[email_address] = account
        save_auth_store_unlocked(data)

    paths = auth_paths(create=False)
    emit({
        "ok": True,
        "saved": account_public(account),
        "auth_dir": str(paths["auth_dir"]),
        "note": "Secret was saved but not printed.",
    })


def cmd_auth_delete(args: argparse.Namespace) -> None:
    if args.confirm_delete != "yes":
        fail("This removes stored mailbox credentials. Re-run with --confirm-delete yes.")
    with auth_store_lock(create=True):
        data = load_auth_store_unlocked(create=True)
        accounts = data.setdefault("accounts", {})
        if args.all:
            count = len(accounts)
            paths = auth_paths(create=False)
            auth_dir: Path = paths["auth_dir"]
            if auth_dir.exists():
                shutil.rmtree(auth_dir)
            emit({"ok": True, "deleted": count, "cleared_auth_dir": str(auth_dir)})
            return
        email_address = normalize_email(args.email)
        account = accounts.pop(email_address, None)
        existed = isinstance(account, dict)
        if existed:
            delete_secret_file(account)
        save_auth_store_unlocked(data)
    emit({"ok": True, "email": email_address, "deleted": existed})


def cmd_auth_clear(args: argparse.Namespace) -> None:
    if args.confirm_delete != "yes":
        fail("This removes all Email plugin credentials. Re-run with --confirm-delete yes.")
    with auth_store_lock(create=True):
        paths = auth_paths(create=False)
        auth_dir: Path = paths["auth_dir"]
        existed = auth_dir.exists()
        if existed:
            shutil.rmtree(auth_dir)
    emit({"ok": True, "cleared": existed, "auth_dir": str(auth_dir)})


def cmd_auth_restore(args: argparse.Namespace) -> None:
    with auth_store_lock(create=True):
        paths = auth_paths(create=False)
        data = load_auth_store_unlocked(create=True)
        accounts = data.setdefault("accounts", {})
        changed = False
        migrated = 0
        for email_address, account in list(accounts.items()):
            if not isinstance(account, dict):
                continue
            if account.get("password") and not account.get("secret_file"):
                account["secret_file"] = encrypt_secret(email_address, str(account["password"]))
                account.pop("password", None)
                account["updated_at"] = now_iso()
                changed = True
                migrated += 1
        if changed:
            save_auth_store_unlocked(data)
    public_accounts = [account_public(account, verify_secret=True) for account in accounts.values() if isinstance(account, dict)]
    public_accounts.sort(key=lambda item: str(item.get("email") or ""))
    broken_accounts = [
        item for item in public_accounts
        if (
            item.get("secret_storage") not in ("encrypted", "legacy_plaintext")
            or not item.get("imap_host")
            or not item.get("imap_port")
            or not item.get("smtp_host")
            or not item.get("smtp_port")
        )
    ]
    emit({
        "ok": not broken_accounts,
        "mode": paths["mode"],
        "auth_dir": str(paths["auth_dir"]),
        "count": len(public_accounts),
        "usable_count": len(public_accounts) - len(broken_accounts),
        "requires_attention": bool(broken_accounts),
        "migrated_legacy_plaintext": migrated,
        "accounts": public_accounts,
    })


def cmd_auth_env(args: argparse.Namespace) -> None:
    email_address = normalize_email(args.email or mailbox_username(args))
    account = stored_account(email_address)
    if not account:
        fail("No stored account found for that email.")
    env = {
        "MAIL_USERNAME": email_address,
        "MAIL_PROVIDER": account.get("provider"),
        "IMAP_HOST": account.get("imap_host"),
        "IMAP_PORT": str(account.get("imap_port") or ""),
        "IMAP_SECURITY": account.get("imap_security"),
        "SMTP_HOST": account.get("smtp_host"),
        "SMTP_PORT": str(account.get("smtp_port") or ""),
        "SMTP_SECURITY": account.get("smtp_security"),
    }
    payload: dict[str, Any] = {"ok": True, "email": email_address, "env": env, "contains_password": False}
    if args.shell:
        lines = []
        for key, value in env.items():
            if value:
                lines.append(f"export {key}={shell_quote(value)}")
        payload["shell"] = "\n".join(lines)
    emit(payload)


def cmd_imap_test(args: argparse.Namespace) -> None:
    client = imap_connect(args)
    try:
        status, folders = client.list()
        if status != "OK":
            fail("IMAP LIST failed.")
        emit({
            "ok": True,
            "command": "imap-test",
            "folders_sample": [decode_text(line) for line in (folders or [])[:5]],
            "capabilities": [decode_text(item) for item in getattr(client, "capabilities", [])],
        })
    finally:
        client.logout()


def cmd_imap_list(args: argparse.Namespace) -> None:
    client = imap_connect(args)
    try:
        status, folders = client.list()
        if status != "OK":
            fail("IMAP LIST failed.")
        emit({"ok": True, "folders": [decode_text(line) for line in folders or []]})
    finally:
        client.logout()


def select_folder(client: imaplib.IMAP4, folder: str, readonly: bool) -> None:
    status, _ = client.select(folder, readonly=readonly)
    if status != "OK":
        fail(f"Could not select folder: {folder}")


def cmd_imap_search(args: argparse.Namespace) -> None:
    client = imap_connect(args)
    try:
        select_folder(client, args.folder, readonly=True)
        status, data = client.uid("SEARCH", None, args.criteria)
        if status != "OK":
            fail("IMAP SEARCH failed.")
        uids = (data[0] or b"").decode("ascii", errors="ignore").split()
        selected = uids[-args.limit :] if args.limit else uids
        messages = []
        for uid in selected:
            status, fetched = client.uid(
                "FETCH",
                uid,
                "(BODY.PEEK[HEADER.FIELDS (FROM TO CC SUBJECT DATE MESSAGE-ID)])",
            )
            if status != "OK":
                fail(f"IMAP header FETCH failed for UID {uid}.")
            messages.append({"uid": uid, "headers": message_headers(first_literal(fetched))})
        emit({"ok": True, "count": len(uids), "returned": len(messages), "messages": messages})
    finally:
        client.logout()


def cmd_imap_recent(args: argparse.Namespace) -> None:
    since = (date.today() - timedelta(days=args.days)).strftime("%d-%b-%Y")
    args.criteria = f"SINCE {since}"
    cmd_imap_search(args)


def cmd_imap_fetch(args: argparse.Namespace) -> None:
    client = imap_connect(args)
    try:
        select_folder(client, args.folder, readonly=True)
        query = "(BODY.PEEK[])" if args.body else "(BODY.PEEK[HEADER])"
        status, data = client.uid("FETCH", args.uid, query)
        if status != "OK":
            fail("IMAP FETCH failed.")
        raw = first_literal(data)
        if not raw:
            fail("IMAP FETCH returned no message data.")
        msg = BytesParser(policy=policy.default).parsebytes(raw)
        payload: dict[str, Any] = {"ok": True, "uid": args.uid, "headers": message_headers(raw)}
        if args.body:
            payload["text"] = extract_text(msg, args.max_bytes)
        emit(payload)
    finally:
        client.logout()


def uid_set(uids: list[str]) -> str:
    cleaned = [uid.strip() for uid in uids if uid.strip()]
    if not cleaned:
        fail("At least one UID is required.")
    return ",".join(cleaned)


def require_write_confirmation(args: argparse.Namespace) -> None:
    if args.confirm_write != "yes":
        fail("This changes mailbox state. Re-run with --confirm-write yes.")


def cmd_imap_mark_read(args: argparse.Namespace) -> None:
    require_write_confirmation(args)
    client = imap_connect(args)
    try:
        select_folder(client, args.folder, readonly=False)
        status, _ = client.uid("STORE", uid_set(args.uids), "+FLAGS.SILENT", r"(\Seen)")
        if status != "OK":
            fail("IMAP STORE failed.")
        emit({"ok": True, "marked_read": args.uids})
    finally:
        client.logout()


def cmd_imap_move(args: argparse.Namespace) -> None:
    require_write_confirmation(args)
    client = imap_connect(args)
    try:
        select_folder(client, args.folder, readonly=False)
        status, _ = client.uid("MOVE", uid_set(args.uids), args.target_folder)
        if status != "OK":
            fail("IMAP MOVE failed. Server may not support MOVE; use a provider UI or add COPY+DELETE deliberately.")
        emit({"ok": True, "moved": args.uids, "target_folder": args.target_folder})
    finally:
        client.logout()


def cmd_smtp_test(args: argparse.Namespace) -> None:
    client = smtp_connect(args)
    try:
        code, response = client.noop()
        emit({"ok": 200 <= code < 400, "command": "smtp-test", "code": code, "response": decode_text(response)})
    finally:
        client.quit()


def cmd_smtp_send(args: argparse.Namespace) -> None:
    if args.confirm_send != "yes":
        fail("This sends email. Re-run with --confirm-send yes.")

    username = require(args.username or env_first("MAIL_USERNAME", "MAIL_EMAIL"), "username")
    sender = args.from_addr or env_first("MAIL_FROM") or username
    text = args.text if args.text is not None else sys.stdin.read()
    if not text:
        fail("Missing message text. Pass --text or pipe stdin.")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(args.to)
    msg["Subject"] = args.subject
    msg.set_content(text)

    attachments = []
    total_bytes = 0
    for value in args.attach:
        path = Path(value).expanduser()
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            with os.fdopen(fd, "rb") as fh:
                if not stat.S_ISREG(os.fstat(fh.fileno()).st_mode):
                    fail(f"Attachment is not a regular file: {path}")
                data = fh.read(args.max_attachment_bytes - total_bytes + 1)
        except OSError as exc:
            fail(f"Could not read attachment {path}: {exc}")
        total_bytes += len(data)
        if total_bytes > args.max_attachment_bytes:
            fail(f"Attachments exceed --max-attachment-bytes ({args.max_attachment_bytes}).")
        content_type, encoding = mimetypes.guess_type(path.name)
        if not content_type or encoding:
            content_type = "application/octet-stream"
        maintype, subtype = content_type.split("/", 1)
        if content_type == "message/rfc822":
            embedded = BytesParser(policy=policy.default).parsebytes(data)
            msg.add_attachment(embedded, filename=path.name)
        else:
            # Generic message/* files must not be sent with base64 as that MIME type.
            if maintype == "message":
                maintype, subtype = "application", "octet-stream"
                content_type = "application/octet-stream"
            msg.add_attachment(data, maintype=maintype, subtype=subtype,
                               filename=path.name, cte="base64")
        attachments.append({"filename": path.name, "content_type": content_type, "size": len(data)})

    client = smtp_connect(args)
    try:
        refused = client.send_message(msg)
        sent: dict[str, Any] = {"from": sender, "to": args.to, "subject": args.subject}
        if attachments:
            sent["attachments"] = attachments
        if refused:
            sent["refused"] = {
                address: {"code": code, "response": decode_text(response)}
                for address, (code, response) in refused.items()
            }
        emit({"ok": True, "sent": sent})
    finally:
        client.quit()


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Expected a positive integer.") from None
    if number <= 0:
        raise argparse.ArgumentTypeError("Expected a positive integer.")
    return number


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--username", help="Mailbox username. Defaults to $MAIL_USERNAME or $MAIL_EMAIL.")
    parser.add_argument("--provider", default=argparse.SUPPRESS, help="Provider key or auto. Defaults to $MAIL_PROVIDER or auto.")
    parser.add_argument("--password-env", default="MAIL_PASSWORD", help="Env var containing app password/auth code.")
    parser.add_argument("--timeout", type=float, default=30, help="Network timeout in seconds.")


def add_imap(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--imap-host", help="IMAP host. Defaults to $IMAP_HOST.")
    parser.add_argument("--imap-port", type=int, help="IMAP port. Defaults to $IMAP_PORT or 993.")
    parser.add_argument("--imap-security", choices=("ssl", "starttls", "plain"))
    parser.add_argument("--provider", default=argparse.SUPPRESS, help="Provider key or auto. Defaults to $MAIL_PROVIDER or auto.")


def add_smtp(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--smtp-host", help="SMTP host. Defaults to $SMTP_HOST.")
    parser.add_argument("--smtp-port", type=int, help="SMTP port. Defaults to $SMTP_PORT or 465.")
    parser.add_argument("--smtp-security", choices=("auto", "ssl", "starttls", "plain"))
    parser.add_argument("--provider", default=argparse.SUPPRESS, help="Provider key or auto. Defaults to $MAIL_PROVIDER or auto.")


def add_attachment_imap(parser: argparse.ArgumentParser) -> None:
    add_imap(parser)
    parser.add_argument("--folder", default="INBOX")
    parser.add_argument("--uid", required=True, help="One numeric message UID.")
    parser.add_argument("--max-message-bytes", type=positive_int,
                        default=DEFAULT_MAX_MESSAGE_BYTES,
                        help="Maximum raw email bytes to fetch (default: 50 MiB).")
    parser.add_argument("--max-attachment-bytes", type=positive_int,
                        default=DEFAULT_MAX_ATTACHMENT_BYTES,
                        help="Maximum combined decoded attachment bytes (default: 25 MiB).")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operate an IMAP/SMTP mailbox using env-held credentials.")
    add_common(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("providers", help="List built-in provider profiles.")
    p.set_defaults(func=cmd_providers)

    p = sub.add_parser("profile", help="Infer host/port settings for one email address.")
    p.add_argument("--email", help="Mailbox address. Defaults to $MAIL_USERNAME or $MAIL_EMAIL.")
    p.add_argument("--provider", default=argparse.SUPPRESS, help="Provider key or auto. Use for custom enterprise domains.")
    p.add_argument("--shell", action="store_true", help="Include export commands in JSON output.")
    p.set_defaults(func=cmd_profile)

    p = sub.add_parser("auth-path", help="Show the selected persistent auth directory.")
    p.add_argument("--create", action="store_true", help="Create the auth directory if missing.")
    p.set_defaults(func=cmd_auth_path)

    p = sub.add_parser("auth-list", help="List stored mailbox accounts without printing secrets.")
    p.set_defaults(func=cmd_auth_list)

    p = sub.add_parser("auth-check", help="Read-only saved-account preflight; does not decrypt, migrate, or write files.")
    p.set_defaults(func=cmd_auth_check)

    p = sub.add_parser("auth-restore", help="Preflight stored accounts for a new conversation; migrates legacy plaintext records.")
    p.set_defaults(func=cmd_auth_restore)

    p = sub.add_parser("auth-save", help="Save one mailbox app password/authorization code in the plugin auth store.")
    p.add_argument("--email", help="Mailbox address. Defaults to $MAIL_USERNAME or $MAIL_EMAIL.")
    p.add_argument("--provider", default="auto", help="Provider key or auto. Use for custom enterprise domains.")
    p.add_argument("--credential", help="Human label for the credential type.")
    p.add_argument("--password-env", default="MAIL_PASSWORD", help="Env var containing app password/auth code.")
    p.add_argument("--password-stdin", action="store_true", help="Read app password/auth code from stdin.")
    p.add_argument("--imap-host", help="IMAP host. Defaults to inferred provider or $IMAP_HOST.")
    p.add_argument("--imap-port", type=int, help="IMAP port. Defaults to inferred provider or $IMAP_PORT.")
    p.add_argument("--imap-security", choices=("ssl", "starttls", "plain"))
    p.add_argument("--smtp-host", help="SMTP host. Defaults to inferred provider or $SMTP_HOST.")
    p.add_argument("--smtp-port", type=int, help="SMTP port. Defaults to inferred provider or $SMTP_PORT.")
    p.add_argument("--smtp-security", choices=("auto", "ssl", "starttls", "plain"))
    p.set_defaults(func=cmd_auth_save)

    p = sub.add_parser("auth-env", help="Print non-secret env values for a stored mailbox.")
    p.add_argument("--email", help="Mailbox address. Defaults to $MAIL_USERNAME or $MAIL_EMAIL.")
    p.add_argument("--shell", action="store_true", help="Include export commands in JSON output.")
    p.set_defaults(func=cmd_auth_env)

    p = sub.add_parser("auth-delete", help="Delete stored mailbox credentials.")
    p.add_argument("--email", help="Mailbox address to remove.")
    p.add_argument("--all", action="store_true", help="Remove every stored mailbox account.")
    p.add_argument("--confirm-delete")
    p.set_defaults(func=cmd_auth_delete)

    p = sub.add_parser("auth-clear", help="Delete the whole Email plugin auth directory for plugin uninstall/disconnect.")
    p.add_argument("--confirm-delete")
    p.set_defaults(func=cmd_auth_clear)

    p = sub.add_parser("imap-test", help="Login and list a few folders.")
    add_imap(p)
    p.set_defaults(func=cmd_imap_test)

    p = sub.add_parser("imap-list", help="List IMAP folders.")
    add_imap(p)
    p.set_defaults(func=cmd_imap_list)

    p = sub.add_parser("imap-search", help='Search a folder, e.g. --criteria "UNSEEN SINCE 12-Jun-2026".')
    add_imap(p)
    p.add_argument("--folder", default="INBOX")
    p.add_argument("--criteria", default="ALL", help="Raw IMAP SEARCH criteria.")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_imap_search)

    p = sub.add_parser("imap-recent", help="Search recent messages by day window.")
    add_imap(p)
    p.add_argument("--folder", default="INBOX")
    p.add_argument("--days", type=int, default=3)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_imap_recent)

    p = sub.add_parser("imap-fetch", help="Fetch headers or text for one UID.")
    add_imap(p)
    p.add_argument("--folder", default="INBOX")
    p.add_argument("--uid", required=True)
    p.add_argument("--body", action="store_true", help="Include text/plain body.")
    p.add_argument("--max-bytes", type=int, default=20000)
    p.set_defaults(func=cmd_imap_fetch)

    p = sub.add_parser("imap-attachments", help="List attachments and inline files without marking mail read.")
    add_attachment_imap(p)
    p.set_defaults(func=cmd_imap_attachments)

    p = sub.add_parser("imap-download", help="Save selected or all attachments; never overwrite existing files.")
    add_attachment_imap(p)
    p.add_argument("--output-dir", required=True, help="Directory for saved attachments.")
    p.add_argument("--attachment-id", type=positive_int, action="append",
                   help="ID from imap-attachments. Repeat to select files; omit to save all.")
    p.set_defaults(func=cmd_imap_download)

    p = sub.add_parser("imap-mark-read", help="Mark one or more UIDs as read.")
    add_imap(p)
    p.add_argument("--folder", default="INBOX")
    p.add_argument("--uid", dest="uids", action="append", required=True)
    p.add_argument("--confirm-write")
    p.set_defaults(func=cmd_imap_mark_read)

    p = sub.add_parser("imap-move", help="Move one or more UIDs to another folder if server supports MOVE.")
    add_imap(p)
    p.add_argument("--folder", default="INBOX")
    p.add_argument("--uid", dest="uids", action="append", required=True)
    p.add_argument("--target-folder", required=True)
    p.add_argument("--confirm-write")
    p.set_defaults(func=cmd_imap_move)

    p = sub.add_parser("smtp-test", help="Login to SMTP and run NOOP.")
    add_smtp(p)
    p.set_defaults(func=cmd_smtp_test)

    p = sub.add_parser("smtp-send", help="Send an email. Requires --confirm-send yes.")
    add_smtp(p)
    p.add_argument("--from", dest="from_addr")
    p.add_argument("--to", action="append", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--text")
    p.add_argument("--attach", action="append", default=[], metavar="PATH",
                   help="Attach a local file. Repeat for multiple files.")
    p.add_argument("--max-attachment-bytes", type=positive_int,
                   default=DEFAULT_MAX_ATTACHMENT_BYTES,
                   help="Maximum combined attachment bytes before encoding (default: 25 MiB).")
    p.add_argument("--confirm-send")
    p.set_defaults(func=cmd_smtp_send)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
        return 0
    except imaplib.IMAP4.error as exc:
        emit({"ok": False, "error": f"IMAP error: {exc}"})
        return 1
    except smtplib.SMTPException as exc:
        emit({"ok": False, "error": f"SMTP error: {exc}"})
        return 1
    except TimeoutError as exc:
        emit({"ok": False, "error": f"Timeout: {exc}"})
        return 1
    except RecursionError:
        emit({"ok": False, "error": "Email MIME nesting is too deep to process safely."})
        return 1
    except OSError as exc:
        emit({"ok": False, "error": f"I/O error: {exc}"})
        return 1
    except (ValueError, OverflowError) as exc:
        emit({"ok": False, "error": f"Invalid configuration or input: {exc}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
