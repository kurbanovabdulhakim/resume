"""
Complete 1-Click Pipeline Setup for all 293 Financial Analyst Vacancies in Tashkent.

Generates unique, tailor-made, humanized cover letters for all 293 vacancies,
updates Hermes Copilot queue (data/hh_autonomy_queue.json),
updates Desktop Interactive Catalog (Интерактивный_Каталог_Вакансий.html),
updates Excel Workbook (Вакансии_Финансовый_Аналитик_293_HH.xlsx),
and syncs SQLite positions.db.
"""

from __future__ import annotations

import html
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.hh_ai import audit_cover_letter


def clean_company_name(name: str) -> str:
    c = html.unescape(name or "").strip()
    c = re.sub(r"\s+", " ", c)
    return c


def clean_title(title: str) -> str:
    t = html.unescape(title or "").strip()
    t = re.sub(r"\s+", " ", t)
    return t


def strip_ai_tells(text: str) -> str:
    t = text.replace(" — ", ", ").replace("—", "-").replace("--", "-")
    t = re.sub(r"\bне\s+только\b(.*?)\bно\s+и\b", r"\1 и", t, flags=re.IGNORECASE)
    t = re.sub(r"\bне\s+просто\b(.*?)\bа\b", r"\1,", t, flags=re.IGNORECASE)
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def build_unique_letter(v: dict, index: int) -> Tuple[str, str, str, str]:
    vid = str(v.get("id", ""))
    title = clean_title(v.get("title", "Финансовый аналитик"))
    company = clean_company_name(v.get("company", "компании"))
    desc = (v.get("description") or "").lower()
    title_lower = title.lower()
    comp_lower = company.lower()
    text_corpus = f"{title_lower} {comp_lower} {desc}"

    # Alternate natural greetings
    greetings = [
        f"Здравствуйте! Меня заинтересовала вакансия «{title}» в {company}.",
        f"Добрый день! Направляю отклик на вакансию «{title}» в компании {company}.",
        f"Здравствуйте! Откликаюсь на позицию «{title}» в компании {company}.",
        f"Добрый день! Заинтересовала позиция «{title}» в {company}.",
    ]
    greeting = greetings[index % len(greetings)]

    variant = "financial_analyst"
    domain = "financial_analysis"
    domain_name = "FP&A и Аналитика"

    # --- BESPOKE & SECTOR-SPECIFIC HANDLERS ---

    # 1. NESTLE
    if "нестле" in comp_lower or "nestle" in comp_lower:
        domain = "fmcg_sales_finance"
        domain_name = "FMCG и Продажи"
        p1 = (
            "Имею профильное образование Ташкентского финансового института по специальности «Экономика и финансы». "
            "В сфере коммерческих финансов и дистрибуции опираюсь на опыт контроля взаиморасчетов, мониторинга "
            "фактической маржинальности продаж и сверки отгрузок в учетных системах (1С, SmartUp). "
            "В Explorer Logistics на позиции CEO/COO настроил сквозной P&L, оптимизировав постоянные расходы на 18%."
        )
        p2 = (
            "Умею анализировать доходность каналов сбыта, оценивать эффективность скидок и маркетинговых инвестиций (ROI), "
            "а также контролировать соблюдение коммерческих политик партнерами. В строительном проекте Murad Buildings вел "
            "строгий материальный учет без недостач, а в АКБ «Равнак-банк» снизил операционные ошибки на 22%. "
            "Продвинутый пользователь Excel и Power BI. Буду рад обсудить задачи на собеседовании."
        )

    # 2. BELLISSIMO PIZZA
    elif "bellissimo" in comp_lower:
        domain = "horeca_fpa"
        domain_name = "HoReCa и FP&A"
        variant = "operations_manager"
        p1 = (
            "Окончил Ташкентский финансовый институт («Экономика и финансы»). Как руководитель в Explorer Logistics (CEO/COO), "
            "я выстроил систему управленческого учета P&L и Cash Flow с нуля, описал регламенты процессов и сократил накладные затраты на 18%. "
            "Понимаю специфику сетевого ритейла и общепита: расчет unit-экономики каждой пиццерии, контроль показателей Food Cost и Labor Cost."
        )
        p2 = (
            "Умею проводить факторный анализ план-факт отклонений, выявлять резервы оптимизации себестоимости и строить сценарные "
            "финансовые модели для открытия новых точек. Продвинуто владею Excel (сводные таблицы, Power Query) и Power BI для дашбордов руководства. "
            "Буду рад обсудить цели FP&A направления Bellissimo Pizza."
        )

    # 3. NEXTPORT LOGISTICS & Transport/Logistics companies
    elif "nextport" in comp_lower or "my freighter" in comp_lower or "dry port" in comp_lower or ("логист" in comp_lower and "финанс" in title_lower):
        domain = "logistics_finance"
        domain_name = "Логистика и Финансы"
        p1 = (
            "Имею высшее финансово-экономическое образование (ТФИ) и прямой опыт руководства логистической компанией. "
            "В Explorer Logistics на позициях CEO и операционного управляющего я отвечал за P&L бизнеса, рассчитывал себестоимость рейсов, "
            "контролировал расходы на собственный и привлеченный транспорт и оптимизировал постоянные затраты на 18%."
        )
        p2 = (
            "Внедрил сквозные регламенты взаимодействия, ускорив обработку заказов на 25%. Умею анализировать рентабельность направлений перевозок, "
            "управлять дебиторской задолженностью клиентов и контролировать Cash Flow. Свободно владею продвинутым Excel, 1С и Power BI. "
            "Буду рад применить опыт в вашей логистической компании."
        )

    # 4. CONSTRUCTION / REAL ESTATE (UET, Murad Buildings partners, etc.)
    elif any(k in comp_lower or k in desc for k in ["uet construction", "девелоп", "строитель", "смр", "недвижим", "генподряд"]):
        domain = "construction_finance"
        domain_name = "Строительство и Девелопмент"
        p1 = (
            "Имею диплом Ташкентского финансового института по направлению «Экономика и финансы» и практический опыт в девелопменте. "
            "В Murad Buildings отвечал за учет поступающих строительных материалов, контроль списания ТМЦ по фактическим нормам расхода "
            "и исключение недостач на объектах. Регулярно проводил инвентаризации остатков со сверкой данных в 1С."
        )
        p2 = (
            "В Explorer Logistics на позиции CEO/COO выстроил управленческую отчетность P&L и оптимизировал накладные расходы на 18%. "
            "Понимаю логику сметного планирования, разделения затрат по объектам строительства и контроля субподрядчиков. "
            "Уверенно работаю с 1С:Бухгалтерия, 1С:УТ и сложными таблицами Excel. Готов обсудить задачи на интервью."
        )

    # 5. BANKING & CREDIT RISK (TBC, Kapitalbank, Ipoteka, Anor, Octobank, Agrobank, etc.)
    elif any(k in comp_lower or k in title_lower for k in ["tbc", "капиталбанк", "anor", "ипотека", "ipoteka", "octobank", "агробанк", "банк", "bank", "кредитн", "credit risk"]):
        domain = "banking_risk"
        domain_name = "Банки и Риски"
        p1 = (
            "Окончил Ташкентский финансовый институт по направлению «Экономика и финансы». Опыт работы в банковском секторе "
            "получил в АКБ «Равнак-банк», где в качестве супервайзера стандартов контролировал операционную деятельность отделений, "
            "проводил проверки кассовой дисциплины и регламентов, снизив число операционных ошибок на 22%."
        )
        p2 = (
            "В Explorer Logistics (CEO/COO) настроил систему финансового учета P&L и Cash Flow, сократив накладные затраты на 18%. "
            "Понимаю нормативы Центрального банка Узбекистана, методику оценки финансовой устойчивости заемщиков и принципы управления ликвидностью. "
            "Свободно работаю с анализом больших массивов данных в Excel и Power BI. Буду рад пройти собеседование."
        )

    # 6. LOGISTICS / SUPPLY CHAIN / PROCUREMENT (Non-finance titles)
    elif any(k in title_lower for k in ["логист", "закуп", "снабжен", "вэд", "склад", "транспорт", "supply chain", "procurement"]):
        domain = "logistics_procurement"
        domain_name = "Логистика и Закупки"
        variant = "operations_manager"
        p1 = (
            "Имею практический опыт руководства операционной деятельностью в Explorer Logistics (CEO/COO), где управлял "
            "транспортными перевозками, регламентировал работу с контрагентами и рассчитывал себестоимость маршрутов. "
            "Оптимизировал затраты на наемный транспорт и постоянные расходы компании на 18%."
        )
        p2 = (
            "В девелопменте Murad Buildings координировал снабжение объектов стройматериалами, входной контроль и списание ТМЦ "
            "строго по нормам без недостач. Профильное образование: ТФИ («Экономика и финансы»). "
            "Понимаю экономику грузоперевозок, складской учет и управление поставками. Буду рад обсудить задачи на встрече."
        )

    # 7. ACCOUNTING / 1C / INVENTORY / COSTING
    elif any(k in title_lower for k in ["бухгалтер", "тмц", "материал", "первичк", "ревизор", "инвентаризац", "калькуляц", "себестоимост", "учетчик"]) or any(k in desc for k in ["списание материалов", "списание тмц", "инвентаризация", "первичных документов", "сверка с 1с"]):
        domain = "accounting_tmz"
        domain_name = "Бухучет и ТМЦ"
        p1 = (
            "Окончил Ташкентский финансовый институт по направлению «Экономика и финансы». В строительном проекте Murad Buildings "
            "вел сплошной материальный учет, входной контроль поступающих материалов и списание ТМЦ по утвержденным нормам "
            "без единой недостачи. Организовывал регулярные инвентаризации складов с оперативной сверкой данных в 1С."
        )
        p2 = (
            "В АКБ «Равнак-банк» как супервайзер контролировал кассовую дисциплину и снизил операционные ошибки на 22%. "
            "В Explorer Logistics наладил управленческий учет P&L и оптимизировал накладные расходы на 18%. "
            "Уверенно знаю план счетов, первичный учет, калькуляцию себестоимости, 1С и продвинутый Excel. Буду рад обсудить задачи на интервью."
        )

    # 8. MANAGEMENT / CFO / DIRECTORS / HEAD OF FP&A
    elif any(k in title_lower for k in ["директор", "руководитель", "cfo", "главный", "начальник", "управляющий", "head", "lead", "финансовый менеджер"]):
        domain = "management_cfo"
        domain_name = "Управление и CFO"
        variant = "operations_manager"
        p1 = (
            "Руководя компанией Explorer Logistics (CEO/COO), я отвечал за финансовую устойчивость бизнеса, рентабельность сделок "
            "и операционную дисциплину. С нуля внедрил систему управленческой отчетности (P&L, Cash Flow, Баланс), разработал регламенты SOP "
            "и сократил постоянные расходы (OpEx) на 18%."
        )
        p2 = (
            "Опираюсь на сильную экономическую базу Ташкентского финансового института и опыт руководства командами. "
            "В АКБ «Равнак-банк» контролировал стандарты операционной деятельности (-22% ошибок). Свободно владею финансовым "
            "моделированием в Excel и визуализацией данных в Power BI. Буду рад обсудить стратегические задачи компании на встрече."
        )

    # 9. GENERAL FINANCIAL ANALYSIS / FP&A / MODELING (Default)
    else:
        domain = "financial_analysis"
        domain_name = "FP&A и Аналитика"
        if "модел" in desc or "инвест" in desc or "dcf" in desc or "рынк" in desc:
            p1 = (
                "Имею высшее финансово-экономическое образование (ТФИ) и практический опыт управления финансами. "
                "В Explorer Logistics на позиции CEO/COO настроил регулярную управленческую отчетность P&L и Cash Flow, "
                "рассчитал маржинальность и юнит-экономику направлений, сократив накладные расходы компании на 18%."
            )
            p2 = (
                "Уверенно разрабатываю финансовые модели в Excel (сценарные прогнозы, точка безубыточности, оценка доходности проектов). "
                "В Murad Buildings вел сплошной материальный учет без недостач, а в АКБ «Равнак-банк» проводил аудит стандартов (-22% ошибок). "
                "Свободно работаю с Power BI, сводными таблицами и 1С. Готов обсудить аналитические задачи на собеседовании."
            )
        else:
            p1 = (
                "Окончил Ташкентский финансовый институт по направлению «Экономика и финансы». В Explorer Logistics (CEO/COO) "
                "внедрил систему регулярного управленческого учета: P&L, Cash Flow и ежемесячный план-факт анализ бюджетов. "
                "Системный контроль статей затрат позволил устранить кассовые разрывы и снизить операционные издержки на 18%."
            )
            p2 = (
                "В Murad Buildings обеспечивал строгий складской учет материалов без недостач со сверкой в 1С, а в АКБ «Равнак-банк» "
                "контролировал стандарты обслуживания (-22% операционных ошибок). Продвинутый пользователь Excel "
                "(сложные формулы, Power Query, сводные таблицы) и Power BI. Буду рад пройти собеседование."
            )

    closing = (
        "С уважением,\n"
        "Абдулхаким Курбанов\n"
        "Тел: +998 90 855-07-90 | Telegram: @SAWAS0078"
    )

    letter = f"{greeting}\n\n{p1}\n\n{p2}\n\n{closing}"
    cleaned = strip_ai_tells(letter)
    return cleaned, domain, domain_name, variant


def main():
    target_dir = Path(r"C:\Users\Abdulkhakim\Desktop\Вакансии_Финансовый_Аналитик_Ташкент")
    v_path = target_dir / "vacancies_full.json"
    vacancies = json.loads(v_path.read_text(encoding="utf-8"))
    print(f"[STEP 1] Loaded {len(vacancies)} vacancies from {v_path}")

    # Generate letters and audit
    processed_items = []
    passed = 0
    failed = 0

    for idx, v in enumerate(vacancies):
        letter, domain, domain_name, variant = build_unique_letter(v, idx)
        title = clean_title(v.get("title", ""))
        company = clean_company_name(v.get("company", ""))
        audit = audit_cover_letter(letter, company=company, position=title)

        if not audit["ok"]:
            print(f"[AUDIT FAIL] {company} - {title}: {audit['issues']}")
            failed += 1
        else:
            passed += 1

        v["cover_letter"] = letter
        v["domain"] = domain
        v["domain_name"] = domain_name
        v["cv_variant"] = variant
        processed_items.append(v)

    print(f"[STEP 2] Audited {len(vacancies)} letters: {passed} passed, {failed} failed")
    assert failed == 0, f"{failed} letters failed humanizer audit!"

    # Sort: Tier 1 first, then by salary / id
    processed_items.sort(key=lambda x: (0 if x.get("tier") == 1 else 1, x.get("id")))

    # Assign priority rank (1..293)
    for rank, item in enumerate(processed_items, start=1):
        item["priority_rank"] = rank

    # 1. Update data/hh_autonomy_queue.json
    queue_file = Config.HH_QUEUE_FILE
    queue_data = {"updated_at": "2026-11-15T20:10:00", "total_items": len(processed_items), "items": {}}

    for item in processed_items:
        vid = str(item["id"])
        queue_data["items"][vid] = {
            "vacancy_id": vid,
            "title": item["title"],
            "company": item["company"],
            "url": item.get("url") or f"https://tashkent.hh.uz/vacancy/{vid}",
            "priority_url": "https://tashkent.hh.uz/vacancies/finansovyy_analitik",
            "priority_rank": item["priority_rank"],
            "tier": item.get("tier", 2),
            "tier_name": item.get("tier_name", ""),
            "salary": item.get("salary", "Не указана"),
            "status": "queued",
            "cv_variant": item.get("cv_variant", "financial_analyst"),
            "cover_letter": item["cover_letter"],
            "detail": f"Domain: {item.get('domain_name', 'Finance')}"
        }

    queue_file.parent.mkdir(parents=True, exist_ok=True)
    queue_file.write_text(json.dumps(queue_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[STEP 3] Saved {len(processed_items)} queued vacancies to {queue_file}")

    # 2. Update Desktop vacancies_full.json
    v_path.write_text(json.dumps(processed_items, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[STEP 4] Updated {v_path}")

    # 3. Update Excel Workbook with 'Сопроводительное письмо'
    excel_file = target_dir / "Вакансии_Финансовый_Аналитик_293_HH.xlsx"
    wb = openpyxl.Workbook()

    font_title = Font(name="Calibri", size=14, bold=True, color="1F497D")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True)
    font_regular = Font(name="Calibri", size=10)
    fill_header = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    fill_tier1 = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    border_thin = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    # Sheet 1: Все_293_Вакансии
    ws_all = wb.active
    ws_all.title = "Все_293_Вакансии"
    ws_all["A1"] = f"БАЗА ВАКАНСИЙ С СОПРОВОДИТЕЛЬНЫМИ ПИСЬМАМИ ДЛЯ 1-КЛИК ОТКЛИКА (293 ВАКАНСИИ, HH.UZ)"
    ws_all["A1"].font = font_title

    headers = [
        "№", "ID", "Название вакансии", "Компания", "Тематика отклика", "Уровень (Tier)", 
        "Зарплата", "Опыт", "Ключевые навыки", "Ссылка на HH", "Уникальное Сопроводительное Письмо (1-клик)"
    ]

    for c_idx, h in enumerate(headers, start=1):
        cell = ws_all.cell(row=3, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for r_idx, v in enumerate(processed_items, start=4):
        c1 = ws_all.cell(row=r_idx, column=1, value=r_idx - 3)
        c2 = ws_all.cell(row=r_idx, column=2, value=v["id"])
        c3 = ws_all.cell(row=r_idx, column=3, value=v["title"])
        c4 = ws_all.cell(row=r_idx, column=4, value=v["company"])
        c5 = ws_all.cell(row=r_idx, column=5, value=v.get("domain_name", "FP&A"))
        c6 = ws_all.cell(row=r_idx, column=6, value=v["tier_name"])
        c7 = ws_all.cell(row=r_idx, column=7, value=v["salary"])
        c8 = ws_all.cell(row=r_idx, column=8, value=v["experience"])
        c9 = ws_all.cell(row=r_idx, column=9, value=v["skills"])
        c10 = ws_all.cell(row=r_idx, column=10, value=v["url"])
        c11 = ws_all.cell(row=r_idx, column=11, value=v["cover_letter"])

        for cell in [c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11]:
            cell.font = font_regular
            cell.border = border_thin
            cell.alignment = Alignment(vertical="top")

        c1.alignment = Alignment(horizontal="center", vertical="top")
        c2.alignment = Alignment(horizontal="center", vertical="top")
        c5.alignment = Alignment(horizontal="center", vertical="top")
        c6.alignment = Alignment(horizontal="center", vertical="top")
        c8.alignment = Alignment(horizontal="center", vertical="top")
        c11.alignment = Alignment(vertical="top", wrap_text=True)

        if v["tier"] == 1:
            c4.font = font_bold
            c6.font = font_bold
            c6.fill = fill_tier1

    ws_all.column_dimensions["A"].width = 6
    ws_all.column_dimensions["B"].width = 14
    ws_all.column_dimensions["C"].width = 36
    ws_all.column_dimensions["D"].width = 30
    ws_all.column_dimensions["E"].width = 24
    ws_all.column_dimensions["F"].width = 18
    ws_all.column_dimensions["G"].width = 26
    ws_all.column_dimensions["H"].width = 14
    ws_all.column_dimensions["I"].width = 28
    ws_all.column_dimensions["J"].width = 35
    ws_all.column_dimensions["K"].width = 85

    ws_all.auto_filter.ref = f"A3:K{len(processed_items)+3}"

    # Sheet 2: Tier 1 Топ Компании
    ws_t1 = wb.create_sheet("Tier_1_Топ_Компании_67")
    ws_t1["A1"] = "ТОП-67 РАБОТОДАТЕЛЕЙ (БАНКИ, ТЕЛЕКОМ, ФИНТЕХ, МЕЖДУНАРОДНЫЕ ХОЛДИНГИ)"
    ws_t1["A1"].font = font_title

    for c_idx, h in enumerate(headers, start=1):
        cell = ws_t1.cell(row=3, column=c_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    t1_items = [v for v in processed_items if v.get("tier") == 1]
    for r_idx, v in enumerate(t1_items, start=4):
        c1 = ws_t1.cell(row=r_idx, column=1, value=r_idx - 3)
        c2 = ws_t1.cell(row=r_idx, column=2, value=v["id"])
        c3 = ws_t1.cell(row=r_idx, column=3, value=v["title"])
        c4 = ws_t1.cell(row=r_idx, column=4, value=v["company"])
        c5 = ws_t1.cell(row=r_idx, column=5, value=v.get("domain_name", "FP&A"))
        c6 = ws_t1.cell(row=r_idx, column=6, value=v["tier_name"])
        c7 = ws_t1.cell(row=r_idx, column=7, value=v["salary"])
        c8 = ws_t1.cell(row=r_idx, column=8, value=v["experience"])
        c9 = ws_t1.cell(row=r_idx, column=9, value=v["skills"])
        c10 = ws_t1.cell(row=r_idx, column=10, value=v["url"])
        c11 = ws_t1.cell(row=r_idx, column=11, value=v["cover_letter"])

        for cell in [c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11]:
            cell.font = font_regular
            cell.border = border_thin
            cell.alignment = Alignment(vertical="top")

        c1.alignment = Alignment(horizontal="center", vertical="top")
        c2.alignment = Alignment(horizontal="center", vertical="top")
        c4.font = font_bold
        c5.alignment = Alignment(horizontal="center", vertical="top")
        c6.alignment = Alignment(horizontal="center", vertical="top")
        c6.fill = fill_tier1
        c8.alignment = Alignment(horizontal="center", vertical="top")
        c11.alignment = Alignment(vertical="top", wrap_text=True)

    ws_t1.column_dimensions["A"].width = 6
    ws_t1.column_dimensions["B"].width = 14
    ws_t1.column_dimensions["C"].width = 36
    ws_t1.column_dimensions["D"].width = 30
    ws_t1.column_dimensions["E"].width = 24
    ws_t1.column_dimensions["F"].width = 18
    ws_t1.column_dimensions["G"].width = 26
    ws_t1.column_dimensions["H"].width = 14
    ws_t1.column_dimensions["I"].width = 28
    ws_t1.column_dimensions["J"].width = 35
    ws_t1.column_dimensions["K"].width = 85
    ws_t1.auto_filter.ref = f"A3:K{len(t1_items)+3}"

    wb.save(excel_file)
    print(f"[STEP 5] Saved updated Excel to {excel_file}")

    # 4. Re-generate Desktop Interactive HTML Catalog
    html_file = target_dir / "Интерактивный_Каталог_Вакансий.html"
    generate_interactive_html(html_file, processed_items)
    print(f"[STEP 6] Generated Interactive HTML Catalog with 1-click apply: {html_file}")


def generate_interactive_html(html_file: Path, items: List[dict]):
    items_json = json.dumps(items, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>1-Click Пульт Откликов: 293 Вакансии (Ташкент, HH.uz)</title>
    <style>
        :root {{
            --bg: #0b0f19;
            --card-bg: #151c2e;
            --border: #232d46;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --accent-green: #22c55e;
            --accent-green-hover: #16a34a;
            --accent-gold: #fbbf24;
            --accent-purple: #a855f7;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
        body {{ background-color: var(--bg); color: var(--text-main); padding: 24px; line-height: 1.5; }}
        
        .header {{ 
            margin-bottom: 24px; 
            padding-bottom: 16px; 
            border-bottom: 1px solid var(--border); 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            flex-wrap: wrap; 
            gap: 16px; 
        }}
        .header h1 {{ font-size: 24px; font-weight: 700; color: #fff; }}
        .header-badges {{ display: flex; gap: 10px; }}
        .stats-badge {{ background: #1e293b; border: 1px solid #334155; color: var(--accent); padding: 6px 14px; border-radius: 9999px; font-size: 13px; font-weight: 600; }}
        .applied-badge {{ background: rgba(34, 197, 94, 0.15); border: 1px solid rgba(34, 197, 94, 0.3); color: var(--accent-green); padding: 6px 14px; border-radius: 9999px; font-size: 13px; font-weight: 600; }}
        
        .controls {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; align-items: center; }}
        .search-box {{ flex: 1; min-width: 280px; padding: 10px 16px; border-radius: 8px; border: 1px solid var(--border); background: var(--card-bg); color: #fff; font-size: 14px; outline: none; }}
        .search-box:focus {{ border-color: var(--accent); }}
        .filter-btn {{ padding: 8px 14px; border-radius: 8px; border: 1px solid var(--border); background: var(--card-bg); color: var(--text-muted); cursor: pointer; font-size: 13px; font-weight: 600; transition: all 0.2s; }}
        .filter-btn:hover, .filter-btn.active {{ background: var(--accent); color: #0b0f19; border-color: var(--accent); }}

        .table-container {{ background: var(--card-bg); border-radius: 12px; border: 1px solid var(--border); overflow-x: auto; box-shadow: 0 10px 30px rgba(0,0,0,0.4); }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }}
        th {{ background: #0e1526; padding: 14px 16px; font-weight: 600; color: var(--text-muted); border-bottom: 1px solid var(--border); position: sticky; top: 0; white-space: nowrap; }}
        td {{ padding: 14px 16px; border-bottom: 1px solid var(--border); vertical-align: top; }}
        tr:hover td {{ background: rgba(255, 255, 255, 0.02); }}
        tr.row-applied td {{ background: rgba(34, 197, 94, 0.04); }}

        .title-link {{ color: #fff; text-decoration: none; font-weight: 700; font-size: 14px; display: block; }}
        .title-link:hover {{ color: var(--accent); text-decoration: underline; }}
        .company-name {{ font-weight: 600; color: var(--accent); margin-top: 3px; font-size: 13.5px; }}
        .salary-badge {{ color: var(--accent-gold); font-weight: 700; margin-top: 4px; font-size: 13px; }}
        .domain-tag {{ display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; text-transform: uppercase; }}
        .domain-fpa {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }}
        .domain-cfo {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }}
        .domain-tmz {{ background: rgba(234, 179, 8, 0.15); color: #facc15; border: 1px solid rgba(234, 179, 8, 0.3); }}
        .domain-log {{ background: rgba(52, 211, 153, 0.15); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3); }}
        .domain-bank {{ background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.3); }}

        .tier-badge {{ font-size: 11px; padding: 2px 7px; border-radius: 4px; background: rgba(52, 211, 153, 0.15); color: var(--accent-green); font-weight: 700; margin-left: 6px; }}
        
        .action-group {{ display: flex; flex-direction: column; gap: 6px; width: 220px; }}
        .btn-apply-1click {{ 
            background: var(--accent-green); 
            color: #0b0f19; 
            border: none; 
            padding: 9px 14px; 
            border-radius: 7px; 
            cursor: pointer; 
            font-size: 13px; 
            font-weight: 700; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            gap: 6px; 
            transition: all 0.15s; 
            white-space: nowrap;
        }}
        .btn-apply-1click:hover {{ background: var(--accent-green-hover); transform: translateY(-1px); }}
        .btn-secondary-group {{ display: flex; gap: 6px; }}
        .btn-sub {{ 
            flex: 1; 
            background: #1e293b; 
            color: #cbd5e1; 
            border: 1px solid #334155; 
            padding: 6px 10px; 
            border-radius: 6px; 
            cursor: pointer; 
            font-size: 11.5px; 
            font-weight: 600; 
            text-align: center; 
            transition: all 0.2s; 
        }}
        .btn-sub:hover {{ background: #334155; color: #fff; }}

        /* Modal */
        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.75); z-index: 1000; justify-content: center; align-items: center; padding: 20px; backdrop-filter: blur(4px); }}
        .modal-content {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; max-width: 780px; width: 100%; max-height: 85vh; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 40px rgba(0,0,0,0.6); }}
        .modal-header {{ padding: 18px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: flex-start; }}
        .modal-title {{ font-size: 17px; font-weight: 700; color: #fff; }}
        .modal-close {{ background: none; border: none; color: var(--text-muted); font-size: 24px; cursor: pointer; line-height: 1; }}
        .modal-body {{ padding: 20px 24px; overflow-y: auto; color: #cbd5e1; font-size: 13.5px; }}
        .modal-textarea {{ width: 100%; height: 260px; background: #0b0f19; border: 1px solid #334155; border-radius: 8px; color: #f1f5f9; padding: 14px; font-size: 13.5px; line-height: 1.6; outline: none; font-family: inherit; resize: vertical; }}
        .modal-textarea:focus {{ border-color: var(--accent); }}
        .modal-footer {{ padding: 14px 24px; border-top: 1px solid var(--border); display: flex; justify-content: flex-end; gap: 10px; }}

        /* Toast notification */
        .toast {{ 
            position: fixed; 
            bottom: 24px; 
            right: 24px; 
            background: #047857; 
            color: #fff; 
            padding: 14px 22px; 
            border-radius: 10px; 
            font-weight: 600; 
            font-size: 14px; 
            box-shadow: 0 10px 25px rgba(0,0,0,0.6); 
            display: none; 
            z-index: 2000; 
        }}
    </style>
</head>
<body>

    <div class="header">
        <div>
            <h1>Интерактивный пульт откликов: 293 вакансии (Ташкент, HH.uz)</h1>
            <p style="color: var(--text-muted); font-size: 14px; margin-top: 4px;">1 клик копирует уникальное адаптированное письмо в буфер обмена и мгновенно открывает вакансию на HH.uz</p>
        </div>
        <div class="header-badges">
            <div class="stats-badge" id="statsBadge">Загрузка...</div>
            <div class="applied-badge" id="appliedBadge">Отправлено: 0</div>
        </div>
    </div>

    <div class="controls">
        <input type="text" id="searchBox" class="search-box" placeholder="Поиск по названию, компании (Nestle, Nextport, TBC...), навыкам (Excel, 1C, Power BI)...">
        <button class="filter-btn active" data-filter="all">Все (293)</button>
        <button class="filter-btn" data-filter="tier1">★ Tier 1 Топ (67)</button>
        <button class="filter-btn" data-filter="domain_fpa">FP&A и Анализ</button>
        <button class="filter-btn" data-filter="domain_tmz">Бухучет и ТМЦ</button>
        <button class="filter-btn" data-filter="domain_cfo">Управление и CFO</button>
        <button class="filter-btn" data-filter="domain_log">Логистика и Закупки</button>
        <button class="filter-btn" data-filter="domain_bank">Банки и Риски</button>
        <button class="filter-btn" data-filter="salary">С открытой зарплатой</button>
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th style="width: 40px; text-align: center;">№</th>
                    <th>Вакансия и Компания</th>
                    <th>Тематика отклика</th>
                    <th>Зарплата</th>
                    <th>Опыт</th>
                    <th>Ключевые навыки</th>
                    <th style="text-align: center; width: 230px;">1-Клик Действие</th>
                </tr>
            </thead>
            <tbody id="tableBody"></tbody>
        </table>
    </div>

    <!-- Modal for viewing / editing letter -->
    <div class="modal" id="modal">
        <div class="modal-content">
            <div class="modal-header">
                <div>
                    <div class="modal-title" id="mTitle">Сопроводительное письмо</div>
                    <div style="color: var(--text-muted); font-size: 13px; margin-top: 3px;" id="mSub"></div>
                </div>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <textarea class="modal-textarea" id="mTextarea"></textarea>
            </div>
            <div class="modal-footer">
                <button class="btn-sub" onclick="copyModalLetter()" style="padding: 10px 18px; font-size: 13px;">📋 Скопировать текст</button>
                <button class="btn-apply-1click" onclick="applyModalLetter()" style="padding: 10px 18px; font-size: 13px;">⚡ Открыть HH.uz и применить</button>
            </div>
        </div>
    </div>

    <div class="toast" id="toast">✅ Письмо скопировано в буфер! Открываю вакансию на HH.uz...</div>

    <script>
        const vacancies = {items_json};
        let currentFilter = 'all';
        let searchQuery = '';
        let activeModalVid = null;
        const appliedSet = new Set(JSON.parse(localStorage.getItem('hh_applied_vids') || '[]'));

        function getDomainBadge(domain, domainName) {{
            let cls = 'domain-fpa';
            if (domain === 'accounting_tmz') cls = 'domain-tmz';
            else if (domain === 'management_cfo') cls = 'domain-cfo';
            else if (domain === 'logistics_procurement' || domain === 'logistics_finance') cls = 'domain-log';
            else if (domain === 'banking_risk') cls = 'domain-bank';
            return `<span class="domain-tag ${{cls}}">${{domainName || 'Финансы'}}</span>`;
        }}

        function showToast(msg) {{
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.display = 'block';
            setTimeout(() => {{ t.style.display = 'none'; }}, 3200);
        }}

        function renderTable() {{
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';

            const filtered = vacancies.filter(v => {{
                // Search query
                const q = searchQuery.toLowerCase().trim();
                const matchSearch = !q || 
                    v.title.toLowerCase().includes(q) || 
                    v.company.toLowerCase().includes(q) || 
                    (v.skills || '').toLowerCase().includes(q) || 
                    (v.domain_name || '').toLowerCase().includes(q);

                if (!matchSearch) return false;

                // Category filter
                if (currentFilter === 'tier1') return v.tier === 1;
                if (currentFilter === 'salary') return v.salary && v.salary !== 'Не указана';
                if (currentFilter === 'domain_fpa') return v.domain === 'financial_analysis' || v.domain === 'fmcg_sales_finance' || v.domain === 'horeca_fpa';
                if (currentFilter === 'domain_tmz') return v.domain === 'accounting_tmz' || v.domain === 'construction_finance';
                if (currentFilter === 'domain_cfo') return v.domain === 'management_cfo';
                if (currentFilter === 'domain_log') return v.domain === 'logistics_procurement' || v.domain === 'logistics_finance';
                if (currentFilter === 'domain_bank') return v.domain === 'banking_risk';

                return true;
            }});

            document.getElementById('statsBadge').innerText = `Показано: ${{filtered.length}} из ${{vacancies.length}}`;
            document.getElementById('appliedBadge').innerText = `Отправлено: ${{appliedSet.size}}`;

            filtered.forEach((v, idx) => {{
                const tr = document.createElement('tr');
                const isApplied = appliedSet.has(v.id);
                if (isApplied) tr.classList.add('row-applied');

                const tierHtml = v.tier === 1 ? '<span class="tier-badge">★ Tier 1</span>' : '';
                const salaryHtml = v.salary && v.salary !== 'Не указана' ? `<div class="salary-badge">${{v.salary}}</div>` : '<div style="color: var(--text-muted); font-size: 12px; margin-top: 4px;">Зарплата не указана</div>';

                tr.innerHTML = `
                    <td style="text-align: center; color: var(--text-muted); font-weight: 600;">${{idx + 1}}</td>
                    <td>
                        <a href="${{v.url}}" target="_blank" class="title-link">${{v.title}}</a>
                        <div class="company-name">${{v.company}}${{tierHtml}}</div>
                        ${{salaryHtml}}
                    </td>
                    <td>${{getDomainBadge(v.domain, v.domain_name)}}</td>
                    <td style="white-space: nowrap;">${{v.salary}}</td>
                    <td style="white-space: nowrap; color: var(--text-muted);">${{v.experience}}</td>
                    <td style="max-width: 200px; color: #cbd5e1; font-size: 12px;">${{v.skills || 'Не указаны'}}</td>
                    <td>
                        <div class="action-group">
                            <button class="btn-apply-1click" onclick="apply1Click('${{v.id}}', '${{v.url}}')">
                                ${{isApplied ? '✅ Отправлено (Повторить)' : '⚡ Отклик в 1 клик'}}
                            </button>
                            <div class="btn-secondary-group">
                                <button class="btn-sub" onclick="openLetterModal('${{v.id}}')">✉️ Письмо</button>
                                <button class="btn-sub" onclick="copyLetterOnly('${{v.id}}')">📋 Копия</button>
                            </div>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            }});
        }}

        async function apply1Click(vid, url) {{
            const item = vacancies.find(x => x.id === vid);
            if (!item) return;

            // 1. Copy letter to clipboard
            try {{
                await navigator.clipboard.writeText(item.cover_letter);
                showToast('✅ Письмо скопировано в буфер! Открываю HeadHunter...');
            }} catch (e) {{
                const ta = document.createElement('textarea');
                ta.value = item.cover_letter;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                showToast('✅ Письмо скопировано в буфер! Открываю HeadHunter...');
            }}

            // 2. Mark applied
            appliedSet.add(vid);
            localStorage.setItem('hh_applied_vids', JSON.stringify(Array.from(appliedSet)));

            // 3. Open HH in new tab
            window.open(url, '_blank');

            // 4. Notify backend copilot if running
            try {{
                fetch('http://127.0.0.1:8080/api/apply', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ vacancy_id: vid, cover_letter: item.cover_letter, cv_variant: item.cv_variant }})
                }}).catch(() => {{}});
            }} catch (err) {{}}

            renderTable();
        }}

        async function copyLetterOnly(vid) {{
            const item = vacancies.find(x => x.id === vid);
            if (!item) return;
            try {{
                await navigator.clipboard.writeText(item.cover_letter);
                showToast('📋 Письмо скопировано в буфер обмена!');
            }} catch (e) {{}}
        }}

        function openLetterModal(vid) {{
            const item = vacancies.find(x => x.id === vid);
            if (!item) return;
            activeModalVid = vid;
            document.getElementById('mTitle').innerText = `${{item.title}} — ${{item.company}}`;
            document.getElementById('mSub').innerText = `Тематика: ${{item.domain_name}} | Tier: ${{item.tier_name}}`;
            document.getElementById('mTextarea').value = item.cover_letter;
            document.getElementById('modal').style.display = 'flex';
        }}

        function closeModal() {{
            document.getElementById('modal').style.display = 'none';
        }}

        async function copyModalLetter() {{
            const text = document.getElementById('mTextarea').value;
            await navigator.clipboard.writeText(text);
            showToast('📋 Письмо скопировано!');
        }}

        async function applyModalLetter() {{
            const item = vacancies.find(x => x.id === activeModalVid);
            if (!item) return;
            const text = document.getElementById('mTextarea').value;
            item.cover_letter = text;
            await navigator.clipboard.writeText(text);
            appliedSet.add(activeModalVid);
            localStorage.setItem('hh_applied_vids', JSON.stringify(Array.from(appliedSet)));
            window.open(item.url, '_blank');
            closeModal();
            renderTable();
            showToast('✅ Письмо скопировано! Открываю HH...');
        }}

        // Event listeners
        document.getElementById('searchBox').addEventListener('input', (e) => {{
            searchQuery = e.target.value;
            renderTable();
        }});

        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentFilter = btn.dataset.filter;
                renderTable();
            }});
        }});

        window.onclick = function(event) {{
            const modal = document.getElementById('modal');
            if (event.target === modal) closeModal();
        }};

        renderTable();
    </script>
</body>
</html>
"""
    html_file.write_text(html_content, encoding="utf-8")


if __name__ == "__main__":
    main()
