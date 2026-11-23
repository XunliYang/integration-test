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
| `orchestration-center` (backend `orchestrate` :5001, `host_agent`, `samples/`) | Workflow recall and execution; complaint handling agent host | Runtime dependency on registry-center (`AGENT_REGISTRY_URL` / shared `openan-net`); `workflow-exec-engine>=0.1.1,<0.2`, `a2a-t-sdk>=1.2.0,<2` |
| `a2a-t-sdk-python` | Agent-to-agent task collaboration | Version per orchestration-center constraint above |
| Domain agents (Customer Care, Billing, CDN, Vendor FAN) | Mock/sample agents from `openan-demo` mockagent scenario package or orchestration-center `samples/` | Endpoints via `MOCK_AGENTS_HOST` / `SAMPLE_AGENTS_HOST` |
| NOC expert endpoint (simulated) | Receives escalation with diagnostic context | Test-side stub; contract to be confirmed (see §9) |
| LLM dependency | Intent classification / workflow generation where used | `USE_MOCK_LLM=true` for deterministic CI runs; real-LLM runs are an optional variant with deterministic assertions only |

All components deploy from the RC image package under test (`IMAGE_REGISTRY` / `IMAGE_TAG`), in `DEPLOY_MODE=online-helm` (real cluster, `KUBECONFIG`) or `offline-compose`. SIT runs on a real environment per Framework §5.1; mock agents are allowed as scenario participants, but the centers under test must be the real RC builds.

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

| Case ID | Name | Variant coverage | Priority | Execution |
| --- | --- | --- | --- | --- |
| `[SIT-complaint-handling-001]` | Branch A (outage/billing) end-to-end closed loop | A, autonomous closure | P0 | smoke, full |
| `[SIT-complaint-handling-002]` | Branch B (streaming/speed) end-to-end closed loop | B, autonomous closure | P0 | smoke, full |
| `[SIT-complaint-handling-003]` | Intent-to-workflow recall routing correctness | A vs B vs unknown category | P1 | full |
| `[SIT-complaint-handling-004]` | Agent retrieval matches recalled workflow | A and B card sets | P1 | full |
| `[SIT-complaint-handling-005]` | Expert handoff carries full diagnostic context | A or B, unresolved edge case | P1 | full |
| `[SIT-complaint-handling-006]` | Required domain agent unavailable: graceful degradation | A with Billing agent down | P1 | full |
| `[SIT-complaint-handling-007]` | Unknown complaint category: defined fallback | neither A nor B | P2 | full |
| `[SIT-complaint-handling-008]` | Concurrent complaints isolation | A + B in parallel | P2 | full |

P0/P1 cases must be `Automatable=Yes` with Requirement Link filled (scenario epic issue) per the case-table template rules.

### 5.1 Case definitions (preconditions / steps / assertions / cleanup)

**001 - Branch A end-to-end (P0)**
- Preconditions: RC centers deployed and healthy; branch A workflow imported; Customer Care / Billing / Vendor 1 FAN agents registered and reachable; `USE_MOCK_LLM=true`.
- Steps: (1) submit the "no internet access" complaint intent; (2) subscribe to the execution SSE event stream; (3) wait for terminal execution status via framework wait/retry (no `sleep`).
- Assertions (all explicit): workflow recalled is the branch A definition (identifier match, not text match); execution reaches terminal status `complete`; SSE sequence contains stage events and A2A-T task events for exactly the three branch A agents; result payload contains a diagnosis conclusion structure (required fields present) and handling suggestions field; each invoked agent reports task success state.
- Cleanup: delete created execution records / test-owned workflows per fixture rules; deregister nothing owned by the session baseline.

**002 - Branch B end-to-end (P0)**
- Same structure as 001 with branch B intent, workflow, and agent set (Customer Care / CDN / Vendor 2 FAN); assertions mirror 001 on the branch B identifiers.

**003 - Recall routing correctness (P1)**
- Steps: submit branch A intent, branch B intent, and an unknown-category intent in separate executions.
- Assertions: A intent recalls the A workflow ID; B intent recalls the B workflow ID; unknown intent produces the defined fallback (see 007), never a silently wrong branch. Routing assertions compare workflow identifiers/status codes, not LLM-generated wording.

**004 - Agent retrieval correctness (P1)**
- Steps: execute both branches; capture the agent cards actually pulled from Registry Center during execution (via execution context/events or registry query audit).
- Assertions: branch A pulls exactly {Customer Care, Billing, Vendor 1 FAN}; branch B exactly {Customer Care, CDN, Vendor 2 FAN}; card fields (org/name/capabilities) match the registered cards; no cross-branch agent leakage.

**005 - Expert handoff (P1)**
- Preconditions: NOC handoff stub running; scenario data forces an unresolved edge case (standard workflow cannot resolve).
- Steps: submit the edge-case intent; wait for escalation.
- Assertions: escalation reaches the stub exactly once; payload contains the full diagnostic history (per-agent task results and timestamps present and ordered); execution terminal state reflects "escalated", not "complete" or silent failure; no partial diagnosis is dropped (field-level completeness check).

**006 - Domain agent unavailable (P1)**
- Preconditions: Billing agent endpoint made unreachable (test-controlled fault injection, e.g., stop the mock agent or block its route).
- Steps: submit branch A intent; observe execution.
- Assertions: execution terminates in a defined failed/degraded state with a clear error identifying the unavailable agent; no false `complete`; SSE/log evidence records the failure reason; remaining agents' state is consistent (no orphaned running tasks after teardown).
- Cleanup: restore the Billing agent; verify registry health state recovers.

**007 - Unknown category fallback (P2)**
- Assertions: system returns the defined fallback behavior (explicit "no matching workflow" response or escalation per product contract - contract to be confirmed, §9); never executes an arbitrary branch; response is deterministic in structure.

**008 - Concurrent complaints (P2)**
- Steps: submit one A and one B complaint concurrently.
- Assertions: both reach their own correct terminal states; execution contexts, agent task IDs, and SSE streams do not cross-contaminate (assert per-execution identifiers); results identical to sequential runs 001/002.

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
| components | `orchestration-center`, `registry-center`, `a2a-t-sdk`, `mockagent` |
| priority | `P0` / `P1` / `P2` per §5 matrix |
| execution | `smoke` (001, 002), `full` (all) |

- Case table rows follow the fixed 16-column template (`docs/templates/testcases-template-fields.md`), Module = `system-integration`, Component Deps as listed above; orchestration keys (`language_profile`, `protocol_primitive`, `execution_strategy`, `environment`) go in Notes.

## 8. Execution, CI Mapping, and Gates

| Trigger | S1 subset | Basis |
| --- | --- | --- |
| Daily build | smoke: 001, 002 | Framework §7.2 (daily = full FIT + smoke SIT) |
| RC-0 / RC-1 | full: 001-008 | Framework §7.2, §4.3.2/§4.3.3 |
| Pre-release | all S1 cases rerun on RC | Framework §7.2 |

- SIT exit gate: S1 pass rate = 100%, no skips allowed (Framework §8.3). A failing S1 case blocks release entry; `skip-temporarily` is not an acceptable end state for SIT at release time;
- Defects: failed cases open issues with evidence attached; P0 respond within 24h and fix in current release; regression case added after fix (Framework §9);
- Results archived per release: plan in `docs/plans/<YY>-<season>/`, report in `docs/reports/<YY>-<season>/`, JUnit XML + report per Framework §7.1.

## 9. Open Items (must be resolved before case implementation)

| # | Item | Owner | Impact |
| --- | --- | --- | --- |
| 1 | NOC expert handoff interface contract (endpoint, payload schema, terminal state naming) | orchestration-center WG | Blocks 005 assertions; until confirmed, 005 stays draft |
| 2 | Unknown-category fallback contract (explicit no-match response vs escalation) | orchestration-center WG | Blocks 007 expected result |
| 3 | Mock agent scenario package availability for Billing / CDN / Vendor FAN in `openan-demo` | Integration Testing WG | Blocks 002/004/006 if only FAN samples exist today |
| 4 | Real-LLM variant inclusion in RC runs (deterministic assertions only) | Integration Testing WG | Optional variant; default CI stays `USE_MOCK_LLM=true` |