---
name: Feature Test Tracking
about: Track a feature's integration testing lifecycle (handover → plan review → TRR → FIT → report)
title: "[Feature Test] <feature>: <summary>"
labels: feature-test
---

## Description

<Feature overview and integration testing scope: what the feature delivers, FIT scope, and key scenarios; link the feature proposal if available>

## Basic Information

| Item | Value |
| ---- | ----- |
| Feature / Module (`feature.slug`) | `<feature>` |
| Milestone (`<YY>-<season>`) | `26-winter` |
| Feature WG / Test Owner | `<WG>` / `<Name>` |
| Maintainer | `<Name>` |

**Requirement links**: `<issue links, separated by semicolons>`

## Related PRs

- Test plan + case table (`docs/plans/<milestone>/`): <PR link>
- Automated FIT cases (`e2e/<feature>/`): <PR link>
- Test report (`docs/reports/<milestone>/`): <PR link>

## Progress Checklist

- [ ] Handover issue submitted (this issue)
- [ ] Test plan and case table merged into `docs/plans/<milestone>/`
- [ ] FIT automated cases merged into `e2e/<feature>/`
- [ ] Plan, cases, and code reviewed by the Integration Testing WG
- [ ] TRR passed (Test Checklist Chapter 1)
- [ ] FIT execution complete; self-test report delivered
- [ ] Test report merged into `docs/reports/<milestone>/`

## Notes

<risks, dependencies, schedule>
