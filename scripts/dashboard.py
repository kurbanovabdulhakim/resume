"""
Pipeline Dashboard & AI Context Generator.

Compiles current state from positions.db into:
1. dashboard.html — Interactive standalone visual Kanban board
2. PIPELINE.md — Human-readable Markdown summary table
3. AI_CONTEXT.md — Machine-readable state for cold-starting AI agents

Usage:
    python scripts/dashboard.py [--json]
"""

from __future__ import annotations
import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import get_connection, init_database
from scripts.logger import log_event


def fetch_pipeline_metrics(db_path: Path) -> Dict[str, Any]:
    """Queries positions.db for comprehensive pipeline counters and active leads."""
    conn = get_connection(db_path)
    c = conn.cursor()

    total_vacancies = c.execute("SELECT COUNT(*) FROM vacancies").fetchone()[0]
    active_vacancies = c.execute("SELECT COUNT(*) FROM vacancies WHERE is_active = 1").fetchone()[0]

    # Status breakdown
    statuses = ["applied", "viewed", "invited", "interview", "offer", "rejected", "declined"]
    status_counts = {s: 0 for s in statuses}
    for row in c.execute("SELECT status, COUNT(*) FROM applications GROUP BY status").fetchall():
        if row[0] in status_counts:
            status_counts[row[0]] = row[1]
        else:
            status_counts[row[0]] = row[1]

    # Tier breakdown
    tier_counts = {1: 0, 2: 0, 3: 0}
    for row in c.execute("SELECT tier, COUNT(*) FROM vacancies GROUP BY tier").fetchall():
        if row[0] in tier_counts:
            tier_counts[row[0]] = row[1]

    # Sector breakdown
    sector_counts = {}
    for row in c.execute("SELECT sector, COUNT(*) FROM vacancies GROUP BY sector").fetchall():
        sector_counts[row[0] or "Other"] = row[1]

    # Applications list with details
    apps_query = """
        SELECT a.id, a.vacancy_id, v.title, v.company, v.tier, v.sector, v.url, 
               a.status, a.applied_at, a.last_updated, a.notes
        FROM applications a
        JOIN vacancies v ON a.vacancy_id = v.id
        ORDER BY 
            CASE a.status
                WHEN 'offer' THEN 1
                WHEN 'interview' THEN 2
                WHEN 'invited' THEN 3
                WHEN 'viewed' THEN 4
                WHEN 'applied' THEN 5
                WHEN 'rejected' THEN 6
                ELSE 7
            END,
            v.tier ASC,
            a.last_updated DESC
    """
    all_apps = []
    for r in c.execute(apps_query).fetchall():
        all_apps.append({
            "id": r[0],
            "vacancy_id": r[1],
            "title": r[2],
            "company": r[3],
            "tier": r[4],
            "sector": r[5],
            "url": r[6],
            "status": r[7],
            "applied_at": r[8],
            "last_updated": r[9],
            "notes": r[10] or "",
        })

    # Urgent leads (invited or interview)
    urgent_leads = [
        app for app in all_apps if app["status"] in ("invited", "interview")
    ]

    conn.close()

    return {
        "total_vacancies": total_vacancies,
        "active_vacancies": active_vacancies,
        "total_applications": sum(status_counts.values()),
        "status_counts": status_counts,
        "tier_counts": tier_counts,
        "sector_counts": sector_counts,
        "applications": all_apps,
        "urgent_leads": urgent_leads,
    }


def generate_kanban_html(data: Dict[str, Any], output_path: Path) -> None:
    """Renders standalone responsive HTML Kanban dashboard."""
    statuses = ["applied", "viewed", "invited", "interview", "offer", "rejected"]
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Group apps by status
    grouped: Dict[str, List[Dict[str, Any]]] = {s: [] for s in statuses}
    for app in data["applications"]:
        s = app["status"]
        if s in grouped:
            grouped[s].append(app)
        else:
            grouped.setdefault("rejected", []).append(app)

    columns_html = []
    status_titles = {
        "applied": "📨 Отправлен отклик",
        "viewed": "👀 Просмотрено",
        "invited": "⭐ Приглашение",
        "interview": "🎙️ Собеседование",
        "offer": "🎉 Оффер",
        "rejected": "❌ Отказ",
    }

    for s in statuses:
        items = grouped[s]
        cards_html = []
        for it in items[:60]:  # limit per column to keep HTML snappy
            tier_badge = f'<span class="badge tier-{it["tier"]}">Tier {it["tier"]}</span>'
            sector_badge = f'<span class="badge sector">{it["sector"]}</span>'
            notes_div = f'<div class="card-notes">{it["notes"]}</div>' if it["notes"] else ''
            link_a = f'<a href="{it["url"]}" target="_blank" class="card-link">HH ↗</a>' if it["url"] else ''
            card = f"""
            <div class="card status-{it["status"]}" data-status="{it["status"]}">
              <div class="card-header">
                {tier_badge}
                {sector_badge}
              </div>
              <div class="card-title">{it["title"]}</div>
              <div class="card-company">{it["company"]}</div>
              {notes_div}
              <div class="card-footer">
                <span class="card-date">{str(it["last_updated"])[:10]}</span>
                {link_a}
              </div>
            </div>"""
            cards_html.append(card)

        col_html = f"""
        <div class="kanban-col status-{s}" data-status="{s}">
          <div class="col-header">
            <h3>{status_titles[s]}</h3>
            <span class="col-count">{len(items)}</span>
          </div>
          <div class="cards-container">
            {''.join(cards_html) if cards_html else '<div class="empty-col">Нет вакансий</div>'}
          </div>
        </div>"""
        columns_html.append(col_html)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Hermes Job Pipeline Dashboard</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #0f172a;
      color: #f8fafc;
      padding: 20px;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #1e293b;
      padding: 16px 24px;
      border-radius: 12px;
      border: 1px solid #334155;
      margin-bottom: 20px;
    }}
    .header h1 {{ font-size: 20px; font-weight: 700; color: #38bdf8; }}
    .stats-bar {{
      display: flex;
      gap: 16px;
      font-size: 13px;
    }}
    .stat-pill {{
      background: #0f172a;
      border: 1px solid #334155;
      padding: 6px 12px;
      border-radius: 8px;
    }}
    .stat-pill strong {{ color: #38bdf8; }}
    .kanban-board {{
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: 16px;
      overflow-x: auto;
      padding-bottom: 20px;
    }}
    .kanban-col {{
      background: #1e293b;
      border-radius: 12px;
      border: 1px solid #334155;
      display: flex;
      flex-direction: column;
      max-height: calc(100vh - 120px);
    }}
    .col-header {{
      padding: 12px 14px;
      border-bottom: 1px solid #334155;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .col-header h3 {{ font-size: 14px; font-weight: 600; color: #f1f5f9; }}
    .col-count {{
      background: #334155;
      color: #38bdf8;
      font-size: 12px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 12px;
    }}
    .cards-container {{
      padding: 12px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .card {{
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 10px;
      transition: border-color 0.15s ease;
    }}
    .card:hover {{ border-color: #38bdf8; }}
    .card-header {{ display: flex; gap: 6px; margin-bottom: 6px; }}
    .badge {{
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
    }}
    .tier-1 {{ background: #854d0e; color: #fef08a; }}
    .tier-2 {{ background: #1e3a8a; color: #bfdbfe; }}
    .tier-3 {{ background: #374151; color: #e5e7eb; }}
    .sector {{ background: #134e4a; color: #99f6e4; }}
    .card-title {{ font-size: 13px; font-weight: 600; color: #f8fafc; margin-bottom: 2px; }}
    .card-company {{ font-size: 12px; color: #94a3b8; margin-bottom: 6px; }}
    .card-notes {{
      font-size: 11px;
      background: #1e293b;
      padding: 4px 6px;
      border-radius: 4px;
      color: #cbd5e1;
      margin-bottom: 6px;
      white-space: pre-wrap;
    }}
    .card-footer {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      color: #64748b;
    }}
    .card-link {{
      color: #38bdf8;
      text-decoration: none;
      font-weight: 600;
    }}
    .card-link:hover {{ text-decoration: underline; }}
    .empty-col {{ font-size: 12px; color: #64748b; text-align: center; padding: 20px 0; }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>⚡ Hermes Job Application Pipeline</h1>
      <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Обновлено: {now_str} | Single Source of Truth: db/positions.db</div>
    </div>
    <div class="stats-bar">
      <div class="stat-pill">Целевых вакансий: <strong>{data['total_vacancies']}</strong></div>
      <div class="stat-pill">Откликов: <strong>{data['total_applications']}</strong></div>
      <div class="stat-pill">Приглашений / Интервью: <strong>{data['status_counts'].get('invited', 0) + data['status_counts'].get('interview', 0)}</strong></div>
      <div class="stat-pill">Офферов: <strong>{data['status_counts'].get('offer', 0)}</strong></div>
    </div>
  </div>

  <div class="kanban-board">
    {''.join(columns_html)}
  </div>
</body>
</html>"""
    output_path.write_text(html, encoding="utf-8")


def generate_pipeline_markdown(data: Dict[str, Any], output_path: Path) -> None:
    """Generates human and AI readable PIPELINE.md compliant with doc-standarts-draft.md."""
    today_str = datetime.date.today().isoformat()
    sc = data["status_counts"]

    urgent_rows = []
    for it in data["urgent_leads"]:
        urgent_rows.append(
            f"| **{it['company']}** | {it['title']} | Tier {it['tier']} | `{it['status']}` | {str(it['last_updated'])[:10]} | {it['notes'] or '—'} | [Открыть]({it['url']}) |"
        )

    urgent_table = "\n".join(urgent_rows) if urgent_rows else "_В данный момент нет активных приглашений или интервью, требующих срочного ответа._"

    content = f"""---
title: Job Application Pipeline Summary
description: Live snapshot of active job search pipeline, interview stages, and response rates from positions.db.
status: active
category: status
tags: [pipeline, status, kanban, applications, hermes]
last-verified: {today_str}
summary-ru: Сводный отчет о текущем статусе воронки откликов, собеседований и конверсии.
summary-uz: Rezyumelar, suhbat bosqichlari va konversiya holati bo'yicha jonli hisobot.
related:
  - AGENTS.md
  - AI_CONTEXT.md
  - db/schema.md
  - dashboard.html
---

# Job Application Pipeline Summary

> **Auto-generated:** `{datetime.datetime.now().isoformat()}`  
> **Single Source of Truth:** `db/positions.db`

---

## 1. Воронка откликов (Pipeline Metrics)

| Метрика / Статус | Количество | Доля от откликов |
| :--- | :---: | :---: |
| **Всего вакансий в базе** | **{data['total_vacancies']}** | — |
| **Всего направлено откликов** | **{data['total_applications']}** | 100.0% |
| 📨 `applied` (Отправлен отклик) | {sc.get('applied', 0)} | {sc.get('applied', 0) / max(data['total_applications'], 1) * 100:.1f}% |
| 👀 `viewed` (Просмотрено HR) | {sc.get('viewed', 0)} | {sc.get('viewed', 0) / max(data['total_applications'], 1) * 100:.1f}% |
| ⭐ `invited` (Приглашение) | {sc.get('invited', 0)} | {sc.get('invited', 0) / max(data['total_applications'], 1) * 100:.1f}% |
| 🎙️ `interview` (Собеседование) | {sc.get('interview', 0)} | {sc.get('interview', 0) / max(data['total_applications'], 1) * 100:.1f}% |
| 🎉 `offer` (Оффер) | {sc.get('offer', 0)} | {sc.get('offer', 0) / max(data['total_applications'], 1) * 100:.1f}% |
| ❌ `rejected` (Отказ) | {sc.get('rejected', 0)} | {sc.get('rejected', 0) / max(data['total_applications'], 1) * 100:.1f}% |

---

## 2. Распределение по приоритетам (Tiers)
- **Tier 1 (Банки, финтех, корпорации):** {data['tier_counts'].get(1, 0)} вакансий
- **Tier 2 (Средний бизнес):** {data['tier_counts'].get(2, 0)} вакансий
- **Tier 3 (Малый бизнес):** {data['tier_counts'].get(3, 0)} вакансий

---

## 3. Приоритетные лиды (Интервью и Приглашения)

| Компания | Должность | Приоритет | Статус | Обновлено | Заметки | Ссылка |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: |
{urgent_table}

---

## 4. Как обновить статус вакансии
```bash
python scripts/update_status.py --vacancy-id <ID> --status interview --notes "Дата и время собеседования"
python scripts/dashboard.py
```
"""
    output_path.write_text(content, encoding="utf-8")


def generate_ai_context_markdown(data: Dict[str, Any], output_path: Path) -> None:
    """Generates machine-readable AI_CONTEXT.md for autonomous agent cold-start."""
    today_str = datetime.date.today().isoformat()
    now_iso = datetime.datetime.now().isoformat()

    urgent_list = [
        {"id": it["vacancy_id"], "company": it["company"], "title": it["title"], "status": it["status"], "notes": it["notes"]}
        for it in data["urgent_leads"]
    ]

    context_yaml = {
        "generated_at": now_iso,
        "database": "db/positions.db",
        "vacancies_total": data["total_vacancies"],
        "active_vacancies": data["active_vacancies"],
        "total_vacancies": data["total_vacancies"],
        "applications_total": data["total_applications"],
        "total_applications": data["total_applications"],
        "statuses": data["status_counts"],
        "tier_distribution": data["tier_counts"],
        "sector_distribution": data["sector_counts"],
        "urgent_leads_count": len(urgent_list),
        "urgent_leads": urgent_list,
        "recommended_next_actions": [
            "Check urgent_leads to prepare tailored CV and interview prep",
            "To sync new batch from Hermes, run: python scripts/sync_hermes.py --json",
            "To generate tailored docs for vacancy, run: python scripts/generate_docs.py --vacancy-id <id> --json",
            "To record interview or status change: python scripts/update_status.py --vacancy-id <id> --status interview --json",
        ],
    }

    content = f"""---
title: Machine-Readable Agent Context State
description: Real-time autonomous context state snapshot consumed by AI agents to operate on positions.db.
status: active
category: status
tags: [ai-context, agent-first, state, pipeline, automation]
last-verified: {today_str}
summary-ru: Машиночитаемый контекст текущего состояния воронки вакансий для ИИ-агентов.
summary-uz: Sun'iy intellekt agentlari uchun vakansiyalar holati bo'yicha mashina o'qiydigan kontekst.
related:
  - AGENTS.md
  - PIPELINE.md
  - db/schema.md
---

# Machine-Readable AI Agent Context

```yaml
{json.dumps(context_yaml, indent=2, ensure_ascii=False)}
```

## Quick Reference for Cold Agents
- **Primary Database:** `db/positions.db` (SQLite, tracked in Git)
- **Sync Command:** `python scripts/sync_hermes.py --json`
- **Document Generation:** `python scripts/generate_docs.py --vacancy-id <id> --json`
- **Update Status:** `python scripts/update_status.py --vacancy-id <id> --status <status> --json`
- **Recompile Dashboard:** `python scripts/dashboard.py --json`
"""
    output_path.write_text(content, encoding="utf-8")


def build_dashboard_artifacts(
    db_path: Path | None = None,
    html_path: Path | None = None,
    pipeline_md_path: Path | None = None,
    ai_context_path: Path | None = None,
) -> Dict[str, Any]:
    """Compiles all three dashboard outputs."""
    target_db = Path(db_path) if db_path else Config.DB_PATH
    target_html = Path(html_path) if html_path else Config.DASHBOARD_HTML_PATH
    target_pipe = Path(pipeline_md_path) if pipeline_md_path else Config.PIPELINE_MD_PATH
    target_ctx = Path(ai_context_path) if ai_context_path else Config.AI_CONTEXT_MD_PATH

    init_database(target_db)
    metrics = fetch_pipeline_metrics(target_db)

    generate_kanban_html(metrics, target_html)
    generate_pipeline_markdown(metrics, target_pipe)
    generate_ai_context_markdown(metrics, target_ctx)

    result = {
        "success": True,
        "code": Config.EXIT_SUCCESS,
        "db_path": str(target_db),
        "dashboard_html": str(target_html),
        "pipeline_md": str(target_pipe),
        "ai_context_md": str(target_ctx),
        "total_vacancies": metrics["total_vacancies"],
        "total_applications": metrics["total_applications"],
        "status_counts": metrics["status_counts"],
    }
    log_event("DASHBOARD_COMPILED", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile dashboard.html, PIPELINE.md, and AI_CONTEXT.md")
    parser.add_argument("--db-path", type=str, default=None, help="Custom DB path")
    parser.add_argument("--html-path", type=str, default=None, help="Custom HTML output path")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()
    db_target = Path(args.db_path) if args.db_path else None
    html_target = Path(args.html_path) if args.html_path else None

    res = build_dashboard_artifacts(db_path=db_target, html_path=html_target)

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        if res["success"]:
            print(f"[OK] Dashboard artifacts successfully compiled:")
            print(f"     HTML Kanban:   {res['dashboard_html']}")
            print(f"     Pipeline MD:   {res['pipeline_md']}")
            print(f"     AI Context:    {res['ai_context_md']}")
            print(f"     Total tracked: {res['total_vacancies']} vacancies ({res['total_applications']} applications)")
        else:
            print(f"[ERROR] Failed to compile dashboard", file=sys.stderr)

    return res["code"]


if __name__ == "__main__":
    sys.exit(main())
