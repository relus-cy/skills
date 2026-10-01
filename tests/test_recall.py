from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "recall"
SCRIPT = SKILL / "scripts" / "recall.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "recall"

# Built at runtime so no secret-shaped literal is stored in the repository.
FAKE_ANTHROPIC_KEY = "sk-ant-" + "api03-" + "Q" * 30
FAKE_GH_TOKEN = "ghp_" + "Z" * 36

CLAUDE_MAIN = "c1111111-1111-4111-8111-111111111111"
CLAUDE_OLD = "c2222222-2222-4222-8222-222222222222"
CLAUDE_OTHER = "c3333333-3333-4333-8333-333333333333"
CLAUDE_SUB = "agent-a5ub"
CLAUDE_SIDECHAIN = "c5555555-5555-4555-8555-555555555555"
CODEX_MAIN = "0199aaaa-0000-7000-8000-000000000001"
CODEX_SUB = "0199aaaa-0000-7000-8000-000000000002"
CODEX_WORKTREE = "0199aaaa-0000-7000-8000-000000000003"
CODEX_WORKER = "0199aaaa-0000-7000-8000-000000000004"
PI_MAIN = "0199bbbb-0000-7000-8000-000000000001"

# Explicit file mtimes, so the --since mtime prefilter never depends on when the test runs.
MTIMES = {
    CLAUDE_MAIN: "2026-09-20T10:07:00+00:00",
    CLAUDE_SUB: "2026-09-20T10:02:00+00:00",
    CLAUDE_OLD: "2026-08-01T09:01:00+00:00",
    CLAUDE_SIDECHAIN: "2026-09-20T11:01:00+00:00",
    CLAUDE_OTHER: "2026-09-21T09:01:00+00:00",
    CODEX_MAIN: "2026-09-22T03:01:00+00:00",
    CODEX_SUB: "2026-09-22T04:01:00+00:00",
    CODEX_WORKTREE: "2026-09-22T05:01:00+00:00",
    CODEX_WORKER: "2026-09-22T06:01:00+00:00",
    PI_MAIN: "2026-09-23T01:01:00+00:00",
}


class RecallCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(os.path.realpath(self.tmp.name))
        self.repo = base / "widget"
        self.other = base / "other-project"
        self.elsewhere = base / "codex-worktrees" / "ab12" / "widget"
        for path in (self.repo, self.other, self.elsewhere):
            path.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "remote", "add", "origin", "https://github.com/acme/widget.git"], check=True
        )
        self.stores = base / "stores"
        replacements = {
            "{{REPO}}": str(self.repo),
            "{{OTHER}}": str(self.other),
            "{{ELSEWHERE}}": str(self.elsewhere),
            "{{ANTHROPIC_KEY}}": FAKE_ANTHROPIC_KEY,
            "{{GH_TOKEN}}": FAKE_GH_TOKEN,
        }
        for source in FIXTURES.rglob("*.jsonl"):
            target = self.stores / source.relative_to(FIXTURES)
            target.parent.mkdir(parents=True, exist_ok=True)
            text = source.read_text(encoding="utf-8")
            for key, value in replacements.items():
                text = text.replace(key, value)
            target.write_text(text, encoding="utf-8")
            stamp = next(v for k, v in MTIMES.items() if k in target.name)
            seconds = datetime.fromisoformat(stamp).timestamp()
            os.utime(target, (seconds, seconds))
        self.env = {
            **os.environ,
            "RECALL_CLAUDE_ROOT": str(self.stores / "claude"),
            "RECALL_CODEX_ROOT": str(self.stores / "codex"),
            "RECALL_PI_ROOT": str(self.stores / "pi"),
            "TZ": "UTC",
        }

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_cli(self, *args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, env=self.env, cwd=self.repo
        )
        self.assertEqual(result.returncode, expect, result.stderr)
        return result

    def list_ids(self, *args: str) -> list[str]:
        out = self.run_cli("list", "--since", "2026-09-01", *args, "--json").stdout
        return [row["id"] for row in json.loads(out)["sessions"]]

    def test_default_list_is_repo_scoped_newest_first_without_subagents(self) -> None:
        self.assertEqual(self.list_ids(), [PI_MAIN, CODEX_WORKTREE, CODEX_MAIN, CLAUDE_MAIN])

    def test_include_subagents_adds_claude_subagent_sidechain_and_codex_subagent(self) -> None:
        self.assertEqual(
            self.list_ids("--include-subagents"),
            [PI_MAIN, CODEX_WORKER, CODEX_WORKTREE, CODEX_SUB, CODEX_MAIN, CLAUDE_SIDECHAIN, CLAUDE_MAIN, CLAUDE_SUB],
        )

    def test_agent_created_worktree_thread_is_listed_and_shown_by_default(self) -> None:
        # Codex desktop starts parallel worktree threads as agent_created_thread; they hold real user work.
        self.assertIn(CODEX_WORKTREE, self.list_ids())
        out = self.run_cli("show", CODEX_WORKTREE).stdout
        self.assertIn("WORKTREE-TICKET-REQUEST", out)
        self.assertIn("WORKTREE-TICKET-REPLY", out)

    def test_agent_created_thread_without_user_messages_is_a_subagent(self) -> None:
        # Worker threads spawned by a root agent carry only encrypted agent messages.
        self.assertNotIn(CODEX_WORKER, self.list_ids())
        self.assertIn(CODEX_WORKER, self.list_ids("--include-subagents"))
        out = self.run_cli("show", CODEX_WORKER).stdout
        self.assertIn("[subagent]", out)
        self.assertIn("WORKER-THREAD-REPLY", out)
        self.assertNotIn("[subagent]", self.run_cli("show", CODEX_WORKTREE).stdout)

    def test_all_projects_adds_other_project_session(self) -> None:
        self.assertEqual(self.list_ids("--all-projects"), [PI_MAIN, CODEX_WORKTREE, CODEX_MAIN, CLAUDE_OTHER, CLAUDE_MAIN])

    def test_since_excludes_old_session_that_since_all_includes(self) -> None:
        self.assertNotIn(CLAUDE_OLD, self.list_ids())
        out = json.loads(self.run_cli("list", "--since", "all", "--json").stdout)
        self.assertEqual([row["id"] for row in out["sessions"]], [PI_MAIN, CODEX_WORKTREE, CODEX_MAIN, CLAUDE_MAIN, CLAUDE_OLD])

    def test_until_excludes_sessions_starting_after_the_day(self) -> None:
        self.assertEqual(self.list_ids("--until", "2026-09-21"), [CLAUDE_MAIN])

    def test_source_filter(self) -> None:
        self.assertEqual(self.list_ids("--source", "codex,pi"), [PI_MAIN, CODEX_WORKTREE, CODEX_MAIN])

    def test_list_json_row_fields(self) -> None:
        out = json.loads(self.run_cli("list", "--since", "2026-09-01", "--source", "codex", "--json").stdout)
        self.assertEqual([r["id"] for r in out["sessions"]], [CODEX_WORKTREE, CODEX_MAIN])
        row = out["sessions"][1]
        self.assertEqual(row["source"], "codex")
        self.assertEqual(row["cwd"], str(self.elsewhere))
        self.assertEqual(row["branch"], "feature-x")
        self.assertEqual(row["user_turns"], 2)
        self.assertEqual(row["first_message"], "Add the Pstack comparison table $think")
        self.assertEqual(row["subagent"], False)
        self.assertEqual(
            datetime.fromisoformat(row["start"]).astimezone(timezone.utc),
            datetime(2026, 9, 22, 2, 0, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(
            datetime.fromisoformat(row["end"]).astimezone(timezone.utc),
            datetime(2026, 9, 22, 3, 0, 30, tzinfo=timezone.utc),
        )
        self.assertNotIn("grep_hits", row)

    def test_grep_is_case_insensitive_or_and_counts_hits(self) -> None:
        out = json.loads(self.run_cli("list", "--since", "2026-09-01", "--grep", "pstack", "--json").stdout)
        self.assertEqual([(r["id"], r["grep_hits"]) for r in out["sessions"]], [(CODEX_MAIN, 1)])
        out = json.loads(
            self.run_cli("list", "--since", "2026-09-01", "--grep", "PSTACK", "--grep", "pi-final", "--json").stdout
        )
        self.assertEqual([(r["id"], r["grep_hits"]) for r in out["sessions"]], [(PI_MAIN, 1), (CODEX_MAIN, 1)])

    def test_text_list_states_scope_and_first_message(self) -> None:
        out = self.run_cli("list", "--since", "2026-09-01", "--source", "pi").stdout
        self.assertIn(f"scope: {self.repo} (origin github.com/acme/widget)", out)
        self.assertIn("window: since 2026-09-01; sources pi; subagent sessions excluded", out)
        self.assertIn("first: PI-SESSION-QUESTION", out)

    def test_show_prints_user_message_and_final_reply_but_not_intermediate(self) -> None:
        out = self.run_cli("show", CLAUDE_MAIN, CODEX_MAIN, PI_MAIN).stdout
        self.assertIn("--- user", out)
        self.assertIn("Fix the login bug please", out)
        self.assertIn("FINAL-CLAUDE fixed and committed", out)
        self.assertNotIn("INTERMEDIATE-CLAUDE-NOTE", out)
        self.assertIn("Add the Pstack comparison table $think", out)
        self.assertIn("FINAL-CODEX table added", out)
        self.assertNotIn("INTERMEDIATE-CODEX", out)
        self.assertIn("PI-SESSION-QUESTION", out)
        self.assertIn("PI-FINAL-ANSWER", out)

    def test_show_merges_codex_pages_and_keeps_annotation_comments(self) -> None:
        out = json.loads(self.run_cli("show", CODEX_MAIN, "--json").stdout)["sessions"][0]
        self.assertEqual(
            [(t["user"], t["assistant"]) for t in out["turns"]],
            [
                ("Add the Pstack comparison table $think", "FINAL-CODEX table added"),
                ("> table added\nANNOTATION-COMMENT\nSECOND-PAGE-REQUEST", "SECOND-PAGE-FINAL"),
            ],
        )
        self.assertEqual(len(out["paths"]), 2)

    def test_injected_harness_text_never_printed(self) -> None:
        shown = self.run_cli("show", CLAUDE_MAIN, CODEX_MAIN, "--max-chars", "100000").stdout
        listed = self.run_cli("list", "--since", "all", "--include-subagents", "--all-projects").stdout
        for text in (shown, listed):
            for injected in (
                "SECRET-REMINDER-TEXT", "system-reminder", "ENV-CONTEXT-TEXT", "environment_context",
                "AGENTS-INSTRUCTIONS-TEXT", "META-SHOULD-NOT-APPEAR", "TASK-NOTE-TEXT", "Response annotations",
                "DEV-TEXT",
            ):
                self.assertNotIn(injected, text)
        self.assertIn("/think plan the cache", shown)

    def test_secrets_are_redacted_in_text_and_json(self) -> None:
        shown = self.run_cli("show", CLAUDE_MAIN).stdout
        self.assertIn("my key is [REDACTED] and token [REDACTED]", shown)
        as_json = self.run_cli("show", CLAUDE_MAIN, "--json").stdout
        self.assertIn("my key is [REDACTED] and token [REDACTED]", as_json)
        for output in (shown, as_json):
            self.assertNotIn(FAKE_ANTHROPIC_KEY, output)
            self.assertNotIn(FAKE_GH_TOKEN, output)
            self.assertNotIn("Q" * 20, output)

    def test_show_lists_commits_and_pull_requests(self) -> None:
        shown = self.run_cli("show", CLAUDE_MAIN).stdout
        self.assertIn("commits:\n  2e7cef6 (main) fix login\n", shown)
        self.assertIn("pull requests / issues:\n  https://github.com/acme/widget/pull/42\n", shown)
        codex = json.loads(self.run_cli("show", CODEX_MAIN, "--json").stdout)["sessions"][0]
        self.assertEqual(codex["commits"], [{"sha": "9f3c2ab", "branch": "feature-x", "message": "add comparison table"}])
        pi = json.loads(self.run_cli("show", PI_MAIN, "--json").stdout)["sessions"][0]
        self.assertEqual(pi["commits"], [{"sha": "4d5e6f7", "branch": "", "message": ""}])

    def test_show_accepts_unique_prefix(self) -> None:
        out = json.loads(self.run_cli("show", "c111", "--json").stdout)
        self.assertEqual([s["id"] for s in out["sessions"]], [CLAUDE_MAIN])

    def test_unknown_and_ambiguous_ids_fail_with_next_step(self) -> None:
        unknown = self.run_cli("show", "deadbeef", expect=2)
        self.assertEqual(unknown.stdout, "")
        self.assertIn("no session id starts with 'deadbeef'", unknown.stderr)
        self.assertIn("recall.py list", unknown.stderr)
        ambiguous = self.run_cli("show", "0199aaaa", expect=2)
        self.assertIn("ambiguous (4 matches", ambiguous.stderr)

    def test_bad_since_value_fails_with_accepted_forms(self) -> None:
        result = self.run_cli("list", "--since", "yesterday", expect=2)
        self.assertIn("--since 'yesterday' is not a time", result.stderr)
        self.assertIn("7d", result.stderr)

    def test_unparseable_in_scope_file_warns_on_stderr(self) -> None:
        drifted = self.stores / "claude" / "-repo" / "d4444444-4444-4444-8444-444444444444.jsonl"
        row = {"type": "human_turn", "cwd": str(self.repo), "timestamp": "2026-09-24T00:00:00Z", "message": {"text": "hi"}}
        drifted.write_text(json.dumps(row) + "\n", encoding="utf-8")
        result = self.run_cli("list", "--since", "2026-09-01")
        self.assertIn(
            f"warning: 1 transcript file(s) in scope yielded no parseable messages (possible format drift), e.g. {drifted}",
            result.stderr,
        )

    def test_missing_store_is_skipped(self) -> None:
        shutil.rmtree(self.stores / "pi")
        self.assertEqual(self.list_ids(), [CODEX_WORKTREE, CODEX_MAIN, CLAUDE_MAIN])


class RecallSkillFileTests(unittest.TestCase):
    def test_frontmatter_matches_directory_and_is_manual_only(self) -> None:
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        self.assertIsNotNone(match)
        fields = dict(line.split(": ", 1) for line in match.group(1).splitlines())
        self.assertEqual(fields["name"], SKILL.name)
        self.assertEqual(fields["disable-model-invocation"], "true")
        self.assertLessEqual(len(fields["description"].strip('"').split()), 45)


if __name__ == "__main__":
    unittest.main()
