# SIT Specification S5: SPN Dedicated-Line Complaint - Full Process

> *Version: v0.1 (Draft)*
> *Maintained by: OpenAN Integration Testing Working Group*
> *Language: English*
> *Scenario slug: `spn-line-full-process` - Case IDs: `[SIT-spn-line-full-process-<number>]`*
> *Scenario baseline: [sit-scenarios.md](../sit-scenarios.md) S5*
> *Governance baseline: [OpenAN Integration Testing Process and Framework](../OpenAN%20Integration%20Testing%20Process%20and%20Framework.md) (cited as "Framework" below)*

---

## 1. Scope

This specification defines the SIT requirements for scenario S5 (SPN Dedicated-Line Complaint, full cross-city process), derived from China Mobile Guangdong Phase 2 (https://openan.dev/best-practices/guangdong-mobile-a2at-usecase.html).

**In scope** - the full complaint closed loop across two sub-flows:

**Fault diagnosis sub-flow:**
1. Ticket grab: the WAIMO fault center agent grabs the complaint ticket from the EOMS process center (simulated by a test stub);
2. Three-layer dispatch: WAIMO agent -> transmission workbench agent -> two SPN domain agents;
3. Parallel diagnosis: the two SPN domain agents diagnose the complaint content in parallel; results are summarized into a consolidated conclusion;
4. Write-back: diagnosis results are written back to the EOMS process center.

**Service restoration sub-flow:**
5. Restoration capability check: whether the OMC system supports restoration for the located fault;
6. Authorization: the workbench performs authorization (Authorization-T business gate) before any repair action;
7. Repair execution: restoration executed toward the (simulated) OMC / line;
8. Completion notification: OMC notifies the workbench that restoration completed (Notification-T);
9. Performance verification: the workbench verifies that service performance indicators have recovered;
10. Recovery notification and closure: the workbench reports the service-recovery notification to the WAIMO fault center; the ticket closes automatically.

**Protocol capabilities exercised in the business loop**: Negotiation-T (cross-layer negotiation driving dispatch/decisions), Authorization-T (repair gate), Notification-T (restoration completion / recovery reporting) - on top of the basic capabilities covered by S4.

**What distinguishes S5 from neighboring scenarios:**

| Property | S4 (`spn-line-diagnosis`) | S5 (this spec) |
| --- | --- | --- |
| Agent layers | Two (workbench -> SPN) | Three (WAIMO -> workbench -> SPN x2) |
| Topology | Single city | Cross-city, multi-vendor (emulated in lab) |
| Closed-loop scope | Diagnosis only, human confirmation | Diagnosis + authorized repair + verification + automatic closure |
| Protocol capabilities | Basic only | Negotiation-T / Authorization-T / Notification-T in the loop |
| SPN participants | One domain agent | Two domain agents, parallel diagnosis + summarization |

**Out of scope** (do not duplicate here):

- Diagnosis-only behavior and integration-approach equivalence (direct vs orchestration-driven) -> S4; S5 reuses S4's line-data fixtures and diagnosis assertions where the diagnosis sub-flow is concerned;
- Protocol schema conformance, state-machine alignment, dual-transport equivalence of Negotiation-T / Authorization-T / Notification-T -> `[SIT-a2at-protocol-*]` and specialized A2A-T protocol testing (Framework §10). S5 asserts these capabilities **as business gates and events in the loop** (authorization precedes repair; notification triggers verification), not protocol schemas;
- Mobile-domain complaint handling -> S2; energy-saving control -> S3; broadband branches -> S1;
- Single-API / single-module checks -> FIT; performance / stability thresholds -> specialized testing.

## 2. System Under Test

### 2.1 Topology (three layers, cross-city, multi-vendor)

```
EOMS process center (test stub)
   ^  ticket grab / diagnosis write-back / closure state
   |
WAIMO fault center agent  [vendor role: Yiyang]  (host_agent + workflow-exec-engine + a2a-t-sdk)
   |  dispatch / recovery notification receipt
   v
transmission workbench agent  [vendor role: Kaitong]  (host_agent + workflow-exec-engine + a2a-t-sdk)
   |  authorization gate / performance verification
   +---------------------------+
   | A2A-T (Negotiation-T / Task-T)   |
   v                           v
SPN domain agent 1 [Huawei role]   SPN domain agent 2 [Huawei role]
   (parallel diagnosis, cross-city ends)
   |
   v
OMC / line simulator (test-owned stateful stub:
   line state, restoration-support flag, performance metrics,
   repair commands, completion notifications)

Registry Center: all agents registered (security capabilities, registration & query)
Orchestration Center: workflow composition / storage / retrieval
   (e.g., generate diagnosis message -> parallel diagnosis with two SPN agents -> summarize)
```

- Three agent layers participate in execution; EOMS remains a process-center stub, the OMC/line is always simulated;
- Cross-city is emulated by placing the two SPN domain agents in separate failure domains (namespaces / network segments) with the real network path between layers; multi-vendor heterogeneity is emulated via SDK language variants (Python / Java) where sample agents are available - variants, not separate scenarios;
- The orchestration workflow under test follows the published composition: generate complaint diagnosis message -> diagnose in parallel with two SPN domain agents -> summarize diagnosis results.

### 2.2 Components and dependency constraints

| Component | Role in S5 | Constraint |
| --- | --- | --- |
| `registry-center` (HTTPS :5000) | Registration / discovery / security for all three layers | mTLS client identity (`REGISTRY_CLIENT_CERT/KEY/CA_CERT`); owner isolation across vendor-role orgs |
| `orchestration-center` (:5001) | Workflow composition / storage / retrieval; parallel diagnosis orchestration | `workflow-exec-engine>=0.1.1,<0.2`, `a2a-t-sdk>=1.2.0,<2`; runtime dependency on registry-center |
| WAIMO fault center agent | Ticket grab, dispatch, recovery notification receipt, closure | Sample mock agent in the Yiyang role; embeds workflow-exec-engine + a2a-t-sdk |
| Transmission workbench agent | Authorization gate, performance verification, recovery reporting | Sample mock agent in the Kaitong role; same SDK constraints |
| SPN domain agents x2 | Parallel diagnosis; restoration execution toward OMC simulator | Sample mock agents in the Huawei role; S4 line-data scenario payloads reused |
| EOMS process center stub | Ticket source, write-back receiver, closure state | Test-side stub; reuse S2/S4 stub pattern |
| OMC / line simulator | Line state, restoration-support flag, performance metrics, repair command log, completion notification emission | Test-owned; contracts per §9 items 2-4 |
| LLM dependency | Diagnosis / negotiation reasoning where used | `USE_MOCK_LLM=true` for deterministic CI runs; real-LLM runs are an optional variant with deterministic assertions only |

All centers and agents under test deploy from the RC image package (`IMAGE_REGISTRY` / `IMAGE_TAG`), `DEPLOY_MODE=online-helm` or `offline-compose`, real environment per Framework §5.1.

## 3. Environment and Configuration Contract

Reuse `e2e/.env.template` (Framework §6.6):

| Variable | Usage in S5 |
| --- | --- |
| `KUBECONFIG`, `OPENAN_NAMESPACE`, `DEPLOY_MODE` | Cluster access; cross-city emulation via namespaces / network segments |
| `REGISTRY_CENTER_URL`, `REGISTRY_CLIENT_CERT`, `REGISTRY_CLIENT_KEY`, `REGISTRY_CA_CERT` | Registry access with mTLS identity |
| `ORCHESTRATION_CENTER_URL`, `ORCH_ACCESS_PASSWORD` | Orchestration access |
| `LLM_CHAT_*`, `A2AT_LLM_*`, `USE_MOCK_LLM` | LLM dependency; mock toggle for determinism |
| `MOCK_AGENTS_HOST`, `SAMPLE_AGENTS_HOST` | WAIMO / workbench / SPN agent endpoints |
| `IMAGE_REGISTRY`, `IMAGE_TAG` | RC build under test |
| `EVIDENCE_DIR` | Failure scene preservation |

New variables, if the lab exposes stubs as services (introduce in the same PR that updates `e2e/.env.template` and README): `EOMS_STUB_URL` (may share the S2 stub), `OMC_SIM_URL`.

Rules: no hardcoded IPs, credentials, or tokens; the OMC/line simulator is test infrastructure, never a production OMC endpoint.

## 4. Test Data and Fixtures

| Fixture | Scope | Content | Cleanup |
| --- | --- | --- | --- |
| Agent cards | module | WAIMO, workbench, SPN x2 registered under distinct vendor-role orgs with valid JWS signatures | Deregister test-owned cards |
| Line-data scenarios | function | **Reused from S4** (`utils/` shared): far-end optical module fault, type mismatch, attenuation misconfiguration, all-normal, far-end data missing; each with precomputed root cause | Reset scenario state per case |
| OMC / line simulator | function | Stateful stub: line state; restoration-support flag (supported / unsupported per scenario); performance metrics (baseline / degraded / recovered sets); repair command log; emits completion notification on repair | Reset state, flags, metrics, command log; **verify line baseline restoration** |
| Complaint tickets | function | Fixed ticket payloads referencing the line under test | Stateless |
| Diagnosis workflow | module | Published composition: generate diagnosis message -> parallel diagnosis (two SPN agents) -> summarize | Delete imported workflow in teardown |
| Authorization policy | module | Grant / deny configuration for the workbench authorization gate (test-controlled) | Restore default policy |
| EOMS stub | function | Ticket source; write-back and closure-state capture | Reset captured state per case |
| Login session | session (read-only) | Orchestration Center session | Not shared mutable state (Framework §6.5) |

**Safety red lines** (apply to every S5 case):

1. All repair commands target the OMC/line simulator only;
2. **No repair action without a prior successful authorization event** (ordering assertion, standing);
3. **No automatic closure without a passed performance verification** (ordering assertion, standing);
4. Every case that changes line state must restore baseline in teardown and assert the restoration;
5. No case depends on wall-clock time; metric sets and notifications are fixture-driven.

- Every case independently repeatable; full suite runs twice with identical results, no manual reset.

## 5. Case Matrix

| Case ID | Name | Sub-flow / variant | Priority | Status | Execution |
| --- | --- | --- | --- | --- | --- |
| `[SIT-spn-line-full-process-001]` | Full E2E happy path: grab -> parallel diagnosis -> write-back -> authorization -> repair -> notification -> verification -> recovery -> closure | both sub-flows | P0 | Draft | excluded until ready |
| `[SIT-spn-line-full-process-002]` | Parallel diagnosis with two SPN agents and correct summarization + write-back | diagnosis sub-flow | P0 | Draft | excluded until ready |
| `[SIT-spn-line-full-process-003]` | Authorization gate: granted precedes repair; denied blocks repair | restoration, Authorization-T | P1 | Draft | excluded until ready |
| `[SIT-spn-line-full-process-004]` | Completion notification triggers performance verification and recovery reporting | restoration, Notification-T | P1 | Draft | excluded until ready |
| `[SIT-spn-line-full-process-005]` | Performance not recovered: no false recovery notification, defined retry/escalation | restoration, verification failure | P1 | Draft | excluded until ready |
| `[SIT-spn-line-full-process-006]` | OMC restoration unsupported: defined alternative path, diagnosis still written back | restoration capability variant | P1 | Draft | excluded until ready |
| `[SIT-spn-line-full-process-007]` | Cross-layer negotiation occurs and converges within bounds | Negotiation-T in the loop | P1 | Draft | excluded until ready |
| `[SIT-spn-line-full-process-008]` | One SPN agent unreachable during parallel diagnosis: defined partial-result handling | diagnosis fault injection | P1 | Draft | excluded until ready |
| `[SIT-spn-line-full-process-009]` | Repair execution failure: defined degraded state, consistent line state | restoration fault injection | P1 | Draft | excluded until ready |
| `[SIT-spn-line-full-process-010]` | Concurrent tickets isolation and closure idempotency | concurrency | P2 | Draft | excluded until ready |

`Ready` means that every contract and environment dependency for the case is resolved and reviewed. A case blocked by any §9 item is `Draft`; §9 item 7 currently blocks the topology setup for every case, so there are no Ready cases. Only a Ready case may retain its `smoke` or `full` execution membership. Draft cases must not be implemented, executed as release evidence, or counted in exit-gate denominators.

P0/P1 rows use Requirement Link https://github.com/project-openan/integration-test/issues/34 and `Automatable=Yes` as the final automation requirement; that future automation requirement does not make a Draft row currently executable. All case definitions below use the same requirement link.

### 5.1 Case definitions (preconditions / steps / assertions / cleanup)

**001 - Full E2E happy path (P0)**
- **Status:** Draft; blocked by §9 items 1, 2, 3, and 7.
- **Requirement:** https://github.com/project-openan/integration-test/issues/34
- **Preconditions:** RC centers deployed; all four agents registered; diagnosis workflow imported; S4 scenario (a) loaded (far-end optical module fault); OMC simulator configured with restoration supported and baseline/degraded/recovered metric sets; authorization policy = grant; EOMS stub ready; `USE_MOCK_LLM=true`. Both SPN agent fixtures are attached to one test-controlled synchronous response barrier. The barrier holds each agent's response after recording its diagnosis-start event and has a bounded test wait.
- **Steps:**
  1. Reset event, command, notification, and ticket captures.
  2. Arm the two-agent barrier before publishing the complaint ticket.
  3. Publish the ticket at the EOMS stub.
  4. Capture the WAIMO grab, workbench dispatch, workflow identifier, and the two child-branch identifiers.
  5. Wait within the barrier bound for both SPN agents to report diagnosis start; a timeout fails the step and still enters cleanup.
  6. Release both held responses only after both start events have been recorded.
  7. Capture both SPN results, the aggregation event, and the diagnosis write-back at EOMS.
  8. Observe authorization, repair, OMC completion notification, performance verification, recovery notification, and EOMS closure using framework waits.
- **Assertions:**
  - **A1 (Steps 1 and 2):** Captures are empty, the ticket ID is unique, and the barrier has two registered participants before the ticket is published.
  - **A2 (Steps 3 and 4):** The grab event precedes dispatch; dispatch reaches the workbench and then two structurally distinct parallel branches, one for each expected SPN agent identity, under the imported workflow identifier.
  - **A3 (Steps 5 and 6):** Both branch-start events carry the same ticket and parent workflow identifiers and occur before the test's barrier-release event. Both result events occur after that release. Parallelism is therefore established by the two branches and controlled start/result ordering, never solely by natural timing overlap.
  - **A4 (Step 7):** Exactly one consolidated conclusion references both branch results and matches the precomputed root cause. The EOMS write-back contains the same ticket ID, conclusion, contributing agent IDs, and event timestamps.
  - **A5 (Step 8):** A grant decision precedes the first simulator repair command; the completion notification precedes verification; verification equals the recovered metric fixture; a passed verification precedes the recovery notification; the recovery notification precedes closure; and EOMS records exactly one closure for the ticket. Decision and notification field assertions use only the confirmed §9 contracts.
- **Finally / Cleanup:** In a `finally` path, release the barrier even after start-wait timeout or assertion failure and assert that neither agent fixture remains blocked. Restore the line baseline and assert equality with the baseline snapshot; reset both SPN fixtures, stubs, policy, metrics, and scenario state; verify that no repair or notification capture leaks into the next case.
- **Automation:** `e2e/system-integration/spn-line-full-process/test_spn_line_full_process.py::test_full_process_closes_after_verified_restoration` — planned after contract confirmation; must not be implemented or counted toward release exit while Draft.

**002 - Parallel diagnosis and summarization (P0)**
- **Status:** Draft; blocked by §9 items 5 and 7.
- **Requirement:** https://github.com/project-openan/integration-test/issues/34
- **Preconditions:** Centers and all four agents are registered; the published diagnosis workflow is imported; S4 scenario (a) and its expected root cause are loaded; EOMS capture is empty; `USE_MOCK_LLM=true`. The two SPN fixtures use the same bounded, test-controlled start barrier as 001. No restoration is requested.
- **Steps:**
  1. Arm the barrier.
  2. Reset captures.
  3. Publish a diagnosis-only complaint ticket.
  4. Capture the generated diagnosis message, workflow ID, and the two parallel child branches.
  5. Wait for both agent-start events within the barrier bound.
  6. Release both responses together.
  7. Capture both results, summarization, and EOMS write-back.
  8. Wait for the diagnosis-only terminal state.
- **Assertions:**
  - **A1 (Steps 1, 2, and 3):** The barrier has exactly the two expected SPN participants and no repair command exists before publication.
  - **A2 (Step 4):** The workflow sequence is generate message -> parallel diagnose -> summarize; the workflow ID matches the imported composition and each child branch has the expected distinct agent ID.
  - **A3 (Steps 5 and 6):** Both starts precede the controlled release and both results follow it; neither branch result is fabricated by the fixture.
  - **A4 (Steps 7 and 8):** One consolidated conclusion contains evidence linked to both branch IDs and the precomputed root-cause classification. The EOMS payload contains the ticket ID, conclusion structure, both contributing agents, and timestamps. The diagnosis-only terminal state is reached and the OMC repair-command log remains empty.
- **Finally / Cleanup:** Release the barrier in all outcomes and assert that no participant remains waiting. Delete test ticket/workflow-run state, reset agent fixtures and EOMS captures, restore line data and metrics to baseline, and assert baseline equality and an empty repair-command log.
- **Automation:** `e2e/system-integration/spn-line-full-process/test_spn_line_full_process.py::test_parallel_diagnosis_summarizes_both_agent_results` — planned after contract confirmation; must not be implemented or counted toward release exit while Draft.

**003 - Authorization gate (P1)**
- **Status:** Draft; blocked by §9 items 1 and 7.
- **Requirement:** https://github.com/project-openan/integration-test/issues/34
- **Preconditions:** The diagnosis and restoration path is deployed; two independent ticket fixtures use the same fault; restoration is supported; recovered metrics are available; the workbench policy fixture supports test-controlled grant and deny; the expected denied state and escalation record will be taken from the confirmed §9 item 1 contract.
- **Steps:**
  1. Set policy = grant.
  2. Publish the first ticket.
  3. Observe diagnosis write-back, the authorization decision, repair, verification, recovery, and terminal state.
  4. Reset all ticket, policy, event, and simulator captures.
  5. Restore the line baseline.
  6. Set policy = deny.
  7. Publish the second ticket.
  8. Observe diagnosis write-back, the authorization decision, and the contracted denied terminal path.
  9. Inspect the complete OMC command logs and EOMS states for both tickets.
- **Assertions:**
  - **A1 (Steps 1, 2, and 3):** The first ticket has one grant decision correlated to its authorization request; every repair command occurs after that grant; closure, if reached, occurs only after passed verification.
  - **A2 (Steps 4 and 5):** The second run starts with no events or commands from the first ticket and with the line equal to baseline.
  - **A3 (Steps 6, 7, and 8):** The second ticket receives one deny decision with the contract-required reason, reaches exactly the contracted denied terminal state and escalation path, and its diagnosis write-back is present.
  - **A4 (Step 9):** The denied ticket has zero repair commands, zero recovery notifications, and zero automatic closures; all grant-run commands and events remain correlated only to the first ticket.
- **Finally / Cleanup:** Restore default authorization policy; clear both tickets and all captures; restore line baseline after either run and assert baseline equality; verify that no denied-ticket repair command or closure exists after cleanup.
- **Automation:** `e2e/system-integration/spn-line-full-process/test_spn_line_full_process.py::test_authorization_gate_controls_repair_execution` — planned after contract confirmation; must not be implemented or counted toward release exit while Draft.

**004 - Notification and verification chain (P1)**
- **Status:** Draft; blocked by §9 items 2, 3, and 7.
- **Requirement:** https://github.com/project-openan/integration-test/issues/34
- **Preconditions:** All agents and stubs are ready; restoration is supported; policy = grant; degraded and recovered metric fixtures and the expected baseline are loaded. The OMC simulator holds its completion notification until released by the test. Completion and recovery payload assertions will use the confirmed §9 item 2 contract; metric criteria will use §9 item 3.
- **Steps:**
  1. Publish a ticket.
  2. Observe grab, parallel diagnosis, diagnosis write-back, and authorization grant.
  3. Allow the repair command to reach the simulator while holding its completion notification.
  4. Verify that no verification-start event has yet been emitted.
  5. Release the OMC completion notification.
  6. Capture workbench receipt, verification start, metric reads, and verification result.
  7. Observe the workbench recovery notification, WAIMO receipt/acknowledgement, and EOMS closure.
- **Assertions:**
  - **A1 (Steps 1 and 2):** The expected diagnosis write-back and grant are correlated to the ticket, and no repair precedes the grant.
  - **A2 (Steps 3 and 4):** Exactly one expected repair command is logged and no verification or recovery event occurs before the held completion notification.
  - **A3 (Steps 5 and 6):** The workbench receives one completion Notification-T event from the expected OMC source before verification starts; verification reads the recovered fixture and its result equals the confirmed recovery criterion.
  - **A4 (Step 7):** The recovery notification follows the passed verification and contains the same ticket ID and verification result; WAIMO acknowledgement precedes exactly one EOMS closure.
- **Finally / Cleanup:** Release any held notification to unblock fixtures, then clear notification, metric, command, and ticket captures. Restore baseline line state and metrics and assert exact baseline equality; verify that no further recovery or closure event is emitted after reset.
- **Automation:** `e2e/system-integration/spn-line-full-process/test_spn_line_full_process.py::test_completion_notification_triggers_verified_recovery` — planned after contract confirmation; must not be implemented or counted toward release exit while Draft.

**005 - Performance not recovered (P1)**
- **Status:** Draft; blocked by §9 items 3 and 7.
- **Requirement:** https://github.com/project-openan/integration-test/issues/34
- **Preconditions:** Restoration is supported and policy = grant. The simulator accepts repair and emits completion but continues to return the degraded metric fixture. The contracted verification failure result, bounded retry/escalation sequence, and terminal state from §9 item 3 are recorded as the expected fixture values; no retry bound or escalation behavior is assumed by this specification.
- **Steps:**
  1. Publish the ticket.
  2. Observe diagnosis write-back, authorization grant, repair, and OMC completion notification.
  3. Allow performance verification to read the unchanged degraded metrics.
  4. Capture each contracted verification retry or escalation event until the expected bounded terminal point is reached.
  5. Inspect recovery notifications, EOMS closure state, OMC commands, and the actual line/metric state.
- **Assertions:**
  - **A1 (Steps 1 and 2):** Diagnosis write-back is present, the grant precedes repair, and completion precedes the first verification attempt.
  - **A2 (Step 3):** Verification returns the contract-defined failure result and the observed metric set exactly equals the degraded fixture rather than the recovered fixture.
  - **A3 (Step 4):** The observed retry/escalation sequence and attempt count exactly match the confirmed contract fixture, do not exceed its bound, and terminate at its specified state.
  - **A4 (Step 5):** No notification claims successful recovery, EOMS has no automatic closure, and line state and command records equal the fixture-derived expectation for the commands actually attempted.
- **Finally / Cleanup:** Stop only test-owned retry drivers, clear all simulator and ticket state, force the line and metrics back to baseline, and assert baseline equality. Assert that no late retry, successful recovery notification, or closure appears after cleanup.
- **Automation:** `e2e/system-integration/spn-line-full-process/test_spn_line_full_process.py::test_unrecovered_performance_prevents_recovery_and_closure` — planned after contract confirmation; must not be implemented or counted toward release exit while Draft.

**006 - Restoration unsupported (P1)**
- **Status:** Draft; blocked by §9 items 4 and 7.
- **Requirement:** https://github.com/project-openan/integration-test/issues/34
- **Preconditions:** The OMC simulator restoration-support flag = unsupported for the located fault. Diagnosis fixtures and expected root cause are loaded. The contracted capability-check result, alternative path, and terminal state from §9 item 4 are the expected values; this case does not presume manual escalation or any other specific alternative.
- **Steps:**
  1. Publish the ticket.
  2. Observe the grab, dispatch, two-agent diagnosis, summarization, and EOMS diagnosis write-back.
  3. Trigger the restoration-capability check for the diagnosed fault.
  4. Capture its result.
  5. Observe the contracted alternative path through its terminal state.
  6. Inspect the OMC repair-command log, EOMS write-backs, notifications, and final ticket state.
- **Assertions:**
  - **A1 (Steps 1 and 2):** Both SPN agent IDs contribute to one conclusion matching the expected root cause, and EOMS receives that conclusion for the same ticket.
  - **A2 (Steps 3 and 4):** The capability result exactly equals the confirmed unsupported value and is correlated to the ticket and located fault.
  - **A3 (Step 5):** The observed alternative-path events and terminal state exactly match the confirmed §9 item 4 contract.
  - **A4 (Step 6):** No repair command is issued, no successful recovery notification is emitted, and the ticket is not represented as successfully restored or automatically closed.
- **Finally / Cleanup:** Reset the support flag to its default, clear alternative-path and ticket captures, restore line state and metrics to baseline, and assert baseline equality, an empty repair-command log, and no late recovery or closure event.
- **Automation:** `e2e/system-integration/spn-line-full-process/test_spn_line_full_process.py::test_unsupported_restoration_uses_contracted_alternative_path` — planned after contract confirmation; must not be implemented or counted toward release exit while Draft.

**007 - Cross-layer negotiation (P1)**
- **Status:** Draft; blocked by §9 items 6 and 7.
- **Requirement:** https://github.com/project-openan/integration-test/issues/34
- **Preconditions:** All layers and the workflow are deployed. After §9 item 6 is resolved, the negotiation peers, scenario, expected outcome, and round/timeout bound are stored in a deterministic fixture. No peer selection or SDK default is assumed by this specification; `USE_MOCK_LLM=true`.
- **Steps:**
  1. Publish the fixture ticket that requires the contracted negotiation.
  2. Capture the parent workflow and task identifiers.
  3. Record every Negotiation-T exchange, peer identity, client/server state, and round number until terminal negotiation state.
  4. Observe the dispatch or restoration decision linked to the negotiation outcome.
  5. Compare the complete trace with the fixture's expected peers, outcome, and bound.
- **Assertions:**
  - **A1 (Steps 1 and 2):** The ticket, workflow, and negotiation correlation IDs are present and no negotiation event belongs to another ticket.
  - **A2 (Step 3):** Exchanges occur only between the contracted peer identities; both sides reach aligned terminal states; the observed round count and framework wait remain within the confirmed bound.
  - **A3 (Step 4):** The subsequent decision references the negotiation outcome identifier and exactly matches the contracted outcome-to-action mapping.
  - **A4 (Step 5):** The trace has one terminal outcome, no exchange after termination, and no unconverged or timed-out negotiation is treated as success.
- **Finally / Cleanup:** Cancel only test-owned pending negotiation tasks, clear the negotiation fixture and captures, restore policy and line baseline, and assert no active negotiation for the ticket, baseline line equality, and no subsequent decision after reset.
- **Automation:** `e2e/system-integration/spn-line-full-process/test_spn_line_full_process.py::test_cross_layer_negotiation_converges_and_drives_decision` — planned after contract confirmation; must not be implemented or counted toward release exit while Draft.

**008 - One SPN agent unreachable (P1)**
- **Status:** Draft; blocked by §9 items 5 and 7.
- **Requirement:** https://github.com/project-openan/integration-test/issues/34
- **Preconditions:** Both SPN agents initially healthy and registered; diagnosis workflow and expected root-cause fixtures loaded. A test-controlled network fault can make only SPN agent 2 unreachable. The expected aggregation/failure result and repair-on-incomplete-diagnosis decision will come from the confirmed §9 item 5 contract.
- **Steps:**
  1. Inject the SPN agent 2 unreachable fault.
  2. Verify the fixture reports that fault.
  3. Publish a new ticket.
  4. Observe the two parallel diagnosis branches, including SPN agent 1's result and SPN agent 2's contracted failure/timeout result.
  5. Observe aggregation, diagnosis write-back, and any subsequent authorization or repair attempt.
  6. Remove the fault.
  7. Wait for registry and endpoint health.
  8. Publish a fresh recovery-probe ticket and observe both diagnosis branches and write-back.
- **Assertions:**
  - **A1 (Steps 1, 2, and 3):** The injected fault affects only SPN agent 2 and the first ticket starts two branches with distinct expected agent IDs.
  - **A2 (Step 4):** SPN agent 1 returns its fixture result; SPN agent 2 reaches the contracted bounded failure/timeout outcome; no result is fabricated for agent 2.
  - **A3 (Step 5):** Aggregation and EOMS write-back exactly match the confirmed partial-result or failure contract and explicitly identify the missing domain where required. Authorization and repair behavior exactly match the confirmed incomplete-diagnosis rule; no unconfirmed repair permission is assumed.
  - **A4 (Steps 6, 7, and 8):** After restoration, agent 2 is healthy and the fresh ticket receives genuine results from both SPN agents and one consolidated write-back correlated only to the recovery-probe ticket.
- **Finally / Cleanup:** Always remove the network fault and wait for agent/registry health; assert that agent 2 is reachable before teardown completes. Clear both tickets and captures, reset the barrier/fixtures if used, restore line baseline, and assert baseline equality and no residual fault injection.
- **Automation:** `e2e/system-integration/spn-line-full-process/test_spn_line_full_process.py::test_unreachable_spn_agent_returns_contracted_partial_result` — planned after contract confirmation; must not be implemented or counted toward release exit while Draft.

**009 - Repair execution failure (P1)**
- **Status:** Draft; blocked by §9 items 7 and 9.
- **Requirement:** https://github.com/project-openan/integration-test/issues/34
- **Preconditions:** Diagnosis succeeds, restoration is supported, policy = grant, and the OMC simulator is configured to fail the repair command. The failure response, bounded retry behavior, degraded terminal state, and expected post-failure line state are supplied by the confirmed §9 item 9 contract and a stateful simulator fixture; no atomicity or retry guarantee is presumed.
- **Steps:**
  1. Snapshot the baseline line state.
  2. Publish the ticket.
  3. Observe diagnosis write-back and authorization grant.
  4. Allow the repair command to reach the simulator.
  5. Capture the injected failure response and every command attempt.
  6. Observe the contracted bounded retry/degraded path through its terminal point.
  7. Inspect completion and recovery notifications, EOMS closure, actual line state, and the command-attempt log.
- **Assertions:**
  - **A1 (Steps 1, 2, and 3):** The diagnosis write-back is present and the grant precedes every repair attempt; the initial line state equals the baseline snapshot.
  - **A2 (Steps 4 and 5):** Each attempt is correlated to the ticket and authorization request, and the simulator returns the configured failure rather than a successful repair result.
  - **A3 (Step 6):** The retry count, event sequence, and degraded terminal state exactly match the confirmed contract and remain within its bound.
  - **A4 (Step 7):** No successful completion notification, successful recovery notification, or automatic closure is emitted. Actual line state equals the fixture-derived state for the attempts recorded in the command log, with no unrecorded mutation.
- **Finally / Cleanup:** Clear the injected repair failure and all ticket/command captures, issue only simulator-owned reset operations as needed, restore the line and metrics to the snapshot baseline, and assert exact baseline equality. Verify that no late retry, completion, recovery, or closure event occurs after reset.
- **Automation:** `e2e/system-integration/spn-line-full-process/test_spn_line_full_process.py::test_failed_repair_preserves_contracted_line_state` — planned after contract confirmation; must not be implemented or counted toward release exit while Draft.

**010 - Concurrent tickets and closure idempotency (P2)**
- **Status:** Draft; blocked by §9 items 1, 2, 3, and 7 for the full restoration path used by this case.
- **Requirement:** https://github.com/project-openan/integration-test/issues/34
- **Preconditions:** Two independent line/fault fixtures and tickets are available with separate expected conclusions and metric sets; restoration is supported and policy = grant; the EOMS stub records every write-back, recovery notification, and closure by ticket ID. Required full-loop contracts are the same confirmed contracts used by 001.
- **Steps:**
  1. Reset both line simulators.
  2. Publish both tickets concurrently through separate test-controlled requests.
  3. Capture both complete stage chains until each ticket reaches its terminal state.
  4. Replay each ticket's closure trigger once after its initial closure.
  5. Compare each ticket's stage graph and conclusion with its own isolated-run expected fixture.
  6. Inspect all post-replay records.
- **Assertions:**
  - **A1 (Steps 1 and 2):** Ticket IDs, line IDs, workflow IDs, and branch IDs are distinct between the two requests and both lines start at their own baseline.
  - **A2 (Step 3):** Every event and command resolves to exactly one ticket and its own line; each conclusion equals its own precomputed expectation; both chains satisfy the standing authorization, verification, and recovery ordering guards.
  - **A3 (Step 4):** Each ticket has exactly one closure. Replay creates no additional closure, diagnosis write-back, repair command, or recovery notification for either ticket.
  - **A4 (Steps 5 and 6):** Each concurrent-run stage graph and terminal result equals the corresponding isolated-run expected fixture, with no cross-ticket identifiers or metric values.
- **Finally / Cleanup:** Clear replay triggers and all ticket/event captures, restore both lines and metric sets independently, and assert each equals its own baseline. Verify both closure counts remain one and no late duplicate write-back, recovery notification, or closure occurs.
- **Automation:** `e2e/system-integration/spn-line-full-process/test_spn_line_full_process.py::test_concurrent_tickets_isolate_and_deduplicate_closure` — planned after contract confirmation; must not be implemented or counted toward release exit while Draft.

## 6. Assertion and Evidence Rules

- Deterministic assertions only: ticket/agent/workflow identifiers, stage event types and **ordering** (authorization -> repair; notification -> verification; verification -> recovery -> closure), root cause classification against precomputed fixtures, metric numeric consistency on fixture values, command-log presence/absence, terminal states, closure count. **Never assert on LLM-generated text**;
- Parallel diagnosis evidence must include two structurally distinct branches, both agent start events, both result events, and aggregation linkage. For 001 and 002, a test-controlled synchronous barrier must hold responses until both starts arrive, use a bounded wait, and be released in `finally`; natural execution-speed overlap alone is not evidence;
- **Standing ordering guards** (§4 red lines 2-3) apply to every case, including fault-injection cases: any repair without prior grant, or closure without passed verification, fails the case regardless of other assertions;
- Negotiation assertions are behavioral (occurrence, convergence, state alignment, outcome linkage); protocol schema conformance stays with `[SIT-a2at-protocol-*]`;
- No `sleep`; framework wait/retry on terminal events and metric convergence (Framework §6.3); no wall-clock dependence;
- No implicit case ordering; each case ID independently runnable (Framework §6.3);
- On failure preserve: full stage event trace with timestamps, negotiation trace, authorization decision record, OMC command log, line state snapshot (actual vs expected), metric sets, write-back payloads, relevant Pod logs from all layers, K8s events into `EVIDENCE_DIR`;
- Teardown: line baseline restoration **asserted**, stubs/policy/scenario reset, test-owned cards deregistered, injected faults cleared (Framework §6.5).

## 7. Tags, Naming, and Code Layout

- Test file: `e2e/system-integration/spn-line-full-process/test_spn_line_full_process.py`;
- Test functions: `test_<action>_<expected_result>` (e.g., `test_full_process_closes_after_verified_restoration`); optional class grouping `TestSpnLineFullProcess`;
- Tags - all five dimensions (Framework §6.4):

| Dimension | Values for S5 |
| --- | --- |
| feature | `system-integration` |
| environment | `online` / `offline` as supported by the lab; cross-city emulation mode noted in Notes |
| components | Copy each case's `Component Deps` cell verbatim from its CSV case row; do not apply a scenario-wide component set |
| priority | `P0` / `P1` / `P2` per §5 matrix |
| execution | Only Ready cases retain their matrix membership: `smoke` for Ready smoke cases and `full` for Ready full cases; every Draft case is excluded until ready |

- Case table rows follow the fixed 16-column template; Module = `system-integration`; per-case Component Deps are the sole source for the `components` tag; orchestration keys in Notes (`protocol_primitive` = Task-T + Negotiation-T + Authorization-T + Notification-T; write-operation safety rules noted). OMC simulator and EOMS stub remain test fixtures, not distribution components, unless a case's CSV Component Deps explicitly identifies another test dependency.
- Fixture reuse: S4 line-data scenarios and diagnosis fixtures are shared via the scenario package `utils/`; S5 adds OMC simulator, authorization policy, and metric-set fixtures on top.

## 8. Execution, CI Mapping, and Gates

| Trigger | S5 subset | Basis |
| --- | --- | --- |
| Daily build | `smoke`: Ready cases marked smoke only; currently none | Framework §7.2 |
| RC-0 / RC-1 | `full`: Ready cases marked full only; currently none | Framework §7.2, §4.3.2/§4.3.3 |
| Pre-release | Rerun all Ready S5 cases on RC; currently none | Framework §7.2 |

- Draft cases are excluded until ready: they must not be implemented, run as smoke/full release evidence, or included in either the numerator or denominator of the exit pass rate. Promotion to Ready requires resolution of every §9 dependency listed by the case and review of the updated matrix and definition;
- SIT exit gate: pass rate = 100% across the current Ready-case set, with no skips (Framework §8.3). An empty Ready set provides no release evidence and must not be reported as a pass;
- **Safety verification is part of the gate**: any standing-guard violation (unauthorized repair, unverified closure, unrestored line state) counts as failed even if functional assertions passed;
- Defects: evidence-attached issues, P0 24h response / current-release fix, regression case after fix (Framework §9);
- Archive: plan `docs/plans/<YY>-<season>/`, report `docs/reports/<YY>-<season>/`, JUnit XML per Framework §7.1/§11.3.

## 9. Open Items (must be resolved before case implementation)

| # | Item | Owner | Impact |
| --- | --- | --- | --- |
| 1 | Authorization-T business gate contract: grant/deny semantics at the workbench, decision record schema, denied terminal state and escalation path | a2a-t-sdk + workbench contributors | Blocks 001/003 ordering and denial assertions |
| 2 | Notification-T contracts: OMC -> workbench completion payload; workbench -> WAIMO recovery notification schema | workbench + SPN agent contributors | Blocks 001/004 assertions |
| 3 | Performance verification contract: metric set, recovery criteria, behavior when not recovered (retry bound / escalation) | workbench contributors | Blocks 001/004/005 assertions |
| 4 | OMC restoration-support flag semantics and the alternative path when unsupported | SPN agent contributors + Integration Testing WG | Blocks 006; OMC simulator design |
| 5 | Parallel-diagnosis aggregation contract: partial-result handling when one SPN agent fails; whether repair may proceed on incomplete diagnosis | orchestration-center WG | Blocks 002/008 assertions |
| 6 | Negotiation points and convergence bounds in the three-layer loop (which peers negotiate, round/timeout contract - shared with S2 §9 item 1) | a2a-t-sdk + orchestration-center WG | Blocks 007 |
| 7 | Cross-city / multi-vendor lab emulation: failure-domain separation for the two SPN agents, SDK language-variant assignment for vendor roles | Infra WG + Integration Testing WG | Blocks topology setup for all cases |
| 8 | Real-LLM variant inclusion in RC runs (deterministic assertions only) | Integration Testing WG | Optional variant; default CI stays `USE_MOCK_LLM=true` |
| 9 | Repair-execution failure contract: failure response, retry bound, degraded terminal state, and expected line-state semantics after failed attempts | SPN agent + workbench contributors | Blocks 009 failure-path and state assertions |
