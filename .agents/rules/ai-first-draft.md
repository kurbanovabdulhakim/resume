---
title: AI-First Development Rules
description: Mandatory guidelines for AI agents operating within the repository
status: active
category: rule
tags: [ai-first, agent, automation]
last-verified: 2026-08-17
trigger: always_on
---
# AI-First Development & Maintenance Rules

These rules define how AI agents (Antigravity, Cursor, Hermes) must operate within this infrastructure to ensure a self-healing, machine-readable, and autonomous environment.

## 1. Documentation as Single Source of Truth (SSOT)

- **YAML over Markdown**: For structured data, prefer YAML files.
- **Zero-Stale-Docs**: Every code change or infrastructure mutation **must** be accompanied by an update to the relevant documentation.
- **Secrets Hygiene**: Never store credentials (passwords, API keys) in documentation or code. Reference them as "from `.env`" or "from host config".

## 2. Autonomous Maintenance (The "Hermes" Principle)

- **Idempotent Scripts**: All maintenance scripts must be idempotent.
- **Self-Healing**: Prefer configurations that auto-recover over manual instructions.

## 3. Planning & Execution

- **Verification Gates**: Every plan MUST include concrete verification steps. Confirming "success" without a verification gate is a failure of the rule.

## 4. AI-Native Code & Security

- **No Hardcoded Secrets**: Use `.env` or system environment variables. Audit all scripts for leaked keys before commitment.
- **Self-Documenting Code**: Write scripts with `--help` flags and JSON output for cross-agent consumption.
- **Traceability**: Every script and config change must be searchable and linked to a decision.

## 5. Failure Behavior

- **Halt and Report**: If a verification gate fails or an error occurs, **halt immediately**. Report the error, current state, and relevant logs.
- **No Blind Retries**: Do not attempt the same failing action more than twice without human intervention.
- **Fail-Safe/Rollback**: If a critical service is impacted, prioritize rolling back to the last known-good state before troubleshooting.
