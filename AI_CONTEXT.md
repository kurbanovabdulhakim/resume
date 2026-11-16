---
title: Machine-Readable Agent Context State
description: Real-time autonomous context state snapshot consumed by AI agents to operate on positions.db.
status: active
category: status
tags: [ai-context, agent-first, state, pipeline, automation]
last-verified: 2026-11-16
summary-ru: Машиночитаемый контекст текущего состояния воронки вакансий для ИИ-агентов.
summary-uz: Sun'iy intellekt agentlari uchun vakansiyalar holati bo'yicha mashina o'qiydigan kontekst.
related:
  - AGENTS.md
  - PIPELINE.md
  - db/schema.md
---

# Machine-Readable AI Agent Context

```yaml
{
  "generated_at": "2026-11-16T23:56:54.102766",
  "database": "db/positions.db",
  "vacancies_total": 5453,
  "active_vacancies": 3115,
  "total_vacancies": 5453,
  "applications_total": 1850,
  "total_applications": 1850,
  "statuses": {
    "applied": 1798,
    "viewed": 0,
    "invited": 6,
    "interview": 46,
    "offer": 0,
    "rejected": 0,
    "declined": 0
  },
  "tier_distribution": {
    "1": 509,
    "2": 2323,
    "3": 2621
  },
  "sector_distribution": {
    "Analytics": 259,
    "Banking": 2,
    "Finance": 2758,
    "Logistics": 346,
    "Management": 2079,
    "Финансовые Data и Бизнес-аналитики": 2,
    "Финансовые аналитики и FP&A": 1,
    "Финансовые директора (CFO)": 1,
    "Финансовые менеджеры и Корпоративные финансы": 2,
    "Финансовый контроль и Аудит": 1,
    "Экономисты предприятий": 2
  },
  "urgent_leads_count": 52,
  "urgent_leads": [
    {
      "id": "136624628",
      "company": "НОУ FINANCE PROFESSIONAL SCHOOL ALGHORITM",
      "title": "ACCA Lecturer / ACCA Instructor",
      "status": "interview",
      "notes": "Отклик Август/Сентябрь 2026. Скриншот: Отклик_136624628_НОУ FINANCE PROFESSIONAL SCHOOL ALGHORIT_20260908_162734.png | Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "136624506",
      "company": "НОУ FINANCE PROFESSIONAL SCHOOL ALGHORITM",
      "title": "SAT (Math-Eng) / Учитель математики в \"Al Jabr School\"",
      "status": "interview",
      "notes": "Отклик Август/Сентябрь 2026. Скриншот: Отклик_136624506_НОУ FINANCE PROFESSIONAL SCHOOL ALGHORIT_20260908_162743.png | Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "136920190",
      "company": "IJOD BINOKOR",
      "title": "Менеджер по продажам/ Начинающий агент в Филиал",
      "status": "interview",
      "notes": "Отклик Август/Сентябрь 2026. Скриншот: Отклик_136920190_IJOD BINOKOR_20260911_143729.png | Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137254123",
      "company": "ALWOOD",
      "title": "Главный бухгалтер",
      "status": "interview",
      "notes": "Отклик Август/Сентябрь 2026. Скриншот: Отклик_137254123_ALWOOD_20260912_161021.png | Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "136656030",
      "company": "EXPERT HOMES",
      "title": "МЕНЕДЖЕР ПО РАБОТЕ С КЛЮЧЕВЫМИ КЛИЕНТАМИ /ПАРТНЁРАМИ (недвижимость) офис Tashkent City Boulevard",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137272727",
      "company": "CLASS A RECRUITING",
      "title": "Driver Recruiter",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "135624730",
      "company": "Grand Diantus",
      "title": "Executive assistant",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137328600",
      "company": "SHARQIY EXPRESS CORP",
      "title": "Operatsion direktor",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137205815",
      "company": "IT-LEGACY",
      "title": "Updater Специалист",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137132938",
      "company": "CALLTECH",
      "title": "Менеджер входящей линии СДЭК (со знанием русского языка в совершенстве)",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137438411",
      "company": "AIVA Group",
      "title": "AI-разработчик / вайбкодер",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137407899",
      "company": "THEPROMOTION",
      "title": "Project Manager / SMM Team Leader",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137052795",
      "company": "Gift Master 2018",
      "title": "Менеджер по продажам (B2B)",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137114208",
      "company": "COURSTRAVELACADEMY",
      "title": "Менеджер маркетплейсов",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137365328",
      "company": "TWINAXIS",
      "title": "Update/Tracking specialist",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137427241",
      "company": "KUDRATOVA IRODA",
      "title": "Бизнес ассистент/Помощник руководителя",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "133262847",
      "company": "ALLUCKING GLOBAL",
      "title": "Ombor operatori / Buyurtmalarni yig‘uvchi",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137415551",
      "company": "REGOS Software",
      "title": "Менеджер по работе с клиентами",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137284874",
      "company": "INCOTRUCK",
      "title": "Стажёр операционного отдела и логистики",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137271043",
      "company": "AKELA GROUP MACHINERY",
      "title": "Менеджер по закупу со знанием английского языка - Стажер",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137244431",
      "company": "AKELA GROUP MACHINERY",
      "title": "Менеджер по продажам со знанием английского языка - Project Manager (Менеджер по продажам проектов)",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137234298",
      "company": "Prowork",
      "title": "Торговый представитель маркетплейс",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137361145",
      "company": "SALES UP TECHNOLOGIES",
      "title": "Менеджер по продажам",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "136279834",
      "company": "CENTRIS",
      "title": "Координатор / Supervisor",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137414796",
      "company": "CENTRIS",
      "title": "Менеджер по закупкам и снабжению",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137365738",
      "company": "CORE LOGISTICS",
      "title": "Junior Диспетчер / HR в Aмериканскую логистику",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137367582",
      "company": "KUDRATOVA IRODA",
      "title": "Assistant of CEO - American timeline",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137368903",
      "company": "KUDRATOVA IRODA",
      "title": "Бизнес ассистент / Операционный менеджер",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137342321",
      "company": "SMART HR",
      "title": "Финансовый директор (CFO) (Ресторанный бизнес)",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137299414",
      "company": "WEBASE",
      "title": "Support Manager",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137318815",
      "company": "USTORES",
      "title": "Финансовый контролер",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "136878397",
      "company": "KUDRATOVA IRODA",
      "title": "Бизнес ассистент/Помощник руководителя (международные поездки)",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137369321",
      "company": "UniStaff ProGroup",
      "title": "Driver Manager (USA Logistics)",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "136809880",
      "company": "ALIFCO",
      "title": "Руководитель отдела по работе с продавцами (Dona.uz)",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137026203",
      "company": "ACADEMY STRATEG",
      "title": "Помощник/Ассистент руководителя",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137042033",
      "company": "Тарба Виталий Георгиевич",
      "title": "Prodject Manager в IT",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "136530412",
      "company": "KUDRATOVA IRODA",
      "title": "Бизнес ассистент / Операционный менеджер",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "136779265",
      "company": "DWED ASSOCIATION",
      "title": "Менеджер по продажам ERP-системы (B2B, IT)",
      "status": "interview",
      "notes": "Отклик Август/Сентябрь 2026. Скриншот: Отклик_136779265_DWED ASSOCIATION_20260911_145727.png | Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137285234",
      "company": "IZISOL",
      "title": "Стажёр отдела логистики",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "136755926",
      "company": "Wellness Point LLC",
      "title": "Teleselling manager",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137541456",
      "company": "PEOPLEOPS",
      "title": "SMM-менеджер (проектный менеджер SMM-направления)",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137132955",
      "company": "CALLTECH",
      "title": "Менеджер в банк (со знанием русского языка в совершенстве)",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137287660",
      "company": "CALLTECH",
      "title": "Менеджер в call-центр сотовой компании (со знанием русского языка)",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "136613544",
      "company": "CLASS A RECRUITING",
      "title": "Driver Recruiter Specialist + Consultant",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "136639456",
      "company": "ITM-CA",
      "title": "Промоутер парламент",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "136704005",
      "company": "EXPERT HOMES",
      "title": "БЕЗ ОПЫТА !!! Начинающий специалист по недвижимости TASHKENT CITY OFFICE",
      "status": "interview",
      "notes": "Приглашение: Приглашение на собеседование. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "137110541",
      "company": "LEADING BUSINESS SOFTWARE",
      "title": "Бухгалтер",
      "status": "invited",
      "notes": "Отклик Август/Сентябрь 2026. Скриншот: Отклик_137110541_LEADING BUSINESS SOFTWARE_20260912_161717.png | Приглашение: Худиева Аида: Напишите в рабочее время в WhatsApp (+7 987 398-27-22) или Telegram (@aidakh98). Контакты: @aidakh98; Cover letter generated & repaired"
    },
    {
      "id": "136956607",
      "company": "Eastline General Services Group",
      "title": "Стажёр логист",
      "status": "invited",
      "notes": "Приглашение: Пройти опрос кандидата через официального Telegram-бота @EGS_Candidate_Bot. Контакты: @EGS_Candidate_Bot, @EGS_Candidate_Bot; Cover letter generated & repaired"
    },
    {
      "id": "136593120",
      "company": "LEADING BUSINESS SOFTWARE",
      "title": "Менеджер по продажам",
      "status": "invited",
      "notes": "Приглашение: Худиева Аида: Напишите в рабочее время в WhatsApp (+7 987 398-27-22) или Telegram (@aidakh98). Контакты: @aidakh98; Cover letter generated & repaired"
    },
    {
      "id": "137177083",
      "company": "ЧП IFOR TOYS",
      "title": "Do'kon rahbari | Директор магазина",
      "status": "invited",
      "notes": "Приглашение: Работодатель спросил: 'Vakansiya bo'yicha berilgan ma'lumot va savollar sizga tushunarli bo'ldimi? Savollarga javobingiz bormi?'. Контакты: В чате HH; Cover letter generated & repaired"
    },
    {
      "id": "136546079",
      "company": "TRANSCEKA LOGISTIC SERVICES",
      "title": "Стажёр отдела логистики",
      "status": "invited",
      "notes": "Приглашение: Пройти опрос кандидата через официального Telegram-бота @EGS_Candidate_Bot. Контакты: @EGS_Candidate_Bot, @EGS_Candidate_Bot; Cover letter generated & repaired"
    },
    {
      "id": "136711726",
      "company": "Eastline Express",
      "title": "Стажёр отдела логистики",
      "status": "invited",
      "notes": "Приглашение: Пройти опрос кандидата через официального Telegram-бота @EGS_Candidate_Bot. Контакты: @EGS_Candidate_Bot, @EGS_Candidate_Bot; Cover letter generated & repaired"
    }
  ],
  "recommended_next_actions": [
    "Check urgent_leads to prepare tailored CV and interview prep",
    "To sync new batch from Hermes, run: python scripts/sync_hermes.py --json",
    "To generate tailored docs for vacancy, run: python scripts/generate_docs.py --vacancy-id <id> --json",
    "To record interview or status change: python scripts/update_status.py --vacancy-id <id> --status interview --json"
  ]
}
```

## Quick Reference for Cold Agents
- **Primary Database:** `db/positions.db` (SQLite, tracked in Git)
- **Sync Command:** `python scripts/sync_hermes.py --json`
- **Document Generation:** `python scripts/generate_docs.py --vacancy-id <id> --json`
- **Update Status:** `python scripts/update_status.py --vacancy-id <id> --status <status> --json`
- **Recompile Dashboard:** `python scripts/dashboard.py --json`
