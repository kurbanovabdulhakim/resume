"""
Hermes + Ollama AI Scoring, Factual Grounding, and Humanized Cover Letter Engine.

Evaluates HeadHunter vacancies against master/resume.md, picks the matching CV variant,
composes individualized Russian cover letters via local Ollama/Hermes, and validates every
letter against document-humanizer rules before submission.

Usage:
    python scripts/hh_ai.py --vacancy-id 139244548 --backend ollama --json
    python scripts/hh_ai.py --title "Финансовый аналитик" --company "AVO.UZ" --backend none --json
"""

from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.generate_docs import resolve_templates
from scripts.init_db import get_connection, init_database
from scripts.logger import log_event

EXCLUDED_ROLE_PATTERNS = [
    r"\bscrum\b",
    r"agile\s*coach",
    r"маркетинг",
    r"marketing",
    r"\bsmm\b",
    r"таргетолог",
    r"дизайнер",
    r"копирайтер",
    r"водител",
    r"курьер",
    r"грузчик",
    r"охранник",
    r"уборщи",
    r"кассир",
    r"продавец",
    r"колл[\-\s]?центр",
    r"call[\-\s]?center",
    r"1с\s*програм",
    r"frontend",
    r"backend",
    r"ios\b",
    r"android\b",
    r"flutter",
    r"devops",
    r"тестиров",
    r"\bqa\b",
    r"менеджер\s+магазина",
    r"директор\s+магазина",
    r"товаровед",
    r"фармацевт",
    r"повар",
    r"официант",
    r"учител",
    r"преподавател",
    r"юрист",
    r"рекрутер",
    r"\bhr\b",
]

FINANCE_PATTERNS = [
    r"финанс",
    r"\bfinance\b",
    r"financial",
    r"fp&a",
    r"treasury",
    r"казнач",
    r"бюджет",
    r"экономист",
    r"p&l",
    r"аудит",
    r"залогов",
    r"риск",
    r"инвест",
]

ANALYTICS_PATTERNS = [
    r"бизнес[\-\s]?аналит",
    r"business\s*analyst",
    r"аналитик",
    r"analyst",
    r"системн\w+\s+аналит",
    r"\bbi\b",
    r"power\s*bi",
    r"sql",
    r"управлен\w+\s+данн",
    r"product\s*manager",
    r"проектами",
    r"project\s*manager",
]

OPERATIONS_PATTERNS = [
    r"операцион",
    r"operations",
    r"\bcoo\b",
    r"исполнительн\w+\s+директор",
    r"снабжен",
    r"закуп",
    r"логист",
    r"склад",
    r"супервайзер",
    r"руководитель\s+проекта",
    r"руководитель\s+направлен",
    r"руководитель\s+центра",
]

BANNED_AI_PHRASES = [
    "не просто",
    "а целая",
    "бесспорно",
    "достичь новых высот",
    "к процветанию",
    "синергия",
    "синергии",
    "бесценный вклад",
    "внести свой вклад",
    "искренне рад приветствовать",
    "идеальным кандидатом",
    "отличным кандидатом",
    "большим интересом проанализировал",
    "мое опыт",
    "что избежало",
    "погрузиться",
    "в современном мире",
    "рады пригласить",
    "уверен, что мои навыки, опыт и способность к быстрой адаптации",
    "tapestry",
    "nestled",
]

THIRD_PERSON_PATTERNS = [
    r"пришел\s+абдулхаким",
    r"\bего\s+опыт\b",
    r"\bего\s+сильные\b",
    r"порадовать\s+его",
    r"данный\s+кандидат",
]

KNOWN_FACT_HALLUCINATIONS = [
    (
        re.compile(r"финансов\w*\s+аналитик\w*[^.!?\n]{0,35}(?:ravnaq|равнак)", re.IGNORECASE),
        "Inaccurate role at Ravnaq Bank (candidate worked as Service Supervisor / Controller, not Financial Analyst)",
    ),
    (
        re.compile(r"(?:ravnaq|равнак)[^.!?\n]{0,35}финансов\w*\s+аналитик", re.IGNORECASE),
        "Inaccurate role at Ravnaq Bank (candidate worked as Service Supervisor / Controller, not Financial Analyst)",
    ),
    (
        re.compile(r"explorer\s+logistics[^.!?\n]{0,45}(?:магазин|шпд|интернет|телеком)", re.IGNORECASE),
        "Inaccurate sphere for Explorer Logistics (logistics company, not retail or telecom)",
    ),
    (
        re.compile(r"(?:богранн|финасов\w|порадовать\s+его)", re.IGNORECASE),
        "Broken Russian word or unnatural phrasing detected",
    ),
]


def load_candidate_profile(master_path: Path | None = None) -> Dict[str, Any]:
    """Loads candidate profile facts cleanly from master/resume.md."""
    path = Path(master_path) if master_path else (Config.MASTER_DIR / "resume.md")
    raw_text = path.read_text(encoding="utf-8") if path.is_file() else ""
    facts_block = (
        f"ФИО: {Config.CANDIDATE_NAME}\n"
        f"Локация: Ташкент, Узбекистан\n"
        f"Контакты: {Config.CANDIDATE_PHONE}, {Config.CANDIDATE_EMAIL}, {Config.CANDIDATE_TELEGRAM}\n"
        "Образование: Ташкентский финансовый институт (ТФИ), Экономика и Финансы.\n"
        "Подтвержденный опыт (строго без искажения должностей):\n"
        "1. EXPLORER LOGISTICS (03.2025-07.2026) - Исполнительный директор (CEO) / Операционный управляющий: "
        "построил управленческую отчетность P&L, снизил накладные расходы на 18%, регламентировал процессы и ускорил обработку заказов на 25%.\n"
        "2. MURAD BUILDINGS (11.2022-01.2024) - Ассистент руководителя проекта / Помощник прораба: "
        "координировал подрядчиков, организовал строгий складской и материальный учет без недостач.\n"
        "3. АКБ «Равнак-банк» / Ravnaq Bank (12.2021-09.2022) - Супервайзер / Контролер стандартов обслуживания: "
        "контролировал операционные стандарты и качество сервиса, обновил чек-листы и снизил операционные ошибки на 22%.\n"
        "Инструменты: Excel (финансовые модели, Power Query, сводные), SQL (PostgreSQL), Power BI, Python, Bitrix24, amoCRM.\n"
        "Языки: Русский (свободно), Узбекский (родной), Английский (деловой)."
    )
    return {
        "name": Config.CANDIDATE_NAME,
        "phone": Config.CANDIDATE_PHONE,
        "email": Config.CANDIDATE_EMAIL,
        "telegram": Config.CANDIDATE_TELEGRAM,
        "raw_text": raw_text,
        "facts_block": facts_block,
    }


def _extract_json_object(raw: str) -> Optional[Dict[str, Any]]:
    cleaned = raw.strip()
    if "```" in cleaned:
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _call_ollama_chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.45,
    timeout: int = 45,
    num_predict: int = 520,
) -> str:
    target_model = model or Config.OLLAMA_MODEL
    url = f"{Config.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    payload = json.dumps(
        {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": Config.OLLAMA_NUM_CTX,
                "num_predict": num_predict,
                "temperature": temperature,
            },
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return str(data.get("message", {}).get("content", "")).strip()


def _call_hermes_chat(prompt: str, timeout: int = 90) -> str:
    hermes_exe = Path.home() / "AppData" / "Local" / "hermes" / "bin" / "hermes.exe"
    cmd = [str(hermes_exe if hermes_exe.is_file() else "hermes"), "chat", "-q", prompt, "-Q"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"hermes exited with {proc.returncode}")
    return proc.stdout.strip()


def _invoke_llm(messages: List[Dict[str, str]], backend: str = "ollama", temperature: float = 0.45) -> str:
    if backend == "hermes":
        combined = "\n\n".join(m["content"] for m in messages)
        return _call_hermes_chat(combined)
    if backend == "ollama":
        return _call_ollama_chat(messages, temperature=temperature)
    return ""


def _count_matches(text: str, patterns: List[str]) -> int:
    return sum(1 for pat in patterns if re.search(pat, text, re.IGNORECASE))


def score_vacancy(
    vacancy: Dict[str, Any],
    profile: Dict[str, Any] | None = None,
    use_llm: bool = True,
    backend: str = "ollama",
    min_score: int = 55,
    description: str = "",
    respect_excludes: bool = True,
) -> Dict[str, Any]:
    """Scores vacancy fit (0-100) and picks matching CV variant."""
    title = str(vacancy.get("title", "")).strip()
    company = str(vacancy.get("company", "")).strip()
    sector = str(vacancy.get("sector", "")).strip()
    tier = int(vacancy.get("tier") or 2)
    combined_lower = f"{title} {sector} {description}".lower()

    if respect_excludes and _count_matches(title.lower(), EXCLUDED_ROLE_PATTERNS) > 0:
        return {
            "score": 15,
            "fit": False,
            "cv_variant": "business_analyst",
            "reason": "Excluded non-target role by title rule",
            "keywords": [],
        }

    title_lower = title.lower()
    t_fin = _count_matches(title_lower, FINANCE_PATTERNS)
    t_ana = _count_matches(title_lower, ANALYTICS_PATTERNS)
    t_ops = _count_matches(title_lower, OPERATIONS_PATTERNS)

    fin_hits = _count_matches(combined_lower, FINANCE_PATTERNS)
    ana_hits = _count_matches(combined_lower, ANALYTICS_PATTERNS)
    ops_hits = _count_matches(combined_lower, OPERATIONS_PATTERNS)

    if t_fin > 0 and t_fin >= t_ana and t_fin >= t_ops:
        cv_variant = "financial_analyst"
    elif t_ops > 0 and t_ops > t_ana:
        cv_variant = "operations_manager"
    elif t_ana > 0:
        cv_variant = "business_analyst"
    elif fin_hits >= ana_hits and fin_hits >= ops_hits and fin_hits > 0:
        cv_variant = "financial_analyst"
    elif ops_hits > ana_hits and ops_hits > 0:
        cv_variant = "operations_manager"
    else:
        cv_variant = "business_analyst"

    base_score = 38
    base_score += 15 if tier == 1 else (8 if tier == 2 else 2)
    base_score += min(35, (fin_hits + ana_hits + ops_hits) * 18)
    base_score = max(0, min(95, base_score))

    keywords = [
        kw
        for kw in ("P&L", "SQL", "Excel", "Power BI", "Python", "BPMN", "SOP", "бюджетирование")
        if kw.lower() in combined_lower
    ]

    result = {
        "score": base_score,
        "fit": base_score >= min_score,
        "cv_variant": cv_variant,
        "reason": f"Tier {tier} | role hits fin={fin_hits}, ana={ana_hits}, ops={ops_hits}",
        "keywords": keywords,
    }

    if use_llm and backend in ("ollama", "hermes") and base_score >= 45:
        prof = profile or load_candidate_profile()
        prompt = (
            "Оцени соответствие вакансии профилю кандидата по шкале от 0 до 100 и выбери cv_variant "
            "(только одно из: financial_analyst, business_analyst, operations_manager).\n"
            f"Вакансия: {title} в компании {company} (Tier {tier}, сектор {sector}).\n"
            f"Описание: {description[:900] if description else 'нет подробного текста'}\n"
            f"Профиль кандидата:\n{prof['facts_block']}\n\n"
            'Верни строго JSON без пояснений: {"score": 80, "cv_variant": "financial_analyst", "reason": "кратко по-русски", "keywords": ["..."]}'
        )
        try:
            raw = _invoke_llm([{"role": "user", "content": prompt}], backend=backend, temperature=0.1)
            parsed = _extract_json_object(raw)
            if parsed and isinstance(parsed.get("score"), (int, float)):
                llm_score = max(0, min(100, int(parsed["score"])))
                blended = int(round((base_score * 0.45) + (llm_score * 0.55)))
                variant = str(parsed.get("cv_variant", "")).strip()
                if variant in ("financial_analyst", "business_analyst", "operations_manager"):
                    result["cv_variant"] = variant
                result["score"] = blended
                result["fit"] = blended >= min_score
                if parsed.get("reason"):
                    result["reason"] = str(parsed["reason"])[:200]
                if isinstance(parsed.get("keywords"), list):
                    result["keywords"] = [str(k)[:40] for k in parsed["keywords"][:5]]
        except Exception as e:
            log_event("HH_AI_SCORE_FALLBACK", {"vacancy_id": vacancy.get("id"), "error": str(e)}, level="WARNING")

    return result


def audit_cover_letter(text: str, company: str = "", position: str = "") -> Dict[str, Any]:
    """Validates a Russian cover letter against humanizer and factual integrity rules."""
    issues: List[str] = []
    clean = (text or "").strip()

    if len(clean) < 180:
        issues.append("Letter is too short (< 180 chars)")
    if len(clean) > 1200:
        issues.append("Letter is too long (> 1200 chars)")
    if "—" in clean or "--" in clean:
        issues.append("Contains forbidden em-dash or double-dash")
    if "{{" in clean or "}}" in clean:
        issues.append("Contains unreplaced template placeholder")

    lowered = clean.lower()
    if re.search(r"не\s+только\b[^.!?\n]{0,120}\bно\s+и\b", lowered):
        issues.append("Contains AI 'not only ... but also' contrast pattern")
    last_token = re.split(r"\s+", clean.strip())[-1].lower() if clean else ""
    dangling_words = {"что", "чтобы", "где", "как", "если", "и", "а", "но", "или", "в", "на", "с", "к", "по", "для", "от", "из"}
    if clean and (clean[-1] in ",;:" or last_token in dangling_words):
        issues.append("Letter appears truncated mid-sentence")

    for phrase in BANNED_AI_PHRASES:
        if phrase in lowered:
            issues.append(f"Contains AI cliché phrase: '{phrase}'")

    for pat in THIRD_PERSON_PATTERNS:
        if re.search(pat, lowered):
            issues.append("Third-person perspective drift detected")
            break

    for pat, msg in KNOWN_FACT_HALLUCINATIONS:
        if pat.search(clean):
            issues.append(msg)

    cyrillic_chars = len(re.findall(r"[а-яА-ЯёЁ]", clean))
    if cyrillic_chars < 80:
        issues.append("Insufficient Russian prose content")

    return {"ok": len(issues) == 0, "issues": issues}


def _strip_ai_dashes(text: str) -> str:
    cleaned = text.replace(" — ", ", ").replace("—", "-").replace("--", "-")
    return re.sub(r"[ \t]+", " ", cleaned).strip()


def _build_template_letter(vacancy: Dict[str, Any], sector: str, profile: Dict[str, Any]) -> str:
    title = str(vacancy.get("title", "вакансию")).strip()
    company = str(vacancy.get("company", "вашу компанию")).strip()
    _, _, hook, achieve = resolve_templates(sector or str(vacancy.get("sector", "Analytics")), title)
    hook_clean = _strip_ai_dashes(hook)
    achieve_clean = _strip_ai_dashes(achieve)
    return (
        f"Здравствуйте! Меня заинтересовала позиция «{title}» в {company}.\n\n"
        f"{hook_clean}\n\n"
        f"{achieve_clean} Дополнительно опираюсь на экономическое образование (ТФИ), опыт контроля стандартов "
        f"в АКБ «Равнак-банк» (-22% ошибок) и владение Excel, SQL, Power BI и Python.\n\n"
        f"Буду рад обсудить ваши задачи и подробнее рассказать о релевантном опыте на собеседовании.\n"
        f"С уважением, {profile['name']} ({profile['phone']}, {profile['telegram']})"
    )


def generate_cover_letter(
    vacancy: Dict[str, Any],
    profile: Dict[str, Any] | None = None,
    backend: str = "ollama",
    description: str = "",
    cv_variant: Optional[str] = None,
) -> Dict[str, Any]:
    """Generates and humanizer-audits a tailored Russian cover letter for a vacancy."""
    prof = profile or load_candidate_profile()
    title = str(vacancy.get("title", "")).strip()
    company = str(vacancy.get("company", "")).strip()
    sector = str(vacancy.get("sector", "Analytics")).strip()

    chosen_variant = cv_variant or score_vacancy(vacancy, profile=prof, use_llm=False).get("cv_variant", "business_analyst")

    if backend in ("ollama", "hermes"):
        sys_msg = (
            "Ты пишешь короткое, деловое и живое сопроводительное письмо на русском языке от первого лица (я) "
            "для отклика на HeadHunter (hh.uz).\n"
            "Правила:\n"
            "1. Длина строго 450-800 символов, 2-3 коротких абзаца.\n"
            "2. Используй только факты из профиля кандидата. Не перечисляй все места работы: выбери 1-2 самых подходящих факта.\n"
            "3. Никогда не приписывай работу аналитиком в Ravnaq Bank (там была должность супервайзера стандартов).\n"
            "4. Запрещено выдумывать сферы деятельности компаний: Explorer Logistics занималась исключительно транспортной логистикой и операционными процессами (не розничными магазинами, не телекомом/ШПД, не инвестиционными фондами).\n"
            "5. Запрещены длинные тире, штампы «не только..., но и», «идеальный кандидат», «отличный кандидат», «внести свой вклад», «достичь новых высот», «бесспорно», «синергия».\n"
            "6. Выведи ТОЛЬКО готовый текст письма без комментариев."
        )
        example_user = (
            "Вакансия: «Бизнес-аналитик» в компании «Kapitalbank».\n"
            "Ключевые акценты вакансии: BPMN, SQL, оптимизация процессов"
        )
        example_assistant = (
            "Здравствуйте! Меня заинтересовала позиция «Бизнес-аналитик» в Kapitalbank.\n\n"
            "В Explorer Logistics (CEO/COO) я описал и регламентировал операционные процессы, ускорил обработку заказов на 25% "
            "и настроил управленческий P&L, сократив накладные расходы на 18%. Ранее в АКБ «Равнак-банк» систематизировал "
            "стандарты обслуживания и снизил операционные ошибки на 22%.\n\n"
            "Уверенно работаю с SQL, Excel, Power BI и Python. Буду рад обсудить задачи на собеседовании.\n\n"
            "С уважением,\nАбдулхаким Курбанов"
        )
        user_msg = (
            f"Вакансия: «{title}» в компании «{company}».\n"
            f"Ключевые акценты вакансии: {description[:900] if description else sector}\n\n"
            f"Профиль кандидата:\n{prof['facts_block']}\n\n"
            "Напиши аналогичное по длине (450-800 символов) и живому стилю письмо под эту вакансию."
        )
        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": example_user},
            {"role": "assistant", "content": example_assistant},
            {"role": "user", "content": user_msg},
        ]

        for attempt in range(2):
            try:
                raw_text = _invoke_llm(messages, backend=backend, temperature=0.45)
                candidate = _strip_ai_dashes(raw_text)
                audit = audit_cover_letter(candidate, company=company, position=title)
                if audit["ok"]:
                    return {
                        "text": candidate,
                        "source": "llm",
                        "audit": audit,
                        "cv_variant": chosen_variant,
                    }
                if attempt == 0:
                    messages.append({"role": "assistant", "content": candidate})
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Исправь письмо. Нарушения: {'; '.join(audit['issues'])}. Верни только исправленный текст от первого лица.",
                        }
                    )
            except Exception as e:
                log_event("HH_AI_LETTER_FALLBACK", {"vacancy_id": vacancy.get("id"), "error": str(e)}, level="WARNING")
                break

    fallback = _strip_ai_dashes(_build_template_letter(vacancy, sector, prof))
    fallback_audit = audit_cover_letter(fallback, company=company, position=title)
    return {
        "text": fallback,
        "source": "template_fallback",
        "audit": fallback_audit,
        "cv_variant": chosen_variant,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score HH vacancy and compose humanized cover letter via Ollama/Hermes")
    parser.add_argument("--vacancy-id", type=str, default=None, help="Vacancy ID in positions.db")
    parser.add_argument("--title", type=str, default=None, help="Manual vacancy title")
    parser.add_argument("--company", type=str, default="", help="Manual employer name")
    parser.add_argument("--sector", type=str, default="Analytics", help="Vacancy sector")
    parser.add_argument("--tier", type=int, default=2, help="Employer tier (1-3)")
    parser.add_argument("--backend", choices=("ollama", "hermes", "none"), default="ollama", help="LLM backend")
    parser.add_argument("--db-path", type=str, default=None, help="Custom SQLite DB path")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    vacancy: Optional[Dict[str, Any]] = None
    if args.vacancy_id:
        db_target = Path(args.db_path) if args.db_path else Config.DB_PATH
        init_database(db_target)
        conn = get_connection(db_target)
        row = conn.execute(
            "SELECT id, title, company, url, tier, sector, salary_text FROM vacancies WHERE id = ?",
            (args.vacancy_id,),
        ).fetchone()
        conn.close()
        if not row:
            res = {"success": False, "code": Config.EXIT_NO_DATA, "error": f"Vacancy ID '{args.vacancy_id}' not found."}
            print(json.dumps(res, ensure_ascii=False, indent=2) if args.json else res["error"])
            return Config.EXIT_NO_DATA
        vacancy = {
            "id": row[0],
            "title": row[1],
            "company": row[2],
            "url": row[3],
            "tier": row[4],
            "sector": row[5],
            "salary_text": row[6],
        }
    elif args.title:
        vacancy = {
            "id": "manual",
            "title": args.title,
            "company": args.company or "Компания",
            "tier": args.tier,
            "sector": args.sector,
        }
    else:
        res = {"success": False, "code": Config.EXIT_ERROR, "error": "Provide --vacancy-id or --title."}
        print(json.dumps(res, ensure_ascii=False, indent=2) if args.json else res["error"])
        return Config.EXIT_ERROR

    profile = load_candidate_profile()
    scoring = score_vacancy(vacancy, profile=profile, use_llm=(args.backend != "none"), backend=args.backend)
    letter = generate_cover_letter(vacancy, profile=profile, backend=args.backend, cv_variant=scoring["cv_variant"])

    out = {
        "success": True,
        "code": Config.EXIT_SUCCESS,
        "vacancy": vacancy,
        "scoring": scoring,
        "letter": letter,
    }
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"Score: {scoring['score']}/100 (fit={scoring['fit']}, variant={scoring['cv_variant']})")
        print(f"Source: {letter['source']} | Audit OK: {letter['audit']['ok']}")
        print("-" * 50)
        print(letter["text"])
    return Config.EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
