# Module Restructure and Mac Deployment Design

**Date:** 2026-04-07
**Status:** Approved

## Summary

Rename the `bookmarks` package to `knowledge`, move `api_server.py` into the package, rename the vague `processors/default.py` to `processors/webpage.py`, add proper CLI entry points, replace Linux systemd service files with macOS launchd plists, and audit unused dependencies.

---

## Section 1: Module Structure

Rename `bookmarks/` → `knowledge/`. Move `api_server.py` → `knowledge/server.py`. Rename `processors/default.py` → `processors/webpage.py`. Update all internal imports throughout the package.

```
knowledge/
├── __init__.py
├── constants.py          (unchanged, imports updated)
├── models.py             (unchanged, imports updated)
├── server.py             (was api_server.py — gains main())
├── listener.py           (unchanged, imports updated)
├── processors/
│   ├── __init__.py
│   ├── base.py           (unchanged)
│   ├── webpage.py        (was default.py — imports updated)
│   └── twitter.py        (unchanged, imports updated)
└── utils/
    ├── images.py         (imports updated)
    ├── llm.py            (imports updated)
    ├── migrations.py     (imports updated)
    ├── secret_creation.py (unchanged)
    └── urls.py           (unchanged)
```

Files untouched: `extension/`, `templates/`, `tests/`, `CLAUDE.md`, `journal/`, `docs/`.

The `tests/test_api_server.py` import `import api_server` must be updated to `from knowledge import server as api_server` (or equivalent).

---

## Section 2: Entry Points

Add `[project.scripts]` to `pyproject.toml`:

```toml
[project.scripts]
knowledge-server = "knowledge.server:main"
knowledge-listener = "knowledge.listener:main"
```

Add a `main()` function to `knowledge/server.py`:

```python
def main():
    app.run(port=5001, host="0.0.0.0", debug=False)
```

`knowledge/listener.py` already has a `main()` via Click — no change needed.

After `uv sync`, both services are invokable as:
- `uv run knowledge-server`
- `uv run knowledge-listener /path/to/watch --prefix data_`

---

## Section 3: Deployment (launchd)

Replace `scripts/knowledge.service` and `scripts/knowledge-listener.service` with macOS launchd agents.

### Files

```
scripts/
├── run-with-env.sh                        (sources .env, then exec $@)
├── com.wkerr.knowledge-server.plist
└── com.wkerr.knowledge-listener.plist
```

Keep the old `.service` files in git history but remove them from the repo.

### `scripts/run-with-env.sh`

```bash
#!/bin/bash
set -a
source "$(dirname "$0")/../.env"
set +a
exec "$@"
```

This sources the `.env` file from the repo root before handing off to the actual command. Keeps API keys and env vars out of the plist files.

### `scripts/com.wkerr.knowledge-listener.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wkerr.knowledge-listener</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/wkerr/development/knowledge-management/scripts/run-with-env.sh</string>
        <string>/Users/wkerr/.local/bin/uv</string>
        <string>run</string>
        <string>--directory</string>
        <string>/Users/wkerr/development/knowledge-management</string>
        <string>knowledge-listener</string>
        <string>/Users/wkerr/sync/inbound</string>
        <string>--prefix</string>
        <string>data_</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/wkerr/development/knowledge-management</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/knowledge-listener.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/knowledge-listener.err</string>
</dict>
</plist>
```

### `scripts/com.wkerr.knowledge-server.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wkerr.knowledge-server</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/wkerr/development/knowledge-management/scripts/run-with-env.sh</string>
        <string>/Users/wkerr/.local/bin/uv</string>
        <string>run</string>
        <string>--directory</string>
        <string>/Users/wkerr/development/knowledge-management</string>
        <string>gunicorn</string>
        <string>--workers</string>
        <string>3</string>
        <string>--bind</string>
        <string>0.0.0.0:5001</string>
        <string>knowledge.server:app</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/wkerr/development/knowledge-management</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/knowledge-server.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/knowledge-server.err</string>
</dict>
</plist>
```

### `Makefile`

```makefile
PLIST_DIR := $(HOME)/Library/LaunchAgents
SCRIPTS_DIR := scripts

.PHONY: install uninstall start stop logs

install:
	cp $(SCRIPTS_DIR)/com.wkerr.knowledge-server.plist $(PLIST_DIR)/
	cp $(SCRIPTS_DIR)/com.wkerr.knowledge-listener.plist $(PLIST_DIR)/
	launchctl load $(PLIST_DIR)/com.wkerr.knowledge-server.plist
	launchctl load $(PLIST_DIR)/com.wkerr.knowledge-listener.plist

uninstall:
	launchctl unload $(PLIST_DIR)/com.wkerr.knowledge-server.plist || true
	launchctl unload $(PLIST_DIR)/com.wkerr.knowledge-listener.plist || true
	rm -f $(PLIST_DIR)/com.wkerr.knowledge-server.plist
	rm -f $(PLIST_DIR)/com.wkerr.knowledge-listener.plist

start:
	launchctl start com.wkerr.knowledge-server
	launchctl start com.wkerr.knowledge-listener

stop:
	launchctl stop com.wkerr.knowledge-server
	launchctl stop com.wkerr.knowledge-listener

logs:
	tail -f /tmp/knowledge-server.log /tmp/knowledge-listener.log
```

---

## Section 4: Dependency Cleanup

### Remove (9 unused packages)

- `absl-py` — only used by deleted `arxiv_test.py`
- `fastapi` — never used; Flask is the server
- `uvicorn` — paired with fastapi, unused
- `langchain` — not imported anywhere
- `pymupdf4llm` — not imported anywhere
- `replicate` — not imported anywhere
- `selenium` — not imported anywhere
- `sqlalchemy` — not imported anywhere
- `tweepy` — not imported anywhere

### Add (4 packages)

- `gunicorn` — production server in plist
- `requests` — directly imported by `twitter.py`, currently only transitive
- `jinja2` — directly imported by processors, currently only transitive
- `httpx` — directly imported by `llm.py`, currently only transitive

---

## Execution Order

1. Dependency cleanup (`pyproject.toml` + `uv sync`) — safest first, verifies nothing breaks
2. Package rename (`bookmarks/` → `knowledge/`) — bulk import updates
3. Move `api_server.py` → `knowledge/server.py`, rename `processors/default.py` → `processors/webpage.py`
4. Add `[project.scripts]` entry points + `main()` in `server.py`
5. Update `tests/test_api_server.py` imports
6. Add launchd plists, `run-with-env.sh`, `Makefile`
7. Delete old `.service` files
