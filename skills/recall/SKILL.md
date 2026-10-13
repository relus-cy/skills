---
name: recall
description: "Rebuild the user's recent working context from local Claude Code, Codex and Pi transcripts, checked against live git/gh state, as a short resume brief. Use for catch me up, where did I leave off, 回顾一下, 我之前做到哪了, 接着上次."
disable-model-invocation: true
---

# Recall

Rebuild where the user's work stands so a fresh agent can resume it. `recall.py` below means `python3 <this skill's directory>/scripts/recall.py`; run `recall.py list --help` for every flag.

1. **Lock the scope, then state it back in one line.** Defaults: the current directory's repository, the last 7 days, the topic if the user named one. Read another project only when asked (`--all-projects`). "All" means `--since all`; never shrink it to "recent" without saying so. If the user already handed you a full state capsule (branch, paths, the change), use it and skip mining.
2. **Mine transcripts.** Run `recall.py list [--since …] [--grep <topic>]…`, pick the in-scope sessions, then `recall.py show <id>…`. Skip the session you are running in (usually the newest) and obvious smoke tests. Report any stderr warning about unparseable files; it means the transcript format drifted.
   - More than 8 sessions: fan out to subagents, each with a batch of IDs. Each runs `show` and returns, per session ID: goal, decisions, open threads, user corrections, artifacts (commits, PRs, branches). Raw transcript text stays in the subagents.
3. **Verify against live state.** For every commit and PR found: `git log --oneline --since <window start>`, `git status --short`, `git branch -a --contains <sha>`, `gh pr view <n> --json state,mergedAt,headRefName`. Live state wins over what a transcript claims. A SHA that no branch contains belongs to another repo or was rewritten; drop it or say so.
4. **Write the brief** to the contract below, in the user's language. Cite session IDs (first 8 characters) for transcript claims.

## Brief contract

- **Capsule**: at most 5 bullets — what this work is and where it stands overall.
- **Threads**: one line each, starting with exactly one tag: `[merged #N]`, `[open PR #N]`, `[committed <sha>, unpushed]`, `[in flight <branch>]`, `[uncommitted]`, `[planned, not started]`. An untagged line is not allowed.
- **Problems**: at most 5 recurring ones, including corrections the user had to repeat and fixes that were reverted, so the next attempt starts where the last one failed.
- **Next move**: one concrete action.

Stay on the locked topic; an adjacent thread enters only if it blocks this one. When the brief outgrows a screen, cut detail before threads.

## Limits

- Codex subagent task payloads are stored encrypted; with `--include-subagents` their turns show a placeholder and only the replies are readable.
- `show` lists SHA-like tokens from final replies as well as `git commit` output, so step 3 is what makes a SHA trustworthy.
- Secrets in transcripts print as `[REDACTED]`; do not try to recover them.
