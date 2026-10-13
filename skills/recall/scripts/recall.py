#!/usr/bin/env python3
"""Mine local agent chat transcripts (Claude Code, Codex, Pi) for recent working context.

Standard library only. Read-only: never writes to the transcript stores.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOURCES = ("claude", "codex", "pi")
DEFAULT_ROOTS = {
    "claude": ("RECALL_CLAUDE_ROOT", "~/.claude/projects"),
    "codex": ("RECALL_CODEX_ROOT", "~/.codex/sessions"),
    "pi": ("RECALL_PI_ROOT", "~/.pi/agent/sessions"),
}
FIRST_MESSAGE_CHARS = 120
USER_TURN_CHARS = 700
FINAL_TURN_CHARS = 1500
# Codex thread_source values that can hold the user's own conversation. An
# "agent_created_thread" counts only when it has real user messages (see parse_codex).
TOP_LEVEL_CODEX_SOURCES = (None, "user", "agent_created_thread")

# ---------------------------------------------------------------- redaction

_SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?(?:-----END [A-Z0-9 ]*PRIVATE KEY-----|\Z)", re.DOTALL),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[abpr]-[A-Za-z0-9-]{10,}"),
]
_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9._~+/=-]{8,}")


def redact(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return _BEARER.sub(r"\1[REDACTED]", text)


def redact_obj(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [redact_obj(v) for v in value]
    if isinstance(value, dict):
        return {k: redact_obj(v) for k, v in value.items()}
    return value


# ---------------------------------------------------------------- errors


class RecallError(Exception):
    """A user-facing error whose message says what to do instead."""


# ---------------------------------------------------------------- time


def parse_ts(value) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def parse_bound(value: str, flag: str, end_of_day: bool) -> datetime | None:
    value = value.strip()
    if value.lower() == "all":
        return None
    match = re.fullmatch(r"(\d+)([hdw])", value)
    if match:
        unit = {"h": "hours", "d": "days", "w": "weeks"}[match.group(2)]
        return datetime.now(timezone.utc) - timedelta(**{unit: int(match.group(1))})
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        day = datetime.strptime(value, "%Y-%m-%d").astimezone()
        return day + timedelta(days=1) if end_of_day else day
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise RecallError(
            f"{flag} {value!r} is not a time. Use a relative span (7d, 12h, 2w), "
            "a local date (2026-09-30), an ISO datetime, or 'all' for no bound."
        ) from None
    return dt if dt.tzinfo else dt.astimezone()


def fmt_local(dt: datetime | None) -> str:
    return dt.astimezone().strftime("%Y-%m-%d %H:%M") if dt else "?"


def fmt_iso(dt: datetime | None) -> str | None:
    return dt.astimezone().isoformat(timespec="seconds") if dt else None


# ---------------------------------------------------------------- model


@dataclass
class Turn:
    time: datetime | None
    user: str
    final: str = ""


@dataclass
class Session:
    source: str
    id: str
    paths: list[Path]
    cwd: str = ""
    branch: str = ""
    repo_url: str = ""
    subagent: bool = False
    start: datetime | None = None
    end: datetime | None = None
    raw_messages: int = 0
    message_like: int = 0
    turns: list[Turn] = field(default_factory=list)
    tool_texts: list[str] = field(default_factory=list)

    def touch(self, ts: datetime | None) -> None:
        if ts is None:
            return
        if self.start is None or ts < self.start:
            self.start = ts
        if self.end is None or ts > self.end:
            self.end = ts

    def add_user(self, ts: datetime | None, text: str) -> None:
        self.turns.append(Turn(ts, redact(text)))

    def add_assistant(self, text: str) -> None:
        if self.turns and text.strip():
            self.turns[-1].final = redact(text.strip())

    def add_tool(self, text: str) -> None:
        if text:
            self.tool_texts.append(text)


def block_texts(content, kinds=("text", "input_text", "output_text")) -> list[str]:
    if isinstance(content, str):
        return [content]
    out = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") in kinds and isinstance(block.get("text"), str):
                out.append(block["text"])
    return out


def stringify(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(stringify(v) for v in value)
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        if "content" in value:
            return stringify(value["content"])
        if "output" in value:
            return stringify(value["output"])
        return json.dumps(value, ensure_ascii=False)
    return "" if value is None else str(value)


def iter_json(path: Path):
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except OSError:
        return


# ---------------------------------------------------------------- cleaning

_REMINDER = re.compile(r"<system-reminder>.*?(?:</system-reminder>|\Z)", re.DOTALL)
_TASK_NOTE = re.compile(r"<task-notification>.*?(?:</task-notification>|\Z)", re.DOTALL)
_LOCAL_OUT = re.compile(r"<(local-command-stdout|local-command-stderr|local-command-caveat|bash-stdout|bash-stderr)>.*?(?:</\1>|\Z)", re.DOTALL)
_SKILL_LINK = re.compile(r"\[([$@][\w:.-]+)\]\([^)]*\)")


def _tag(text: str, name: str) -> str:
    match = re.search(rf"<{name}>(.*?)</{name}>", text, re.DOTALL)
    return match.group(1).strip() if match else ""


def clean_claude_user(text: str) -> str:
    text = _REMINDER.sub("", text)
    text = _TASK_NOTE.sub("", text)
    if "<command-name>" in text:
        command = f"{_tag(text, 'command-name')} {_tag(text, 'command-args')}".strip()
        text = re.sub(r"<(command-name|command-message|command-args)>.*?</\1>", "", text, flags=re.DOTALL)
        text = command + ("\n" + text.strip() if text.strip() else "")
    bash = _tag(text, "bash-input")
    if bash:
        text = re.sub(r"<bash-input>.*?</bash-input>", f"! {bash}", text, flags=re.DOTALL)
    text = _LOCAL_OUT.sub("", text)
    text = re.sub(r"<!-- (?:attach|reply(?: \d+)?) -->", "", text)
    text = text.strip()
    if text.startswith("[Request interrupted by user"):
        return ""
    return text


# Harness-injected Codex user blocks; each starts with one of these markers.
_CODEX_DROP_PREFIXES = (
    "# AGENTS.md instructions",
    "# Files mentioned by the user",
    "The following is the Codex agent history",
)
_CODEX_DROP_TAGS = {
    "environment_context", "user_instructions", "permissions instructions", "recommended_plugins",
    "subagent_notification", "skill", "turn_aborted", "image", "/image", "external_codex_apps_open_page",
    "in-app-browser-context", "collaboration_mode", "codex_apps_client_time_context", "skills_instructions",
    "apps_instructions", "plugins_instructions", "user_shell_command",
}


def _annotations(text: str) -> str:
    """Render Codex response annotations (quoted selection + the user's comment)."""
    raw = _tag(text, "response-annotations")
    try:
        items = json.loads(raw) if raw else []
    except json.JSONDecodeError:
        return ""
    notes = []
    for item in items if isinstance(items, list) else []:
        if isinstance(item, dict) and str(item.get("annotation") or "").strip():
            quote = re.sub(r"\s+", " ", str(item.get("text") or "")).strip()[:100]
            notes.append(f"> {quote}\n{str(item['annotation']).strip()}")
    return "\n".join(notes)


def clean_codex_block(text: str) -> str:
    notes = _annotations(text) if "<response-annotations>" in text else ""
    marker = "## My request:"
    if marker in text:
        text = text.rsplit(marker, 1)[1]
    elif notes:
        text = ""
    return "\n".join(part for part in (notes, _clean_codex_request(text)) if part)


def _clean_codex_request(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if stripped.startswith(_CODEX_DROP_PREFIXES):
        return ""
    tag = re.match(r"<(/?[\w][\w -]*?)[\s>]", stripped)
    if tag:
        name = tag.group(1)
        if name == "send_user_message_question_reply":
            try:
                items = json.loads(_tag(stripped, name))
                return "\n".join(f"answer: {i.get('answer')}" for i in items if isinstance(i, dict))
            except (json.JSONDecodeError, TypeError):
                return ""
        if name in _CODEX_DROP_TAGS or stripped.endswith(f"</{name}>"):
            return ""
    stripped = _REMINDER.sub("", stripped)
    return _SKILL_LINK.sub(r"\1", stripped).strip()


# ---------------------------------------------------------------- adapters


def parse_claude(path: Path, subagent: bool) -> Session:
    sid = path.stem
    session = Session("claude", sid, [path], subagent=subagent)
    for obj in iter_json(path):
        kind = obj.get("type")
        if "message" in obj:
            session.message_like += 1
        if kind not in ("user", "assistant"):
            continue
        message = obj.get("message")
        if not isinstance(message, dict):
            continue
        session.raw_messages += 1
        if obj.get("isSidechain") and not subagent:
            continue
        if not session.cwd and isinstance(obj.get("cwd"), str):
            session.cwd = obj["cwd"]
        branch = obj.get("gitBranch")
        if isinstance(branch, str) and branch and branch != "HEAD":
            session.branch = branch
        ts = parse_ts(obj.get("timestamp"))
        session.touch(ts)
        content = message.get("content")
        if kind == "assistant":
            texts = block_texts(content, ("text",))
            if texts:
                session.add_assistant("\n".join(texts))
            continue
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    session.add_tool(stringify(block.get("content")))
        if obj.get("isMeta") or obj.get("isCompactSummary"):
            continue
        origin = obj.get("origin")
        if isinstance(origin, dict) and origin.get("kind") not in (None, "human"):
            continue
        text = clean_claude_user("\n".join(block_texts(content, ("text",))))
        if text:
            session.add_user(ts, text)
    return session


def claude_head(path: Path) -> tuple[str, bool]:
    """Return (cwd, all-sidechain) from the first entries without parsing the whole file."""
    for index, obj in enumerate(iter_json(path)):
        if obj.get("type") in ("user", "assistant") and isinstance(obj.get("cwd"), str):
            return obj["cwd"], bool(obj.get("isSidechain"))
        if index > 200:
            break
    return "", False


def parse_codex(paths: list[Path]) -> Session:
    session: Session | None = None
    source = None
    human_turns = 0
    for path in paths:
        for obj in iter_json(path):
            kind = obj.get("type")
            payload = obj.get("payload")
            if not isinstance(payload, dict):
                continue
            if kind == "session_meta":
                if session is None:
                    git = payload.get("git") if isinstance(payload.get("git"), dict) else {}
                    source = payload.get("thread_source")
                    session = Session(
                        "codex", str(payload.get("id", "")), paths,
                        cwd=str(payload.get("cwd") or ""),
                        branch=str(git.get("branch") or ""),
                        repo_url=str(git.get("repository_url") or ""),
                        subagent=source not in (None, "user"),
                    )
                    session.touch(parse_ts(payload.get("timestamp")))
                continue
            if session is None or kind != "response_item":
                continue
            session.message_like += 1
            ptype = payload.get("type")
            ts = parse_ts(obj.get("timestamp"))
            if ptype == "message":
                role = payload.get("role")
                if role not in ("user", "assistant"):
                    continue
                session.raw_messages += 1
                session.touch(ts)
                texts = block_texts(payload.get("content"))
                if role == "assistant":
                    if texts:
                        session.add_assistant("\n".join(texts))
                    continue
                text = "\n".join(t for t in (clean_codex_block(b) for b in texts) if t).strip()
                if text:
                    human_turns += 1
                    session.add_user(ts, text)
            elif ptype == "agent_message" and session.subagent:
                # Inter-agent task payloads are stored encrypted; keep a placeholder turn
                # so the subagent's final replies stay attached to something.
                session.raw_messages += 1
                session.touch(ts)
                header = " ".join(block_texts(payload.get("content")))
                kind_match = re.search(r"Message Type: (\w+)", header)
                label = kind_match.group(1) if kind_match else "MESSAGE"
                session.add_user(ts, f"[{label} from {payload.get('author') or 'agent'}; payload encrypted in transcript]")
            elif ptype in ("function_call_output", "custom_tool_call_output"):
                session.add_tool(stringify(payload.get("output")))
    if session is None:
        session = Session("codex", codex_id(paths[0]) or paths[0].stem, paths)
    elif source == "agent_created_thread" and human_turns:
        # A thread the desktop app forked off a user conversation; worker threads that
        # carry only encrypted agent messages stay subagents.
        session.subagent = False
    return session


def parse_pi(path: Path) -> Session:
    session = Session("pi", pi_id(path), [path])
    for obj in iter_json(path):
        kind = obj.get("type")
        if kind == "session":
            session.id = str(obj.get("id") or session.id)
            session.cwd = str(obj.get("cwd") or "")
            session.touch(parse_ts(obj.get("timestamp")))
            continue
        if kind != "message" or not isinstance(obj.get("message"), dict):
            continue
        message = obj["message"]
        role = message.get("role")
        if role != "system":
            session.message_like += 1
        ts = parse_ts(obj.get("timestamp"))
        if role == "toolResult":
            session.add_tool("\n".join(block_texts(message.get("content"))))
            continue
        if role not in ("user", "assistant"):
            continue
        session.raw_messages += 1
        session.touch(ts)
        texts = block_texts(message.get("content"))
        if role == "assistant":
            if texts:
                session.add_assistant("\n".join(texts))
        else:
            text = _REMINDER.sub("", "\n".join(texts)).strip()
            if text:
                session.add_user(ts, text)
    return session


def pi_head(path: Path) -> str:
    for obj in iter_json(path):
        return str(obj.get("cwd") or "") if obj.get("type") == "session" else ""
    return ""


def codex_head(path: Path) -> dict:
    for obj in iter_json(path):
        if obj.get("type") == "session_meta" and isinstance(obj.get("payload"), dict):
            return obj["payload"]
        return {}
    return {}


# ---------------------------------------------------------------- discovery

_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_CODEX_NAME = re.compile(rf"rollout-.*?-({_UUID})(?:_{_UUID})?\.jsonl$")


def codex_id(path: Path) -> str:
    match = _CODEX_NAME.search(path.name)
    return match.group(1) if match else ""


def pi_id(path: Path) -> str:
    stem = path.stem
    return stem.split("_", 1)[1] if "_" in stem else stem


def store_root(source: str) -> Path:
    env, default = DEFAULT_ROOTS[source]
    return Path(os.environ.get(env) or default).expanduser()


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def claude_files(include_subagents: bool) -> list[tuple[Path, bool]]:
    root = store_root("claude")
    if not root.is_dir():
        return []
    out = [(p, False) for p in root.glob("*/*.jsonl")]
    if include_subagents:
        out += [(p, True) for p in root.glob("*/*/subagents/*.jsonl")]
    return out


def codex_groups() -> dict[str, list[Path]]:
    root = store_root("codex")
    groups: dict[str, list[Path]] = {}
    if not root.is_dir():
        return groups
    for path in root.glob("*/*/*/*.jsonl"):
        sid = codex_id(path) or path.stem
        groups.setdefault(sid, []).append(path)
    for paths in groups.values():
        paths.sort(key=lambda p: p.name)
    return groups


def pi_files() -> list[Path]:
    root = store_root("pi")
    return list(root.glob("*/*.jsonl")) if root.is_dir() else []


# ---------------------------------------------------------------- scope


def _git(cwd: str, *args: str) -> str:
    try:
        result = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    url = re.sub(r"^[a-z+]+://", "", url)
    url = re.sub(r"^[^@/]+@", "", url)
    url = url.replace(":", "/", 1) if re.match(r"^[^/]+:[^/]", url) else url
    return url.lower()


@dataclass
class Scope:
    roots: list[str]
    origin: str
    all_projects: bool

    def matches(self, cwd: str, repo_url: str = "") -> bool:
        if self.all_projects:
            return True
        if self.origin and repo_url and normalize_url(repo_url) == self.origin:
            return True
        if not cwd:
            return False
        candidates = {os.path.normpath(cwd), os.path.realpath(cwd)}
        return any(c == r or c.startswith(r.rstrip("/") + "/") for c in candidates for r in self.roots)


def build_scope(cwd: str, all_projects: bool) -> Scope:
    base = os.path.abspath(os.path.expanduser(cwd))
    if not os.path.isdir(base):
        raise RecallError(f"--cwd {cwd!r} is not a directory. Pass the repository you want to recall, or --all-projects.")
    roots = {base}
    top = _git(base, "rev-parse", "--show-toplevel")
    if top:
        roots = {top}
        common = _git(base, "rev-parse", "--path-format=absolute", "--git-common-dir")
        if common and os.path.basename(common) == ".git":
            roots.add(os.path.dirname(common))
    expanded = set()
    for root in roots:
        expanded.add(os.path.normpath(root))
        expanded.add(os.path.realpath(root))
    origin = _git(base, "remote", "get-url", "origin")
    return Scope(sorted(expanded), normalize_url(origin) if origin else "", all_projects)


# ---------------------------------------------------------------- extraction

_COMMIT_LINE = re.compile(r"\[([^\]\s]+)(?: \(root-commit\))? ([0-9a-f]{7,40})\] ([^\n]*)")
_HEX = re.compile(r"(?<![0-9A-Za-z_/-])[0-9a-f]{7,40}(?![0-9A-Za-z_-])")
_PR = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/(?:pull|issues)/\d+")


def extract_commits(session: Session) -> list[dict]:
    found: list[dict] = []

    def add(sha: str, branch: str = "", message: str = "") -> None:
        for item in found:
            if item["sha"].startswith(sha) or sha.startswith(item["sha"]):
                item["branch"] = item["branch"] or branch
                item["message"] = item["message"] or message
                return
        found.append({"sha": sha, "branch": branch, "message": redact(message.strip())})

    for text in session.tool_texts:
        for match in _COMMIT_LINE.finditer(text):
            add(match.group(2), match.group(1), match.group(3))
    for turn in session.turns:
        for token in _HEX.findall(turn.final):
            if re.search(r"\d", token) and re.search(r"[a-f]", token):
                add(token)
    return found


def extract_prs(session: Session) -> list[str]:
    seen: list[str] = []
    texts = [t.user for t in session.turns] + [t.final for t in session.turns] + session.tool_texts
    for text in texts:
        for url in _PR.findall(text):
            if url not in seen:
                seen.append(url)
    return seen


def trim(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def one_line(text: str, limit: int) -> str:
    return trim(re.sub(r"\s+", " ", text), limit)


# ---------------------------------------------------------------- list


def collect(args) -> tuple[Scope, list[Session], list[str]]:
    scope = build_scope(args.cwd, args.all_projects)
    since = parse_bound(args.since, "--since", end_of_day=False)
    until = parse_bound(args.until, "--until", end_of_day=True) if args.until else None
    sources = parse_sources(args.source)
    floor = since.timestamp() if since else 0.0
    sessions: list[Session] = []

    if "claude" in sources:
        for path, in_subdir in claude_files(args.include_subagents):
            if _mtime(path) < floor:
                continue
            cwd, sidechain = claude_head(path)
            subagent = in_subdir or sidechain
            if subagent and not args.include_subagents:
                continue
            if cwd and not scope.matches(cwd):
                continue
            sessions.append(parse_claude(path, subagent))
    if "codex" in sources:
        for paths in codex_groups().values():
            if max(_mtime(p) for p in paths) < floor:
                continue
            meta = codex_head(paths[0])
            if meta:
                if meta.get("thread_source") not in TOP_LEVEL_CODEX_SOURCES and not args.include_subagents:
                    continue
                git = meta.get("git") if isinstance(meta.get("git"), dict) else {}
                if not scope.matches(str(meta.get("cwd") or ""), str(git.get("repository_url") or "")):
                    continue
            session = parse_codex(paths)
            if session.subagent and not args.include_subagents:
                continue
            sessions.append(session)
    if "pi" in sources:
        for path in pi_files():
            if _mtime(path) < floor:
                continue
            cwd = pi_head(path)
            if cwd and not scope.matches(cwd):
                continue
            sessions.append(parse_pi(path))

    warnings: list[str] = []
    unparsed = [
        s for s in sessions
        if s.message_like and not s.raw_messages and (not s.cwd or scope.matches(s.cwd, s.repo_url))
    ]
    if unparsed:
        warnings.append(
            f"warning: {len(unparsed)} transcript file(s) in scope yielded no parseable messages "
            f"(possible format drift), e.g. {unparsed[0].paths[0]}"
        )
    kept = []
    for s in sessions:
        if not s.turns or not scope.matches(s.cwd, s.repo_url):
            continue
        if since and (s.end is None or s.end < since):
            continue
        if until and (s.start is None or s.start >= until):
            continue
        kept.append(s)
    kept.sort(key=lambda s: s.end or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return scope, kept, warnings


def parse_sources(value: str) -> list[str]:
    sources = [s.strip().lower() for s in value.split(",") if s.strip()]
    unknown = [s for s in sources if s not in SOURCES]
    if unknown or not sources:
        raise RecallError(f"--source {value!r} has unknown source(s) {unknown}. Use a comma list of: {','.join(SOURCES)}.")
    return sources


def grep_hits(session: Session, needles: list[str]) -> int:
    lowered = [n.lower() for n in needles]
    hits = 0
    for turn in session.turns:
        for text in (turn.user, turn.final):
            low = text.lower()
            if any(n in low for n in lowered):
                hits += 1
    return hits


def cmd_list(args) -> int:
    scope, sessions, warnings = collect(args)
    needles = args.grep or []
    rows = []
    for s in sessions:
        hits = grep_hits(s, needles) if needles else None
        if needles and not hits:
            continue
        row = {
            "source": s.source,
            "id": s.id,
            "start": fmt_iso(s.start),
            "end": fmt_iso(s.end),
            "cwd": s.cwd,
            "branch": s.branch,
            "user_turns": len(s.turns),
            "first_message": one_line(s.turns[0].user, FIRST_MESSAGE_CHARS),
            "subagent": s.subagent,
            "path": str(s.paths[-1]),
        }
        if needles:
            row["grep_hits"] = hits
        rows.append((s, row))
    for warning in warnings:
        print(warning, file=sys.stderr)
    scope_desc = {
        "projects": "all" if scope.all_projects else scope.roots,
        "origin": scope.origin or None,
        "since": args.since,
        "until": args.until,
        "sources": parse_sources(args.source),
        "grep": needles,
        "include_subagents": args.include_subagents,
    }
    if args.json:
        print(json.dumps(redact_obj({"scope": scope_desc, "sessions": [r for _, r in rows]}), ensure_ascii=False, indent=2))
        return 0
    where = "all projects" if scope.all_projects else ", ".join(sorted(set(scope.roots)))
    lines = [
        f"scope: {where}" + (f" (origin {scope.origin})" if scope.origin and not scope.all_projects else ""),
        f"window: since {args.since}" + (f" until {args.until}" if args.until else "")
        + f"; sources {','.join(scope_desc['sources'])}"
        + ("; subagents included" if args.include_subagents else "; subagent sessions excluded")
        + (f"; grep {' | '.join(needles)}" if needles else ""),
        f"{len(rows)} session(s), newest first. Next: recall.py show <id>...",
        "",
    ]
    for s, row in rows:
        span = f"{fmt_local(s.start)} -> {fmt_local(s.end)}"
        extra = f"  hits={row['grep_hits']}" if needles else ""
        sub = "  [subagent]" if s.subagent else ""
        lines.append(f"{s.source:<6} {s.id}  {span}  branch={s.branch or '-'}  turns={len(s.turns)}{extra}{sub}")
        lines.append(f"       cwd: {s.cwd}")
        lines.append(f"       first: {row['first_message']}")
    print(redact("\n".join(lines)))
    return 0


# ---------------------------------------------------------------- show


def index_sessions() -> list[tuple[str, str, list[Path], bool]]:
    entries: list[tuple[str, str, list[Path], bool]] = []
    for path, subagent in claude_files(include_subagents=True):
        entries.append(("claude", path.stem, [path], subagent))
    for sid, paths in codex_groups().items():
        entries.append(("codex", sid, paths, False))
    for path in pi_files():
        entries.append(("pi", pi_id(path), [path], False))
    return entries


def resolve(ident: str, entries) -> tuple[str, str, list[Path], bool]:
    exact = [e for e in entries if e[1] == ident]
    matches = exact or [e for e in entries if e[1].startswith(ident)]
    if not matches:
        raise RecallError(
            f"no session id starts with {ident!r} in any store. Run `recall.py list` (add --all-projects, "
            "--since all or --include-subagents to widen) and copy an id from its output."
        )
    if len(matches) > 1:
        options = ", ".join(f"{e[0]}:{e[1]}" for e in matches[:8])
        raise RecallError(f"id prefix {ident!r} is ambiguous ({len(matches)} matches: {options}). Pass a longer prefix from `recall.py list`.")
    return matches[0]


def load(entry) -> Session:
    source, _, paths, subagent = entry
    if source == "claude":
        return parse_claude(paths[0], subagent or "/subagents/" in str(paths[0]))
    if source == "codex":
        return parse_codex(paths)
    return parse_pi(paths[0])


def budget_turns(turns: list[dict], max_chars: int) -> tuple[list[dict], int]:
    def size(t):
        return len(t["user"]) + len(t["assistant"]) + 40

    if sum(size(t) for t in turns) <= max_chars or len(turns) <= 1:
        return turns, 0
    kept_tail: list[dict] = []
    used = size(turns[0])
    for turn in reversed(turns[1:]):
        if used + size(turn) > max_chars:
            break
        kept_tail.insert(0, turn)
        used += size(turn)
    omitted = len(turns) - 1 - len(kept_tail)
    return [turns[0]] + kept_tail, omitted


def cmd_show(args) -> int:
    entries = index_sessions()
    resolved = [resolve(ident, entries) for ident in args.ids]
    out = []
    for entry in resolved:
        s = load(entry)
        turns = [
            {"time": fmt_iso(t.time), "user": trim(t.user, USER_TURN_CHARS), "assistant": trim(t.final, FINAL_TURN_CHARS)}
            for t in s.turns
        ]
        turns, omitted = budget_turns(turns, args.max_chars)
        out.append({
            "source": s.source,
            "id": s.id,
            "cwd": s.cwd,
            "branch": s.branch,
            "start": fmt_iso(s.start),
            "end": fmt_iso(s.end),
            "subagent": s.subagent,
            "paths": [str(p) for p in s.paths],
            "user_turns": len(s.turns),
            "omitted_turns": omitted,
            "turns": turns,
            "commits": extract_commits(s),
            "pull_requests": extract_prs(s),
        })
    if args.json:
        print(json.dumps(redact_obj({"sessions": out}), ensure_ascii=False, indent=2))
        return 0
    lines: list[str] = []
    for item in out:
        lines.append(f"=== {item['source']} {item['id']}" + ("  [subagent]" if item["subagent"] else ""))
        lines.append(f"cwd: {item['cwd'] or '?'}  branch: {item['branch'] or '-'}")
        start, end = parse_ts(item["start"]), parse_ts(item["end"])
        lines.append(f"time: {fmt_local(start)} -> {fmt_local(end)}  user turns: {item['user_turns']}")
        lines.append("file: " + ", ".join(item["paths"]))
        for number, turn in enumerate(item["turns"], 1):
            if number == 2 and item["omitted_turns"]:
                lines.append(f"\n[... {item['omitted_turns']} middle turn(s) omitted; rerun with a larger --max-chars to see them]")
            lines.append(f"\n--- user {fmt_local(parse_ts(turn['time']))}\n{turn['user']}")
            lines.append(f"--- final reply\n{turn['assistant'] or '(no text reply)'}")
        lines.append("\ncommits:" + ("" if item["commits"] else " none found"))
        for commit in item["commits"]:
            meta = " ".join(x for x in (f"({commit['branch']})" if commit["branch"] else "", commit["message"]) if x)
            lines.append(f"  {commit['sha']} {meta}".rstrip())
        lines.append("pull requests / issues:" + ("" if item["pull_requests"] else " none found"))
        lines.extend(f"  {url}" for url in item["pull_requests"])
        lines.append("")
    print(redact("\n".join(lines)))
    return 0


# ---------------------------------------------------------------- cli

HELP = """\
Mine local agent transcripts (Claude Code, Codex, Pi) to rebuild recent working context.

Typical flow:
  recall.py list                       # sessions for this repo, last 7 days
  recall.py list --grep pstack --grep recall
  recall.py show 01a0f5c2 4f67d217     # turns + commits/PRs for chosen sessions

Stores (override with env vars; a missing store is skipped):
  claude  $RECALL_CLAUDE_ROOT  default ~/.claude/projects
  codex   $RECALL_CODEX_ROOT   default ~/.codex/sessions
  pi      $RECALL_PI_ROOT      default ~/.pi/agent/sessions

Scope: a session belongs to the repo when its cwd is inside the repo root or its main
worktree root, or (Codex) its recorded repository_url equals the repo's origin.
Subagent, sidechain and reviewer sessions are hidden unless --include-subagents;
a Codex agent-created thread counts as the user's own when it has real user messages.
Output is redacted: API keys, tokens and private keys print as [REDACTED].
"""

LIST_HELP = """\
List sessions newest first: source, id, time range, cwd, branch, user-turn count and
the first real user message. Files are skipped by mtime before parsing, so short windows
stay fast. A stderr warning reports in-scope files with zero parseable messages
(transcript format drift); report it rather than ignoring it.

examples:
  recall.py list --since 2d
  recall.py list --since 2026-09-01 --until 2026-09-15 --source codex
  recall.py list --all-projects --since 30d --grep deploy --json
"""

SHOW_HELP = """\
Show sessions by id (a unique prefix is enough): header, then each real user message
with the FINAL assistant text of that turn, then commit SHAs and GitHub PR/issue URLs
found in tool output and final replies. Long sessions keep the first turn and the newest
turns that fit --max-chars; the gap is marked. Ids come from `recall.py list`.

examples:
  recall.py show 01a0f5c2
  recall.py show 01a0f5c2 4f67d217 --max-chars 4000 --json
"""


def build_parser() -> argparse.ArgumentParser:
    fmt = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(prog="recall.py", description=HELP, formatter_class=fmt)
    sub = parser.add_subparsers(dest="command", metavar="{list,show}")

    p_list = sub.add_parser("list", help="list sessions in scope", description=LIST_HELP, formatter_class=fmt)
    p_list.add_argument("--cwd", default=os.getcwd(), help="repository to recall (default: current directory)")
    p_list.add_argument("--since", default="7d", help="lower bound: 7d, 12h, 2w, YYYY-MM-DD, ISO time, or 'all' (default 7d)")
    p_list.add_argument("--until", default=None, help="upper bound, same forms; a date includes that whole day")
    p_list.add_argument("--grep", action="append", metavar="KW", help="case-insensitive keyword over user messages and final replies; repeat for OR")
    p_list.add_argument("--source", default=",".join(SOURCES), help="comma list of claude,codex,pi (default all)")
    p_list.add_argument("--all-projects", action="store_true", help="do not restrict to --cwd's repository")
    p_list.add_argument("--include-subagents", action="store_true", help="also list subagent, sidechain and reviewer sessions")
    p_list.add_argument("--json", action="store_true", help="machine-readable output")

    p_show = sub.add_parser("show", help="show turns, commits and PRs of sessions", description=SHOW_HELP, formatter_class=fmt)
    p_show.add_argument("ids", nargs="+", metavar="ID", help="session id or unique prefix")
    p_show.add_argument("--max-chars", type=int, default=8000, help="approximate per-session text budget (default 8000)")
    p_show.add_argument("--json", action="store_true", help="machine-readable output")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    try:
        return cmd_list(args) if args.command == "list" else cmd_show(args)
    except RecallError as exc:
        print(f"recall: error: {exc}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    sys.exit(main())
