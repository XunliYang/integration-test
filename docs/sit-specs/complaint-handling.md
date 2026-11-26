# SIT Specification S1: Home Broadband Complaint Handling

> *Version: v0.1 (Draft)*
> *Maintained by: OpenAN Integration Testing Working Group*
> *Language: English*
> *Scenario slug: `complaint-handling` - Case IDs: `[SIT-complaint-handling-<number>]`*
> *Scenario baseline: [sit-scenarios.md](../sit-scenarios.md) S1*
> *Governance baseline: [OpenAN Integration Testing Process and Framework](../OpenAN%20Integration%20Testing%20Process%20and%20Framework.md) (cited as "Framework" below)*

---

## 1. Scope

This specification defines the SIT requirements for scenario S1 (Home Broadband Complaint Handling), derived from the published example case "Home Broadband Complaint Handling" (https://openan.dev/best-practices/usecase.html).

**In scope** - the distribution-level closed loop:

1. Intent capture: a call-center-style complaint intent enters the complaint handling agent;
2. Workflow recall: Orchestration Center retrieves the workflow matching the complaint category;
3. Agent retrieval: Registry Center issues the agent cards required by the recalled workflow;
4. Multi-agent execution: domain agents collaborate over A2A-T to produce a diagnosis;
5. Closure or expert handoff: resolved cases close autonomously; unresolved cases escalate to a NOC expert endpoint with full diagnostic context.

Both workflow branches are variants of this one scenario (see sit-scenarios.md §2):

| Variant | Trigger intent | Domain agents | Execution path |
| --- | --- | --- | --- |
| A - outage / billing | "No internet for two days" | Customer Care, Billing, Vendor 1 FAN | account status -> billing blocks -> physical-layer diagnostic |
| B - streaming / speed degraded | "YouTube/Netflix playback is slow" | Customer Care, CDN, Vendor 2 FAN | service quality check -> CDN node routing -> access-network congestion |

**Out of scope** (do not duplicate here):

- Single-API / single-module contract checks -> FIT cases in `e2e/registry-center/`, `e2e/orchestration-center/`;
- A2A-T protocol conformance, dual-transport equivalence, cross-language SDK interop -> `[SIT-a2at-protocol-*]` and specialized A2A-T protocol testing (Framework §10);
- Performance / stress thresholds, 7x24h stability runs -> specialized testing (Framework §10); thresholds are set in release test plans, not here;
- Pure UI layout/styling (Framework §5.2).

## 2. System Under Test

### 2.1 Topology

```
call-center intent (simulated)
        |
        v
complaint handling agent (host_agent + workflow-exec-engine)
        |                        |
        | workflow recall        | agent card retrieval (A2A-T)
        v                        v
Orchestration Center -------> Registry Center
        |
        | A2A-T Task-T collaboration
        v
Customer Care + Billing + Vendor 1 FAN   (branch A)
Customer Care + CDN    + Vendor 2 FAN   (branch B)
        |
        v
diagnosis conclusion -> autonomous closure
                    \-> NOC expert handoff (unresolved variant)
```

### 2.2 Components and dependency constraints

| Component | Role in S1 | Constraint |
| --- | --- | --- |
| `registry-center` (backend `agent_registry`, HTTPS :5000) | Agent card registration / discovery for all domain agents | mTLS client identity required (`REGISTRY_CLIENT_CERT/KEY/CA_CERT`) |
| `orchestration-center` (backend `orchestrate` :5001, `host_agent`, `samples/`) | Workflow recall and complaint handling agent host | Runtime dependency on registry-center (`AGENT_REGISTRY_URL` / shared `openan-net`) |
| `workflow-exec-engine` | Workflow execution within the complaint handling agent | Version `>=0.1.1,<0.2`; used with `a2a-t-sdk>=1.2.0,<2` |
| `a2a-t-sdk-python` | Agent-to-agent task collaboration | Version per orchestration-center constraint above |
| Domain agents (Customer Care, Billing, CDN, Vendor FAN) | Sample mock agents shipped with the distribution: orchestration-center `samples/` (started via `start_agents_server.py`, registered into Registry Center) and the `openan-demo` mockagent scenario package | Endpoints via `MOCK_AGENTS_HOST` / `SAMPLE_AGENTS_HOST` |
| NOC expert endpoint (simulated) | Receives escalation with diagnostic context | Test-side stub; contract to be confirmed (see §9) |
| LLM dependency | Intent classification / workflow generation where used | `USE_MOCK_LLM=true` for deterministic CI runs; real-LLM runs are an optional variant with deterministic assertions only |

All components deploy from the RC image package under test (`IMAGE_REGISTRY` / `IMAGE_TAG`), in `DEPLOY_MODE=online-helm` (real cluster, `KUBECONFIG`) or `offline-compose`. SIT runs on a real environment per Framework §5.1.

## 3. Environment and Configuration Contract

Reuse the existing `e2e/.env.template` contract (Framework §6.6). Variables consumed by S1:

| Variable | Usage in S1 |
| --- | --- |
| `KUBECONFIG`, `OPENAN_NAMESPACE`, `DEPLOY_MODE` | Cluster access and deployment mode |
| `REGISTRY_CENTER_URL`, `REGISTRY_CLIENT_CERT`, `REGISTRY_CLIENT_KEY`, `REGISTRY_CA_CERT` | Registry access with mTLS identity |
| `ORCHESTRATION_CENTER_URL`, `ORCH_ACCESS_PASSWORD` | Orchestration backend access / login session |
| `LLM_CHAT_*`, `A2AT_LLM_*`, `USE_MOCK_LLM` | LLM dependency; mock toggle for determinism |
| `MOCK_AGENTS_HOST`, `SAMPLE_AGENTS_HOST` | Domain agent endpoints |
| `IMAGE_REGISTRY`, `IMAGE_TAG` | RC build under test |
| `EVIDENCE_DIR` | Failure scene preservation |

Rules:

- No new variable may be introduced by S1 test code without simultaneously updating `e2e/.env.template` and the README (Framework §6.6, §11.2);
- No hardcoded IPs, credentials, or tokens in test code or scenario data;
- If the NOC handoff stub needs a configurable endpoint, add `NOC_HANDOFF_URL` to `.env.template` in the same PR that introduces it.

## 4. Test Data and Fixtures

| Fixture | Scope | Content | Cleanup |
| --- | --- | --- | --- |
| Domain agent cards | session (read-only registration baseline) or module | Agent cards for Customer Care, Billing, CDN, Vendor 1 FAN, Vendor 2 FAN, registered with valid JWS signatures | Deregister test-owned cards in teardown; never mutate cards owned by other cases |
| Branch workflows | module | Workflow definitions for branch A and branch B, stored/imported into Orchestration Center | Delete imported workflows in teardown |
| Complaint intents | function | Fixed intent payloads: branch A trigger, branch B trigger, unknown-category trigger, unresolved-edge-case trigger | Stateless |
| NOC handoff stub | function | Test-side receiver capturing escalation payloads | Reset captured payloads per case |
| Login session | session (read-only) | Orchestration Center session from `ORCH_ACCESS_PASSWORD` | Not shared mutable state (Framework §6.5) |

- Mutable state must never be shared across cases (Framework §6.5);
- Every case must be independently repeatable: running the full S1 suite twice in a row on the same environment must produce identical results without manual reset.

## 5. Case Matrix

IDs continue from the existing baseline case `[SIT-complaint-handling-001]` in `docs/templates/testcases-template.csv` (branch A end-to-end, P0). Do not renumber it.

| Case ID | Name | Variant coverage | Priority | Status | Execution |
| --- | --- | --- | --- | --- | --- |
| `[SIT-complaint-handling-001]` | Branch A (outage/billing) end-to-end closed loop | A, autonomous closure | P0 | Ready | smoke |
| `[SIT-complaint-handling-002]` | Branch B (streaming/speed) end-to-end closed loop | B, autonomous closure | P0 | Ready | smoke |
| `[SIT-complaint-handling-003]` | Intent-to-workflow recall routing correctness | A vs B | P1 | Ready | full |
| `[SIT-complaint-handling-004]` | Agent retrieval matches recalled workflow | A and B card sets | P1 | Ready | full |
| `[SIT-complaint-handling-005]` | Expert handoff carries full diagnostic context | A or B, unresolved edge case | P1 | Draft | excluded until ready |
| `[SIT-complaint-handling-006]` | Required domain agent unavailable: graceful degradation | A with Billing agent down | P1 | Ready | full |
| `[SIT-complaint-handling-007]` | Unknown complaint category: defined fallback | neither A nor B | P2 | Draft | excluded until ready |
| `[SIT-complaint-handling-008]` | Concurrent complaints isolation | A + B in parallel | P2 | Ready | full |

P0/P1 rows use Requirement Link https://github.com/project-openan/integration-test/issues/34 and `Automatable=Yes` as the final automation requirement; a Draft row remains excluded from current execution even though it is required to be automated after promotion.

### 5.1 Case definitions (preconditions / steps / assertions / cleanup)

Draft cases below record expected design only. Their contracts are not confirmed; they must not be implemented, executed, or counted in release-exit denominators until their blocking open items are resolved and their matrix status changes to Ready.

**001 - Branch A end-to-end (P0)**
- Status: Ready.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions: RC centers are deployed and healthy; the branch A workflow with a known workflow ID is imported; Customer Care, Billing, and Vendor 1 FAN cards are registered and their endpoints are reachable; `USE_MOCK_LLM=true`; the execution store contains no test-owned branch A execution.
- Steps: (1) submit the fixed "no internet access" complaint intent and record its execution ID; (2) subscribe to that execution's SSE stream; (3) collect its events through the terminal event; (4) compare the order of the received stage events and task-completion events; (5) list the domain agents identified by the received task events; (6) query the terminal execution by the recorded ID; (7) query each identified agent task by the recorded IDs.
- Assertions: for step 1, the response returns one execution ID and the recalled workflow ID exactly equals the imported branch A ID; for steps 2 and 3, the terminal status is `complete`; for step 4, every stage event precedes its corresponding task-completion event; for step 5, the task events identify exactly Customer Care, Billing, and Vendor 1 FAN with no other domain agent; for step 6, the result contains the required diagnosis-conclusion and handling-suggestions fields; for step 7, every identified task is successful.
- finally/Cleanup: in a `finally` block, close the SSE subscription and delete the test-owned execution and imported workflow; retain session-baseline agent cards. Recovery assertion: subsequent queries return not found for the deleted execution and workflow, all three baseline agents remain registered and reachable, and no test-owned task remains running.
- Automation: `e2e/system-integration/complaint-handling/test_complaint_handling.py::test_submit_outage_complaint_completes_with_billing_diagnosis`

**002 - Branch B end-to-end (P0)**
- Status: Ready.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions: RC centers are deployed and healthy; the branch B workflow with a known workflow ID is imported; Customer Care, CDN, and Vendor 2 FAN cards are registered and their endpoints are reachable; `USE_MOCK_LLM=true`; the execution store contains no test-owned branch B execution.
- Steps: (1) submit the fixed "YouTube/Netflix playback is slow" complaint intent and record its execution ID; (2) subscribe to that execution's SSE stream; (3) collect its events through the terminal event; (4) compare the order of the received stage events and task-completion events; (5) list the domain agents identified by the received task events; (6) query the terminal execution by the recorded ID; (7) query each identified agent task by the recorded IDs.
- Assertions: for step 1, the response returns one execution ID and the recalled workflow ID exactly equals the imported branch B ID; for steps 2 and 3, the terminal status is `complete`; for step 4, every stage event precedes its corresponding task-completion event; for step 5, the task events identify exactly Customer Care, CDN, and Vendor 2 FAN with no other domain agent; for step 6, the result contains the required diagnosis-conclusion and handling-suggestions fields; for step 7, every identified task is successful.
- finally/Cleanup: in a `finally` block, close the SSE subscription and delete the test-owned execution and imported workflow; retain session-baseline agent cards. Recovery assertion: subsequent queries return not found for the deleted execution and workflow, all three baseline agents remain registered and reachable, and no test-owned task remains running.
- Automation: `e2e/system-integration/complaint-handling/test_complaint_handling.py::test_submit_streaming_complaint_completes_with_cdn_diagnosis`

**003 - Recall routing correctness (P1)**
- Status: Ready. The unknown-category scenario is covered independently by 007 and is not part of this case.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions: RC centers are healthy; branch A and branch B workflows with distinct known IDs are imported; all agents required by both workflows are registered and reachable; `USE_MOCK_LLM=true`.
- Steps: (1) submit the branch A intent in a new execution and record its recalled workflow ID; (2) wait for that execution to terminate and record its terminal status; (3) submit the branch B intent in a separate new execution and record its recalled workflow ID; (4) wait for that execution to terminate and record its terminal status; (5) query both execution records by their distinct execution IDs; (6) compare each stored workflow ID with the ID captured for its own submission.
- Assertions: for step 1, the A execution recalls exactly the branch A workflow ID and does not recall the branch B ID; for step 2, the A execution reaches `complete`; for step 3, the B execution recalls exactly the branch B workflow ID and does not recall the branch A ID; for step 4, the B execution reaches `complete`; for step 5, the execution IDs remain distinct; for step 6, each stored workflow ID equals the ID captured for its own submission. Compare identifiers and statuses, never generated wording.
- finally/Cleanup: in a `finally` block, delete both test-owned executions and both imported workflows. Recovery assertion: queries for all deleted IDs return not found, no test-owned execution remains active, and the registered agent-card baseline is unchanged.
- Automation: `e2e/system-integration/complaint-handling/test_complaint_handling.py::test_submit_known_intents_recalls_matching_workflow`

**004 - Agent retrieval correctness (P1)**
- Status: Ready.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions: RC centers are healthy; branch A and branch B workflows are imported with known IDs; five uniquely identifiable cards for Customer Care, Billing, CDN, Vendor 1 FAN, and Vendor 2 FAN are registered with known org, name, and capability fields; registry audit or execution-event capture is enabled; `USE_MOCK_LLM=true`.
- Steps: (1) execute the branch A intent; (2) read the cards captured as retrieved for its execution ID; (3) execute the branch B intent in a separate execution; (4) read the cards captured as retrieved for that execution ID; (5) query the registered-card records; (6) compare the org, name, and capabilities of every retrieved card with its registered record; (7) check each execution's retrieved set for a card that belongs only to the other branch; (8) check each execution's retrieved set for duplicate or unexpected agent retrievals.
- Assertions: for steps 1 and 2, branch A retrieves exactly {Customer Care, Billing, Vendor 1 FAN}; for steps 3 and 4, branch B retrieves exactly {Customer Care, CDN, Vendor 2 FAN}; for steps 5 and 6, every retrieved card's org, name, and capabilities equal its registered record; for step 7, each execution contains no card belonging only to the other branch; for step 8, no duplicate or unexpected agent retrieval appears.
- finally/Cleanup: in a `finally` block, stop audit capture and delete both executions and imported workflows; remove only test-owned cards. Recovery assertion: deleted execution and workflow IDs return not found, audit capture is stopped, and the registry contains exactly its pre-case card set.
- Automation: `e2e/system-integration/complaint-handling/test_complaint_handling.py::test_execute_branches_retrieves_only_required_agent_cards`

**005 - Expert handoff (P1)**
- Status: Draft — blocked by Open Item 1; the NOC endpoint, payload schema, and escalated terminal-state contract are unconfirmed. This expected design must not be implemented or counted in exit gates.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions (planned): RC centers and branch agents are healthy; the NOC handoff stub is running at the eventually contracted endpoint; scenario data forces an unresolved edge case; the expected payload schema and terminal-state name have been confirmed; `USE_MOCK_LLM=true`.
- Steps (planned): (1) start capture on an empty NOC stub; (2) submit the unresolved edge-case intent; (3) collect the execution event stream until the contracted terminal event; (4) retrieve the execution history; (5) retrieve the NOC stub's received requests.
- Assertions (planned, after contract confirmation): for steps 1 and 2, exactly one escalation request is received for the execution; for step 3, the terminal state equals the contracted escalated state and is neither `complete` nor an unclassified failure; for steps 4 and 5, the request validates against the confirmed schema and contains every per-agent task result and timestamp from execution history in the contracted order, with no missing diagnostic field.
- finally/Cleanup (planned): in a `finally` block, close capture, reset the stub, and delete test-owned executions, workflows, and unresolved scenario data. Recovery assertion: the stub has no captured requests, deleted resource IDs return not found, no test-owned task remains active, and the agent baseline is healthy.
- Automation: planned after contract confirmation — `e2e/system-integration/complaint-handling/test_complaint_handling.py::test_submit_unresolved_complaint_hands_off_full_diagnostic_context`

**006 - Domain agent unavailable (P1)**
- Status: Ready.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions: RC centers and branch A dependencies are healthy; the branch A workflow is imported; a test-controlled mechanism can make only the Billing endpoint unreachable and restore it; Customer Care and Vendor 1 FAN remain reachable; `USE_MOCK_LLM=true`; the pre-case registry health snapshot is recorded.
- Steps: (1) make the Billing endpoint unreachable; (2) run the health/route probe for Billing and for the other two branch A agents; (3) submit the branch A intent and record its execution ID; (4) collect its events until a terminal execution state; (5) query the execution logs for the recorded execution ID; (6) query the execution tasks for the recorded execution ID; (7) restore the Billing endpoint; (8) run Billing's health/route probe again.
- Assertions: for steps 1 and 2, only Billing is unreachable; for steps 3 and 4, execution reaches terminal state `failed`, never `complete`, and emits a terminal event within the framework timeout; for step 5, the structured error identifies the Billing agent ID; for step 6, Customer Care and Vendor 1 FAN task states are terminal and no task remains `running`; for steps 7 and 8, Billing becomes reachable and its registry health equals the pre-case snapshot.
- finally/Cleanup: in a `finally` block, remove the route block or restart the mock agent even after assertion failure, close event capture, and delete the test-owned execution and workflow. Recovery assertion: Billing and the other baseline agents are reachable and healthy, no injected route block remains, deleted IDs return not found, and no orphaned task remains running.
- Automation: `e2e/system-integration/complaint-handling/test_complaint_handling.py::test_submit_outage_with_billing_unreachable_reports_failed_terminal_state`

**007 - Unknown category fallback (P2)**
- Status: Draft — blocked by Open Item 2; execution is excluded until ready.
- Expected design: after the product contract is confirmed, submit an unknown-category intent and assert the contracted explicit no-match response or escalation, a deterministic response structure, and that neither branch A nor branch B executes. Until then, do not implement this case or count it in exit gates.

**008 - Concurrent complaints (P2)**
- Status: Ready.
- Steps: (1) submit one A and one B complaint concurrently and record their separate execution IDs; (2) subscribe to their separate SSE streams; (3) wait for both executions to terminate; (4) collect their task and result records; (5) compare the workflow IDs, agent sets, event identifiers, and result structures of the two complaints.
- Assertions: for steps 1 and 2, distinct execution IDs and independent SSE streams are returned for A and B; for steps 3 and 4, both executions complete and every task reaches a successful terminal state; for step 5, A recalls only workflow A and invokes exactly the A agent set, B recalls only workflow B and invokes exactly the B agent set, no identifiers, events, or result payloads cross complaints, and each result matches its own sequential expected structure.
- finally/Cleanup: close both streams and delete both executions and test-owned workflows in a `finally` block. Recovery assertion: no test-owned execution or task remains active and the registry/workflow baseline is restored.

## 6. Assertion and Evidence Rules

- Deterministic assertions only: status codes, workflow/agent identifiers, SSE event types and ordering, terminal execution states, required-field presence. **Never assert on LLM-generated text content** (case-table rule; applies even when `USE_MOCK_LLM=false`);
- No `sleep`; use framework wait/retry (`eventually`, SSE terminal-event waits, Playwright auto-wait where UI is involved) - Framework §6.3;
- No implicit ordering between cases; 003/004 may group closely related checks in one test function per Framework §6.3, but each case ID maps to independently runnable logic;
- On failure preserve: SSE/event trace, execution records, relevant Pod logs, K8s events into `EVIDENCE_DIR` (Framework §6.3);
- Every case cleans up in teardown: executions, imported workflows, test-owned agent cards, stub state (Framework §6.5).

## 7. Tags, Naming, and Code Layout

- Test file: `e2e/system-integration/complaint-handling/test_complaint_handling.py` (cross-feature SIT scenario home per Framework §5.1 `system-integration/`; feature-local system cases remain under `e2e/<feature>/system-integration/` per §6.2);
- Test functions: `test_<action>_<expected_result>` (e.g., `test_submit_outage_complaint_completes_with_billing_diagnosis`); optional class grouping `TestComplaintHandling`;
- Tags - all five dimensions on every case (Framework §6.4):

| Dimension | Values for S1 |
| --- | --- |
| feature | `system-integration` |
| environment | `online` (helm cluster) / `offline` (compose) as supported by the lab |
| components | Candidate scenario labels: `orchestration-center`, `registry-center`, `workflow-exec-engine`, `a2a-t-sdk`, `mockagent`; actual labels are selected per case from the CSV Component Deps |
| priority | `P0` / `P1` / `P2` per §5 matrix |
| execution | `smoke` (Ready cases 001, 002), `full` (Ready cases 003, 004, 006, 008); Draft cases are excluded until ready |

- Case table rows follow the fixed 16-column template (`docs/templates/testcases-template-fields.md`), Module = `system-integration`. The actual code component labels must be taken from each case row's CSV Component Deps; the scenario-level candidate list above must not be copied wholesale onto every case. Orchestration keys (`language_profile`, `protocol_primitive`, `execution_strategy`, `environment`) go in Notes.

## 8. Execution, CI Mapping, and Gates

| Trigger | S1 Ready subset | Basis |
| --- | --- | --- |
| Daily build | smoke: Ready 001, 002 | Framework §7.2 (daily = full FIT + smoke SIT) |
| RC-0 / RC-1 | full: Ready 001-004, 006, 008 | Framework §7.2, §4.3.2/§4.3.3 |
| Pre-release | all currently Ready S1 cases (001-004, 006, 008) rerun on RC | Framework §7.2 |

- Draft cases 005 and 007 are `excluded until ready`: they are not in smoke/full execution sets or the current release-exit denominator. A Draft case may enter these sets only after its blockers are resolved, its definition is finalized, and its matrix status changes to Ready.
- SIT exit gate: the pass rate over currently Ready S1 cases only = 100%, with no skips among those cases (Framework §8.3). A failing Ready S1 case blocks release entry; `skip-temporarily` is not an acceptable end state for SIT at release time. Draft cases neither pass nor fail the gate and must not be counted as skips;
- Defects: failed cases open issues with evidence attached; P0 respond within 24h and fix in current release; regression case added after fix (Framework §9);
- Results archived per release: plan in `docs/plans/<YY>-<season>/`, report in `docs/reports/<YY>-<season>/`, JUnit XML + report per Framework §7.1.

## 9. Open Items (case-specific blockers)

| # | Item | Owner | Impact |
| --- | --- | --- | --- |
| 1 | NOC expert handoff interface contract (endpoint, payload schema, terminal state naming) | orchestration-center WG | Blocks 005 assertions; until confirmed, 005 stays draft |
| 2 | Unknown-category fallback contract (explicit no-match response vs escalation) | orchestration-center WG | Blocks 007 expected result |
| 3 | Real-LLM variant inclusion in RC runs (deterministic assertions only) | Integration Testing WG | Optional variant; default CI stays `USE_MOCK_LLM=true` |
