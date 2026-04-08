# Web Article Processor: Claude Code Handoff Design

**Date:** 2026-04-07
**Status:** Approved

## Overview

Replace the OpenAI API call in `knowledge/processors/webpage.py` with a staged-file handoff to a
Claude Code subprocess. Python handles all mechanical pre-processing; Claude handles classification,
summarization, and writing the final Obsidian note.

## Architecture

```
Chrome ext → Flask API → JSON file → listener.py
                                          ↓
                               webpage.py (Python)
                                 1. readability extraction
                                 2. markdownify
                                 3. image localization
                                 4. write staged JSON → data/staged/<url_hash>.json
                                          ↓
                               subprocess: claude -p "..."
                                          ↓
                               web-article skill (Claude)
                                 1. read staged JSON
                                 2. classify into folder taxonomy
                                 3. generate title slug
                                 4. write Obsidian note → <vault>/<folder>/<slug>.md
                                 5. move web_page_dir → <vault>/<folder>/<slug>/
                                 6. delete staged JSON
```

Python exits after the subprocess call. It has no knowledge of what Claude decided. The staged file
is the complete handoff contract between Python and Claude.

## Staged File Format

Written to `data/staged/<url_hash>.json`:

```json
{
  "url": "https://example.com/article",
  "url_hash": "abc123def456...",
  "readability_markdown": "# Article Title\n\nClean article text...",
  "web_page_dir": "data/web-pages/abc123def456.../",
  "staged_at": "2026-04-07T14:32:00"
}
```

- `readability_markdown` — clean article text from `readabilipy` + `markdownify`; what Claude reads to understand the content
- `web_page_dir` — **absolute path** to the directory Python wrote (`raw.html`, `readability.md`, `article.md`); Claude moves this to the vault after classification
- `url_hash` — used only to locate the `web_page_dir`; not used as an output filename

## Output Naming

Claude derives a kebab-case slug from the article title (e.g. `attention-is-all-you-need`). Both
output artifacts share this slug:

- Summary note: `<vault>/<folder>/<slug>.md`
- Content dir: `<vault>/<folder>/<slug>/` (contains `article.md`, `raw.html`, `readability.md`)

## Python Changes

### `knowledge/processors/webpage.py`

Replace lines 162–199 (the "Create Metadata and Summary" section through `os.rename`) with:

1. Ensure `data/staged/` directory exists
2. Write staged JSON to `data/staged/<url_hash>.json`
3. `subprocess.run(["claude", "-p", f"Process the web article staged at data/staged/{url_hash}.json using the web-article skill"], check=True)`

Delete:
- `ExpectedOutput`, `Metadata`, `PublicationInfo`, `Folder`, `DocumentType`, `SourceType`,
  `ConfidenceLevel` Pydantic models and enums — only existed to parse OpenAI structured output
- Jinja2 template rendering for the note (moves to skill)
- `base.get_filename()` call — naming moves to skill
- `os.rename()` call — directory move moves to skill

Keep:
- All readability extraction, markdownify, image localization logic (lines 141–158)
- Writing `raw.html` and `article.md` to `data/web-pages/<url_hash>/`

### `knowledge/utils/llm.py`

Delete:
- `call_llm()` — no longer called
- `call_structured_llm()` — no longer called
- `tiktoken` import and `tokenizer` setup
- `openai` import

Keep:
- `call_structured_llm_with_pdf()` — still used for PDF processing via Anthropic SDK
- `get_url_hash()`, `get_content_hash()` — still used
- `anthropic`, `httpx`, `pydantic` imports (needed by PDF function)

## Skill: `web-article`

**Location:** `/Users/wkerr/sync/Obsidian/.claude/skills/web-article/SKILL.md`

### Workflow

1. Read the staged JSON at the path provided in the prompt
2. Read `readability_markdown` to understand the content
3. Classify into the folder taxonomy (inline — do not invoke sub-skills)
4. Generate a kebab-case slug from the title
5. Write the Obsidian summary note to `<vault>/<folder>/<slug>.md`
6. Move `web_page_dir` → `<vault>/<folder>/<slug>/`
7. Delete the staged JSON

### Folder Taxonomy

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

### Note Template

```markdown
---
content-type: article
tags: [article, <kebab-case topic tags>]
date: <YYYY-MM-DD today>
source: <url>
title: "<title>"
folder: <folder>
read: false
read-date:
priority: 1
---

# <title>

> [!abstract] One-line hook
> <Core claim or what makes this worth reading>

**Source:** [<publisher/domain>](<url>)
**Published:** <date if available>

## Summary

<3–5 narrative paragraphs: context/motivation, main argument, supporting evidence, implications.
Written from reading the content — not a reformatted lede.>

## Key Points

- <point>
- <point>
- <point>

## Highlights for Wes

**Directly relevant:**
- **<Topic>**: <Specific takeaway connected to Wes's role>

**Tangentially useful:**
- <Lighter connections>

## Related Notes

<Wikilinks to relevant vault notes with one-line rationale>

## Questions & Follow-ups

<Specific, actionable questions tied to Wes's work at Riot>
```

### Personalization for Wes

Wes is **Head of Technology Research at Riot Games** with a PhD in CS (AI × games). Prioritize:

- AI for games, NPC behavior, RL in games, procedural content, world modeling, embodied agents
- LLMs & agents: practical agentic systems, tool use, reasoning, multi-agent architectures
- Research strategy, long-term bets, academia-industry collaboration
- Leadership: managing research teams, communicating technical vision
- Foundational models: capability curves, architecture trends, fine-tuning, eval methods
- Player experience: engagement, recommendation systems, personalization at scale
- Industry moves: EA SEED, DeepMind, Google DeepMind, OpenAI, game studio AI initiatives
- Riot-specific themes: VALORANT bots, embodied agents, League of Legends recommenders

## What Does Not Change

- `listener.py` — no changes
- `twitter.py` — no changes (no LLM calls)
- `models.py` — no changes
- `templates/` — article.md template can be removed once skill is in use; no immediate action needed
- Chrome extension — no changes
- Flask API server (`server.py`) — no changes
- Obsidian vault folder structure — no changes
