
---
title: Documentation Standards
description: Mandatory rules for any AI agent creating or modifying documentation files
status: active
category: rule
tags: [ai-first, agent, doc-standards]
last-verified: 2026-08-17
trigger: always_on
---
# AI-First Documentation Standards

> **Purpose:** Mandatory directives for any AI agent (Antigravity, Cursor, Hermes) creating or modifying `.md` files in this repository.

## 1. Frontmatter is Mandatory

Every new `.md` file **must** start with YAML frontmatter using the full schema:

```yaml
---
title: English Title (primary key for AI routing)
description: One-line English purpose summary (for AI routing)
status: active | pending | done | future
category: runbook | architecture | model | phase | reference | security | status | rule | index
tags: [keyword1, keyword2, keyword3]
last-verified: YYYY-MM-DD
summary-ru: Optional Russian summary for humans (1-2 lines)
summary-uz: Optional Uzbek summary for humans (1-2 lines)
related:
  - path/to/related-file.md
---
```

## 2. English `title` and `description` Required

- **`title`**: Always in English. Primary key for AI routing and indexing.
- **`description`**: Always in English (one line, no markdown).

## 3. Language Convention

- **Document body:** English (AI-first processing language)
- **Code blocks, commands, YAML:** English (universal)
- **Summaries:** `summary-ru` / `summary-uz` in frontmatter for human operators.

## 4. No Orphan Files & Update AGENTS.md

Every file must be indexed in `README.md` or `AGENTS.md`.
