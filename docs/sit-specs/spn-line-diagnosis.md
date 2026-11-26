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

| Case ID | Name | Variant coverage | Priority | Status | Execution | Component Deps |
| --- | --- | --- | --- | --- | --- | --- |
| `[SIT-spn-line-diagnosis-001]` | E2E diagnosis via orchestration-driven invocation (approach B) | far-end optical module fault scenario | P0 | Draft | excluded until ready | `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent` |
| `[SIT-spn-line-diagnosis-002]` | E2E diagnosis via direct A2A-T invocation (approach A) | same scenario, direct path | P0 | Draft | excluded until ready | `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent` |
| `[SIT-spn-line-diagnosis-003]` | Integration-approach equivalence: A and B yield consistent conclusions | A vs B comparison | P1 | Draft | excluded until ready | `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent` |
| `[SIT-spn-line-diagnosis-004]` | Root-cause variant coverage (type mismatch; attenuation misconfiguration; all-normal) | scenario matrix, approach B | P1 | Draft | excluded until ready | `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent` |
| `[SIT-spn-line-diagnosis-005]` | Registration and discovery correctness for both agents | basic capabilities, approach B | P1 | Draft | excluded until ready | `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent` |
| `[SIT-spn-line-diagnosis-006]` | SPN agent unreachable: defined failure, no fabricated diagnosis | fault injection, approaches A and B | P1 | Draft | excluded until ready | `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent` |
| `[SIT-spn-line-diagnosis-007]` | Expert confirmation receives full evidence; no repair action ever occurs | human-in-the-loop + scope guard, approach B | P2 | Draft | excluded until ready | `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent` |
| `[SIT-spn-line-diagnosis-008]` | Far-end data missing: defined degraded conclusion, not a fabricated root cause | partial data, approach B | P2 | Draft | excluded until ready | `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent` |

All cases are Draft because §9 items 3 and 4 block the ticket and line-data fixtures required by every execution, while items 1, 2, and 5 add case-specific blockers. Draft definitions are design input only: they must not be implemented, scheduled, or counted in smoke/full execution or exit-gate denominators. A case may become Ready only after every open item affecting its preconditions, steps, assertions, and cleanup is resolved. P0/P1 rows use Requirement Link https://github.com/project-openan/integration-test/issues/34 and `Automatable=Yes` as the final automation requirement; that future automation requirement does not make a Draft row currently executable.

The matrix records runtime path dependencies, not scenario-wide blanket labels. Direct approach A (002) excludes `orchestration-center`; orchestration-driven 001/003/004/005/006/007/008 include it because at least one execution uses approach B. The authoritative machine-readable code labels are the per-case **Component Deps** values in the generated CSV; §7's scenario list is only a union and must not be copied to every case.

### 5.1 Case definitions (preconditions / steps / assertions / cleanup)

**001 - Approach B E2E diagnosis (P0)**
- Status: **Draft**; blocked by §9 items 1 (conclusion), 3 (ticket), and 4 (line-data) contracts.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Component Deps: `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent`.
- Preconditions: RC centers are deployed; workbench and SPN agents are registered; the approach-B workflow is imported with a known ID; scenario (a) has fixed far-end abnormal transmit power and near-end normal values and expected classification `far_end_optical_module_fault`; intake and evidence capture are reset; `USE_MOCK_LLM=true`.
- Steps:
  1. Submit the scenario-(a) complaint through the intake stub and record its ticket ID.
  2. Capture workflow retrieval, task events, and terminal state for that ticket using framework wait/retry.
  3. Retrieve the structured conclusion, evidence, and complete command/event log.
- Assertions:
  - Step 1: exactly one ticket is accepted and all captured execution records reference its ID.
  - Step 2: the executed workflow ID equals the imported ID; task peer identities include workbench and SPN agent; terminal state is `complete`.
  - Step 3: classification equals `far_end_optical_module_fault`; far-end and near-end evidence fields exactly equal scenario-(a) fixture values; the log contains zero restoration, repair, or NE write commands.
- finally/Cleanup: in `finally`, delete the test execution/workflow, reset scenario and stub state, and clear event capture. Assert the ticket/workflow no longer exists, the SPN scenario is baseline, and no execution or NE write remains active; cleanup failure fails the case.
- Automation: `e2e/system-integration/spn-line-diagnosis/test_spn_line_diagnosis.py::test_orchestrated_optical_fault_returns_fixture_conclusion` (planned after contract confirmation).

**002 - Approach A E2E diagnosis (P0)**
- Status: **Draft**; blocked by §9 items 2 (direct-approach selection), 1 (conclusion), 3 (ticket), and 4 (line-data) contracts.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Component Deps: `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent`; `orchestration-center` is not in this invocation path.
- Preconditions: workbench and SPN agents are registered; the workbench is explicitly configured for direct invocation; scenario (a) has fixed far-end abnormal transmit power and near-end normal values and expected classification `far_end_optical_module_fault`; orchestration execution capture is armed to prove non-participation; `USE_MOCK_LLM=true`.
- Steps:
  1. Submit a scenario-(a) complaint and record its ticket ID.
  2. Capture direct task events.
  3. Query orchestration execution records until the diagnosis terminates.
  4. Retrieve the conclusion, evidence, and complete command/event log.
- Assertions:
  - Step 1: the ticket is accepted and the workbench selects approach A for its execution.
  - Steps 2 and 3: task events identify workbench as caller and SPN agent as peer; no orchestration-driven execution or workflow ID exists for the ticket; terminal state is `complete`.
  - Step 4: classification equals `far_end_optical_module_fault`; far-end and near-end evidence exactly equal scenario-(a) fixture values; zero restoration, repair, or NE write commands occur.
- finally/Cleanup: in `finally`, reset approach selection, scenario and stubs, and remove test execution records. Assert the ticket has no remaining execution, direct selection is reset, scenario data is baseline, and no orchestration record was created during cleanup; cleanup failure fails the case.
- Automation: `e2e/system-integration/spn-line-diagnosis/test_spn_line_diagnosis.py::test_direct_optical_fault_returns_fixture_conclusion_without_orchestration` (planned after contract confirmation).

**003 - Approach equivalence (P1)**
- Status: **Draft**; blocked by §9 items 2 (approach selection), 1 (conclusion), 3 (ticket), and 4 (line-data) contracts.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Component Deps: `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent` because this case executes both paths.
- Preconditions: both agents are registered; direct selection and the approach-B workflow are available; two independent tickets use identical scenario-(a) readings and expected classification `far_end_optical_module_fault`; execution captures are isolated by ticket ID.
- Steps:
  1. Submit ticket A with direct invocation.
  2. Capture its terminal result and conclusion.
  3. Submit ticket B through orchestration-driven invocation.
  4. Capture its terminal result and conclusion.
  5. Normalize only the contracted execution-path metadata.
  6. Compare the two conclusions, evidence, participants, and logs.
- Assertions:
  - Steps 1 and 2: A reaches `complete`, has no workflow ID/orchestration execution, and its conclusion/evidence equal scenario-(a) expectations.
  - Steps 3 and 4: B reaches `complete`, has the expected workflow ID and orchestration execution, and its conclusion/evidence equal scenario-(a) expectations.
  - Steps 5 and 6: A and B classification identifiers, evidence values, and workbench/SPN participant sets are identical; workflow metadata is absent for A and present for B; both logs contain zero restoration, repair, or NE write commands.
- finally/Cleanup: in `finally`, delete both executions and the test workflow, reset direct selection, scenarios, and stubs. Assert neither ticket remains active, no A/B capture crosses the other ticket ID, and all fixtures equal baseline; cleanup failure fails the case.
- Automation: `e2e/system-integration/spn-line-diagnosis/test_spn_line_diagnosis.py::test_direct_and_orchestrated_paths_return_identical_conclusions` (planned after contract confirmation).

**004 - Root-cause variants (P1)**
- Status: **Draft**; blocked by §9 items 1 (classification/evidence schema), 3 (ticket), and 4 (sample-agent payload) contracts.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Component Deps: `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent`.
- Preconditions: approach B is configured; independent fixtures define (b) mismatched module types, (c) incorrect attenuation, and (d) all-normal readings, each with exact expected classification and evidence values; workflow, stubs, and event capture are reset for each variant.
- Steps:
  1. For each of (b), (c), and (d), load exactly one variant.
  2. For the loaded variant, submit a fresh ticket through approach B.
  3. Wait for each ticket's terminal state.
  4. Retrieve its conclusion and evidence by ticket ID.
  5. Inspect each full event/command log before resetting and loading the next variant.
- Assertions:
  - Steps 1 and 2: each execution uses the imported workflow and the ticket references only the currently loaded variant.
  - Steps 3 and 4: (b) returns the contracted module-type-mismatch classification, (c) returns the contracted attenuation-misconfiguration classification, and (d) returns the contracted no-fault classification; every evidence field exactly equals its variant fixture and no other variant's values appear.
  - Step 5: all three executions reach `complete`; each log contains zero restoration, repair, or NE write commands and no cross-ticket evidence.
- finally/Cleanup: after every variant and in outer `finally`, delete its execution and reset scenario/stub state; finally delete the workflow. Assert all three tickets are inactive, the all-normal baseline is restored, and no residual variant data or NE write remains; cleanup failure fails the case.
- Automation: `e2e/system-integration/spn-line-diagnosis/test_spn_line_diagnosis.py::test_orchestrated_root_cause_variants_match_fixture_classifications` (planned after contract confirmation).

**005 - Registration and discovery (P1)**
- Status: **Draft**; blocked by §9 item 3 (ticket fixtures and executable discovery/error details) and §9 item 4 (line-data fixtures) needed by the negative probe.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Component Deps: `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent`.
- Preconditions: registry is healthy and empty of test cards; workbench and SPN card fixtures have exact org/name/capability values; approach-B workflow and scenario (a) are ready; cleanup retains original card state for restoration.
- Steps:
  1. Register both agent cards.
  2. Query discovery using the workbench's capability query.
  3. Submit a scenario-(a) ticket through approach B.
  4. Capture discovery and invocation identities.
  5. Deregister only the SPN card.
  6. Repeat discovery.
  7. Submit a fresh negative-probe ticket.
  8. Restore the SPN registration.
  9. Repeat discovery as a recovery probe.
- Assertions:
  - Steps 1 and 2: both returned cards exactly match the registered org/name/capability fields and no unexpected SPN match exists.
  - Steps 3 and 4: discovery audit identifies the SPN card, the invocation carries that discovered identity, workflow execution reaches `complete`, and no NE write occurs.
  - Steps 5, 6, and 7: discovery returns no SPN match; the negative ticket reaches the contracted discovery-error terminal state, produces no diagnosis conclusion, and issues no agent invocation or NE write.
  - Steps 8 and 9: the restored card is returned with its original fields and registry health is ready.
- finally/Cleanup: in `finally`, restore both original card registrations, remove negative/positive executions and workflow, and reset scenario/stubs. Assert registry contents equal the captured baseline, both agents are healthy when present in baseline, and no test ticket remains active; cleanup failure fails the case.
- Automation: `e2e/system-integration/spn-line-diagnosis/test_spn_line_diagnosis.py::test_registry_discovery_controls_invocation_and_recovers` (planned after contract confirmation).

**006 - SPN agent unreachable (P1)**
- Status: **Draft**; blocked by §9 item 3 (ticket fixtures and contracted failure/write-back behavior) and §9 item 4 (line-data fixtures).
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Component Deps: `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent` because this case executes both paths.
- Preconditions: both agents are registered and healthy; direct selection and approach-B workflow are available; scenario (a) and its expected optical-fault conclusion are loaded; intake/error capture is reset; a reversible endpoint fault is armed without changing registration.
- Steps:
  1. Make the SPN endpoint unreachable.
  2. Submit a direct-path ticket and wait for its terminal failure.
  3. With the same fault active, submit an independent orchestration-driven ticket and wait for its terminal failure.
  4. Inspect both conclusions/write-backs and command logs.
  5. Remove the endpoint fault.
  6. Wait for registry/agent health.
  7. Submit a fresh direct-path recovery ticket.
  8. Retrieve its conclusion.
- Assertions:
  - Steps 1 and 2: the direct execution reaches the contracted unavailable-agent failure identifying SPN; it has no workflow ID and no diagnosis conclusion.
  - Step 3: the orchestration execution reaches the same contracted failure identifying SPN and expected workflow ID; it has no diagnosis conclusion.
  - Steps 4, 5, and 6: each intake stub capture contains exactly the contracted error write-back for its own ticket and no root cause; both logs contain zero restoration, repair, or NE write commands; health becomes ready after fault removal.
  - Steps 7 and 8: the recovery ticket reaches `complete`, returns classification `far_end_optical_module_fault` with exact scenario-(a) evidence, and confirms normal post-fault diagnosis.
- finally/Cleanup: in `finally`, remove endpoint fault, restore approach selection, delete test workflow/executions, and reset scenarios/stubs. Assert endpoint and registry health recover, all tickets are inactive, scenario data equals baseline, and no residual fault or NE write remains; cleanup failure fails the case.
- Automation: `e2e/system-integration/spn-line-diagnosis/test_spn_line_diagnosis.py::test_unreachable_spn_agent_fails_without_diagnosis_and_recovers` (planned after contract confirmation).

**007 - Expert confirmation + scope guard (P2)**
- Steps:
  1. Submit an approach-B diagnosis ticket.
  2. Wait for its structured conclusion.
  3. Capture the expert-confirmation request at the expert stub and read the ticket state.
  4. Retrieve the near/far-end evidence, per-agent task results, timestamps, and the entire command and event log.
- Assertions:
  - Steps 1 and 2: diagnosis reaches its contracted conclusion stage with the expected workflow and ticket identifiers.
  - Step 3: exactly one confirmation request in the contracted schema is received and the ticket state reflects awaiting confirmation, not auto-closed.
  - Step 4: the confirmation request contains the conclusion and full supporting evidence (near/far-end readings, per-agent task results, timestamps), and across the entire run zero restoration, repair, or NE write commands occur toward any NE (command/event log absence assertion - this is the S4/S5 boundary guard).
- finally/Cleanup: reset confirmation/intake stubs and scenario state, delete execution/workflow, and assert no ticket remains awaiting confirmation or closed automatically.

**008 - Far-end data missing (P2)**
- Preconditions: scenario (e) - far-end readings unavailable.
- Steps:
  1. Submit an approach-B ticket for scenario (e) and record its ticket ID.
  2. Capture execution through the contracted terminal state.
  3. Retrieve its conclusion and evidence.
  4. Inspect all evidence values and the complete command and event log.
- Assertions:
  - Step 1: the ticket is accepted and execution references the missing-far-end fixture.
  - Steps 2 and 3: the conclusion is a defined degraded outcome (e.g., the insufficient far-end data classification per contract §9 item 1) that explicitly marks the missing data, no fabricated far-end evidence values appear, local-end evidence is still reported, and the terminal state is the contracted degraded-complete or failed state, never a silent hang.
  - Step 4: zero restoration, repair, or NE write commands occur.
- finally/Cleanup: restore complete line data, remove execution/workflow and stub captures, and assert scenario state and ticket lifecycle return to baseline with no NE write.

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
| components | Scenario union only: `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent`; use §5 per-case Component Deps for code labels |
| priority | `P0` / `P1` / `P2` per §5 matrix |
| execution | Ready cases only: `smoke` (001, 002 after promotion), `full` (the other cases after promotion); all current cases are `excluded until ready` |

- Case table rows follow the fixed 16-column template; Module = `system-integration`; Component Deps are copied from the same case's §5 matrix row, not from the scenario union (in particular, direct 002 has no `orchestration-center`); orchestration keys in Notes (`protocol_primitive` = Task-T basic flows; integration approach A/B noted per case). Draft rows must not be emitted as executable automation or given smoke/full code labels.
- Fixture reuse: S5 reuses S4's line-data scenarios and agent fixtures; shared fixture code lives in the scenario package's `utils/`, not duplicated per scenario.

## 8. Execution, CI Mapping, and Gates

| Trigger | S4 subset | Basis |
| --- | --- | --- |
| Daily build | smoke: Ready cases designated smoke; currently none | Framework §7.2 |
| RC-0 / RC-1 | full: all Ready cases; currently none | Framework §7.2, §4.3.2/§4.3.3 |
| Pre-release | all Ready S4 cases rerun on RC; currently none | Framework §7.2 |

- Draft cases 001-008 are excluded from current smoke/full selections, automation implementation, and every exit-gate denominator. With zero Ready cases, S4 readiness is **not evaluable** and must not be reported as passed; the smoke/full and exit gates remain blocked pending contract confirmation and explicit per-case promotion.
- Once any case becomes Ready, the SIT exit gate applies only to the Ready set: pass rate = 100%, no skips among selected Ready cases (Framework §8.3). Draft cases are neither passes, failures, nor skips and never increase the denominator;
- Defects: evidence-attached issues, P0 24h response / current-release fix, regression case after fix (Framework §9);
- Archive: plan `docs/plans/<YY>-<season>/`, report `docs/reports/<YY>-<season>/`, JUnit XML per Framework §7.1/§11.3.

## 9. Open Items (must be resolved before case implementation)

| # | Item | Owner | Impact |
| --- | --- | --- | --- |
| 1 | Diagnosis conclusion schema: root cause classification vocabulary (incl. "no fault" and "insufficient data" classes), near/far-end evidence fields, degraded-terminal-state naming | workbench/SPN agent contributors + Integration Testing WG | Blocks 001/002/003/004/008 assertions |
| 2 | Integration-approach selection mechanism: how the lab forces approach A (direct) vs B (orchestration-driven) per execution | orchestration-center WG | Blocks 002/003; both approaches are mandatory coverage |
| 3 | Intake stub ticket schema (10086/EOMS/WAIMO chain); reuse of S2 stub pattern | Integration Testing WG | Blocks ticket fixtures |
| 4 | S4 line-data scenario payloads on the shipped sample agents (optical power / module type / attenuation fixtures; test data authoring, not new agents) | Integration Testing WG | Blocks fixture content for all cases |
| 5 | Expert confirmation interface contract (request payload, ticket state naming) | workbench contributors | Blocks 007 assertions |
| 6 | Real-LLM variant inclusion in RC runs (deterministic assertions only) | Integration Testing WG | Optional variant; default CI stays `USE_MOCK_LLM=true` |
