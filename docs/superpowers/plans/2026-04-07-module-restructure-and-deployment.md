# Module Restructure and Mac Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename `bookmarks/` → `knowledge/`, move `api_server.py` into the package, rename `processors/default.py` → `processors/webpage.py`, add CLI entry points, replace Linux systemd service files with macOS launchd plists, and audit unused dependencies.

**Architecture:** Pure refactor — no behavior changes. Dependency cleanup first (safest, verifies nothing breaks), then the bulk rename, then moving `api_server.py`, then wiring up entry points, then creating deployment files. Each task leaves the repo in a working state with passing tests.

**Tech Stack:** Python/uv, pyproject.toml entry points, macOS launchd, gunicorn, Flask

---

## File Map

| Action | Path |
|--------|------|
| Create | `knowledge/` (from `bookmarks/`) |
| Rename | `bookmarks/processors/default.py` → `knowledge/processors/webpage.py` |
| Move | `api_server.py` → `knowledge/server.py` |
| Modify | `pyproject.toml` (deps + entry points + package name) |
| Modify | `tests/test_api_server.py` (import path) |
| Create | `scripts/run-with-env.sh` |
| Create | `scripts/com.wkerr.knowledge-server.plist` |
| Create | `scripts/com.wkerr.knowledge-listener.plist` |
| Create | `Makefile` |
| Delete | `scripts/knowledge.service` |
| Delete | `scripts/knowledge-listener.service` |

---

### Task 1: Dependency cleanup

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Verify tests pass before touching anything**

```bash
uv run pytest tests/ -v
```

Expected: 5 passed.

- [ ] **Step 2: Remove 9 unused packages and add 4 direct dependencies**

In `pyproject.toml`, under `[project] dependencies`, remove:
```
"absl-py",
"fastapi",
"uvicorn",
"langchain",
"pymupdf4llm",
"replicate",
"selenium",
"sqlalchemy",
"tweepy",
```

Add (if not already present):
```
"gunicorn",
"requests",
"jinja2",
"httpx",
```

- [ ] **Step 3: Sync the lockfile**

```bash
uv sync
```

Expected: Resolves cleanly. If a package shows up as "not found", check the exact name in PyPI.

- [ ] **Step 4: Verify tests still pass**

```bash
uv run pytest tests/ -v
```

Expected: 5 passed.

- [ ] **Step 5: Verify the two main modules import cleanly**

```bash
uv run python -c "from bookmarks import listener; print('listener OK')"
uv run python -c "import api_server; print('api_server OK')"
```

Expected:
```
listener OK
api_server OK
```

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: remove 9 unused deps, promote 4 transitive deps to explicit"
```

---

### Task 2: Rename bookmarks/ → knowledge/ and default.py → webpage.py

**Files:**
- Rename: `bookmarks/` → `knowledge/`
- Rename: `knowledge/processors/default.py` → `knowledge/processors/webpage.py`
- Modify: `knowledge/listener.py` (imports)
- Modify: `knowledge/processors/webpage.py` (imports)
- Modify: `knowledge/processors/twitter.py` (imports)
- Modify: `knowledge/utils/llm.py` (imports)
- Modify: `knowledge/utils/migrations.py` (imports)
- Modify: `knowledge/processors/__init__.py` (if it imports default)
- Modify: `pyproject.toml` (package name)

- [ ] **Step 1: Rename the directory and the default processor**

```bash
git mv bookmarks knowledge
git mv knowledge/processors/default.py knowledge/processors/webpage.py
```

- [ ] **Step 2: Update imports in knowledge/listener.py**

Change:
```python
from bookmarks.processors import default
```
To:
```python
from knowledge.processors import webpage
```

And any usage `default.process_url(...)` → `webpage.process_url(...)`.

Also update any other `from bookmarks` imports in this file to `from knowledge`.

- [ ] **Step 3: Update imports in knowledge/processors/webpage.py**

Change all occurrences of `from bookmarks` to `from knowledge`:
```python
from knowledge import constants
from knowledge import models
from knowledge.processors import base
from knowledge.utils import llm
from knowledge.utils import images
from knowledge.utils import urls
```

- [ ] **Step 4: Update imports in knowledge/processors/twitter.py**

Change:
```python
from bookmarks import constants
from bookmarks.utils.urls import USER_AGENTS
```
To:
```python
from knowledge import constants
from knowledge.utils.urls import USER_AGENTS
```

- [ ] **Step 5: Update imports in knowledge/processors/__init__.py**

Read the file. If it imports `default`, change to `webpage`. If it's empty or doesn't reference these, no change needed.

- [ ] **Step 6: Update imports in knowledge/utils/llm.py**

Change:
```python
from bookmarks import models
```
To:
```python
from knowledge import models
```

- [ ] **Step 7: Update imports in knowledge/utils/migrations.py**

Change:
```python
from bookmarks import models
```
To:
```python
from knowledge import models
```

- [ ] **Step 8: Update pyproject.toml package name**

In `[tool.setuptools.packages.find]` or equivalent package declaration, change `bookmarks` to `knowledge`. Also update the project name from `perpetua` to `knowledge` if desired (check spec — spec says rename the package, project name can stay).

The key change is ensuring the installed package is `knowledge`, not `bookmarks`. Find `packages = [{include = "bookmarks"}]` or similar and update to `knowledge`.

- [ ] **Step 9: Verify imports resolve**

```bash
uv run python -c "from knowledge import listener; print('listener OK')"
uv run python -c "from knowledge import constants; print('constants OK')"
```

Expected: both print OK.

- [ ] **Step 10: Run tests**

```bash
uv run pytest tests/ -v
```

Expected: tests may fail on `import api_server` — that's OK, `api_server.py` still exists at the top level. If only the listener/knowledge tests pass and api_server tests pass (since api_server still imports from `bookmarks` — wait, bookmarks is gone now).

**Important:** `api_server.py` still imports `from bookmarks import models` — those will break now that the directory is `knowledge`. Update `api_server.py` at this step:

Change in `api_server.py`:
```python
from bookmarks import models
from bookmarks.utils import secret_creation
```
To:
```python
from knowledge import models
from knowledge.utils import secret_creation
```

Re-run:
```bash
uv run pytest tests/ -v
```

Expected: 5 passed.

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "refactor: rename bookmarks → knowledge, default.py → webpage.py, update all imports"
```

---

### Task 3: Move api_server.py → knowledge/server.py and update tests

**Files:**
- Move: `api_server.py` → `knowledge/server.py`
- Modify: `knowledge/server.py` (add `main()`)
- Modify: `tests/test_api_server.py` (update import)

- [ ] **Step 1: Move the file**

```bash
git mv api_server.py knowledge/server.py
```

- [ ] **Step 2: Add main() to knowledge/server.py**

At the bottom of `knowledge/server.py`, add:

```python
def main():
    app.run(port=5001, host="0.0.0.0", debug=False)
```

- [ ] **Step 3: Update tests/test_api_server.py**

Change the import at the top of the file:
```python
import api_server
```
To:
```python
from knowledge import server as api_server
```

No other changes needed — all `api_server.` references in the test body continue to work because the import aliases it.

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/ -v
```

Expected: 5 passed.

- [ ] **Step 5: Verify the server module loads**

```bash
uv run python -c "from knowledge import server; print('server OK')"
```

Expected: `server OK`

- [ ] **Step 6: Commit**

```bash
git add knowledge/server.py tests/test_api_server.py
git commit -m "refactor: move api_server.py → knowledge/server.py, add main()"
```

---

### Task 4: Add entry points to pyproject.toml

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add [project.scripts] section**

Add to `pyproject.toml`:

```toml
[project.scripts]
knowledge-server = "knowledge.server:main"
knowledge-listener = "knowledge.listener:main"
```

- [ ] **Step 2: Run uv sync to register the entry points**

```bash
uv sync
```

Expected: resolves cleanly.

- [ ] **Step 3: Verify entry points are callable**

```bash
uv run knowledge-server --help 2>&1 | head -5 || uv run python -c "from knowledge.server import main; print('main() exists')"
uv run python -c "from knowledge.listener import main; print('listener main() exists')"
```

Expected: no ImportError. The server's `main()` doesn't take args so `--help` may error — that's fine as long as it starts (you can Ctrl-C or just verify the function exists).

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/ -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add knowledge-server and knowledge-listener entry points"
```

---

### Task 5: Add launchd deployment files and remove old service files

**Files:**
- Create: `scripts/run-with-env.sh`
- Create: `scripts/com.wkerr.knowledge-server.plist`
- Create: `scripts/com.wkerr.knowledge-listener.plist`
- Create: `Makefile`
- Delete: `scripts/knowledge.service`
- Delete: `scripts/knowledge-listener.service`

- [ ] **Step 1: Create scripts/run-with-env.sh**

```bash
#!/bin/bash
set -a
source "$(dirname "$0")/../.env"
set +a
exec "$@"
```

Make it executable:
```bash
chmod +x scripts/run-with-env.sh
```

- [ ] **Step 2: Create scripts/com.wkerr.knowledge-listener.plist**

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

- [ ] **Step 3: Create scripts/com.wkerr.knowledge-server.plist**

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

- [ ] **Step 4: Create Makefile**

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

Note: Makefile recipes require actual tab characters, not spaces. Use a tab before each command.

- [ ] **Step 5: Delete old service files**

```bash
git rm scripts/knowledge.service scripts/knowledge-listener.service
```

- [ ] **Step 6: Run tests one final time**

```bash
uv run pytest tests/ -v
```

Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add scripts/run-with-env.sh scripts/com.wkerr.knowledge-server.plist scripts/com.wkerr.knowledge-listener.plist Makefile
git commit -m "feat: add launchd plists, run-with-env.sh, Makefile; remove Linux service files"
```
