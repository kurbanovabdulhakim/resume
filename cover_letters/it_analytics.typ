#set page(
  paper: "a4",
  margin: (x: 2cm, y: 2.2cm),
)
#set text(
  font: ("Segoe UI", "Calibri", "Arial"),
  size: 10.5pt,
  fill: rgb("#1e293b"),
  lang: "ru"
)
#set par(
  justify: true,
  leading: 0.75em,
)

// Header
#grid(
  columns: (1fr, auto),
  align: (left, right),
  [
    #text(size: 16pt, weight: "bold", fill: rgb("#0f172a"))[{{candidate_name}}] \
    #v(2pt)
    #text(size: 10.5pt, weight: "medium", fill: rgb("#0284c7"))[Бизнес-аналитик • Data Analyst • BPMN & SQL]
  ],
  [
    #text(size: 9pt, fill: rgb("#64748b"))[
      #link("tel:{{candidate_phone}}")[{{candidate_phone}}] \
      #link("mailto:{{candidate_email}}")[{{candidate_email}}] \
      Telegram: #link("https://t.me/SAWAS0078")[{{candidate_telegram}}] \
      Ташкент, Узбекистан
    ]
  ]
)

#v(8pt)
#line(length: 100%, stroke: 1.5pt + rgb("#0284c7"))
#v(12pt)

#grid(
  columns: (auto, 1fr),
  gutter: 10pt,
  [*Дата:*], [{{date}}],
  [*Кому:*], [IT & Product Hiring Team {{company}}],
  [*Позиция:*], [{{position}}],
)

#v(14pt)

#text(size: 11pt, weight: "bold", fill: rgb("#0f172a"))[Здравствуйте, команда {{company}}!]

#v(6pt)

Хочу предложить свою кандидатуру на роль *{{position}}* в компании *{{company}}*.

Мой профиль сочетает строгое экономическое мышление (Ташкентский финансовый институт) и практические навыки оцифровки процессов: моделирование AS-IS/TO-BE (BPMN), написание ТЗ, анализ продуктовых и операционных метрик, работу с реляционными базами данных (SQL) и построение дашбордов в Power BI.

{{key_achievement}}

Я умею выступать мостом между бизнес-заказчиками и разработчиками, четко формулировать требования, приоритизировать бэклог и валидировать результаты на основе реальных данных.

Буду рад подробнее обсудить задачи команды {{company}} и продемонстрировать свои кейсы на интервью.

#v(18pt)

#text(weight: "bold")[С уважением,] \
#v(2pt)
*{{candidate_name}}* \
#text(size: 9pt, fill: rgb("#64748b"))[{{candidate_phone}} | {{candidate_email}} | Telegram: {{candidate_telegram}}]
