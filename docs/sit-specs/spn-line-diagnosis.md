# SIT Specification S4: SPN Dedicated-Line Complaint - Diagnosis Only

> *Version: v0.1 (Draft)*
> *Maintained by: OpenAN Integration Testing Working Group*
> *Language: English*
> *Scenario slug: `spn-line-diagnosis` - Case IDs: `[SIT-spn-line-diagnosis-<number>]`*
> *Scenario baseline: [sit-scenarios.md](../sit-scenarios.md) S4*
> *Governance baseline: [OpenAN Integration Testing Process and Framework](../OpenAN%20Integration%20Testing%20Process%20and%20Framework.md) (cited as "Framework" below)*

---

## 1. Scope

This specification defines the SIT requirements for scenario S4 (SPN Dedicated-Line Complaint, diagnosis only), derived from China Mobile Guangdong Phase 1 (https://openan.dev/best-practices/guangdong-mobile-a2at-usecase.html).

**In scope** - the single-city, two-layer diagnosis closed loop:

1. Complaint intake: an enterprise dedicated-line complaint flows through the call center / process center / fault center (10086 / EOMS / WAIMO, simulated by test stubs) to the transmission workbench agent;
2. Agent discovery: the workbench agent discovers the SPN domain agent via the Registry Center;
3. Diagnosis execution: workbench agent and SPN domain agent collaborate over A2A-T basic capabilities (registration, orchestration, basic business flows) to diagnose the dedicated line using near-end and far-end network data;
4. Conclusion: a structured diagnosis conclusion (root cause classification + supporting evidence) is produced and made available for human expert confirmation.

**Both validated integration approaches are first-class variants and must each be covered:**

| Approach | Path | Phase 1 status |
| --- | --- | --- |
| A - direct invocation | Workbench agent directly invokes the SPN agent's A2A-T interface | Validated in production pilot |
| B - orchestration-driven | Orchestration Center composes/retrieves the workflow and drives the invocation | Validated in production pilot |

**What distinguishes S4 from neighboring scenarios:**

| Property | S2 (`cross-domain-complaint`) | S4 (this spec) | S5 (`spn-line-full-process`) |
| --- | --- | --- | --- |
| Domain | Mobile: wireless / core / SPN / optimization | Transmission: SPN dedicated line | Same SPN line |
| Collaboration | Dynamic negotiation, generalization | Basic flows, two-layer | Three-layer, advanced capabilities |
| Closed-loop scope | Diagnosis + write-back + closure | **Diagnosis only** | Diagnosis + authorized restoration + verification + closure |
| Protocol capabilities | Negotiation-T in business loop | Basic only | Negotiation-T / Authorization-T / Notification-T |

**Out of scope** (do not duplicate here):

- Service restoration, authorization, recovery notification, automatic closure -> S5. **S4 cases must assert that no restoration/repair/write action toward network elements occurs** (scope guard, §6);
- Negotiation-T / Authorization-T / Notification-T behavior -> S5 and `[SIT-a2at-protocol-*]`;
- Cross-city, three-layer topology -> S5;
- Mobile-domain complaint handling -> S2; broadband complaint branches -> S1;
- Protocol schema conformance and dual-transport equivalence -> `[SIT-a2at-protocol-*]`;
- Single-API / single-module checks -> FIT; performance / stability thresholds -> specialized testing.

## 2. System Under Test

### 2.1 Topology (single city, two agent layers)

```
10086 / EOMS / WAIMO fault center (test stubs)
        | complaint ticket
        v
transmission workbench agent (host_agent + workflow-exec-engine, embeds a2a-t-sdk)
        |                       |
        | approach A: direct    | approach B: orchestration-driven
        | A2A-T invocation      v
        |               Orchestration Center <--> Registry Center
        |                       |
        +-----------+-----------+
                    | A2A-T Task-T (basic flows)
                    v
        SPN domain agent (sample mock agent emulating the NCE SPN agent, OMC-based)
                    |
                    v
        SPN line data fixture: near-end / far-end NE readings
        (optical power, module types, attenuation settings)
                    |
                    v
        structured diagnosis conclusion -> human expert confirmation (stub)
```

- Two agent layers only: workbench agent -> SPN domain agent. No third-layer fault-center agent participates in execution (the fault center is an intake/write-back stub);
- The dedicated line has a near end and a far end (as in the live pilot between two sites); both ends' data are fixture-provided through the SPN domain agent;
- The SPN domain agent is a sample mock agent shipped with the distribution, carrying S4 scenario payloads; it emulates the OMC-based NCE SPN agent's diagnostic data interface, not real OMC integration.

### 2.2 Components and dependency constraints

| Component | Role in S4 | Constraint |
| --- | --- | --- |
| `registry-center` (HTTPS :5000) | Registration / discovery of workbench and SPN agents | mTLS client identity (`REGISTRY_CLIENT_CERT/KEY/CA_CERT`) |
| `orchestration-center` (:5001) | Approach B workflow composition/retrieval and driven invocation | `workflow-exec-engine>=0.1.1,<0.2`, `a2a-t-sdk>=1.2.0,<2`; runtime dependency on registry-center |
| Transmission workbench agent (`host_agent` + `workflow-exec-engine`) | Diagnosis driver; supports both integration approaches | Embeds `a2a-t-sdk`; approach selection mechanism per §9 item 2 |
| SPN domain agent | Sample mock agent with S4 line-data scenario payloads | Registered into Registry Center; endpoints via `MOCK_AGENTS_HOST` / `SAMPLE_AGENTS_HOST` |
| 10086 / EOMS / WAIMO stubs | Ticket intake source; conclusion receiver | Test-side stubs; ticket schema per §9 item 3 |
| Human expert confirmation stub | Receives conclusion + evidence for confirmation | Test-side stub; contract per §9 item 5 |
| LLM dependency | Diagnosis reasoning where used | `USE_MOCK_LLM=true` for deterministic CI runs; real-LLM runs are an optional variant with deterministic assertions only |

All centers and agents under test deploy from the RC image package (`IMAGE_REGISTRY` / `IMAGE_TAG`), `DEPLOY_MODE=online-helm` or `offline-compose`, real environment per Framework §5.1.

## 3. Environment and Configuration Contract

Reuse `e2e/.env.template` (Framework §6.6):

| Variable | Usage in S4 |
| --- | --- |
| `KUBECONFIG`, `OPENAN_NAMESPACE`, `DEPLOY_MODE` | Cluster access and deployment mode |
| `REGISTRY_CENTER_URL`, `REGISTRY_CLIENT_CERT`, `REGISTRY_CLIENT_KEY`, `REGISTRY_CA_CERT` | Registry access with mTLS identity |
| `ORCHESTRATION_CENTER_URL`, `ORCH_ACCESS_PASSWORD` | Orchestration access (approach B) |
| `LLM_CHAT_*`, `A2AT_LLM_*`, `USE_MOCK_LLM` | LLM dependency; mock toggle for determinism |
| `MOCK_AGENTS_HOST`, `SAMPLE_AGENTS_HOST` | Workbench agent and SPN domain agent endpoints |
| `IMAGE_REGISTRY`, `IMAGE_TAG` | RC build under test |
| `EVIDENCE_DIR` | Failure scene preservation |

New variables, if the lab exposes the stubs/workbench as services (introduce in the same PR that updates `e2e/.env.template` and README): `WAIMO_STUB_URL`, `WORKBENCH_AGENT_URL`, `EXPERT_CONFIRM_STUB_URL`. Intake/confirmation stubs may reuse the S2 stub pattern (ticket intake + write-back receiver) to avoid duplicate infrastructure.

Rules: no hardcoded IPs, credentials, or tokens.

## 4. Test Data and Fixtures

| Fixture | Scope | Content | Cleanup |
| --- | --- | --- | --- |
| Agent cards | module | Workbench agent + SPN domain agent registered with valid JWS signatures | Deregister test-owned cards |
| Line-data scenarios | function | Designed near-end/far-end readings with **precomputed root cause** per scenario: (a) far-end optical module fault -> far-end abnormal transmit power, local normal; (b) mismatched optical module types on the two ends; (c) incorrect attenuation setting; (d) all-normal line (no fault); (e) far-end data missing | Reset SPN agent scenario state per case |
| Complaint tickets | function | Fixed dedicated-line complaint payloads referencing the line under test | Stateless |
| Diagnosis workflow (approach B) | module | Workflow definition for driven invocation, imported into Orchestration Center | Delete in teardown |
| Intake / confirmation stubs | function | Ticket source; conclusion + evidence receiver; confirmation capture | Reset captured state per case |
| Login session | session (read-only) | Orchestration Center session | Not shared mutable state (Framework §6.5) |

**Diagnosis-correctness method**: each line-data scenario has a precomputed root cause classification and expected evidence fields. Cases assert the structured conclusion matches the expectation (classification identifier + evidence field values), never LLM-generated wording. The reference scenario set mirrors the live-pilot root causes (optical module fault, type mismatch, attenuation misconfiguration, local power normal).

- Every case independently repeatable; full suite runs twice with identical results, no manual reset.

## 5. Case Matrix

| Case ID | Name | Variant coverage | Priority | Execution |
| --- | --- | --- | --- | --- |
| `[SIT-spn-line-diagnosis-001]` | E2E diagnosis via orchestration-driven invocation (approach B) | far-end optical module fault scenario | P0 | smoke, full |
| `[SIT-spn-line-diagnosis-002]` | E2E diagnosis via direct A2A-T invocation (approach A) | same scenario, direct path | P0 | smoke, full |
| `[SIT-spn-line-diagnosis-003]` | Integration-approach equivalence: A and B yield consistent conclusions | A vs B comparison | P1 | full |
| `[SIT-spn-line-diagnosis-004]` | Root-cause variant coverage (type mismatch; attenuation misconfiguration; all-normal) | scenario matrix | P1 | full |
| `[SIT-spn-line-diagnosis-005]` | Registration and discovery correctness for both agents | basic capabilities | P1 | full |
| `[SIT-spn-line-diagnosis-006]` | SPN agent unreachable: defined failure, no fabricated diagnosis | fault injection | P1 | full |
| `[SIT-spn-line-diagnosis-007]` | Expert confirmation receives full evidence; no repair action ever occurs | human-in-the-loop + scope guard | P2 | full |
| `[SIT-spn-line-diagnosis-008]` | Far-end data missing: defined degraded conclusion, not a fabricated root cause | partial data | P2 | full |

P0/P1 cases must be `Automatable=Yes` with Requirement Link filled (scenario epic issue).

### 5.1 Case definitions (preconditions / steps / assertions / cleanup)

**001 - Approach B E2E diagnosis (P0)**
- Preconditions: RC centers deployed; workbench + SPN agents registered; diagnosis workflow imported; line-data scenario (a) loaded (far-end optical module fault); intake stub ready; `USE_MOCK_LLM=true`.
- Steps: (1) submit the dedicated-line complaint ticket; (2) observe workflow retrieval and driven invocation via SSE/SDK events; (3) wait for terminal diagnosis state with framework wait/retry.
- Assertions: the diagnosis workflow was retrieved and executed (workflow identifier match); SPN agent participated (agent identifier in task events); terminal state `complete`; conclusion structure present with root cause classification = far-end optical module fault (precomputed expectation), far-end transmit power evidence abnormal and local transmit power evidence normal (fixture values); **no restoration/repair command issued** (scope guard).
- Cleanup: delete execution records per fixture rules; reset scenario state.

**002 - Approach A E2E diagnosis (P0)**
- Preconditions: same scenario (a); workbench configured for direct invocation (mechanism per §9 item 2); Orchestration Center not in the invocation path.
- Steps: submit the same ticket; observe direct A2A-T invocation.
- Assertions: workbench invoked the SPN agent's A2A-T interface directly (task events show workbench -> SPN peer identities; no orchestration-driven execution record for this ticket); terminal state and conclusion match the same precomputed expectation as 001; scope guard holds.

**003 - Approach equivalence (P1)**
- Steps: run the same ticket under A and B (two independent executions).
- Assertions: root cause classification identical; evidence field values identical; participating agent set identical; both terminal states `complete`. Differences allowed only in execution-path metadata (workflow ID present in B, absent in A) - asserted explicitly, not ignored.

**004 - Root-cause variants (P1)**
- Steps: run scenarios (b) mismatched module types, (c) incorrect attenuation, (d) all-normal, under approach B (approach A covered by 002/003; variant x approach full cross is P2-level coverage, not required here).
- Assertions: each conclusion's classification equals the precomputed expectation; scenario (d) yields an explicit "no fault found" classification, never a fabricated root cause; evidence fields carry the corresponding fixture readings.

**005 - Registration and discovery (P1)**
- Steps: register both agents; query discovery as performed by the workbench; run one diagnosis.
- Assertions: agent cards discoverable with correct org/name/capability fields matching registration; workbench resolves the SPN agent via registry (discovery event/audit); invocation carries the discovered identity; an unregistered SPN agent is not invocable (negative probe: discovery returns no match, workbench reports defined error).

**006 - SPN agent unreachable (P1)**
- Preconditions: SPN agent endpoint made unreachable (test-controlled fault injection).
- Steps: submit ticket under both approaches (sequentially).
- Assertions: terminal state is a defined failure identifying the unavailable agent; **no diagnosis conclusion is produced** (absence assertion - a failure must not carry a root cause); intake stub receives the defined error write-back; after restoring the agent, a fresh ticket diagnoses normally (recovery probe).
- Cleanup: restore agent; verify registry health state recovers.

**007 - Expert confirmation + scope guard (P2)**
- Steps: run a diagnosis to conclusion; capture the confirmation request at the expert stub.
- Assertions: confirmation request contains the conclusion and full supporting evidence (near/far-end readings, per-agent task results, timestamps); ticket state reflects "awaiting confirmation", not auto-closed; **across the entire run, zero restoration/repair/write commands toward any NE** (command/event log absence assertion - this is the S4/S5 boundary guard).

**008 - Far-end data missing (P2)**
- Preconditions: scenario (e) - far-end readings unavailable.
- Steps: submit ticket; observe.
- Assertions: conclusion is a defined degraded outcome (e.g., "insufficient far-end data" classification per contract §9 item 1), explicitly marking the missing data; no fabricated far-end evidence values; local-end evidence still reported; terminal state is defined (degraded-complete or failed per contract), never silent hang.

## 6. Assertion and Evidence Rules

- Deterministic assertions only: workflow/agent/ticket identifiers, root cause classification identifiers, evidence field values against fixtures, terminal states, event presence/absence, discovery results. **Never assert on LLM-generated text**;
- **Scope guard is a standing assertion**: every S4 case asserts absence of restoration/repair/write actions toward network elements. Any such action observed = case failure regardless of other assertions (S4 is diagnosis only; restoration belongs to S5);
- No `sleep`; framework wait/retry on terminal events (Framework §6.3);
- No implicit case ordering; 003 may group the A/B runs in one test function per Framework §6.3 with each case ID independently runnable;
- On failure preserve: ticket lifecycle, SSE/SDK event trace, discovery audit, conclusion payload, relevant Pod logs, K8s events into `EVIDENCE_DIR`;
- Teardown: executions, imported workflows, test-owned cards, stub state, injected faults (Framework §6.5).

## 7. Tags, Naming, and Code Layout

- Test file: `e2e/system-integration/spn-line-diagnosis/test_spn_line_diagnosis.py`;
- Test functions: `test_<action>_<expected_result>` (e.g., `test_submit_line_complaint_direct_invocation_matches_orchestrated_conclusion`); optional class grouping `TestSpnLineDiagnosis`;
- Tags - all five dimensions (Framework §6.4):

| Dimension | Values for S4 |
| --- | --- |
| feature | `system-integration` |
| environment | `online` / `offline` as supported by the lab |
| components | `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent` |
| priority | `P0` / `P1` / `P2` per §5 matrix |
| execution | `smoke` (001, 002), `full` (all) |

- Case table rows follow the fixed 16-column template; Module = `system-integration`; Component Deps as above; orchestration keys in Notes (`protocol_primitive` = Task-T basic flows; integration approach A/B noted per case).
- Fixture reuse: S5 reuses S4's line-data scenarios and agent fixtures; shared fixture code lives in the scenario package's `utils/`, not duplicated per scenario.

## 8. Execution, CI Mapping, and Gates

| Trigger | S4 subset | Basis |
| --- | --- | --- |
| Daily build | smoke: 001, 002 | Framework §7.2 |
| RC-0 / RC-1 | full: 001-008 | Framework §7.2, §4.3.2/§4.3.3 |
| Pre-release | all S4 cases rerun on RC | Framework §7.2 |

- SIT exit gate: S4 pass rate = 100%, no skips (Framework §8.3);
- Defects: evidence-attached issues, P0 24h response / current-release fix, regression case after fix (Framework §9);
- Archive: plan `docs/plans/<YY>-<season>/`, report `docs/reports/<YY>-<season>/`, JUnit XML per Framework §7.1/§11.3.

## 9. Open Items (must be resolved before case implementation)

| # | Item | Owner | Impact |
| --- | --- | --- | --- |
| 1 | Diagnosis conclusion schema: root cause classification vocabulary (incl. "no fault" and "insufficient data" classes), near/far-end evidence fields, degraded-terminal-state naming | workbench/SPN agent contributors + Integration Testing WG | Blocks 001/004/008 assertions |
| 2 | Integration-approach selection mechanism: how the lab forces approach A (direct) vs B (orchestration-driven) per execution | orchestration-center WG | Blocks 002/003; both approaches are mandatory coverage |
| 3 | Intake stub ticket schema (10086/EOMS/WAIMO chain); reuse of S2 stub pattern | Integration Testing WG | Blocks ticket fixtures |
| 4 | S4 line-data scenario payloads on the shipped sample agents (optical power / module type / attenuation fixtures; test data authoring, not new agents) | Integration Testing WG | Blocks fixture content for all cases |
| 5 | Expert confirmation interface contract (request payload, ticket state naming) | workbench contributors | Blocks 007 assertions |
| 6 | Real-LLM variant inclusion in RC runs (deterministic assertions only) | Integration Testing WG | Optional variant; default CI stays `USE_MOCK_LLM=true` |