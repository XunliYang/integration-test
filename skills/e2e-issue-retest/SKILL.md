---
name: e2e-issue-retest
description: When a GitHub bug Issue carries the status/pending-test label, rerun the original failed case(s) per the reproduction command in the Issue; reuse the e2e-test-runner pre-check/execution/cleanup conventions, stream logs with immediate first-failure feedback; on success produce a pass conclusion, on failure produce the failed-case identifier, evidence paths, and E2E source path aligned with e2e-failure-analyzer, and generate a GitHub Issue status/comment write-back draft (write-back requires user authorization)
---

# e2e-issue-retest

Covers the "pending-test retest" stage of the defect-closure workflow: after a source-code bug Issue is fixed and labeled pending-test, rerun the original E2E case(s) against the fixed code. Success produces a conclusion that the Issue can be closed; failure is reported immediately and handed to failure analysis. This skill does **not modify code, does not determine root cause, and does not write back to the Issue on its own**.

Execution is delegated to `skills/e2e-test-runner/SKILL.md` (four phases and language dispatch); failure evidence is aligned with the input requirements of `skills/e2e-failure-analyzer/SKILL.md`.

## Trigger Conditions

The user asks for a pending-test retest, an Issue re-run, verification of a source fix, or runs /e2e-issue-retest.

## Status Convention (openAN Unified)

GitHub Issues have only open/closed states; "pending test" is expressed via the label `status/pending-test`:

- Entering pending test: after the fix PR merges, a human or a process applies this label.
- Retest passed (PASSED): suggest removing the `status/pending-test` label + closing the issue + commenting the verification evidence.
- Retest failed (FAILED): keep the label, keep the issue open + comment the failure evidence.

This convention is the openAN skill set's unified status label convention; status labels in github-issue-creator and other skills must reuse the same `status/*` naming — do not invent separate enums.

## Capability Boundaries

- Handles only **open bug Issues carrying the `status/pending-test` label**.
- Reruns only the reproduction command / failed cases from the Issue; running the full suite without scope is prohibited.
- Streams logs in real time; the first failure is reported immediately (case name, error summary, artifact path); the cleanup phase still runs.
- Modifies no source or test code; does not call GitHub MCP comment/close/edit APIs (write-back produces a draft only; execution requires explicit user authorization).

## Inputs

| Input | Form | Required | Notes |
| --- | --- | --- | --- |
| Issue identifier | GitHub URL or `owner/repo#number` | Yes | e.g. `https://github.com/project-openan/registry-center/issues/42` |
| Issue data | GitHub MCP `get_issue` | Yes | Reads `state` / `labels` / `title` / `body`; when MCP is unavailable, ask the user to paste a snapshot (format: `assets/issue-snapshot.example.json`) |
| E2E source path | `--project-root` or a path in the Issue body | Yes | Root of the fixed repo under test / test repo |
| Reproduction command | "Reproduction Steps" or a command in the body, or explicit failed-case identifiers | Yes | Prefer the minimal repro command from the Issue (pytest `-k` / file level, JUnit5 `-Dtest`, Vitest/Playwright `-g`, bats `--filter`) |

### Extracted from the Issue Body

Prefer fields produced by e2e-failure-analyzer / github-issue-creator:

- `Reproduction Steps` / `command` (minimal repro command)
- `Test case ID` / `caseId` / failed case name (`testName`)
- `Log/report path` / `testFile` / failed test file
- `E2E source path (test project root)`

### Input Gates (any one holds -> BLOCKED, do not run tests)

1. Cannot parse `owner/repo#issue_number`.
2. The Issue is not open, or its labels do not include `status/pending-test`.
3. `project_root` is missing.
4. Neither a reproduction command nor an explicit failed-case identifier is available.
5. The command contains a plaintext token or password.

## Execution Flow

1. Parse the Issue identifier; when GitHub MCP is available, call `get_issue` and persist the result as `issue.json` (fields: `owner,repo,issue_number,url,title,state,labels,body`); when unavailable, ask the user to paste a snapshot.
2. Verify the Issue is open and carries the `status/pending-test` label; otherwise go BLOCKED and list the missing items.
3. Extract the reproduction command and case identifiers from the body and locate `project_root`; declare the minimal command to be executed (equivalent to a dry run), then actually execute it.
4. Execute per the e2e-test-runner four-phase convention: pre-check (toolchain) -> preparation (environment variables / service health) -> execution (streamed logs, first failure reported immediately) -> cleanup (only processes and containers started by this run). Run only the extracted minimal scope; do not expand it.
5. Produce the verdict and artifacts; on FAILED, ensure the evidence covers the analyzer's three elements (failed case identifier, failure evidence source, E2E source path) so it can be handed directly to e2e-failure-analyzer.

## Outputs

Artifacts land under `<project_root>/.test-output/<timestamp>/`, following the e2e-test-runner phase-4 archive convention. If this run already produced a `.test-output/<timestamp>/` directory (JUnit XML, logs), place the retest conclusion in the same directory so `logPath` references stay consistent.

| Artifact | When | Purpose |
| --- | --- | --- |
| `latest.json` | Every run | Structured conclusion, containing `verdict`, the verification command, exitCode, failed cases, and evidence paths |
| `retest-result.md` | Every run | Conversation- / human-readable result |
| `github-issue-update-input.md` | Every run | Write-back draft, executed only after user authorization |

`verdict`:

| Value | Meaning | Write-back suggestion |
| --- | --- | --- |
| `PASSED` | The original failed case(s) now pass | Remove the `status/pending-test` label + close the issue + comment (with the verification command and evidence paths) |
| `FAILED` | The retest still fails | Keep open + comment (with the failed case, 3-8 lines of key logs, and evidence paths); hand the evidence to `e2e-failure-analyzer` |
| `BLOCKED` | The pending-test gate is not satisfied | Do not run tests; explain the missing items to the user |

## Conversation Delivery Format

```markdown
## E2E Pending-Test Retest Result
- Verdict: PASSED / FAILED / BLOCKED
- Issue: owner/repo#number (open + status/pending-test)
- Verification command:
- E2E source path:
- Failed case identifier: (FAILED only)
- Failure evidence source: (FAILED only)
- Failure-analysis input: the three elements handed to e2e-failure-analyzer (FAILED only)
- Write-back suggestion: remove label + close | keep open + comment
```

On failure, attach only 3-8 lines of key logs; pasting large log dumps is prohibited.

## Quality Self-Check

- [ ] Confirmed the Issue is open and carries the `status/pending-test` label
- [ ] Ran only the Issue's reproduction command or the explicit failed-case scope; did not run unrelated full suites
- [ ] Declared the minimal command to the user before executing
- [ ] On failure, reported immediately; the evidence three elements can be handed directly to e2e-failure-analyzer
- [ ] Generated the write-back draft and did not comment/close/edit the Issue without authorization
