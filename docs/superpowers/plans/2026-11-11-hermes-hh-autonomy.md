# Hermes + Ollama Visible HeadHunter Autonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or inline TDD) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a verified, visibly running HeadHunter (`hh.uz`) autonomous application workflow powered by `Hermes + Ollama` and integrated with `db/positions.db`, defaulting to Option 1 (`--mode browser --confirm none`, up to `--daily-limit 200` in spaced waves, auto-pausing cleanly on CAPTCHA/login) with instant CLI and live mid-run fallback to Option 2 (`--confirm each`), `--mode api`, and `--mode assist`.

**Architecture:** Five focused modules follow `AGENTS.md` CLI/stdlib standards (`--help`, `--json`, exit codes `0/1/2`, `Config` paths, `positions.db` SSOT, `humanizer` compliance): (1) Hermes + `Config` isolation fixes, (2) `hh_ai.py` grounded Ollama scorer and humanized cover-letter validator, (3) `hh_queue.py` daily limit + wave state + DB selector, (4) `hh_apply.py` multi-mode runner (`BrowserDriver` via visible Edge + `hh_main_session`, `ApiDriver`, `AssistDriver`), and (5) `launch_hh_visible.ps1` foreground launcher. Pre-application states live in `data/hh_autonomy_*.json` so `db/schema.sql` status constraints remain intact until real submission.

**Tech Stack:** Python 3.12 stdlib (`sqlite3`, `urllib`, `json`, `argparse`, `unittest`), `Selenium 4.47.0` + cached `msedgedriver.exe` + visible `msedge.exe`, local `Ollama` (`qwen2.5-coder:7b` at `http://127.0.0.1:11434`), `Hermes Agent v0.21.0`.

## Global Constraints

- `db/positions.db` is Single Source of Truth; after any DB update run `scripts/dashboard.py` logic or CLI (never hand-edit `AI_CONTEXT.md`).
- Every new/updated CLI script must support `--help`, `--json`, idempotency, and exit codes `Config.EXIT_SUCCESS (0)`, `Config.EXIT_ERROR (1)`, `Config.EXIT_NO_DATA (2)`.
- Never hardcode repo paths outside `scripts.config.Config`.
- All cover letters must satisfy `document-humanizer.md` (no em-dashes `—`, no banned AI clichés, 1st-person Russian, strictly verified facts from `master/resume.md`).
- Zero CAPTCHA solving/bypassing/evasion/spoofing; pause visibly and prompt user on CAPTCHA, SMS, or login gates.
- Keep all existing `15` tests green and build every component test-first.

---

### Task 1: Tune Hermes Ollama Context & Fix Config Isolation + Cleanup

**Files:**
- Modify: `C:\Users\Abdulkhakim\AppData\Local\hermes\config.yaml` (plus backup `.bak`)
- Modify: `C:\Users\Abdulkhakim\Git-Projects\resume\.gitignore`
- Modify: `C:\Users\Abdulkhakim\Git-Projects\resume\scripts\config.py`
- Modify: `C:\Users\Abdulkhakim\Git-Projects\resume\scripts\portals\hh_watcher.py`
- Modify: `C:\Users\Abdulkhakim\Git-Projects\resume\scripts\portals\olx_outreach.py`
- Test: `C:\Users\Abdulkhakim\Git-Projects\resume\tests\test_config.py`

**Interfaces:**
- Produces in `Config`: `DATA_DIR`, `HH_QUEUE_FILE`, `HH_STATE_FILE`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_NUM_CTX`, `HH_SESSION_PROFILE_DIR`, fixed `DEFAULT_HERMES_QUEUE_PATHS` (no empty-string `Path('.')` bug).
- Produces in `hh_watcher.py`: optional `HH_ACCESS_TOKEN` Bearer support + explicit `http_status` error tracking.
- Produces in `olx_outreach.py`: dependency-free draft generation with zero external `mywork` imports and zero illegal DB status strings.

- [ ] **Step 1: Add failing tests in `tests/test_config.py` and `tests/test_portals.py`**
  Verify `Path('.')` does not appear in `Config.DEFAULT_HERMES_QUEUE_PATHS` when `HERMES_QUEUE_FILE` is empty, verify `Config.HH_QUEUE_FILE`, `Config.OLLAMA_NUM_CTX == 12288`, `Config.HH_SESSION_PROFILE_DIR`, and verify `olx_outreach.process_pending_olx_vacancies` succeeds against a fresh temp DB without modifying `applications.status` illegally.
- [ ] **Step 2: Run targeted unit tests to verify they fail (`RED`)**
  Run `python -m unittest tests.test_config tests.test_portals -v`.
- [ ] **Step 3: Apply Hermes config tuning + `config.py` / `.gitignore` / `hh_watcher.py` / `olx_outreach.py` fixes**
  - Back up `C:\Users\Abdulkhakim\AppData\Local\hermes\config.yaml` -> `config.yaml.bak`, update `context_length: 12288` and `ollama_num_ctx: 12288` while keeping `qwen2.5-coder:7b` as default.
  - Fix `config.py`, add `.gitignore` rules for `data/hh_autonomy_*.json`, clean `olx_outreach.py` and `hh_watcher.py`.
- [ ] **Step 4: Run targeted tests (`GREEN`)**
  Run `python -m unittest tests.test_config tests.test_portals -v` -> all pass.

---

### Task 2: Grounded Profile Loader, Ollama Fit Scorer & Humanized Cover Letter Validator (`scripts/hh_ai.py`)

**Files:**
- Create: `C:\Users\Abdulkhakim\Git-Projects\resume\scripts\hh_ai.py`
- Test: `C:\Users\Abdulkhakim\Git-Projects\resume\tests\test_hh_ai.py`

**Interfaces:**
- Produces:
  - `load_candidate_profile(master_path: Path | None = None) -> Dict[str, Any]`
  - `score_vacancy(vacancy: Dict[str, Any], profile: Dict[str, Any] | None = None, use_llm: bool = True, backend: str = "ollama") -> Dict[str, Any]` -> returns `{"score": int, "fit": bool, "cv_variant": str, "reason": str, "keywords": List[str]}`
  - `audit_cover_letter(text: str, company: str = "", position: str = "") -> Dict[str, Any]` -> returns `{"ok": bool, "issues": List[str]}` enforcing zero em-dashes (`—`), zero banned clichés, zero 3rd-person drift, zero placeholder leaks, length bounds (`250..1200`), and factual employer-role accuracy.
  - `generate_cover_letter(vacancy: Dict[str, Any], profile: Dict[str, Any] | None = None, backend: str = "ollama", description: str = "") -> Dict[str, Any]` -> returns `{"text": str, "source": "llm"|"template_fallback", "audit": Dict, "cv_variant": str}`
  - `main() -> int` supporting `--vacancy-id`, `--title`, `--company`, `--backend ollama|hermes|none`, `--db-path`, `--json`, `--help`.

- [ ] **Step 1: Write failing unit tests in `tests/test_hh_ai.py`**
  Test:
  1. `score_vacancy(..., use_llm=False)` scores `"Старший финансовый аналитик"` at Tier 1 high (`>= 70`, variant `financial_analyst`) and rejects `"Scrum-мастер"` / `"Директор по маркетингу"` below threshold (`< 55`).
  2. `audit_cover_letter` catches em-dashes (`—`), banned clichés (`"не просто ... а"`, `"бесспорно"`, `"к процветанию"`), 3rd-person hallucinations (`"пришел Абдулхаким"`, `"его опыт"`), wrong Ravnaq Bank role (`"финансовый аналитик в Ravnaq Bank"`), and passes a crisp 1st-person Russian cover letter mentioning real `Explorer Logistics` / `Ravnaq Bank` facts.
  3. `generate_cover_letter` with mocked failing/bad LLM retries once and falls back safely to a clean `humanizer`-verified template letter that passes `audit_cover_letter`.
- [ ] **Step 2: Run `python -m unittest tests.test_hh_ai -v` (`RED`)**
- [ ] **Step 3: Implement `scripts/hh_ai.py`**
- [ ] **Step 4: Run `python -m unittest tests.test_hh_ai -v` (`GREEN`)**

---

### Task 3: Autonomy Queue, Daily Cap & Spaced-Wave Pacing (`scripts/hh_queue.py`)

**Files:**
- Create: `C:\Users\Abdulkhakim\Git-Projects\resume\scripts\hh_queue.py`
- Test: `C:\Users\Abdulkhakim\Git-Projects\resume\tests\test_hh_queue.py`

**Interfaces:**
- Consumes: `Config`, `init_database`, `get_connection`, `score_vacancy`, `generate_cover_letter`.
- Produces:
  - `load_autonomy_state(state_path: Path | None = None) -> Dict[str, Any]` (tracks today's date, `applied_today`, `session_count`, recent timestamps)
  - `record_daily_apply(state_path: Path | None = None, count: int = 1) -> Dict[str, Any]`
  - `remaining_daily_quota(daily_limit: int = 200, state_path: Path | None = None) -> int`
  - `select_candidate_vacancies(db_path: Path | None = None, limit: int = 200, min_score: int = 55, queue_path: Path | None = None) -> List[Dict[str, Any]]` (queries unapplied active `hh.uz` rows ordered by `tier ASC, published_at DESC`, excludes items already marked `applied` / `skipped` / `needs_human` in queue JSON, scores fit deterministically first)
  - `upsert_queue_item(item: Dict[str, Any], queue_path: Path | None = None) -> None`
  - `main() -> int` supporting `--prepare`, `--limit`, `--min-score`, `--status`, `--reset-skipped`, `--db-path`, `--json`, `--help`.

- [ ] **Step 1: Write failing unit tests in `tests/test_hh_queue.py`**
  Test DB selection excluding applied vacancies and already-queued items, scoring priority (`Tier 1 Financial Analyst` ranked before `Tier 3 Operations`, mismatches excluded), daily quota rollover on new date, and cap enforcement (`daily_limit=200` stops cleanly at `0` remaining).
- [ ] **Step 2: Run `python -m unittest tests.test_hh_queue -v` (`RED`)**
- [ ] **Step 3: Implement `scripts/hh_queue.py`**
- [ ] **Step 4: Run `python -m unittest tests.test_hh_queue -v` (`GREEN`)**

---

### Task 4: Multi-Mode Visible Application Runner (`scripts/hh_apply.py` + `scripts/launch_hh_visible.ps1`)

**Files:**
- Create: `C:\Users\Abdulkhakim\Git-Projects\resume\scripts\hh_apply.py`
- Create: `C:\Users\Abdulkhakim\Git-Projects\resume\scripts\launch_hh_visible.ps1`
- Test: `C:\Users\Abdulkhakim\Git-Projects\resume\tests\test_hh_apply.py`

**Interfaces:**
- Consumes: `Config`, `hh_ai`, `hh_queue`, `update_application_status`, `refresh_dashboard` (`scripts/dashboard.py`), `log_event`.
- Produces:
  - `HHPageState` / `inspect_hh_page(url: str, page_text: str, selectors_present: Dict[str, bool]) -> str` (`"ready" | "captcha_or_login" | "already_applied" | "archived" | "unknown"`)
  - `SubmitResult` (`status`: `"applied" | "already_applied" | "archived" | "needs_human" | "captcha_paused" | "skipped" | "error"`, `detail`: str, `cv_variant`: str | None)
  - `ApplicationDriver` implementations:
    - `DryRunDriver` (for verified dry-run simulation & tests)
    - `EdgeSeleniumDriver` (visible `Edge` + `hh_main_session`, human scroll/read delays, auto-resume selection, questionnaire check `--on-questions defer|pause`, interactive CAPTCHA/login pause allowing live switch from `--confirm none` to `--confirm each` or quit)
    - `OfficialApiDriver` (`POST https://api.hh.ru/negotiations` with `HH_ACCESS_TOKEN`, handling `403 Forbidden` gracefully)
    - `AssistDriver` (visible Edge open + clipboard letter copy + user `Enter`)
  - `run_apply_session(...) -> Dict[str, Any]` managing wave pacing (`--wave-size 25`, `--wave-pause-sec 900`), `--daily-limit 200`, `--mode browser|api|assist`, `--confirm none|batch|each`, `--harvest-queries`, live status output, DB updates + dashboard sync.
  - `main() -> int` supporting `--help`, `--json`, `--dry-run`, `--mode`, `--confirm`, `--on-questions`, `--limit`, `--daily-limit`, `--wave-size`, `--wave-pause`, `--min-delay`, `--max-delay`, `--min-score`, `--backend ollama|hermes|none`, `--profile-dir`, `--harvest-queries`, `--db-path`.

- [ ] **Step 1: Write failing unit tests in `tests/test_hh_apply.py`**
  Test:
  1. `inspect_hh_page` detects CAPTCHA/ddos-guard/login URLs, archived vacancies, already-applied text (`"Вы откликнулись"`), and ready vacancies accurately.
  2. Mocked `run_apply_session` with `--confirm none`: marks archived row `is_active = 0` in DB, syncs `already_applied` to DB `'applied'`, defers `needs_human` without crashing, pauses on CAPTCHA and supports simulated live switch to `'each'` mode, records `'applied'` + incremented daily quota + refreshes dashboard.
  3. `OfficialApiDriver` returns clean actionable `forbidden` result on mocked `HTTP 403` and `applied` on mocked `HTTP 201`.
  4. `hh_apply.py --dry-run --limit 3 --backend none --json` CLI smoke run exits cleanly with `0` or `2`.
- [ ] **Step 2: Run `python -m unittest tests.test_hh_apply -v` (`RED`)**
- [ ] **Step 3: Implement `scripts/hh_apply.py` and `scripts/launch_hh_visible.ps1`**
- [ ] **Step 4: Run `python -m unittest tests.test_hh_apply -v` (`GREEN`)**

---

### Task 5: End-to-End Multi-Pass Verification & Visible Foreground Launch

- [ ] **Step 1: Update `scripts/README.md` and `tests/` if needed, run full `python -m unittest discover tests -v`** -> 100% pass, zero failures/skips.
- [ ] **Step 2: Pass 1–2 Live Ollama + DB Dry-Run Verification**
  Run `hh_queue.py --prepare --limit 10` / `hh_apply.py --dry-run --limit 5 --backend ollama --json` on real `db/positions.db` (non-mutating / clean rollback or dry-run) and manually audit every generated Russian cover letter for natural tone, factual accuracy against `master/resume.md`, and zero AI clichés.
- [ ] **Step 3: Live Non-Submitting Visible Edge Profile Smoke Check**
  Verify visible `Edge` opens cleanly with `C:\Users\Abdulkhakim\.gemini\hh_main_session`, loads `https://tashkent.hh.uz` without driver errors or immediate crash, and confirm session state.
- [ ] **Step 4: Foreground Visible Launch (`launch_hh_visible.ps1`)**
  Launch the verified visible PowerShell runner window (`Start-Process` foreground console) + visible Edge window directly on user's desktop so the user watches scoring, humanized letter writing, wave pacing, and real browser actions in real time.
