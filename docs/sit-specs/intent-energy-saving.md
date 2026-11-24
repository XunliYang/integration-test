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

| Case ID | Name | Variant coverage | Priority | Execution |
| --- | --- | --- | --- | --- |
| `[SIT-intent-energy-saving-001]` | Five-stage closed loop completes in valley period | full loop, single cell | P0 | smoke, full |
| `[SIT-intent-energy-saving-002]` | Cost-first decision correctness against tariff schedule | decision quality (precomputed expectation) | P0 | smoke, full |
| `[SIT-intent-energy-saving-003]` | Experience guardrail blocks forbidden action on high-load cell | guardrail variant | P1 | full |
| `[SIT-intent-energy-saving-004]` | Tariff period switch drives adapted actions | valley -> peak transition | P1 | full |
| `[SIT-intent-energy-saving-005]` | Effect evaluation compares baseline and feeds back | evaluation / feedback stage | P1 | full |
| `[SIT-intent-energy-saving-006]` | NE execution failure: defined degraded state, no inconsistent NE state | fault injection | P1 | full |
| `[SIT-intent-energy-saving-007]` | Explicit restoration path and state consistency | rollback / write safety | P2 | full |
| `[SIT-intent-energy-saving-008]` | Multi-cell / concurrent intent scheduling isolation | concurrency | P2 | full |

P0/P1 cases must be `Automatable=Yes` with Requirement Link filled (scenario epic issue).

### 5.1 Case definitions (preconditions / steps / assertions / cleanup)

**001 - Five-stage closed loop (P0)**
- Preconditions: RC centers deployed; energy-saving agent + vendor wireless agent registered; NE simulator at baseline with one low-load cell; tariff fixture set to valley period; `USE_MOCK_LLM=true`.
- Steps: (1) submit the cost-optimization intent; (2) observe perception, decision, scheduling, execution, evaluation stages via SDK/SSE events; (3) wait for loop terminal state with framework wait/retry.
- Assertions: all five stages produced their stage events in order (perception data collected -> decision recorded -> scheduling task issued -> NE command executed -> evaluation produced); NE simulator state shows the decided sleep action applied to the target cell; evaluation report structure present with baseline and post-execution metric fields; loop reaches terminal `complete` state.
- Cleanup: restore NE baseline and assert restoration; reset tariff period.

**002 - Cost-first decision correctness (P0)**
- Preconditions: designed fixture - tariff schedule and cell loads such that the cost-optimal action set is precomputed (e.g., sleep cell X in valley, keep cell Y active; a naive energy-only policy would choose differently).
- Steps: submit intent; capture the decided and executed action set.
- Assertions: executed action set **equals the precomputed cost-optimal set** (cell identifiers + action types, exact match); decision record references the tariff period in effect; no action outside the vocabulary; the distinguishing cell (where cost-first and energy-only policies diverge) received the cost-first action.

**003 - Experience guardrail (P1)**
- Preconditions: tariff in valley (sleep economically attractive); target cell load above the guardrail threshold.
- Steps: submit intent covering the high-load cell.
- Assertions: no sleep/shutdown command issued to the protected cell (NE command log absence assertion); decision record contains the guardrail constraint as the exclusion reason (structured field, not text match); other eligible cells still acted upon; guardrail config unchanged after the run.

**004 - Tariff period switch (P1)**
- Steps: start in valley with sleep actions applied; switch the tariff fixture to peak; trigger re-evaluation per product contract (periodic or event-driven - §9 item 2).
- Assertions: new decision adapts to peak (wake actions for cells whose sleep is no longer cost-optimal, per precomputed expectation); no stale-period actions executed after the switch (command timestamps vs switch marker); NE state converges to the peak-optimal state; transition produces evaluation records for both periods.

**005 - Effect evaluation and feedback (P1)**
- Steps: run the loop to execution; feed post-execution metrics via the NE simulator (including a designed experience-degradation signal, e.g., load rise on a sleeping cell's neighbor).
- Assertions: evaluation report computes deltas from the fixture baseline (numeric consistency: delta = post - baseline on the fixture-provided metrics); degradation signal triggers the defined corrective feedback (corrective task event present, targeting the affected cell per contract §9 item 4); evaluation is linked to the originating intent/execution ID.

**006 - NE execution failure (P1)**
- Preconditions: NE simulator configured to reject/fail the command for one target cell (test-controlled fault injection).
- Steps: submit multi-cell intent; observe.
- Assertions: loop reaches a defined degraded terminal state identifying the failed cell/action; successful cells' state is consistent with their executed commands (no partial/inconsistent NE state); failure recorded in evaluation/context; no infinite retry (bounded per contract); no forbidden action on guardrail-protected cells during failure handling.
- Cleanup: clear fault injection; restore NE baseline and assert restoration.

**007 - Explicit restoration and state consistency (P2)**
- Steps: apply sleep actions; issue the explicit restoration path (wake commands per contract); query NE state and orchestration execution records.
- Assertions: all cells return to baseline state; NE simulator state and orchestration-side records agree on final state per cell (no divergence); restoration commands appear in the command log with correct ordering; a second restoration is idempotent (no error, no state change).

**008 - Multi-cell / concurrent intents (P2)**
- Steps: submit one multi-cell intent and a second independent intent concurrently (or two overlapping multi-cell intents per fixture design).
- Assertions: per-cell final states match each intent's precomputed expectation; command logs attributable to correct intent/execution IDs; no cross-contamination of decisions or evaluations; results identical to sequential runs.

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
| execution | `smoke` (001, 002), `full` (all) |

- Case table rows follow the fixed 16-column template; Module = `system-integration`; Component Deps as above; orchestration keys in Notes (`protocol_primitive` = Task-T; execution strategy notes the write-operation safety rules).

## 8. Execution, CI Mapping, and Gates

| Trigger | S3 subset | Basis |
| --- | --- | --- |
| Daily build | smoke: 001, 002 | Framework §7.2 |
| RC-0 / RC-1 | full: 001-008 | Framework §7.2, §4.3.2/§4.3.3 |
| Pre-release | all S3 cases rerun on RC | Framework §7.2 |

- SIT exit gate: S3 pass rate = 100%, no skips (Framework §8.3);
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