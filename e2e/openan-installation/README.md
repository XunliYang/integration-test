# openan-installation E2E Tests

This package automates the FIT/DFX test cases for the OpenAN system-level installation and deployment tooling (`openan-installation`), covering the five installation lines, the installer configuration contract, and the installer's non-functional design capabilities. Backend framework: **pytest** (repo standard, Framework §7.1); all cases run shell/kubectl/docker commands **locally on the target test host**.

> Scope boundary: this package covers the installer itself (install/uninstall/config/build lines). Business-level FIT cases of deployed components (registry-center, orchestration-center APIs) live in their own packages; this package only uses those services as deployment-verification vehicles (health endpoints, token API), per the FIT/DFX attribution criteria.

## Test Scope

Case source: [`docs/plans/26-winter/testcases-openan-installation.csv`](../../docs/plans/26-winter/testcases-openan-installation.csv) (51 reviewed cases: 24 FIT + 27 DFX). **Batch 1 delivers all 12 P0 cases** (all labeled `execution=smoke`); batches 2–5 cover the remaining 39 cases (24 P1, 15 P2), so every case in the table now has automation code.

### Batch 1 — P0 (this delivery)

| Case ID | Verifies | Env profile | Status |
| --- | --- | --- | --- |
| `FIT-openan-installation-binary-install-001` | One-click binary full-stack install with single remote entry | online-vm | 🚧 batch 1 |
| `FIT-openan-installation-binary-components-001` | `--reg` installs registry-center only, no other resources | online-vm | 🚧 batch 1 |
| `FIT-openan-installation-llm-config-001` | Valid LLM config passes validation and is written | online-vm | 🚧 batch 1 |
| `FIT-openan-installation-helm-online-001` | Online Helm wizard full install; platform usable | cluster-ops | 🚧 batch 1 |
| `FIT-openan-installation-helm-components-001` | Wizard component selection deploys registry-center only | cluster-ops | 🚧 batch 1 |
| `FIT-openan-installation-offline-k8s-001` | Offline K8s bundle installs fully offline | offline-node | 🚧 batch 1 |
| `FIT-openan-installation-offline-compose-001` | Offline compose stack healthy with single public entry | offline-node | 🚧 batch 1 |
| `DFX-openan-installation-testability-001` | Chart renders standard probes; kubelet keeps pods Ready | cluster-ops | 🚧 batch 1 |
| `DFX-openan-installation-serviceability-001` | Binary install re-run is idempotent and keeps certificates | online-vm | 🚧 batch 1 |
| `DFX-openan-installation-serviceability-003` | Binary `uninstall --force` removes artifacts, preserves env tools | online-vm | 🚧 batch 1 |
| `DFX-openan-installation-reliability-001` | Bundled DB data survives pod restart via PVC | cluster-ops | 🚧 batch 1 |
| `DFX-openan-installation-security-002` | Offline default enables in-cluster HTTPS with generated CA | offline-node | 🚧 batch 1 |

### Batch 2 — online-vm P1 (this delivery)

| Case ID | Verifies | Env profile | Status |
| --- | --- | --- | --- |
| `FIT-openan-installation-binary-regurl-001` | Orchestration-only install writes the registry URL as-is | online-vm | 🚧 batch 2 |
| `FIT-openan-installation-binary-filestore-001` | Binary install defaults registry-center to file persistence | online-vm | 🚧 batch 2 |
| `FIT-openan-installation-binary-offline-001` | Binary offline tarball install brings services up | offline-node | 🚧 batch 2 |
| `FIT-openan-installation-local-build-001` | build.sh tags and pushes images to a custom local registry | online-vm (build host) | 🚧 batch 2 |
| `DFX-openan-installation-testability-002` | Binary install exposes PIDs and logs | online-vm | 🚧 batch 2 |
| `DFX-openan-installation-reliability-003` | Port conflict is detected and cleared before service start | online-vm | 🚧 batch 2 |
| `DFX-openan-installation-security-001` | API key input is masked and never echoed in full | online-vm | 🚧 batch 2 |

### Batch 3 — cluster-ops P1 (this delivery)

| Case ID | Verifies | Env profile | Status |
| --- | --- | --- | --- |
| `FIT-openan-installation-helm-values-001` | Non-interactive install with `--values` completes | cluster-ops | 🚧 batch 3 |
| `FIT-openan-installation-db-type-001` | Bundled `database.type=postgresql` deploys postgres and services work | cluster-ops | 🚧 batch 3 |
| `FIT-openan-installation-db-type-002` | Bundled `database.type=mysql` deploys mysql and services work | cluster-ops | 🚧 batch 3 |
| `FIT-openan-installation-db-type-003` | External `database.type` deploys no in-cluster DB and passes the type through | cluster-ops | 🚧 batch 3 |
| `DFX-openan-installation-diagnosability-002` | Online installer precheck fails clearly when the cluster is unreachable | cluster-ops | 🚧 batch 3 |
| `DFX-openan-installation-serviceability-007` | Online Helm uninstall preserves runtime PVCs until data cleanup is confirmed | cluster-ops | 🚧 batch 3 |
| `DFX-openan-installation-reliability-002` | Storage auto-detection falls back to a hostPath PV | cluster-ops (dedicated) | 🚧 batch 3 |
| `DFX-openan-installation-reliability-004` | Bare-metal cluster without LB gets a MetalLB auto-provisioned entry | cluster-ops (dedicated) | 🚧 batch 3 |
| `DFX-openan-installation-reliability-005` | Cluster without MetalLB gets a reachable NodePort entry fallback | cluster-ops (dedicated) | 🚧 batch 3 |

### Batch 4 — offline-node P1 (this delivery)

| Case ID | Verifies | Env profile | Status |
| --- | --- | --- | --- |
| `FIT-openan-installation-offline-k8s-002` | Values registry prefix replacement installs from a local registry | offline-node (K8s) | 🚧 batch 4 |
| `DFX-openan-installation-diagnosability-001` | Offline check-env reports the exact fix for a missing prerequisite | offline-node (K8s) | 🚧 batch 4 |
| `DFX-openan-installation-serviceability-002` | Offline installer re-run upgrades the release in place | offline-node (K8s) | 🚧 batch 4 |
| `DFX-openan-installation-serviceability-005` | Offline uninstall removes the release, the in-cluster registry and optional data | offline-node (K8s) | 🚧 batch 4 |
| `DFX-openan-installation-serviceability-006` | Compose uninstall keeps data volumes for reinstall reuse | offline-node (compose) | 🚧 batch 4 |
| `DFX-openan-installation-serviceability-008` | Binary offline uninstall removes versioned directories and the static web root | offline-node (binary) | 🚧 batch 4 |
| `DFX-openan-installation-security-003` | User-provided certificate Secrets are honored | offline-node (K8s) | 🚧 batch 4 |
| `DFX-openan-installation-security-006` | Compose config parser rejects injection attempts and managed-key override | offline-node (compose) | 🚧 batch 4 |

### Batch 5 — P2 (this delivery)

| Case ID | Verifies | Env profile | Status |
| --- | --- | --- | --- |
| `FIT-openan-installation-binary-regurl-002` | Full-stack mode writes the local registry URL as http | online-vm | 🚧 batch 5 |
| `FIT-openan-installation-binary-sample-001` | `--sample` starts the agents example server | online-vm | 🚧 batch 5 |
| `FIT-openan-installation-binary-version-001` | `--reg-version` pins the component source tag | online-vm | 🚧 batch 5 |
| `FIT-openan-installation-llm-config-002` | Invalid LLM endpoint fails validation with a retry prompt | online-vm | 🚧 batch 5 |
| `FIT-openan-installation-local-build-002` | `build-offline.sh --app-source build` builds the bundle from local sources | online-vm (build host) | 🚧 batch 5 |
| `FIT-openan-installation-binary-pack-001` | `pack.sh` builds a dual-architecture binary offline bundle | online-vm (build host) | 🚧 batch 5 |
| `FIT-openan-installation-compose-db-001` | Compose `DATABASE_TYPE=postgresql` selects the bundled postgres | offline-node (compose) | 🚧 batch 5 |
| `FIT-openan-installation-frontend-select-001` | `frontend.type=workflow-designer` deploys the legacy frontend | cluster-ops | 🚧 batch 5 |
| `DFX-openan-installation-serviceability-004` | Interactive uninstall shows the plan and cancels without changes | online-vm | 🚧 batch 5 |
| `DFX-openan-installation-performance-001` | HPA scales `openan-frontend` on CPU pressure and scales back | cluster-ops | 🚧 batch 5 |
| `DFX-openan-installation-security-004` | Disabling HTTPS flips the whole chain with an explicit warning | offline-node (K8s) | 🚧 batch 5 |
| `DFX-openan-installation-security-005` | Compose stack publishes only the public entry | offline-node (compose) | 🚧 batch 5 |
| `DFX-openan-installation-compatibility-001` | `build.sh` produces multi-arch manifests for amd64 and arm64 | online-vm (build host) | 🚧 batch 5 |
| `DFX-openan-installation-compatibility-002` | Runtime auto-install adapts to the distro family | online-vm (fresh VM) | 🚧 batch 5 |
| `DFX-openan-installation-compatibility-003` | Binary offline package selects wheels by host architecture | offline-node (fresh VM, binary) | 🚧 batch 5 |

### Coverage

All 51 reviewed cases have automation code and an `Automated Test` entry in the case table (36 P0/P1 cases in batches 1–4, 15 P2 cases in batch 5). Cases whose preconditions need special hosts or clusters skip with an explicit reason until the matching `OPENAN_INSTALL_*` switch is set.

### Files

Test modules are grouped by installation line (`binary/`, `binary-offline/`, `image-build/`, `compose/`, `helm/`, `offline-k8s/); `utils/` and `conftest.py` are shared. The case table's `Automated Test` column uses the same `<line>/<file>::<test>` form.

| File | Covers | Responsibility |
| --- | --- | --- |
| `conftest.py` | — | Env loading (`e2e/.env`), marker registration, machine-profile gate, failure cleanup and scene capture |
| `utils/env.py` | — | `.env` parsing + typed accessors for `OPENAN_INSTALL_*` |
| `utils/shell.py` | — | Local command executor (subprocess, timeout, output capture, evidence saving with secret redaction, cookie-jar curl), interactive pexpect driver, kubectl helpers, wait/retry, scene capture, `KEY=VALUE` reader, ANSI stripping |
| `utils/binary_install.py` | — | Binary one-click driver (composable prompt answers, install/uninstall, registry readiness, interactive `configure_llm.sh`) |
| `utils/binary_offline.py` | — | Binary offline driver (directory gate, install/uninstall with ANSI-stripped output, component directories) |
| `utils/build_tools.py` | — | Build-tool driver (`build.sh`, image inspection, retention list) |
| `utils/compose_install.py` | — | Compose driver (generated config set, check-env, install/uninstall, status, state reset) |
| `utils/helm_install.py` | — | Online Helm driver (wizard with composable answers, configure-only mode, `--values` deploy, parametrized uninstall, cluster queries) |
| `utils/offline_install.py` | — | Offline K8s driver (check-env, install/uninstall with `--yes` or piped answers, config copies, Secret/PVC/Ingress readers, in-cluster TLS probe, access URL parsing) |
| `utils/oc_auth.py` | — | OC admin token flow incl. first-boot forced password change (403 → login → change-password → token) |
| `utils/agentcard.py` | — | Minimal sample AgentCard fixture and register/fetch/delete helpers |
| `binary/test_binary_compatibility.py` | DFX compatibility-002/003 | Runtime auto-install per distro family; wheel selection per architecture |
| `binary/test_binary_filestore.py` | FIT binary-filestore-001 | File persistence default and the AgentCard data path |
| `binary/test_binary_install.py` | FIT binary-install-001, binary-components-001 | Binary one-click install main paths |
| `binary/test_binary_options.py` | FIT binary-sample-001, binary-version-001 | `--sample` and `--reg-version` install options |
| `binary/test_binary_regurl.py` | FIT binary-regurl-001/002 | Orchestration-only and full-stack registry URL handling |
| `binary/test_binary_reliability.py` | DFX reliability-003 | Port conflict detection and cleanup |
| `binary/test_binary_security.py` | DFX security-001 | API key masking in interactive `configure_llm.sh` |
| `binary/test_binary_serviceability.py` | DFX serviceability-001/003/004 | Idempotent re-run; forced uninstall; cancelled interactive uninstall |
| `binary/test_binary_testability.py` | DFX testability-002 | PID/kill-command summary and log files |
| `binary/test_llm_config.py` | FIT llm-config-001/002 | LLM configuration validation and write |
| `binary-offline/test_binary_offline.py` | FIT binary-offline-001, DFX serviceability-008 | Binary offline tarball install and uninstall |
| `image-build/test_build.py` | FIT local-build-001/002, binary-pack-001, DFX compatibility-001 | build.sh, build-offline.sh and pack.sh drivers |
| `compose/test_compose_security.py` | DFX security-005, security-006 | Published ports; compose config parser protections |
| `compose/test_compose_serviceability.py` | DFX serviceability-006, FIT compose-db-001 | Compose uninstall keeps volumes for reinstall; bundled PostgreSQL |
| `compose/test_offline_compose.py` | FIT offline-compose-001 | Offline compose stack install |
| `helm/test_data_persistence.py` | DFX reliability-001 | Pod recreation data survival |
| `helm/test_helm_database.py` | FIT db-type-001/002/003 | Bundled postgresql/mysql and external database contracts |
| `helm/test_helm_diagnosability.py` | DFX diagnosability-002 | Unreachable cluster fails at the preflight |
| `helm/test_helm_online.py` | FIT helm-online-001, helm-components-001 | Online Helm wizard installs (pexpect-driven TTY) |
| `helm/test_helm_performance.py` | DFX performance-001 | Frontend HPA scale-out and scale-back (`slow`) |
| `helm/test_helm_probes.py` | DFX testability-001 | Probe contract rendering and pod readiness |
| `helm/test_helm_reliability.py` | DFX reliability-002/004/005 | hostPath fallback, MetalLB auto-provision, NodePort entry |
| `helm/test_helm_serviceability.py` | DFX serviceability-007 | Uninstall keeps runtime PVCs until data cleanup is confirmed |
| `helm/test_helm_values.py` | FIT helm-values-001, frontend-select-001 | Non-interactive `--values` deploy; frontend type selection |
| `offline-k8s/test_offline_https.py` | DFX security-002 | Offline in-cluster HTTPS with generated CA |
| `offline-k8s/test_offline_k8s.py` | FIT offline-k8s-001 | Offline K8s bundle install |
| `offline-k8s/test_offline_k8s_diagnosability.py` | DFX diagnosability-001 | check-env fault injection |
| `offline-k8s/test_offline_k8s_registry.py` | FIT offline-k8s-002 | Local-registry image prefix in a values-only Helm install |
| `offline-k8s/test_offline_k8s_serviceability.py` | DFX serviceability-002, serviceability-005 | In-place re-run; full offline uninstall |
| `offline-k8s/test_offline_tls.py` | DFX security-003, security-004 | Custom certificate Secrets; HTTPS disabled |

## Directory Structure

```text
e2e/openan-installation/
├── README.md                     # this file
├── conftest.py                   # env load, markers, profile gate, cleanup fixture
├── utils/
│   ├── env.py                    # .env contract accessors
│   ├── shell.py                  # local shell/curl/kubectl executor, pexpect driver, redaction, wait/retry
│   ├── binary_install.py         # binary one-click driver
│   ├── binary_offline.py         # binary offline driver
│   ├── build_tools.py            # build.sh driver, image inspection, retention list
│   ├── compose_install.py        # compose driver: generated config, install/uninstall, status
│   ├── helm_install.py           # online Helm wizard driver (pexpect)
│   ├── offline_install.py        # offline K8s bundle driver, config copies, TLS probe
│   ├── oc_auth.py                # admin token flow with first-boot password change
│   └── agentcard.py              # sample AgentCard fixture and registry API helpers
├── binary/
│   ├── test_binary_compatibility.py
│   ├── test_binary_filestore.py
│   ├── test_binary_install.py
│   ├── test_binary_options.py
│   ├── test_binary_regurl.py
│   ├── test_binary_reliability.py
│   ├── test_binary_security.py
│   ├── test_binary_serviceability.py
│   ├── test_binary_testability.py
│   └── test_llm_config.py
├── binary-offline/
│   └── test_binary_offline.py
├── image-build/
│   └── test_build.py
├── compose/
│   ├── test_compose_security.py
│   ├── test_compose_serviceability.py
│   └── test_offline_compose.py
├── helm/
│   ├── test_data_persistence.py
│   ├── test_helm_database.py
│   ├── test_helm_diagnosability.py
│   ├── test_helm_online.py
│   ├── test_helm_performance.py
│   ├── test_helm_probes.py
│   ├── test_helm_reliability.py
│   ├── test_helm_serviceability.py
│   └── test_helm_values.py
└── offline-k8s/
    ├── test_offline_https.py
    ├── test_offline_k8s.py
    ├── test_offline_k8s_diagnosability.py
    ├── test_offline_k8s_registry.py
    ├── test_offline_k8s_serviceability.py
    └── test_offline_tls.py
```

## Suite Lifecycle

Unlike service packages, **there is no suite-level install/uninstall**: every case is self-contained and performs its own install → verify → uninstall cycle (exactly as written in the case CSV steps).

- `install_env` (session, autouse): loads `e2e/.env`, validates `OPENAN_INSTALL_MACHINE_PROFILE` and **errors** with a clear message when it is unset or unknown. `OPENAN_INSTALL_REPO_PATH` is required on `online-vm` / `cluster-ops` hosts (offline-node cases only need the bundle paths). The LLM key, admin password and DB password are registered for redaction.
- Per case: profile gate → environment gate (skip with an explicit reason) → `cleanup.add(...)` registers the uninstall **before** the installer starts → install under test → assertions on results → the case's own uninstall step with its assertions.
- **Failure path**: when a case fails, the `cleanup` fixture first captures the scene (`evidence/openan-installation/<case>-scene-*.log`: listening ports, Pods, PVCs, events, Helm releases, container logs) and then runs the registered uninstall steps LIFO, saving each output as `<case>-cleanup-N.log`. A cleanup step that exits non-zero is listed under `HOST LEFT DIRTY BY FAILED CLEANUP` in `test-run.log`: reset the host before the next run. Cleanup results never mask the original failure; a passing case has already asserted its own uninstall.
- **Secret handling**: `pexpect` runs with echo off, and every transcript, evidence file, log line and assertion message is passed through `utils/shell.py::redact` — registered values (`OPENAN_INSTALL_LLM_API_KEY`, `OPENAN_INSTALL_ADMIN_PASSWORD`, `OPENAN_INSTALL_DB_PASSWORD`, the derived admin password, generated bearer tokens, the compose admin password) plus credential-looking fields (`access_token`, `api_key`, `password`, `Authorization: Bearer …`).
- **Serial execution only**: install cases mutate whole-host state (ports, directories, systemd-level processes, cluster namespace). Do not run with `pytest-xdist` for this package.

## Prerequisites

1. Python 3.10+ with `pytest` and `pexpect` (wizard-driven cases require a pty driver; Linux only).
2. The `openan-installation` repository checked out locally (`OPENAN_INSTALL_REPO_PATH`) with the required install scripts executable.
3. Machine profile set per host:
    - `online-vm` — networked Linux VM (Debian/Ubuntu or CentOS/RHEL/openEuler families, sudo) for the binary one-click line;
    - `cluster-ops` — ops host with `kubectl`, `helm`, `python3` and a reachable K8s v1.25+ cluster (`KUBECONFIG`), images pullable with tag `OPENAN_INSTALL_IMAGE_TAG`;
    - `offline-node` — offline host (K8s node with pre-staged bundle, or compose host with Docker Engine + Compose v2.20+).
4. Cluster cases require a default StorageClass or hostPath fallback enabled; a reachable OpenAI-compatible LLM endpoint for the wizard connectivity probe.

## Environment Requirements

**Cluster source — existing cluster, no bootstrap.** Containerized cases connect to an **existing** K8s cluster via `KUBECONFIG` (LFN-provided, availability confirmed by the Integration Testing WG). This package does not create kind/k3s clusters: Framework §5.1 requires FIT to run on real environments, and kind is only a local-development option (Framework §7.1).

**Offline bundles — pre-staged, not built here.** The offline bundles (`openan-offline-<TAG>.tar.gz`, `openan-offline-compose-<TAG>.tar.gz`) are built on a networked build machine (`build-offline.sh` / compose packaging) and transferred to the offline node before the run. Paths are injected via `OPENAN_INSTALL_OFFLINE_K8S_BUNDLE` / `OPENAN_INSTALL_OFFLINE_COMPOSE_BUNDLE`; bundle-building cases are a later batch.

**Version matrix** (from the case preconditions):

| Item | Requirement | Applies to |
| --- | --- | --- |
| Online K8s cluster | v1.25+, nodes Ready, reachable via kubectl | cluster-ops cases |
| Offline K8s cluster | v1.33+, containerd trusting the in-cluster registry | offline-node (K8s) |
| Helm | 3.14+ | cluster-ops cases |
| Docker Engine | 20.10+ (buildx for later build cases) | all profiles |
| Compose | v2.20+ (`ps --format json` must report health) | offline-node (compose) |
| Python | 3.10+ (compose host / ops machine); 3.12+ (binary targets) | all profiles |
| Node.js | 20.19+ (pre-installed on binary offline hosts) | offline-node (binary) |
| Bundled MySQL (chart) | 8.4.3 (per values.yaml descriptor) | cluster cases with bundled mysql |

**Version under test — injected, never hardcoded.** The version under test is the RC image tag published by Release Management, injected via `OPENAN_INSTALL_IMAGE_TAG` (maps to the `<IMAGE_TAG>` / `<TAG>` placeholders in the case table). Component source-version pinning (`<VER>`, `binary-version-001`) and `--reg-version` variants are P2 cases in a later batch.

## Environment Variables

Loaded from `e2e/.env` (see `.env.template`; **never commit real values**):

```bash
# Machine profile of this host: online-vm | cluster-ops | offline-node
OPENAN_INSTALL_MACHINE_PROFILE=
# Local checkout path of the openan-installation repository
OPENAN_INSTALL_REPO_PATH=
# One-click binary scripts subdirectory (relative to the repo path)
OPENAN_INSTALL_BINARY_SUBDIR=binary/one-click
# LLM endpoint for configure_llm.sh / wizard connectivity validation
OPENAN_INSTALL_LLM_MODEL=
OPENAN_INSTALL_LLM_API_URL=
OPENAN_INSTALL_LLM_API_KEY=
# Online Helm line
OPENAN_INSTALL_IMAGE_TAG=
OPENAN_INSTALL_ADMIN_PASSWORD=
OPENAN_INSTALL_DB_PASSWORD=
# MetalLB pool answered at the wizard's "MetalLB IP pool" prompt (must be routable and unused in the cluster network)
OPENAN_INSTALL_METALLB_POOL=
# Wizard frontend choice and, for portal, the portal image tag
OPENAN_INSTALL_FRONTEND_TYPE=workflow-designer
OPENAN_INSTALL_PORTAL_TAG=v1.0.0
# Offline lines (bundle paths; empty = the corresponding cases skip)
OPENAN_INSTALL_OFFLINE_K8S_BUNDLE=
OPENAN_INSTALL_OFFLINE_COMPOSE_BUNDLE=
OPENAN_INSTALL_OFFLINE_CONFIG_ENV=
# Orchestration-only binary install: registry URL entered at the prompt (binary-regurl-001)
OPENAN_INSTALL_REGISTRY_URL=
# Binary offline install directory (install.sh plus dist/*.tar.gz, or the tarballs next to it)
OPENAN_INSTALL_BINARY_OFFLINE_DIR=
# Private registry (host:port) whose images offline-k8s-002 uses in the values file; empty = case skips
OPENAN_INSTALL_LOCAL_REGISTRY=
# Source tag for binary-version-001 (a registry-center tag other than the built-in default v1.0.0); empty = case skips
OPENAN_INSTALL_REG_VERSION=
# Local source checkouts with a Dockerfile for build-offline.sh --app-source build (local-build-002); empty = case skips
OPENAN_INSTALL_REGISTRY_SRC=
OPENAN_INSTALL_ORCHESTRATION_SRC=
# Opt-in for compatibility-002/003: set to 1 only on a disposable VM whose runtimes the installer may change
OPENAN_INSTALL_FRESH_VM=
# Optional ssh target of an adjacent machine for the security-005 port probe; empty = host-side probing only
OPENAN_INSTALL_PROBE_HOST=
# Build-machine cases: opt-in switch plus push target
OPENAN_INSTALL_BUILD_HOST=
OPENAN_INSTALL_BUILD_REGISTRY=
OPENAN_INSTALL_BUILD_NAMESPACE=project-openan
OPENAN_INSTALL_BUILD_TAG=
OPENAN_INSTALL_BUILD_PLATFORMS=linux/amd64
# External database for db-type-003 (lowercase type the services support, e.g. gauss); empty = case skips
OPENAN_INSTALL_EXTERNAL_DB_TYPE=
OPENAN_INSTALL_EXTERNAL_DB_HOST=
OPENAN_INSTALL_EXTERNAL_DB_PORT=
OPENAN_INSTALL_EXTERNAL_DB_PASSWORD=
# Opt-in for cases that change cluster-wide state (reliability-002/004/005); set to 1 only on a dedicated test cluster
OPENAN_INSTALL_DEDICATED_CLUSTER=
```

| Variable | Used by | Missing behavior |
| --- | --- | --- |
| `OPENAN_INSTALL_MACHINE_PROFILE` | all cases | session fixture errors for every case (`profile not set` / unknown profile) |
| `OPENAN_INSTALL_REPO_PATH` | online-vm / cluster-ops cases | session fixture errors on these profiles (offline-node cases do not need it) |
| `OPENAN_INSTALL_LLM_*` | llm-config-001, helm wizard cases | cases skip (`… not configured`) |
| `OPENAN_INSTALL_IMAGE_TAG` | helm-online-001, helm-components-001, testability-001, reliability-001 | cases skip (`OPENAN_INSTALL_IMAGE_TAG is not set`) |
| `OPENAN_INSTALL_ADMIN_PASSWORD` / `_DB_PASSWORD` | helm wizard cases | cases skip (`… are not set`) |
| `OPENAN_INSTALL_METALLB_POOL` | helm wizard cases | cases skip when unset **and** the cluster has no `openan-pool` IPAddressPool |
| `OPENAN_INSTALL_FRONTEND_TYPE` / `_PORTAL_TAG` | helm wizard cases | defaults `workflow-designer` / `v1.0.0` |
| `OPENAN_INSTALL_OFFLINE_K8S_BUNDLE` + `_OFFLINE_CONFIG_ENV` | offline-k8s-001, security-002 | cases skip when either is empty |
| `OPENAN_INSTALL_OFFLINE_COMPOSE_BUNDLE` | offline-compose-001 | case skips on `offline-node` profile |
| `OPENAN_INSTALL_REGISTRY_URL` | binary-regurl-001 | case skips |
| `OPENAN_INSTALL_BINARY_OFFLINE_DIR` | binary-offline-001, serviceability-008 (later: compatibility-003) | case skips |
| `OPENAN_INSTALL_LOCAL_REGISTRY` | offline-k8s-002 | case skips |
| `OPENAN_INSTALL_REG_VERSION` | binary-version-001 | case skips (also when equal to the default `v1.0.0`) |
| `OPENAN_INSTALL_REGISTRY_SRC` / `_ORCHESTRATION_SRC` | local-build-002 | case skips |
| `OPENAN_INSTALL_FRESH_VM` | compatibility-002/003 | cases skip unless set to `1` |
| `OPENAN_INSTALL_PROBE_HOST` | security-005 | adjacent-machine probe is skipped; host-side probing still runs |
| `OPENAN_INSTALL_BUILD_HOST` | local-build-001 | case skips unless set to `1` (build cases are opt-in) |
| `OPENAN_INSTALL_BUILD_REGISTRY` | local-build-001 | case skips |
| `OPENAN_INSTALL_BUILD_NAMESPACE` / `_BUILD_TAG` / `_BUILD_PLATFORMS` | build cases | defaults `project-openan` / `OPENAN_INSTALL_IMAGE_TAG` / `linux/amd64` |
| `OPENAN_INSTALL_EXTERNAL_DB_TYPE` / `_HOST` / `_PORT` / `_PASSWORD` | db-type-003 | case skips |
| `OPENAN_INSTALL_DEDICATED_CLUSTER` | reliability-002/004/005 | cases skip unless set to `1` (they change cluster-wide state) |
| `EVIDENCE_DIR` | all cases | defaults to `evidence/` relative to the working directory |

Placeholders in the case table (`<TAG>`, `<MODEL>`, `<KEY>`, `<POOL>`, …) map one-to-one onto these variables; no environment-specific value is hardcoded in test code.

## Labels

Every case carries its labels as pytest markers (strict mode is on; unregistered markers fail collection):

| Dimension | Marker | Source |
| --- | --- | --- |
| feature | `openan-installation` | module `pytestmark` |
| milestone | `26-winter` | per test function |
| Case ID | `FIT-openan-installation-…` / `DFX-openan-installation-…` | per test function; registered in `conftest.py::CASE_IDS` |
| environment | `online` / `offline` / `with-workload-cluster` | module `pytestmark` |
| components | `registry-center`, `orchestration-center`, … | per test function, copied from the CSV `Component Deps` column |
| priority | `P0` / `P1` / `P2` | module `pytestmark` |
| execution | `smoke` / `full` / `slow` | module `pytestmark` |
| skip | `skip-temporarily` | only together with an issue link in the skip reason |

## How to Run

From the repository root:

```bash
cp e2e/.env.template e2e/.env   # fill real values on the target host
cd e2e
pytest openan-installation/ -v                 # all cases applicable to this host profile
pytest openan-installation/ -m smoke -v         # batch-1 P0 set
pytest openan-installation/test_binary_install.py -v   # single file
pytest openan-installation/ -m FIT-openan-installation-binary-install-001   # single case
```

Run **one feature directory per pytest invocation**: every feature package exposes a top-level `utils` package, and pytest's default import mode would let the first package on `sys.path` shadow the others. `conftest.py` refuses to load when another package's `utils` is already imported.

Timeout guidance: single install cases take 3–10 minutes; pass `-m smoke` in PR gates; do not add `xdist`. Failure evidence (command output, scene captures, cleanup results) is written to `EVIDENCE_DIR` (default `evidence/`, git-ignored) with secrets redacted; `test-run.log` records START/END, outcome and the session totals.

## Case Behavior Notes

- **Binary one-click**: interactive prompts are answered by anchored patterns (`utils/binary_install.py`). The default cases answer "n" to the sample-agents prompt and assert the summary does not list the agents server; `serviceability-003` starts it on purpose so the sample-agent ports are really occupied before the uninstall (orchestration-center v1.0.0 binds 8899-8907/26335/26336; `uninstall.sh` additionally scans 8080, which no sample server binds). The binary registry-center has no `/health` route, so readiness is checked through the query API (recorded in the case table).
- **Online Helm wizard**: the driver answers every wizard prompt explicitly, including `Database` → `in-cluster` and `Database backend` → `postgresql`. The uninstall driver answers the three uninstall questions by their prompt text.
- **testability-001**: registry-center and orchestration-center exit with a storage error until the bundled database is reachable and restart three times on a fresh install (Known Product Defect #5). The case allows up to `STARTUP_RESTART_TOLERANCE` (3) restarts for these two Pods, requires `RESTARTS 0` for every other Pod and requires every count to stay unchanged for `RESTART_SETTLE_SECONDS` (120); a count that still changes inside the window is a crash loop and fails.
- **Offline K8s**: `install.sh` and `uninstall.sh` run with `--yes`, so the cleanup also removes PVCs/PVs, the namespace and the MetalLB pool and the next case starts from a clean cluster. The platform URL is taken from the installer's `Access URL:` line (HTTP or HTTPS depending on `INGRESS_HOST`).
- **Offline compose**: the admin password is read from `runtime/compose.json` (the value the container actually receives). Because `scripts/uninstall.sh` keeps the SQL volume and bind-mounted data by design, the case removes them afterwards (`down --volumes`) so every run is a first boot.
- **security-002**: the in-cluster HTTPS check runs in a temporary Pod that mounts the `openan-ingress-client` Secret, using the registry-center image; the Pod is deleted in-case.
- **reliability-001**: card writes need a `vendor_agent` bearer credential; the case adds one to `openan-rc-credentials` (the wizard only provisions a `partner_service` token). The chart default `registry.signatureValidationEnabled=false` accepts the unsigned sample card.
- **binary-regurl-001**: `OPENAN_INSTALL_REGISTRY_URL` is written to `server.conf` as entered; it does not have to be reachable for the case's assertions.
- **binary-filestore-001**: registry-center v1.0.0 stores the storage mode as `persistence.mode` in `etc/conf/persistence.conf` and exposes no access-token mechanism on the binary line, so the AgentCard is registered without one.
- **reliability-003**: the placeholder is `python -m http.server 5000 --bind 127.0.0.1`, started by the test as the same user that runs the installer (`ss -ltnp` only shows the PIDs of that user's processes, and `free_port` can only kill them).
- **security-001**: assertions run on the raw, un-redacted transcript (`CommandResult.stdout`), so a real leak would be detected; that transcript is never written to the evidence directory.
- **Binary offline** (`test_binary_offline.py`): `install.sh` and `uninstall.sh` print ANSI colour codes plus `✓`/`⚠`; their output is passed through `strip_ansi` before any assertion. An already extracted component directory is overwritten (the `Overwrite? (y/n):` prompt is answered `y`).
- **Build cases** (`test_build.py`): opt-in through `OPENAN_INSTALL_BUILD_HOST=1`; `docker login` must be done beforehand. `build.sh registry` pushes to the custom registry for local-build-001; `build.sh registry orchestration` builds the multi-arch manifests for compatibility-001; `build-offline.sh --app-source build` uses the two source checkouts for local-build-002; `pack.sh` builds the binary bundles (dual-arch wheels in both bundles, npm cache in the orchestration-center bundle only) for binary-pack-001. Build artifacts are deleted by the case; pushed image tags are appended to `evidence/openan-installation/image-retention.log` instead of being deleted, because deleting a tag depends on the registry type.
- **Configure-only wizard** (helm-values-001, db-type-001/002/003): `configure_online_helm()` answers `n` at `Deploy with this configuration?`; by then the wizard has already created `deployment.generated.json` and every Secret, so the cases continue with `./install.sh --values … --skip-build --skip-infra` or a direct `helm upgrade --install` exactly as the case table says.
- **Database variants**: the wizard driver selects `postgresql`/`mysql` or the external SQL prompts (`OPENAN_INSTALL_EXTERNAL_DB_*`). The `Database` prompt must be answered `external`: `configure.py` lower-cases the input, so the displayed option text `external SQL` is rejected.
- **MetalLB pool**: `uninstall.sh` always deletes `openan-pool`; cases that deploy without the wizard's infrastructure phase call `ensure_metallb_pool()` first so that a LoadBalancer address exists.
- **Dedicated-cluster cases** (`OPENAN_INSTALL_DEDICATED_CLUSTER=1`): reliability-002 removes the default StorageClass annotation and restores it; reliability-004 deletes the `metallb-system` and `ingress-nginx` namespaces (plus the admission webhook) and lets the installer reinstall them; reliability-005 patches the ingress-nginx Service to NodePort 30080/30443 (a manual QUICKSTART step — the installer only prints the fallback address) and restores it. Without the switch these cases skip.
- **reliability-004**: `install.sh` configures the MetalLB pool before the validation webhook that serves it is Ready, so a fresh MetalLB install fails with `failed calling webhook` (Known Product Defect #6). `install_online_helm()` recognises that failure in the infrastructure phase, waits for the `controller` Deployment in `metallb-system` and reruns `install.sh` once; the rerun's transcript is kept under a `-retry1` evidence stem.
- **reliability-005**: the HTTPS entry `https://<node-IP>:30443/` is checked with certificate verification disabled (`curl -k`), like every other HTTPS check in this package; the certificate SAN for the node IP is not asserted.
- **diagnosability-002**: the unreachable cluster is a temporary kubeconfig pointing at `https://127.0.0.1:1`, injected only into the installer's environment (`KUBECONFIG`); nothing on the ops machine is changed.
- **Offline K8s driver** (`utils/offline_install.py`): `install.sh` always runs with `--yes`. `uninstall.sh` runs with `--yes` (yes to persistent-data cleanup, MetalLB pool removal and namespace deletion) unless the case passes explicit answers, which are piped to the script in prompt order. Cases that change a setting (diagnosability-001, security-003) work on a copy of `config.env` written under `EVIDENCE_DIR` (mode 0600); the operator's `config.env` is never modified.
- **In-cluster TLS probe** (security-002, security-003): a temporary Pod built from the registry-center image mounts the ingress-client Secret under test and opens `https://registry-center:5000/rest/v1/registry-center/agent-cards` with `ca.crt` as the trust anchor; the Pod is deleted in-case. registry-center v1.0.0 has no `/health` route (the chart's own probes use the query endpoint).
- **offline-k8s-002**: the Secrets the chart references are created by a normal `scripts/install.sh` run; the release is then uninstalled with answers `y, n, n` so that the MetalLB pool and the namespace survive, and `example.values.yaml` (taken from the repository checkout, `<REG_HOST>` replaced) is deployed with plain Helm. On a cluster without a default StorageClass the hostPath settings are passed with `--set`.
- **Compose cases** (`utils/compose_install.py`): the configuration set (`config.env`, runtime env files, models, credential file) is generated by the test under `EVIDENCE_DIR/compose-config/` and installed with `scripts/install.sh --config <generated file>`; `install.sh --eval` and `gen-secrets.sh` are not used (see Known Product Defects #2 — offline-compose-001 is the only case that still exercises `--eval`). `reset_compose_state()` removes the SQL volume and the bind-mounted data after a case that must start from a first boot.
- **serviceability-005**: `uninstall.sh` leaves the node's `/data/openan-*` directories in place by design; the case asserts that the listing is unchanged and that the manual-cleanup hint is printed.
- **binary-sample-001 / binary-version-001**: the sample agents server is verified through the ports orchestration-center v1.0.0 really binds (8899-8907, 26335, 26336), not through the 8080 of the port table; `--reg-version` is checked against the `[MODE]` banner, the release archive URL and `.source-version`.
- **llm-config-002**: `configure_llm.sh` only shows the retry prompt when it is started without the full flag set, so the case drives it interactively (`run_binary_script`) and answers `skip` at the `Model [ … ]` retry prompt.
- **serviceability-004**: the interactive `./uninstall.sh` is driven by `run_interactive` and answered `n` at `Proceed with uninstallation? [y/N]:`; the plan sections and the `[CANCEL]` line are asserted on the transcript.
- **compatibility-002 / 003** (`OPENAN_INSTALL_FRESH_VM=1`): compatibility-002 runs the full-stack install because the Node.js resolver only runs for orchestration-center, probes the host's runtimes first with the installer's own gates (`python3.12`/`python3` at 3.12+, `node` at 20.19+) and then matches either the reuse lines (`[OK] Python <ver> (python3.12)` / `(python3)`, `[OK] Node.js v<ver>`) on a host that already has them or the Python/Node auto-install lines of the host's distro family on a host without them — the probed state is logged, so `test-run.log` shows which path a run really exercised; compatibility-003 matches the architecture detection lines and the `{arch} manylinux` wheel the offline installer installs.
- **performance-001** (`slow`): needs a working `kubectl top` (metrics-server); 8 `yes` loops per frontend pod, one HPA observation per minute, up to 10 minutes for scale-out and 15 for scale-back.
- **security-004**: `HTTPS_ENABLED="false"` is applied on a config copy; the switch values are read from the ConfigMaps. The assertion that registry-center mounts no `tls-certs` volume fails until Known Product Defect #4 is fixed.
- **security-005**: only `openan-nginx` publishes a host port; the application and SQL ports are probed on the host address (and, when `OPENAN_INSTALL_PROBE_HOST` is set, from the adjacent machine over ssh) and must be unreachable.

## Known Product Defects

The cases of defects 1-4 keep asserting the documented behaviour and **fail** until the product is fixed; they are not worked around. Defects 5 and 6 cannot be waited out inside one run, so their cases tolerate exactly the behaviour described below and still pass. File an issue in openan-installation for each defect and mark the cases of defects 1-4 `skip-temporarily` with the issue link once it exists.

| # | Defect (openan-installation @ `e62e01e`, also present in `upstream/main` `f29c9f5`) | Affected cases |
| --- | --- | --- |
| 1 | The wizard with registry only reads the undefined `tags["frontend"]` and exits 1 (`containerized/online-install/configure.py:699`) | helm-components-001 |
| 2 | compose `install.sh --eval` cannot run: `log_info`/`log_warn`/`die` are not defined, `local admin_pass` sits outside a function, and `gen-secrets.sh` reads an undefined `$BUNDLE_DIR` (`offline-install-compose/scripts/install.sh:19,45`; `scripts/gen-secrets.sh:215`) | offline-compose-001, compose-db-001 (batch 5) |
| 3 | The offline K8s installer looks for the certificate tool at `<bundle>/../../tool/`, which does not exist in an extracted bundle (`offline-install/scripts/check-env.sh:20,113`; `scripts/install.sh:27,634`; `build/build-offline.sh:141`) | offline-k8s-001, security-002 and every offline K8s case that installs with the default HTTPS mode |
| 4 | With `HTTPS_ENABLED=false` registry-center still mounts the `tls-certs` volume, contrary to the QUICKSTART table (`offline-install/chart/templates/registry-center/deployment.yaml:119,143`) | security-004 (batch 5) |
| 5 | The registry-center and orchestration-center Deployments start together with the bundled database and gate nothing on it (their `initContainers` only prepare directories); both services exit with a storage error until the database is reachable (registry-center: `verify_storage_ready()` in `agent_registry/start.py`; orchestration-center: `initialize_storage()` in `orchestrate/start.py`), which costs each of them three CrashLoopBackOff restarts on a fresh install | testability-001 (allows up to 3 restarts for these two Pods and then requires unchanged counts for 120 s) |
| 6 | The online installer applies the IPAddressPool and L2Advertisement as soon as the MetalLB CRDs exist, before the validation webhook that serves them is Ready (`containerized/online-install/install.sh:409-421,458-478`; the MetalLB v0.16.1 webhooks use `failurePolicy: Fail`), so a fresh MetalLB install fails with a `failed calling webhook` InternalError from the API server and `install.sh` exits 1 | reliability-004 (reruns `install.sh` once after the `controller` Deployment is Ready) |

## Known Limitations

1. Profile-based auto-skip: cases not applicable to the current host profile are reported as **skipped** with an explicit reason (this is how one suite serves online-vm, cluster-ops, and offline-node hosts).
2. Wizard-driven Helm cases automate the interactive installer via `pexpect`; if the wizard flow changes, expectations must be updated (they assert printed banners and final resource states, not exact prompt text).
3. A failing case triggers the automatic cleanup; when a cleanup step itself fails the host stays dirty and must be reset by hand (`test-run.log` → `HOST LEFT DIRTY BY FAILED CLEANUP`).
4. `offline-node` hosts must pre-stage bundles (`OPENAN_INSTALL_OFFLINE_*`); the package does not build offline bundles itself (build-tooling cases are a later batch).
5. Offline-node cases invoke `sudo` and assume passwordless sudo (NOPASSWD) on the test hosts.
6. First-boot admin token flow: the OC rejects the first `POST /api/v1/auth/token` with the initial password (403 Password change required, no token issued). `utils/oc_auth.py` performs the documented web flow (`/api/orchestrate/rest/v1/orchestrate/auth/login` → `/auth/change-password` → token), derives the changed password as `<initial>1aA!`, and reports whether the forced-change branch was taken; both helm-online-001 and offline-compose-001 assert that it was.
7. The default frontend is `workflow-designer` (`OPENAN_INSTALL_FRONTEND_TYPE`, default `workflow-designer`; its image follows the orchestration tag). To test the portal frontend instead, set `OPENAN_INSTALL_FRONTEND_TYPE=portal` plus `OPENAN_INSTALL_PORTAL_TAG` (portal publishes only the `v1.0.0` tag, no `latest`/newer tags).
8. The portal `v1.0.0` nginx gateway does not proxy the Orchestration Center external API prefix `/api/v1/*`; the token endpoint is therefore called through `/api/orchestrate/api/v1/auth/token` (ingress → OC), and this deviation is recorded in the case table notes. This is a product gateway/version-alignment defect tracked against `openan-portal` / `orchestration-center`.
9. Agent registration (`DFX-reliability-001`) posts a minimal sample AgentCard fixture (`utils/agentcard.py`) with a `vendor_agent` bearer credential added to `openan-rc-credentials`; if the Registry Center changes its credential format or enforces JWS signatures, update the fixture accordingly.
