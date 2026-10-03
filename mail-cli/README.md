# mail-cli

A portable email skill with a standalone Python CLI. Read mail over IMAP, send mail over SMTP, and send, list, or download attachments. QQ Mail has a built-in server profile.

## Give it to an agent through GitHub

This skill is maintained in the `mail-cli/` directory of `relus-cy/skills`. After publishing the change, share the GitHub directory link with your agent and ask:

> Read `mail-cli/SKILL.md` in the `relus-cy/skills` repository. Acquire the complete `mail-cli/` directory so its bundled script is available, and use it for my mailbox tasks. Start by checking the runtime and mailbox setup. Use credentials configured locally for this agent.

An agent that supports the [Agent Skills format](https://agentskills.io/specification) can install this directory as a skill folder named `mail-cli`. An agent with shell access can also read the instructions and run the CLI directly. A GitHub URL provides the files; it does not by itself install a skill or grant mailbox access. Private repositories require the receiving agent to have repository access.

The agent-facing entry point is [`SKILL.md`](SKILL.md). Share its GitHub file link when your agent needs a direct document link, and keep the complete skill directory available for the bundled script. To reproduce a reviewed version, share a link pinned to a commit.

## Run the CLI

Requires Python 3.10+ on macOS/Linux and access to your mail servers. There are no third-party Python dependencies. The optional encrypted credential store additionally needs OpenSSL.

From the skill directory (`mail-cli/` inside the repository):

```sh
python3 scripts/mail_cli.py --help
python3 scripts/mail_cli.py profile --email example@qq.com
```

Configure `MAIL_USERNAME` and `MAIL_PASSWORD` in the execution environment before mailbox operations. For QQ Mail, enable IMAP/SMTP and use the generated authorization code as the password. Keep credentials in local secret configuration, outside this repository. [Tencent's account setup guidance](https://cloud.tencent.com/document/product/1270/55456)

Also provide all three connection settings for each protocol, so the CLI can operate without consulting a legacy credential store. For QQ Mail, set these non-secret variables before the commands below; for another provider, use the settings returned by `profile`:

```sh
export IMAP_HOST=imap.qq.com IMAP_PORT=993 IMAP_SECURITY=ssl
export SMTP_HOST=smtp.qq.com SMTP_PORT=465 SMTP_SECURITY=ssl
```

```sh
python3 scripts/mail_cli.py imap-test
python3 scripts/mail_cli.py imap-recent --limit 10
python3 scripts/mail_cli.py imap-attachments --uid 42
python3 scripts/mail_cli.py imap-download --uid 42 --output-dir ./attachments
```

To select attachments, repeat `--attachment-id` with IDs from the list. To send files after authorizing the recipients and contents:

```sh
python3 scripts/mail_cli.py smtp-send \
  --to recipient@example.com --subject 'Documents' --text 'Please see the attachments.' \
  --attach ./report.pdf --attach './data.csv' --confirm-send yes
```

Use subcommand `--help` for connection overrides and configurable size limits. Global options such as `--username` go before the subcommand. Commands with omitted connection settings can consult and migrate a legacy saved-account store; for environment-only operation, supply host, port, and security explicitly as described in `SKILL.md`.

Command results and handled runtime errors are JSON on stdout. Connection, TLS, filesystem, and invalid-value exceptions return `{"ok": false, "error": "..."}` with a nonzero exit code. Ports must be integers from 1 through 65535. `--help` uses plain text; invalid CLI syntax is reported as plain text on stderr. Automation should check the exit code and the JSON `ok` field, and retain stderr for failures without a JSON response. Some legacy preflight commands can report `ok: false` with exit code zero.

## Packaging choice

| Format | What this skill directory provides |
| --- | --- |
| CLI | `scripts/mail_cli.py`, runnable independently with Python |
| Skill | `SKILL.md` plus the bundled CLI, for agents that can execute shell commands |
| Plugin | Requires an adapter for the receiving application's plugin API; no application-specific plugin is included |

If an agent exposes only tool connections, an [MCP server](https://modelcontextprotocol.io/docs/getting-started/intro) could wrap the same implementation. That is an additional integration, not a requirement for agents with shell access.

## Tests and limits

```sh
python3 -m unittest discover -s tests -v
```

The acceptance suite uses subprocess CLI calls and temporary localhost IMAP/SMTP servers. It checks actual MIME data, downloaded bytes, read-only IMAP use, safe filenames, size limits, `.eml` handling, and failure behavior. Real provider accounts require a separate connectivity test with your own credentials.

Attachments are ordinary MIME parts; cloud attachment links are not fetched. Downloads avoid overwriting existing files. `.eml` serialization preserves message structure but may normalize line endings. The CLI supports password/app-password/authorization-code login; it does not implement OAuth.
