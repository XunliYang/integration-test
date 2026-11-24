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

| Case ID | Name | Sub-flow / variant | Priority | Execution |
| --- | --- | --- | --- | --- |
| `[SIT-spn-line-full-process-001]` | Full E2E happy path: grab -> parallel diagnosis -> write-back -> authorization -> repair -> notification -> verification -> recovery -> closure | both sub-flows | P0 | smoke, full |
| `[SIT-spn-line-full-process-002]` | Parallel diagnosis with two SPN agents and correct summarization + write-back | diagnosis sub-flow | P0 | smoke, full |
| `[SIT-spn-line-full-process-003]` | Authorization gate: granted precedes repair; denied blocks repair | restoration, Authorization-T | P1 | full |
| `[SIT-spn-line-full-process-004]` | Completion notification triggers performance verification and recovery reporting | restoration, Notification-T | P1 | full |
| `[SIT-spn-line-full-process-005]` | Performance not recovered: no false recovery notification, defined retry/escalation | restoration, verification failure | P1 | full |
| `[SIT-spn-line-full-process-006]` | OMC restoration unsupported: defined alternative path, diagnosis still written back | restoration capability variant | P1 | full |
| `[SIT-spn-line-full-process-007]` | Cross-layer negotiation occurs and converges within bounds | Negotiation-T in the loop | P1 | full |
| `[SIT-spn-line-full-process-008]` | One SPN agent unreachable during parallel diagnosis: defined partial-result handling | diagnosis fault injection | P1 | full |
| `[SIT-spn-line-full-process-009]` | Repair execution failure: defined degraded state, consistent line state | restoration fault injection | P1 | full |
| `[SIT-spn-line-full-process-010]` | Concurrent tickets isolation and closure idempotency | concurrency | P2 | full |

P0/P1 cases must be `Automatable=Yes` with Requirement Link filled (scenario epic issue).

### 5.1 Case definitions (preconditions / steps / assertions / cleanup)

**001 - Full E2E happy path (P0)**
- Preconditions: RC centers deployed; all four agents registered; diagnosis workflow imported; S4 scenario (a) loaded (far-end optical module fault); OMC simulator: restoration supported, metrics baseline/degraded/recovered sets configured; authorization policy = grant; EOMS stub ready; `USE_MOCK_LLM=true`.
- Steps: (1) publish the complaint ticket at the EOMS stub; (2) observe the full loop via SDK/SSE events; (3) wait for terminal ticket state with framework wait/retry.
- Assertions (stage ordering is the backbone): ticket grabbed by WAIMO agent (grab event precedes dispatch); dispatch reaches workbench then both SPN agents; parallel diagnosis tasks overlap in time (both started before either finished) and summarize produces one consolidated conclusion matching the precomputed root cause; diagnosis write-back received at EOMS stub; **authorization grant event precedes the first repair command** (timestamp/order assertion); repair command logged at OMC simulator; completion notification received by workbench **before** verification starts; verification passes against the recovered metric set; recovery notification received at WAIMO **after** verification pass; ticket terminal state = closed at EOMS stub; closure happens exactly once.
- Cleanup: restore line baseline and assert restoration; reset stubs, policy, scenario state.

**002 - Parallel diagnosis and summarization (P0)**
- Steps: run the diagnosis sub-flow to write-back (restoration not required for this case; OMC flag may be unsupported).
- Assertions: both SPN agents participated (agent identifiers in task events); execution followed the published workflow composition (generate message -> parallel diagnose -> summarize; workflow identifier match); consolidated conclusion contains both agents' evidence contributions and the precomputed root cause classification; write-back payload at EOMS contains ticket ID, conclusion structure, contributing agents, timestamps; no repair action occurred (diagnosis-only run).

**003 - Authorization gate (P1)**
- Steps: run the loop twice with authorization policy = grant, then = deny (two independent executions).
- Assertions: grant run - repair executed only after the grant event (ordering); deny run - **zero repair commands** (command-log absence assertion), ticket reaches the defined denied terminal state (manual escalation per contract §9 item 1), diagnosis write-back still delivered, no automatic closure; denial recorded with reason field.

**004 - Notification and verification chain (P1)**
- Steps: run the restoration sub-flow with OMC completion notification enabled.
- Assertions: Notification-T completion event received by workbench (event type + source identity); verification starts only after the notification (ordering); verification compares post-repair metrics against the fixture baseline/recovered set (numeric consistency on fixture values); recovery notification to WAIMO contains ticket ID and verification result; WAIMO acknowledges and closure follows.

**005 - Performance not recovered (P1)**
- Preconditions: OMC simulator reports repair complete but metrics remain degraded (fixture-designed).
- Assertions: verification fails explicitly; **no recovery notification claiming success** (absence assertion); defined retry or escalation path per contract §9 item 3 (bounded, no infinite loop); ticket not auto-closed; line state and records consistent; eventual teardown restores baseline.

**006 - Restoration unsupported (P1)**
- Preconditions: OMC simulator restoration-support flag = unsupported for the located fault.
- Assertions: no repair command issued; defined alternative path taken (manual/escalation per contract §9 item 4); diagnosis conclusion still written back to EOMS; ticket terminal state reflects the alternative path, not false closure.

**007 - Cross-layer negotiation (P1)**
- Steps: run a scenario requiring negotiation between layers (e.g., restoration strategy between workbench and SPN agents, per contract §9 item 6).
- Assertions: Negotiation-T exchanges occur between the expected peer identities; client/server negotiation states aligned at termination; convergence within the bounded round/timeout contract (shared with S2 §9 item 1; until confirmed, SDK default bound recorded in Notes); negotiation outcome drives the subsequent dispatch/repair decision (outcome-to-action linkage via identifiers).

**008 - One SPN agent unreachable (P1)**
- Preconditions: SPN agent 2 endpoint unreachable (test-controlled fault injection).
- Steps: submit ticket; observe parallel diagnosis.
- Assertions: partial-result handling follows contract §9 item 5 (degraded conclusion explicitly marking the missing domain, or defined failure - never a fabricated full conclusion); write-back reflects the degraded state; no repair authorized on an incomplete diagnosis unless the contract explicitly allows it (assert per contract); after restoring the agent, a fresh ticket completes normally (recovery probe).
- Cleanup: restore agent; verify registry health recovers.

**009 - Repair execution failure (P1)**
- Preconditions: OMC simulator configured to fail the repair command.
- Assertions: defined degraded terminal state identifying the failed repair; line state consistent with the commands actually executed (no partial/inconsistent state); completion notification not falsely emitted; no recovery notification; no auto-closure; retry bounded per contract; teardown restores baseline and asserts restoration.

**010 - Concurrent tickets and closure idempotency (P2)**
- Steps: submit two tickets (different lines/scenarios) concurrently; after closure, replay the closure trigger once.
- Assertions: per-ticket stage chains do not cross-contaminate (identifiers throughout); each ticket's conclusion matches its own precomputed expectation; closure exactly once per ticket - replay produces no duplicate closure, write-back, or recovery notification (idempotency); results identical to sequential runs.

## 6. Assertion and Evidence Rules

- Deterministic assertions only: ticket/agent/workflow identifiers, stage event types and **ordering** (authorization -> repair; notification -> verification; verification -> recovery -> closure), root cause classification against precomputed fixtures, metric numeric consistency on fixture values, command-log presence/absence, terminal states, closure count. **Never assert on LLM-generated text**;
- **Standing ordering guards** (§4 red lines 2-3) apply to every case, including fault-injection cases: any repair without prior grant, or closure without passed verification, fails the case regardless of other assertions;
- Negotiation assertions are behavioral (occurrence, convergence, state alignment, outcome linkage); protocol schema conformance stays with `[SIT-a2at-protocol-*]`;
- No `sleep`; framework wait/retry on terminal events and metric convergence (Framework §6.3); no wall-clock dependence;
- No implicit case ordering; each case ID independently runnable (Framework §6.3);
- On failure preserve: full stage event trace with timestamps, negotiation trace, authorization decision record, OMC command log, line state snapshot (actual vs expected), metric sets, write-back payloads, relevant Pod logs from all layers, K8s events into `EVIDENCE_DIR`;
- Teardown: line baseline restoration **asserted**, stubs/policy/scenario reset, test-owned cards deregistered, injected faults cleared (Framework §6.5).

## 7. Tags, Naming, and Code Layout

- Test file: `e2e/system-integration/spn-line-full-process/test_spn_line_full_process.py`;
- Test functions: `test_<action>_<expected_result>` (e.g., `test_submit_ticket_closes_only_after_verified_restoration`); optional class grouping `TestSpnLineFullProcess`;
- Tags - all five dimensions (Framework §6.4):

| Dimension | Values for S5 |
| --- | --- |
| feature | `system-integration` |
| environment | `online` / `offline` as supported by the lab; cross-city emulation mode noted in Notes |
| components | `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent` (OMC simulator and EOMS stub are test fixtures, not distribution components) |
| priority | `P0` / `P1` / `P2` per §5 matrix |
| execution | `smoke` (001, 002), `full` (all) |

- Case table rows follow the fixed 16-column template; Module = `system-integration`; Component Deps as above; orchestration keys in Notes (`protocol_primitive` = Task-T + Negotiation-T + Authorization-T + Notification-T; write-operation safety rules noted).
- Fixture reuse: S4 line-data scenarios and diagnosis fixtures are shared via the scenario package `utils/`; S5 adds OMC simulator, authorization policy, and metric-set fixtures on top.

## 8. Execution, CI Mapping, and Gates

| Trigger | S5 subset | Basis |
| --- | --- | --- |
| Daily build | smoke: 001, 002 | Framework §7.2 |
| RC-0 / RC-1 | full: 001-010 | Framework §7.2, §4.3.2/§4.3.3 |
| Pre-release | all S5 cases rerun on RC | Framework §7.2 |

- SIT exit gate: S5 pass rate = 100%, no skips (Framework §8.3);
- **Safety verification is part of the gate**: any standing-guard violation (unauthorized repair, unverified closure, unrestored line state) counts as failed even if functional assertions passed;
- Defects: evidence-attached issues, P0 24h response / current-release fix, regression case after fix (Framework §9);
- Archive: plan `docs/plans/<YY>-<season>/`, report `docs/reports/<YY>-<season>/`, JUnit XML per Framework §7.1/§11.3.

## 9. Open Items (must be resolved before case implementation)

| # | Item | Owner | Impact |
| --- | --- | --- | --- |
| 1 | Authorization-T business gate contract: grant/deny semantics at the workbench, decision record schema, denied terminal state and escalation path | a2a-t-sdk + workbench contributors | Blocks 001/003 ordering and denial assertions |
| 2 | Notification-T contracts: OMC -> workbench completion payload; workbench -> WAIMO recovery notification schema | workbench + SPN agent contributors | Blocks 001/004 assertions |
| 3 | Performance verification contract: metric set, recovery criteria, behavior when not recovered (retry bound / escalation) | workbench contributors | Blocks 004/005 assertions |
| 4 | OMC restoration-support flag semantics and the alternative path when unsupported | SPN agent contributors + Integration Testing WG | Blocks 006; OMC simulator design |
| 5 | Parallel-diagnosis aggregation contract: partial-result handling when one SPN agent fails; whether repair may proceed on incomplete diagnosis | orchestration-center WG | Blocks 002/008 assertions |
| 6 | Negotiation points and convergence bounds in the three-layer loop (which peers negotiate, round/timeout contract - shared with S2 §9 item 1) | a2a-t-sdk + orchestration-center WG | Blocks 007 |
| 7 | Cross-city / multi-vendor lab emulation: failure-domain separation for the two SPN agents, SDK language-variant assignment for vendor roles | Infra WG + Integration Testing WG | Blocks topology setup for all cases |
| 8 | Real-LLM variant inclusion in RC runs (deterministic assertions only) | Integration Testing WG | Optional variant; default CI stays `USE_MOCK_LLM=true` |