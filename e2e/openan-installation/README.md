# openan-installation E2E Tests

This package automates the FIT/DFX test cases for the OpenAN system-level installation and deployment tooling (`openan-installation`), covering the five installation lines, the installer configuration contract, and the installer's non-functional design capabilities. Backend framework: **pytest** (repo standard, Framework §7.1); all cases run shell/kubectl/docker commands **locally on the target test host**.

> Scope boundary: this package covers the installer itself (install/uninstall/config/build lines). Business-level FIT cases of deployed components (registry-center, orchestration-center APIs) live in their own packages; this package only uses those services as deployment-verification vehicles (health endpoints, token API), per the FIT/DFX attribution criteria.

## Test Scope

Case source: [`docs/plans/26-winter/testcases-openan-installation.csv`](../../docs/plans/26-winter/testcases-openan-installation.csv) (46 reviewed cases). **Batch 1 delivers all 12 P0 cases** (all labeled `execution=smoke`); P1/P2 cases follow in later batches.

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

### Later batches

The remaining 34 reviewed cases (P1/P2: config matrix, db-type, offline variants, diagnosability, serviceability 002/004/005/006, reliability 002/003/004, performance/HPA, security 001/003/004/005, compatibility, build tooling) are scheduled in subsequent deliveries; their IDs and statuses will be appended here as batches land.

### Files

| File | Covers | Responsibility |
| --- | --- | --- |
| `conftest.py` | — | Env loading (`e2e/.env`), marker registration, machine-profile gate |
| `utils/env.py` | — | `.env` parsing + typed accessors for `OPENAN_INSTALL_*` |
| `utils/shell.py` | — | Local command executor (subprocess, timeout, output capture, evidence saving, cookie-jar curl), kubectl helpers, wait/retry |
| `utils/helm_install.py` | — | Online Helm wizard driver (pexpect answers, install/uninstall, pod/platform helpers) |
| `utils/oc_auth.py` | — | OC admin token flow incl. first-boot forced password change (403 → login → change-password → token) |
| `utils/agentcard.py` | — | Minimal sample AgentCard fixture for registry data-persistence verification |
| `test_binary_install.py` | FIT binary-install-001, binary-components-001 | Binary one-click install main paths |
| `test_binary_serviceability.py` | DFX serviceability-001, serviceability-003 | Idempotent re-run; forced uninstall |
| `test_llm_config.py` | FIT llm-config-001 | LLM configuration validation and write |
| `test_helm_online.py` | FIT helm-online-001, helm-components-001 | Online Helm wizard installs (pexpect-driven TTY) |
| `test_helm_probes.py` | DFX testability-001 | Probe contract rendering and pod readiness |
| `test_data_persistence.py` | DFX reliability-001 | Pod recreation data survival |
| `test_offline_k8s.py` | FIT offline-k8s-001 | Offline K8s bundle install |
| `test_offline_compose.py` | FIT offline-compose-001 | Offline compose stack install |
| `test_offline_https.py` | DFX security-002 | Offline in-cluster HTTPS with generated CA |

## Directory Structure

```text
e2e/openan-installation/
├── README.md                     # this file
├── conftest.py                   # env load, markers, profile gate (session fixture)
├── utils/
│   ├── env.py                    # .env contract accessors
│   ├── shell.py                  # local shell/curl/kubectl executor + wait/retry
│   ├── helm_install.py           # online Helm wizard driver (pexpect)
│   ├── oc_auth.py                # admin token flow with first-boot password change
│   └── agentcard.py              # sample AgentCard fixture
├── test_binary_install.py
├── test_binary_serviceability.py
├── test_llm_config.py
├── test_helm_online.py
├── test_helm_probes.py
├── test_data_persistence.py
├── test_offline_k8s.py
├── test_offline_compose.py
└── test_offline_https.py
```

## Suite Lifecycle

Unlike service packages, **there is no suite-level install/uninstall**: every case is self-contained and performs its own install → verify → uninstall cycle (exactly as written in the case CSV steps).

- `install_env` (session, autouse): loads `e2e/.env`, validates `OPENAN_INSTALL_MACHINE_PROFILE` and `OPENAN_INSTALL_REPO_PATH`, fails fast with a clear message on a malformed contract.
- Per-case: machine-profile gate → install under test → assertions on results → cleanup (uninstall) as the final step of the case.
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
| Compose | v2.20+ | offline-node (compose) |
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
# One-click binary scripts subdirectory (relative to repo path)
OPENAN_INSTALL_BINARY_SUBDIR=binary/one-click
# LLM endpoint for configure_llm.sh / wizard connectivity validation
OPENAN_INSTALL_LLM_MODEL=
OPENAN_INSTALL_LLM_API_URL=
OPENAN_INSTALL_LLM_API_KEY=
# Online Helm line
OPENAN_INSTALL_IMAGE_TAG=
OPENAN_INSTALL_ADMIN_PASSWORD=
OPENAN_INSTALL_DB_PASSWORD=
# Offline lines (bundle paths; empty = the corresponding cases skip)
OPENAN_INSTALL_OFFLINE_K8S_BUNDLE=
OPENAN_INSTALL_OFFLINE_COMPOSE_BUNDLE=
OPENAN_INSTALL_OFFLINE_CONFIG_ENV=
```

| Variable | Used by | Missing behavior |
| --- | --- | --- |
| `OPENAN_INSTALL_MACHINE_PROFILE` | all cases | whole package skips with reason `profile not set` |
| `OPENAN_INSTALL_REPO_PATH` | online-vm / cluster-ops cases | session fixture fails fast |
| `OPENAN_INSTALL_LLM_*` | llm-config-001, helm wizard cases | cases skip (`LLM endpoint not configured`) |
| `OPENAN_INSTALL_IMAGE_TAG` | helm-online-001, helm-components-001 | cases skip (`image tag not set`) |
| `OPENAN_INSTALL_ADMIN_PASSWORD` / `_DB_PASSWORD` | helm wizard cases | cases skip (`wizard secrets not set`) |
| `OPENAN_INSTALL_OFFLINE_K8S_BUNDLE` | offline-k8s-001 | case skips on `offline-node` profile |
| `OPENAN_INSTALL_OFFLINE_COMPOSE_BUNDLE` | offline-compose-001 | case skips on `offline-node` profile |
| `OPENAN_INSTALL_OFFLINE_CONFIG_ENV` | security-002 | case skips on `offline-node` profile |

Placeholders in the case table (`<TAG>`, `<MODEL>`, `<KEY>`, …) map one-to-one onto these variables; no value is hardcoded in test code.

## How to Run

From the repository root:

```bash
cp e2e/.env.template e2e/.env   # fill real values on the target host
cd e2e
pytest openan-installation/ -v                       # all cases applicable to this host profile
pytest openan-installation/ -m smoke -v               # batch-1 P0 set
pytest openan-installation/test_binary_install.py -v   # single file
pytest openan-installation/ -k binary_install_001 -v  # single case
```

Timeout guidance: single install cases take 3–10 minutes; pass `-m smoke` in PR gates; do not add `xdist`. Failure evidence (command output) is captured to `EVIDENCE_DIR` (default `evidence/`, git-ignored).

## Known Limitations

1. Profile-based auto-skip: cases not applicable to the current host profile are reported as **skipped** with an explicit reason (this is how one suite serves online-vm, cluster-ops, and offline-node hosts).
2. Wizard-driven Helm cases automate the interactive installer via `pexpect`; if the wizard flow changes, expectations must be updated (they assert printed banners and final resource states, not exact prompt text).
3. A case that fails mid-way may leave artifacts; the dedicated uninstall cases and a manual `./uninstall.sh --force` recover the host. A post-failure forced cleanup is deliberately not automated to avoid masking real uninstall defects.
4. `offline-node` hosts must pre-stage bundles (`OPENAN_INSTALL_OFFLINE_*`); the package does not build offline bundles itself (build-tooling cases are a later batch).
5. Agent registration (`DFX-reliability-001`) posts a minimal sample AgentCard fixture (`utils/agentcard.py`) with optional mTLS credentials from `REGISTRY_CLIENT_CERT/KEY`; if the Registry Center enforces JWS signatures or a stricter schema in this release, update the fixture accordingly.
6. Offline-node cases invoke `sudo` and assume passwordless sudo (NOPASSWD) on the test hosts.
7. LLM secrets (`OPENAN_INSTALL_LLM_API_KEY`, `OPENAN_INSTALL_ADMIN_PASSWORD`, `OPENAN_INSTALL_DB_PASSWORD`) live only in `e2e/.env` (never committed); interactive transcripts are saved under `EVIDENCE_DIR` and must be reviewed for accidental secret leakage before archiving evidence.
8. First-boot admin token flow: the OC rejects the first `POST /api/v1/auth/token` with the initial password (403 Password change required, no token issued). `utils/oc_auth.py` performs the documented web flow (`/api/orchestrate/rest/v1/orchestrate/auth/login` → `/auth/change-password` → token) and derives the changed password as `<initial>1aA!`; on re-runs against kept data both passwords are tried.
9. Compose `--eval` mode auto-generates the admin password; the compose case reads `OC_ADMIN_INITIAL_PASSWORD` from the generated runtime env files (requires sudo) instead of `OPENAN_INSTALL_ADMIN_PASSWORD`.
10. The default frontend is `workflow-designer` (`OPENAN_INSTALL_FRONTEND_TYPE`, default `workflow-designer`; its image follows the orchestration tag). To test the portal frontend instead, set `OPENAN_INSTALL_FRONTEND_TYPE=portal` plus `OPENAN_INSTALL_PORTAL_TAG` (portal publishes only the `v1.0.0` tag, no `latest`/newer tags).
11. The portal `v1.0.0` nginx gateway does not proxy the Orchestration Center external API prefix `/api/v1/*`; `get_admin_token`'s final `POST /api/v1/auth/token` therefore returns 405 through the portal entry, while the same call succeeds directly against the OC service. This is a product gateway/version-alignment defect tracked against `openan-portal` / `orchestration-center`.
12. `openan-installation` defect that blocks a first run: `containerized/online-install/install.sh` is committed without the executable bit (`100644`; run `chmod +x`).
