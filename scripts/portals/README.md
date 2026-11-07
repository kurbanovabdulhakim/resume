---
title: Job Portals Integration and Scrapers Guide
description: Architecture, scrapers status, and roadmap for candidate job portals across Uzbekistan (hh.uz, OLX UZ, Telegram channels).
status: active
category: architecture
tags: [portals, scrapers, hh-uz, olx, telegram, roadmap]
last-verified: 2026-11-08
summary-ru: Руководство по интеграции с порталами поиска работы в Узбекистане, статус парсеров и политика работы с Telegram-каналами.
summary-uz: O'zbekistondagi ish qidirish portallari bilan integratsiya yo'riqnomasi va Telegram kanallari bo'yicha reja.
related:
  - AGENTS.md
  - db/schema.md
  - scripts/sync_hermes.py
---

# Job Portals Integration Guide

This directory contains standalone parser and ingestion modules for various job platforms across Tashkent and Uzbekistan.

## Portal Status Matrix

| Portal | Ingestion Method | Script | Status | Notes |
| :--- | :--- | :--- | :---: | :--- |
| **hh.uz (HeadHunter)** | JSON API / Selenium via Hermes | `scripts/portals/hh_watcher.py` | **Active** | Primary channel (1,500+ tracked vacancies) |
| **OLX UZ (Rabota)** | HTTP HTML Scraper / Parsers | `scripts/portals/olx_scraper.py` | **Active** | Targeted local SMB and direct listings |
| **Telegram Channels** | Telethon / MTProto parser | — | **Deferred (Future)** | **Explicit constraint: Not active yet (`not yet telegram channels`)** |
| **LinkedIn** | Manual entry / URL import | `scripts/add_position.py` | **Active** | High-touch corporate and executive roles |

---

## Telegram Channels Roadmap Policy

> [!NOTE]
> Per project directives, **Telegram channels are currently out of scope (`not yet telegram channels`)**.
> 
> When enabled in a future release:
> 1. Ingestion will use Telethon sessions saved in host configuration.
> 2. Channels to monitor: `@ishga_marhamat`, `@tashkent_jobs`, `@uz_hr`.
> 3. Discovered leads will be inserted into `positions.db` with `source='telegram'`.

---

## Running Portal Scrapers

### 1. Ingest OLX Listings
```bash
python scripts/portals/olx_scraper.py --query "аналитик" --limit 20 --json
```

### 2. Check Fresh HeadHunter Vacancies
```bash
python scripts/portals/hh_watcher.py --query "бизнес-аналитик" --json
```
