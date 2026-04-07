# Knowledge Listener Scope Reduction

**Date:** 2026-04-07
**Status:** Approved

## Summary

Remove arxiv and youtube processing from the knowledge-listener service. These URL types do not require HTML content (arxiv fetches via its own API and PDF download; youtube fetches via YouTube Data API). Rather than writing unnecessary large JSON payloads to disk and then discarding them, arxiv and youtube URLs will be silently ignored at the API server boundary and never queued.

## Changes

### `api_server.py`

In `add_bookmark()`, add an inline URL check before writing the file to disk:

```python
if "arxiv.org" in url.lower() or "youtube.com" in url.lower():
    logger.info(f"Skipping unsupported URL type: {url}")
    return jsonify({"success": True, "skipped": True})
```

No imports from processor modules. Returns a success response so the browser extension behaves normally.

### `bookmarks/listener.py`

- Remove `from bookmarks.processors import arxiv`
- Remove `from bookmarks.processors import youtube`
- Remove the `arxiv` and `youtube` branches from `process_file()`

`process_file()` becomes: check for twitter → else default.

### Files to Delete

- `bookmarks/processors/arxiv.py`
- `bookmarks/processors/arxiv_test.py`
- `bookmarks/processors/youtube.py`
- `templates/prompts/arxiv.md`
- `templates/prompts/youtube.md`
- `templates/youtube.md`

## Data Flow After Change

```
Browser extension → POST /api/bookmark
    ├── arxiv.org URL  → return {success: true, skipped: true}  (no file written)
    ├── youtube.com URL → return {success: true, skipped: true}  (no file written)
    └── other URL      → write JSON file to ~/sync/inbound/
                              └── listener picks it up
                                      ├── twitter URL → twitter processor
                                      └── other URL   → default processor
```

## Out of Scope

- No changes to the twitter or default processors.
- No new mechanism for processing arxiv or youtube URLs — they are simply ignored.
