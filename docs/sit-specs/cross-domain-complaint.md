# SIT Specification S2: Mobile Cross-Domain Collaborative Complaint Handling

> *Version: v0.1 (Draft)*
> *Maintained by: OpenAN Integration Testing Working Group*
> *Language: English*
> *Scenario slug: `cross-domain-complaint` - Case IDs: `[SIT-cross-domain-complaint-<number>]`*
> *Scenario baseline: [sit-scenarios.md](../sit-scenarios.md) S2*
> *Governance baseline: [OpenAN Integration Testing Process and Framework](../OpenAN%20Integration%20Testing%20Process%20and%20Framework.md) (cited as "Framework" below)*

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

| Case ID | Name | Variant coverage | Priority | Execution |
| --- | --- | --- | --- | --- |
| `[SIT-cross-domain-complaint-001]` | Single-domain complaint E2E automated closure (wireless fault) | known issue, one domain, two tiers | P0 | smoke, full |
| `[SIT-cross-domain-complaint-002]` | Cross-domain joint fault location E2E closure (wireless + core network) | known issue, multi-domain negotiation | P0 | smoke, full |
| `[SIT-cross-domain-complaint-003]` | Novel problem handled by dynamic negotiation (no pre-coded workflow) | generalization variant | P1 | full |
| `[SIT-cross-domain-complaint-004]` | Group-province tiering: cross-tier registration, discovery and invocation | two-tier topology | P1 | full |
| `[SIT-cross-domain-complaint-005]` | Diagnosis write-back to process center with full context | closure / write-back | P1 | full |
| `[SIT-cross-domain-complaint-006]` | Domain agent unreachable or negotiation rejected: defined degraded terminal state | fault injection | P1 | full |
| `[SIT-cross-domain-complaint-007]` | Remaining domain combinations (SPN fault; wireless optimization) | domain coverage | P2 | full |
| `[SIT-cross-domain-complaint-008]` | Concurrent cross-domain complaints isolation | concurrency | P2 | full |

P0/P1 cases must be `Automatable=Yes` with Requirement Link filled (scenario epic issue).

### 5.1 Case definitions (preconditions / steps / assertions / cleanup)

**001 - Single-domain E2E closure (P0)**
- Preconditions: two tiers deployed and healthy; four domain agents + recognition agent registered; wireless fault scenario payload loaded; EOMS stub running; `USE_MOCK_LLM=true`.
- Steps: (1) submit a wireless-fault ticket via the intake stub; (2) observe recognition, discovery, negotiation and task execution via SDK events / SSE; (3) wait for terminal ticket state with framework wait/retry.
- Assertions: ticket reaches terminal closed state; the wireless fault domain agent was discovered via the group-tier registry and participated (agent identifier match); negotiation exchange occurred between recognition agent and domain agent (Negotiation-T events present, client/server states aligned at termination); diagnosis conclusion structure present in the write-back; no other domain agent was invoked.

**002 - Cross-domain joint fault location (P0)**
- Same structure with a joint wireless + core network ticket.
- Assertions: both domain agents participate; joint localization produces a single consolidated conclusion (required fields present, contributing domains identified); negotiation converges to a terminal state within the bounded round/timeout contract (§9 item 1); ticket closed; per-domain evidence retained in the conclusion context.

**003 - Novel problem, dynamic negotiation (P1)**
- Preconditions: no pre-coded workflow matches the ticket category (verified: workflow retrieval returns no match or is bypassed by the recognition agent).
- Steps: submit the novel-problem ticket; observe handling.
- Assertions: handling proceeds without a recalled fixed workflow (execution context shows negotiation-driven composition, workflow ID absent or marked dynamic); Negotiation-T exchanges occur and reach a terminal state; ticket reaches a defined terminal state (closed with conclusion, or explicit "cannot locate" outcome - never silent hang or false closure). Assertions are on identifiers, event types, and states, not on generated wording.

**004 - Group-province tiering (P1)**
- Steps: register province-owned agents into the group-tier registry; run a complaint; capture discovery and invocation paths.
- Assertions: registration and discovery cross the tier boundary over the real network path (registry audit / agent card org fields match province org); owner isolation holds (province org cannot read/modify group-owned cards beyond its permissions - negative probe); cross-tier invocation succeeds and task events carry correct agent identities; with the group tier briefly unreachable, the provincial side reports a defined error rather than silently falling back to stale local state (fault-injection probe, restore afterwards).

**005 - Write-back with full context (P1)**
- Steps: run a cross-domain complaint to closure; capture the EOMS stub receipt.
- Assertions: write-back happens exactly once per ticket; payload contains ticket ID, conclusion structure, contributing domains, and per-agent diagnostic history with timestamps; ticket state transition sequence at the stub is monotonic (intake -> processing -> closed), no duplicate or out-of-order transitions.

**006 - Unreachable / rejecting domain agent (P1)**
- Preconditions: test-controlled fault injection - core network agent endpoint unreachable, or configured to reject negotiation.
- Steps: submit the joint ticket; observe.
- Assertions: terminal state is a defined degraded/failed outcome identifying the failing domain; no false closure; remaining domain results are preserved in context; negotiation does not loop indefinitely (bounded by the round/timeout contract); after restoring the agent, a fresh ticket completes normally (recovery probe).
- Cleanup: restore agent; verify registry health state recovers.

**007 - Remaining domain combinations (P2)**
- Steps: run SPN-fault and wireless-optimization tickets (separately).
- Assertions: mirror 001 per domain; SPN participation here is complaint diagnosis only - no restoration/authorization actions occur (those belong to S5).

**008 - Concurrent complaints isolation (P2)**
- Steps: submit one single-domain and one cross-domain ticket concurrently.
- Assertions: independent terminal states; negotiation sessions, task IDs, and write-back payloads do not cross-contaminate (per-ticket identifier assertions); results identical to sequential runs.

## 6. Assertion and Evidence Rules

- Deterministic assertions only: ticket/ticket-state identifiers, agent/org identifiers, Negotiation-T and Task-T event types and state alignment, terminal states, required-field presence, write-back transition ordering. **Never assert on LLM-generated text**;
- Negotiation-specific: assert that negotiation **occurred and converged** (event presence + aligned terminal states + bounded rounds). Round limits and timeout values come from the contract in §9 item 1; until confirmed, use the SDK default bound and record it in the case Notes;
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
| execution | `smoke` (001, 002), `full` (all) |

- Case table rows follow the fixed 16-column template; Module = `system-integration`; Component Deps as above; orchestration keys (`language_profile`, `protocol_primitive`, `execution_strategy`, `environment`) in Notes. `protocol_primitive` includes Negotiation-T for this scenario.

## 8. Execution, CI Mapping, and Gates

| Trigger | S2 subset | Basis |
| --- | --- | --- |
| Daily build | smoke: 001, 002 | Framework §7.2 |
| RC-0 / RC-1 | full: 001-008 | Framework §7.2, §4.3.2/§4.3.3 |
| Pre-release | all S2 cases rerun on RC | Framework §7.2 |

- SIT exit gate: S2 pass rate = 100%, no skips (Framework §8.3);
- Defects: evidence-attached issues, P0 24h response / current-release fix, regression case after fix (Framework §9);
- Archive: plan `docs/plans/<YY>-<season>/`, report `docs/reports/<YY>-<season>/`, JUnit XML per Framework §7.1/§11.3.

## 9. Open Items (must be resolved before case implementation)

| # | Item | Owner | Impact |
| --- | --- | --- | --- |
| 1 | Negotiation convergence contract: max rounds / timeout, terminal state naming for converged / failed / rejected negotiation | a2a-t-sdk + orchestration-center WG | Blocks bounded-convergence assertions in 002/003/006 |
| 2 | EOMS process center write-back schema and ticket state machine (operator-specific in production; community stub contract) | Integration Testing WG + case contributor | Blocks 005 payload assertions |
| 3 | Two-tier lab mode: separate namespaces vs separate clusters; cross-tier network path and mTLS trust setup between tiers | Infra WG + Integration Testing WG | Blocks 004 and the environment section of all cases |
| 4 | Domain scenario payloads for wireless / core / SPN / optimization on the shipped sample agents (test data authoring, not new agents) | Integration Testing WG | Blocks 001/002/007 fixture content |
| 5 | Real-LLM variant inclusion in RC runs (deterministic assertions only) | Integration Testing WG | Optional variant; default CI stays `USE_MOCK_LLM=true` |