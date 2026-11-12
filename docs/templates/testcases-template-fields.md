# Test Case Table Field Description

The OpenAN integration test case table uses a **fixed 16-column CSV** format: building on the industry-standard 14-column case table, it adds "Requirement Link" and "Component Deps" columns for requirement traceability, requirement coverage statistics, and component dependency declaration. **Columns must not be added or removed**; the header must be verbatim:

```csv
Milestone,Case Name,Case ID,Module,Component Deps,Requirement Link,Case Type,Priority,Precondition,Steps,Expected Result,Automatable,Automated Test,Dev Owner,Test Owner,Notes
```

## Field Filling Rules

| # | Field | Required | Rule | Example |
|---|------|------|---------|------|
| 1 | Milestone | Yes | Milestone in `<YY>-<season>` format (e.g., `26-winter`), matching the version directory under `docs/plans/` and consistent with the test plan | `26-winter` |
| 2 | Case Name | Yes | A verb-object business description stating "what to do + under what conditions" in one sentence, without a case ID prefix | `Register AgentCard and query it (with mTLS client identity)` |
| 3 | Case ID | Yes | Globally unique, wrapped in square brackets; FIT: `[FIT-<feature>-<topic>-<number>]`; SIT: `[SIT-<scenario>-<number>]` | `[FIT-registry-center-agentcard-001]` |
| 4 | Module | Yes | Identifier of the module under test, mapping to `feature.slug` (kebab-case, matching the feature directory name in the integration-test repository, e.g., an openan repository name or an in-repo module) | `registry-center`, `orchestration-center`, `a2a-t-sdk`, `openan-portal`, `openan-installation`, `system-integration` |
| 5 | Component Deps | Yes | Deployed OpenAN components the case depends on or interacts with (other than the module under test), multiple values separated by semicolons; sample/mock agents (e.g., `mockagent`) count when the case requires them running; `n/a` when only the module under test is involved. Feeds the `components` code label | `registry-center;mockagent` |
| 6 | Requirement Link | Required for P0/P1 | Issue link(s) of the corresponding requirement/feature, multiple links separated by semicolons; SIT scenario cases may link to a scenario epic issue. Used for the requirement traceability matrix and requirement coverage statistics | `https://github.com/project-openan/registry-center/issues/1` |
| 7 | Case Type | Yes | Allowed values: Functional Test / Exception Test / Protocol Test / Performance Test / Stress Test / Stability Test / Security Test / Compatibility Test / Deployment Test / System Test | `Functional Test` |
| 8 | Priority | Yes | `P0` (blocks the core path) / `P1` (major functionality) / `P2` (general scenarios) | `P0` |
| 9 | Precondition | Yes | Environment/data/dependency readiness; multiple items separated by semicolons | `Registry Center deployed via Helm with mTLS client certificate configured` |
| 10 | Steps | Yes | Numbered steps `1. ...\n2. ...` (wrap line breaks inside a cell in CSV double quotes); one action per step | `1. Log in to the Orchestration Center to get a session\n2. Submit a natural-language intent...` |
| 11 | Expected Result | Yes | Deterministic assertions corresponding to each step; **LLM-related cases use deterministic assertions** (status codes/structure/status fields), never directly asserting model-generated text | `Execution completes with status complete` |
| 12 | Automatable | Yes | `Yes` / `No`; P0/P1 must be `Yes` | `Yes` |
| 13 | Automated Test | Backfilled after automation | Location in the automation code: `test_xxx.py::test_func` or `test-xxx.spec.ts` | `test_agentcard.py::test_register_agent_success` |
| 14 | Dev Owner | Yes | Development owner of the module | `<Name>` |
| 15 | Test Owner | Yes | Owner of case design and execution | `<Name>` |
| 16 | Notes | As needed | Fault injection method (network cut / wrong credentials / unreachable dependency), data source, related defect issues, etc. | `Fault injection: LLM endpoint unreachable` |

## Mapping to Code Labels

The CSV does not carry execution labels; the following dimensions are expressed in the test code as pytest markers / Ginkgo Labels (required on every case):

| CSV Field | Code Label | Description |
|----------|----------|------|
| Case ID | `Label("FIT-registry-center-agentcard-001")` | Ensures `--label-filter` can locate a single case |
| Milestone | `Label("26-winter")` | |
| Priority | `Label("P0")` | |
| Module | `feature.slug` (directory name) | |
| Component Deps | `components` label (framework §6.4) | Case-level required-components dimension |
| Case Name | `It` / `test_` description body | Natural language, without a case ID prefix |
| Precondition | `BeforeEach` / `BeforeAll` (fixture) | |
| Steps | `By("Step N")` + implementation | |
| Expected Result | `Expect` assertions | Omitting assertions is prohibited |
| Notes | Fault injection implementation (network cut / wrong credentials / stubs) | |
| Requirement Link | Not mapped to code labels | Used for the requirement traceability matrix and requirement coverage statistics (test report) |

Environment/execution layer labels (`environment`, `execution=smoke|full|slow`, `skip-temporarily`) are additionally annotated by the automation code; the `components` label is derived from the Component Deps column.

## Quality Requirements

- Every CSV case maps to at least one `It` / `test`
- One assertion per step; expected results must not be empty
- P0/P1 cases must have the requirement link filled in; requirement coverage = (number of approved requirements with corresponding executed cases) / (number of approved requirements)
- Environment variables are externalized (reference `.env.template`); hardcoding secrets or intranet addresses is prohibited
- The CSV is saved in UTF-8 encoding; cells containing line breaks must be wrapped in double quotes
