# Web Article Claude Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the OpenAI API call in `webpage.py` with a staged-file handoff to a Claude Code subprocess that writes the final Obsidian note directly.

**Architecture:** Python handles all mechanical work (readability extraction, markdownify, image localization) and writes a staged JSON file. It then invokes `claude -p "..."` as a subprocess. Claude loads the `web-article` skill, classifies the content, and writes the note and content directory to the Obsidian vault.

**Tech Stack:** Python stdlib `subprocess`, `json`, `pathlib`; `readabilipy`, `markdownify`; Claude Code CLI; Obsidian vault at `/Users/wkerr/sync/Obsidian/wkerr-kg`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `tests/test_webpage_processor.py` | Create | Tests for staged JSON content and subprocess invocation |
| `knowledge/constants.py` | Modify | Add `STAGED_PATH` |
| `knowledge/processors/webpage.py` | Modify | Remove Pydantic models/enums, replace LLM section with staging + subprocess |
| `knowledge/utils/llm.py` | Modify | Remove `call_llm`, `call_structured_llm`, `tiktoken`, `openai` |
| `pyproject.toml` | Modify | Remove `openai` and `tiktoken` dependencies |
| `/Users/wkerr/sync/Obsidian/.claude/skills/web-article/SKILL.md` | Create | Skill that reads staged JSON and writes vault note |

---

## Task 1: Write failing tests for new `process_url()` behavior

**Files:**
- Create: `tests/test_webpage_processor.py`

- [ ] **Step 1: Create the test file**

```python
# tests/test_webpage_processor.py

# Standard Library
import hashlib
import json
import subprocess
from pathlib import Path
from unittest import mock

# Third Party
import pytest


@pytest.fixture(autouse=True)
def patch_paths(tmp_path, monkeypatch):
    from knowledge import constants

    monkeypatch.setattr(constants, "WEB_PAGE_PATH", str(tmp_path / "web-pages"))
    monkeypatch.setattr(constants, "STAGED_PATH", str(tmp_path / "staged"))


@pytest.fixture(autouse=True)
def mock_readability():
    with mock.patch("readabilipy.simple_json_from_html_string") as m:
        m.return_value = {"plain_content": "<p>Test article content.</p>"}
        yield m


@pytest.fixture(autouse=True)
def mock_images():
    with mock.patch("knowledge.utils.images.process_article_images") as m:
        m.side_effect = lambda url_hash, html, url: html
        yield m


@pytest.fixture
def mock_subprocess():
    with mock.patch("subprocess.run") as m:
        yield m


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def test_process_url_writes_staged_json(mock_subprocess, tmp_path):
    from knowledge.processors import webpage

    url = "https://example.com/article"
    html = "<html><body><p>Test article content.</p></body></html>"

    webpage.process_url(url, html)

    url_hash = _url_hash(url)
    staged_file = tmp_path / "staged" / f"{url_hash}.json"

    assert staged_file.exists(), "staged JSON file was not written"
    data = json.loads(staged_file.read_text())

    assert data["url"] == url
    assert data["url_hash"] == url_hash
    assert "readability_markdown" in data
    assert len(data["readability_markdown"]) > 0
    assert "web_page_dir" in data
    assert Path(data["web_page_dir"]).is_absolute(), "web_page_dir must be an absolute path"
    assert "staged_at" in data


def test_process_url_invokes_claude_with_staged_path(mock_subprocess, tmp_path):
    from knowledge.processors import webpage

    url = "https://example.com/article"
    html = "<html><body><p>Test article content.</p></body></html>"

    webpage.process_url(url, html)

    url_hash = _url_hash(url)
    staged_path = str(tmp_path / "staged" / f"{url_hash}.json")

    mock_subprocess.assert_called_once()
    cmd = mock_subprocess.call_args[0][0]
    kwargs = mock_subprocess.call_args[1]

    assert cmd[0] == "claude"
    assert cmd[1] == "-p"
    assert staged_path in cmd[2]
    assert "web-article" in cmd[2]
    assert kwargs.get("check") is True


def test_process_url_writes_web_page_files(mock_subprocess, tmp_path):
    from knowledge.processors import webpage

    url = "https://example.com/article"
    html = "<html><body><p>Test article content.</p></body></html>"

    webpage.process_url(url, html)

    url_hash = _url_hash(url)
    web_page_dir = tmp_path / "web-pages" / url_hash

    assert (web_page_dir / "raw.html").exists()
    assert (web_page_dir / "readability.md").exists()
    assert (web_page_dir / "article.md").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_webpage_processor.py -v
```

Expected: `ImportError` or `AttributeError` — `STAGED_PATH` doesn't exist yet and `process_url` still calls the LLM.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_webpage_processor.py
git commit -m "test: add failing tests for web article Claude handoff"
```

---

## Task 2: Add `STAGED_PATH` to `constants.py`

**Files:**
- Modify: `knowledge/constants.py`

- [ ] **Step 1: Add `STAGED_PATH` to constants**

In `knowledge/constants.py`, add after the existing imports:

```python
STAGED_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "staged")
```

The full file after edit:

```python
# Standard Library
import os
import pathlib

KNOWLEDGE_BASE_PATH = os.path.join(os.path.expanduser("~"), "sync", "Obsidian", "wkerr-kg")
RESEARCH_PAPERS_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "research-papers")
RESEARCH_MARKDOWN_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "research-md")
RESEARCH_NOTES_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "research-notes")

TWITTER_MEDIA_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "twitter/media")
TWITTER_JSON_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "twitter/json")
TWITTER_NOTES_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "twitter/notes")

TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
TWITTER_RAW_PATH = pathlib.Path("/tmp/twitter/raw")

WEB_PAGE_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "web-pages")
WEB_MARKDOWN_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "web-markdown")
WEB_READABILITY_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "web-readability")
WEB_READABILITY_HTML_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "web-readability-html")
WEB_SUMMARY_PATH = os.path.join(KNOWLEDGE_BASE_PATH, "web-notes")

STAGED_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "staged")

FOLDER_STRUCTURE = [
    "AI/DeepLearning/Architectures",
    "AI/DeepLearning/Agents",
    "AI/DeepLearning/GenerativeAI",
    "AI/DeepLearning/GameAI",
    "AI/DeepLearning/ReinforcementLearning",
    "AI/DeepLearning/Safety",
    "AI/DeepLearning/ExplainableAI",
    "AI/Ethics",
    "AI/MachineLearning/Applications",
    "AI/MachineLearning/ClassicalAlgorithms",
    "AI/MachineLearning/Engineering",
    "AI/RecommenderSystems",
    "Personal/Finance",
    "Personal/Health",
    "Personal/Politics",
    "Personal/Entertainment",
    "Professional/Productivity",
    "Professional/SoftwareEngineering",
    "Research/DataScience",
    "Research/Science",
    "Research/Technology",
]
```

- [ ] **Step 2: Commit**

```bash
git add knowledge/constants.py
git commit -m "feat: add STAGED_PATH constant"
```

---

## Task 3: Rewrite `process_url()` in `webpage.py`

**Files:**
- Modify: `knowledge/processors/webpage.py`

- [ ] **Step 1: Replace the entire file contents**

```python
# Standard Library
import datetime
import json
import logging
import os
import subprocess

# Third Party
import click
import markdownify
import peewee
import readabilipy

# Project
from knowledge import constants
from knowledge import models
from knowledge.utils import images
from knowledge.utils import llm
from knowledge.utils import urls

logger = logging.getLogger(__name__)


def process_url(url: str, html_content: str = None) -> None:
    os.makedirs(constants.WEB_PAGE_PATH, exist_ok=True)

    url_hash = llm.get_url_hash(url)
    web_page_dir = os.path.join(constants.WEB_PAGE_PATH, url_hash)
    os.makedirs(web_page_dir, exist_ok=True)

    # 1. HTML content
    if not html_content:
        html_content = urls.get_content(url)

    with open(os.path.join(web_page_dir, "raw.html"), "w") as f:
        f.write(html_content)

    # 2. Readability extraction
    readability_obj = readabilipy.simple_json_from_html_string(html_content, use_readability=True)
    plain_content = readability_obj["plain_content"]
    readability_markdown = markdownify.markdownify(plain_content)
    with open(os.path.join(web_page_dir, "readability.md"), "w") as f:
        f.write(readability_markdown)

    # 3. Full article markdown with localized images
    processed_html = images.process_article_images(url_hash, html_content, url)
    article_markdown = markdownify.markdownify(processed_html)
    with open(os.path.join(web_page_dir, "article.md"), "w") as f:
        f.write(article_markdown)

    # 4. Stage for Claude
    os.makedirs(constants.STAGED_PATH, exist_ok=True)
    staged_path = os.path.join(constants.STAGED_PATH, f"{url_hash}.json")
    staged_data = {
        "url": url,
        "url_hash": url_hash,
        "readability_markdown": readability_markdown,
        "web_page_dir": os.path.abspath(web_page_dir),
        "staged_at": datetime.datetime.now().isoformat(),
    }
    with open(staged_path, "w") as f:
        json.dump(staged_data, f, indent=2)

    # 5. Invoke Claude to classify, summarize, and write vault note
    subprocess.run(
        [
            "claude",
            "-p",
            f"Process the web article staged at {staged_path} using the web-article skill",
        ],
        check=True,
    )


@click.command()
@click.argument("url")
@click.option(
    "--html-content", default=None, help="Optional HTML content to process instead of downloading"
)
def process(url: str, html_content: str = None):
    """Process a URL and generate a markdown summary."""
    db = peewee.SqliteDatabase("data/database.db")
    models.db.initialize(db)

    try:
        process_url(url, html_content)
        click.echo(f"Successfully processed URL: {url}")
    except Exception as e:
        click.echo(f"Error processing URL: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    process()
```

- [ ] **Step 2: Run the tests**

```bash
uv run pytest tests/test_webpage_processor.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 3: Run the full test suite to check for regressions**

```bash
uv run pytest -v
```

Expected: All tests pass (including `tests/test_api_server.py`).

- [ ] **Step 4: Commit**

```bash
git add knowledge/processors/webpage.py
git commit -m "feat: replace OpenAI call with staged JSON + Claude subprocess in webpage processor"
```

---

## Task 4: Remove unused functions from `llm.py`

**Files:**
- Modify: `knowledge/utils/llm.py`

- [ ] **Step 1: Replace the file, removing `call_llm`, `call_structured_llm`, tiktoken, and openai**

```python
# Standard Library
import base64
import hashlib
import json

# Third Party
import anthropic
import httpx
import pydantic

# Project
from knowledge import models


def get_url_hash(url):
    return hashlib.sha256(url.encode()).hexdigest()


def get_content_hash(content, prompt_template, max_tokens):
    hash_string = f"{content}|{prompt_template}|{max_tokens}"
    return hashlib.sha256(hash_string.encode()).hexdigest()


def call_structured_llm_with_pdf(
    url_hash: str,
    system_prompt: str,
    user_prompt: str,
    pdf_url: str,
    response_format: pydantic.BaseModel = None,
) -> pydantic.BaseModel:
    model = "claude-3-5-sonnet-20241022"
    pdf_data = base64.standard_b64encode(httpx.get(pdf_url).content).decode("utf-8")

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_data,
                    },
                },
                {
                    "type": "text",
                    "text": user_prompt,
                },
            ],
        },
        {"role": "assistant", "content": "Here is the JSON requested:\n{"},
    ]

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=model,
        betas=["pdfs-2024-09-25"],
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )
    json_string = "{" + response.content[0].text
    try:
        summary_obj = response_format.model_validate_json(json_string)
    except Exception as e:
        print(e)
        print(json_string)
        raise e
    print(summary_obj)

    audit = models.ChatPromptAudit.create(
        response_id=response.id,
        url_hash=url_hash,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        content_tokens=0,
        total_tokens=0,
        output=json_string,
    )
    audit.save()
    return response.id, summary_obj
```

- [ ] **Step 2: Run the full test suite**

```bash
uv run pytest -v
```

Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add knowledge/utils/llm.py
git commit -m "chore: remove call_llm and call_structured_llm, drop openai/tiktoken from llm.py"
```

---

## Task 5: Remove `openai` and `tiktoken` from dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Remove the two dependencies from `pyproject.toml`**

In the `dependencies` list, remove these two lines:
```
    "openai>=1.82.1",
    "tiktoken>=0.9.0",
```

- [ ] **Step 2: Sync the environment**

```bash
uv sync
```

Expected: uv removes openai and tiktoken from the environment.

- [ ] **Step 3: Run the full test suite to verify nothing is broken**

```bash
uv run pytest -v
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: remove openai and tiktoken dependencies"
```

---

## Task 6: Create the `web-article` skill

**Files:**
- Create: `/Users/wkerr/sync/Obsidian/.claude/skills/web-article/SKILL.md`

- [ ] **Step 1: Create the skill directory and file**

```bash
mkdir -p "/Users/wkerr/sync/Obsidian/.claude/skills/web-article"
```

- [ ] **Step 2: Write the skill file**

Create `/Users/wkerr/sync/Obsidian/.claude/skills/web-article/SKILL.md`:

```markdown
---
name: web-article
description: >
  Reads a staged web article JSON file, classifies it into the knowledge base folder structure,
  and writes a personalized Obsidian summary note with the article content alongside.
---

Base directory for this skill: /Users/wkerr/sync/Obsidian/.claude/skills/web-article

# Web Article Skill

Reads a staged web article, classifies it, and writes a personalized Obsidian summary note.

Produces two artifacts per article, both stored under the classified folder:
- **Content directory**: `<vault>/<folder>/<slug>/` (contains `article.md`, `raw.html`, `readability.md`)
- **Obsidian summary note**: `<vault>/<folder>/<slug>.md`

The `<slug>` is a kebab-case name derived from the article title (e.g. `attention-is-all-you-need`).
Both artifacts share the same slug so they are co-located and named consistently.

## Workflow

### Step 1 — Read the staged file

Read the JSON file at the path given in the prompt. Extract:
- `url` — original URL
- `url_hash` — used to locate `web_page_dir`
- `readability_markdown` — clean article text for reading and summarization
- `web_page_dir` — absolute path to the directory containing `article.md`, `raw.html`, `readability.md`

### Step 2 — Read the article content

Read `readability_markdown` from the staged data. This is the cleaned, readable version of the
article. Use it for classification, summarization, and writing the summary note.

### Step 3 — Classify the article

Using your reading of the content, pick the single best-fit folder from this taxonomy:

```
AI/DeepLearning/Architectures
AI/DeepLearning/Agents
AI/DeepLearning/GenerativeAI
AI/DeepLearning/GameAI
AI/DeepLearning/ReinforcementLearning
AI/DeepLearning/Safety
AI/DeepLearning/ExplainableAI
AI/Ethics
AI/MachineLearning/Applications
AI/MachineLearning/ClassicalAlgorithms
AI/MachineLearning/Engineering
AI/RecommenderSystems
Personal/Finance
Personal/Health
Personal/Politics
Personal/Entertainment
Professional/Productivity
Professional/SoftwareEngineering
Research/DataScience
Research/Science
Research/Technology
```

Rules:
- Prefer the most specific applicable folder
- Base choice on primary topic, not peripheral themes
- For interdisciplinary content, choose by primary audience/purpose

Also select 3–8 kebab-case topic tags for the note frontmatter.

### Step 4 — Generate the slug

Derive a kebab-case slug from the article title. Keep it short and meaningful (4–7 words max).
Example: "Why Transformers Work So Well" → `why-transformers-work-so-well`

### Step 5 — Move the content directory

```bash
VAULT="/Users/wkerr/sync/Obsidian/wkerr-kg"
FOLDER="<folder>"   # e.g. AI/DeepLearning/Agents
SLUG="<slug>"
WEB_PAGE_DIR="<web_page_dir from staged JSON>"

mkdir -p "$VAULT/$FOLDER/$SLUG"
mv "$WEB_PAGE_DIR"/* "$VAULT/$FOLDER/$SLUG/"
rmdir "$WEB_PAGE_DIR"
```

### Step 6 — Write the Obsidian summary note

Output path: `/Users/wkerr/sync/Obsidian/wkerr-kg/<folder>/<slug>.md`

Write the summary from your own reading of the article. Do NOT use boilerplate. Every section
should reflect the actual content of this specific article.

Use Obsidian Flavored Markdown (frontmatter, wikilinks, callouts).

#### Note template

```markdown
---
content-type: article
tags: [article, <kebab-case topic tags>]
date: <YYYY-MM-DD today>
source: <url>
title: "<title>"
folder: <folder>
content: "[[<folder>/<slug>/article.md]]"
read: false
read-date:
priority: 1
---

# <title>

> [!abstract] One-line hook
> <The core claim or result in one punchy sentence — what makes this worth reading>

**Source:** [<publisher or domain>](<url>)
**Published:** <date if available, otherwise omit>

## Summary

<3–5 narrative paragraphs covering: context and motivation, main argument or findings, supporting
evidence, implications. Write this in your own words from reading the article — not a reformatted
lede. Tell the story of what the author is saying and why it matters.>

## Key Points

- <point>
- <point>
- <point>
- <point>
- <point>

## Highlights for Wes

**Directly relevant:**
- **<Bold topic name>**: <Specific, concrete takeaway connected to Wes's role — not generic>

**Tangentially useful:**
- <Lighter connections — methods or ideas that could transfer even if the domain is different>

If the article has little directly relevant content, say so honestly and highlight the most
tangentially useful ideas.

## Related Notes

<Wikilinks to relevant vault notes with a one-line note on why each is relevant. Search the vault:
Glob: /Users/wkerr/sync/Obsidian/wkerr-kg/**/<topic>.md>

## Questions & Follow-ups

<Specific, actionable questions tied to Wes's work at Riot — experiments to try, things to verify,
or open problems this article raises>
```

#### Personalizing for Wes

Wes is **Head of Technology Research at Riot Games** with a PhD in CS (AI × games). Prioritize
content relevant to:

- **AI for games**: game agents, NPC behavior, RL in games, procedural content, world modeling, embodied agents
- **LLMs & agents**: practical agentic systems, tool use, reasoning, multi-agent architectures
- **Research strategy**: how tech research orgs operate, long-term bets, academia-industry collaboration
- **Leadership**: managing research teams, communicating technical vision, team structure
- **Foundational models**: capability curves, architecture trends, fine-tuning, eval methods
- **Player experience**: engagement, recommendation systems, personalization at scale
- **Industry moves**: EA SEED, DeepMind, Google DeepMind, OpenAI, game studio AI initiatives
- **Riot-specific themes**: VALORANT bots, embodied agents, League of Legends recommenders

### Step 7 — Delete the staged file

```bash
rm "<staged_file_path>"
```

### Step 8 — Return output paths

Tell the user:
- Classified folder and reason for the classification
- Content directory path
- Summary note path
```

- [ ] **Step 3: Verify the file was written correctly**

```bash
head -5 "/Users/wkerr/sync/Obsidian/.claude/skills/web-article/SKILL.md"
```

Expected: YAML frontmatter with `name: web-article`.

- [ ] **Step 4: Commit (from the knowledge-management repo)**

```bash
cd /Users/wkerr/development/knowledge-management
git add docs/superpowers/plans/2026-04-07-web-article-claude-handoff.md
git commit -m "docs: add implementation plan for web-article Claude handoff"
```
