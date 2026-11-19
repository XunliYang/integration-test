# Orchestration Center Test Plan (Sandbox Verification)

> Version: v0.3 | Date: 2026-11-19 | Author: Orchestration Center WG test owner (Zhoujie628) | Review status: Pending review
> Related feature proposal: [integration-test#11](https://github.com/project-openan/integration-test/issues/11) (sandbox verification, upstream [orchestration-center#76](https://github.com/project-openan/orchestration-center/issues/76)) | Version milestone: `26-winter`
> Archive path: `docs/plans/26-winter/`

---

## 1. Overview

### 1.1 Purpose

Verify that `orchestration-center` delivers the 26-winter sandbox-verification capability covered by this plan, and that it meets the Feature Integration Test (FIT) entry and exit quality requirements:

- **Sandbox-level verification with a generated stub default agent** (topic `sandbox-verify`, issue #11, dev status "Coding Finished"): before real execution, a dry-run validates PSOP structure integrity, step reachability, context passing and exception paths, using stub agents generated from the registered AgentCards instead of contacting real agents. This topic is runnable and automated this cycle and carries both P0 cases.

### 1.2 Scope

**In scope** (aligned with the integration testing boundaries in Framework §5.2):

- Cross-module calls between `orchestration-center` and `registry-center` (AgentCard registration, listing and resolution)
- The sandbox dry-run lifecycle over the internal API: start, poll, read report and events, delete, plus the Stub Template contract
- Business-level negatives of the dry run: structurally invalid PSOP (cycle), unregistered task agent, stub error scenario, invalid template payload

**Out of scope**:

- **Role-based orchestration (tracking issue #10, upstream orchestration-center#74)**: the feature is at "Design & Coding 40% - handover not ready" and its design still needs TSC review. Per Framework §4.2 (Stage 1: "Test design may begin only after the feature proposal has passed TSC review"), no test design for #10 is included in this plan. When #74 hands over, the role-mapping case design is submitted as a follow-up PR against this directory and this plan is updated.
- Module-internal unit tests of the `orchestration-center` repository (for example `tests/test_sandbox_validator.py`)
- Frontend rendering of the workflow designer graph (frontend manual/UI automation)
- Performance, stress, long-duration stability, fault-injection, security and compatibility probes - these belong to the DFX plans (Framework §10); only functional correctness is asserted here
- Real business output of domain agents (LLM-generated content is never asserted; only status, event and structural fields)
- DAG-traversal and per-subtask dispatch internals owned by the workflow engine SDK (the `workflow-engine-sdk` feature, issue #13)

### 1.3 References

| Document | Link/Path |
|------|----------|
| OpenAN Integration Testing Process and Framework | `docs/OpenAN Integration Testing Process and Framework.md` (§4.2, §5.2, §6, §7, §8) |
| OpenAN Test Checklist | `docs/openan-test-checklist.md` |
| Feature requirement | integration-test#11; upstream [orchestration-center#76](https://github.com/project-openan/orchestration-center/issues/76) |
| Orchestration Center API surface | `orchestrate/server/frontend_support_server.py` (internal `/rest/v1/orchestrate/*`), `orchestrate/server/external_api.py` (external `/api/v1/*`), `orchestrate/server/sandbox_api.py` (sandbox routes) |
| Orchestration Center design notes | `orchestration-center/AGENTS.md`, `orchestration-center/README.md` |
| PSOP data model | `orchestrate/core/model/psop.py` |
| Case table (this milestone) | `docs/plans/26-winter/testcases-orchestration-center.csv` |
| Tracking issue | [integration-test#11](https://github.com/project-openan/integration-test/issues/11) |

---

## 2. Objects Under Test

| Component | Repository | Version/Build | Test Layer | Notes |
|------|------|----------|----------|------|
| Orchestration Center | `orchestration-center` | `<tag/commit>` | FIT (module under test) | PSOP storage and retrieval, A2A-T dispatch channel, SSE event relay, execution records, sandbox verification service |
| Registry Center | `registry-center` | `<tag/image digest>` | FIT (dependency) | AgentCard registration and listing; the source of the AgentCards the sandbox resolves |
| Sample agents (`mockagent`) | `openan-demo` `mockagent` package | `<tag>` | FIT (dependency) | The Host Agent registration only; sandbox cases never start domain agent endpoints |
| Workflow Engine SDK | `workflow-engine-sdk-python` (`workflow_engine` package, distribution `workflow_exec_engine 0.1.1`) | `<version>` | Execution engine reached through the Host Agent | Owns DAG traversal and per-subtask dispatch; emits `task_request`/`task_status_changed` events carrying `data.agent` |
| Portal / workflow designer | `openan-portal`, `workflow-designer` | `<tag>` | Out of scope | Not exercised by these cases |

---

## 3. Test Strategy

### 3.1 Test Layers

| Layer | Executor | Scope |
|------|--------|------|
| FIT | Orchestration Center WG | Integration correctness of the sandbox dry run against a real Registry Center |
| DFX | Integration Testing WG | Logs/metrics/self-healing/performance/security probes of the same feature (not in this plan) |
| SIT | Integration Testing WG | Release-level combinations (for example the SPN complaint closed loop) that reuse these primitives |

### 3.2 Test Types

Aligned with Framework §10; applicable to this feature:

- [x] Functional testing (dry-run report content, context passing, template contract, PSOP round-trip)
- [x] Exception testing (business negatives: invalid structure, unregistered agent, stub error scenario, skill mismatch, invalid template payload)
- [ ] Performance testing / [ ] Stress testing / [ ] Long-duration stability / [ ] Reliability-fault injection
- [ ] Security testing / [ ] Compatibility testing / [ ] Deployment mode testing

### 3.3 Test Method

- Real-environment execution: `orchestration-center` and `registry-center` are deployed (K8s workload cluster or compose stack); only the LLM is externalized. No service is mocked at the integration layer.
- Sandbox cases use the dry-run service, which generates stub responses in-process (`StubAgentRuntime`) from the registered AgentCards; domain agent endpoints are deliberately **not** started, which proves that no real agent is contacted.
- Assertions are deterministic and never touch agent-generated text.
- Cleanup is mandatory and is the last step of every case: delete PSOP workflows, execution records, sandbox verifications, saved stub templates and test AgentCards; every cleanup step has its own assertion (re-query returns 404 / template count 0 / AgentCard re-query returns 200 with an empty list).
- Prohibitions: no `sleep`-based synchronisation (poll the verification/execution resource with framework wait/retry); no shared mutable state between cases; no assertion-free steps.

### 3.4 Automation Strategy

- The 8 cases (6 P0/P1 plus 2 P2) are automated in pytest under `e2e/orchestration-center/` with `language_profile:python`; 100% of P0/P1 cases are automated, as the contract requires.
- `execution_strategy` layering: `smoke` for the two P0 cases (`sandbox-verify-001`, `sandbox-verify-002`), `full` for the other 6.
- Assertions are deterministic: HTTP status codes, envelope `code`/`status`/`data` fields, report field values (`verdict`, `mode`, `verification_scope`, `route_policy`, `execution_path`, `context_trace`, `stub_interactions`, `static_checks`), PSOP JSON and dispatch counts.
- Failed cases are archived as issues with the sandbox report JSON (or the SSE transcript), the request payload and backend logs attached.

---

## 4. Test Scenarios

| Scenario ID | Scenario Description | Components | Priority | Notes |
|---------|---------|----------|--------|-------|
| SCN-orchestration-center-001 | Default stub dry-run of a valid PSOP produces a `pass` report with all static checks and generated stub interactions | orchestration-center, registry-center | P0 | Case `sandbox-verify-001`; the core dry-run path of issue #11 |
| SCN-orchestration-center-002 | Context passing: a SelfLoop merge step receives both parallel branch outputs, verified through `context_trace` | orchestration-center, registry-center | P0 | Case `sandbox-verify-002` |
| SCN-orchestration-center-003 | Structure integrity gate: an invalid PSOP is rejected by static validation and no stub execution happens | orchestration-center, registry-center | P1 | Case `sandbox-verify-003` |
| SCN-orchestration-center-004 | Exception paths in the dry-run: stub error scenario report, unregistered task agent, stub template override and invalid template payloads | orchestration-center, registry-center | P1-P2 | Cases `sandbox-verify-004` to `sandbox-verify-007` |
| SCN-orchestration-center-005 | Editor snapshot dry-run: an unsaved PSOP is verified without persistence and a malformed snapshot is rejected | orchestration-center, registry-center | P2 | Case `sandbox-verify-008` |

---

## 5. Test Case Design

### 5.1 Numbering Rules

- FIT cases: `[FIT-orchestration-center-{topic}-{3 digits}]`, for example `[FIT-orchestration-center-sandbox-verify-001]`
- Topic used by this plan: `sandbox-verify` (001-008); the sequence is continuous from 001
- Test file naming (Framework §6.1): `e2e/orchestration-center/test_sandbox_verify.py`; test functions named `test_action_expected_result` (for example `test_run_valid_psop_returns_pass_report`)

### 5.2 Priority Definitions

| Priority | Definition | Pass Rate Requirement |
|--------|------|-----------|
| P0 | The core execution path of the tracked feature (dry-run pass; context passing) | 100% (TRR entry and release gate) |
| P1 | Main functionality coverage and business negatives of the feature | 100% |
| P2 | Complex variants and payload-level negatives | >= 80% |

Case distribution (must equal the CSV): 8 cases - **P0: 2, P1: 4, P2: 2**; `sandbox-verify` 8 cases (P0 2 / P1 4 / P2 2, all `Automatable=Yes`). Case types: Functional Test 5, Exception Test 3. Execution strategy: `smoke` 2, `full` 6.

### 5.3 Label Dimensions

Every case carries, in code: `feature=orchestration-center`, `environment=with-workload-cluster`, `components` (derived from `Component Deps`, `registry-center` for every row), `priority`, `execution` (`smoke` for the two P0 cases, `full` otherwise), and `skip-temporarily` only with an issue link. `language_profile:python` and `protocol_primitive` (`Task-T` for the real-dispatch protocol case, `none` for the sandbox/REST rows) are recorded per case in the CSV Notes.

### 5.4 Case Table

The 8 cases are carried in `docs/plans/26-winter/testcases-orchestration-center.csv` (fixed 16 columns, UTF-8, RFC4180 quoting). Every row's Requirement Link carries the component requirement issue (orchestration-center#76) joined with the integration-test tracking issue (#11). Field rules follow `docs/templates/testcases-template-fields.md`.

| Topic | Channel under test | Cases | Automated this cycle |
|------|------|------|------|
| `sandbox-verify` | `POST /rest/v1/orchestrate/sandbox/{workflow_id}/run`, `GET/DELETE /rest/v1/orchestrate/sandbox/verifications[/{id}]`, `GET .../verifications/{id}/events`, `GET/PUT /rest/v1/orchestrate/sandbox/templates/{workflow_id}` | 001-008 | Yes - 8 of 8 |

Requirement coverage: integration-test#11 -> `sandbox-verify-001` to `sandbox-verify-008` (8 cases, executable). Upstream orchestration-center#76 is recorded in the plan header for the requirement traceability matrix. Tracking issue #10 (role-based orchestration) has no cases in this plan by design; see §1.2.

### 5.5 Case Design Requirements

- Every case includes preconditions (environment/data state only, max 6 items), numbered steps whose last step is the cleanup action, `see result N` markers, and one machine-checkable expected result per marker.
- Sandbox assertions use the report contract verified in `orchestrate/sandbox/models.py` (`SandboxRunReport`) and `orchestrate/validation/sandbox_validator.py` (`SandboxCheck`, check ids `structure.*` and `agents.*`).
- Cases are independent: each one creates its own PSOP, AgentCards and verifications, and deletes them in the final step. Session-level fixtures are limited to read-only configuration (base URLs, tokens).
- The sandbox cases require a **non-empty** Registry Center: `get_agent_cards()` returns `404 "No available agents found"` when the registry lists nothing (`orchestrate/server/response_utils.py`), and the dry-run start route propagates that status.

---

## 6. Test Environment and Data

### 6.1 Environment Topology

| Item | Value |
|----|------|
| Deployment mode | K8s workload cluster (Helm) or the compose stack; both give the same two service endpoints |
| Orchestration Center | `http://<host>:5001`, `persistence_mode=file` (files under `data/workflow_storage/`), `agent_registry_url` pointing at Registry Center |
| Registry Center | `http://<host>:5000`, token-protected `/rest/v1/registry-center/*` (only `/keys` bypasses the token middleware; registration requires an administrator or vendor-agent credential) |
| Sample agents | Host Agent registered as `Host Agent` (config key `workflow_host_agent_name`); domain agents are not needed |
| Sandbox storage | Reports `data/workflow_storage/sandbox/reports/<verification_id>.json`, templates `data/workflow_storage/sandbox/templates/<workflow_id>.json` |
| Environment provider | Integration Testing WG |

### 6.2 Dependent Services

| Dependency | Configuration | Notes |
|------|---------|------|
| Registry Center | `agent_registry_url`, `agent_registry.token_env=REGISTRY_ACCESS_TOKEN` (see `etc/conf/server.conf.example`) | Required by every sandbox case (AgentCard resolution) |
| Orchestration Center auth | Admin account plus a Bearer session token from `POST /rest/v1/orchestrate/auth/login`; the middleware protects `/rest/v1/orchestrate` and `/psops` (`orchestrate/server/auth.py`) | Required by every internal-API step |
| LLM endpoint | `etc/config/models.yaml` + `.env` keys, or a mock endpoint | Not used by these cases (PSOPs are created directly, not generated from intent), so no case depends on LLM output |
| Persistence backend | `persistence_mode=file` for FIT; PostgreSQL/MySQL run the same handlers | Sandbox sessions and templates are file-backed in all modes |

### 6.3 Test Data

- AgentCard fixtures: sandbox agents `agent-a`/`agent-b` (Task-T, matching skills), one unregistered name `missing-agent`.
- Agent processes: the `openan-demo` `mockagent` scenario package, or the in-repo samples started with `python -m samples.start_agents_server` from the `orchestration-center` repository. Only the Host Agent registration matters; the sandbox cases never start domain agent endpoints.
- PSOP fixtures: linear 2-step, parallel 2-branch plus SelfLoop merge, cyclic (invalid), missing-agent, and an unsaved editor snapshot `draft-workflow-001`.
- Stub template fixtures: step-scoped (`step` + `subtask_index`), agent-scoped, invalid-field, out-of-range `delay_ms`, and 200/201 entry boundary lists.
- All assets are generated by fixtures at runtime and deleted in the case cleanup step; no fixture is committed with real credentials.

### 6.4 Environment Variables

`OC_BASE_URL`, `REGISTRY_BASE_URL`, `OC_ACCESS_TOKEN`, `REGISTRY_ACCESS_TOKEN`, `AGENT_CARD_ORG`, `HOST_AGENT_NAME`, `A2AT_LLM_*` (only if sample agents are started), `USE_MOCK_LLM`. New variables introduced by this plan must be synchronised to `e2e/.env.template` and documented in the e2e README; secrets never appear in tracked files (Framework §6.6).

---

## 7. Entry and Exit Criteria

| Gate | Criteria | Source |
|------|------|------|
| TRR entry (into FIT) | P0/P1 pass rate = 100% over the 6 automatable P0/P1 cases (`sandbox-verify-001` to `sandbox-verify-006`), P2 >= 80% over the P2 cases (`sandbox-verify-007`, `sandbox-verify-008`), unit tests of the module not decreasing, image deployable, cases merged | Framework §8.1 |
| FIT exit | Overall pass rate >= 95% over the automatable cases, every failed case archived as an issue with `skip-temporarily`, report reviewed by the Integration Testing WG | Framework §8.2 |
| SIT exit / release entry | SIT pass rate = 100% with no skips, 7x24h without P0/P1 failures, install/upgrade/rollback passed, no open P0 (P1 only with workarounds) | Framework §8.3 |

Feature-specific exit condition: the two P0 cases (`sandbox-verify-001`, `sandbox-verify-002`) must pass unattended in `smoke` on the release candidate image before TRR.

---

## 8. Defect Management

- Severity and SLA per Framework §9.1 (P0: 24h response / fix in the current release; P1: 3 business days; P2: next release).
- Each failed case is archived as an issue containing the sandbox report JSON (or the SSE transcript), the execution record, the request payload and backend logs.
- Fix PRs must add a regression case to the matching topic and re-run all cases of this feature (8 this cycle).
- A case that fails because the promised behaviour is not implemented yet is recorded as a product gap, not as a case defect.

---

## 9. Schedule and Responsibilities

| Milestone | Date | Owner | Deliverable |
|------|------|--------|--------|
| Test plan review approved | 2026-11-25 | Integration Testing WG | This plan merged into `docs/plans/26-winter/` |
| Case writing completed | 2026-12-05 | Zhoujie628 | `testcases-orchestration-center.csv` + automation for the 8 `sandbox-verify` cases under `e2e/orchestration-center/` |
| TRR review | 2026-12-12 | Integration Testing WG | TRR conclusion (Test Checklist Chapter 1); gate set = the 6 automatable P0/P1 `sandbox-verify` cases |
| FIT completed / report review | 2026-12-18 | Zhoujie628 | Test report under `docs/reports/26-winter/` |

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|------|---------|
| **Issue #10 (role-based orchestration) is out of scope this cycle**: its design has not passed TSC review and the role abstraction does not exist in the code (`Task` in `orchestrate/core/model/psop.py:45-51` still requires `agent`, no role field; `orchestrate/runtime/exec_engine.py` has no role/instance-mapping logic) | No FIT coverage for #10 until handover; the tracking issue must not be closed on this plan's account | The tracking issue #10 records the handover condition; when #74 lands, role-mapping case design is submitted as a follow-up PR and this plan is updated in the same change (Framework §4.2) |
| Sandbox routes are internal-only (`/rest/v1/orchestrate/sandbox/*`); they are not exposed on `/api/v1` | Automation must use the internal API and therefore needs an account session token; an external-API health check would misleadingly report the feature as absent | Cases use the internal API with a Bearer token; the fact is pinned by `tests/test_sandbox_api.py::test_sandbox_routes_are_not_exposed_by_external_api` |
| The dry-run requires a non-empty Registry Center (otherwise `404 "No available agents found"`), so it cannot run as a pure stub-only offline dry-run | Sandbox cases fail for the wrong reason in a bare environment | Every sandbox case lists `registry-center` in `Component Deps` and registers its AgentCards in the case; the precondition states that agent endpoints are not started, which preserves the "no real agent contacted" property |
| Stub templates saved with `PUT /sandbox/templates/{workflow_id}` are **not** automatically applied to a run; the run uses the `templates` array of the request body | A reviewer could expect persisted templates to drive the next dry-run | Case `sandbox-verify-006` asserts both behaviours explicitly (persistence via GET, application via the request body) so the actual contract is locked |
| Unstable or unreachable external LLM / sample agents | Flaky cases | No executed case depends on LLM output (PSOPs are created through the API); sandbox cases need no domain agent endpoint |
| Sandbox timeout and concurrency are code defaults (`sandbox_run_timeout_seconds=60`, `sandbox_max_concurrent_runs=4`) and are absent from `server.conf.example` | A slow environment produces `status=timed_out` instead of a verdict, and parallel cases queue | Cases poll with a bounded retry budget and never assert wall-clock time; the two keys are documented in the e2e README and may be raised in the FIT values file |
| Registry token / mTLS material is environment-specific | Registration steps fail before any feature logic runs | Tokens are injected via environment variables only (Framework §6.6); `client_verify_server` and CA material follow the deployment profile |

---

## 11. Deliverables and Archive

| Deliverable | Archive Path |
|--------|---------|
| Test plan (this document) | `docs/plans/26-winter/orchestration-center-test-plan.md` |
| Case table CSV (8 cases, all executable) | `docs/plans/26-winter/testcases-orchestration-center.csv` |
| Test code (8 `sandbox-verify` cases) | `e2e/orchestration-center/` |
| Test report | `docs/reports/26-winter/` (template: `test-report-template.md`) |

---

## Appendix

### A. Verified API and field reference

Internal API (session token required): `POST /rest/v1/orchestrate/workflows` (201, `data.workflow_id`), `GET /rest/v1/orchestrate/workflows/{workflow_id}`, `DELETE /rest/v1/orchestrate/workflows/{workflow_id}` (200; re-query returns 404), `GET /rest/v1/orchestrate/execute?psop_id=&user_intent=&target_agent=&lang=` (SSE), `GET /rest/v1/orchestrate/dispatch?intent=&agent_name=&lang=` (SSE), `GET/DELETE /rest/v1/orchestrate/execution-records[/{execution_id}]`, `GET /rest/v1/orchestrate/agent-cards`, and the sandbox routes in §5.4. Liveness: `GET /health` -> `{"status":"ok"}`.

External API: `GET /api/v1/orchestrate/psop/{psop_id}`, `POST /api/v1/orchestrate/search`, `POST|GET /api/v1/orchestrate/execute[/{psop_id}]`, `GET /api/v1/executions`, `GET /api/v1/executions/{execution_id}`. Envelope: `{"code":..., "message":..., "status":"success|error", "data":...}` (`orchestrate/server/response_utils.py`: `ok` = 200, `created` = 201).

SSE event vocabulary forwarded by `orchestrate/server/sse_executor.py` from the SDK (`workflow_engine.control.control_points.EventType`): `start`, `psop_update`, `step_start`, `step_complete`, `task_request`, `task_response`, `task_status_changed`, `agent_request`, `agent_response`, `route_decision`, `negotiation_request`, `negotiation_resolved`, `negotiation_failed`, `complete`, `error`; heartbeats are `: heartbeat` comment frames every 15 s. `start` carries `data.phase` (`searching`/`loading`/`dispatching`) and `data.workflow_id`; `task_request`/`task_status_changed` carry `data.step`, `data.subtask_index`, `data.agent`, `data.status`.

Execution record (`orchestrate/core/model/execution_record.py`): `execution_id`, `psop_id`, `psop_name`, `started_at`, `completed_at`, `status` (`running|success|failed|stopped`), `final_psop`, `events`, `error`.

Sandbox report (`orchestrate/sandbox/models.py` `SandboxRunReport`): `verification_id`, `workflow_id`, `workflow_name`, `mode=sandbox`, `verification_scope=structure_and_stub_execution`, `route_policy=always_allow_stub`, `scenario`, `verdict` (`pass|warning|fail`), `static_checks[]` (`check_id`, `status`, `detail`, `affected`, `evidence`, `suggestions`), `execution_path[]`, `context_trace[]` (`step`, `subtask_index`, `agent`, `skill`, `upstream_steps`, `upstream_result_count`), `stub_interactions[]` (`step`, `subtask_index`, `agent`, `skill`, `scenario`, `template_id`, `task_state`, `response_text`, `error_code`, `negotiation_rounds`), `risks[]`, `suggestions[]`, `error`, `events_truncated`, `report_truncated`.

Static check ids: `structure.blank_step_name`, `structure.duplicate_step`, `structure.empty_subtasks`, `structure.next_targets`, `structure.cycle`, `structure.reachability` (warning only), `structure.context_sources`, `agents.duplicate_card` (warning), `agents.missing`, `agents.skill_match` (warning), `agents.task_t_extension`, `agents.negotiation_t_extension` (warning).

Stub contract: `scenario` in `success|error|delay|negotiation`; a template matches on `workflow_id`, `step`, `subtask_index`, `agent`, `skill`, `card_name`, and the most specific match wins (step+subtask_index 7 > agent+skill 6 > agent 5 > card_name 4 > generic 3); response text may only use the whitelisted variables `workflow_id`, `workflow_name`, `intent`, `step_name`, `task_description`, `skill`, `agent`; the generated default template id is `generated-card-default`. Verification statuses: `queued`, `running`, `completed`, `failed`, `cancelled`, `timed_out`.

Registry API used by the center (`orchestrate/registry_client/client.py`): `POST /rest/v1/registry-center/agent-cards` (body `{"agentCards":[...]}`), `GET /rest/v1/registry-center/agent-cards[?name=&organization=&provider=]`, `GET|PUT|DELETE /rest/v1/registry-center/agent-cards/{organization}/{name}` (the detail GET answers 200 with an empty `agentCards` list for a missing card).

### B. Verification-source convention

Every CSV row ends with `verification source:` naming the `orchestration-center` repository paths (with line numbers where useful) where the asserted behaviour was verified.

### C. Follow-up for tracking issue #10

Role-based orchestration (issue #10, upstream #74) is out of scope this cycle because the design has not passed TSC review. When it hands over: submit the role-mapping case design as a follow-up PR against `docs/plans/26-winter/`, extend this plan (§1, §4, §5.2, §7) in the same change, and re-tier the new rows with `Automatable=Yes`.
