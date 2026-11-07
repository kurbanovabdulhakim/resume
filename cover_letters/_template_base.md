---
title: Base Cover Letter Template Specification
description: Canonical base cover letter template specifying placeholder tags and formatting for automated document generation.
status: active
category: reference
tags: [template, cover-letter, generator, placeholders]
last-verified: 2026-11-08
summary-ru: Спецификация базового шаблона сопроводительного письма с описанием всех тегов подстановки.
summary-uz: Avtomatlashtirilgan hujjat yaratish uchun barcha placeholder teglari tavsiflangan asosiy qoplama xati shabloni.
related:
  - cover_letters/banking_finance.md
  - cover_letters/logistics_aviation.md
  - cover_letters/fmcg_distribution.md
  - cover_letters/it_analytics.md
  - scripts/generate_docs.py
---

# Base Cover Letter Template

This base template documents all dynamic variables substituted by `scripts/generate_docs.py`:

- `{{company}}`: Employer name (e.g., "Kapitalbank", "Murad Buildings")
- `{{position}}`: Vacancy title (e.g., "Senior Business Analyst")
- `{{sector_hook}}`: Targeted sector-specific opening paragraph
- `{{key_achievement}}`: Metric-driven achievement tailored to the role
- `{{salary_expectation}}`: Expected salary range (e.g., "$1,500 - $2,500")
- `{{candidate_name}}`: Candidate full name (Абдулхаким Курбанов)
- `{{candidate_phone}}`: Contact phone (+998 90 855-07-90)
- `{{candidate_email}}`: Email address (aa998908550790@gmail.com)
- `{{candidate_telegram}}`: Telegram handle (@SAWAS0078)
- `{{date}}`: Date of generation (YYYY-MM-DD)

---

**Дата:** {{date}}  
**Кому:** Команде найма {{company}}  
**Позиция:** {{position}}  
**Кандидат:** {{candidate_name}} (тел: {{candidate_phone}}, email: {{candidate_email}}, Telegram: {{candidate_telegram}})

### Уважаемые коллеги из {{company}}!

Меня заинтересовала вакансия **{{position}}** в вашей организации. 

{{sector_hook}}

{{key_achievement}}

Обладая высшим экономическим образованием (Ташкентский финансовый институт) и практическим опытом руководства операционной и аналитической деятельностью, я готов подключиться к задачам {{company}} и обеспечить прозрачность процессов, надежный учет и измеримый финансовый результат.

Буду рад обсудить возможности сотрудничества и детали задач на собеседовании.

С уважением,  
**{{candidate_name}}**  
{{candidate_phone}} | {{candidate_email}} | {{candidate_telegram}}
