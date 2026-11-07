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
    #text(size: 10.5pt, weight: "medium", fill: rgb("#0284c7"))[Операционный менеджер • Логистика & Снабжение]
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
  [*Кому:*], [Руководству и HR-департаменту {{company}}],
  [*Вакансия:*], [{{position}}],
)

#v(14pt)

#text(size: 11pt, weight: "bold", fill: rgb("#0f172a"))[Уважаемые коллеги из {{company}}!]

#v(6pt)

Направляю отклик на открытую вакансию *{{position}}* в компании *{{company}}*.

Имею непосредственный опыт управления логистической компанией (EXPLORER LOGISTICS) в должности генерального/операционного директора. Знаю изнутри процессы автомобильных перевозок, координации маршрутов, складской логистики, документооборота и работы с поставщиками и подрядчиками.

{{key_achievement}}

Мой подход строится на выстраивании четких регламентов (SOP), исключении простоев, строгом материальном учете и автоматизации процессов контроля грузов и сроков.

Готов применить свой управленческий и практический опыт для оптимизации цепочек поставок и масштабирования операционной эффективности {{company}}.

#v(18pt)

#text(weight: "bold")[С уважением,] \
#v(2pt)
*{{candidate_name}}* \
#text(size: 9pt, fill: rgb("#64748b"))[{{candidate_phone}} | {{candidate_email}} | Telegram: {{candidate_telegram}}]
