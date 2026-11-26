# SIT Specification S2: Mobile Cross-Domain Collaborative Complaint Handling

> *Version: v0.1 (Draft)*
> *Milestone: `26-winter` | Archive path: `docs/plans/26-winter/sit-specs/` (version-specific SIT design artifact)*
> *Maintained by: OpenAN Integration Testing Working Group*
> *Language: English*
> *Scenario slug: `cross-domain-complaint` - Case IDs: `[SIT-cross-domain-complaint-<number>]`*
> *Scenario baseline: [sit-scenarios.md](../sit-scenarios.md) S2*
> *Governance baseline: [OpenAN Integration Testing Process and Framework](../../../OpenAN%20Integration%20Testing%20Process%20and%20Framework.md) (cited as "Framework" below)*

---

## 1. Scope

This specification defines the SIT requirements for scenario S2 (Mobile Cross-Domain Collaborative Complaint Handling), derived from China Mobile Henan Practice 1 (https://openan.dev/best-practices/henan-mobile-openan-usecase.html).

**In scope** - the distribution-level closed loop:

1. Complaint intake: a complaint ticket enters the provincial complaint platform from the call center / process center (10086 / EOMS, simulated by test stubs);
2. Smart recognition: the provincial recognition agent identifies the complaint and drives cross-domain handling;
3. Cross-domain discovery: required domain agents are discovered via the group-tier Registry Center;
4. Autonomous negotiation and joint fault location: the recognition agent and domain agents negotiate over A2A-T (Negotiation-T) and collaboratively locate the fault - including problems without a pre-coded workflow;
5. Closure and write-back: the diagnosis conclusion is written back to the process center and the ticket closes end-to-end.

Domain agents cover four professional domains: **wireless optimization, wireless fault, core network fault, SPN fault**.

**What distinguishes S2 from neighboring scenarios** (and therefore what its cases must actually exercise):

| Difference | S1 (`complaint-handling`) | S2 (this spec) |
| --- | --- | --- |
| Collaboration mode | Fixed workflow recall by complaint category | Dynamic autonomous negotiation; generalization to unknown issues |
| Domain span | Broadband: billing / CDN / FAN | Mobile: wireless optimization / wireless fault / core network fault / SPN fault |
| Deployment | Single tier | Group-province two tiers |
| Closed-loop scope | Diagnosis + closure / NOC handoff | Diagnosis + write-back to process center + closure (no network repair) |

**Out of scope** (do not duplicate here):

- Negotiation-T protocol state-machine conformance, dual-transport equivalence, cross-language SDK interop as protocol properties -> `[SIT-a2at-protocol-*]` and specialized A2A-T protocol testing (Framework §10). S2 asserts negotiation **behavior in the business loop** (it happens, converges, and its outcome drives the ticket), not protocol schema conformance;
- SPN dedicated-line diagnosis / restoration flows -> S4 / S5; S2 touches the SPN fault domain only as one participating domain in mobile complaint handling;
- Fixed-workflow broadband complaint branches -> S1;
- Single-API / single-module contract checks -> FIT;
- Performance / negotiation throughput thresholds, 7x24h stability -> specialized testing (Framework §10).

## 2. System Under Test

### 2.1 Topology (group-province two tiers)

```
GROUP TIER (simulated group platform)
  Registry Center  <---- registration / discovery ----+
  Orchestration Center (workflow composition/retrieval) |
        ^                                             |
        | cross-tier A2A-T                            |
--------|---------------------------------------------|------
PROVINCE TIER                                         |
  10086 / EOMS process center (test stubs)            |
        | ticket intake / result write-back           |
        v                                             |
  provincial recognition agent (host_agent +          |
  workflow-exec-engine, embeds a2a-t-sdk) ------------+
        |
        | Negotiation-T / Task-T, autonomous negotiation
        v
  wireless optimization agent | wireless fault agent
  core network fault agent    | SPN fault agent
  (sample mock agents, registered into group-tier Registry Center)
```

- The two tiers are deployed as separate failure domains in the lab (separate namespaces or clusters; concrete lab mode is an open decision, §9). Cross-tier calls must traverse the real network path between tiers, not in-process shortcuts;
- The recognition agent and domain agents embed the workflow execution engine SDK with the A2A-T SDK, matching the production architecture;
- Cross-vendor heterogeneity is emulated by running participating agents on different SDK language variants (Python / Java) where sample agents are available; this is a variant, not a separate scenario.

### 2.2 Components and dependency constraints

| Component | Role in S2 | Constraint |
| --- | --- | --- |
| `registry-center` (group tier, HTTPS :5000) | Registration / discovery of provincial and domain agents across tiers | mTLS client identity (`REGISTRY_CLIENT_CERT/KEY/CA_CERT`); owner isolation applies to provincial vs group orgs |
| `orchestration-center` (group tier, :5001) | Workflow composition / retrieval where a known flow exists; negotiation-driven handling must not require a pre-coded workflow | `workflow-exec-engine>=0.1.1,<0.2`, `a2a-t-sdk>=1.2.0,<2`; runtime dependency on registry-center |
| Provincial recognition agent (`host_agent` + `workflow-exec-engine`) | Intelligent recognition engine of the complaint platform | Embeds `a2a-t-sdk` per constraint above |
| Domain agents: wireless optimization, wireless fault, core network fault, SPN fault | Sample mock agents shipped with the distribution (orchestration-center `samples/`, `openan-demo` mockagent), carrying S2 domain scenario payloads (§4) | Registered into group-tier Registry Center; endpoints via `MOCK_AGENTS_HOST` / `SAMPLE_AGENTS_HOST` |
| 10086 / EOMS process center stubs | Ticket intake source and write-back receiver | Test-side stubs; write-back schema to be confirmed (§9) |
| LLM dependency | Recognition / negotiation reasoning where used | `USE_MOCK_LLM=true` for deterministic CI runs; real-LLM runs are an optional variant with deterministic assertions only |

All centers and agents under test deploy from the RC image package (`IMAGE_REGISTRY` / `IMAGE_TAG`), `DEPLOY_MODE=online-helm` or `offline-compose`, real environment per Framework §5.1.

## 3. Environment and Configuration Contract

Reuse `e2e/.env.template` (Framework §6.6):

| Variable | Usage in S2 |
| --- | --- |
| `KUBECONFIG`, `OPENAN_NAMESPACE`, `DEPLOY_MODE` | Cluster access; two-tier separation via namespaces or second cluster context |
| `REGISTRY_CENTER_URL`, `REGISTRY_CLIENT_CERT`, `REGISTRY_CLIENT_KEY`, `REGISTRY_CA_CERT` | Group-tier registry access with mTLS identity |
| `ORCHESTRATION_CENTER_URL`, `ORCH_ACCESS_PASSWORD` | Group-tier orchestration access |
| `LLM_CHAT_*`, `A2AT_LLM_*`, `USE_MOCK_LLM` | LLM dependency; mock toggle for determinism |
| `MOCK_AGENTS_HOST`, `SAMPLE_AGENTS_HOST` | Provincial recognition agent and domain agent endpoints |
| `IMAGE_REGISTRY`, `IMAGE_TAG` | RC build under test |
| `EVIDENCE_DIR` | Failure scene preservation |

Rules:

- If the two-tier lab mode requires a second cluster context or a province-tier URL, introduce the variables (e.g., `PROVINCE_KUBECONFIG`, `PROVINCE_AGENT_URL`) in the same PR that updates `e2e/.env.template` and README;
- EOMS write-back stub endpoint, if configurable, follows the same rule (e.g., `EOMS_STUB_URL`);
- No hardcoded IPs, credentials, or tokens.

## 4. Test Data and Fixtures

| Fixture | Scope | Content | Cleanup |
| --- | --- | --- | --- |
| Domain agent cards | module | Cards for the four domain agents plus the provincial recognition agent, registered into the group-tier registry with valid JWS signatures under the correct org (province vs group owner isolation) | Deregister test-owned cards; restore registry baseline |
| Domain scenario payloads | module | Fault scenario data per domain: wireless fault (e.g., cell outage signature), core network fault, SPN fault, wireless optimization degradation; each payload defines the observable evidence the domain agent returns | Stateless data; reset agent stub state per case |
| Complaint tickets | function | Fixed ticket payloads: single-domain ticket, cross-domain joint ticket (wireless + core), novel-problem ticket with no pre-coded workflow, per-domain combination tickets | Stateless |
| EOMS process center stub | function | Receives write-back; captures payload and ticket state transitions | Reset captured state per case |
| Known-flow workflow (optional) | module | One pre-coded workflow for the known-issue variant, imported into group-tier Orchestration Center | Delete in teardown |
| Login session | session (read-only) | Orchestration Center session | Not shared mutable state (Framework §6.5) |

- Domain scenario payloads are test data authored on top of the shipped sample agents; they are not new agent implementations;
- Every case independently repeatable; full suite runs twice with identical results, no manual reset.

## 5. Case Matrix

| Case ID | Name | Variant coverage | Priority | Status | Execution |
| --- | --- | --- | --- | --- | --- |
| `[SIT-cross-domain-complaint-001]` | Single-domain complaint E2E automated closure (wireless fault) | known issue, one domain, two tiers | P0 | Draft | excluded until ready |
| `[SIT-cross-domain-complaint-002]` | Cross-domain joint fault location E2E closure (wireless + core network) | known issue, multi-domain negotiation | P0 | Draft | excluded until ready |
| `[SIT-cross-domain-complaint-003]` | Novel problem handled by dynamic negotiation (no pre-coded workflow) | generalization variant | P1 | Draft | excluded until ready |
| `[SIT-cross-domain-complaint-004]` | Group-province tiering: cross-tier registration, discovery and invocation | two-tier topology | P1 | Draft | excluded until ready |
| `[SIT-cross-domain-complaint-005]` | Diagnosis write-back to process center with full context | closure / write-back | P1 | Draft | excluded until ready |
| `[SIT-cross-domain-complaint-006]` | Domain agent unreachable or negotiation rejected: defined degraded terminal state | two independent parameterized fault-injection runs | P1 | Draft | excluded until ready |
| `[SIT-cross-domain-complaint-007]` | Remaining domain combinations (SPN fault; wireless optimization) | domain coverage | P2 | Draft | excluded until ready |
| `[SIT-cross-domain-complaint-008]` | Concurrent cross-domain complaints isolation | concurrency | P2 | Draft | excluded until ready |

P0/P1 rows use Requirement Link https://github.com/project-openan/integration-test/issues/34 and `Automatable=Yes` as the final automation requirement; a Draft row remains excluded from current execution even though it is required to be automated after promotion.

### 5.1 Case definitions (preconditions / steps / assertions / cleanup)

All S2 cases are currently Draft. The definitions below preserve the expected design, but the referenced contracts are not confirmed; none may be implemented, executed, or counted in release-exit denominators until its blocking open items are resolved and its matrix status changes to Ready.

**001 - Single-domain E2E closure (P0)**
- Status: Draft — blocked by Open Items 1, 2, 3, and 4 (negotiation convergence contract, write-back/ticket-state contract, two-tier lab contract, and wireless scenario fixture).
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions (planned): the contracted two-tier topology is deployed and healthy; the recognition agent and four domain agents are registered in their contracted orgs; the confirmed wireless-fault payload is loaded; the EOMS stub implements the confirmed ticket state machine and write-back schema and starts empty; `USE_MOCK_LLM=true`.
- Steps (planned): (1) submit one fixed wireless-fault ticket through the intake stub and record its ticket ID; (2) collect recognition, registry-discovery, Negotiation-T, Task-T, and ticket events associated with that ID; (3) query the terminal ticket, the write-back captured by EOMS, and all agent invocations for the ticket.
- Assertions (planned, after contract confirmation): for step 1, exactly one ticket with the submitted ID enters the contracted intake state; for step 2, discovery returns the wireless-fault agent ID from the group-tier registry, negotiation events occur and terminate in the contracted converged state, and no other domain agent ID is invoked; for step 3, the ticket reaches the contracted closed state, exactly one schema-valid write-back contains the required conclusion fields, and all recorded states and agent IDs belong to the submitted ticket.
- finally/Cleanup (planned): in a `finally` block, delete the test ticket, clear EOMS captures, reset domain scenario state, and remove test-owned registrations and event subscriptions. Recovery assertion: the ticket ID is absent, the stub is empty, no test-owned negotiation or task remains active, and both tiers return to their pre-case registration and health snapshots.
- Automation: planned after contract confirmation — `e2e/system-integration/cross-domain-complaint/test_cross_domain_complaint.py::test_submit_wireless_fault_ticket_closes_with_single_domain_diagnosis`

**002 - Cross-domain joint fault location (P0)**
- Status: Draft — blocked by Open Items 1, 2, 3, and 4 (negotiation bounds/state names, write-back/ticket states, two-tier lab, and wireless/core fixtures).
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions (planned): the contracted two-tier topology is healthy; recognition, wireless-fault, and core-network-fault agents are registered and reachable with confirmed scenario payloads; the other domain agents are registered; negotiation round/timeout and terminal-state contracts are available; the EOMS stub starts empty; `USE_MOCK_LLM=true`.
- Steps (planned): (1) submit one fixed joint wireless-plus-core ticket and record its ticket ID; (2) collect all negotiation rounds, task events, and participating agent IDs until negotiation reaches a terminal state or the confirmed bound is exceeded; (3) query the consolidated conclusion, EOMS write-back, and terminal ticket state for that ticket.
- Assertions (planned, after contract confirmation): for step 1, one ticket enters the contracted intake state; for step 2, both the wireless-fault and core-network-fault agent IDs participate, negotiation converges within the confirmed maximum rounds and timeout, client/server terminal states match the contracted converged state, and neither SPN nor optimization is invoked; for step 3, one consolidated conclusion identifies exactly both contributing domains and retains each domain's evidence, one schema-valid write-back is received, and the ticket reaches the contracted closed state.
- finally/Cleanup (planned): in a `finally` block, delete the ticket, clear EOMS and agent captures, and remove test-owned registrations and subscriptions. Recovery assertion: no ticket, write-back, active negotiation, or active task owned by the case remains, and both tiers match their pre-case health and registration snapshots.
- Automation: planned after contract confirmation — `e2e/system-integration/cross-domain-complaint/test_cross_domain_complaint.py::test_submit_joint_ticket_closes_with_consolidated_conclusion`

**003 - Novel problem, dynamic negotiation (P1)**
- Status: Draft — blocked by Open Items 1, 2, 3, and 4 (negotiation terminal/bound contract, ticket outcome/write-back contract, two-tier lab, and novel-problem domain fixtures).
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions (planned): the contracted two-tier topology is healthy; recognition and required domain agents are registered; a fixed novel-problem ticket and its required domain fixtures are confirmed; workflow retrieval is observable; no pre-coded workflow matches the novel category; EOMS starts empty; `USE_MOCK_LLM=true`.
- Steps (planned): (1) query workflow retrieval for the novel category and record the no-match evidence; (2) submit the novel-problem ticket; (3) collect its execution context, negotiation events, and task events through terminal handling; (4) query the terminal ticket; (5) query the captured write-back.
- Assertions (planned, after contract confirmation): for step 1, retrieval returns the contracted no-match result and no fixed workflow ID; for steps 2 and 3, the execution context carries the contracted dynamic-composition marker, Negotiation-T events occur and terminate within the confirmed bound, and client/server terminal states align; for steps 4 and 5, the ticket reaches exactly one contracted terminal outcome (closed with a schema-valid conclusion or explicit cannot-locate), with no silent hang and no closed outcome lacking the required conclusion. Assertions use identifiers, event types, and states, not generated wording.
- finally/Cleanup (planned): in a `finally` block, delete the ticket and any dynamically created test-owned execution resources, clear EOMS and event captures, and restore agent fixtures. Recovery assertion: no case-owned ticket, workflow, negotiation, task, or write-back remains and both tiers match their pre-case health snapshots.
- Automation: planned after contract confirmation — `e2e/system-integration/cross-domain-complaint/test_cross_domain_complaint.py::test_submit_novel_ticket_uses_dynamic_negotiation_without_fixed_workflow`

**004 - Group-province tiering (P1)**
- Status: Draft — blocked by Open Item 3 (two-tier topology, real network path, and cross-tier mTLS trust).
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions (planned): separate group and province failure domains are deployed using the confirmed lab mode; cross-tier mTLS trust and network observability are configured; group-owned and province-owned card baselines and permissions are known; one province complaint fixture and its required agents are available; the group tier is initially reachable.
- Steps (planned): (1) register a test-owned province agent into the group-tier registry; (2) query it using authorized province credentials; (3) attempt to read a group-owned card outside the province org's permissions; (4) attempt to modify the same group-owned card outside the province org's permissions; (5) submit the province complaint and capture registry and invocation network paths and task identities; (6) make the group tier unreachable; (7) submit a fresh province complaint and observe its terminal response; (8) restore group-tier connectivity; (9) repeat health and discovery probes.
- Assertions (planned, after contract confirmation): for steps 1 and 2, the registered card carries the province org ID and authorized discovery traverses the contracted real cross-tier network path; for steps 3 and 4, both unauthorized operations return the contracted authorization failure and the group-owned card remains byte-for-byte unchanged; for step 5, invocation succeeds over the cross-tier path and task events carry the expected province and group agent IDs; for steps 6 and 7, the fresh complaint returns the contracted group-unreachable error within the confirmed timeout and does not use stale local discovery state; for steps 8 and 9, health and authorized discovery succeed again.
- finally/Cleanup (planned): in a `finally` block, restore group-tier connectivity, delete both tickets and the test-owned province card, and stop network/audit capture. Recovery assertion: no injected network fault remains, the group-owned card is unchanged, test-owned tickets and card IDs are absent, and registry discovery and both-tier health match their baselines.
- Automation: planned after contract confirmation — `e2e/system-integration/cross-domain-complaint/test_cross_domain_complaint.py::test_submit_province_complaint_uses_secure_cross_tier_discovery_and_invocation`

**005 - Write-back with full context (P1)**
- Status: Draft — blocked by Open Items 1, 2, 3, and 4 (successful joint handling prerequisites and the EOMS schema/state machine).
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions (planned): the contracted two-tier joint-complaint path is operational with confirmed wireless/core fixtures and negotiation bounds; the EOMS stub implements the confirmed write-back schema and ticket transition contract; its capture store is empty; a fixed joint ticket has a unique ticket ID; `USE_MOCK_LLM=true`.
- Steps (planned): (1) submit the fixed joint ticket and record the EOMS intake transition; (2) collect processing events; (3) wait for the contracted terminal ticket state; (4) retrieve every EOMS request and state transition for the ticket; (5) compare them with per-agent execution history.
- Assertions (planned, after contract confirmation): for step 1, one intake transition records the exact ticket ID; for steps 2 and 3, the processing-to-terminal sequence follows the confirmed state machine and contains no duplicate or out-of-order transition; for steps 4 and 5, exactly one terminal write-back validates against the confirmed schema and contains the ticket ID, conclusion, exactly the contributing domain IDs, and every per-agent diagnostic result and timestamp in the contracted order, with no missing or extra history entry.
- finally/Cleanup (planned): in a `finally` block, delete the test ticket, clear EOMS requests/transitions, stop execution capture, and reset agent fixtures. Recovery assertion: the EOMS store contains no case ticket or write-back, no test-owned task or negotiation remains active, and the intake stub is ready to accept a fresh ticket.
- Automation: planned after contract confirmation — `e2e/system-integration/cross-domain-complaint/test_cross_domain_complaint.py::test_close_joint_ticket_writes_back_full_diagnostic_context_once`

**006 - Unreachable / rejecting domain agent (P1)**
- Status: Draft — blocked by Open Items 1, 2, 3, and 4. Case ID 006 has two independent parameterized runs; neither variant may be hidden behind or inferred from the other.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Automation: planned after contract confirmation — parameterized node `e2e/system-integration/cross-domain-complaint/test_cross_domain_complaint.py::test_joint_ticket_domain_fault_returns_defined_terminal_state` with independent `unreachable` and `negotiation_rejected` parameter sets.

***006 parameter `unreachable` — independent setup, run, and recovery***
- Preconditions / setup (planned): deploy the confirmed two-tier topology; load confirmed wireless/core fixtures; register healthy recognition, wireless-fault, and core-network-fault agents; start an empty EOMS stub; record the core agent's healthy registry snapshot; inject a network/endpoint fault that makes only the core-network agent unreachable; verify wireless remains reachable.
- Steps (planned): (1) verify the core-agent health/route probe fails and the wireless-agent probe succeeds; (2) submit the fixed joint ticket; (3) collect its negotiation/task events; (4) wait until the contracted degraded/failed terminal outcome or confirmed timeout; (5) query the ticket, write-back/error result, remaining-domain result, and all task states; (6) remove only the endpoint fault; (7) probe core-agent health/discovery; (8) submit a fresh joint ticket with no fault; (9) observe it through terminal handling.
- Assertions (planned, after contract confirmation): for step 1, only core is unreachable; for steps 2, 3, and 4, handling terminates within the confirmed negotiation bound in the contracted unreachable/degraded outcome, never false closure, and the structured error identifies the core agent ID; for step 5, the wireless result is retained in context and no negotiation or task remains active beyond the bound; for steps 6 and 7, core health and discovery match the pre-fault snapshot; for steps 8 and 9, the fresh ticket reaches the contracted closed outcome with both domain contributions.
- finally/Cleanup / recovery assertions (planned): in a `finally` block, remove the endpoint fault, delete both tickets, clear stubs, and stop captures. Assert the fault is absent, core is reachable and registered as before, both ticket IDs are absent, no case-owned negotiation/task remains active, and EOMS is empty.

***006 parameter `negotiation_rejected` — independent setup, run, and recovery***
- Preconditions / setup (planned): deploy the confirmed two-tier topology; load confirmed wireless/core fixtures; register recognition, wireless-fault, and core-network-fault agents with reachable endpoints; start an empty EOMS stub; record the core agent's healthy registry snapshot; configure only the core mock agent to return the contracted negotiation rejection while preserving endpoint reachability; verify wireless negotiation remains available.
- Steps (planned): (1) verify core endpoint health succeeds and its negotiation probe returns the configured rejection; (2) submit the fixed joint ticket; (3) collect negotiation/task events; (4) wait for the contracted rejected/degraded terminal outcome or confirmed timeout; (5) query the ticket, structured rejection, remaining-domain result, and all negotiation/task states; (6) remove only the rejection configuration; (7) verify a core negotiation probe can converge; (8) submit a fresh joint ticket with rejection disabled; (9) observe it through terminal handling.
- Assertions (planned, after contract confirmation): for step 1, core remains reachable and returns the contracted rejection; for steps 2, 3, and 4, handling terminates within the confirmed negotiation bound in the contracted rejected/degraded outcome, never false closure, and identifies the core agent ID and rejection reason code; for step 5, the wireless result is retained, no retry exceeds the confirmed bound, and no negotiation/task remains active; for steps 6 and 7, a fresh core negotiation converges and registry health remains unchanged; for steps 8 and 9, the fresh ticket reaches the contracted closed outcome with both domain contributions.
- finally/Cleanup / recovery assertions (planned): in a `finally` block, remove the rejection configuration, delete both tickets, clear stubs, and stop captures. Assert rejection is disabled, core remains reachable and registered as before, both ticket IDs are absent, no case-owned negotiation/task remains active, and EOMS is empty.

**007 - Remaining domain combinations (P2)**
- Status: Draft — blocked by Open Items 2, 3, and 4; execution is excluded until ready.
- Expected design: run SPN-fault and wireless-optimization tickets separately after their payload, topology, and write-back contracts are confirmed. For each ticket, assert discovery and participation of exactly its required domain, a schema-valid diagnosis and contracted closure, and no other domain invocation. For SPN, additionally assert that only complaint diagnosis occurs and no restoration or authorization action is emitted.

**008 - Concurrent complaints isolation (P2)**
- Status: Draft — blocked by Open Items 1, 2, 3, and 4; execution is excluded until ready.
- Expected design: after the relevant contracts are confirmed, submit one single-domain and one cross-domain ticket concurrently. Assert independent contracted terminal states; per-ticket negotiation session IDs, task IDs, event streams, and write-back payloads contain no identifiers or diagnostic evidence from the other ticket; cleanup restores empty stubs and the pre-case health baseline.

## 6. Assertion and Evidence Rules

- Deterministic assertions only: ticket/ticket-state identifiers, agent/org identifiers, Negotiation-T and Task-T event types and state alignment, terminal states, required-field presence, write-back transition ordering. **Never assert on LLM-generated text**;
- Negotiation-specific: assert that negotiation **occurred and converged** (event presence + aligned terminal states + bounded rounds). Round limits, timeout values, and terminal state names must come from the contract in §9 item 1. Until confirmed, all affected cases remain Draft and excluded; do not substitute SDK defaults as an executable release-gate contract;
- No `sleep`; framework wait/retry on terminal events (Framework §6.3);
- No implicit case ordering; closely related checks may share one test function per Framework §6.3 with each case ID independently runnable;
- On failure preserve: negotiation trace (message sequence and states), ticket lifecycle record, SDK/SSE events, relevant Pod logs from both tiers, K8s events into `EVIDENCE_DIR`;
- Teardown cleans: tickets, stub state, test-owned cards, imported workflows, injected faults (Framework §6.5).

## 7. Tags, Naming, and Code Layout

- Test file: `e2e/system-integration/cross-domain-complaint/test_cross_domain_complaint.py`;
- Test functions: `test_<action>_<expected_result>` (e.g., `test_submit_joint_ticket_closes_with_consolidated_conclusion`); optional class grouping `TestCrossDomainComplaint`;
- Tags - all five dimensions (Framework §6.4):

| Dimension | Values for S2 |
| --- | --- |
| feature | `system-integration` |
| environment | `online` / `offline` as supported by the lab; two-tier mode noted in Notes |
| components | `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent` |
| priority | `P0` / `P1` / `P2` per §5 matrix |
| execution | No current smoke/full cases; all Draft cases are `excluded until ready` |

- Case table rows follow the fixed 16-column template; Module = `system-integration`. Actual code component labels must come from each case row's CSV Component Deps rather than copying the scenario-level list wholesale; orchestration keys (`language_profile`, `protocol_primitive`, `execution_strategy`, `environment`) go in Notes. `protocol_primitive` includes Negotiation-T for cases that exercise negotiation.

## 8. Execution, CI Mapping, and Gates

| Trigger | S2 Ready subset | Basis |
| --- | --- | --- |
| Daily build | smoke: none currently; all cases are Draft and `excluded until ready` | Framework §7.2 |
| RC-0 / RC-1 | full: none currently; all cases are Draft and `excluded until ready` | Framework §7.2, §4.3.2/§4.3.3 |
| Pre-release | rerun every case that has become Ready on RC; currently none | Framework §7.2 |

- The current S2 smoke and full execution sets are empty because all eight cases have unresolved blockers. When a case's blockers are resolved and its matrix status changes to Ready, only that case becomes eligible for its designated smoke/full set and the release-exit denominator.
- SIT exit gate: the pass rate over currently Ready S2 cases only must be 100%, with no skips among those cases (Framework §8.3). Draft cases are not executable tests, skips, passes, failures, or denominator entries. With zero Ready cases, no S2 pass-rate result or release readiness credit may be claimed;
- Defects: evidence-attached issues, P0 24h response / current-release fix, regression case after fix (Framework §9);
- Archive: plan `docs/plans/<YY>-<season>/`, report `docs/reports/<YY>-<season>/`, JUnit XML per Framework §7.1/§11.3.

## 9. Open Items (case-specific blockers)

| # | Item | Owner | Impact |
| --- | --- | --- | --- |
| 1 | Negotiation convergence contract: max rounds / timeout, terminal state naming for converged / failed / rejected negotiation | a2a-t-sdk + orchestration-center WG | Blocks bounded-convergence assertions in 001/002/003/005/006/008 |
| 2 | EOMS process center write-back schema and ticket state machine (operator-specific in production; community stub contract) | Integration Testing WG + case contributor | Blocks ticket-outcome and payload assertions in 001/002/003/005/006/007/008 |
| 3 | Two-tier lab mode: separate namespaces vs separate clusters; cross-tier network path and mTLS trust setup between tiers | Infra WG + Integration Testing WG | Blocks 004 and the environment section of all cases |
| 4 | Domain scenario payloads for wireless / core / SPN / optimization on the shipped sample agents (test data authoring, not new agents) | Integration Testing WG | Blocks fixture content in 001/002/003/005/006/007/008 |
| 5 | Real-LLM variant inclusion in RC runs (deterministic assertions only) | Integration Testing WG | Optional variant; default CI stays `USE_MOCK_LLM=true` |
