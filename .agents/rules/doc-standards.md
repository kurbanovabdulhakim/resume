---
title: Documentation and Template Standards
description: Guidelines for documentation format, template placeholders, and auto-generated state files.
status: active
category: rule
last-verified: 2026-11-08
---

# Documentation & Template Standards (`resume`)

---

## 1. Document Frontmatter Schema
Core repository markdown documents (guides, runbooks, schemas) should begin with concise YAML frontmatter:

```yaml
---
title: Concise Document Title
description: Single-line summary of purpose
status: active | draft | future
category: runbook | architecture | rule | reference
last-verified: YYYY-MM-DD
---
```

---

## 2. Template Conventions (`cover_letters/` & `variants/`)
- Placeholders must strictly use the double curly brace syntax: `{{variable_name}}`.
- Supported standard placeholders:
  - `{{company}}` — Target employer name
  - `{{position}}` — Job title
  - `{{sector_hook}}` — Opening paragraph tailored to industry/sector
  - `{{key_achievement}}` — Metric-driven achievement highlight
  - `{{salary_expectation}}` — Desired compensation
  - `{{candidate_name}}` — Abdulkhakim Kurbanov
  - `{{date}}` — Generation date
- Templates must document their placeholders in an HTML comment block at the top of the file.

---

## 3. Auto-Generated Files
- `AI_CONTEXT.md`, `PIPELINE.md`, and `dashboard.html` are generated programmatically by `scripts/dashboard.py`.
- **Never edit these files by hand.** Always run `python scripts/dashboard.py` to regenerate them after updating the database.

---

## 4. Language & Link Standards
- **Architecture, scripts & runbooks:** English.
- **Master Resume & CV Variants:** Russian (with English variants if needed).
- **Cover Letters:** Target language of the employer (Russian / Uzbek / English).
- **Link Integrity:** Always reference workspace files using canonical relative paths (e.g., `db/schema.sql`, `scripts/config.py`).
