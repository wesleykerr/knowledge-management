# Repository Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete five dead/accidental files that don't belong to any of the three repository components (extension, API endpoint, listener).

**Architecture:** Pure deletion — no code changes required. Nothing in the active codebase imports any of these files. Verify with a grep scan and existing tests before and after.

**Tech Stack:** git, uv (for running tests)

---

## File Map

| Action | Path |
|--------|------|
| Delete | `bookmarks/cli.py` |
| Delete | `bookmarks/structured_output.py` |
| Delete | `bookmarks/utils/schema_creator.py` |
| Delete | `templates/academic.md` |
| Delete | `templates/paper.md` |

---

### Task 1: Delete dead files and verify

**Files:**
- Delete: `bookmarks/cli.py`
- Delete: `bookmarks/structured_output.py`
- Delete: `bookmarks/utils/schema_creator.py`
- Delete: `templates/academic.md`
- Delete: `templates/paper.md`

- [ ] **Step 1: Confirm nothing imports the files being deleted**

```bash
grep -r "from bookmarks import cli\|from bookmarks.cli\|import cli" bookmarks/ api_server.py
grep -r "from bookmarks import structured_output\|structured_output" bookmarks/ api_server.py
grep -r "schema_creator" bookmarks/ api_server.py
grep -r "academic\.md" bookmarks/ api_server.py
```

Expected: no matches for any of these. If any match is found, stop and report before proceeding.

- [ ] **Step 2: Run existing tests to establish a passing baseline**

```bash
uv run pytest tests/ -v
```

Expected output:
```
5 passed in 0.XX s
```

- [ ] **Step 3: Delete the five files**

```bash
git rm bookmarks/cli.py \
       bookmarks/structured_output.py \
       bookmarks/utils/schema_creator.py \
       templates/academic.md \
       templates/paper.md
```

Expected: each line prints `rm '<file>'`, exit 0.

- [ ] **Step 4: Verify tests still pass**

```bash
uv run pytest tests/ -v
```

Expected: same 5 passed, no new failures.

- [ ] **Step 5: Verify listener and api_server still import cleanly**

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
git commit -m "chore: delete dead and accidental files"
```
