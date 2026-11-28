# OpenAN Installation Test Plan

> Version: v0.6 | Date: 2026-11-28 | Author: Installation WG test owner (TBD) | Review status: Pending review
> Related feature proposal: [openan-installation#2](https://github.com/project-openan/openan-installation/issues/2) · [#5](https://github.com/project-openan/openan-installation/issues/5) · [#9](https://github.com/project-openan/openan-installation/issues/9) · [#36](https://github.com/project-openan/openan-installation/issues/36) | Tracking issue: [integration-test#19](https://github.com/project-openan/integration-test/issues/19) | Version milestone: `26-winter`
> Archive path: `docs/plans/26-winter/`

---

## 1. Overview

### 1.1 Purpose

Verify that the system-level installation and deployment tooling (`openan-installation`) delivers all deployment modes committed for the 26-winter release and meets the Feature Integration Test (FIT) entry and exit quality requirements. This covers the five installation lines, the configuration matrix, the build tooling, and the non-functional (DFX) design capabilities of the installer.

### 1.2 Scope

**In scope** (aligned with the integration testing boundaries in Framework §5.2):

- Five installation lines: binary one-click (online), binary offline tarball, online Helm wizard, offline K8s bundle, offline compose stack
- Modular component selection (`--reg`, wizard selection, chart values)
- Configuration matrix: LLM configuration and validation, registry URL handling, unified `database.type` (bundled postgresql/mysql, external pass-through, compose `DATABASE_TYPE`), frontend type, non-interactive `--values` install, `--sample`, version pinning
- Build tooling: image build/tag/push to a custom local registry, offline bundle build from local source trees, binary offline bundle build (`pack.sh`)
- DFX dimensions of the installer: testability (probes, external state identification), diagnosability (check-env, precheck failures), serviceability (idempotent install, in-place upgrade, uninstall completeness, data retention), reliability (PVC persistence, storage fallback, port conflict, MetalLB auto-provision), performance (HPA scaling), security (TLS material, secret masking, exposure surface), compatibility (multi-arch, distro families)

**Out of scope** (excluded by the confirmed requirement boundary for this release):

- Package preparation (per-component repository CI/CD) — not implemented in the requirement
- Cross-version upgrade paths (issue #5 sections 3.1/3.2/3.3) — not implemented in the requirement
- Module-internal unit tests (module repositories)
- Large-scale performance benchmarks and 7×24h stability runs (specialized testing; see the specialized test plan)

### 1.3 References

| Document | Link/Path |
|------|----------|
| OpenAN Integration Testing Process and Framework | `docs/OpenAN Integration Testing Process and Framework.md` |
| OpenAN Test Checklist | `docs/openan-test-checklist.md` |
| Feature requirements | openan-installation issues #2, #5, #9, #36 |
| Installation docs | `openan-installation` QUICKSTARTs (binary/one-click, binary/offline-install, containerized/online-install, containerized/offline-install, offline-install-compose), `openan-chart/values.yaml`, `config.env.example` |
| Tracking issue | [integration-test#19](https://github.com/project-openan/integration-test/issues/19) |

---

## 2. Objects Under Test

| Component | Repository | Version/Build | Test Layer | Notes |
|------|------|----------|----------|------|
| Installation & Deployment | `openan-installation` | <tag/commit> | FIT (deployment) | One-click scripts, offline bundles, Helm chart, compose stack, build scripts |
| Registry Center | `registry-center` | <tag/image digest> | Verification vehicle | Deployed by the installer; registration/query used to verify install correctness |
| Orchestration Center | `orchestration-center` | <tag/image digest> | Verification vehicle | Deployed by the installer; nginx entry and token API used to verify readiness |
| Frontend | `openan-frontend` / `openan-portal` / `workflow-designer` | <tag/image digest> | Verification vehicle | Frontend type selection verified via Pod image and page status |
| Databases | PostgreSQL / MySQL / external (e.g., gauss) | per values | Verification vehicle | `database.type` contract and bundled/external behavior |

---

## 3. Test Strategy

### 3.1 Test Layers

| Layer | Executor | Scope |
|------|--------|------|
| FIT | Installation WG | Integration correctness of all installation lines and the installer configuration contract |
| DFX (FIT-level non-functional) | Installation WG | Testability, diagnosability, serviceability, reliability, scaling, security, compatibility of the installer itself |
| SIT | Integration Testing WG | Release-level multi-feature combinations on RC versions (covered by the release test plan) |

### 3.2 Test Types

Aligned with Framework §10; applicable to this feature:

- [x] Functional testing (install main paths, component selection, configuration writes)
- [x] Exception testing (LLM validation failure, precheck failures, port conflicts)
- [x] Deployment testing (install/uninstall/idempotency/in-place upgrade; all five lines)
- [x] Stability testing (Pod recreation data survival, storage fallback, auto-provisioned entry)
- [x] Performance testing (HPA auto-scaling behavior)
- [x] Security testing (TLS certificates, secret masking, port exposure surface)
- [x] Compatibility testing (amd64/arm64, Debian-family/CentOS-family distros)

### 3.3 Test Method

- Real-environment execution: online VMs, real K8s clusters, offline hosts; services under test are not mocked
- Deterministic assertions only: exit codes, HTTP status codes, ports, files/directories, Pod status, Secret names, config file content — no LLM-output assertions; LLM endpoints are used only for installer connectivity validation or skipped per case
- Interactive installers are driven via pseudo-TTY (expect/python pty) where automation requires it
- Prohibitions: no sleep-based synchronization (use wait/retry); no sharing of mutable state between cases; no missing assertions

### 3.4 Automation Strategy

- 100% of P0/P1 cases automated and repeatable
- `execution` label layering: `smoke` (PR gate) / `full` (Daily) / `slow` (HPA observation window ~25 min)
- Failed cases automatically archived as issues with the scene preserved (logs, command output, Pod status, K8s events)

---

## 4. Test Scenarios

| Scenario ID | Scenario Description | Components | Priority | Notes |
|---------|---------|----------|--------|------|
| SCN-INST-001 | One-click binary full-stack install with single remote entry | binary/one-click | P0 | Install main path |
| SCN-INST-002 | Modular component selection across lines | binary flags, Helm wizard, chart values | P0 | --reg / wizard / values |
| SCN-INST-003 | Configuration matrix | LLM config, registry URL, database.type, frontend type, --sample, version pin | P0–P2 | Issues #5/#36 |
| SCN-INST-004 | Online Helm wizard + non-interactive --values install | online-install | P0 | Issue #2 |
| SCN-INST-005 | Offline K8s bundle install + local registry prefix replacement | offline-install | P0 | Issue #9 |
| SCN-INST-006 | Offline compose stack (--eval + DATABASE_TYPE) | offline-install-compose | P0–P2 | Issue #9/#36 |
| SCN-INST-007 | Binary offline tarball install | binary/offline-install | P1 | Issue #9 |
| SCN-INST-008 | Build tooling (image tag/push, offline bundle from local source) | containerized/build, offline build | P1–P2 | Issue #9 |
| SCN-INST-009 | Installer DFX capabilities (probes, diagnostics, idempotency, uninstall, data survival, HPA, TLS, multi-arch/distro) | all lines | P0–P2 | 27 DFX cases |

---

## 5. Test Case Design

### 5.1 Numbering Rules

- FIT cases: `FIT-openan-installation-<topic>-<number>` (e.g., `FIT-openan-installation-binary-install-001`)
- DFX cases: `DFX-openan-installation-<topic>-<number>` (e.g., `DFX-openan-installation-reliability-001`)

### 5.2 Priority Definitions

| Priority | Definition | Pass Rate Requirement |
|--------|------|-----------|
| P0 | Scenarios that block installation/the core deployment path | 100% (TRR entry and release gate) |
| P1 | Major functionality impaired but with workarounds | 100% |
| P2 | General scenarios | ≥80% |

### 5.3 Label Dimensions

Every case must carry the full set of labels in code: `feature` (openan-installation), `environment` (online/offline/with-workload-cluster), `components`, `priority`, `execution` (smoke/full/slow), `skip` (temporary skips must reference an issue). Case-level component dependencies are declared in the CSV `Component Deps` column.

### 5.4 Case Table

Cases are carried in the 16-column CSV archived in the same directory as this plan: [`testcases-openan-installation.csv`](testcases-openan-installation.csv) — **51 cases: 24 FIT + 27 DFX**. The DFX dimension is declared per case in the `Notes` column (`DFX type`: DFT/DFD/DFS/DFR/DFP/DFNS/DFC) and mapped to the standard `Case Type` values (Deployment/Exception/Stability/Performance/Security/Compatibility Test).

Revision v0.2 (2026-11-19 coverage audit): fixed two stale chart-contract cases (testability-001 OC probes exec→tcpSocket; performance-001 retargeted from orchestration HPA — rejected by the chart — to openan-frontend HPA), corrected the first-boot admin token flow (initial password → 403 Password change required → change password → token), and added five audit-gap cases: online uninstall data preservation (serviceability-007), binary offline uninstall (serviceability-008), No-MetalLB NodePort fallback (reliability-005), compose config parser injection protection (security-006), binary offline bundle build (binary-pack-001).

Revision v0.3 (2026-11-26 test-code review): aligned the case table with the batch-1 automation. binary-install-001 and binary-components-001 verify readiness through the registry query API (the binary registry-center v1.0.0 exposes no `/health` route) and through the reverse-proxied API endpoints; llm-config-001 supplies the API key through the `LLM_API_KEY` environment variable; the offline K8s cases run the installers with `--yes`; serviceability-003 starts the sample agents server so that the sample-agent ports are really released; the token endpoint deviation caused by the frontend gateway (bare `/api/v1/*` is not proxied) is recorded in the Notes of helm-online-001 and offline-compose-001.

Revision v0.4 (2026-11-26 P1/P2 automation, batch 2): aligned the seven online-vm cases of batch 2 with the automation. registry-center v1.0.0 exposes no `/health` route, so binary-offline-001 and reliability-003 check the query API instead; the binary orchestration backend serves no root route, so binary-regurl-001 checks a concrete API path through the proxy; binary-filestore-001 reads `persistence.mode` from `etc/conf/persistence.conf` and registers without an access token; testability-002 asserts the log paths printed by the install summary (the QUICKSTART `frontend.log` entry is stale); local-build-001 verifies the pushed manifest with `imagetools inspect` because the registry catalog lists repository names only; security-001 needs a key of 9+ characters to observe the first-4/last-4 mask. Batch 3 (the cluster-ops P1 cases) aligned helm-values-001 (the values file and Secrets come from the wizard with a cancelled deploy), db-type-003 (`PERSISTENCE_MODE` is read with `kubectl exec … printenv` because it is injected through a ConfigMap), diagnosability-002 (the phase is named Preflight and the exit code is 2), serviceability-007 (namespace deletion must also be declined), reliability-002 (the fallback is automatic, pinned to the first node, with three PVs) and reliability-005 (switching ingress-nginx to NodePort is a manual QUICKSTART step; the installer only prints the fallback address). Batch 4 (the offline-node P1 cases) aligned offline-k8s-002 (Secrets come from a prior installer run, the values file from the repository), serviceability-005 (hostPath directories are left in place by design), serviceability-006 (the reinstall uses the same config file), security-003 and security-002 (registry-center v1.0.0 exposes no `/health` route, so the in-cluster TLS check opens the query endpoint) and security-006 (a runtime env file that overrides a managed key is rejected with exit code 1). Batch 5 (the 15 P2 cases) aligned binary-sample-001 (the sample agents server binds 8899-8907/26335/26336, not 8080), llm-config-002 (the retry prompt only exists in interactive mode), security-004 (the HTTPS switch is rendered into ConfigMaps and orchestration-center keeps tcpSocket probes), compatibility-001/002/003 (build.sh components and registry flags; the full-stack install is needed for the Node.js runtime; the offline installer's architecture lines and the query endpoint), binary-pack-001 (the npm cache is part of the orchestration-center bundle only) and compose-db-001 (the configuration references the files generated by `gen-secrets.sh --eval`).

Revision v0.5 (2026-11-27 test-code fix after the first VM run): compatibility-002 asserted both the reuse line of an existing interpreter and the family auto-install lines, so it could pass on no host — a VM that already has Python 3.12+ prints no auto-install line and a fresh VM prints no reuse line. The case now probes the host's runtimes first with the installer's own gates (`python3.12`/`python3` at 3.12+, `node` at 20.19+) and asserts the reuse lines on a host that already has them or the family auto-install lines on a host without them; the probed state is written to `test-run.log`. The Expected Result and Notes of compatibility-002 record the reuse behaviour.

Revision v0.6 (2026-11-28 cluster-ops alignment): testability-001 allows registry-center and orchestration-center up to three start-up restarts (both exit with a storage error until the bundled database is reachable) and requires every restart count to stay unchanged for 120 seconds; every other Pod must still show `RESTARTS 0`. reliability-004 accepts one rerun of `install.sh` after a first run that fails in the infrastructure phase because the MetalLB validation webhook is not Ready yet. Both are product gaps that one run cannot wait out; they are recorded in the package README (Known Product Defects 5 and 6) and still need an issue in openan-installation.

Case table status: generated via the test-case generation skills, cross-checked for the FIT/DFX boundary, case-reviewed, and audited against the repository architecture/QUICKSTART documents. Review intermediates are not archived in this repository.

### 5.5 Case Design Requirements

- Every case includes: preconditions, steps, assertions, and cleanup actions (teardown removes services, test data, and restores backups)
- Cases must be independently repeatable; depending on execution order is prohibited
- Placeholder inputs (`<TAG>`, `<MODEL>`, `<LOCAL_REGISTRY>`, etc.) are parameterized via environment variables at automation time

---

## 6. Test Environment and Data

### 6.1 Environment Topology

| Item | Value |
|----|------|
| Online VMs | Linux x86_64/aarch64; Debian/Ubuntu family and CentOS/RHEL/openEuler family; sudo access |
| Online K8s cluster | v1.25+ with default StorageClass; bare-metal variant without LB (MetalLB case) and a variant without default StorageClass (hostPath fallback case) |
| Offline K8s cluster | v1.33+; containerd trusting the in-cluster registry; 20GB+ free disk on the install node |
| Offline compose host | Docker Engine + Compose v2.20+, Python 3.10+ |
| Binary offline host | Python 3.12+, Node.js 20.19+, nginx, openssl pre-installed (x86_64 and aarch64) |
| Environment provider | LF Networking Foundation; availability confirmed by the Integration Testing WG |

### 6.2 Dependent Services

| Dependency | Configuration | Notes |
|------|---------|------|
| LLM endpoint | External OpenAI-compatible endpoint (online); internal endpoint (offline); or skip path | Connectivity validation only; no output assertions |
| External database | Service-supported external type (e.g., gauss) with database/user created | **Provisioned by the Integration Testing WG** (case `db-type-003`) |
| Local image registry | Harbor or local registry (push/pull) | `local-build-001`, `offline-k8s-002`, `compatibility-001` |
| Build machine | Docker 20.10+/buildx/QEMU | Image and offline bundle build cases |

### 6.3 Test Data

- values files per `deployment.yaml.example` / `example.values.yaml` (all image tags, non-secret fields)
- `config.env` for offline lines (METALLB_POOL, DB_PASSWORD, OC_ADMIN_PASSWORD, LLM endpoint)
- Self-provided certificate material for the custom-TLS case; test Agent registration payloads for service-level verification
- Test API keys (8+ chars) for the masking case

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
- Failed cases automatically archived as issues with logs, command output, and cluster info attached
- Fix PRs must add regression cases and rerun all FIT cases for the feature

---

## 9. Schedule and Responsibilities

| Milestone | Target | Owner | Deliverable |
|------|------|--------|--------|
| Test plan + case table review | target 2026-11-22 | Integration Testing WG | This plan + CSV merged into `docs/plans/26-winter/` |
| TRR review | target 2026-11-24 | Installation WG Maintainer | TRR conclusion (Test Checklist Chapter 1) |
| FIT full self-test + report | target 2026-12-05 (RC-0 acceptance) | WG test owner | Self-test report in `docs/reports/26-winter/` |
| RC-1 regression | 2026-11-25 ~ 2026-12-16 (RC-1 window) | Integration Testing WG | RC-1 test report |

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|------|---------|
| Special environments hard to obtain (bare-metal without LB, cluster without default StorageClass, aarch64 hosts) | Case delays / descoping | Apply to the Integration Testing WG in advance; reuse the community lab; mark affected cases `skip-temporarily` with issue links if unavailable |
| External database instance availability (gauss) | db-type-003 blocked | Provisioned by the Integration Testing WG; confirm before RC-0 |
| Interactive installer automation (wizards, confirmations) | Flaky automation | Use pseudo-TTY drivers (expect/python pty) and non-interactive variants (`--values`, piped `yes`) where documented |
| LLM endpoint instability (connectivity validation cases) | Case flakiness | Connectivity-only assertions; documented skip path; mock/stub endpoint where allowed |
| Long observation windows (HPA ~25 min) | CI duration | `slow` execution label; dedicated CI timeout |

---

## 11. Deliverables and Archive

| Deliverable | Archive Path |
|--------|---------|
| Test plan (this document) | `docs/plans/26-winter/` |
| Case table CSV | `docs/plans/26-winter/testcases-openan-installation.csv` |
| Test code | `e2e/openan-installation/` |
| Test report | `docs/reports/26-winter/` (template: [test-report-template.md](../../templates/test-report-template.md)) |

---

## Appendix

- Test Checklist: `docs/openan-test-checklist.md`
- Framework document: `docs/OpenAN Integration Testing Process and Framework.md`
- Tracking issue: [integration-test#19](https://github.com/project-openan/integration-test/issues/19)
