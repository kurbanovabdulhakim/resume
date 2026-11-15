# Design Spec: Hermes + Ollama Visible HeadHunter Autonomy Pipeline

**Date:** 2026-11-11  
**Author:** Abdulkhakim Kurbanov (with Antigravity)  
**Status:** Approved (Mode 1 Primary + Live Fallback to Mode 2 / API / Assist)

---

## 1. Goal & Scope

Build, thoroughly verify, and visibly run a localized **Hermes + Ollama + HeadHunter (`hh.uz`)** job-application workflow integrated directly with `db/positions.db` and the `resume` repository.

- **Primary Launch Mode:** `--mode browser --confirm none` (autonomous visible Edge wave execution with human-like pacing, progressive daily cap up to `200`, unique LLM-composed Russian cover letters, automatic pause + alert on CAPTCHA / login / SMS).
- **Live Fallback / Saved Alternative Modes (1-command or mid-run switchable):**
  1. `--confirm each` (Variant 2: opens vacancy, fills tailored letter, waits for user `Enter` before clicking submit — switchable live at any pause prompt or via CLI flag).
  2. `--confirm batch` (preview N scored items, confirm once, run batch).
  3. `--mode api` (Official HeadHunter OAuth `POST /negotiations` via `dev.hh.ru` token when authorized).
  4. `--mode assist` (opens vacancy + copies personalized letter for manual click).

---

## 2. Verified Environment & Platform Constraints

Direct checks on `2026-11-11` established these real-world constraints that shape the design:

1. **Unauthenticated `api.hh.ru/vacancies` returns `HTTP 403 {"errors":[{"type":"forbidden"}]}`** (ddos-guard / frontik), so `hh_watcher.py` must not rely blindly on unauthenticated API scraping. However:
   - `db/positions.db` already contains **1,477 active unapplied `hh.uz` vacancies** (`38` Tier 1, `143` Tier 2, `1,296` Tier 3) ready for scoring and application.
   - Logged-in visible Edge can legitimately browse `tashkent.hh.uz/search/vacancy` pages when refreshing fresh vacancies, and `hh_watcher.py` supports `HH_ACCESS_TOKEN` Bearer auth when available.
2. **HeadHunter Platform Limits & CAPTCHA Policy:**
   - Official daily application cap on HH is **200 applications per 24 hours** (configurable via `--daily-limit`, default `200`, executed in natural spaced waves e.g. `--wave-size 25`).
   - **Zero anti-bot evasion / CAPTCHA bypass / spoofing / reverse-engineered mobile tokens.** Any CAPTCHA, SMS/email challenge, or re-login screen triggers an **immediate visible & audible pause** (`winsound` / terminal prompt) so the user handles it directly in the open Edge window, and offers an instant live option to switch into `--confirm each` (Variant 2) if challenges appear too often.
3. **Local LLM Benchmark (`127.0.0.1:11434` on RTX 4060 Ti 8.0 GiB VRAM):**
   - `hermes3:8b` hallucinated 3rd-person recruiter perspective and broken Russian spelling (`9.02s`).
   - `qwen2.5-coder:7b` produced grammatical 1st-person Russian (`6.52s`) when given structured prompts.
   - Because Hermes CLI enforces a minimum `64,000` context check (`context_length` and `ollama_num_ctx: 65536`) for tool use, `config.yaml` preserves `65536` for interactive `hermes`, while `hh_ai.py` sends `num_ctx: 12288` (`Config.OLLAMA_NUM_CTX`) directly to Ollama `127.0.0.1:11434/api/chat` so batch scoring/drafting stays in 8 GiB GPU VRAM without CPU offload.
4. **Database Schema Integrity (`db/schema.sql`):**
   - `applications.status` strictly allows `('applied', 'viewed', 'invited', 'interview', 'offer', 'rejected', 'declined')`.
   - Pre-application queue states (`ready`, `needs_human`, `skipped`, `failed`, `applied`) live cleanly in `logs/hh_autonomy_queue.json` (gitignored/runtime) or `data/`, NEVER writing invalid strings into `applications.status`.

---

## 3. Architecture & Components

### A. Configuration & Workspace Isolation (`scripts/config.py`, `hermes/config.yaml`, `scripts/portals/olx_outreach.py`)
- Preserved `C:\Users\Abdulkhakim\AppData\Local\hermes\config.yaml` (`config.yaml.bak` backup created) at `context_length: 65536` / `ollama_num_ctx: 65536` for Hermes tool-use compatibility, while `Config.OLLAMA_NUM_CTX = 12288` caps Ollama KV-cache inside batch `hh_ai.py` calls.
- Fix `Config.DEFAULT_HERMES_QUEUE_PATHS` bug where empty `HERMES_QUEUE_FILE` resolved to `Path(".")`.
- Add `Config` runtime constants (derivable from `PROJECT_ROOT` & env overrides):
  - `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (`qwen2.5-coder:7b`), `OLLAMA_NUM_CTX` (`12288`)
  - `HH_SESSION_PROFILE_DIR` (defaults to `Path.home() / ".gemini" / "hh_main_session"`, overrideable via `HH_PROFILE_DIR`)
  - `DATA_DIR` (`PROJECT_ROOT / "data"`), `HH_QUEUE_FILE`, `HH_STATE_FILE` (gitignored via `.gitignore`)
- Clean `scripts/portals/olx_outreach.py` of the broken hardcoded `mywork` import path and illegal DB status strings (`ready_for_outreach`, `needs_in_site_message`), routing OLX outreach drafts cleanly via `humanizer`-checked local helper / valid DB notes.
- Fix `scripts/portals/hh_watcher.py` to add `HH-User-Agent`, optional `HH_ACCESS_TOKEN` Bearer auth, and structured HTTP error classification (`forbidden_api` vs network error).

### B. Profile Grounding, Fit Scoring & Humanized Cover Letter Engine (`scripts/hh_ai.py`)
- **Factual Profile Loader (`load_candidate_profile`):** reads `master/resume.md` and `cover_letters/` templates so every LLM prompt contains verified employers, dates, education (`ТФИ`), tools (`Python, SQL, Power BI, Excel, Bitrix24, amoCRM`), and metrics (`-18% OpEx`, `-25% order cycle`, `-22% service errors`).
- **Role Scoring & Variant Picker (`score_vacancy`):**
  - Deterministic filter penalizing non-target roles (e.g., `scrum`, `smm`, `маркетинг`, `водитель`, `курьер`, `колл-центр`, `дизайнер`, `1с программист`) and boosting target analytics/finance/operations/management matches (`Tier 1/2`).
  - Local `Ollama` scoring pass (`--llm-backend ollama | hermes | none`) refines fit score (`0..100`), selects matching `cv_variant` (`financial_analyst`, `business_analyst`, `operations_manager`), and returns `skip` reason for mismatches below threshold (`--min-score`, default `55`).
- **Humanized Cover Letter Generator & Auditor (`generate_cover_letter`, `audit_cover_letter`):**
  - System + user prompt strictly adhering to `document-humanizer.md`: 1st-person voice (`"Я"` / `"Меня заинтересовала..."`), 3 concise paragraphs (`350–900` chars), zero em-dashes (`—`), zero AI cliché phrases (`не просто ... а`, `бесспорно`, `достичь новых высот`, `к процветанию`, `погрузиться`, `синергия`), zero third-person drift or unverified role claims (e.g. never claiming `"финансовый аналитик в Равнак-банке"` when actual role was `"супервайзер / контролер стандартов"`).
  - Post-generation validator checks factual consistency, Cyrillic grammar heuristics, placeholder leaks, length bounds, and banned patterns. Retries once on failure, otherwise falls back cleanly to a deterministic `cover_letters/` humanized template render.

### C. Queue & Pacing Engine (`scripts/hh_queue.py`)
- Pulls unapplied active `hh.uz` vacancies from `db/positions.db` sorted by `tier ASC, published_at DESC`.
- Persists daily application counters & per-vacancy states in `data/hh_autonomy_state.json` and `data/hh_autonomy_queue.json`:
  - Daily limit check (rolling 24h / calendar day counter persisted across restarts, `--daily-limit` default `200`).
  - Wave tracking (`--wave-size` default `25`, `--wave-pause-sec` default `900` = 15 min configurable down/up).
  - Deduplication against `positions.db` (`applied`, `rejected`, `declined`, etc.) and previously archived/skipped vacancies.
  - Progressive just-in-time preparation: prepares small lookahead (`batch` of next 5–10) or generates each letter right as the cycle runs so Edge opens within seconds instead of waiting 20 minutes up front.

### D. Multi-Mode Visible Application Runner (`scripts/hh_apply.py` + `scripts/launch_hh_visible.ps1`)
- **`BrowserDriver` (Selenium 4.47 + Visible `Edge` + `hh_main_session`):**
  - Launches non-headless visible `msedge.exe` window positioned cleanly on screen.
  - Opens vacancy URL; checks for archive/unavailable status (auto-marks `vacancies.is_active = 0` in DB if closed), checks if HH already shows `"Вы откликнулись"` (syncs `'applied'` idempotently to DB).
  - **Guardrail Detection:** scans DOM/URL for login gate, CAPTCHA (`smartcaptcha`, `recaptcha`, `ddos-guard`, `captcha`), or SMS code -> immediately sounds alert, displays bright interactive pause banner with live options:
    - `[Enter]` resume after manual completion in Edge
    - `[2]` switch this session live to `--confirm each` (Variant 2)
    - `[s]` skip current vacancy
    - `[q]` save state and exit cleanly
  - **Human-like Interaction:** gradual vertical scrolling, variable page-read delay (`6–15s`), real element focus & button click on `"Откликнуться"`, selects matching HH resume option if multi-resume selector appears, checks mandatory employer questionnaire (`Вопросы работодателя` / external test):
    - `--on-questions defer | pause` (default `defer` in `--confirm none` so unattended batch logs `needs_human` with URL + draft letter without stalling, or `pause` when user wants live prompt).
  - Expands/focuses cover letter input, inserts humanized letter naturally, confirms (or submits in `--confirm none`), verifies `"Отклик отправлен"` / `"Вы откликнулись"`.
  - Records `'applied'` + `cv_variant` + `cover_letter_sent=1` via `update_application_status`, updates daily counter, regenerates `dashboard.py`, waits natural inter-application interval (`--min-delay 30 --max-delay 75` configurable), optionally refreshes search harvest pages via visible browser (`--harvest-queries`) when queue runs low.
- **`ApiDriver` (`--mode api`):** Official OAuth `POST https://api.hh.ru/negotiations` using `HH_ACCESS_TOKEN`, explicitly reporting `403` permission errors cleanly without unofficial credentials.
- **`AssistDriver` (`--mode assist`):** Opens vacancy in visible Edge, prints & copies humanized letter to clipboard, waits `Enter` after manual click, logs `'applied'` to DB.
- **Foreground Launcher (`scripts/launch_hh_visible.ps1`):** ensures Ollama `11434` is up, optionally opens interactive `hermes` companion or runs `hh_apply.py` directly in a visible foreground PowerShell console alongside Edge so nothing runs hidden in background.

---

## 4. Verification Plan Before Live Launch

1. Unit tests (`python -m unittest discover tests`) covering:
   - `config.py` path resolution & non-dot `DEFAULT_HERMES_QUEUE_PATHS`
   - `hh_ai.py` deterministic role filter, prompt grounding, and `humanizer` audit rejecting em-dashes, 3rd person, banned clichés, and hallucinated titles
   - `hh_queue.py` daily cap enforcement, idempotency, state persistence, DB exclusion
   - `hh_apply.py` mock driver state transitions (CAPTCHA pause -> continue/switch to mode 2, archived vacancy -> DB deactivate, already applied -> DB sync, questions -> defer/pause, dry-run execution)
   - `olx_outreach.py` valid imports & DB status compatibility
2. Live multi-pass dry-run against real `db/positions.db` + live `Ollama (qwen2.5-coder:7b)` generating & auditing sample cover letters on top Tier 1/2 vacancies.
3. Live non-submitting browser smoke check (`Edge` + `hh_main_session`) verifying `hh.uz` loads visibly without immediate crash, login state check, and DOM selector inspection before enabling live submit.
