# SIT Specification S3: Intent-Driven Dynamic Energy Saving

> *Version: v0.1 (Draft)*
> *Maintained by: OpenAN Integration Testing Working Group*
> *Language: English*
> *Scenario slug: `intent-energy-saving` - Case IDs: `[SIT-intent-energy-saving-<number>]`*
> *Scenario baseline: [sit-scenarios.md](../sit-scenarios.md) S3*
> *Governance baseline: [OpenAN Integration Testing Process and Framework](../OpenAN%20Integration%20Testing%20Process%20and%20Framework.md) (cited as "Framework" below)*

---

## 1. Scope

This specification defines the SIT requirements for scenario S3 (Intent-Driven Dynamic Energy Saving), derived from China Mobile Henan Practice 2 (https://openan.dev/best-practices/henan-mobile-openan-usecase.html).

**In scope** - the five-stage optimization/control closed loop:

1. **Intent intake**: an electricity-cost optimization intent (not raw energy saving) enters the energy-saving agent, together with the dynamic time-of-use tariff policy;
2. **Data perception**: network load and energy-consumption data are collected from the (simulated) network elements;
3. **Value decision**: the agent decides where/when to act against the tariff schedule, balancing electricity cost and user experience;
4. **Orchestration scheduling**: Orchestration Center schedules the decided actions toward the vendor wireless network agent;
5. **Network-element execution + effect evaluation**: the vendor agent executes energy-saving actions on the (simulated) NEs; post-execution metrics are evaluated against baseline and fed back.

**What distinguishes S3 from all other scenarios** (and therefore what its cases must actually exercise):

| Property | S1 / S2 / S4 (diagnosis) | S3 (this spec) |
| --- | --- | --- |
| Loop type | Read-only fault diagnosis | Optimization / control with **network-element write operations** |
| Goal assertion | Diagnosis conclusion structure | **Cost-first decision correctness** against a designed tariff scenario |
| Time dependency | None | Time-of-use tariff periods; tests must control the tariff clock, never depend on wall-clock time |
| Safety requirement | None beyond cleanup | Every write must be reversible; NE state restored and verified in teardown; experience guardrails enforced |
| Feedback | Ticket closure / write-back | **Effect evaluation** comparing post-execution metrics to baseline, with corrective feedback |

**Out of scope** (do not duplicate here):

- Complaint handling of any domain -> S1 / S2 / S4 / S5;
- The vendor's internal energy-saving / RF optimization algorithm quality -> vendor domain; S3 tests the **integration loop** (intent -> decision -> scheduling -> execution -> evaluation) with a simulated NE, not algorithm optimality in real radio conditions;
- Authorization-T / Negotiation-T protocol conformance -> `[SIT-a2at-protocol-*]`; if execution authorization applies to S3 writes, it is asserted as a business gate (§9 item 5), not as protocol schema testing;
- Absolute energy/cost savings benchmarks, performance thresholds -> specialized testing and release test plans (Framework §10);
- Single-API / single-module checks -> FIT.

## 2. System Under Test

### 2.1 Topology (three tiers per the published architecture)

```
PERCEPTION / DECISION TIER
  energy-saving agent (host_agent + workflow-exec-engine, embeds a2a-t-sdk)
    ^  tariff policy + intent (test fixture, controllable tariff clock)
    |  load / energy data (perception)
    v
ORCHESTRATION TIER
  Orchestration Center  <---->  Registry Center
    |  scheduled energy-saving actions (A2A-T Task-T)
    v
EXECUTION TIER
  vendor wireless network agent (sample mock agent, cross-vendor role)
    |  energy-saving commands (sleep / wake / carrier-level actions per contract)
    v
  NE simulator (test-owned stateful stub: cell state, load, energy metrics)
    |
    +--> post-execution metrics --> effect evaluation --> feedback to decision tier
```

- The NE is **always simulated** in community SIT. No case may target a real network element;
- The vendor wireless agent is a sample mock agent shipped with the distribution, carrying S3 scenario payloads; cross-vendor heterogeneity is emulated via SDK language variants where available (variant, not a separate scenario);
- Effect evaluation closes the loop back to the decision tier; a run that executes actions but produces no evaluation is a failed loop, not a partial pass.

### 2.2 Components and dependency constraints

| Component | Role in S3 | Constraint |
| --- | --- | --- |
| `registry-center` (HTTPS :5000) | Registration / discovery of energy-saving agent and vendor wireless agent | mTLS client identity (`REGISTRY_CLIENT_CERT/KEY/CA_CERT`) |
| `orchestration-center` (:5001) | Scheduling of decided actions; workflow composition/retrieval | `workflow-exec-engine>=0.1.1,<0.2`, `a2a-t-sdk>=1.2.0,<2`; runtime dependency on registry-center |
| Energy-saving agent (`host_agent` + `workflow-exec-engine`) | Perception, value decision, effect evaluation | Embeds `a2a-t-sdk` per constraint above |
| Vendor wireless network agent | Executes energy-saving actions toward the NE simulator | Sample mock agent; endpoints via `MOCK_AGENTS_HOST` / `SAMPLE_AGENTS_HOST` |
| NE simulator | Stateful test stub: cell on/sleep state, load level, energy-consumption metrics; accepts commands, reports state | Test-owned; command vocabulary and state schema per §9 item 1 |
| Tariff policy source | Time-of-use tariff schedule with controllable current period | Test fixture; injection mechanism per §9 item 2 |
| LLM dependency | Decision reasoning where used | `USE_MOCK_LLM=true` for deterministic CI runs; real-LLM runs are an optional variant with deterministic assertions only |

All centers and agents under test deploy from the RC image package (`IMAGE_REGISTRY` / `IMAGE_TAG`), `DEPLOY_MODE=online-helm` or `offline-compose`, real environment per Framework §5.1.

## 3. Environment and Configuration Contract

Reuse `e2e/.env.template` (Framework §6.6):

| Variable | Usage in S3 |
| --- | --- |
| `KUBECONFIG`, `OPENAN_NAMESPACE`, `DEPLOY_MODE` | Cluster access and deployment mode |
| `REGISTRY_CENTER_URL`, `REGISTRY_CLIENT_CERT`, `REGISTRY_CLIENT_KEY`, `REGISTRY_CA_CERT` | Registry access with mTLS identity |
| `ORCHESTRATION_CENTER_URL`, `ORCH_ACCESS_PASSWORD` | Orchestration access |
| `LLM_CHAT_*`, `A2AT_LLM_*`, `USE_MOCK_LLM` | LLM dependency; mock toggle for determinism |
| `MOCK_AGENTS_HOST`, `SAMPLE_AGENTS_HOST` | Energy-saving agent and vendor wireless agent endpoints |
| `IMAGE_REGISTRY`, `IMAGE_TAG` | RC build under test |
| `EVIDENCE_DIR` | Failure scene preservation |

New variables required by S3 (introduce in the same PR that updates `e2e/.env.template` and README):

| Variable | Purpose |
| --- | --- |
| `NE_SIM_URL` | NE simulator state/command endpoint (test-owned stub) |
| `TARIFF_SOURCE_URL` | Tariff policy source with controllable current period, if exposed as a service rather than an in-process fixture |

Rules: no hardcoded IPs, credentials, or tokens; the NE simulator and tariff source are test infrastructure, never production endpoints.

## 4. Test Data and Fixtures

| Fixture | Scope | Content | Cleanup |
| --- | --- | --- | --- |
| Tariff schedule | module | Deterministic time-of-use periods (peak / flat / valley) with fixed prices; controllable "current period" override; designed so each scenario has a **precomputed expected action set** | Reset current period to baseline |
| Network state | function | Cell inventory with load levels and baseline energy metrics; includes high-load cells that guardrails must protect | Reset NE simulator to baseline state; **verify restoration** |
| NE simulator | function | Stateful stub implementing the command vocabulary (§9 item 1); records every command with timestamp; exposes state + metrics queries | Reset state and command log per case |
| Agent cards | module | Energy-saving agent + vendor wireless agent registered with valid JWS signatures | Deregister test-owned cards |
| Guardrail config | module | Experience protection rules (e.g., load threshold above which a cell must not be put to sleep) per §9 item 3 | Restore default config |
| Intent payloads | function | Cost-optimization intent; variants: valley-period intent, period-switch sequence, guardrail-conflict intent, multi-cell intent | Stateless |
| Login session | session (read-only) | Orchestration Center session | Not shared mutable state (Framework §6.5) |

**Decision-correctness method**: fixtures are designed so the cost-optimal action set is computable in advance (fixed tariffs + fixed loads + fixed action vocabulary). Cases assert the executed action set equals the precomputed expectation - never "the decision looks reasonable" and never LLM-generated wording.

**Safety red lines** (apply to every S3 case):

1. All write commands target the NE simulator only;
2. Every case that changes NE state must restore baseline in teardown and **assert the restoration** (state query equals baseline); a case leaving modified NE state fails cleanup verification;
3. No case may depend on wall-clock time; tariff period is always fixture-controlled;
4. Guardrail-protected cells must never receive a forbidden action in any case, including fault-injection cases.

## 5. Case Matrix

| Case ID | Name | Variant coverage | Priority | Status | Execution |
| --- | --- | --- | --- | --- | --- |
| `[SIT-intent-energy-saving-001]` | Five-stage closed loop completes in valley period | full loop, single cell | P0 | Draft | excluded until ready |
| `[SIT-intent-energy-saving-002]` | Cost-first decision correctness against tariff schedule | decision quality (precomputed expectation) | P0 | Draft | excluded until ready |
| `[SIT-intent-energy-saving-003]` | Experience guardrail blocks forbidden action on high-load cell | guardrail variant | P1 | Draft | excluded until ready |
| `[SIT-intent-energy-saving-004]` | Tariff period switch drives adapted actions | valley -> peak transition | P1 | Draft | excluded until ready |
| `[SIT-intent-energy-saving-005]` | Effect evaluation compares baseline and feeds back | evaluation / feedback stage | P1 | Draft | excluded until ready |
| `[SIT-intent-energy-saving-006]` | NE execution failure: defined degraded state, no inconsistent NE state | fault injection | P1 | Draft | excluded until ready |
| `[SIT-intent-energy-saving-007]` | Explicit restoration path and state consistency | rollback / write safety | P2 | Draft | excluded until ready |
| `[SIT-intent-energy-saving-008]` | Multi-cell / concurrent intent scheduling isolation | concurrency | P2 | Draft | excluded until ready |

All cases are Draft because §9 item 1 blocks every execution assertion; the other open items add case-specific blockers. Draft definitions are design input only: they must not be implemented, scheduled, or counted in smoke/full execution or exit-gate denominators. A case may become Ready only after every open item affecting its preconditions, steps, assertions, and cleanup is resolved. P0/P1 rows use Requirement Link https://github.com/project-openan/integration-test/issues/34 and `Automatable=Yes` as the final automation requirement; that future automation requirement does not make a Draft row currently executable.

### 5.1 Case definitions (preconditions / steps / assertions / cleanup)

**001 - Five-stage closed loop (P0)**
- Status: **Draft**; blocked by the NE command/state/metrics contract and the other contracts needed to make its assertions executable.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions: RC centers are deployed; energy-saving and vendor wireless agents are registered; the NE simulator has one low-load cell at a captured baseline; the tariff fixture is set to valley with a precomputed sleep expectation; `USE_MOCK_LLM=true`; event capture is armed.
- Steps:
  1. Submit the valley cost-optimization intent for the fixture cell and record its intent ID.
  2. Collect perception, decision, scheduling, execution, and evaluation events for that intent until the terminal event, using framework wait/retry.
  3. Query the decision record, NE command log/state, and evaluation report by intent/execution ID.
- Assertions:
  - Step 1: exactly one execution context is created for the submitted intent and its ID is present in all subsequently captured records.
  - Step 2: the five stage events occur exactly once and in the order perception -> decision -> scheduling -> execution -> evaluation; the terminal state is `complete`.
  - Step 3: the NE log contains exactly the precomputed sleep command for the target cell; queried cell state equals the expected post-action state; the evaluation contains the fixture baseline and post-execution metric values and references the same execution ID.
- finally/Cleanup: in `finally`, restore the captured NE baseline, reset the tariff period, and clear captured events. Assert that every cell and metric equals its baseline, the tariff period equals baseline, and no test intent remains active; cleanup failure fails the case.
- Automation: `e2e/system-integration/intent-energy-saving/test_intent_energy_saving.py::test_valley_intent_completes_five_stage_loop` (planned after contract confirmation).

**002 - Cost-first decision correctness (P0)**
- Status: **Draft**; the action vocabulary, state schema, and executable decision record are not contracted.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions: the fixture has valley/peak prices and two cells with fixed loads; its expected cost-first set is sleep cell X and keep cell Y active, while the fixture's energy-only alternative would also sleep Y; both cells start at captured baseline states; `USE_MOCK_LLM=true`.
- Steps:
  1. Submit the cost-optimization intent for cells X and Y under the valley fixture.
  2. Capture the decision record and all resulting NE commands until execution terminates.
  3. Query both cells and compare the normalized decided and executed cell/action pairs with the fixture expectation.
- Assertions:
  - Step 1: the execution references the valley tariff fixture ID and the two requested cell IDs.
  - Step 2: the decision record identifies the valley period; every emitted command belongs to the contracted vocabulary; execution reaches `complete`.
  - Step 3: decided and executed sets both equal exactly `{(X, sleep)}`; Y receives no sleep/shutdown command; final states are X asleep and Y active.
- finally/Cleanup: in `finally`, restore both cells and the tariff fixture to baseline and clear the execution capture. Assert X and Y states and all baseline metrics are restored and no further command is emitted for the test execution; cleanup failure fails the case.
- Automation: `e2e/system-integration/intent-energy-saving/test_intent_energy_saving.py::test_valley_decision_executes_exact_cost_first_action_set` (planned after contract confirmation).

**003 - Experience guardrail (P1)**
- Status: **Draft**; blocked by the guardrail threshold/enforcement/reason contract as well as the NE command contract.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions: valley pricing makes sleep economically attractive; protected cell H exceeds the fixture guardrail threshold and eligible cell L is below it; the expected action set contains sleep for L only; both cells and guardrail configuration are captured at baseline.
- Steps:
  1. Submit one intent covering H and L.
  2. Capture the decision exclusions and NE commands until terminal state.
  3. Query final cell states and reload the guardrail configuration.
- Assertions:
  - Step 1: the execution references exactly H and L and the active guardrail fixture version.
  - Step 2: H has a structured guardrail exclusion with the contracted reason code; L has the precomputed sleep decision; the command log contains no sleep/shutdown command for H and exactly one expected sleep command for L; terminal state is `complete`.
  - Step 3: H remains in its baseline state, L reaches asleep, and the guardrail configuration is byte-for-byte equal to baseline.
- finally/Cleanup: in `finally`, restore both cells and guardrail configuration, then reset the tariff period. Assert H and L and their metrics equal baseline, guardrail configuration equals baseline, and no test command remains in flight; cleanup failure fails the case.
- Automation: `e2e/system-integration/intent-energy-saving/test_intent_energy_saving.py::test_high_load_guardrail_excludes_protected_cell` (planned after contract confirmation).

**004 - Tariff period switch (P1)**
- Status: **Draft**; blocked by tariff injection/re-evaluation and NE command/state contracts.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions: one cell starts at captured baseline; valley and peak fixtures have precomputed expected states asleep and active respectively; the fixture exposes a controllable period marker and the contracted re-evaluation trigger; `USE_MOCK_LLM=true`.
- Steps:
  1. Submit the intent in valley and wait for the valley execution/evaluation to complete.
  2. Atomically switch the fixture to peak, record the switch marker, and invoke or observe the contracted re-evaluation trigger.
  3. Capture all commands and evaluations after the marker and query final NE state.
- Assertions:
  - Step 1: the valley command set equals the precomputed sleep set, NE state is asleep, and a valley evaluation references the valley period.
  - Step 2: exactly one peak re-evaluation is associated with the switch marker and its decision references the peak period.
  - Step 3: the post-switch command set equals the precomputed wake set; no valley-period command has a timestamp after the marker; final NE state is active; distinct valley and peak evaluations reference the same intent and their respective periods.
- finally/Cleanup: in `finally`, restore NE baseline, reset the fixture to its baseline period, and disable the test re-evaluation trigger. Assert cell state/metrics and tariff period equal baseline and no subsequent command is emitted for the test intent; cleanup failure fails the case.
- Automation: `e2e/system-integration/intent-energy-saving/test_intent_energy_saving.py::test_peak_switch_executes_precomputed_adapted_actions` (planned after contract confirmation).

**005 - Effect evaluation and feedback (P1)**
- Status: **Draft**; blocked by the evaluation/baseline/degradation/corrective-feedback and NE metrics contracts.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions: one executed-action fixture has fixed baseline and post-execution metrics, including a contracted degradation signal for neighbor cell N; expected numeric deltas and the corrective target are precomputed; NE baseline and event capture are established.
- Steps:
  1. Submit the intent and wait for its initial execution ID to reach the execution stage.
  2. Publish the fixture post-execution metrics for that execution and wait for evaluation and feedback terminal events.
  3. Retrieve the evaluation, corrective task, and related NE command/state records.
- Assertions:
  - Step 1: the execution ID and baseline metric snapshot are linked to the submitted intent before post-execution metrics are supplied.
  - Step 2: exactly one evaluation references the intent/execution ID; every reported delta equals `post - baseline` for the fixture metrics; exactly one corrective feedback event carries the contracted degradation code and target N.
  - Step 3: the corrective task references the originating execution and N, and any resulting command set equals the precomputed corrective expectation without touching guardrail-protected cells.
- finally/Cleanup: in `finally`, cancel any unfinished corrective task, restore all NE cells/metrics and tariff state to baseline, and clear injected metrics. Assert all state equals baseline, injected metrics are absent, and no initial or corrective task remains active; cleanup failure fails the case.
- Automation: `e2e/system-integration/intent-energy-saving/test_intent_energy_saving.py::test_degradation_metrics_produce_linked_corrective_feedback` (planned after contract confirmation).

**006 - NE execution failure (P1)**
- Status: **Draft**; blocked by NE failure/retry/degraded-state and evaluation contracts.
- Requirement: https://github.com/project-openan/integration-test/issues/34
- Preconditions: cells F and S start at captured baseline; the simulator is configured to reject the contracted command for F with a fixed error and accept it for S; the expected bounded retry count and degraded terminal code are defined by the contract; no guardrail-protected cell is targeted.
- Steps:
  1. Submit one multi-cell intent for F and S and capture commands, retries, and terminal events.
  2. Wait with framework retry until the bounded failure handling terminates, then query both cells and the evaluation/context records.
  3. Remove the F fault injection and submit a fresh probe intent for F and S.
- Assertions:
  - Step 1: commands for F and S carry the same originating execution ID and F returns the injected error; the command count for F equals the contracted bounded attempt count, with no additional retry after termination.
  - Step 2: the terminal state is the contracted degraded code and identifies F, its action, and error; S state equals its successful command expectation while F remains at baseline; the evaluation/context records the same F failure; no other cell receives a command.
  - Step 3: the fresh probe reaches `complete`, both cells reach the probe's precomputed states, and no injected error occurs, proving recovery independent of cleanup.
- finally/Cleanup: in `finally`, clear fault injection even after assertion failure, terminate test executions, and restore all NE and tariff state. Assert the simulator accepts a health probe, F/S and all metrics equal baseline, and no test execution remains active; cleanup failure fails the case.
- Automation: `e2e/system-integration/intent-energy-saving/test_intent_energy_saving.py::test_ne_command_failure_bounds_retries_and_recovers` (planned after contract confirmation).

**007 - Explicit restoration and state consistency (P2)**
- Steps: apply sleep actions; issue the explicit restoration path (wake commands per contract); query NE state and orchestration execution records.
- Assertions: all cells return to baseline state; NE simulator state and orchestration-side records agree on final state per cell (no divergence); restoration commands appear in the command log with correct ordering; a second restoration is idempotent (no error, no state change).
- finally/Cleanup: restore all fixtures and assert NE, orchestration records, and tariff state return to baseline.

**008 - Multi-cell / concurrent intents (P2)**
- Steps: submit one multi-cell intent and a second independent intent concurrently (or two overlapping multi-cell intents per fixture design).
- Assertions: per-cell final states match each intent's precomputed expectation; command logs attributable to correct intent/execution IDs; no cross-contamination of decisions or evaluations; results identical to sequential runs.
- finally/Cleanup: terminate both executions, restore all fixtures, and assert every cell and tariff setting equals baseline.

## 6. Assertion and Evidence Rules

- Deterministic assertions only: stage event types and ordering, cell/action identifiers, executed-vs-expected action set equality, NE simulator state queries, command-log timestamps and ordering, evaluation numeric consistency on fixture metrics, terminal states. **Never assert on LLM-generated text**;
- **No wall-clock dependence**: all time-related behavior is driven by the tariff fixture and recorded timestamps, never by the runner's local time (Framework §6.3 no-sleep rule extends to time-based waiting here);
- No `sleep`; framework wait/retry on terminal events and NE state convergence;
- No implicit case ordering; each case ID independently runnable (Framework §6.3);
- On failure preserve: full stage event trace, decision record, NE command log, NE state snapshot (actual vs expected), evaluation report, relevant Pod logs, K8s events into `EVIDENCE_DIR`;
- Teardown: restore NE baseline + tariff period + guardrail config, **assert restoration**, deregister test-owned cards (Framework §6.5 and §4 safety red lines).

## 7. Tags, Naming, and Code Layout

- Test file: `e2e/system-integration/intent-energy-saving/test_intent_energy_saving.py`;
- Test functions: `test_<action>_<expected_result>` (e.g., `test_submit_valley_intent_executes_precomputed_sleep_set`); optional class grouping `TestIntentEnergySaving`;
- Tags - all five dimensions (Framework §6.4):

| Dimension | Values for S3 |
| --- | --- |
| feature | `system-integration` |
| environment | `online` / `offline` as supported by the lab |
| components | `orchestration-center`, `registry-center`, `a2a-t-sdk`, `workflow-exec-engine`, `mockagent` (NE simulator and tariff source are test fixtures, not distribution components) |
| priority | `P0` / `P1` / `P2` per §5 matrix |
| execution | Ready cases only: `smoke` (001, 002 after promotion), `full` (each Ready case); all current cases are `excluded until ready` |

- Case table rows follow the fixed 16-column template; Module = `system-integration`; Component Deps as above; orchestration keys in Notes (`protocol_primitive` = Task-T; execution strategy notes the write-operation safety rules). Draft rows must not be emitted as executable automation or given smoke/full code labels.

## 8. Execution, CI Mapping, and Gates

| Trigger | S3 subset | Basis |
| --- | --- | --- |
| Daily build | smoke: Ready cases designated smoke; currently none | Framework §7.2 |
| RC-0 / RC-1 | full: all Ready cases; currently none | Framework §7.2, §4.3.2/§4.3.3 |
| Pre-release | all Ready S3 cases rerun on RC; currently none | Framework §7.2 |

- Draft cases 001-008 are excluded from current smoke/full selections, automation implementation, and every exit-gate denominator. With zero Ready cases, S3 readiness is **not evaluable** and must not be reported as passed; the smoke/full and exit gates remain blocked pending contract confirmation and explicit per-case promotion.
- Once any case becomes Ready, the SIT exit gate applies only to the Ready set: pass rate = 100%, no skips among selected Ready cases (Framework §8.3). Draft cases are neither passes, failures, nor skips and never increase the denominator;
- **Cleanup verification is part of the gate**: any case leaving NE state modified counts as failed even if its functional assertions passed;
- Defects: evidence-attached issues, P0 24h response / current-release fix, regression case after fix (Framework §9);
- Archive: plan `docs/plans/<YY>-<season>/`, report `docs/reports/<YY>-<season>/`, JUnit XML per Framework §7.1/§11.3.

## 9. Open Items (must be resolved before case implementation)

| # | Item | Owner | Impact |
| --- | --- | --- | --- |
| 1 | Energy-saving action vocabulary and NE simulator contract (command set: cell sleep/wake, carrier-level actions; state schema; metrics fields) | orchestration-center WG + Integration Testing WG | Blocks all execution assertions and the NE simulator implementation |
| 2 | Tariff period injection mechanism (controllable tariff clock / configurable source) and re-evaluation trigger (periodic vs event-driven) | Integration Testing WG | Blocks 004 and the no-wall-clock rule implementation |
| 3 | Experience guardrail contract (threshold semantics, enforcing party: decision agent vs vendor agent, exclusion-reason field) | case contributor + orchestration-center WG | Blocks 003 assertions |
| 4 | Effect evaluation contract (metric set, baseline definition, degradation signal, corrective feedback trigger and target) | orchestration-center WG | Blocks 005 assertions |
| 5 | Whether execution authorization (Authorization-T) applies to NE writes in this scenario; if yes, the business gate contract | a2a-t-sdk + orchestration-center WG | Determines whether an authorization-denial case is added to the matrix |
| 6 | Real-LLM variant inclusion in RC runs (deterministic assertions only) | Integration Testing WG | Optional variant; default CI stays `USE_MOCK_LLM=true` |
