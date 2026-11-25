# OpenAN System Integration Test Plan

> Version: v0.1 | Date: 2026-11-25 | Author: Junjie Huang | Review status: Pending review
> Related feature proposal: [integration-test#34](https://github.com/project-openan/integration-test/issues/34) | Version milestone: `26-winter`
> Archive path: `docs/plans/26-winter/`

---

## 1. Overview

### 1.1 Purpose

This plan defines the release-level System Integration Testing (SIT) scope for the OpenAN `26-winter` release. It verifies five end-to-end application scenarios across Registry Center, Orchestration Center, the workflow execution engine, A2A-T SDKs, sample agents, and external-system stubs on a real deployment.

The detailed scenario inventory is in [../../sit-scenarios.md](../../sit-scenarios.md). The five scenario specifications linked below are the design source for the 42 rows in [testcases-system-integration.csv](testcases-system-integration.csv).

### 1.2 Scope

**In scope**:

- Multi-feature closed loops: intent intake, workflow handling, agent discovery, A2A-T collaboration, result write-back, and terminal state;
- Fixed-workflow and dynamically negotiated complaint handling;
- Read-only diagnosis and explicitly authorized optimization/restoration paths;
- Cross-tier, cross-city, and multi-vendor collaboration represented by real network calls and test-controlled collaborators;
- Deterministic functional and exception assertions, fixture isolation, and environment restoration.

**Out of scope**:

- Single-module behavior owned by component UT or FIT;
- A2A-T protocol conformance and cross-language transport equivalence owned by the specialized protocol plan;
- Pure UI layout and styling;
- Performance, capacity, 7x24h stability, security, and compatibility benchmarks owned by their specialized plans;
- Contracts listed as open items until the responsible WG confirms them.

### 1.3 References

| Document | Link/Path |
|------|----------|
| SIT tracking issue | [integration-test#34](https://github.com/project-openan/integration-test/issues/34) |
| OpenAN Integration Testing Process and Framework | `docs/OpenAN Integration Testing Process and Framework.md` |
| SIT scenario inventory | `docs/sit-scenarios.md` |
| S1 specification | `docs/sit-specs/complaint-handling.md` |
| S2 specification | `docs/sit-specs/cross-domain-complaint.md` |
| S3 specification | `docs/sit-specs/intent-energy-saving.md` |
| S4 specification | `docs/sit-specs/spn-line-diagnosis.md` |
| S5 specification | `docs/sit-specs/spn-line-full-process.md` |
| Case-table field rules | `docs/templates/testcases-template-fields.md` |
| Best-practice sources | https://openan.dev/best-practices.html |

## 2. Objects Under Test

| Component | Repository / package | Version/Build | Test Layer | Notes |
|------|------|----------|----------|------|
| Registry Center | `registry-center` | RC image selected by `IMAGE_REGISTRY` / `IMAGE_TAG` | SIT | AgentCard registration and discovery |
| Orchestration Center | `orchestration-center` | Same RC build | SIT | Workflow recall/composition and execution events |
| Workflow execution engine | `workflow-exec-engine` | Version constrained by the RC component | SIT dependency | Host-agent workflow execution |
| A2A-T SDK | `a2a-t-sdk-python` / `a2a-t-sdk-java` | Version constrained by the RC component | SIT dependency | Business-loop Task-T / Negotiation-T / Authorization-T / Notification-T behavior |
| Sample Agents | `orchestration-center/samples`, `openan-demo/mockagent` | Same RC scenario package | SIT dependency | Deterministic domain-agent collaborators |
| External-system stubs | Test-owned NOC, EOMS, OMC, and network-element fixtures | Test implementation version | SIT dependency | Controlled contracts and evidence capture; no production writes |
| Installation & Deployment | `openan-installation` | RC deployment artifact | SIT dependency | Online Helm or Offline Compose as supported by the lab |

Only components participating in a case are declared in that row's `Component Deps`. A component being deployed but not participating is not sufficient reason to add its code label.

## 3. Test Strategy

### 3.1 Test Layers

| Layer | Executor | Scope |
|------|--------|------|
| FIT | Feature WG | Feature-level integration correctness and module contracts |
| SIT | Integration Testing WG | The five cross-feature business closed loops in this plan |

### 3.2 Test Types

- [x] Functional testing: business status, component identifiers, structured results, and event chains;
- [x] Exception testing: unavailable agents, rejected negotiation, failed writes, and degraded terminal states;
- [ ] Protocol conformance testing: covered by the specialized A2A-T protocol plan;
- [ ] Performance, stress, stability, security, compatibility, and deployment benchmarking: covered by specialized plans.

### 3.3 Test Method

- Execute Ready cases on a real Kubernetes cluster or supported Compose environment; do not replace the services under test with in-process mocks;
- Use sample agents and test-owned stubs only for external collaborators and controlled fault injection;
- Use mock LLM mode for deterministic CI; optional real-LLM runs assert identifiers, structure, status, and state rather than generated wording;
- Use bounded framework waits and event-driven synchronization, never `sleep`;
- Isolate mutable fixtures per case and restore all test-controlled state in `finally`/teardown;
- Preserve event traces, execution records, logs, and Kubernetes evidence in `EVIDENCE_DIR` on failure.

### 3.4 Automation and Readiness Strategy

- Every P0/P1 row has `Automatable=Yes` as its final automation requirement and a planned test-function mapping in the scenario specification;
- `status:ready` means the requirement link, contract, fixture, deterministic expected result, cleanup, and automation mapping are sufficiently defined for implementation;
- `status:draft` means a named open item blocks implementation. Draft rows are design inventory only: they are excluded from current smoke/full selection and current pass-rate denominators;
- A Draft row becomes Ready only after its blocking contract is linked or resolved and the matrix, specification, and CSV are updated together;
- Ready P0/P1 cases require 100% automation and repeatability. Final SIT exit cannot claim complete scenario coverage while release-required cases remain Draft; any scope change requires Integration Testing WG approval and an update to the plan and tracking issue.

## 4. Test Scenarios

| Scenario ID | Scenario Description | Components | Case Count | Priority Distribution | Specification |
|---------|---------|----------|------------|-----------------------|---------------|
| S1 | Broadband complaint: fixed workflow, discovery, multi-agent diagnosis, closure or expert handoff | orchestration-center; registry-center; workflow-exec-engine; a2a-t-sdk; mockagent | 8 | P0 2 / P1 4 / P2 2 | [S1](../../sit-specs/complaint-handling.md) |
| S2 | Mobile cross-domain complaint: group-province collaboration, negotiation, diagnosis, write-back | orchestration-center; registry-center; workflow-exec-engine; a2a-t-sdk; mockagent | 8 | P0 2 / P1 4 / P2 2 | [S2](../../sit-specs/cross-domain-complaint.md) |
| S3 | Intent-driven energy-cost optimization with guardrails and effect evaluation | orchestration-center; registry-center; a2a-t-sdk; mockagent | 8 | P0 2 / P1 4 / P2 2 | [S3](../../sit-specs/intent-energy-saving.md) |
| S4 | Single-city SPN diagnosis through direct or orchestration-driven integration | registry-center; a2a-t-sdk; workflow-exec-engine; mockagent; orchestration-center only where used | 8 | P0 2 / P1 4 / P2 2 | [S4](../../sit-specs/spn-line-diagnosis.md) |
| S5 | Cross-city SPN diagnosis, authorized restoration, verification, notification, and closure | orchestration-center; registry-center; workflow-exec-engine; a2a-t-sdk; mockagent | 10 | P0 2 / P1 7 / P2 1 | [S5](../../sit-specs/spn-line-full-process.md) |

The case-level `Status` and `Execution` columns in each specification are authoritative for current execution selection. The CSV carries the same state as `status:ready` or `status:draft` in Notes.

## 5. Test Case Design

### 5.1 Numbering Rules

- Case IDs follow `[SIT-<scenario>-<number>]` and are globally unique;
- S1 continues from the existing `[SIT-complaint-handling-001]` template example without renumbering;
- This plan contains 42 cases: P0 10 / P1 23 / P2 9.

### 5.2 Priority Definitions

| Priority | Definition | Ready-case Pass Requirement |
|--------|------|---------------------------|
| P0 | Core closed-loop path | 100% |
| P1 | Major functionality and defined degradation | 100% |
| P2 | General variants | At least 80% for intermediate execution; final SIT exit follows Framework §8.3 |

Draft cases are not converted into passes, skips, or executable failures; they remain outside current execution denominators until Ready.

### 5.3 Label Dimensions

Every automated case carries `feature=system-integration`, `environment`, case-derived `components`, `priority`, `execution=smoke|full|slow`, the milestone, and the Case ID. Draft cases receive no current smoke/full label until they become Ready.

### 5.4 Case Table

The 16-column case table is archived at `docs/plans/26-winter/testcases-system-integration.csv`. Its header is verbatim from the repository template; no status column is added. Readiness and orchestration metadata are carried in Notes as semicolon-separated `key:value` entries.

Every P0/P1 row links to [integration-test#34](https://github.com/project-openan/integration-test/issues/34) as the SIT scenario epic. Component requirement issues may be added alongside it when a more specific approved requirement exists.

### 5.5 Case Design Requirements

- Every P0/P1 case has independent preconditions, numbered steps, deterministic assertions, cleanup/recovery, and a planned test-function mapping;
- No case relies on “same as” another case for required execution content;
- Different fault modes are separate cases or explicitly parameterized runs with independent setup, assertions, and teardown;
- Parallel behavior uses controlled synchronization or structural assertions, never timing assumptions based on agent speed;
- Each case is independently runnable and leaves no orphaned task, workflow, registration, authorization, ticket, or stub state.

## 6. Test Environment and Data

### 6.1 Environment Topology

| Item | Value |
|----|------|
| Deployment mode | Online Helm or Offline Compose, according to the scenario and supported lab mode |
| Environment provider | Integration Testing WG |
| Build under test | RC artifact identified by `IMAGE_REGISTRY` and `IMAGE_TAG` |
| Network path | Real cross-service and cross-tier network calls; no in-process substitution |
| Evidence | JUnit XML plus traces, logs, and cluster events archived per run |

### 6.2 Dependent Services

| Dependency | Configuration | Notes |
|------|------|------|
| LLM | Existing model configuration or `USE_MOCK_LLM=true` | Mock mode is the deterministic default |
| Registry identity | Existing mTLS certificate variables | Secrets remain external to the repository |
| Sample agents | `MOCK_AGENTS_HOST` / `SAMPLE_AGENTS_HOST` | Scenario payloads are versioned test fixtures |
| External-system stubs | Existing endpoint injection or a future reviewed variable | NOC/EOMS/OMC/NE contracts remain Draft where unresolved |

### 6.3 Test Data

- Signed AgentCards and organization ownership fixtures;
- Fixed workflow definitions and complaint intents;
- Domain-specific fault evidence and expected structured classifications;
- Tariff schedules, guardrails, precomputed decision results, and simulated network-element state;
- SPN line data, authorization decisions, restoration outcomes, and performance samples;
- Test-controlled synchronization barriers for parallel diagnosis.

### 6.4 Environment Variables

This documentation-only change introduces no variable consumed by test code and therefore does not change `e2e/.env.template`. Candidate variables mentioned in scenario Open Items are not an active environment contract. The automation PR that consumes a new variable must add it to `e2e/.env.template` and the README in the same change, without committing credentials, addresses, or tokens.

## 7. Entry and Exit Criteria

| Gate | Criteria | Source |
|------|----------|--------|
| Design entry | Scenario inventory, specification, CSV row, requirement link, and readiness state are aligned | This plan |
| Automation entry for a case | `status:ready`; contracts and fixtures confirmed; deterministic assertions and cleanup defined | This plan §3.4 |
| Current smoke/full execution | Select Ready rows only; Draft rows are excluded explicitly, not skipped at runtime | Framework §7.2 and this plan |
| Current Ready-case gate | Ready P0/P1 pass rate 100%; no missing assertions or unmanaged mutable state | Framework §8.3 |
| Final SIT exit / release entry | Framework §8.3 requirements pass; all release-required cases are Ready and executed, or an approved scope change is recorded in #34 | Framework §8.3 |

## 8. Defect Management

- Failed executed cases open issues with Case ID, build, environment, event trace, logs, and fixture state attached;
- Severity and response follow Framework §9.1;
- A fix adds or updates a regression case and reruns the affected scenario;
- An unresolved design contract is tracked as an Open Item, not misreported as a product test failure.

## 9. Schedule and Responsibilities

| Milestone | Date / Window | Owner | Deliverable |
|------|--------|--------|--------|
| Test plan and case-table review | Before RC execution | Integration Testing WG | Reviewed plan and 16-column CSV |
| Open-contract resolution | Before affected case implementation | Responsible component WG | Contract linked to the scenario Open Item |
| RC-0 SIT execution | 2026-10-30 through 2026-11-25, per #34 | Integration Testing WG | Ready-case results and defect evidence |
| RC-1 regression | 2026-11-25 through 2026-12-16, per #34 | Integration Testing WG | Required regression and final readiness disposition |
| SIT report | After RC-1 execution | Integration Testing WG | `docs/reports/26-winter/` report and exit conclusion |

Development ownership in the CSV is assigned to the participating OpenAN Component WGs; test design and execution ownership is the Integration Testing WG. Individual owners must be recorded in the execution report when assigned.

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Open interface or state contracts | Case cannot be implemented deterministically | Keep the row Draft, name the blocker, and resolve it before automation |
| LLM instability | Flaky routing or diagnosis assertions | Use mock mode and assert identifiers, structures, and states |
| Timing-sensitive parallel assertions | False failures on valid schedules | Use bounded test-controlled barriers or structural parallel-flow assertions |
| Fault injection leaves mutated state | Subsequent cases fail or production-like data is damaged | Use test-owned fixtures, `finally` restoration, and post-teardown health checks |
| Incorrect component labels | Wrong environment provisioning or test selection | Derive labels from each CSV row's actual Component Deps |
| Draft rows silently reduce release coverage | False SIT exit conclusion | Report Ready/Draft counts and require explicit WG-approved scope disposition |

## 11. Deliverables and Archive

| Deliverable | Archive Path |
|--------|---------|
| Scenario inventory | `docs/sit-scenarios.md` |
| Scenario specifications | `docs/sit-specs/` |
| Test plan | `docs/plans/26-winter/system-integration-test-plan.md` |
| Case table | `docs/plans/26-winter/testcases-system-integration.csv` |
| Automated test code | `e2e/system-integration/<scenario>/` (separate automation PR) |
| Test report | `docs/reports/26-winter/` (separate execution/report PR) |

## Appendix

- Test Checklist: `docs/openan-test-checklist.md`
- Framework: `docs/OpenAN Integration Testing Process and Framework.md`
- Tracking issue: https://github.com/project-openan/integration-test/issues/34
