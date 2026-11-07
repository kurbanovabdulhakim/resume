#set page(
  paper: "a4",
  margin: (x: 2cm, y: 2.2cm),
)
#set text(
  font: ("Inter", "Segoe UI", "Arial"),
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
    #text(size: 10.5pt, weight: "medium", fill: rgb("#0284c7"))[Бизнес-аналитик • Финансовый аналитик • Операционный менеджер]
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
  [*Кому:*], [Отделу подбора персонала {{company}}],
  [*Вакансия:*], [{{position}}],
)

#v(14pt)

#text(size: 11pt, weight: "bold", fill: rgb("#0f172a"))[Уважаемые коллеги из {{company}}!]

#v(6pt)

Меня заинтересовала позиция *{{position}}* в компании *{{company}}*.

{{sector_hook}}

{{key_achievement}}

Обладая высшим экономическим образованием (Ташкентский финансовый институт) и практическим опытом руководства операционной и аналитической деятельностью, я готов подключиться к задачам {{company}} и обеспечить прозрачность процессов, надежный учет и измеримый финансовый результат.

Буду рад обсудить возможности сотрудничества и детали задач на собеседовании.

#v(16pt)

#text(weight: "bold")[С уважением,] \
#v(2pt)
*{{candidate_name}}* \
#text(size: 9pt, fill: rgb("#64748b"))[{{candidate_phone}} | {{candidate_email}} | Telegram: {{candidate_telegram}}]
