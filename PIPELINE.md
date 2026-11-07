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

> **Auto-generated:** `2026-11-08T00:26:03.850211`  
> **Single Source of Truth:** `db/positions.db`

---

## 1. Воронка откликов (Pipeline Metrics)

| Метрика / Статус | Количество | Доля от откликов |
| :--- | :---: | :---: |
| **Всего вакансий в базе** | **1533** | — |
| **Всего направлено откликов** | **107** | 100.0% |
| 📨 `applied` (Отправлен отклик) | 106 | 99.1% |
| 👀 `viewed` (Просмотрено HR) | 0 | 0.0% |
| ⭐ `invited` (Приглашение) | 0 | 0.0% |
| 🎙️ `interview` (Собеседование) | 1 | 0.9% |
| 🎉 `offer` (Оффер) | 0 | 0.0% |
| ❌ `rejected` (Отказ) | 0 | 0.0% |

---

## 2. Распределение по приоритетам (Tiers)
- **Tier 1 (Банки, финтех, корпорации):** 93 вакансий
- **Tier 2 (Средний бизнес):** 160 вакансий
- **Tier 3 (Малый бизнес):** 1280 вакансий

---

## 3. Приоритетные лиды (Интервью и Приглашения)

| Компания | Должность | Приоритет | Статус | Обновлено | Заметки | Ссылка |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: |
| **АО OPEN BANK AJ** | Аналитик данных (Data Analyst) в банк / финтех | Tier 1 | `interview` | 2026-11-08 | Imported via Hermes Batch Queue [Hermes sync]
[2026-11-08T00:25:56.940584] Приглашение на 1-й раунд: техническое интервью с Lead Analyst (Четверг 15:00) | [Открыть](https://tashkent.hh.uz/vacancy/137871661) |

---

## 4. Как обновить статус вакансии
```bash
python scripts/update_status.py --vacancy-id <ID> --status interview --notes "Дата и время собеседования"
python scripts/dashboard.py
```
