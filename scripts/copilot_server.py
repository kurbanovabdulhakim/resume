"""
Hermes Interactive Copilot Server (Option 1).

Serves a lightning-fast, zero-bot-detection Copilot Web UI for HeadHunter applications.
Ollama pre-generates personalized cover letters; the user clicks to copy to clipboard
and open the vacancy directly in their genuine browser with 0% CAPTCHA.
"""

from __future__ import annotations

import argparse
import datetime
import http.server
import json
import os
import re
import socketserver
import sqlite3
import sys
import threading
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import init_database


class CopilotService:
    """Core logic managing positions.db and hh_autonomy_queue.json for Copilot UI."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        queue_path: Optional[Path] = None,
        state_path: Optional[Path] = None,
    ) -> None:
        self.db_path = Path(db_path) if db_path else Config.DB_PATH
        self.queue_path = Path(queue_path) if queue_path else Config.HH_QUEUE_FILE
        self.state_path = Path(state_path) if state_path else Config.HH_STATE_FILE
        init_database(self.db_path)

    def get_queue(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns ordered vacancies merged with live SQLite applications status."""
        items_map: Dict[str, Dict[str, Any]] = {}
        if self.queue_path.exists():
            try:
                data = json.loads(self.queue_path.read_text(encoding="utf-8"))
                items_map = data.get("items", {})
            except Exception:
                items_map = {}

        # Fetch applications from DB to guarantee live sync
        conn = sqlite3.connect(self.db_path)
        applied_rows = conn.execute(
            "SELECT vacancy_id, status, applied_at, cv_variant, cover_letter_sent FROM applications"
        ).fetchall()
        db_apps = {str(r[0]): {"status": r[1], "applied_at": r[2], "cv_variant": r[3], "cover_letter": r[4]} for r in applied_rows}

        # Also fetch vacancies details from DB
        vac_rows = conn.execute("SELECT id, title, company, url, tier, sector FROM vacancies").fetchall()
        db_vacs = {str(r[0]): {"title": r[1], "company": r[2], "url": r[3], "tier": r[4], "sector": r[5]} for r in vac_rows}
        conn.close()

        merged_list: List[Dict[str, Any]] = []

        # First add queue items
        seen_ids = set()
        for vid, q_item in items_map.items():
            vid_str = str(vid)
            seen_ids.add(vid_str)
            item = dict(q_item)
            item["vacancy_id"] = vid_str

            # Overlay DB app state if applied in DB, but honor explicit queued status in queue file
            if vid_str in db_apps:
                if q_item.get("status") == "queued":
                    item["status"] = "queued"
                else:
                    item["status"] = db_apps[vid_str]["status"]
                item["applied_at"] = db_apps[vid_str].get("applied_at")

                # Keep tailored cover letter from queue if present, otherwise fallback to DB
                if not item.get("cover_letter") or len(str(item.get("cover_letter")).strip()) <= 10:
                    db_let = db_apps[vid_str].get("cover_letter")
                    if isinstance(db_let, str) and len(db_let.strip()) > 10:
                        item["cover_letter"] = db_let
                if not item.get("cv_variant") and db_apps[vid_str].get("cv_variant"):
                    item["cv_variant"] = db_apps[vid_str]["cv_variant"]

            # Sanitize cover letter if it was saved as 1 or '1'
            cur_let = item.get("cover_letter")
            if cur_let in (1, "1", "0", 0) or (isinstance(cur_let, str) and len(cur_let.strip()) <= 5):
                item["cover_letter"] = ""

            # Overlay vacancy metadata
            if vid_str in db_vacs:
                if not item.get("title"):
                    item["title"] = db_vacs[vid_str]["title"]
                if not item.get("company"):
                    item["company"] = db_vacs[vid_str]["company"]
                if not item.get("url"):
                    item["url"] = db_vacs[vid_str]["url"]
                item["tier"] = db_vacs[vid_str]["tier"]
                item["sector"] = db_vacs[vid_str]["sector"]

            merged_list.append(item)

        # Sort: 'queued' first by priority_rank, then 'applied' by applied_at desc
        def sort_key(x: Dict[str, Any]) -> tuple:
            is_queued = 0 if x.get("status") == "queued" else 1
            rank = x.get("priority_rank", 999999)
            return (is_queued, rank)

        merged_list.sort(key=sort_key)

        if status_filter:
            merged_list = [x for x in merged_list if x.get("status") == status_filter]

        return merged_list

    def mark_applied(
        self,
        vacancy_id: str,
        cover_letter: str = "",
        cv_variant: str = "financial_analyst",
        notes: str = "Applied via Hermes Copilot Dashboard",
    ) -> Dict[str, Any]:
        """Records the application in SQLite, queue JSON, and daily state JSON."""
        vid = str(vacancy_id).strip()
        now_iso = datetime.datetime.now().isoformat()

        # 1. Update positions.db
        conn = sqlite3.connect(self.db_path)
        existing = conn.execute("SELECT id FROM applications WHERE vacancy_id = ?", (vid,)).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE applications
                SET status = 'applied', applied_at = ?, cv_variant = ?, cover_letter_sent = ?, notes = ?, last_updated = ?
                WHERE vacancy_id = ?
                """,
                (now_iso, cv_variant, cover_letter, notes, now_iso, vid),
            )
        else:
            conn.execute(
                """
                INSERT INTO applications (vacancy_id, status, applied_at, cv_variant, cover_letter_sent, notes, last_updated)
                VALUES (?, 'applied', ?, ?, ?, ?, ?)
                """,
                (vid, now_iso, cv_variant, cover_letter, notes, now_iso),
            )
        conn.commit()
        conn.close()

        # 2. Update queue JSON
        if self.queue_path.exists():
            try:
                q_data = json.loads(self.queue_path.read_text(encoding="utf-8"))
                items = q_data.get("items", {})
                if vid in items:
                    items[vid]["status"] = "applied"
                    items[vid]["updated_at"] = now_iso
                    items[vid]["cover_letter"] = cover_letter
                    items[vid]["cv_variant"] = cv_variant
                else:
                    items[vid] = {
                        "vacancy_id": vid,
                        "status": "applied",
                        "updated_at": now_iso,
                        "cover_letter": cover_letter,
                        "cv_variant": cv_variant,
                    }
                q_data["updated_at"] = now_iso
                self.queue_path.write_text(json.dumps(q_data, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass

        # 3. Update daily state JSON
        today_str = datetime.date.today().isoformat()
        state = {"date": today_str, "applied_today": 0, "waves_completed": 0, "last_applied_at": None}
        if self.state_path.exists():
            try:
                state = json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        if state.get("date") != today_str:
            state["date"] = today_str
            state["applied_today"] = 1
        else:
            state["applied_today"] = int(state.get("applied_today", 0)) + 1
        state["last_applied_at"] = now_iso
        self.state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

        return {"success": True, "vacancy_id": vid, "applied_at": now_iso}

    def generate_letter_for(self, vacancy_id: str) -> Dict[str, Any]:
        """Uses Ollama qwen2.5-coder:7b to generate tailored letter on demand."""
        vid = str(vacancy_id).strip()
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT id, title, company, url FROM vacancies WHERE id = ?", (vid,)).fetchone()
        conn.close()

        title = row[1] if row else "Финансовый аналитик"
        company = row[2] if row else "Компания"
        url = row[3] if row else f"https://tashkent.hh.uz/vacancy/{vid}"

        from scripts.hh_ai import generate_cover_letter

        gen = generate_cover_letter({"id": vid, "title": title, "company": company, "url": url})
        text = gen.get("text", "")
        variant = gen.get("cv_variant", "financial_analyst")

        # Save into queue
        if self.queue_path.exists():
            try:
                q_data = json.loads(self.queue_path.read_text(encoding="utf-8"))
                items = q_data.get("items", {})
                if vid in items:
                    items[vid]["cover_letter"] = text
                    items[vid]["cv_variant"] = variant
                    self.queue_path.write_text(json.dumps(q_data, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass

        return {"success": True, "cover_letter": text, "cv_variant": variant}

    def pregenerate_queued(self, count: int = 30, verbose: bool = True) -> int:
        """Pregenerates cover letters in batch for the first N queued vacancies."""
        items = self.get_queue(status_filter="queued")
        to_gen = [x for x in items if not x.get("cover_letter")][:count]
        if not to_gen:
            if verbose:
                print(f"[COPILOT] All top queued items already have tailored cover letters!")
            return 0

        if verbose:
            print(f"[COPILOT] Pre-generating cover letters for {len(to_gen)} vacancies via Ollama...")

        done = 0
        for idx, item in enumerate(to_gen, 1):
            vid = item["vacancy_id"]
            comp = item.get("company", "Company")
            title = item.get("title", "Position")
            if verbose:
                print(f"  [{idx}/{len(to_gen)}] Generating: {comp} — {title}...", flush=True)
            res = self.generate_letter_for(vid)
            if res.get("success"):
                done += 1
        return done


# Embedded Single-Page Application (HTML/CSS/JS)
COPILOT_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hermes Copilot — Отклики на HeadHunter</title>
<style>
:root {
  --bg: #0b0f19;
  --card-bg: #151c2e;
  --card-border: #232d46;
  --text-main: #f1f5f9;
  --text-muted: #94a3b8;
  --accent: #38bdf8;
  --accent-hover: #0284c7;
  --green: #22c55e;
  --green-hover: #16a34a;
  --yellow: #eab308;
  --blue: #3b82f6;
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--text-main);
  padding: 24px;
  line-height: 1.5;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto 24px auto;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--card-border);
}
.header h1 { font-size: 24px; font-weight: 700; color: #fff; }
.header-badge {
  background: #1e293b;
  border: 1px solid #334155;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
}
.stats-bar {
  display: flex;
  gap: 16px;
  max-width: 1200px;
  margin: 0 auto 24px auto;
}
.stat-card {
  flex: 1;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  padding: 16px 20px;
  border-radius: 12px;
}
.stat-title { font-size: 13px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; }
.stat-value { font-size: 28px; font-weight: 800; color: #fff; margin-top: 4px; }

.controls-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto 20px auto;
  gap: 16px;
  flex-wrap: wrap;
}
.tabs { display: flex; gap: 8px; }
.tab-btn {
  background: #1e293b;
  border: 1px solid #334155;
  color: var(--text-muted);
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s;
}
.tab-btn.active {
  background: var(--accent);
  color: #0b0f19;
  border-color: var(--accent);
}
.search-input {
  background: #1e293b;
  border: 1px solid #334155;
  color: #fff;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  min-width: 280px;
}
.search-input:focus { outline: none; border-color: var(--accent); }

.grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 1200px;
  margin: 0 auto;
}
.card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 14px;
  padding: 20px;
  transition: transform 0.15s, border-color 0.15s;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.card:hover { border-color: #3b82f6; }
.card.applied {
  border-color: #15803d;
  background: #0f1c1d;
  opacity: 0.85;
}
.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}
.card-info h2 { font-size: 18px; font-weight: 700; color: #fff; }
.card-company { font-size: 15px; color: var(--accent); font-weight: 600; margin-top: 2px; }
.badge-group { display: flex; gap: 8px; }
.badge {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.badge-queued { background: rgba(234, 179, 8, 0.15); color: var(--yellow); border: 1px solid rgba(234, 179, 8, 0.3); }
.badge-applied { background: rgba(34, 197, 94, 0.15); color: var(--green); border: 1px solid rgba(34, 197, 94, 0.3); }

.letter-box {
  background: #0d1322;
  border: 1px solid #1e293b;
  border-radius: 8px;
  padding: 14px;
  font-size: 13.5px;
  color: #cbd5e1;
  white-space: pre-wrap;
  font-family: inherit;
  line-height: 1.6;
}
.letter-box:focus {
  outline: none;
  border-color: var(--accent);
}

.card-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.btn-primary {
  background: var(--green);
  color: #0b0f19;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.2s, transform 0.1s;
}
.btn-primary:hover { background: var(--green-hover); transform: translateY(-1px); }
.btn-primary:active { transform: translateY(0); }

.btn-secondary {
  background: #1e293b;
  color: #cbd5e1;
  border: 1px solid #334155;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-secondary:hover { background: #334155; color: #fff; }

.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: #047857;
  color: #fff;
  padding: 14px 22px;
  border-radius: 10px;
  font-weight: 600;
  box-shadow: 0 10px 25px rgba(0,0,0,0.5);
  display: none;
  z-index: 1000;
}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>Hermes Copilot — Интерактивный пульт откликов</h1>
    <p style="color: var(--text-muted); font-size: 14px; margin-top: 4px;">Кликните кнопку — письмо автоматически скопируется в буфер, откроется HH, а отклик отметится в базе.</p>
  </div>
  <div class="header-badge">Ollama qwen2.5-coder:7b • 0% Капчи</div>
</div>

<div class="stats-bar">
  <div class="stat-card">
    <div class="stat-title">В очереди на отправку</div>
    <div class="stat-value" id="stat-queued">0</div>
  </div>
  <div class="stat-card">
    <div class="stat-title">Отправлено сегодня</div>
    <div class="stat-value" id="stat-applied" style="color: var(--green);">0</div>
  </div>
  <div class="stat-card">
    <div class="stat-title">Всего в базе откликов</div>
    <div class="stat-value" id="stat-total">0</div>
  </div>
</div>

<div class="controls-bar">
  <div class="tabs">
    <button class="tab-btn active" onclick="setTab('queued', this)">В очереди (<span id="tab-cnt-queued">0</span>)</button>
    <button class="tab-btn" onclick="setTab('applied', this)">Отправленные (<span id="tab-cnt-applied">0</span>)</button>
    <button class="tab-btn" onclick="setTab('all', this)">Все вакансии (<span id="tab-cnt-all">0</span>)</button>
  </div>
  <input type="text" class="search-input" id="search" placeholder="Поиск по компании или вакансии..." oninput="render()">
</div>

<div class="grid" id="items-grid">
  <div style="text-align: center; color: var(--text-muted); padding: 40px;">Загрузка очереди вакансий...</div>
</div>

<div class="toast" id="toast">✅ Письмо скопировано! Переходим на HeadHunter...</div>

<script>
let allItems = [];
let activeTab = 'queued';

async function fetchQueue() {
  try {
    const res = await fetch('/api/queue');
    const data = await res.json();
    allItems = data.items || [];
    updateStats();
    render();
  } catch (err) {
    console.error('Fetch queue failed:', err);
  }
}

function updateStats() {
  const queued = allItems.filter(x => x.status === 'queued').length;
  const applied = allItems.filter(x => x.status === 'applied').length;
  document.getElementById('stat-queued').innerText = queued;
  document.getElementById('stat-applied').innerText = applied;
  document.getElementById('stat-total').innerText = allItems.length;

  document.getElementById('tab-cnt-queued').innerText = queued;
  document.getElementById('tab-cnt-applied').innerText = applied;
  document.getElementById('tab-cnt-all').innerText = allItems.length;
}

function setTab(tab, btn) {
  activeTab = tab;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  render();
}

function showToast(text) {
  const t = document.getElementById('toast');
  t.innerText = text;
  t.style.display = 'block';
  setTimeout(() => { t.style.display = 'none'; }, 3000);
}

async function applyOne(vid, url) {
  const card = document.getElementById('card-' + vid);
  const ta = document.getElementById('letter-' + vid);
  const letter = ta ? ta.value : '';

  // 1. Copy to clipboard
  try {
    await navigator.clipboard.writeText(letter);
    showToast('✅ Письмо скопировано в буфер! Открываю HH...');
  } catch (e) {
    // fallback
    if (ta) {
      ta.select();
      document.execCommand('copy');
      showToast('✅ Письмо скопировано! Открываю HH...');
    }
  }

  // 2. Open vacancy in new tab
  window.open(url, '_blank');

  // 3. Mark applied in backend API
  const item = allItems.find(x => x.vacancy_id === vid);
  if (item) {
    item.status = 'applied';
    item.applied_at = new Date().toISOString();
  }
  updateStats();
  render();

  try {
    await fetch('/api/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vacancy_id: vid,
        cover_letter: letter,
        cv_variant: item ? item.cv_variant : 'financial_analyst'
      })
    });
  } catch (err) {
    console.error('API apply failed:', err);
  }
}

async function openChatAndCopy(vid, url) {
  const ta = document.getElementById('letter-' + vid);
  const letter = ta ? ta.value : '';
  try {
    await navigator.clipboard.writeText(letter);
    showToast('💬 Письмо скопировано в буфер! Открываю чат с работодателем...');
  } catch (e) {
    if (ta) {
      ta.select();
      document.execCommand('copy');
      showToast('💬 Письмо скопировано в буфер! Открываю чат с работодателем...');
    }
  }
  window.open(url, '_blank');
}

async function copyOnly(vid) {
  const ta = document.getElementById('letter-' + vid);
  if (ta) {
    await navigator.clipboard.writeText(ta.value);
    showToast('📋 Письмо скопировано в буфер обмена!');
  }
}

function render() {
  const container = document.getElementById('items-grid');
  const q = document.getElementById('search').value.toLowerCase().trim();

  let filtered = allItems;
  if (activeTab === 'queued') {
    filtered = filtered.filter(x => x.status === 'queued');
  } else if (activeTab === 'applied') {
    filtered = filtered.filter(x => x.status === 'applied');
  }

  if (q) {
    filtered = filtered.filter(x => 
      (x.company || '').toLowerCase().includes(q) || 
      (x.title || '').toLowerCase().includes(q)
    );
  }

  if (filtered.length === 0) {
    container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 60px; font-size: 16px;">Нет подходящих вакансий в этом списке.</div>';
    return;
  }

  container.innerHTML = filtered.map(item => {
    const isApplied = item.status === 'applied';
    const badgeHtml = isApplied 
      ? '<span class="badge badge-applied">✅ Отклик отправлен</span>'
      : '<span class="badge badge-queued">В очереди</span>';
    
    const letter = item.cover_letter || 'Загрузка или генерация письма...';
    const url = item.url || ('https://tashkent.hh.uz/vacancy/' + item.vacancy_id);

    const salaryHtml = item.salary && item.salary !== 'Не указана'
      ? `<div style="color: #fbbf24; font-weight: 700; font-size: 14px; margin-top: 4px;">💰 ${item.salary}</div>`
      : '';
    const tierBadge = item.tier === 1 
      ? '<span style="background: rgba(52, 211, 153, 0.2); color: #34d399; font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 700; margin-left: 8px;">★ Tier 1</span>'
      : '';

    return `
      <div class="card ${isApplied ? 'applied' : ''}" id="card-${item.vacancy_id}">
        <div class="card-top">
          <div class="card-info">
            <h2>${item.title || 'Позиция'}</h2>
            <div class="card-company">${item.company || 'Компания'}${tierBadge}</div>
            ${salaryHtml}
          </div>
          <div class="badge-group">
            ${badgeHtml}
          </div>
        </div>

        <textarea class="letter-box" id="letter-${item.vacancy_id}" rows="5">${letter}</textarea>

        <div class="card-actions">
          ${isApplied ? `
            <button class="btn-primary" style="background: linear-gradient(135deg, #059669, #10b981);" onclick="openChatAndCopy('${item.vacancy_id}', '${url}')">
              <span>💬 Открыть чат на HH (Скопировать письмо)</span>
            </button>
          ` : `
            <button class="btn-primary" onclick="applyOne('${item.vacancy_id}', '${url}')">
              <span>⚡ Откликнуться в 1 клик (Скопировать и открыть HH)</span>
            </button>
          `}
          <div style="display: flex; gap: 8px;">
            <button class="btn-secondary" onclick="copyOnly('${item.vacancy_id}')">📋 Скопировать письмо</button>
            <a href="${url}" target="_blank" class="btn-secondary" style="text-decoration: none; display: flex; align-items: center;">🔗 Открыть вакансию</a>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

fetchQueue();
</script>
</body>
</html>
"""


class CopilotRequestHandler(http.server.BaseHTTPRequestHandler):
    """Handles REST API and static HTML requests for Copilot."""

    service: CopilotService

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/copilot.html", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(COPILOT_HTML.encode("utf-8"))
            return

        if parsed.path == "/api/queue":
            qs = urllib.parse.parse_qs(parsed.query)
            status_filter = qs.get("status", [None])[0]
            items = self.service.get_queue(status_filter=status_filter)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "items": items}, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if parsed.path == "/api/apply":
            vid = payload.get("vacancy_id", "")
            letter = payload.get("cover_letter", "")
            cv = payload.get("cv_variant", "financial_analyst")
            res = self.service.mark_applied(vid, cover_letter=letter, cv_variant=cv)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
            return

        if parsed.path == "/api/generate":
            vid = payload.get("vacancy_id", "")
            res = self.service.generate_letter_for(vid)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        # Keep terminal output clean
        return


def run_copilot_server(
    port: int = 8080,
    db_path: Optional[Path] = None,
    queue_path: Optional[Path] = None,
    state_path: Optional[Path] = None,
    pregenerate_count: int = 30,
    open_browser: bool = True,
) -> None:
    """Initializes service, pregenerates letters, and runs HTTP server."""
    service = CopilotService(db_path=db_path, queue_path=queue_path, state_path=state_path)

    if pregenerate_count > 0:
        service.pregenerate_queued(count=pregenerate_count, verbose=True)

    handler = CopilotRequestHandler
    handler.service = service

    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True

    with ThreadedTCPServer(("127.0.0.1", port), handler) as httpd:
        url = f"http://127.0.0.1:{port}"
        print(f"\n" + "=" * 68)
        print(f"[OK] Hermes Copilot Server listening at: {url}")
        print(f"     Откройте эту страницу в браузере для отправки откликов.")
        print(f"     Нажмите Ctrl+C для остановки сервера.")
        print(f"=" * 68 + "\n", flush=True)

        if open_browser:
            import webbrowser
            try:
                webbrowser.open(url)
            except Exception:
                pass

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[STOP] Stopping Hermes Copilot Server...")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Hermes Copilot Dashboard Server")
    parser.add_argument("--port", type=int, default=8080, help="HTTP server port")
    parser.add_argument("--pregenerate", type=int, default=30, help="Number of queued letters to pregenerate via Ollama")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_args()

    run_copilot_server(
        port=args.port,
        pregenerate_count=args.pregenerate,
        open_browser=not args.no_browser,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
