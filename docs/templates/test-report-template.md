# <Feature/Version> Test Report

> Version: vX.Y | Date: YYYY-MM-DD | Prepared by: <Test Owner> | Review status: Pending review
> Related test plan: [docs/plans/<version>/test-plan-<feature>.md](<link>) | Version milestone: `<YY>-<season>` (e.g., `26-winter`)
> Archive path: `docs/reports/<version>/` (merged via PR after passing Integration Testing WG review)

---

## 1. Test Overview

### 1.1 Test Objects and Versions

| Component | Repository | Version under test (tag/image digest) | Notes |
|------|------|---------------------------|------|
| Registry Center | `registry-center` | <tag / digest> | |
| Orchestration Center | `orchestration-center` | <tag / digest> | |
| A2A-T SDK | `a2a-t-sdk-python` / `a2a-t-sdk-java` | <version> | |
| Portal | `openan-portal` | <tag> | |
| Installation & Deployment | `openan-installation` | <tag> | |

### 1.2 Test Scope

Reference the test plan scope; if actual execution deviates from the plan, explain item by item (including the reasons and impact of any trimming).

### 1.3 Test Environment

| Item | Value |
|----|------|
| Deployment mode | Online Helm / Offline Compose |
| K8s / Helm version | <version> |
| Cluster size | <node count/spec> |
| LLM dependency | Real endpoint: <provider/model> / mock |
| External database | <MySQL/PostgreSQL version> |
| Sample agents | <openan-demo mockagent scenario package> |

### 1.4 Execution Period and Personnel

| Item | Content |
|----|------|
| Execution period | YYYY-MM-DD ~ YYYY-MM-DD |
| Executor | <Name> |
| Test owner | <Name> |

---

## 2. Case Execution Results

### 2.1 Overall Data

| Metric | Value | Target | Met |
|------|------|------|---------|
| Number of planned cases | | — | — |
| Case execution rate | | =100% | |
| Case pass rate (overall) | | FIT ≥95% | |
| P0 pass rate | | =100% | |
| P1 pass rate | | =100% | |
| P2 pass rate | | ≥80% | |
| Failed case archiving rate (issue + `skip-temporarily`) | | =100% | |

### 2.2 Layered Results

| Layer | Executed | Passed | Pass rate | Notes |
|------|--------|------|--------|------|
| FIT | | | | |
| SIT | | | | 100% required, no skips |
| A2A-T protocol conformance | | | | Dual transport + cross-language SDKs |
| Deployment modes (install/upgrade/rollback) | | | | Online Helm / Offline Compose |

### 2.3 Automation and Execution Layer Statistics

| Metric | Value |
|------|------|
| Automation rate (P0/P1 require 100%) | |
| Number of smoke / full / slow cases | |
| Number of cases marked `skip-temporarily` (each must reference an issue) | |

### 2.4 Failed Case List

| Case ID | Priority | Failure symptom | Related issue | Status | Evidence (trace/log/screenshot links) |
|----------|--------|---------|-----------|------|------------------------------|
| [FIT-...-xxx] | | | | skip-temporarily / fixed | |

---

## 3. Defect Statistics

### 3.1 Defect Overview

| Severity | New | Closed | Remaining | SLA compliance (Framework §9.1) |
|--------|------|--------|------|--------------------------|
| P0 | | All must be closed | | 24h response / fix in current release |
| P1 | | Closed or with workaround | | 3 business days |
| P2 | | | | Next release |
| P3 | | | | Scheduled as needed |

### 3.2 Remaining Defects and Risks

| Issue | Severity | Impact | Workaround | Risk acceptor | Latest fix version |
|-------|--------|------|---------|-----------|-------------|
| | | | | | |

### 3.3 Defect Trend (optional)

<Defect discovery/closure trend chart or reopen rate data>

---

## 4. Non-Functional Test Results

### 4.1 Performance

| Key interface/scenario | P50 | P95 | P99 | Baseline (previous version) | This run | Conclusion |
|--------------|-----|-----|-----|----------------|------|------|
| AgentCard registration | | | | | | |
| AgentCard query/semantic search | | | | | | |
| Workflow execution | | | | | | |
| A2A-T negotiation | | | | | | |

### 4.2 Stress and Capacity

| Scenario | Capacity metric | Result | Conclusion |
|------|---------|------|------|
| <concurrent workflows / large-scale agent registration> | | | |

### 4.3 Long-Duration Stability (7×24h)

| Metric | Result | Threshold | Conclusion |
|------|------|------|------|
| P0/P1 failure count | | 0 | |
| Memory/handle growth | | See the specialized test plan | |
| Performance degradation | | See the specialized test plan | |

### 4.4 Reliability and Fault Injection

| Fault scenario | Expected behavior | Actual result | Conclusion |
|---------|---------|---------|------|
| Network failure | Graceful degradation/auto-recovery | | |
| LLM unavailable | Clear error code, no partial output | | |
| Dependent service failure | Degradation per design, state consistent after recovery | | |

### 4.5 A2A-T Protocol Conformance and Interoperability

| Item | Result | Conclusion |
|----|------|------|
| Task-T/Negotiation-T/Notification-T/Authorization-T four message types: dual-transport consistency between JSON-RPC and HTTP+REST | | |
| Python SDK ↔ Java SDK interoperability | | |
| Protocol version compatibility (e.g., v1.0/v1.1) | | |

### 4.6 Security

| Item | Result | Conclusion |
|----|------|------|
| Vulnerability scanning (requirement: no Critical; every High has a fix plan + risk acceptance) | | |
| mTLS / JWS validation (including jku allowlist fail-closed) | | |
| Authorization-T authorization verification | | |
| Content security (prompt injection filtering) | | |

### 4.7 Compatibility

| Dimension | Coverage result | Conclusion |
|------|---------|------|
| K8s version × OS × database backend × browser | Per the specialized test plan matrix | |

---

## 5. Coverage and Requirement Traceability

| Metric | Value | Target | Met |
|------|------|------|---------|
| Requirement coverage (approved requirements with corresponding executed cases) | | 100% | |
| Integration test API coverage (counted by OpenAPI paths) | | ≥80% | |
| Module UT line coverage | | ≥70% (core ≥80%), no downward trend | |

---

## 6. Quality Metrics Summary (Release Decision Input)

| Metric | Value | Notes |
|--------|------|------|
| Case execution rate / pass rate (overall, P0, P1) | | |
| Defect density | | Defects / code size or function points |
| Remaining defects (by severity) | | |
| Automation rate | | |
| Flaky rate (inconsistency ratio on case reruns) | | |
| Coverage | | See Section 5 |

---

## 7. Conclusions and Recommendations

- [ ] Meets FIT exit criteria (Framework §8.2)
- [ ] Meets SIT exit / release entry criteria (Framework §8.3)
- [ ] Conditional pass (conditions and remaining items: ______; risk acceptor: ______; latest closure version: ______)

**Conclusions and recommendations**: <input recommendations for the Go / No-Go decision>

---

## 8. Review Record

| Item | Content |
|----|------|
| Review date | YYYY-MM-DD |
| Attendees | <Integration Testing WG / Feature WG> |
| Sign-off | |
| Review comments | |

---

## Appendix

- Evidence links: Allure report <link>, CI pipeline <link>, test plan <link>, case CSV <link>
- References: [Test Checklist](../../docs/openan-test-checklist.md), [Framework document](../../docs/OpenAN Integration Testing Process and Framework.md)
