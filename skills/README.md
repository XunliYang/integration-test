# Skills Overview

Agent skills for the OpenAN integration-testing workflow. Each skill lives in its own directory with a `SKILL.md` (the machine-readable contract) plus `references/`, `scripts/`, `templates/`, and `assets/` as needed. Invoke a skill by name (e.g. `/test-cases-generator`) or let the agent pick it up automatically from your request.

## Skills at a Glance

| Skill | What It Does | Typical Trigger |
|-------|--------------|-----------------|
| [test-cases-generator](#test-cases-generator) | Orchestrates the full generate → boundary-check → review → revise loop (max 3 epochs) for FIT and/or DFX case CSVs | "generate test cases with review" |
| [feature-level-test-cases-gen](#feature-level-test-cases-gen) | Generates FIT case CSVs (business functional correctness only) | "generate FIT cases" |
| [dfx-test-cases-gen](#dfx-test-cases-gen) | Generates DFX case CSVs (non-functional: DFT/DFD/DFS/DFR/DFP/DFNS/DFC) | "generate DFX cases" |
| [test-cases-reviewer](#test-cases-reviewer) | Reviews case CSVs against the 16-column template, checklist, and FIT/DFX attribution rules | "review these test cases" |
| [e2e-test-code-gen](#e2e-test-code-gen) | Converts a reviewed CSV into executable tests (pytest / JUnit5 / Vitest+Playwright / bats) | "generate test code from this CSV" |
| [e2e-test-runner](#e2e-test-runner) | Actually runs the tests (4 phases: pre-check → preparation → execution → cleanup) | "run the tests of repo X" |
| [e2e-failure-analyzer](#e2e-failure-analyzer) | Analyzes failures: extracts evidence, clusters, classifies root cause (5-class) | "analyze this failure log" |
| [e2e-test-regression](#e2e-test-regression) | Fixes test code for items classified `E2E_CODE_BUG` | "fix the test code per this report" |
| [e2e-issue-verifier](#e2e-issue-verifier) | Full-stack failure verification: minimal rerun, root-cause localization, Issue/PR write-back and handoff | "verify this e2e failure / handle this Issue" |
| [smoke-test](#smoke-test) | Not a skill — a smoke-test guide with sample inputs to validate the other skills | — |

## The Pipeline at a Glance

```text
requirements/design/source code
        │
        ▼
┌─ test-cases-generator (orchestrator) ──────────┐
│  · feature-level-test-cases-gen  → FIT CSV     │
│  · dfx-test-cases-gen            → DFX CSV     │
│  · boundary check + dedup                      │
│  · test-cases-reviewer (review, ≤3 epochs)     │
└────────────────────────────────────────────────┘
        │  reviewed 16-column CSV
        ▼
e2e-test-code-gen  →  tests/README.md → executable test code
        │
        ▼
e2e-test-runner    →  structured results (JUnit XML / reports)
        │  on failure
        ▼
e2e-failure-analyzer  →  root-cause classification
        │
        ├─ E2E_CODE_BUG  → e2e-test-regression (fix test code)
        ├─ SOURCE_BUG    → github-issue-creator (new Issue)
        └─ verify / close the loop → e2e-issue-verifier
```

All case CSVs use the fixed **16-column** header (official 15 columns + `Component Deps` as the 5th column, UTF-8 with BOM):

```csv
Milestone,Case Name,Case ID,Module,Component Deps,Requirement Link,Case Type,Priority,Precondition,Steps,Expected Result,Automatable,Automated Test,Dev Owner,Test Owner,Notes
```

---

## test-cases-generator

**Full-pipeline orchestrator.** Chains generation, FIT/DFX boundary checking, and review into a closed "generate → check → review → revise" loop (hard limit: 3 epochs). It does not write cases itself — it drives the three sub-skills below and delivers the final CSV plus review/boundary reports.

- **Inputs (hard gate):** at least one feature material (proposal/design/API doc/manual/source code), generation scope (`FIT` / `DFX` / `FIT+DFX`), feature/module name. Optional: requirement links, target repo, milestone, existing FIT CSV, final/intermediate output paths.
- **Outputs:** final CSV (no `epoch-` suffix), review report, boundary-check report, per-epoch intermediates under `intermediate/`, full-pipeline summary.

```text
/test-cases-generator

Generate FIT+DFX test cases from docs/xxx-proposal.md and the registry-center source code, with review.
Feature/module name: agent-registration
Target repo: registry-center
Milestone: 26-winter
Final FIT: outputs/registry-center_agent-registration-fit-test-cases.csv
Final DFX: outputs/registry-center_agent-registration-dfx-test-cases.csv
```

## feature-level-test-cases-gen

**Generates FIT (Feature-level Integration Test) case CSVs.** Business functional correctness only: deployment readiness, main paths, functional config changes, business state transitions, business-level negatives. Non-functional scenarios (self-healing, probes/logs/metrics, performance, security, compatibility) are excluded — they belong to DFX.

- **Inputs (required):** at least one feature material + feature/module name. Optional: source code, reference CSV, requirement links, milestone, output path.
- **Output:** 16-column FIT CSV (`outputs/<repo>_<feature>-fit-test-cases.csv` by default), information-gap list, coverage summary.

```text
/feature-level-test-cases-gen

Generate FIT cases from docs/xxx-proposal.md and the registry-center source code.
Feature name: agent-registration
Milestone: 26-winter
Output to outputs/registry-center_agent-registration-fit-test-cases.csv
```

## dfx-test-cases-gen

**Generates DFX (Design for X) non-functional case CSVs.** Covers the applicable subset of the seven dimensions — DFT (testability), DFD (diagnosability), DFS (serviceability), DFR (reliability), DFP (performance), DFNS (security), DFC (compatibility) — based strictly on what the materials support; padding all seven is forbidden. Never duplicates FIT business scenarios.

- **Inputs (required):** at least one feature material + feature/module name. Optional: existing FIT CSV (for dedup), source code, reference CSV, milestone.
- **Output:** 16-column DFX CSV with `dfx_type:DFx` in Notes, information-gap list, DFX-type coverage summary.

```text
/dfx-test-cases-gen

Generate DFX cases from docs/xxx-proposal.md, the design doc, and the registry-center source code.
Feature name: agent-registration
Milestone: 26-winter
Output to outputs/registry-center_agent-registration-dfx-test-cases.csv
```

## test-cases-reviewer

**Reviews case CSVs** against the 16-column template, the review checklist, and the FIT/DFX attribution criteria; supports FIT-only, DFX-only, or full-set tables, per-row guide selection for mixed tables, counterpart-CSV cross-deduplication, and DFX seven-dimension coverage analysis.

- **Inputs (required):** the case file. Optional: classification (FIT/DFX/full set), counterpart CSV, boundary-check conclusion, target milestone, requirement materials, output path.
- **Output:** Markdown review report (`outputs/<filename>-review-report.md` by default) with mandatory-item failures and remediation suggestions, plus a conversation summary.

```text
/test-cases-reviewer

Review outputs/registry-center_agent-registration-dfx-test-cases.csv
Case classification: DFX
Target milestone: 26-winter
Requirement materials: docs/xxx-proposal.md
```

## e2e-test-code-gen

**Converts a reviewed CSV into executable test code** in the target repo. Supports four language profiles driven by the `language_profile` key in Notes: Python (pytest), Java (JUnit5), JS (Vitest+Playwright), Shell (bats). README-first: generates the test package's `tests/README.md` (architecture + execution scheme) and generates code only after user confirmation. Refuses and lists missing items when orchestration inputs are insufficient.

- **Inputs (required):** reviewed 16-column CSV, target repo, orchestration inputs (service topology, env-var contract, etc.).
- **Output:** `tests/README.md` + test code under the target repo's `e2e/<feature>/` (Java: `src/test/java`), case-ID ↔ test-file mapping table.

```text
/e2e-test-code-gen

Reviewed CSV: outputs/registry-center-agentcard-fit-cases.csv
Target repo: openan/registry-center (local path C:\...\registry-center)
Scope: all FIT cases + P0/P1 DFX cases
```

Helper scripts (parse/validate only — they do not write tests):

```bash
node scripts/parse-test-cases.mjs <csv-path> [--ids ...] [--priority P0,P1]
node scripts/build-codegen-plan.mjs [config-path]
node scripts/run.mjs [config-path]
```

## e2e-test-runner

**Executes the tests** of a target OpenAN repo end to end: pre-check (toolchain per language) → preparation (env vars, docker-compose, health checks) → execution (language-specific commands, real-time logs, first failure reported verbatim immediately) → cleanup (stop only what it started, archive artifacts to `.test-output/<timestamp>/`).

- **Output:** structured JSON (repo, lang, command, exitCode, failedCases) designed for consumption by `e2e-failure-analyzer`.
- **Hard constraint:** never modifies source or test code.

```text
/e2e-test-runner

Run registry-center's tests. The repo is at <local path>; run only the integration layer.
If the environment fails the pre-check, report what is missing honestly.
```

## e2e-failure-analyzer

**Analyzes test failures** from logs, JUnit XML, Playwright reports, screenshots, traces, or Issue links. Extracts evidence, clusters by error signature, and classifies each cluster as `E2E_CODE_BUG`, `SOURCE_BUG`, `ENV_INFRA`, `FLAKY_TIMING`, or `INSUFFICIENT_INFO` with confidence and cited evidence.

- **Output:** Markdown conclusions table + follow-up invocation text (issue-creator draft for SOURCE_BUG, fix instructions for E2E_CODE_BUG, etc.).
- **Hard constraint:** read-only — never executes commands, modifies code, or creates Issues.

```text
/e2e-failure-analyzer

Analyze this failure log: <path>/sample-failure.log
Background: registry-center's integration tests; the log is in the file.
```

## e2e-test-regression

**Fixes test code** for items classified `E2E_CODE_BUG` in an `e2e-failure-analyzer` report. Makes minimal, reversible changes (one commit/hunk per cluster), verifies with the report's commands, and produces a fix report.

- **Prerequisites (refuses otherwise):** the report exists; every item is `E2E_CODE_BUG`; the target repo's git tree is clean.
- **Hard constraints:** never modifies the product source; skips `SOURCE_BUG` / `ENV_INFRA` / `FLAKY_TIMING` / `INSUFFICIENT_INFO` items; no git commit/push without explicit authorization.

```text
/e2e-test-regression

Process this analysis report: <path>/sample-analysis-e2e-code-bug.md
Target repo: <local path>
```

## e2e-issue-verifier

**Full-stack failure verification and closure.** Parses the failure/Issue, retrieves Issue context via GitHub MCP, extracts and clusters evidence, generates a minimal verification command (Playwright locally; pytest/Maven/bats locally or via SSH for backend), runs it, localizes root cause jointly from source code and real environment state, determines fix status, and drafts Issue/PR write-backs.

- **Handoff rules:** fixes → `github-issue-fixer`, new Issues → `github-issue-creator`; both require explicit user authorization first.
- **Input gate:** stops and asks when only "the test failed" is provided, or when a required SSH environment is not specified.

```text
/e2e-issue-verifier

Analyze and verify this failure: target repo <path>, backend Python case
FIT-registry-center-agentcard-001 fails when running
`python -m pytest skills/smoke-test/fixture/test_agent_register.py -q`,
assertion 200 != 201.
```

## smoke-test

**Not a skill** — a validation suite for the skills above. Contains `sample-cases.csv`, sample failure logs and analysis reports, and a fixture pytest file, together with step-by-step pass criteria for each skill (including negative tests for STOP/refusal behavior). Use it after installing or modifying skills to confirm they behave per their `SKILL.md` contracts. See [smoke-test/README.md](smoke-test/README.md).
