# <Feature Name> Test Plan

> Version: vX.Y | Date: YYYY-MM-DD | Author: <Name> | Review status: Pending review
> Related feature proposal: <link> | Version milestone: `<YY>-<season>` (e.g., `26-winter`)
> Archive path: `docs/plans/<version>/` (merged via PR after review approval)

---

## 1. Overview

### 1.1 Purpose

<State which feature/version this plan targets and what goals it verifies. Example: verify that registry-center integrates correctly with other components in this release and meets the Feature Integration Test (FIT) entry and exit quality requirements.>

### 1.2 Scope

**In scope** (aligned with the integration testing boundaries in Framework §5.2):

- Cross-module API calls, cross-service data flows, event trigger chains
- Installation/upgrade/rollback paths
- Multi-feature combined usage (e.g., Registry Center + Orchestration Center + sample agents)
- End-user critical paths on a real Kubernetes cluster or virtual machines

**Out of scope**:

- Boundary conditions of individual functions (module repository UT)
- Pure UI layout and styling (frontend manual/UI automation)
- Large-scale performance benchmarks (specialized performance testing; see the specialized test plan)

### 1.3 References

| Document | Link/Path |
|------|----------|
| OpenAN Integration Testing Process and Framework | `docs/OpenAN Integration Testing Process and Framework.md` |
| Feature proposal | <link> |
| Component API documentation | Registry Center API Reference / Orchestration Center API Reference |
| Deployment contract | `openan-installation/containerized/TRANSPORT_DEPLOYMENT.md` |
| Compatibility matrix | <specialized test plan link> |

---

## 2. Objects Under Test

| Component | Repository | Version/Build | Test Layer | Notes |
|------|------|----------|----------|------|
| Registry Center | `registry-center` | <tag/image digest> | FIT | AgentCard registration/query/heartbeat/change broadcast |
| Orchestration Center | `orchestration-center` | <tag/image digest> | FIT | Workflow orchestration, PSOP generation, execution, SSE events |
| A2A-T SDK | `a2a-t-sdk-python` / `a2a-t-sdk-java` | <version> | UT (module repository) + FIT (interoperability) | JSON-RPC / HTTP+REST dual transport |
| Workflow Engine SDK | `workflow-engine-sdk-java` / `workflow-engine-sdk-python` | <version> | UT (module repository) | Host Agent execution engine |
| Portal | `openan-portal` | <tag> | UI testing | Showroom/Playground |
| Installation & Deployment | `openan-installation` | <tag> | Deployment testing | Online Helm / Offline Compose |
| Sample Agents | `openan-demo` | <tag> | FIT dependency | mockagent scenario package |

---

## 3. Test Strategy

### 3.1 Test Layers

| Layer | Executor | Scope |
|------|--------|------|
| FIT | Feature WG | Integration correctness of multiple modules/services within this feature |
| SIT | Integration Testing WG | Release-level multi-feature combinations, end-to-end closed-loop scenarios |

### 3.2 Test Types

Aligned with Framework §10; check as needed for the feature:

- [ ] Functional testing (API integration, event chains)
- [ ] Exception testing (network faults, dependency faults, degradation when the LLM is unavailable)
- [ ] A2A-T protocol testing (protocol conformance, prompt contracts, interoperability: cross-language SDKs interoperating with the A2A base protocol)
- [ ] Performance testing (key interface P99: AgentCard registration/query, workflow execution, A2A-T negotiation)
- [ ] Stress/capacity testing
- [ ] Long-duration stability testing (7×24h)
- [ ] Reliability/fault injection
- [ ] Security testing (mTLS, JWS validation, Authorization-T, prompt injection filtering, vulnerability scanning)
- [ ] Compatibility testing (K8s version × OS × database backend × browser)
- [ ] Deployment mode testing (Online Helm / Offline Compose; upgrade/rollback)

### 3.3 Test Method

- Real-environment execution: FIT runs on a real K8s cluster/VMs; services under test are not mocked at the integration layer
- LLM dependency handling: choose either an external LLM endpoint (models.yaml + key injection) or a mock LLM; **cases depending on LLM output use deterministic assertions** (assert structure/status codes/flow states, never directly asserting model-generated text)
- Sample agents: use `openan-demo/mockagent` or Orchestration Center samples as collaborators
- Prohibitions: no sleep-based synchronization (use framework wait/retry); no sharing of mutable state between cases; no missing assertions (log-only)

### 3.4 Automation Strategy

- 100% of P0/P1 cases automated and repeatable
- `execution` label layering: `smoke` (PR gate) / `full` (Daily) / `slow` (long-duration stability)
- Failed cases automatically archived as issues with the scene preserved (trace/log/screenshots/Pod logs/K8s events)

---

## 4. Test Scenarios

| Scenario ID | Scenario Description | Components | Priority | Notes |
|---------|---------|----------|--------|------|
| SCN-<feature>-001 | <Example: intent input → Orchestration Center generates PSOP → Registry Center retrieves AgentCard → A2A-T negotiation → Host Agent execution → SSE event stream closed loop> | orchestration-center, registry-center, a2a-t-sdk, mockagent | P0 | End-to-end closed loop |
| SCN-<feature>-002 | <scenario description> | <components> | P1 | |
| ... | | | | |

---

## 5. Test Case Design

### 5.1 Numbering Rules

- FIT cases: `FIT-<feature>-<topic>-<number>`, e.g., `FIT-registry-center-agentcard-001`
- SIT cases: `SIT-<scenario>-<number>`, e.g., `SIT-complaint-handling-001`

### 5.2 Priority Definitions

| Priority | Definition | Pass Rate Requirement |
|--------|------|-----------|
| P0 | Scenarios that block installation/the core closed-loop path | 100% (TRR entry and release gate) |
| P1 | Major functionality impaired but with workarounds | 100% |
| P2 | General scenarios | ≥80% |

### 5.3 Label Dimensions

Every case must carry the full set of labels in code: `feature`, `environment`, `components`, `priority`, `execution` (`smoke`/`full`/`slow`), `skip` (temporary skips must reference an issue).

### 5.4 Case Table

Cases are carried in a 16-column CSV archived in the same directory as this plan: `docs/plans/<version>/testcases-<feature>.csv`. P0/P1 cases must have the requirement link (issue) filled in to support requirement coverage traceability. See [Test Case Table Field Description](testcases-template-fields.md) for field filling rules and [testcases-template.csv](testcases-template.csv) for the template.

### 5.5 Case Design Requirements

- Every case includes: preconditions, steps, assertions, and cleanup actions (teardown deletes all created resources)
- Cases must be independently repeatable; depending on execution order is prohibited (use explicit declarations when ordering is truly required)
- Session-level fixtures are limited to read-only configuration (e.g., LLM config, login state)

---

## 6. Test Environment and Data

### 6.1 Environment Topology

| Item | Value |
|----|------|
| Deployment mode | Online Helm (K8s cluster) / Offline Compose (single host), executed per the modes supported in this release |
| K8s/Helm version | <version; supported range per the specialized test plan> |
| Cluster size | <node count/spec> |
| Environment provider | Integration Testing WG |

### 6.2 Dependent Services

| Dependency | Configuration | Notes |
|------|---------|------|
| LLM endpoint | models.yaml + `.env` named keys, or `USE_MOCK_LLM=true` | Required by semantic search/intent generation |
| External database | MySQL/PostgreSQL (file/SQLite is dev mode) | Injected via deployment values |
| Image registry | `IMAGE_REGISTRY` | ghcr.io or an intranet image registry |

### 6.3 Test Data

- AgentCard samples (including signature/JWK configuration)
- PSOP workflow templates, SPG library samples
- Mock/sample agents (`openan-demo/mockagent`, Orchestration Center samples)

### 6.4 Environment Variables

See `e2e/.env.template` at the repository root; variables newly introduced by this plan must be synchronized to the template and documented in the README.

---

## 7. Entry and Exit Criteria

| Gate | Criteria | Source |
|------|------|------|
| TRR entry (into FIT) | P0/P1 pass rate = 100%, P2 ≥ 80%, UT coverage not decreasing, image deployable | Framework §8.1 |
| FIT exit | Overall pass rate ≥ 95%, failed cases archived as issue + `skip-temporarily`, performance not lower than the previous version baseline, report reviewed by the Integration Testing WG | Framework §8.2 |
| SIT exit / release entry | SIT pass rate = 100% with no skips, 7×24h without P0/P1 failures, install/upgrade/rollback all passed, no open P0 (P1 with workarounds), compatibility matrix passed | Framework §8.3 |

---

## 8. Defect Management

- Severity classification and SLA per Framework §9.1 (P0: 24h response / fix in current release; P1: 3 business days; P2: next release; P3: scheduled as needed)
- Failed cases automatically archived as issues with trace/log/screenshots/cluster info attached
- Fix PRs must add regression cases and rerun all FIT cases for the feature

---

## 9. Schedule and Responsibilities

| Milestone | Date | Owner | Deliverable |
|------|------|--------|--------|
| Test plan review approved | YYYY-MM-DD | <WG test owner> | This plan merged into `docs/plans/<version>/` |
| Case writing completed | YYYY-MM-DD | <Test owner> | Case CSV + automation code |
| TRR review | YYYY-MM-DD | <Feature WG Maintainer> | TRR conclusion (see Chapter 1 of the Test Checklist) |
| FIT completed / report review | YYYY-MM-DD | <Test owner> | Test report `docs/reports/<version>/` |

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|------|---------|
| External LLM instability causing case flakiness | Case pass rate fluctuation | Mock LLM/stub responses; deterministic assertions |
| Insufficient environment resources (real cluster) | Test delays | Apply to the Integration Testing WG in advance; reuse the community lab |
| Cross-language SDK interoperability differences | Negotiation/execution failures | Run A2A-T protocol conformance cases first |

---

## 11. Deliverables and Archive

| Deliverable | Archive Path |
|--------|---------|
| Test plan (this document) | `docs/plans/<version>/` |
| Case table CSV | `docs/plans/<version>/testcases-<feature>.csv` |
| Test code | `e2e/<feature>/` |
| Test report | `docs/reports/<version>/` (template: [test-report-template.md](test-report-template.md)) |

---

## Appendix

- Test Checklist: `../../docs/openan-test-checklist.md`
- Framework document: `../../docs/OpenAN Integration Testing Process and Framework.md`
