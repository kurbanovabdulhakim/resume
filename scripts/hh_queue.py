"""
HeadHunter Autonomy Queue, Daily Quota, and Wave State Manager.

Selects prioritized unapplied hh.uz vacancies from db/positions.db, maintains daily
application caps (up to HH platform's 200/day ceiling), prepares humanized drafts,
and stores pre-application queue states outside schema-constrained DB statuses.

Usage:
    python scripts/hh_queue.py --prepare --limit 25 --backend ollama --json
    python scripts/hh_queue.py --status --json
"""

from __future__ import annotations
import argparse
import datetime
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.hh_ai import generate_cover_letter, load_candidate_profile, score_vacancy
from scripts.init_db import get_connection, init_database
from scripts.logger import log_event

TERMINAL_QUEUE_STATUSES = {"applied", "archived", "skipped"}


def _today_str(today: Optional[str] = None) -> str:
    return today or datetime.date.today().isoformat()


def load_autonomy_state(state_path: Path | None = None, today: Optional[str] = None) -> Dict[str, Any]:
    """Loads persisted daily application quota state, rolling over on a new date."""
    target = Path(state_path) if state_path else Config.HH_STATE_FILE
    cur_date = _today_str(today)
    default_state: Dict[str, Any] = {
        "date": cur_date,
        "applied_today": 0,
        "waves_completed": 0,
        "last_applied_at": None,
        "mode_history": [],
    }
    if not target.is_file():
        return default_state
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("date") != cur_date:
            return default_state
        default_state.update(data)
        return default_state
    except Exception:
        return default_state


def save_autonomy_state(state: Dict[str, Any], state_path: Path | None = None) -> None:
    target = Path(state_path) if state_path else Config.HH_STATE_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def record_daily_apply(
    state_path: Path | None = None,
    count: int = 1,
    today: Optional[str] = None,
    mode: Optional[str] = None,
) -> Dict[str, Any]:
    """Increments applied_today counter and persists state."""
    state = load_autonomy_state(state_path=state_path, today=today)
    state["applied_today"] = max(0, int(state.get("applied_today", 0)) + count)
    state["last_applied_at"] = datetime.datetime.now().isoformat()
    if mode and (not state.get("mode_history") or state["mode_history"][-1] != mode):
        state.setdefault("mode_history", []).append(mode)
    save_autonomy_state(state, state_path=state_path)
    return state


def remaining_daily_quota(
    daily_limit: int = 200,
    state_path: Path | None = None,
    today: Optional[str] = None,
) -> int:
    """Returns how many applications remain under today's ceiling."""
    state = load_autonomy_state(state_path=state_path, today=today)
    return max(0, int(daily_limit) - int(state.get("applied_today", 0)))


def load_queue(queue_path: Path | None = None) -> Dict[str, Dict[str, Any]]:
    """Loads queue dict keyed by vacancy_id."""
    target = Path(queue_path) if queue_path else Config.HH_QUEUE_FILE
    if not target.is_file():
        return {}
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("items"), dict):
            return raw["items"]
        if isinstance(raw, dict):
            return raw
    except Exception:
        pass
    return {}


def save_queue(items: Dict[str, Dict[str, Any]], queue_path: Path | None = None) -> None:
    target = Path(queue_path) if queue_path else Config.HH_QUEUE_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.datetime.now().isoformat(),
        "total_items": len(items),
        "items": items,
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_queue_item(item: Dict[str, Any], queue_path: Path | None = None) -> None:
    """Creates or updates one queue entry keyed by vacancy_id."""
    vid = str(item.get("vacancy_id") or item.get("id") or "").strip()
    if not vid:
        raise ValueError("Queue item must contain 'vacancy_id' or 'id'.")
    items = load_queue(queue_path=queue_path)
    merged = dict(items.get(vid, {}))
    merged.update(item)
    merged["vacancy_id"] = vid
    merged["updated_at"] = datetime.datetime.now().isoformat()
    items[vid] = merged
    save_queue(items, queue_path=queue_path)


def normalize_target_url(url: str) -> str:
    """Normalizes an HH category/search URL by stripping page offsets while keeping filters."""
    raw = str(url or "").strip()
    if not raw:
        return ""
    parts = urllib.parse.urlsplit(raw)
    query_pairs = [
        (k, v)
        for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() != "page"
    ]
    query_pairs.sort()
    path = parts.path.rstrip("/") or "/"
    clean_query = urllib.parse.urlencode(query_pairs)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, clean_query, ""))


def select_candidate_vacancies(
    db_path: Path | None = None,
    limit: int = 200,
    min_score: int = 55,
    queue_path: Path | None = None,
    include_needs_human: bool = False,
    target_url: Optional[str] = None,
    target_min_score: int = 0,
    target_only: bool = False,
) -> List[Dict[str, Any]]:
    """Selects and ranks unapplied active hh.uz vacancies matching candidate profile."""
    target_db = Path(db_path) if db_path else Config.DB_PATH
    init_database(target_db)

    queue_items = load_queue(queue_path=queue_path)
    canon_target = normalize_target_url(target_url) if target_url else ""
    always_blocked = {"applied", "archived"}
    if not include_needs_human:
        always_blocked.add("needs_human")

    conn = get_connection(target_db)
    rows = conn.execute(
        """
        SELECT v.id, v.title, v.company, v.url, v.tier, v.sector, v.salary_text, v.published_at, v.scraped_at
        FROM vacancies v
        LEFT JOIN applications a ON v.id = a.vacancy_id
        WHERE v.source = 'hh.uz' AND v.is_active = 1 AND a.id IS NULL
        ORDER BY v.tier ASC, v.published_at DESC, v.scraped_at DESC
        """
    ).fetchall()
    conn.close()

    scored: List[Dict[str, Any]] = []
    for row in rows:
        vid, title, company, url, tier, sector, salary_text, pub_at, scr_at = row
        existing = queue_items.get(str(vid))
        is_target = bool(canon_target and existing and existing.get("priority_url") == canon_target)
        if target_only and not is_target:
            continue

        if existing:
            st = existing.get("status")
            if st in always_blocked:
                continue
            if st == "skipped" and not (is_target and target_min_score <= 0):
                continue

        eff_min = target_min_score if is_target else min_score
        eff_respect_excludes = not (is_target and target_min_score <= 0)
        vac = {
            "id": str(vid),
            "title": title,
            "company": company,
            "url": url,
            "tier": tier,
            "sector": sector,
            "salary_text": salary_text,
            "published_at": pub_at,
            "scraped_at": scr_at,
        }
        fit_info = score_vacancy(
            vac,
            use_llm=False,
            min_score=eff_min,
            respect_excludes=eff_respect_excludes,
        )
        if not fit_info["fit"]:
            continue
        vac["score"] = fit_info["score"]
        vac["cv_variant"] = fit_info["cv_variant"]
        vac["reason"] = fit_info["reason"]
        vac["queued_letter"] = existing.get("cover_letter") if existing else None
        vac["is_target_url"] = is_target
        vac["priority_rank"] = existing.get("priority_rank") if existing else None
        vac["respect_excludes"] = eff_respect_excludes
        vac["effective_min_score"] = eff_min
        scored.append(vac)

    scored.sort(
        key=lambda v: (
            0 if v.get("is_target_url") else 1,
            int(v.get("priority_rank") or 999999) if v.get("is_target_url") else -int(v["score"]),
            int(v.get("tier") or 2),
            -(len(str(v.get("published_at") or ""))),
        )
    )
    return scored[:limit]


def prepare_queue_items(
    limit: int = 25,
    min_score: int = 55,
    backend: str = "ollama",
    db_path: Path | None = None,
    queue_path: Path | None = None,
) -> Dict[str, Any]:
    """Pre-scores and prepares humanized cover letters for up to limit candidates."""
    candidates = select_candidate_vacancies(db_path=db_path, limit=limit, min_score=min_score, queue_path=queue_path)
    profile = load_candidate_profile()
    prepared: List[Dict[str, Any]] = []

    for vac in candidates:
        res_score = score_vacancy(vac, profile=profile, use_llm=(backend != "none"), backend=backend, min_score=min_score)
        if not res_score["fit"]:
            upsert_queue_item(
                {
                    "vacancy_id": vac["id"],
                    "title": vac["title"],
                    "company": vac["company"],
                    "url": vac["url"],
                    "score": res_score["score"],
                    "status": "skipped",
                    "detail": res_score["reason"],
                },
                queue_path=queue_path,
            )
            continue

        letter = generate_cover_letter(
            vac, profile=profile, backend=backend, cv_variant=res_score["cv_variant"]
        )
        entry = {
            "vacancy_id": vac["id"],
            "title": vac["title"],
            "company": vac["company"],
            "url": vac["url"],
            "tier": vac["tier"],
            "sector": vac["sector"],
            "score": res_score["score"],
            "cv_variant": letter["cv_variant"],
            "cover_letter": letter["text"],
            "letter_source": letter["source"],
            "audit_ok": letter["audit"]["ok"],
            "status": "ready",
        }
        upsert_queue_item(entry, queue_path=queue_path)
        prepared.append(entry)

    out = {
        "success": True,
        "code": Config.EXIT_SUCCESS if prepared else Config.EXIT_NO_DATA,
        "prepared_count": len(prepared),
        "candidates_checked": len(candidates),
        "items": prepared,
    }
    log_event("HH_QUEUE_PREPARED", {"prepared_count": len(prepared), "checked": len(candidates), "backend": backend})
    return out


def queue_status_summary(
    db_path: Path | None = None,
    queue_path: Path | None = None,
    state_path: Path | None = None,
    daily_limit: int = 200,
) -> Dict[str, Any]:
    """Returns queue breakdown, daily counter, and remaining DB unapplied count."""
    items = load_queue(queue_path=queue_path)
    counts: Dict[str, int] = {}
    for entry in items.values():
        st = str(entry.get("status", "unknown"))
        counts[st] = counts.get(st, 0) + 1

    state = load_autonomy_state(state_path=state_path)
    candidates = select_candidate_vacancies(db_path=db_path, limit=5000, queue_path=queue_path)
    return {
        "success": True,
        "code": Config.EXIT_SUCCESS,
        "date": state["date"],
        "applied_today": state["applied_today"],
        "remaining_today": remaining_daily_quota(daily_limit=daily_limit, state_path=state_path),
        "daily_limit": daily_limit,
        "eligible_candidates_in_db": len(candidates),
        "queue_counts": counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage HeadHunter autonomy queue and daily limits")
    parser.add_argument("--prepare", action="store_true", help="Prepare scored vacancies & humanized cover letters")
    parser.add_argument("--status", action="store_true", help="Show daily quota and queue status")
    parser.add_argument("--limit", type=int, default=25, help="Max vacancies to prepare/list")
    parser.add_argument("--daily-limit", type=int, default=200, help="Daily application cap")
    parser.add_argument("--min-score", type=int, default=55, help="Minimum role-fit score (0-100)")
    parser.add_argument("--backend", choices=("ollama", "hermes", "none"), default="ollama", help="LLM backend")
    parser.add_argument("--reset-needs-human", action="store_true", help="Clear needs_human flags so items retry")
    parser.add_argument("--db-path", type=str, default=None, help="Custom DB path")
    parser.add_argument("--queue-path", type=str, default=None, help="Custom queue JSON path")
    parser.add_argument("--state-path", type=str, default=None, help="Custom daily state JSON path")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    db_target = Path(args.db_path) if args.db_path else None
    q_target = Path(args.queue_path) if args.queue_path else None
    s_target = Path(args.state_path) if args.state_path else None

    if args.reset_needs_human:
        items = load_queue(queue_path=q_target)
        cleared = 0
        for vid in list(items.keys()):
            if items[vid].get("status") == "needs_human":
                del items[vid]
                cleared += 1
        save_queue(items, queue_path=q_target)
        res = {"success": True, "code": Config.EXIT_SUCCESS, "cleared_needs_human": cleared}
        print(json.dumps(res, ensure_ascii=False, indent=2) if args.json else f"[OK] Cleared {cleared} needs_human entries.")
        return Config.EXIT_SUCCESS

    if args.prepare:
        res = prepare_queue_items(
            limit=args.limit,
            min_score=args.min_score,
            backend=args.backend,
            db_path=db_target,
            queue_path=q_target,
        )
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"[OK] Prepared {res['prepared_count']} of {res['candidates_checked']} candidates.")
        return res["code"]

    res = queue_status_summary(db_path=db_target, queue_path=q_target, state_path=s_target, daily_limit=args.daily_limit)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(
            f"[STATUS] Date: {res['date']} | Applied today: {res['applied_today']}/{res['daily_limit']} | "
            f"Remaining: {res['remaining_today']} | Eligible in DB: {res['eligible_candidates_in_db']}"
        )
    return res["code"]


if __name__ == "__main__":
    sys.exit(main())
