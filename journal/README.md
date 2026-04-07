# Journal Format

Use one Markdown file per day in this directory:

- `YYYY-MM-DD.md`

Each entry should use the same section order:

1. `# YYYY-MM-DD`
2. `## Context`
3. `## Notes`
4. `## Questions`
5. `## Tasks`
6. `## Next steps`

## Section guidance

### `## Context`

- Record the current project context and why the discussion matters.
- List the main files, modules, or references involved.

### `## Notes`

- Capture conclusions, design reasoning, and technical explanations from the discussion.
- Keep this section factual and durable.

### `## Questions`

- Record unresolved design questions or places where we need to make a choice.

### `## Tasks`

- Use Markdown checkboxes for actionable follow-ups.
- Format tasks like:

```md
- [ ] TODO(wkerr): Short description.
```

### `## Next steps`

- Record the most likely immediate implementation steps.
- Keep this short and practical.

## Template

```md
# YYYY-MM-DD

## Context

Short summary of the current topic and relevant files.

## Notes

- Durable notes from the discussion.

## Questions

- Open design question.

## Tasks

- [ ] TODO(wkerr): Follow-up task.

## Next steps

- Immediate implementation step.
```
