---
title: Machine-Readable Agent Context State
description: Real-time autonomous context state snapshot consumed by AI agents to operate on positions.db.
status: active
category: status
tags: [ai-context, agent-first, state, pipeline, automation]
last-verified: 2026-11-08
summary-ru: Машиночитаемый контекст текущего состояния воронки вакансий для ИИ-агентов.
summary-uz: Sun'iy intellekt agentlari uchun vakansiyalar holati bo'yicha mashina o'qiydigan kontekst.
related:
  - AGENTS.md
  - PIPELINE.md
  - db/schema.md
---

# Machine-Readable AI Agent Context

```yaml
{
  "generated_at": "2026-11-08T00:18:36.315592",
  "database": "db/positions.db",
  "vacancies_total": 1533,
  "active_vacancies": 1533,
  "total_vacancies": 1533,
  "applications_total": 107,
  "total_applications": 107,
  "statuses": {
    "applied": 107,
    "viewed": 0,
    "invited": 0,
    "interview": 0,
    "offer": 0,
    "rejected": 0,
    "declined": 0
  },
  "tier_distribution": {
    "1": 93,
    "2": 160,
    "3": 1280
  },
  "sector_distribution": {
    "Analytics": 103,
    "Finance": 312,
    "Logistics": 235,
    "Management": 883
  },
  "urgent_leads_count": 0,
  "urgent_leads": [],
  "recommended_next_actions": [
    "Check urgent_leads to prepare tailored CV and interview prep",
    "To sync new batch from Hermes, run: python scripts/sync_hermes.py --json",
    "To generate tailored docs for vacancy, run: python scripts/generate_docs.py --vacancy-id <id> --json",
    "To record interview or status change: python scripts/update_status.py --vacancy-id <id> --status interview --json"
  ]
}
```

## Quick Reference for Cold Agents
- **Primary Database:** `db/positions.db` (SQLite, tracked in Git)
- **Sync Command:** `python scripts/sync_hermes.py --json`
- **Document Generation:** `python scripts/generate_docs.py --vacancy-id <id> --json`
- **Update Status:** `python scripts/update_status.py --vacancy-id <id> --status <status> --json`
- **Recompile Dashboard:** `python scripts/dashboard.py --json`
