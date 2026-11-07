"""
Pipeline Dashboard & AI Context Generator.

Compiles current state from positions.db into:
1. dashboard.html — Interactive standalone visual Kanban board & Table CRM
2. PIPELINE.md — Human-readable Markdown summary table
3. AI_CONTEXT.md — Machine-readable state for cold-starting AI agents

Usage:
    python scripts/dashboard.py [--json]
"""

from __future__ import annotations
import argparse
import datetime
import html
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
               a.status, a.applied_at, a.last_updated, a.notes, v.salary_text
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
            "salary_text": r[11] or "",
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
    """Renders executive-grade responsive HTML Kanban dashboard & Table view."""
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
        "viewed": "👀 Просмотрено HR",
        "invited": "⭐ Приглашение",
        "interview": "🎙️ Собеседование",
        "offer": "🎉 Оффер",
        "rejected": "❌ Отказ",
    }

    # Build Kanban cards
    for s in statuses:
        items = grouped[s]
        cards_html = []
        for it in items:
            t = it["tier"]
            tier_class = f"badge-t{t}"
            tier_label = f"Tier {t}" if t != 1 else "⭐ Tier 1"

            sector_badge = f'<span class="badge-sector">{html.escape(it["sector"])}</span>'
            salary_badge = (
                f'<span class="badge-salary">{html.escape(it["salary_text"])}</span>'
                if it["salary_text"]
                else ""
            )
            notes_div = (
                f'<div class="card-notes">{html.escape(it["notes"])}</div>'
                if it["notes"]
                else ""
            )
            link_a = (
                f'<a href="{it["url"]}" target="_blank" class="card-link">HH ↗</a>'
                if it["url"]
                else ""
            )

            search_blob = f"{it['company']} {it['title']} {it['sector']} {it['notes']}".lower()

            card = f"""
            <div class="card status-{it['status']}" 
                 data-status="{it['status']}" 
                 data-tier="{t}" 
                 data-sector="{html.escape(it['sector'])}"
                 data-search="{html.escape(search_blob)}">
              <div class="card-header">
                <span class="{tier_class}">{tier_label}</span>
                {sector_badge}
                {salary_badge}
              </div>
              <div class="card-title">{html.escape(it['title'])}</div>
              <div class="card-company">{html.escape(it['company'])}</div>
              {notes_div}
              <div class="card-footer">
                <span class="card-date">🕒 {str(it['last_updated'])[:10]}</span>
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
            {''.join(cards_html) if cards_html else '<div class="empty-col">Нет вакансий в этом статусе</div>'}
          </div>
        </div>"""
        columns_html.append(col_html)

    # Build Table rows
    table_rows = []
    for idx, it in enumerate(data["applications"], 1):
        t = it["tier"]
        tier_badge = f'<span class="badge-t{t}">Tier {t}</span>'
        status_label = status_titles.get(it["status"], it["status"])
        status_badge = f'<span class="badge-status badge-status-{it["status"]}">{status_label}</span>'
        salary_str = html.escape(it["salary_text"]) if it["salary_text"] else '<span class="text-muted">—</span>'
        search_blob = f"{it['company']} {it['title']} {it['sector']} {it['notes']}".lower()

        row = f"""
        <tr class="table-row status-{it['status']}" 
            data-status="{it['status']}" 
            data-tier="{t}" 
            data-sector="{html.escape(it['sector'])}"
            data-search="{html.escape(search_blob)}">
          <td style="color: var(--text-sub);">{idx}</td>
          <td><strong>{html.escape(it['company'])}</strong></td>
          <td>
            <a href="{it['url']}" target="_blank" class="vac-link">{html.escape(it['title'])}</a>
            {f'<div class="snippet-sub">{html.escape(it["notes"])}</div>' if it["notes"] else ''}
          </td>
          <td>{tier_badge}</td>
          <td><span class="badge-sector">{html.escape(it['sector'])}</span></td>
          <td>{salary_str}</td>
          <td>{status_badge}</td>
          <td style="white-space: nowrap; color: var(--text-sub);">{str(it['last_updated'])[:10]}</td>
          <td>
            <a href="{it['url']}" target="_blank" class="action-btn">HH ↗</a>
          </td>
        </tr>"""
        table_rows.append(row)

    urgent_count = data["status_counts"].get("invited", 0) + data["status_counts"].get("interview", 0)

    html_page = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>⚡ Hermes 2.0 • Executive Recruitment Command Hub</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0b0f19;
      --surface: #131b2e;
      --surface-hover: #1c2742;
      --border: #233152;
      --text-main: #f1f5f9;
      --text-sub: #94a3b8;
      --primary: #3b82f6;
      --success: #10b981;
      --danger: #ef4444;
      --gold: #f59e0b;
      --purple: #8b5cf6;
      --cyan: #06b6d4;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text-main);
      line-height: 1.5;
      padding: 24px;
    }}

    /* HEADER */
    .header {{
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 24px 28px;
      margin-bottom: 24px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .header-titles h1 {{
      font-size: 24px;
      font-weight: 800;
      margin-bottom: 6px;
      background: linear-gradient(90deg, #60a5fa, #a78bfa);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .header-titles p {{
      color: var(--text-sub);
      font-size: 13px;
    }}
    .live-badge {{
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #34d399;
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .live-dot {{
      width: 8px;
      height: 8px;
      background: #10b981;
      border-radius: 50%;
      box-shadow: 0 0 8px #10b981;
    }}

    /* KPI GRID */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .kpi-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px 20px;
      position: relative;
      overflow: hidden;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }}
    .kpi-card::before {{
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0; height: 3px;
    }}
    .kpi-total::before {{ background: var(--primary); }}
    .kpi-purple::before {{ background: var(--purple); }}
    .kpi-gold::before {{ background: var(--gold); }}
    .kpi-cyan::before {{ background: var(--cyan); }}
    .kpi-green::before {{ background: var(--success); }}
    .kpi-num {{ font-size: 26px; font-weight: 800; margin-bottom: 4px; }}
    .kpi-label {{ color: var(--text-sub); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}

    /* CONTROLS BAR */
    .controls-bar {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      margin-bottom: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}
    .controls-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }}
    .tabs-group {{
      display: flex;
      gap: 8px;
    }}
    .tab-btn {{
      background: #17223b;
      border: 1px solid var(--border);
      color: var(--text-sub);
      padding: 8px 16px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .tab-btn.active {{
      background: var(--primary);
      color: white;
      border-color: var(--primary);
      box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }}
    .search-box {{
      flex: 1;
      min-width: 280px;
      padding: 10px 16px;
      background: #0b0f19;
      border: 1px solid var(--border);
      border-radius: 8px;
      color: white;
      font-size: 13px;
      outline: none;
      transition: border-color 0.2s;
    }}
    .search-box:focus {{ border-color: var(--primary); }}

    .filters-group {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }}
    .filter-label {{
      font-size: 12px;
      color: var(--text-sub);
      margin-right: 4px;
      font-weight: 600;
    }}
    .pill-btn {{
      background: #0f172a;
      border: 1px solid var(--border);
      color: var(--text-sub);
      padding: 4px 12px;
      border-radius: 16px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .pill-btn:hover {{ border-color: var(--primary); color: white; }}
    .pill-btn.active {{
      background: #1e3a8a;
      border-color: #3b82f6;
      color: #93c5fd;
    }}

    /* KANBAN BOARD */
    .kanban-board {{
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: 16px;
      overflow-x: auto;
      padding-bottom: 20px;
    }}
    .kanban-col {{
      background: var(--surface);
      border-radius: 12px;
      border: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      max-height: calc(100vh - 280px);
      min-width: 250px;
    }}
    .col-header {{
      padding: 12px 14px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #162035;
      border-top-left-radius: 11px;
      border-top-right-radius: 11px;
    }}
    .col-header h3 {{ font-size: 13px; font-weight: 700; color: #f1f5f9; }}
    .col-count {{
      background: #233152;
      color: #38bdf8;
      font-size: 11px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 10px;
    }}
    .cards-container {{
      padding: 10px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}

    /* CARDS */
    .card {{
      background: #0b0f19;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
      transition: all 0.2s ease;
      position: relative;
    }}
    .card:hover {{
      border-color: #3b82f6;
      transform: translateY(-2px);
      box-shadow: 0 6px 16px rgba(0,0,0,0.4);
    }}
    .card-header {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-bottom: 8px;
    }}
    .card-title {{
      font-size: 13px;
      font-weight: 700;
      color: #f8fafc;
      margin-bottom: 4px;
      line-height: 1.35;
    }}
    .card-company {{
      font-size: 12px;
      color: #94a3b8;
      margin-bottom: 8px;
      font-weight: 500;
    }}
    .card-notes {{
      font-size: 11px;
      background: #131b2e;
      border: 1px solid #1e293b;
      padding: 6px 8px;
      border-radius: 6px;
      color: #cbd5e1;
      margin-bottom: 8px;
      white-space: pre-wrap;
      line-height: 1.4;
    }}
    .card-footer {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      color: #64748b;
      border-top: 1px solid #1a233a;
      padding-top: 8px;
    }}
    .card-link {{
      color: #60a5fa;
      text-decoration: none;
      font-weight: 700;
      background: #17223b;
      padding: 2px 8px;
      border-radius: 4px;
      border: 1px solid #233152;
    }}
    .card-link:hover {{
      background: #2563eb;
      color: white;
      border-color: #3b82f6;
    }}

    /* BADGES */
    .badge-t1 {{
      background: rgba(245, 158, 11, 0.2);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.4);
      padding: 2px 7px;
      border-radius: 4px;
      font-weight: 700;
      font-size: 10px;
      text-transform: uppercase;
    }}
    .badge-t2 {{
      background: rgba(59, 130, 246, 0.2);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.4);
      padding: 2px 7px;
      border-radius: 4px;
      font-weight: 600;
      font-size: 10px;
      text-transform: uppercase;
    }}
    .badge-t3 {{
      background: rgba(148, 163, 184, 0.15);
      color: #cbd5e1;
      border: 1px solid rgba(148, 163, 184, 0.3);
      padding: 2px 7px;
      border-radius: 4px;
      font-weight: 500;
      font-size: 10px;
    }}
    .badge-sector {{
      background: rgba(6, 182, 212, 0.15);
      color: #67e8f9;
      border: 1px solid rgba(6, 182, 212, 0.3);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 600;
    }}
    .badge-salary {{
      background: rgba(16, 185, 129, 0.15);
      color: #6ee7b7;
      border: 1px solid rgba(16, 185, 129, 0.3);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 600;
    }}

    .empty-col {{
      font-size: 12px;
      color: #475569;
      text-align: center;
      padding: 30px 10px;
    }}

    /* TABLE VIEW */
    .table-view-container {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      overflow-x: auto;
      box-shadow: 0 8px 20px rgba(0,0,0,0.3);
      display: none;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
    }}
    th {{
      background: #17223b;
      color: var(--text-sub);
      font-weight: 700;
      padding: 14px 16px;
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
    }}
    td {{
      padding: 12px 16px;
      border-bottom: 1px solid #1a2540;
      vertical-align: middle;
    }}
    tr:hover {{ background: var(--surface-hover); }}
    .vac-link {{ color: #60a5fa; text-decoration: none; font-weight: 600; }}
    .vac-link:hover {{ text-decoration: underline; color: #93c5fd; }}
    .snippet-sub {{ font-size: 11px; color: var(--text-sub); margin-top: 4px; line-height: 1.3; }}
    .action-btn {{
      color: #38bdf8;
      background: #17223b;
      border: 1px solid #233152;
      padding: 4px 10px;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 600;
      font-size: 11px;
    }}
    .action-btn:hover {{ background: #2563eb; color: white; }}
    .badge-status {{
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .badge-status-applied {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid #2563eb; }}
    .badge-status-interview {{ background: rgba(245, 158, 11, 0.25); color: #fbbf24; border: 1px solid #f59e0b; }}
    .badge-status-invited {{ background: rgba(139, 92, 246, 0.25); color: #c084fc; border: 1px solid #8b5cf6; }}
    .badge-status-offer {{ background: rgba(16, 185, 129, 0.25); color: #34d399; border: 1px solid #10b981; }}
    .badge-status-rejected {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #dc2626; }}
  </style>
</head>
<body>
  <div class="header">
    <div class="header-titles">
      <h1>⚡ Hermes 2.0 • Executive Recruitment Command Hub</h1>
      <p>Ташкент & Узбекистан • База данных: <code>db/positions.db</code> • Автоматическая синхронизация с HeadHunter</p>
    </div>
    <div class="live-badge">
      <div class="live-dot"></div>
      <span>Синхронизировано: {now_str}</span>
    </div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card kpi-total">
      <div class="kpi-num">{data['total_vacancies']}</div>
      <div class="kpi-label">Целевых вакансий в базе</div>
    </div>
    <div class="kpi-card kpi-purple">
      <div class="kpi-num">{data['total_applications']}</div>
      <div class="kpi-label">Откликов направлено</div>
    </div>
    <div class="kpi-card kpi-gold">
      <div class="kpi-num">{urgent_count}</div>
      <div class="kpi-label">Интервью & Приглашения</div>
    </div>
    <div class="kpi-card kpi-cyan">
      <div class="kpi-num">{data['tier_counts'].get(1, 0)}</div>
      <div class="kpi-label">Tier 1 Корпорации & Банки</div>
    </div>
    <div class="kpi-card kpi-green">
      <div class="kpi-num">{data['status_counts'].get('offer', 0)}</div>
      <div class="kpi-label">Офферы</div>
    </div>
  </div>

  <div class="controls-bar">
    <div class="controls-top">
      <div class="tabs-group">
        <button class="tab-btn active" id="tab-kanban" onclick="switchView('kanban')">📋 Kanban Воронка</button>
        <button class="tab-btn" id="tab-table" onclick="switchView('table')">📊 Детальная таблица ({len(data['applications'])})</button>
      </div>
      <input type="text" id="liveSearch" class="search-box" placeholder="🔍 Быстрый поиск по компании, должности, заметкам... (Клавиша: /)" oninput="applyFilters()">
    </div>

    <div class="filters-group">
      <span class="filter-label">Сектор:</span>
      <button class="pill-btn active" data-filter-type="sector" data-val="all" onclick="setFilter('sector', 'all', this)">Все секторы</button>
      <button class="pill-btn" data-filter-type="sector" data-val="Finance" onclick="setFilter('sector', 'Finance', this)">🏦 Банки & Финансы</button>
      <button class="pill-btn" data-filter-type="sector" data-val="Analytics" onclick="setFilter('sector', 'Analytics', this)">📊 Аналитика & IT</button>
      <button class="pill-btn" data-filter-type="sector" data-val="Logistics" onclick="setFilter('sector', 'Logistics', this)">🚚 Логистика & Склад</button>
      <button class="pill-btn" data-filter-type="sector" data-val="Management" onclick="setFilter('sector', 'Management', this)">👔 Менеджмент</button>

      <span class="filter-label" style="margin-left: 14px;">Приоритет:</span>
      <button class="pill-btn active" data-filter-type="tier" data-val="all" onclick="setFilter('tier', 'all', this)">Все Tiers</button>
      <button class="pill-btn" data-filter-type="tier" data-val="1" onclick="setFilter('tier', '1', this)">⭐ Tier 1</button>
      <button class="pill-btn" data-filter-type="tier" data-val="2" onclick="setFilter('tier', '2', this)">🔷 Tier 2</button>
      <button class="pill-btn" data-filter-type="tier" data-val="3" onclick="setFilter('tier', '3', this)">⚪ Tier 3</button>
    </div>
  </div>

  <!-- KANBAN BOARD VIEW -->
  <div class="kanban-board" id="view-kanban">
    {''.join(columns_html)}
  </div>

  <!-- TABLE VIEW -->
  <div class="table-view-container" id="view-table">
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Компания</th>
          <th>Должность</th>
          <th>Приоритет</th>
          <th>Сектор</th>
          <th>Зарплата</th>
          <th>Этап найма</th>
          <th>Обновлено</th>
          <th>Действия</th>
        </tr>
      </thead>
      <tbody>
        {''.join(table_rows)}
      </tbody>
    </table>
  </div>

  <script>
    let activeSector = 'all';
    let activeTier = 'all';

    function switchView(viewName) {{
      const kanbanView = document.getElementById('view-kanban');
      const tableView = document.getElementById('view-table');
      const tabKanban = document.getElementById('tab-kanban');
      const tabTable = document.getElementById('tab-table');

      if (viewName === 'kanban') {{
        kanbanView.style.display = 'grid';
        tableView.style.display = 'none';
        tabKanban.classList.add('active');
        tabTable.classList.remove('active');
      }} else {{
        kanbanView.style.display = 'none';
        tableView.style.display = 'block';
        tabKanban.classList.remove('active');
        tabTable.classList.add('active');
      }}
    }}

    function setFilter(type, val, btn) {{
      document.querySelectorAll(`[data-filter-type="${{type}}"]`).forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (type === 'sector') activeSector = val;
      if (type === 'tier') activeTier = val;
      applyFilters();
    }}

    function applyFilters() {{
      const q = document.getElementById('liveSearch').value.toLowerCase().trim();

      // Filter Kanban cards
      document.querySelectorAll('.card').forEach(card => {{
        const searchBlob = (card.getAttribute('data-search') || '').toLowerCase();
        const sector = card.getAttribute('data-sector') || '';
        const tier = card.getAttribute('data-tier') || '';

        const matchQ = !q || searchBlob.includes(q);
        const matchSector = (activeSector === 'all') || (sector === activeSector);
        const matchTier = (activeTier === 'all') || (tier === activeTier);

        card.style.display = (matchQ && matchSector && matchTier) ? 'block' : 'none';
      }});

      // Filter Table rows
      document.querySelectorAll('.table-row').forEach(row => {{
        const searchBlob = (row.getAttribute('data-search') || '').toLowerCase();
        const sector = row.getAttribute('data-sector') || '';
        const tier = row.getAttribute('data-tier') || '';

        const matchQ = !q || searchBlob.includes(q);
        const matchSector = (activeSector === 'all') || (sector === activeSector);
        const matchTier = (activeTier === 'all') || (tier === activeTier);

        row.style.display = (matchQ && matchSector && matchTier) ? '' : 'none';
      }});
    }}

    // Focus search on '/'
    document.addEventListener('keydown', (e) => {{
      if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {{
        e.preventDefault();
        document.getElementById('liveSearch').focus();
      }}
    }});
  </script>
</body>
</html>"""
    output_path.write_text(html_page, encoding="utf-8")


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
