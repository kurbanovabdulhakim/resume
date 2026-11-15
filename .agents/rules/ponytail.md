---
title: Ponytail Minimalist Ladder Rule
description: Enforces the 7-rung minimalist ladder, YAGNI, standard library prioritization, and anti-bloat principles.
status: active
category: rule
last-verified: 2026-11-08
---

# Ponytail — Pragmatic Senior Dev Directives

> **Core Insight:** Agent failure is proportional to trajectory length. The best code is the code you never wrote. The best tool call is the one the agent never had to reason about.

---

## 1. The 7-Rung Minimalist Ladder

Before writing any new code or abstractions, stop at the **first rung** that solves the requirement:

1. **Does this need to exist at all? (YAGNI):** Reject speculative requirements and hypothetical edge cases immediately.
2. **Already in this codebase? (Reuse):** Inspect existing utilities in `scripts/` (`config.py`, `logger.py`, etc.) before creating new scripts.
3. **Does the Standard Library do it? (Stdlib First):** Use Python stdlib (`sqlite3`, `pathlib`, `json`, `re`, `argparse`, `datetime`) before reaching for third-party libraries.
4. **Does a native CLI or platform tool cover it?:** Prefer native SQLite CLI, Git, or OS tools over complex custom wrappers.
5. **Does an already-installed package solve it?:** Check `requirements.txt` before installing anything new. Never run global pip installs.
6. **Can it be a simple function or one-liner?:** Procedural, readable functions beat complex multi-layer OOP hierarchies.
7. **Only then: write the minimum code that works.**

---

## 2. Bug Fixes: Root Cause, Never Symptoms

- A test error or bug report shows a symptom.
- Trace callers back to find the single shared root cause before applying patches.
- Never write shallow caller-specific patches that leave sister paths broken.

---

## 3. Hard Boundaries & Safety

- **Structured Logging:** Operational events must be logged to `logs/YYYY-MM-DD.jsonl` via `scripts/logger.py`.
- **Secrets Protection:** Never hardcode account credentials, auth tokens, session cookies, or personal identity numbers.
- **Verification Before Completion:** Always verify changes by running test suites (`python -m unittest discover tests`) or running target scripts with `--json`.
- **Deletion Over Addition:** Prefer removing dead code and redundant templates over creating new ones.
