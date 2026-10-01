# Sync vendored skills

Status: current procedure

Vendored skills are generated output. Edit `vendor/<name>/sync.json` (upstream repository, pinned commit, skill paths, exact text patches, forbidden leftovers), then regenerate; never edit the generated skill directories by hand.

## Check for upstream changes

```bash
python scripts/sync_vendor.py status pstack
```

The command prints the pinned commit and the upstream `HEAD`. It reads the network and writes nothing.

## Update

```bash
python scripts/sync_vendor.py update pstack            # upstream HEAD
python scripts/sync_vendor.py update pstack --ref <sha>
git diff --stat
```

The script fetches only the configured paths, copies each skill with the upstream `LICENSE`, applies every patch, stamps a generated-by line into each `SKILL.md` frontmatter, and only then replaces the top-level skill directories and the pin.

## Failure and recovery

`patch no longer applies` means upstream rewrote patched text; `still contains` means upstream added text a patch must cover. Both abort before any write, so the previous output and pin stay intact. Read the upstream change, adjust `sync.json`, and rerun. To roll back a bad update, restore the previous commit's skill directories and `sync.json` with Git.

## Verify

Run `bash scripts/verify.sh`. `tests/test_vendor_sync.py` covers the success output and both abort paths offline. After an update, reinstall the changed skills through skillshare so targets receive them.
