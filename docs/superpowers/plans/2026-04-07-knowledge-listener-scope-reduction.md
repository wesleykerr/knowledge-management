# Knowledge Listener Scope Reduction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove arxiv and youtube URL processing from the knowledge-listener pipeline by filtering them out at the api_server before they ever hit disk.

**Architecture:** Add an inline URL check in `api_server.py`'s `add_bookmark()` endpoint; strip arxiv/youtube branches from `listener.py`; delete the now-dead processor files, templates, and their package dependencies.

**Tech Stack:** Python, Flask, pytest (for new api_server tests), uv (dependency management)

---

## File Map

| Action | Path |
|--------|------|
| Modify | `api_server.py` |
| Create | `tests/test_api_server.py` |
| Modify | `bookmarks/listener.py` |
| Delete | `bookmarks/processors/arxiv.py` |
| Delete | `bookmarks/processors/arxiv_test.py` |
| Delete | `bookmarks/processors/youtube.py` |
| Delete | `templates/prompts/arxiv.md` |
| Delete | `templates/prompts/youtube.md` |
| Delete | `templates/youtube.md` |
| Modify | `pyproject.toml` |

---

### Task 1: Add URL filtering to api_server.py

**Files:**
- Modify: `api_server.py` (around line 102, inside `add_bookmark()`)
- Create: `tests/test_api_server.py`

- [ ] **Step 1: Create the test file**

Create `tests/test_api_server.py`:

```python
# Standard Library
import json
import os
import sys

# Third Party
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import api_server


@pytest.fixture
def client():
    api_server.app.config["TESTING"] = True
    # Override API key for tests
    api_server.API_KEY = "test-key"
    with api_server.app.test_client() as client:
        yield client


def auth_headers():
    return {"Authorization": "Bearer test-key", "Content-Type": "application/json"}


def test_arxiv_url_is_skipped(client, tmp_path, monkeypatch):
    monkeypatch.setattr(api_server, "OUTPUT_DIR", str(tmp_path))

    response = client.post(
        "/api/bookmark",
        data=json.dumps({"url": "https://arxiv.org/abs/2410.21228", "html_content": "<html/>"}),
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["skipped"] is True
    assert list(tmp_path.iterdir()) == []  # no file written


def test_youtube_url_is_skipped(client, tmp_path, monkeypatch):
    monkeypatch.setattr(api_server, "OUTPUT_DIR", str(tmp_path))

    response = client.post(
        "/api/bookmark",
        data=json.dumps({"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "html_content": "<html/>"}),
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["skipped"] is True
    assert list(tmp_path.iterdir()) == []


def test_regular_url_is_queued(client, tmp_path, monkeypatch):
    monkeypatch.setattr(api_server, "OUTPUT_DIR", str(tmp_path))

    response = client.post(
        "/api/bookmark",
        data=json.dumps({"url": "https://example.com/article", "html_content": "<html/>"}),
        headers=auth_headers(),
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data.get("skipped") is None
    assert len(list(tmp_path.iterdir())) == 1  # file was written


def test_missing_api_key_returns_401(client):
    response = client.post(
        "/api/bookmark",
        data=json.dumps({"url": "https://example.com"}),
        content_type="application/json",
    )
    assert response.status_code == 401


def test_missing_url_returns_400(client):
    response = client.post(
        "/api/bookmark",
        data=json.dumps({"html_content": "<html/>"}),
        headers=auth_headers(),
    )
    assert response.status_code == 400
```

- [ ] **Step 2: Run the tests to confirm they fail**

```bash
python -m pytest tests/test_api_server.py -v
```

Expected: `test_arxiv_url_is_skipped` and `test_youtube_url_is_skipped` fail because the filter doesn't exist yet. `test_regular_url_is_queued`, `test_missing_api_key_returns_401`, and `test_missing_url_returns_400` may pass or fail depending on current state.

- [ ] **Step 3: Add the URL filter to api_server.py**

In `api_server.py`, inside `add_bookmark()`, add the skip check immediately after `url = data["url"]` (around line 107):

```python
        url = data["url"]
        html_content = data.get("html_content")
        screenshot = data.get("screenshot")  # This will be a base64 encoded PNG

        # arxiv and youtube are handled independently; no HTML needed
        if "arxiv.org" in url.lower() or "youtube.com" in url.lower():
            logger.info(f"Skipping unsupported URL type: {url}")
            return jsonify({"success": True, "skipped": True})
```

The full `add_bookmark()` function body after this change:

```python
@app.route("/api/bookmark", methods=["POST", "OPTIONS"])
@require_api_key
def add_bookmark():
    if request.method == "OPTIONS":
        return handle_preflight()

    try:
        data = request.get_json()
        logger.info(
            f"Request data: URL={data.get('url')}, "
            f"HTML Content Length={len(data.get('html_content', ''))}, "
            f"Screenshot Length={len(data.get('screenshot', ''))}"
        )

        if not data or "url" not in data:
            logger.error("No URL provided in request")
            return jsonify({"error": "No URL provided"}), 400

        url = data["url"]
        html_content = data.get("html_content")
        screenshot = data.get("screenshot")  # This will be a base64 encoded PNG

        # arxiv and youtube are handled independently; no HTML needed
        if "arxiv.org" in url.lower() or "youtube.com" in url.lower():
            logger.info(f"Skipping unsupported URL type: {url}")
            return jsonify({"success": True, "skipped": True})

        try:
            filename = generate_filename(url)
            output_path = os.path.join(OUTPUT_DIR, filename)
            with open(output_path, "w") as output_io:
                json.dump(data, output_io)

            logger.info("Successfully processed bookmark")
            return jsonify({"success": True})
        except Exception as e:
            logger.error("Error processing request: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        logger.error("Error parsing request: %s", str(e))
        return jsonify({"error": "Invalid request format"}), 400
```

- [ ] **Step 4: Run the tests to confirm they all pass**

```bash
python -m pytest tests/test_api_server.py -v
```

Expected output:
```
tests/test_api_server.py::test_arxiv_url_is_skipped PASSED
tests/test_api_server.py::test_youtube_url_is_skipped PASSED
tests/test_api_server.py::test_regular_url_is_queued PASSED
tests/test_api_server.py::test_missing_api_key_returns_401 PASSED
tests/test_api_server.py::test_missing_url_returns_400 PASSED
5 passed
```

- [ ] **Step 5: Commit**

```bash
git add api_server.py tests/test_api_server.py
git commit -m "feat: skip arxiv and youtube URLs in api_server"
```

---

### Task 2: Remove arxiv and youtube from listener.py

**Files:**
- Modify: `bookmarks/listener.py`

- [ ] **Step 1: Edit listener.py**

Remove the two import lines at the top of `bookmarks/listener.py`:

```python
# DELETE these two lines:
from bookmarks.processors import arxiv
from bookmarks.processors import youtube
```

Replace the body of `process_file()` — remove the arxiv and youtube branches. The function should become:

```python
def process_file(file_path: str):
    for attempt in range(3):
        try:
            with open(file_path, "r") as input_io:
                data = json.load(input_io)
        except json.JSONDecodeError:
            if attempt < 2:
                time.sleep(0.1)
                continue
            else:
                raise

    print(data["url"])
    if twitter.is_twitter_url(data["url"]):
        print("twitter")
        twitter.process_twitter_url(data["url"], data["html_content"], data["screenshot"])
    else:
        default.process_url(data["url"], data["html_content"])
    os.remove(file_path)
```

- [ ] **Step 2: Verify the module imports cleanly**

```bash
python -c "from bookmarks import listener; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add bookmarks/listener.py
git commit -m "refactor: remove arxiv and youtube branches from listener"
```

---

### Task 3: Delete dead processor files and templates

**Files to delete:**
- `bookmarks/processors/arxiv.py`
- `bookmarks/processors/arxiv_test.py`
- `bookmarks/processors/youtube.py`
- `templates/prompts/arxiv.md`
- `templates/prompts/youtube.md`
- `templates/youtube.md`

- [ ] **Step 1: Delete the files**

```bash
git rm bookmarks/processors/arxiv.py \
       bookmarks/processors/arxiv_test.py \
       bookmarks/processors/youtube.py \
       templates/prompts/arxiv.md \
       templates/prompts/youtube.md \
       templates/youtube.md
```

- [ ] **Step 2: Verify nothing imports the deleted modules**

```bash
python -m pytest tests/test_api_server.py -v
python -c "from bookmarks import listener; print('OK')"
```

Expected: all 5 tests pass, listener imports cleanly.

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: delete arxiv and youtube processors and templates"
```

---

### Task 4: Remove unused dependencies from pyproject.toml

**Files:**
- Modify: `pyproject.toml`

These packages are now only referenced by the deleted files:
- `arxiv>=2.2.0`
- `google-api-python-client>=2.171.0`
- `marker-pdf[full]==1.7.4`
- `youtube-transcript-api>=1.0.3`

- [ ] **Step 1: Remove the four dependencies from pyproject.toml**

In `pyproject.toml`, remove these four lines from the `dependencies` list:

```toml
    "arxiv>=2.2.0",
    "google-api-python-client>=2.171.0",
    "marker-pdf[full]==1.7.4",
    "youtube-transcript-api>=1.0.3",
```

- [ ] **Step 2: Sync the lockfile**

```bash
uv sync
```

Expected: uv removes the packages without errors.

- [ ] **Step 3: Run tests one final time**

```bash
python -m pytest tests/test_api_server.py -v
python -c "from bookmarks import listener; print('OK')"
```

Expected: all 5 tests pass, listener imports cleanly.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: remove arxiv, youtube, and marker-pdf dependencies"
```
