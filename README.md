# integration-test

The OpenAN integration-test repository serves as the central hub for end-to-end integration testing, housing test plans, execution cases, evaluation reports, and domain-specific testing skills. The governing baseline is the OpenAN Integration Testing Process and Framework (see `docs/OpenAN Integration Testing Process and Framework.md`).

## Directory Structure

```
integration-test/
├── e2e/                              # Backend integration tests (pytest)
│   ├── framework/                    # Shared capabilities: K8s client, env loading, utilities
│   ├── <feature>/                    # One directory per feature (e.g., registry-center, orchestration-center)
│   │   ├── test_<feature>_api.py
│   │   ├── test_<topic>.py
│   │   ├── system-integration/       # System-level integration cases for this feature
│   │   │   └── test_<scenario>.py
│   │   └── utils/  static/
│   └── .env.template                 # Environment variable contract template (only the template is kept in the repo; committing .env is prohibited)
├── e2e-frontend/                     # Frontend UI automation (Playwright, optional)
├── docs/
│   ├── templates/                    # Test plan / case table / test report templates
│   ├── plans/<version>/              # Test plan archive
│   └── reports/<version>/            # Test report archive
└── README.md
```

## Case Naming and Labels

- Case ID: `FIT-<feature>-<topic>-<number>` (e.g., `FIT-orchestration-workflow-001`); SIT cases: `SIT-<scenario>-<number>`
- Test files: `test_<topic>.py`; test functions: `test_<action>_<expected_result>`; Playwright: `test-<scenario>.spec.ts`
- Label dimensions (pytest markers, required on every case):

| Dimension | Examples | Description |
|------|------|------|
| feature | `registry-center`, `orchestration-center` | Feature identifier |
| environment | `with-workload-cluster`, `online`, `offline` | CI environment filtering |
| components | `registry-center`, `openan-portal` | Required components |
| priority | `P0`, `P1`, `P2` | Case priority |
| execution | `smoke`, `full`, `slow` | PR CI runs `smoke`; Daily runs `full` |
| skip | `skip-temporarily` | Temporary skip; must reference an issue link |

## How to Run

```bash
cp e2e/.env.template e2e/.env   # Fill in real environment values
cd e2e && pytest <feature>/ -m "not slow"
```

CI trigger strategy: PR runs `smoke` for affected feature directories; Daily runs the full `full` set + SIT smoke; RC triggers full FIT+SIT and starts the long-duration stability test; pre-release reruns all P0/P1 and SIT on the RC.

## Security Red Lines

- The repository keeps only `.env.template`; **committing `.env`, real credentials, IPs, or tokens is strictly prohibited**
- If Code Review finds hardcoded secrets or intranet addresses, the merge is rejected
