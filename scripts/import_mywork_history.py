"""
Import Historical Vacancies & Applications from mywork into positions.db.

Ingests:
1. Ташкент_Вакансии_Финансы_Август_Сентябрь_2026.xlsx (2,278 vacancies, 1,328 applied)
2. final_invitations_report.json (52 invitations & interviews)
3. REAL_HEADHUNTER_NEGOTIATIONS.json & chats_detailed_breakdown.json (live negotiation states)
4. АНАЛИЗ_2500_ВАКАНСИЙ_ТАШКЕНТ.xlsx (1,406 rejected/excluded vacancies with reasons)

Usage:
    python scripts/import_mywork_history.py [--excel PATH] [--dry-run] [--json]
"""

from __future__ import annotations
import argparse
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import openpyxl
from scripts.config import Config
from scripts.init_db import get_connection, init_database
from scripts.logger import log_event
from scripts.sync_hermes import normalize_sector, parse_salary_range

TIER_1_KEYWORDS = [
    "банк", "bank", "tbc", "anor", "kapital", "ipak yuli", "hamkor", "sqb", "nbu", "infin",
    "aloqa", "asakabank", "deloitte", "pwc", "kpmg", "ey", "ernst", "uzum", "payme", "click",
    "beeline", "ucell", "mobiuz", "korzinka", "makro", "havas", "akfa", "artel", "nestle",
    "pepsi", "coca-cola", "knauf", "bat", "huawei", "zte"
]


def infer_tier(company: str) -> int:
    comp_lower = company.lower()
    if any(k in comp_lower for k in TIER_1_KEYWORDS):
        return 1
    return 2


def parse_russian_date(date_str: Optional[str]) -> str:
    """Converts '09.09.2026 14:00' to ISO format '2026-09-09T14:00:00'."""
    if not date_str:
        return datetime.datetime.now().isoformat()
    try:
        parts = date_str.strip().split()
        d_parts = parts[0].split(".")
        day, month, year = int(d_parts[0]), int(d_parts[1]), int(d_parts[2])
        if len(parts) > 1 and ":" in parts[1]:
            t_parts = parts[1].split(":")
            hour, minute = int(t_parts[0]), int(t_parts[1])
            return datetime.datetime(year, month, day, hour, minute).isoformat()
        return datetime.datetime(year, month, day, 12, 0).isoformat()
    except Exception:
        return datetime.datetime.now().isoformat()


def determine_cv_variant(sector: str, title: str) -> str:
    combined = f"{sector} {title}".lower()
    if any(k in combined for k in ["финанс", "finance", "аудит", "бухгалтер", "казначей"]):
        return "financial_analyst"
    if any(k in combined for k in ["аналитик", "data", "analytics", " bi ", "sql"]):
        return "business_analyst"
    return "operations_manager"


def import_history(
    excel_path: Optional[Path] = None,
    rejected_excel_path: Optional[Path] = None,
    invitations_path: Optional[Path] = None,
    negotiations_path: Optional[Path] = None,
    db_path: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    target_db = Path(db_path) if db_path else Config.DB_PATH
    init_database(target_db)

    mywork_dir = Config.PROJECT_ROOT.parent / "mywork"
    main_excel = Path(excel_path) if excel_path else (mywork_dir / "Ташкент_Вакансии_Финансы_Август_Сентябрь_2026.xlsx")
    rej_excel = Path(rejected_excel_path) if rejected_excel_path else (mywork_dir / "АНАЛИЗ_2500_ВАКАНСИЙ_ТАШКЕНТ.xlsx")
    inv_file = Path(invitations_path) if invitations_path else (mywork_dir / "final_invitations_report.json")
    neg_file = Path(negotiations_path) if negotiations_path else (mywork_dir / "REAL_HEADHUNTER_NEGOTIATIONS.json")

    if not main_excel.is_file():
        return {"success": False, "error": f"Main Excel file not found: {main_excel}", "code": Config.EXIT_ERROR}

    conn = get_connection(target_db)
    cursor = conn.cursor()

    stats = {
        "vacancies_added": 0,
        "vacancies_updated": 0,
        "vacancies_excluded_added": 0,
        "applications_added": 0,
        "applications_updated": 0,
        "status_progressed": 0,
    }

    # 1. Parse Main Excel: Ташкент_Вакансии_Финансы_Август_Сентябрь_2026.xlsx
    wb = openpyxl.load_workbook(main_excel, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    wb.close()

    header = rows[0]
    id_idx = header.index("ID Вакансии")
    title_idx = header.index("Название вакансии")
    company_idx = header.index("Компания")
    salary_idx = header.index("Зарплата (текст)")
    pub_idx = header.index("Дата публикации")
    url_idx = header.index("Ссылка на вакансию")
    letter_idx = header.index("Сопроводительное письмо")
    status_idx = header.index("Статус отклика")
    applied_time_idx = header.index("Время отклика")
    screen_idx = header.index("Скриншот чата")

    for r in rows[1:]:
        raw_id = r[id_idx]
        if raw_id is None:
            continue
        vid = str(raw_id).strip()
        if not vid or vid == "None":
            continue

        title = str(r[title_idx] or "Без названия").strip()
        company = str(r[company_idx] or "Не указано").strip()
        salary_raw = str(r[salary_idx] or "").strip()
        pub_raw = str(r[pub_idx] or "").strip()
        url = str(r[url_idx] or f"https://tashkent.hh.uz/vacancy/{vid}").strip()
        cover_letter = str(r[letter_idx] or "").strip()
        status_text = str(r[status_idx] or "").strip()
        applied_time_raw = str(r[applied_time_idx] or "").strip()
        screen_path = str(r[screen_idx] or "").strip()

        tier = infer_tier(company)
        sector = normalize_sector("", title)
        s_min, s_max = parse_salary_range(salary_raw)
        published_iso = parse_russian_date(pub_raw)
        applied_iso = parse_russian_date(applied_time_raw) if applied_time_raw else published_iso

        is_applied = (status_text == "Отправлен")
        is_active = 1 if is_applied else 0

        cursor.execute("SELECT id, tier, sector FROM vacancies WHERE id = ?", (vid,))
        existing_v = cursor.fetchone()
        if existing_v:
            stats["vacancies_updated"] += 1
            if not dry_run:
                cursor.execute(
                    """
                    UPDATE vacancies 
                    SET salary_min = coalesce(salary_min, ?),
                        salary_max = coalesce(salary_max, ?),
                        salary_text = coalesce(salary_text, ?),
                        published_at = coalesce(published_at, ?)
                    WHERE id = ?
                """,
                    (s_min, s_max, salary_raw, published_iso, vid),
                )
        else:
            stats["vacancies_added"] += 1
            if not dry_run:
                cursor.execute(
                    """
                    INSERT INTO vacancies (id, title, company, url, source, tier, sector, salary_min, salary_max, salary_text, published_at, scraped_at, is_active)
                    VALUES (?, ?, ?, ?, 'hh.uz', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (vid, title, company, url, tier, sector, s_min, s_max, salary_raw, published_iso, published_iso, is_active),
                )

        if is_applied:
            cursor.execute("SELECT id, status FROM applications WHERE vacancy_id = ?", (vid,))
            existing_app = cursor.fetchone()
            cv_variant = determine_cv_variant(sector, title)
            cover_sent = 1 if len(cover_letter) > 10 else 0
            pdf_sent = 1 if len(screen_path) > 5 else 0
            note = f"Отклик Август/Сентябрь 2026. Скриншот: {Path(screen_path).name if screen_path else 'нет'}"

            if existing_app:
                stats["applications_updated"] += 1
                if not dry_run:
                    cursor.execute(
                        """
                        UPDATE applications
                        SET cover_letter_sent = max(cover_letter_sent, ?),
                            pdf_sent_in_chat = max(pdf_sent_in_chat, ?),
                            applied_at = coalesce(applied_at, ?)
                        WHERE vacancy_id = ?
                    """,
                        (cover_sent, pdf_sent, applied_iso, vid),
                    )
            else:
                stats["applications_added"] += 1
                if not dry_run:
                    cursor.execute(
                        """
                        INSERT INTO applications (vacancy_id, status, applied_at, cv_variant, cover_letter_sent, pdf_sent_in_chat, notes, last_updated)
                        VALUES (?, 'applied', ?, ?, ?, ?, ?, ?)
                    """,
                        (vid, applied_iso, cv_variant, cover_sent, pdf_sent, note, applied_iso),
                    )

    # 2. Parse Invitations & Interviews: final_invitations_report.json
    if inv_file.is_file():
        try:
            with open(inv_file, "r", encoding="utf-8") as f:
                inv_list = json.load(f)
            for it in inv_list:
                url = it.get("url", "")
                m = re.search(r"/vacancy/(\d+)", url)
                if not m:
                    continue
                vid = m.group(1)
                emp_msg = it.get("employer_msg", "")
                company = it.get("company", "Работодатель")
                title = it.get("title", "Позиция")
                tier = infer_tier(company)
                sector = normalize_sector("", title)
                s_min, s_max = parse_salary_range(it.get("salary"))

                # Status: if "собеседование" in message -> 'interview', else 'invited'
                app_status = "interview" if "собеседован" in emp_msg.lower() else "invited"
                action_note = f"Приглашение: {emp_msg}. Контакты: {it.get('telegrams') or it.get('phones') or 'в чате HH'}"
                now_iso = datetime.datetime.now().isoformat()

                # Ensure vacancy exists
                cursor.execute("SELECT id FROM vacancies WHERE id = ?", (vid,))
                if not cursor.fetchone():
                    stats["vacancies_added"] += 1
                    if not dry_run:
                        cursor.execute(
                            """
                            INSERT INTO vacancies (id, title, company, url, source, tier, sector, salary_min, salary_max, salary_text, scraped_at, is_active)
                            VALUES (?, ?, ?, ?, 'hh.uz', ?, ?, ?, ?, ?, ?, 1)
                        """,
                            (vid, title, company, url, tier, sector, s_min, s_max, it.get("salary"), now_iso),
                        )

                # Upsert application stage
                cursor.execute("SELECT id, status, notes FROM applications WHERE vacancy_id = ?", (vid,))
                existing_app = cursor.fetchone()
                if existing_app:
                    stats["status_progressed"] += 1
                    if not dry_run:
                        cursor.execute(
                            """
                            UPDATE applications
                            SET status = ?, notes = coalesce(notes, '') || ' | ' || ?, last_updated = ?
                            WHERE vacancy_id = ?
                        """,
                            (app_status, action_note, now_iso, vid),
                        )
                else:
                    stats["applications_added"] += 1
                    if not dry_run:
                        cursor.execute(
                            """
                            INSERT INTO applications (vacancy_id, status, applied_at, cv_variant, cover_letter_sent, pdf_sent_in_chat, notes, last_updated)
                            VALUES (?, ?, ?, 'financial_analyst', 1, 1, ?, ?)
                        """,
                            (vid, app_status, now_iso, action_note, now_iso),
                        )
        except Exception as e:
            log_event("IMPORT_INVITATIONS_ERROR", {"error": str(e)}, level="WARNING")

    # 3. Parse HeadHunter Negotiations: REAL_HEADHUNTER_NEGOTIATIONS.json
    if neg_file.is_file():
        try:
            with open(neg_file, "r", encoding="utf-8") as f:
                neg_list = json.load(f)
            for it in neg_list:
                url = it.get("url", "")
                m = re.search(r"/vacancy/(\d+)", url)
                if not m:
                    continue
                vid = m.group(1)
                snippet = it.get("snippet", "")
                now_iso = datetime.datetime.now().isoformat()

                new_status = None
                if "собеседование" in snippet.lower():
                    new_status = "interview"
                elif "отказ" in snippet.lower():
                    new_status = "rejected"
                elif "просмотрен" in snippet.lower() and "не просмотрен" not in snippet.lower():
                    new_status = "viewed"

                if new_status:
                    cursor.execute("SELECT status FROM applications WHERE vacancy_id = ?", (vid,))
                    row = cursor.fetchone()
                    if row:
                        curr_status = row[0]
                        # Only upgrade or set status reasonably
                        if (curr_status == "applied" and new_status in ("viewed", "interview", "rejected")) or \
                           (curr_status == "viewed" and new_status in ("interview", "rejected")):
                            stats["status_progressed"] += 1
                            if not dry_run:
                                cursor.execute(
                                    "UPDATE applications SET status = ?, last_updated = ? WHERE vacancy_id = ?",
                                    (new_status, now_iso, vid),
                                )
        except Exception as e:
            log_event("IMPORT_NEGOTIATIONS_ERROR", {"error": str(e)}, level="WARNING")

    # 4. Ingest Rejected Vacancies: АНАЛИЗ_2500_ВАКАНСИЙ_ТАШКЕНТ.xlsx (Sheet: ❌ Отклоненные вакансии)
    if rej_excel.is_file():
        try:
            wb_rej = openpyxl.load_workbook(rej_excel, read_only=True)
            if "❌ Отклоненные вакансии" in wb_rej.sheetnames:
                ws_rej = wb_rej["❌ Отклоненные вакансии"]
                r_rows = list(ws_rej.iter_rows(values_only=True))
                # Header: ('№', 'Отклоненная должность', 'Компания', 'Причина отклонения (Красный маркер)', 'Зарплата', 'Краткое описание', 'Ссылка на HeadHunter')
                for r in r_rows[1:]:
                    url = str(r[6] or "").strip()
                    m = re.search(r"/vacancy/(\d+)", url)
                    if not m:
                        continue
                    vid = m.group(1)
                    title = str(r[1] or "Без названия").strip()
                    company = str(r[2] or "Не указано").strip()
                    reason = str(r[3] or "Исключено").strip()
                    salary_raw = str(r[4] or "").strip()
                    s_min, s_max = parse_salary_range(salary_raw)
                    sector = normalize_sector("", title)
                    now_iso = datetime.datetime.now().isoformat()

                    cursor.execute("SELECT id FROM vacancies WHERE id = ?", (vid,))
                    if not cursor.fetchone():
                        stats["vacancies_excluded_added"] += 1
                        if not dry_run:
                            cursor.execute(
                                """
                                INSERT INTO vacancies (id, title, company, url, source, tier, sector, salary_min, salary_max, salary_text, scraped_at, is_active)
                                VALUES (?, ?, ?, ?, 'hh.uz', 3, ?, ?, ?, ?, ?, 0)
                            """,
                                (vid, title, company, url, sector, s_min, s_max, f"{salary_raw} [Причина: {reason}]", now_iso),
                            )
            wb_rej.close()
        except Exception as e:
            log_event("IMPORT_REJECTED_ERROR", {"error": str(e)}, level="WARNING")

    if not dry_run:
        conn.commit()
    conn.close()

    log_event("MYWORK_HISTORY_IMPORTED", stats)
    return {"success": True, "stats": stats, "code": Config.EXIT_SUCCESS}


def main() -> int:
    parser = argparse.ArgumentParser(description="Import historical vacancies and applications from mywork into positions.db")
    parser.add_argument("--excel", type=str, default=None, help="Path to master Excel file")
    parser.add_argument("--rejected-excel", type=str, default=None, help="Path to rejected vacancies Excel")
    parser.add_argument("--invitations", type=str, default=None, help="Path to invitations json")
    parser.add_argument("--negotiations", type=str, default=None, help="Path to negotiations json")
    parser.add_argument("--db-path", type=str, default=None, help="Custom SQLite DB path")
    parser.add_argument("--dry-run", action="store_true", help="Perform simulation without database modification")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()
    res = import_history(
        excel_path=Path(args.excel) if args.excel else None,
        rejected_excel_path=Path(args.rejected_excel) if args.rejected_excel else None,
        invitations_path=Path(args.invitations) if args.invitations else None,
        negotiations_path=Path(args.negotiations) if args.negotiations else None,
        db_path=Path(args.db_path) if args.db_path else None,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        if res["success"]:
            st = res["stats"]
            print("==================================================================")
            print("  ИСТОРИЯ ИЗ MYWORK УСПЕШНО ИМПОРТИРОВАНА В POSITIONS.DB")
            print("==================================================================")
            print(f"  Новых подходящих/архивных вакансий: {st['vacancies_added']}")
            print(f"  Обновлено метаданных вакансий:      {st['vacancies_updated']}")
            print(f"  Добавлено исключённых вакансий:     {st['vacancies_excluded_added']}")
            print(f"  Новых записей откликов:            {st['applications_added']}")
            print(f"  Обновлено существующих откликов:   {st['applications_updated']}")
            print(f"  Продвинуто по воронке (собесед.):  {st['status_progressed']}")
            print("==================================================================")
        else:
            print(f"Ошибка импорта: {res.get('error')}")

    return res.get("code", Config.EXIT_SUCCESS)


if __name__ == "__main__":
    sys.exit(main())
