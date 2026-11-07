---
title: Database Schema and Query Reference
description: Canonical SQLite database schema documentation and SQL query reference for positions.db.
status: active
category: architecture
tags: [database, sqlite, schema, reference, vacancies, applications]
last-verified: 2026-11-08
summary-ru: Документация канонической схемы SQLite базы данных positions.db и справочник типовых SQL запросов.
summary-uz: positions.db SQLite ma'lumotlar bazasining kanonik sxemasi hujjatlari va odatiy SQL so'rovlar ma'lumotnomasi.
related:
  - db/schema.sql
  - AGENTS.md
  - docs/superpowers/specs/2026-11-07-job-tracker-design.md
---

# Database Schema & Query Reference

The SQLite database at `db/positions.db` is the **Single Source of Truth (SSOT)** for all vacancy tracking, application statuses, and generated documents.

## Schema Overview

### 1. `vacancies` Table
Stores raw and normalized information about every discovered or targeted job opening.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `TEXT` | `PRIMARY KEY` | HeadHunter vacancy ID (numeric string) or generated UUID |
| `title` | `TEXT` | `NOT NULL` | Job title (e.g., "Senior Business Analyst") |
| `company` | `TEXT` | `NOT NULL` | Employer name (e.g., "Kapitalbank") |
| `url` | `TEXT` | | Direct link to posting |
| `source` | `TEXT` | `DEFAULT 'hh.uz'` | Source: `hh.uz`, `olx`, `telegram`, `linkedin`, `manual` |
| `tier` | `INTEGER`| `DEFAULT 2` | `1` = Banks/Tier-1 Corps, `2` = Mid-sized, `3` = Small business |
| `sector` | `TEXT` | `DEFAULT 'Finance'`| `Finance`, `Logistics`, `Analytics`, `Management`, `Other` |
| `salary_min` | `INTEGER` | | Minimum parsed salary |
| `salary_max` | `INTEGER` | | Maximum parsed salary |
| `salary_text`| `TEXT` | | Original unparsed salary string |
| `published_at`| `TEXT` | | ISO 8601 publication timestamp |
| `scraped_at` | `TEXT` | | ISO 8601 scrape timestamp |
| `is_active` | `INTEGER`| `DEFAULT 1` | `1` = active, `0` = archived / closed |

### 2. `applications` Table
Tracks the full pipeline lifecycle for each applied position.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Auto-incrementing identifier |
| `vacancy_id` | `TEXT` | `NOT NULL`, FK → `vacancies(id)` | Foreign key to vacancy |
| `status` | `TEXT` | Enum: `applied`, `viewed`, `invited`, `interview`, `offer`, `rejected`, `declined` | Current progression stage |
| `applied_at` | `TEXT` | | ISO 8601 timestamp of initial application |
| `cv_variant` | `TEXT` | | CV variant used (`business_analyst`, `financial_analyst`, etc.) |
| `cover_letter_sent` | `INTEGER` | `DEFAULT 0` | `1` if cover letter was dispatched |
| `pdf_sent_in_chat` | `INTEGER` | `DEFAULT 0` | `1` if resume PDF was sent directly to employer chat |
| `notes` | `TEXT` | | Free-form notes, interviewer feedback, next steps |
| `last_updated` | `TEXT` | | ISO 8601 timestamp of last status change |

### 3. `documents` Table
Audit trail of all generated PDFs and Markdown assets for specific positions.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Auto-incrementing identifier |
| `vacancy_id` | `TEXT` | `NOT NULL`, FK → `vacancies(id)` | Target vacancy ID |
| `doc_type` | `TEXT` | Enum: `cover_letter`, `cv` | Document category |
| `variant_used`| `TEXT` | | Template or variant name used |
| `file_path` | `TEXT` | `NOT NULL` | Path relative to repository root under `generated/` |
| `generated_at`| `TEXT` | | ISO 8601 timestamp |

---

## Common SQL Queries for AI Agents

### 1. Check Pipeline Status Summary
```sql
SELECT status, COUNT(*) AS count
FROM applications
GROUP BY status
ORDER BY count DESC;
```

### 2. Find All Tier 1 Vacancies with Active Invitations
```sql
SELECT v.company, v.title, a.status, a.applied_at, a.last_updated, a.notes
FROM vacancies v
JOIN applications a ON v.id = a.vacancy_id
WHERE v.tier = 1 AND a.status IN ('invited', 'interview')
ORDER BY a.last_updated DESC;
```

### 3. Check for Pending Follow-ups (Applied > 7 days ago with no response)
```sql
SELECT v.company, v.title, v.url, a.applied_at
FROM vacancies v
JOIN applications a ON v.id = a.vacancy_id
WHERE a.status = 'applied' AND a.applied_at <= datetime('now', '-7 days')
ORDER BY a.applied_at ASC;
```
