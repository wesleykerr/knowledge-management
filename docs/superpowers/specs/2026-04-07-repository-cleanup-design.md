# Repository Cleanup Design

**Date:** 2026-04-07
**Status:** Approved

## Summary

Remove files that don't belong to any of the three components that make up this repository: the Chrome extension, the API endpoint, and the knowledge-listener process. All five files are either dead code (not imported anywhere) or accidental commits.

## The Three Components

1. **Chrome extension** — `extension/`
2. **API endpoint** — `api_server.py` + `bookmarks/utils/secret_creation.py`
3. **Listener process** — `bookmarks/listener.py`, processors (default, twitter), utils (llm, urls, images), models, constants, templates (article, twitter, prompts/default), scripts

## Files to Delete

| File | Reason |
|---|---|
| `bookmarks/cli.py` | References `bookmark_processor` module that doesn't exist — dead CLI never wired up |
| `bookmarks/structured_output.py` | Scratch dev file with hard-coded blog content and arxiv URL; not imported anywhere |
| `bookmarks/utils/schema_creator.py` | Old OpenAI schema utility with stale `arxiv_url` field; not imported anywhere |
| `templates/academic.md` | Was the arxiv note template; orphaned when arxiv processor was deleted |
| `templates/paper.md` | An actual research note accidentally committed to the repo |

## Approach

Single `git rm` of all five files in one commit. No code changes required — nothing imports any of these files.

## Out of Scope

- No changes to `bookmarks/models.py` or `bookmarks/utils/migrations.py` (these serve the listener's LLM audit logging)
- No changes to `scripts/` service files
- No changes to untracked files (`agentic-update.md`, `evolution.md`) — those are outside git's purview
