# OpenAN SIT Scenario Inventory

> *Version: v0.1 (Draft)*
> *Maintained by: OpenAN Integration Testing Working Group*
> *Language: English*
> *Status: scenario baseline only - per-scenario SIT specifications are NOT defined in this document yet.*

---

## 1. Purpose

This document enumerates the distinct application scenarios for System Integration Testing (SIT), derived from the three published OpenAN best-practice cases. It serves as the agreed baseline for writing per-scenario SIT specifications in subsequent work.

Sources (https://openan.dev/best-practices.html):

| Case | Title | URL |
| --- | --- | --- |
| Case 1 | Home Broadband Complaint Handling (multi-agent example) | https://openan.dev/best-practices/usecase.html |
| Case 2 | China Mobile Henan: From Operations Automation to E2E Collaborative Autonomy | https://openan.dev/best-practices/henan-mobile-openan-usecase.html |
| Case 3 | China Mobile Guangdong: A2A-T Cross-City SPN Dedicated-Line Complaint Handling | https://openan.dev/best-practices/guangdong-mobile-a2at-usecase.html |

## 2. Scenario Splitting Criterion

A SIT scenario is defined by the combination of:

1. **Closed-loop scope** under test (e.g., diagnosis only vs. diagnosis + authorized repair + verification + closure);
2. **Integration topology** (agent layers, deployment tiers, single-site vs. cross-site);
3. **Protocol capability set** exercised (basic registration/orchestration/task flows vs. Negotiation-T / Authorization-T / Notification-T).

Workflow branches and sub-flows inside one scenario (e.g., complaint-category routing, diagnosis sub-flow vs. restoration sub-flow) are **scenario variants**, not separate scenarios. This criterion is applied uniformly to all cases.

## 3. Scenario Inventory (5 scenarios)

| # | Scenario | Slug (for `SIT-<scenario>-<number>`) | Source | Type | Specification |
| --- | --- | --- | --- | --- | --- |
| S1 | Home broadband complaint handling | `complaint-handling` | Case 1 (branches A + B merged) | Fault diagnosis, fixed workflow | [Draft v0.1](sit-specs/complaint-handling.md) |
| S2 | Mobile cross-domain collaborative complaint handling | `cross-domain-complaint` | Case 2, Practice 1 | Fault diagnosis, dynamic negotiation | [Draft v0.1](sit-specs/cross-domain-complaint.md) |
| S3 | Intent-driven dynamic energy saving (electricity-cost optimization) | `intent-energy-saving` | Case 2, Practice 2 | Optimization / control closed loop | [Draft v0.1](sit-specs/intent-energy-saving.md) |
| S4 | SPN dedicated-line complaint - diagnosis only (single city, two layers) | `spn-line-diagnosis` | Case 3, Phase 1 | Fault diagnosis, basic protocol capabilities | [Draft v0.1](sit-specs/spn-line-diagnosis.md) |
| S5 | SPN dedicated-line complaint - full process (cross city, three layers) | `spn-line-full-process` | Case 3, Phase 2 | Diagnosis + restoration + closure, advanced protocol capabilities | Pending |

Slug alignment: S1 reuses the existing `complaint-handling` slug already present in `docs/templates/testcases-template.csv` (`[SIT-complaint-handling-001]`).

### S1 - Home broadband complaint handling

- **Closed-loop scope**: intent capture at call center -> workflow recall (Orchestration Center) -> agent card retrieval (Registry Center) -> multi-agent A2A-T diagnosis -> resolution or escalation to NOC human experts with full diagnostic context.
- **Topology**: one complaint-handling agent + Registry Center + Orchestration Center + three domain agents per branch (Customer Care plus Billing / CDN / Vendor FAN).
- **Protocol capabilities**: registration, agent discovery, workflow recall, basic A2A-T task collaboration.
- **Variants**:
  - Branch A (outage / billing): trigger "no internet"; agents Customer Care, Billing, Vendor 1 FAN; path account status -> billing blocks -> physical-layer diagnostic.
  - Branch B (streaming / speed degraded): trigger "YouTube/Netflix slow"; agents Customer Care, CDN, Vendor 2 FAN; path service quality check -> CDN node routing -> access-network congestion.
  - Autonomous closure vs. expert handoff (human in the loop).
- **Why one scenario, not two**: branches A and B share identical closed-loop scope, topology, and protocol capability set; they differ only in workflow routing.

### S2 - Mobile cross-domain collaborative complaint handling

- **Closed-loop scope**: 10086 call center + EOMS process center + provincial smart-recognition agent -> autonomous negotiation and joint fault location with cross-vendor domain agents -> end-to-end automated closed loop.
- **Topology**: group-province two-tier deployment (group-level MaaS / AI platform hosts Registry Center and Orchestration Center; province builds the complaint platform and recognition agent); four domain agent types: wireless optimization, wireless fault, core network fault, SPN fault.
- **Protocol capabilities**: registration, orchestration, plus dynamic self-negotiation (generalization to unknown issues, not only pre-coded flows).
- **Variants**: different fault-domain combinations; known workflow vs. dynamically negotiated collaboration; group-province tiering.

### S3 - Intent-driven dynamic energy saving

- **Closed-loop scope**: intent (electricity-cost optimization under dynamic time-of-use tariffs, not raw energy saving) -> data perception -> value decision -> orchestration scheduling -> network-element execution -> effect evaluation.
- **Topology**: three-tier architecture; cross-vendor collaboration with a wireless network agent (Huawei) in the pilot.
- **Protocol capabilities**: intent-driven orchestration and cross-vendor agent collaboration; involves network-element write operations and balancing energy cost against user experience.
- **Variants**: tariff-policy changes; different decision outcomes; effect-evaluation feedback loop.
- **Note**: the only non-complaint scenario; the only optimization/control-type closed loop in the inventory.

### S4 - SPN dedicated-line complaint, diagnosis only (Phase 1)

- **Closed-loop scope**: complaint via 10086 -> EMOS -> WAIMO -> transmission workbench agent -> SPN domain agent; end-to-end automatic diagnosis of a live dedicated line; diagnosis conclusion confirmed by human experts. No repair or closure in scope.
- **Topology**: two-layer agent collaboration, single city; Registry Center + Orchestration Center + transmission workbench + one SPN domain agent (NCE).
- **Protocol capabilities**: basic capabilities only - registration, orchestration, basic business flows.
- **Variants**: two validated integration approaches - (a) workbench directly invokes the SPN agent A2A-T interface; (b) orchestration-center-driven invocation.
- **Reference result**: live-line root causes identified (far-end abnormal transmit power from optical-module fault, mismatched optical-module types, incorrect attenuation setting) with local transmit power confirmed normal.

### S5 - SPN dedicated-line complaint, full process (Phase 2)

- **Closed-loop scope**: full cross-city complaint process - service restoration, fault location, automatic repair, automatic closure; diagnosis results written back to the process center; after restoration, performance indicators verified and service-recovery notification reported.
- **Topology**: three-layer, multi-vendor collaboration - WAIMO fault center agent (Yiyang) -> transmission workbench agent (Kaitong) -> two SPN domain agents (Huawei); all registered with Registry Center; workflows composed by Orchestration Center (e.g., generate diagnosis message, diagnose in parallel with two SPN agents, summarize results).
- **Protocol capabilities**: advanced capabilities - Negotiation-T, Authorization-T, Notification-T - on top of basic capabilities.
- **Variants (sub-flows within one scenario)**:
  - Fault diagnosis flow: ticket grab from process center -> dispatch to workbench and OMC -> three-agent coordination -> results written back.
  - Service restoration flow: OMC supports restoration -> workbench authorization -> restoration -> OMC notification -> workbench verifies performance recovery -> recovery notification to WAIMO fault center.
- **Why separate from S4**: closed-loop scope, topology (two vs. three layers, single vs. cross city, vendor count), and protocol capability set all differ; S4 is a capability-stage predecessor, not a branch of S5.

## 4. Cross-Cutting Variant Dimensions

These are not independent scenarios; they are variant axes to be covered inside each scenario specification:

| Dimension | Values observed in the cases |
| --- | --- |
| Human in the loop | Fully autonomous closure vs. escalation to NOC / human expert confirmation (Case 1 expert handoff; Case 3 expert-confirmed diagnosis) |
| Integration approach | Direct agent-to-agent A2A-T invocation vs. Orchestration-Center-driven invocation (Case 3 Phase 1 validated both) |
| Collaboration mode | Fixed workflow recall vs. dynamic autonomous negotiation (Case 1 vs. Cases 2/3) |
| Deployment topology | Single-tier centralized vs. group-province two-tier (Case 2) vs. cross-city multi-region (Case 3) |
| Vendor heterogeneity | Single-vendor example agents (Case 1) vs. cross-vendor live network (Case 2: Huawei; Case 3: Yiyang / Kaitong / Huawei) |
| Operation risk level | Read-only diagnosis (S1, S2, S4) vs. authorized network write operations and restoration (S3, S5) |

## 5. Scope Boundary and Next Steps

- This document fixes **what** the SIT scenarios are and **why** they are split this way. Per-scenario specifications live in `docs/sit-specs/<slug>.md`, one file per scenario, each covering its variants and the applicable cross-cutting dimensions, consistent with `docs/OpenAN Integration Testing Process and Framework.md` (naming §6.1, case rules §6.3, tags §6.4, env contract §6.6, gates §8).
- Specification status is tracked in the inventory table above (§3).
- Case IDs produced later will follow `[SIT-<slug>-<number>]` using the slugs in §3.