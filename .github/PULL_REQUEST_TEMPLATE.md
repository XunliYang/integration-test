## Description

<What this PR delivers and why: test plan / case table / automated cases included, key design decisions, local run results>

## Type

- [ ] Test plan + case table
- [ ] Automated test code
- [ ] Test report
- [ ] Other

## Scope

- Feature / Module (`feature.slug`): `<feature>`
- Milestone: `<YY>-<season>` (e.g., `26-winter`)
- Cases: `<total>` (P0 `<n>` / P1 `<n>` / P2 `<n>`)

## Related

- Tracking issue: <link> (`Closes #<n>`)
- Related PRs: <links>

## Checklist

- [ ] Test plan follows [test-plan-template.md](docs/templates/test-plan-template.md)
- [ ] Case CSV follows [Test Case Table Field Description](docs/templates/testcases-template-fields.md) — 15 fixed columns, verbatim header
- [ ] Case IDs follow `FIT-<feature>-<topic>-<number>`; P0/P1 cases are 100% automatable with requirement links filled
- [ ] LLM-dependent cases use deterministic assertions (status code/structure/state, not generated text)
- [ ] Test code labels complete: `feature` / `environment` / `components` / `priority` / `execution`; no `sleep`, no order dependencies, explicit assertions, teardown cleanup
- [ ] New env vars added to `e2e/.env.template` and documented in README; no `.env`, credentials, IPs, or tokens committed
- [ ] Local self-test passed: `pytest e2e/<feature>/ -m "not slow"`
