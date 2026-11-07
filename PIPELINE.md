---
title: Job Application Pipeline Summary
description: Live snapshot of active job search pipeline, interview stages, and response rates from positions.db.
status: active
category: status
tags: [pipeline, status, kanban, applications, hermes]
last-verified: 2026-11-08
summary-ru: Сводный отчет о текущем статусе воронки откликов, собеседований и конверсии.
summary-uz: Rezyumelar, suhbat bosqichlari va konversiya holati bo'yicha jonli hisobot.
related:
  - AGENTS.md
  - AI_CONTEXT.md
  - db/schema.md
  - dashboard.html
---

# Job Application Pipeline Summary

> **Auto-generated:** `2026-11-08T00:20:35.199828`  
> **Single Source of Truth:** `db/positions.db`

---

## 1. Воронка откликов (Pipeline Metrics)

| Метрика / Статус | Количество | Доля от откликов |
| :--- | :---: | :---: |
| **Всего вакансий в базе** | **1** | — |
| **Всего направлено откликов** | **1** | 100.0% |
| 📨 `applied` (Отправлен отклик) | 0 | 0.0% |
| 👀 `viewed` (Просмотрено HR) | 0 | 0.0% |
| ⭐ `invited` (Приглашение) | 1 | 100.0% |
| 🎙️ `interview` (Собеседование) | 0 | 0.0% |
| 🎉 `offer` (Оффер) | 0 | 0.0% |
| ❌ `rejected` (Отказ) | 0 | 0.0% |

---

## 2. Распределение по приоритетам (Tiers)
- **Tier 1 (Банки, финтех, корпорации):** 1 вакансий
- **Tier 2 (Средний бизнес):** 0 вакансий
- **Tier 3 (Малый бизнес):** 0 вакансий

---

## 3. Приоритетные лиды (Интервью и Приглашения)

| Компания | Должность | Приоритет | Статус | Обновлено | Заметки | Ссылка |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: |
| **Apex Insurance** | Lead Financial Controller | Tier 1 | `invited` | 2026-11-08 | Direct outreach from partner
[2026-11-08T00:20:35.023084] Interview scheduled with Head of Finance | [Открыть](https://hh.uz/vacancy/888777) |

---

## 4. Как обновить статус вакансии
```bash
python scripts/update_status.py --vacancy-id <ID> --status interview --notes "Дата и время собеседования"
python scripts/dashboard.py
```
