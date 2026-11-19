# Workflow Engine SDK Test Plan (DAG Execution, Dispatch, State Sync, Result Callbacks)

> Version: v0.2 | Date: 2026-11-19 | Author: Orchestration Center WG test owner (Zhoujie628) | Review status: Pending review
> Related feature proposal: [orchestration-center#79](https://github.com/project-openan/orchestration-center/issues/79) (tracked in [integration-test#13](https://github.com/project-openan/integration-test/issues/13)) | Version milestone: `26-winter`
> Archive path: `docs/plans/26-winter/` (merged via PR after review approval)

---

## 1. Overview

### 1.1 Purpose

This plan defines the Feature Integration Test (FIT) for `workflow-engine-sdk` in the `26-winter` milestone. The feature delivers a lightweight Multi-Agent Workflow Engine SDK in two language implementations — `workflow-engine-sdk-python` (distribution `workflow-exec-engine`, version `0.1.1`) and `workflow-engine-sdk-java` (`net.openan.workflow.sdk:workflow-engine`, version `0.1.1`) — that performs protocol-level scheduling over a PSOP DAG and AgentCard Skills: task dispatch, state synchronization, and result callbacks.

The goals verified here are:

1. The SDK executes a PSOP DAG correctly as an embedded library: validation before any dispatch, topological ordering, parallel branch fan-out, join semantics, and failed-branch handling reported as a business outcome rather than a crash.
2. Each PSOP step is dispatched to the agent and skill the workflow names, over the A2A-T transport the AgentCard declares, with the payload the host callback produced.
3. Step and workflow state is exposed and transitioned during a run, and can be persisted or forwarded by the application layer.
4. Results are handed back to the application layer through the documented callback contract, with stable failure codes.
5. The Python-side contract surface (`ExecutionResult`, history keys, failure prefixes, error codes) is stated precisely enough that the deferred Java↔Python parity check can be authored later without re-deriving the API.

Business logic (context construction, conditional routing decisions, A2A-T content generation and semantic validation) is out of the SDK; those remain host responsibilities and are exercised only as the callback boundary, never asserted on generated model text.

### 1.2 Scope

**In scope** (aligned with the integration testing boundaries in Framework §5.2):

- SDK-driven workflow execution end to end: DAG traversal, task dispatch over A2A-T, state exposure, result hand-back.
- DAG execution correctness for the shapes the engine promises: linear chains, diamonds, late-branch joins, conditional fan-out, all-denied branches, invalid graphs, failing steps.
- SDK usability against a reference agent setup: `openan-demo/mockagent` stub instances as the remote agents, its `registry_seed/agentcard.json` as the AgentCard source, and `registry-center` as the card authority when the run must resolve cards from the real registry.
- The application-layer hand-back surfaces: `ControlPoint` callbacks, `EventCallback`/`on_event`, and the `on_finish` persistence hook.
- One cross-module path where the SDK is the execution core of the `orchestration-center` host agent, because that is how the reference deployment actually uses it.

**Out of scope**:

- Unit-level boundary testing inside each SDK repository — both repos already ship `test_*.py` / `WorkflowExecutorTest` suites (`workflow-engine-sdk-python/test_*.py`, `workflow-engine-sdk-java/workflow-engine/src/test/java/...`).
- LLM-generated business content quality; every case asserts structure, status, identifiers, and deterministic projections only.
- Performance, stress, long-duration stability, TLS/mTLS hardening, credential encryption, and protocol-log redaction, which are DFX and tracked separately (`agent_credentials.example.json` and `SensitiveDataRedactor` behaviour is only touched where a business failure message must stay readable).
- Negotiation-T interaction-loop depth, Authorization-T and Notification-T channel lifecycles. The SDK implements them, but they belong to the A2A-T protocol feature; this plan asserts Task-T traffic only.
- Changes to the AgentCard/Skill protocols or to orchestration-center backend business logic — the feature explicitly excludes both.
- **Java↔Python contract parity is deferred to DFX and is not part of this submission.** Multi-language SDK interoperability is a DFC scenario ("Not in FIT") per `skills/feature-level-test-cases-gen/references/fit-dfx-scenario-attribution-criteria.md`, so a separate DFX (DFC) table for this feature must carry it; no parity row is present in this FIT case table. The concrete divergences found while authoring are kept in §10 and Appendix B so the DFX author inherits them verbatim: Java history keys `taskId`/`errorCode`/`errorDetails` and an extra `success` field in `task_response`, versus Python `task_id`/`error_code`/`error_details`; and Python's `Invalid workflow: ` prefix with `; `-joined fragments versus Java's single-purpose `IllegalArgumentException` messages. Only the Python-side observables are asserted here, inside `dag-execution-001` (key names) and `dag-execution-004` (prefix and `; ` joining).

### 1.3 References

| Document | Link/Path |
|------|----------|
| OpenAN Integration Testing Process and Framework | `docs/OpenAN Integration Testing Process and Framework.md` (§5.2, §6, §7, §8) |
| OpenAN Test Checklist | `docs/openan-test-checklist.md` |
| Feature proposal | https://github.com/project-openan/orchestration-center/issues/79 |
| Feature handover issue | https://github.com/project-openan/integration-test/issues/13 |
| Python SDK design | `workflow-engine-sdk-python/DESIGN.md` |
| Python SDK integration guide | `workflow-engine-sdk-python/DEVELOPER_GUIDE.md`, `workflow-engine-sdk-python/README.md` |
| Java SDK design | `workflow-engine-sdk-java/docs/en/DESIGN.md` |
| Java SDK API reference | `workflow-engine-sdk-java/docs/en/API_REFERENCE.md`, `docs/en/BUSINESS_CALLBACKS.md` |
| Component API documentation | Registry Center API Reference (`/rest/v1/registry-center/agent-cards`), Orchestration Center API Reference (`/api/v1/orchestrate/*`) |
| Deployment contract | `openan-installation/containerized/TRANSPORT_DEPLOYMENT.md` |
| Compatibility matrix | Specialized compatibility test plan (`26-winter`) |
| FIT/DFX scenario attribution criteria | `skills/feature-level-test-cases-gen/references/fit-dfx-scenario-attribution-criteria.md` (multi-language SDK compatibility = DFC, not FIT) |

---

## 2. Objects Under Test

| Component | Repository | Version/Build | Test Layer | Notes |
|------|------|----------|----------|------|
| Workflow Engine SDK (Python) | `workflow-engine-sdk-python` | `0.1.1` (`workflow_engine.__version__`), source install via `pip install -e .` | FIT (primary) + UT (module repo) | `WorkflowExecutor`, `WorkflowEngineClient`, `A2ATransport`, `execute_psop`, `RegistryClient` |
| Workflow Engine SDK (Java) | `workflow-engine-sdk-java` | `0.1.1` (`net.openan.workflow.sdk:workflow-engine`) | UT (module repo) only — parity deferred to DFX/DFC | `ExecutePsop`, `WorkflowExecutor`, `ControlPoint`, `RegistryClient`; the Java surface in Appendix A feeds the deferred DFC table |
| Reference host agent | `openan-demo/mockagent` | `mockagent_engine` (workflow mode enabled) | FIT dependency | Hosts PSOPs via `execute_psop`; SELF_LOOP steps local, remote steps dispatched over `A2ATransport` |
| Stub agent fleet | `openan-demo/mockagent/agents/an-l4-*` | 20 instances, ports 9101-9120 or gateway prefix `/agents/<id>` | FIT dependency | AgentCards in `registry_seed/agentcard.json`, `provider.organization=OpenAN-Stub`, declare Task-T / Negotiation-T / Authorization-T / Notification-T |
| Registry Center | `registry-center` | `26-winter` release build | FIT dependency (2 cases) | Card authority for `RegistryClient.fetch_agent_cards()` |
| Orchestration Center | `orchestration-center` | `26-winter` release build | FIT dependency (1 case) | Host agent runtime forwards SDK events as A2A task updates |

The module under test is the SDK only. `mockagent`, `registry-center`, and `orchestration-center` appear in the `Component Deps` column exclusively on rows whose steps actually interact with them.

---

## 3. Test Strategy

### 3.1 Test Layers

| Layer | Executor | Scope |
|------|--------|------|
| FIT | Feature WG (Orchestration Center) | SDK integration correctness against a reference agent setup, Python implementation only |
| SIT | Integration Testing WG | Release-level combination of orchestration-center + registry-center + sample agents over the SDK execution core |

### 3.2 Test Types

- [x] Functional testing (DAG execution, dispatch routing, state events, result hand-back)
- [x] Exception testing (invalid DAG, missing AgentCard, callback failures, client/executor reuse)
- [x] A2A-T protocol testing (Task-T content envelope and `A2A-Extensions` activation on dispatch — `task-dispatch-001`, typed `Protocol Test`)
- [ ] Performance testing (owned by the SDK repos and the DFX track)
- [ ] Stress/capacity testing
- [ ] Long-duration stability testing (7×24h)
- [ ] Reliability/fault injection beyond the business negatives already covered (network cut, pod kill, clock skew)
- [ ] Security testing (mTLS, credential encryption, protocol-log redaction — DFX)
- [ ] Compatibility testing — **not in this FIT table**: Java↔Python contract parity is a DFC scenario and moves to a separate DFX (DFC) table for this feature, outside this submission (see Appendix B items 3-4 for the divergence evidence it inherits). K8s/OS version compatibility is a separate specialized plan.
- [ ] Deployment mode testing (covered by `openan-installation`)

### 3.3 Test Method

- Real transport, real agents: dispatch cases run against `mockagent` stub instances over HTTP+JSON (`supportedInterfaces` populated in every card). Only pure DAG/state cases replace the network with `StubWorkflowEngineClient` (`workflow_engine/client/stub_engine_client.py`), which is the SDK's own documented test double and mirrors the Java `StubWorkflowEngineClient`.
- Deterministic payloads: `A2AT_LLM_*` is left unset in the dispatch harness so the host `ControlPoint.on_task` builds the Task-T payload from `a2a_t` `MetadataContent` deterministically (`A2atMessages.from_generated`), exactly as `openan-demo/mockagent/mockagent_engine/workflow_mode.py` does with a dataset template.
- Deterministic assertions: no case asserts model output. Cases assert `ExecutionResult.success/error`, `history` key/values, `step_outputs` keys, `TaskStatus` values, event `type` sequences, `execution_id` stability, error codes, and generated `task_id` values recomputed from `uuid5(NAMESPACE_URL, "<execution_id>:<step>:<index>")`.
- Synchronization: the concurrency case uses a rendezvous barrier in front of two stub agents instead of timing thresholds, so a serial dispatch fails deterministically rather than flakily. No `sleep`-based synchronization is used in any case.
- LLM dependency: none required for the FIT suite. Content generation is stubbed at the callback boundary.

### 3.4 Automation Strategy

- 100% of P0/P1 cases are automated (`Automatable=Yes` for all 14 P0/P1 rows); P2 rows are automated as well, so the whole table is automatable.
- Landing zone: `e2e/workflow-engine-sdk/` in this repository, `pytest` + `pytest-asyncio` for all 20 rows (the table is Python-only; the Java harness belongs to the deferred DFC table).
- `execution` label layering: `smoke` (4 rows, the P0 core path, PR gate) / `full` (16 rows, daily).
- Failure archive: event stream, SDK protocol log (only when `WORKFLOW_ENGINE_PROTOCOL_LOGGING=true`), mockagent access log, and the compose service logs of the failing service.

---

## 4. Test Scenarios

| Scenario ID | Scenario Description | Components | Priority | Notes |
|---------|---------|----------|--------|-------|
| SCN-workflow-engine-sdk-001 | PSOP DAG is parsed, validated and executed in dependency order with stable logical task identity (`dag-execution-001`) | SDK | P0 | Covers `Workflow.from_dict`, `WorkflowExecutor.run`, `_task_id` |
| SCN-workflow-engine-sdk-002 | Parallel branches fan out, a late-branch merge waits for every activated ancestor, and `context_from` scopes the upstream window (`dag-execution-002`, `dag-execution-003`) | SDK | P1 | Covers `_collect_ready`, `ContextBuilder.build_workflow_input` |
| SCN-workflow-engine-sdk-003 | Malformed DAGs are rejected before any dispatch; a denied conditional fan-out ends its branch; a failing step is reported as a failed workflow (`dag-execution-004`, `dag-execution-005`, `dag-execution-006`) | SDK | P1 | Covers `validate_workflow`, `_determine_next_steps`, `_execute_step` |
| SCN-workflow-engine-sdk-004 | A PSOP task reaches the AgentCard-declared agent and skill as a Task-T message with activated extension, from either seed cards or registry-center (`task-dispatch-001`, `task-dispatch-002`, `task-dispatch-004`) | SDK, mockagent, registry-center | P0 | Covers `A2ATransport.get_card`, `validate_content_extensions`, `RegistryClient` |
| SCN-workflow-engine-sdk-005 | Same-step subtasks dispatch concurrently; an unregistered target agent fails without emitting protocol traffic (`task-dispatch-003`, `task-dispatch-005`) | SDK, mockagent | P1 | Covers `_execute_subtasks`, `_dispatch` agent lookup |
| SCN-workflow-engine-sdk-006 | Step and workflow state is exposed as an ordered event stream, guarded against client/executor reuse, and persisted through `on_finish` (`state-sync-001`, `state-sync-002`, `state-sync-003`, `state-sync-005`) | SDK | P0 | Covers `execute_psop` lifecycle, `EventType`, `begin_execution`/`end_execution`, `on_finish` |
| SCN-workflow-engine-sdk-007 | The orchestration-center host agent forwards SDK state to the center as A2A task updates carrying `__sdk_event__` metadata (`state-sync-004`) | orchestration-center, registry-center, mockagent | P2 | Covers `host_agent/runtime.py` event wrapping |
| SCN-workflow-engine-sdk-008 | `ExecutionResult` and per-task results are handed back to the application layer with upstream results, stable failure codes and event reshaping (`result-callback-001` … `-004`) | SDK, mockagent | P0 | Covers `on_finish`, `TaskRequest.workflow_input`, `failure_to_task_result`, `on_event` |

---

## 5. Test Case Design

### 5.1 Numbering Rules

- FIT cases: `[FIT-workflow-engine-sdk-<topic>-<number>]`, topics `dag-execution`, `task-dispatch`, `state-sync`, `result-callback`.
- Sequences start at `001` and are continuous within a topic.

### 5.2 Priority Definitions

| Priority | Definition | Pass Rate Requirement |
|--------|------|-----------|
| P0 | The SDK core path a host cannot ship without: a valid DAG executes, a task reaches its agent, state is observable, the result is handed back | 100% (TRR entry and release gate) |
| P1 | Main functionality: fan-out/join correctness, routing per agent and skill, registry-resolved cards, persistence hook, stable failure codes | 100% |
| P2 | Business negatives and complex variants: all-denied branches, failing steps, unregistered target, card-map refresh, center event forwarding, event reshaping | ≥80% |

### 5.3 Label Dimensions

Every case carries the labels in code: `feature=workflow-engine-sdk`, `environment` (`docker-compose` / `with-workload-cluster`), `components` (derived from `Component Deps`), `priority`, `execution` (`smoke` / `full`). `language_profile` is `python` for every row in this table; Java rows live in the deferred DFX (DFC) table and are not labelled here. Temporary skips must reference a defect issue.

### 5.4 Case Table

Cases are carried in the 16-column CSV archived next to this plan: [`testcases-workflow-engine-sdk.csv`](testcases-workflow-engine-sdk.csv). Field rules follow [Test Case Table Field Description](../../templates/testcases-template-fields.md).

Inventory — 20 rows, 16 fields per data row, header verbatim:

| Topic | Rows | Case IDs | Priority mix |
|---|---|---|---|
| `dag-execution` | 6 | `-001` … `-006` | P0×1, P1×3, P2×2 |
| `task-dispatch` | 5 | `-001` … `-005` | P0×1, P1×3, P2×1 |
| `state-sync` | 5 | `-001` … `-005` | P0×1, P1×2, P2×2 |
| `result-callback` | 4 | `-001` … `-004` | P0×1, P1×2, P2×1 |
| **Total** | **20** | | **P0=4, P1=10, P2=6** |

Label distribution: `language_profile` python 20 (single language; Java parity deferred to DFX); `environment` docker-compose 18 / with-workload-cluster 2; `protocol_primitive` `Task-T` 8 / `none` 12; `execution_strategy` smoke 4 / full 16. Case types: Functional Test 14, Exception Test 5, Protocol Test 1 (the A2A-T Task-T envelope assertion in `task-dispatch-001`).

### 5.5 Case Design Requirements

- Every case has numbered preconditions (≤ 6 items, environment/data state only) and numbered steps whose last step is a cleanup with its own assertion (fixtures deleted, stack stopped, capture lists empty, card count unchanged).
- Every checking step ends with `see result N` and the numbered Expected Result item `N` states a machine-checkable assertion.
- Cases are independently repeatable: generated PSOP fixtures are per-case files, mock agent state is reset in the cleanup step, no case depends on execution order.
- Session-level fixtures are read-only configuration only: the mockagent compose stack, the AgentCard seed set, and `send_timeout_seconds`.

---

## 6. Test Environment and Data

### 6.1 Environment Topology

| Item | Value |
|----|------|
| Deployment mode | `docker-compose` for the SDK-plus-mock-agent cases (18 rows); workload cluster for the two cases that need the real registry-center/orchestration-center (2 rows) |
| Host services | `mockagent` gateway on `127.0.0.1:9300` with `/agents/<id>` prefixes (recommended single-port mode) or per-instance ports `9005-9010` / `9101-9120` |
| Cluster services | `registry-center` `https://127.0.0.1:5000`, `orchestration-center` backend `http://127.0.0.1:5001` (frontend `3003`) |
| Runtimes | Python 3.12+ with `a2a-sdk>=1.1.2,<2`, `a2a-t-sdk>=1.2.0,<2`; JDK 17 + Maven 3.6+ are needed only by the deferred DFX (DFC) parity table, not by this suite |
| Environment provider | Integration Testing WG |

### 6.2 Dependent Services

| Dependency | Configuration | Notes |
|------|---------|------|
| Reference agents | `openan-demo/mockagent` gateway, cards from `registry_seed/agentcard.json` | Referenced by the 10 rows that name `mockagent` in `Component Deps` |
| Registry Center | `REGISTRY_CENTER_URL=https://127.0.0.1:5000`, `REGISTRY_CA_CERT`, registry access token | Used by `RegistryClient.fetch_agent_cards()` in `task-dispatch-004` |
| Orchestration Center | `agent_registry_url` pointing at registry-center, host agent registered, PSOP stored | Used by `state-sync-004` |
| LLM endpoint | Not required; `A2AT_LLM_*` deliberately unset so callback payloads are deterministic | A real endpoint may be used for exploratory runs only |
| External database | Not required; `persistence_mode=file` is sufficient for the one center-side case | PostgreSQL/MySQL not exercised |

### 6.3 Test Data

- PSOP fixtures: linear chain, diamond, late-branch join (`a->b,c; b->d,q; c->d; d->s; s->p; q->m; p->m; m->endNode`), three-edge conditional fan-out, three-step persistable DAG, and two-step remote+aggregate DAG. All loaded through `Workflow.from_dict` so the fixture format is the same one `load_psop` returns.
- Malformed fixtures: duplicate step name, unknown edge target, self cycle, reserved terminal name (`endNode`), `context_from` mixing `"*"` with a named source, blank `task.agent`.
- AgentCard sets: the seed `agentcard.json` (26 cards, `provider.organization=OpenAN-Stub`), plus synthetic sets A/B/C for the card-map refresh case.
- Callback implementations: recording `ControlPoint`, denying `ControlPoint`, `BusinessFailure`-raising `ControlPoint`, event-collecting `EventCallback`, event-reshaping `on_event`.

### 6.4 Environment Variables

The suite reuses `e2e/.env.template` (`REGISTRY_CENTER_URL`, `REGISTRY_CA_CERT`, `ORCHESTRATION_CENTER_URL`, `MOCK_AGENTS_HOST`). SDK-specific variables already documented by the component are `WORKFLOW_ENGINE_PROTOCOL_LOGGING`, `WORKFLOW_ENGINE_PROTOCOL_INCLUDE_SENSITIVE_HEADERS`, and `A2AT_CRED_KEY` (see `workflow-engine-sdk-python/.env.example`). New variables introduced by this plan — `SDK_FIXTURE_DIR` and `MOCKAGENT_GATEWAY_URL` — must be added to `e2e/.env.template` and documented in the README before the automation merges. No secret is hardcoded; registry token and CA path are injected.

---

## 7. Entry and Exit Criteria

| Gate | Criteria | Source |
|------|------|------|
| TRR entry (into FIT) | Both SDK repositories build (`python -m build`, `mvn -B clean verify`), P0/P1 pass rate = 100%, mockagent compose stack and the two cluster services healthy, image deployable | Framework §8.1 |
| FIT exit | Overall pass rate ≥ 95%, failed cases archived as issue + `skip-temporarily`, no open P0/P1, report reviewed by the Integration Testing WG | Framework §8.2 |
| SIT exit / release entry | SIT pass rate = 100% with no skips, install/upgrade/rollback passed, no open P0, compatibility matrix passed | Framework §8.3 |

---

## 8. Defect Management

- Severity per Framework §9.1 (P0: 24h response / fix in current release; P1: 3 business days; P2: next release; P3: scheduled as needed).
- Triage routing: a DAG/routing/state defect goes to the SDK repository that produced it; a Python↔Java contract divergence is not a FIT defect here — it is captured as evidence and handed to the DFX (DFC) author, and filed against both `workflow-engine-sdk-python` and `workflow-engine-sdk-java` if it is later confirmed as a released-behaviour mismatch.
- Failed cases are archived automatically as issues with the event stream, the SDK protocol log, the mockagent access log and compose service logs attached.
- Fix PRs must add a regression case to the owning repository's `test_*.py` / JUnit suite and re-run the full FIT set for this feature.

---

## 9. Schedule and Responsibilities

| Milestone | Date | Owner | Deliverable |
|------|------|--------|--------|
| Test plan review approved | 2026-11-25 | Integration Testing WG | This plan merged into `docs/plans/26-winter/` |
| Case writing completed | 2026-12-05 | Zhoujie628 | `testcases-workflow-engine-sdk.csv` + automation in `e2e/workflow-engine-sdk/` |
| TRR review | 2026-12-12 | Integration Testing WG | TRR conclusion (Test Checklist Chapter 1) |
| FIT completed / report review | 2026-12-18 | Zhoujie628 | Test report in `docs/reports/26-winter/` |

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|---------|---------|
| `workflow-exec-engine` `0.1.1` is source-only — the README states the version note "does not mean this version has been published to PyPI" | Test environment cannot install from an index; PyPI `0.1.0` may behave differently | Pin the reviewed source revision and install with `pip install -e .`; record the commit in the report; do not overwrite a published coordinate |
| Java↔Python contract divergence is out of FIT scope, so this plan cannot prove portability itself | A reader could mistake the plan's passing FIT rows for cross-language parity | Parity is deferred to the DFX (DFC) table; §1.2, §3.2 and Appendix B carry the exact divergence evidence for that author: Java history keys `taskId`/`errorCode`/`errorDetails` plus an extra `success` field in `task_response`, versus Python `task_id`/`error_code`/`error_details`; and Python's `Invalid workflow: ` prefix with `; `-joined fragments versus Java's single-purpose `IllegalArgumentException` text. The Python half of this evidence is asserted here in `dag-execution-001` and `dag-execution-004`, so it cannot silently drift before the DFC lands |
| Java release boundary: Maven Central publishes `0.1.1`, while center HTTP authentication/TLS, PSOP account login and task-state-independent Notification-T handling are unreleased in source | The deferred DFC table could accidentally test unreleased behaviour | The evidence handed over is limited to `0.1.1` surface (event vocabulary, `ExecutionResult` shape, DAG validation); the DFC author must pin an exact source revision for anything beyond it |
| The SDK has no persistence store; state persistence is entirely the host's `on_finish` hook | A reviewer may expect "state persistence" to be an SDK feature | `state-sync-003` asserts the hook contract (arguments, ordering, snapshot boundary) and this plan states the boundary explicitly |
| `mockagent`'s runtime `scenarios/` and `workflows/` directories are not committed in the checked-out tree | A scenario workflow cannot be relied on as a fixture | Every case builds its own PSOP fixture through `Workflow.from_dict`; no case depends on an uncommitted scenario file |
| Skill is carried on `Task`/`TaskRequest`/`TaskExecutionResult` but dispatch routes by AgentCard `name` only | A mistaken expectation that the SDK resolves an agent *from* a skill would produce a false defect | `task-dispatch-002` asserts skill pass-through to `on_task` (where the host selects the Content template) and agent-name routing separately |
| Real registry/orchestration-center availability and clock/rate limits | The two cluster rows could be flaky or blocked | They are P1/P2 and scheduled after the compose rows; rate-limit rejections (HTTP 429/503) are recorded as environment issues, not product defects, and retried via the framework wait/retry helper |
| Condition/join semantics differ subtly between engines on late-join graphs | Silent wrong-input merges (the class of defect the Java history already fixed) | `dag-execution-002` locks the Python side to the Java-derived fixture; the cross-engine comparison itself belongs to the deferred DFC table |

---

## 11. Deliverables and Archive

| Deliverable | Archive Path |
|--------|---------|
| Test plan (this document) | `docs/plans/26-winter/workflow-engine-sdk-test-plan.md` |
| Case table CSV | `docs/plans/26-winter/testcases-workflow-engine-sdk.csv` |
| Test code | `e2e/workflow-engine-sdk/` |
| Test report | `docs/reports/26-winter/` (template: [test-report-template.md](../../templates/test-report-template.md)) |

---

## Appendix

### A. Verified SDK surface referenced by this plan

The Java column documents the surface verified while authoring; it is reference material for the deferred DFX (DFC) parity table and backs no FIT row in this plan.

| Concern | Python | Java |
|---|---|---|
| Execution entry | `WorkflowExecutor(workflow, control_point, engine_client, ...).run()`; `execute_psop(psop, agent_cards, control_point, ...)` | `new WorkflowExecutor(...).run()`; `ExecutePsop.builder()...execute()` |
| Business callbacks | `ControlPoint.on_task / on_self_task / on_route / on_negotiation` | `ControlPoint.onTask / onSelfTask / onRoute / onNegotiation` (+ `ControlPoint.builder()`) |
| Transport | `A2ATransport(agent_cards=..., credentials_config=..., send_timeout_seconds=..., ...)`, `WorkflowEngineClient(transport)` | `A2ATransport`, `WorkflowEngineClient` / `DefaultWorkflowEngineClient` |
| State events | `EventType.START / STEP_START / TASK_REQUEST / TASK_STATUS_CHANGED / TASK_RESPONSE / ROUTE_DECISION / WORKFLOW_COMPLETE / ERROR / COMPLETE / CLOSE`, `EventCallback.on_event` | `EventType` constants with identical string values, `EventCallback` |
| Task/step model | `Workflow`, `WorkflowStep`, `Task`, `JumpCondition`, `StepType.ALL_SUCCESS/ANY_SUCCESS/SELF_LOOP`, `TaskStatus` | `Workflow`, `WorkflowStep`, `Task`, `JumpCondition`, `StepType`, `TaskStatus` |
| Results | `ExecutionResult(success, history, step_outputs, error)`, `TaskExecutionResult`, `TaskResult`, `SendMessageResult` | `ExecutionResult`, `TaskExecutionResult`, `TaskResult`, `SendMessageResult` |
| Validation | `workflow_engine.core.workflow_validator.validate_workflow` → `ValueError("Invalid workflow: ...")` | `WorkflowExecutor.validateWorkflowGraph()` → `IllegalArgumentException` |
| Registry | `RegistryClient.fetch_agent_cards / fetch_agent_card / register_agent_card`, `load_psop`, `search_psop` | `RegistryClient.fetchAgentCards / fetchAgentCard / registerAgentCard`, `LoadPsop` |
| Test double | `StubWorkflowEngineClient` | `StubWorkflowEngineClient` |

### B. Source gaps and assumptions recorded while authoring

1. **No SDK persistence layer.** `ExecutionResult` plus the `on_finish(result, events)` hook is the whole persistence surface (`workflow_engine/runner.py`). `state-sync-003` is written against that hook, not against a store.
2. **Skill is metadata, not a routing key.** It is copied into `TaskRequest` and `TaskExecutionResult`, but `WorkflowEngineClient._dispatch` resolves the target purely by AgentCard name (`self._transport.get_card(request.agent_name)`). Cases assert name-based routing and skill pass-through separately.
3. **Key-naming divergence handed to DFX (DFC).** Python history keys are `task_id`/`error_code`/`error_details` (`workflow_engine/core/executor.py`); Java equivalents are `taskId`/`errorCode`/`errorDetails` and Java's `task_response` payload additionally carries `success` (`WorkflowExecutor.java`). This plan asserts only the Python names (`dag-execution-001`); the cross-language mapping is DFC scope.
4. **Invalid-graph message divergence handed to DFX (DFC).** Python prefixes `"Invalid workflow: "` and joins fragments with `"; "` (`workflow_validator.py`); Java throws single-purpose `IllegalArgumentException` messages and converts them into a failed `ExecutionResult` (`WorkflowExecutor.java` L557-580, L795-865). `dag-execution-004` asserts the Python prefix and joining; the Java comparisons belong to the DFC table.
5. **`mockagent` scenario and workflow runtime directories are absent** from the checked-out tree, so this plan does not depend on them; all PSOPs are case-owned fixtures.
6. **`workflow-exec-engine 0.1.1` is not published** per the SDK README; the harness installs from source. If CI can only install from PyPI, `0.1.0` would be used and the affected cases must be re-baselined.
7. **`mockagent` workflow mode needs `a2a-t-sdk` and, for LLM mode, a live model endpoint.** The FIT harness uses the deterministic `ControlPoint` payload path (dataset template or plain text), never the LLM path.
8. **`registry_seed/agentcard.json` currently holds 26 AgentCards** (20 AN L4 fleet cards plus 6 legacy stub cards). `task-dispatch-004` asserts `N >= 21` and re-reads the live count before and after the run, so seed trimming does not break the case but an accidental mass deletion still fails it.
9. **PSOP `skill` values are AgentCard skill display names**, not ids (for example `Analysis and Evaluation` on `mockagent_an-l4-ran-agent`, `Service Assurance Root Cause Analysis` on `mockagent_an-l4-service-assurance-agent`). The fixtures must use those exact strings, matching how `openan-demo/mockagent/mockagent_engine/workflow_mode.py` keys `AGENT_SKILL_TEMPLATE_MAP`.

### C. Test Checklist

- Test Checklist: `docs/openan-test-checklist.md`
- Framework document: `docs/OpenAN Integration Testing Process and Framework.md`
- Case table field rules: `docs/templates/testcases-template-fields.md`
- SDK test doubles used by this suite: `workflow-engine-sdk-python/workflow_engine/client/stub_engine_client.py` (the Java `workflow-engine-sdk-java/workflow-engine/src/test/java/dev/openan/workflow/engine/StubWorkflowEngineClient.java` equivalent belongs to the deferred DFX/DFC table)
