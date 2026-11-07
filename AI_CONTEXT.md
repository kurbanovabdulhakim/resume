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
  "generated_at": "2026-11-08T00:20:35.200332",
  "database": "db/positions.db",
  "vacancies_total": 1,
  "active_vacancies": 1,
  "total_vacancies": 1,
  "applications_total": 1,
  "total_applications": 1,
  "statuses": {
    "applied": 0,
    "viewed": 0,
    "invited": 1,
    "interview": 0,
    "offer": 0,
    "rejected": 0,
    "declined": 0
  },
  "tier_distribution": {
    "1": 1,
    "2": 0,
    "3": 0
  },
  "sector_distribution": {
    "Finance": 1
  },
  "urgent_leads_count": 1,
  "urgent_leads": [
    {
      "id": "888777",
      "company": "Apex Insurance",
      "title": "Lead Financial Controller",
      "status": "invited",
      "notes": "Direct outreach from partner\n[2026-11-08T00:20:35.023084] Interview scheduled with Head of Finance"
    }
  ],
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
