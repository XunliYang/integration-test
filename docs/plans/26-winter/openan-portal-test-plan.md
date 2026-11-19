# openan-portal (Unified Web Framework, Pluggable Portal) Test Plan

> Version: v0.2 | Date: 2026-11-19 | Author: Zhoujie628 | Review status: Pending review
> Related feature proposal: [orchestration-center#77](https://github.com/project-openan/orchestration-center/issues/77) | Tracking issue: [integration-test#12](https://github.com/project-openan/integration-test/issues/12) | Version milestone: `26-winter`
> Component repository: `openan-portal` (npm workspace root package name `openan-website`)
> Archive path: `docs/plans/26-winter/` (merged via PR after review approval)

---

## 1. Overview

### 1.1 Purpose

Verify that `openan-portal` delivers the unified, pluggable web framework committed for the `26-winter` release and meets the Feature Integration Test (FIT) entry and exit criteria. The plan covers three integration surfaces: the portal shell itself (navigation, authentication, theming, i18n), the mounting of the independent Registry Center and Orchestration Center frontends as sub-applications, and the plugin registration mechanism plus its extension points (including onboarding a sample extension such as Skill Center).

The portal is the only user-facing entry of the release, so a defect here is visible as a release-level failure even when the backend components are healthy. Every case therefore asserts the integration contract between the shell and a deployed component (HTTP status of the API the page calls, URL/route resolution, DOM readiness of the mounted sub-app, session behavior), not the internal correctness of a sub-application.

### 1.2 Scope

**In scope** (aligned with the integration testing boundaries in Framework §5.2):

- Portal shell boot, access authentication (`/auth/check`, `/auth/login`, `/auth/logout`), route guard behavior on deep links, and the admin-only `/users` route
- Theme and language state as framework-level capabilities, including persistence across reloads and propagation to mounted sub-applications
- Sub-application mounting: the Registry Center frontend at `/registry` and the Orchestration Center frontend at `/orchestration`, their data paths through the portal's API gateway, deep-link/bookmark behavior, and one shared session across sub-apps
- Plugin registration mechanism: manifest contract, navigation generation from manifest `menu[].order`, grouped menus, runtime enable/disable, plugin failure isolation, and the release-time artifact validation gate (`npm run plugins:validate`)
- Onboarding a sample extension plugin (Skill Center source plugin) and its iframe mount + language-forwarding contract

**Out of scope**:

- Boundary conditions of individual shell functions (covered by `openan-portal` unit tests under `tests/`, Vitest)
- Pure UI layout and styling (no assertions on colors, spacing, or animation; Framework §5.2 excludes it)
- Business flows inside the sub-applications (workflow authoring/execution, agent registration review) — owned by the `registry-center` and `orchestration-center` FIT tables
- LLM-dependent behavior; no case asserts model-generated text
- Large-scale performance, long-duration stability and security testing (specialized test plans)

### 1.3 References

| Document | Link/Path |
|------|----------|
| OpenAN Integration Testing Process and Framework | `docs/OpenAN Integration Testing Process and Framework.md` |
| OpenAN Test Checklist | `docs/openan-test-checklist.md` |
| Tracking issue (requirement link of every case) | [integration-test#12](https://github.com/project-openan/integration-test/issues/12) |
| Upstream requirement this feature implements | [orchestration-center#77](https://github.com/project-openan/orchestration-center/issues/77) |
| Portal framework and plugin spec | `openan-portal/README.md` (`## Plugin Spec`, `### Manifest Fields`, `## Consumer Repo Integration`, `## Issue #77 Compliance`) |
| Portal deployment contract | `openan-portal/default.conf.template`, `openan-portal/15-openan-backends.envsh`, `openan-portal/scripts/README-DEPLOY-EN.md` |
| Plugin artifact / release gate | `openan-portal/scripts/plugin-artifacts.mjs`, `openan-portal/portal/bundled-plugins.json`, `openan-portal/plugins/plugin-overrides.json` |
| Registry Center sub-app manifest | `registry-center/registry-center-web/plugin.manifest.js`, `registry-center/registry-center-web/vite.bundle.config.js` |
| Orchestration Center sub-app manifest | `orchestration-center/workflow-designer/plugin.manifest.js`, `orchestration-center/workflow-designer/vite.bundle.config.js` |
| Case table | [`testcases-openan-portal.csv`](testcases-openan-portal.csv) |
| Release deployment of the portal image | `openan-installation/containerized/build/portal/README.md` (built from the release artifact `openan-portal-dist.tar.gz` = `index.html` + `assets/` + `plugins/`) |

**Naming alias (traceability to issue #12).** Issue #12 declares `feature.slug` = `web-portal`, but the implementing repository and the module directory in this repository are `openan-portal`. This plan, the CSV `Module` column, and the case IDs therefore use `openan-portal` (`FIT-openan-portal-<topic>-<NNN>`). The mapping is one-to-one:

| Issue #12 field | Value in issue #12 | Value used here | Note |
|---|---|---|---|
| `feature.slug` | `web-portal` | `openan-portal` | Module directory and repository name; case IDs follow the module value |
| Repository to create | `web-portal` (not yet created at issue handover) | `openan-portal` | The framework shell, the SDK, the plugin directory and the deployment templates all live in `openan-portal` |
| Milestone | `26-winter` | `26-winter` | unchanged |
| Requirement link per case | — | `https://github.com/project-openan/orchestration-center/issues/77;https://github.com/project-openan/integration-test/issues/12` | identical in all 19 rows; component requirement issue first |

---

## 2. Objects Under Test

| Component | Repository | Version/Build | Test Layer | Notes |
|------|------|----------|----------|------|
| Portal shell (`web-portal` alias) | `openan-portal` (workspace package `openan-website`, version `1.1.0`) | `<tag/image digest>` | FIT (UI) | `PortalApp` shell: routing, auth, theme, i18n, dynamic header, plugin loader, error boundaries |
| Portal SDK | `openan-portal/packages/portal-sdk` | workspace `file:` link | FIT (contract) | `validateManifest` / `validateManifestMetadata`, `loadEnabledPlugins`, `withPluginDeadline` (default plugin deadline 15 s), `PortalContext` |
| Registry Center sub-app | `registry-center` → `registry-center-web` (plugin `registry-center` v0.2.0, route `/registry`) | `<tag/image digest>` | FIT (mount) | UMD bundle installed at `/plugins/registry-center`; `backend.gateway` = `/api/registry-center` |
| Orchestration Center sub-app | `orchestration-center` → `workflow-designer` (plugin `orchestration-center`, route `/orchestration`) | `<tag/image digest>` | FIT (mount) | Bundle installed at `/plugins/orchestration-center`; `bundled-plugins.json` pins `requiredRoutes: ["/orchestration"]` |
| Bundled plugins (delivery) | `openan-portal/portal/public/plugins/*` | per manifest | FIT (registry) | `registry-center` 0.2.0, `orchestration-center` 0.1.0, `observation-center` 1.0.0, `virtual-showroom` 1.1.0, `an-ontology` 1.0.0, `scenario-showcase` 0.1.0 |
| Source plugins (build-time) | `openan-portal/plugins/*` | workspace | FIT (registry) | `execution-center` (order 3), `skill-center` (order 6); `hello-portal` and the source `orchestration-center` are disabled by `plugins/plugin-overrides.json` |
| Test target runtime | portal nginx entry (unprivileged nginx, port 8080) | `<tag>` | FIT (UI) | Renders `default.conf.template` with `REGISTRY_URL` / `BACKEND_URL` / `OBSERVATION_URL` |

**Objects explicitly not under test:** `observation-center`, `virtual-showroom`, `an-ontology`, `scenario-showcase` and `execution-center` are exercised only as registration/navigation data (their manifests must load and their nav entries must appear); `an-ontology` additionally proves grouped-menu rendering. Their business behavior belongs to their own FIT tables.

---

## 3. Test Strategy

### 3.1 Test Layers

| Layer | Executor | Scope |
|------|--------|-------|
| FIT | Portal WG | Shell ↔ sub-app integration, plugin registration contract, routing/session/i18n correctness on the deployed stack |
| SIT | Integration Testing WG | Release-level combinations (portal + registry + orchestration + installation modes) on RC builds |

### 3.2 Test Types

Aligned with Framework §10; applicable to this feature:

- [x] Functional testing (shell boot, login/logout, route resolution, sub-app mount, nav generation, plugin enable/disable)
- [x] Exception testing (plugin bundle load failure, component-scope 401 isolation, missing preference endpoint)
- [ ] A2A-T protocol testing (not applicable; the portal has `protocol_primitive:none`)
- [ ] Performance testing (FE load budget is tracked by the frontend WG, not FIT)
- [ ] Stress/capacity testing
- [ ] Long-duration stability testing
- [ ] Reliability/fault injection beyond plugin-load failures
- [x] Security testing — only the authentication gate is covered functionally; mTLS/JWS/Authorization-T belong to the specialized security plan
- [x] Compatibility testing — browser matrix only (Chromium for CI; Firefox/WebKit optional), tracked outside this table
- [ ] Deployment mode testing (install/upgrade paths belong to the `openan-installation` plan; the served plugin-artifact contract is verified functionally by `FIT-openan-portal-plugin-registry-001`)

### 3.3 Test Method

- Real-environment execution: portal served from the release image together with the deployed `registry-center` and `orchestration-center`; no mocked backends at the integration layer. Request interception is used only for negative cases (500/401 injection) and is removed inside the same case.
- Deterministic assertions only: HTTP status codes of the API the page calls, URL/`location.pathname`, request cookie presence/identity, `localStorage` keys, `documentElement` class/`colorScheme`, `role=alert` presence, DOM element presence and exact heading text. No assertion on generated text, colors, spacing, or animations.
- Three API surfaces are asserted, each with a different prefix. Verified prefixes: shell/auth calls use `/api/orchestrate/rest/v1/orchestrate/*` (`portal/src/service/api.js`); the Registry Center sub-app calls `/api/registry-center/rest/v1/registry-center/*` (plugin-scoped client from `createApi('/api/registry-center')`); the Orchestration Center sub-app calls `/rest/v1/orchestrate/*` directly (the plugin builds its own paths and the host client has no base URL).
- Sub-app DOM has no test ids, so mount assertions use data-driven exact text (for example the fixture AgentCard name rendered as an `<h3>`) or the plugin's own i18n key. Bundle-delivered plugins carry no locale files, and the bundle loader rewrites only menu labels, so component-level `t('ns:key')` lookups may render the raw key; assertions therefore accept the raw key or the localized value.
- Prohibitions: no sleep-based synchronization (Playwright auto-wait, `expect(...).toBeVisible()`, `waitForResponse`); no shared mutable state between cases (each case creates and deletes its own fixture data); no assertion-free steps.
- Session reuse is a read-only fixture: one signed-in storage state may be captured per case, never shared across cases.

### 3.4 Automation Strategy

- 100% of P0/P1 cases automated and repeatable; all 19 cases in this table are automatable (`Automatable=Yes`, `language_profile:js`).
- Code location: `e2e-frontend/openan-portal/` with one spec per topic — `test-portal-shell.spec.ts`, `test-subapp-mount.spec.ts`, `test-plugin-registry.spec.ts`; helpers (API fixture client, login, plugin-manifest reader) under `e2e-frontend/openan-portal/fixtures/`.
- `execution` label layering: `smoke` (6 cases, PR gate) / `full` (13 cases, Daily) — every P0 core acceptance case uses `smoke`, ordinary P1/P2 uses `full`.
- Labels per case: `feature=openan-portal`, `environment=with-workload-cluster`, `components` (from `Component Deps`), `priority`, `execution`. Any temporary skip must reference an issue.
- On failure the scene is preserved: Playwright trace, screenshot, console log, network log (HAR) and the captured API responses.

---

## 4. Test Scenarios

| Scenario ID | Scenario Description | Components | Priority | Notes |
|---------|---------|----------|--------|-------|
| SCN-openan-portal-001 | Portal entry without a session: shell boots, `/auth/check` reports `authenticated=false`, login card replaces the shell | orchestration-center | P0 | `FIT-openan-portal-portal-shell-001`, `FIT-openan-portal-portal-shell-003` |
| SCN-openan-portal-002 | Access authentication lifecycle: login sets the `session_token` cookie, shell renders nav from manifests, logout revokes the session durably | orchestration-center | P0–P1 | `FIT-openan-portal-portal-shell-002`, `FIT-openan-portal-portal-shell-004`, `FIT-openan-portal-portal-shell-007` |
| SCN-openan-portal-003 | Framework-level theming and i18n: language switch (EN↔zh) and theme switch (dark↔light) with persistence across reload | orchestration-center | P1 | `FIT-openan-portal-portal-shell-005`, `FIT-openan-portal-portal-shell-006` |
| SCN-openan-portal-004 | Registry Center sub-app mount: bundle load, route `/registry`, plugin gateway `/api/registry-center`, fixture AgentCard rendered | registry-center | P0 | `FIT-openan-portal-subapp-mount-001` |
| SCN-openan-portal-005 | Orchestration Center sub-app mount: bundle load with `requiredRoutes`, route `/orchestration`, `/rest/v1/orchestrate` data path | orchestration-center | P0 | `FIT-openan-portal-subapp-mount-002` |
| SCN-openan-portal-006 | Cross-sub-app navigation: one session shared by both sub-apps, bookmarked deep link with a live session, unknown route fallback to the first plugin route | registry-center, orchestration-center | P1 | `FIT-openan-portal-subapp-mount-003`, `FIT-openan-portal-subapp-mount-004`, `FIT-openan-portal-subapp-mount-005` |
| SCN-openan-portal-007 | Failure isolation: a component-scope 401 keeps the host session; a failing bundle surfaces an alert while other sub-apps still mount | registry-center, orchestration-center | P1–P2 | `FIT-openan-portal-subapp-mount-006`, `FIT-openan-portal-plugin-registry-005` |
| SCN-openan-portal-008 | Plugin registration and extension points: artifact contract, nav generation by manifest order with a grouped menu, Skill Center onboarding, runtime enable/disable, preference degradation | registry-center, orchestration-center | P0–P2 | `FIT-openan-portal-plugin-registry-001`, `FIT-openan-portal-plugin-registry-002`, `FIT-openan-portal-plugin-registry-003`, `FIT-openan-portal-plugin-registry-004`, `FIT-openan-portal-plugin-registry-006` |

---

## 5. Test Case Design

### 5.1 Numbering Rules

- FIT cases: `[FIT-openan-portal-<topic>-<NNN>]`, topics `portal-shell`, `subapp-mount`, `plugin-registry` (7 / 6 / 6 cases, continuous from 001)
- SIT cases for this feature will use `SIT-portal-<NNN>` and belong to the release test plan
- Automation mapping: `test-portal-shell.spec.ts` (portal-shell), `test-subapp-mount.spec.ts` (subapp-mount), `test-plugin-registry.spec.ts` (plugin-registry)

### 5.2 Priority Definitions

| Priority | Definition | Pass Rate Requirement |
|--------|------|-----------|
| P0 | Blocks the portal entry or the core mounted-sub-app path (6 cases) | 100% (TRR entry and release gate) |
| P1 | Major shell capability or sub-app navigation impaired, workaround exists (10 cases) | 100% |
| P2 | General scenarios and business negatives (3 cases) | ≥80% |

### 5.3 Label Dimensions

Every case must carry the full set of labels in code: `feature=openan-portal`, `environment=with-workload-cluster`, `components` (derived from the CSV `Component Deps`: `registry-center`, `orchestration-center`), `priority`, `execution` (`smoke`/`full`), `skip` (temporary skips must reference an issue). `language_profile=js`, `protocol_primitive=none` for every row.

### 5.4 Case Table

Cases are carried in the 16-column CSV archived in the same directory: [`testcases-openan-portal.csv`](testcases-openan-portal.csv) — **19 cases**: `portal-shell` 7, `subapp-mount` 6, `plugin-registry` 6; priority split P0 6 / P1 10 / P2 3. P0/P1 rows all carry the tracking issue link for requirement traceability. Every row ends with a cleanup step that also asserts the restored state (session cleared, fixture AgentCard deleted and re-queried as 404, plugin re-enabled, interception removed).

### 5.5 Case Design Requirements

- Every case includes preconditions, numbered steps, one assertion per checked step, and a cleanup step with its own assertion.
- Fixture data is created and destroyed inside the case: the only mutated resource is a Registry Center AgentCard (`FITPortal` / `fit-portal-agent`), deleted in the cleanup step and verified with a 404.
- Ordering independence: a case never depends on another case's session, plugin state, theme/language, or `localStorage`. Language and theme cases restore the default (`en`, dark) in their cleanup step so `localStorage` does not leak between cases.
- Negative cases inject failures with Playwright request interception scoped to the case (bundle manifest 500, component 401) and remove the route handler in cleanup; the missing preference endpoint needs no interception because the production backend already lacks the route.

---

## 6. Test Environment and Data

### 6.1 Environment Topology

| Item | Value |
|----|------|
| Environment label | `with-workload-cluster` — the portal is served together with the deployed `registry-center` and `orchestration-center` behind the deployment entry |
| Portal serving mode | Release image (unprivileged nginx, container port 8080) with `default.conf.template` rendered from `REGISTRY_URL` / `BACKEND_URL` / `OBSERVATION_URL`; default in-cluster values come from `15-openan-backends.envsh` (`registry-center:5000`, `orchestration-center:5001`, `observation-center:5002`). The image content is the release static site (`index.html` + `assets/` + `plugins/`), so bundle artifacts are present without a rebuild |
| Alternative serving modes | `npm run dev` (Vite dev server, port 3003, `scripts/backend-proxy.js`) and `npm run preview` (port 4173) — both implement the same gateway prefixes as nginx; FIT runs against the image |
| Browser | Playwright Chromium, viewport 1366×768, `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` honored |
| Environment provider | Integration Testing WG |

Gateway contract verified in `openan-portal/default.conf.template`:

| Frontend path | Upstream | Behavior |
|---|---|---|
| `/api/orchestrate/*` | `${BACKEND_URL}` | prefix strip; SSE-safe (`proxy_buffering off`) |
| `/api/registry-center/*` and `/api/registry/*` | `${REGISTRY_URL}` | prefix strip (`/api/registry/rest/v1/registry/*` → `/rest/v1/registry-center/*`) |
| `/api/observe/*` | `${OBSERVATION_URL}` | GET/HEAD only |
| `/rest/v1/orchestrate/*`, `/rest/v1/registry-center/*` | orchestration / registry | compatibility for independently built plugins |
| `/plugins/*` | static | `Cache-Control: no-cache`, CORS `*` |
| `/` | static | SPA fallback to `/index.html` |

### 6.2 Dependent Services

| Dependency | Configuration | Notes |
|------|---------|------|
| Orchestration Center | reachable, access authentication active, built-in `admin` account present | Owns `/rest/v1/orchestrate/auth/*` (the shell's only auth backend) and the `/rest/v1/orchestrate/workflows`, `/templates` APIs used by the orchestration sub-app. Authentication is active when the user store holds at least one user (PostgreSQL/MySQL mode) or `access_password` is set in `server.conf` (file mode) — `orchestrate/server/auth.py#L118-L135`; self-registration additionally needs `auth.register.enabled=true` |
| Registry Center | reachable, `/rest/v1/registry-center/agent-cards` writable for fixtures | Sub-app data path `/api/registry-center/rest/v1/registry-center/agent-cards/manage` and `/agents/health` |
| Plugin artifacts | all enabled entries of `portal/bundled-plugins.json` installed under `/plugins/<id>/` | Release gate: `npm run build:release` = `plugins:validate` + build; `plugins:validate` writes `portal/public/plugins.release.json` and `plugins.enabled` |
| SkillHub SPA (optional) | `/skillhub-app/` mount used by the Skill Center plugin | Not a required component: `plugin-registry-003` asserts the iframe element, its `?lang=` parameter and the `openan-lang` postMessage, not the embedded application |

### 6.3 Test Data

- Admin credentials from environment variables (`PORTAL_ADMIN_USER`, `PORTAL_ADMIN_PASSWORD`); never hardcoded, never committed
- One fixture AgentCard for `subapp-mount-001`: organization `FITPortal`, name `fit-portal-agent`, using the AgentCard sample shape from the registry-center test fixtures
- Locale fixtures read from the portal source: `portal/src/i18n/base-en.json`, `base-zh.json` (compared against rendered `nav.settings` / `nav.subtitle`), `plugins/skill-center/src/locales/en.json` (`skills.title`)
- Manifest fixtures read from the deployment: `portal/bundled-plugins.json`, `/plugins/<id>/plugin.manifest.json`, `plugins/plugin-overrides.json`

### 6.4 Environment Variables

See `e2e/.env.template` at the repository root; the variables newly introduced by this plan must be synchronized to that template and documented in the README. The Playwright suite under `e2e-frontend/openan-portal/` reads them from the process environment (CI injects them; a local run may source the template):

| Variable | Purpose |
|---|---|
| `PORTAL_URL` | Portal entry, e.g. `http://<ingress-host>:8080` |
| `PORTAL_ADMIN_USER`, `PORTAL_ADMIN_PASSWORD` | Session fixture for P0/P1 UI cases |
| `REGISTRY_API_URL` | Registry Center API base used to create/delete the fixture AgentCard (`/rest/v1/registry-center`) |
| `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` | Optional browser binary override in CI images |

---

## 7. Entry and Exit Criteria

| Gate | Criteria | Source |
|------|------|------|
| TRR entry (into FIT) | P0/P1 pass rate = 100%, P2 ≥ 80%, `npm run plugins:validate` passes on the release image, portal image deployable with all six bundles installed, shell reachable at the deployment entry | Framework §8.1 |
| FIT exit | Overall pass rate ≥ 95%, failed cases archived as issue + `skip-temporarily`, no open P0, report reviewed by the Integration Testing WG | Framework §8.2 |
| SIT exit / release entry | SIT pass rate = 100% with no skips, 7×24 h without P0/P1 failures, install/upgrade/rollback all passed for the portal entry, compatibility matrix passed | Framework §8.3 |

---

## 8. Defect Management

- Severity per Framework §9.1 (P0: 24 h response, fix in current release; P1: 3 business days; P2: next release)
- Portal-specific triage rule: a case failing only because a manifest is missing from the image is a deployment/artifact defect against `openan-portal` (or the producing component repository); a case failing with the manifest present is a shell or sub-app defect, assigned to the owning repository of the failing layer
- Failed cases are archived automatically as issues with trace, screenshot, console log, HAR and the captured plugin manifest responses
- Fix PRs must add a regression case and rerun the whole `openan-portal` FIT set

---

## 9. Schedule and Responsibilities

| Milestone | Target | Owner | Deliverable |
|------|------|--------|--------|
| Test plan + case table review | 2026-11-25 | Integration Testing WG | This plan + CSV merged into `docs/plans/26-winter/` |
| Automation implemented | 2026-12-04 | Zhoujie628 | `e2e-frontend/openan-portal/` specs, `smoke` green |
| TRR review | 2026-12-09 | Integration Testing WG | TRR conclusion (Test Checklist Chapter 1) |
| FIT full run + self-test report | 2026-12-18 | Zhoujie628 | Report in `docs/reports/26-winter/` |

Dates are targets for the `26-winter` window and will be confirmed with the Integration Testing WG.

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|------|---------|
| Portal image is served without all bundle artifacts installed (shell builds fine, routes 404) | All mount cases fail for a deployment reason, not a code reason | `plugin-registry-001` runs first as the artifact gate; installed-set verification mirrors `scripts/plugin-artifacts.mjs` |
| **Source gap:** the portal requests `GET`/`PUT /api/orchestrate/rest/v1/orchestrate/auth/plugins` for per-user plugin preferences, but `orchestration-center` implements no `/auth/plugins` route (only `login`, `register`, `logout`, `check`, `users`, `delete user`, `change-password` exist) | Per-user preference persistence silently degrades to `localStorage` | The degradation is codified as `plugin-registry-006` (P2; the absent route is the production state, so no request interception is used and the browser-local list must still apply); a follow-up issue must be filed against `orchestration-center` before the release gate |
| **Source gap:** the shell advertises guest browsing (`login.guest_entry`, `openan-guest-entry`, header guest badge) driven by `guest_allowed` in the `/auth/check` payload, but `orchestration-center` never emits `guest_allowed` | The guest branch is unreachable in production, so no guest case was written | Recorded as an open gap; if the backend adds the flag, add a `portal-shell` case for guest browsing |
| **Source gap:** the user-management UI calls `POST /auth/users`, `PUT /auth/users/{u}/role` and `POST /auth/users/{u}/reset-password`, none of which exist in `orchestration-center`; only list and delete are implemented | Create/reset/role UI paths cannot pass, and the non-admin `/users` redirect cannot be exercised without a provisioned non-admin account | `portal-shell-007` asserts only the admin list path and the anonymous guard; the redirect branch is deferred and noted in the case `Notes` |
| Bundle-delivered plugins carry no locale files; the loader only rewrites menu labels | Sub-app components can render raw i18n keys (`orchestration.build_workflow`) instead of localized text | Assertions accept the raw key or the localized value; a locale-delivery change must be reflected in `subapp-mount-002` |
| `portal-sdk` exists in three copies (`openan-portal/packages/portal-sdk`, `registry-center/registry-center-web/portal-sdk`, `orchestration-center/workflow-designer/node_modules/@openan/portal-sdk`) and the registry-center copy still documents `onInit` lifecycle hooks that the canonical SDK explicitly rejects | Manifest contract drift between the shell and a sub-app | Cases always assert behavior of the canonical loader (`openan-portal/packages/portal-sdk`); drift is reported as a defect against the sub-app repository |
| `README.md` states "five independent bundles" while `portal/bundled-plugins.json` enables six (`scenario-showcase` was added) | Reviewers may validate the wrong inventory | The plan and the cases derive the enabled set from `bundled-plugins.json` at run time; the README discrepancy is reported |
| Skill Center mounts `/skillhub-app/` but `default.conf.template` has no location for it, so the SPA fallback (`/index.html`) answers | The embedded application may not load in a release image | Assertions are limited to the iframe element, its `?lang=` parameter and the `openan-lang` postMessage; a deployment check is requested from the release WG |
| The nginx gateway files (`default.conf.template`, `15-openan-backends.envsh`) exist twice: in `openan-portal` and in `openan-installation/containerized/build/portal/`, and the installation copy is what the release image ships | A gateway-contract fix applied to only one copy makes the deployed stack behave differently from the repository cases were verified against | `plugin-registry-001` and the sub-app data-path assertions run against the deployed image, so a stale installation copy fails them; report the mismatch against `openan-installation` and keep both copies in the review checklist |
| Sub-app DOM exposes no test ids and business text is locale-dependent | Brittle selectors | Prefer URL, HTTP status, `localStorage`, `role=alert` and data-driven exact text (fixture agent name); request test ids from the sub-app repositories as an improvement |

---

## 11. Deliverables and Archive

| Deliverable | Archive Path |
|--------|---------|
| Test plan (this document) | `docs/plans/26-winter/openan-portal-test-plan.md` |
| Case table CSV | `docs/plans/26-winter/testcases-openan-portal.csv` |
| Test code (Playwright, `language_profile:js`) | `e2e-frontend/openan-portal/` |
| Test report | `docs/reports/26-winter/` (template: [test-report-template.md](../../templates/test-report-template.md)) |

---

## Appendix

- Verified shell entry points and routes: `/` (SPA fallback), `/registry`, `/orchestration`, `/execution`, `/skills`, `/observation`, `/showroom`, `/an-ontology`, `/scenario-showcase`, `/users` (admin only); any unmatched path is replaced by the first registered route (`Navigate replace`), and a non-admin `/users` request also redirects there.
- Verified plugin manifest fields: `id`, `name`, `version`, `menu[]` (`id`, `labelKey`, `label`, `icon`, `order`, `route`, `group`, `permissions`), `routes[]` (`path`, `component`, `menuId`, `componentExport`, `keepMounted`, `permissions`), `i18n` (`namespace`, `resources`), `backend` (`gateway`, `authScope` ∈ {`host`, `component`}), `standalone` (`enabled`, `entry`), `entry`, `css`. Lifecycle hooks `onInit` / `onActivate` / `onDeactivate` are rejected by `validateManifestMetadata`.
- Verified bundle-delivery fields in `portal/bundled-plugins.json`: `id`, `mode` (`bundle`), `entry` (`/plugins/<id>`), `enabled`, `requiredRoutes`. Bundle contract on disk: `plugin.manifest.json` + `index.js` (UMD, sets `window.__OPENAN_PLUGIN__<id with '-' → '_'>`) + `index.css`.
- Verified browser storage keys: `session_token` (cookie, HttpOnly), `i18nextLng` (language cache), `theme`, `openan-disabled-plugins`, `openan-guest-entry`, `server_config`.
- Verified shell API surface (`portal/src/service/api.js`): `GET /api/orchestrate/rest/v1/orchestrate/auth/check`, `POST .../auth/login`, `POST .../auth/logout`, `POST .../auth/change-password`, `POST .../auth/register`, `GET|POST .../auth/users`, `PUT|DELETE .../auth/users/{username}`, `PUT .../auth/users/{username}/role`, `POST .../auth/users/{username}/reset-password`, `GET|PUT .../auth/plugins`.
- Test Checklist: `docs/openan-test-checklist.md`
- Framework document: `docs/OpenAN Integration Testing Process and Framework.md`
- Tracking issue: [integration-test#12](https://github.com/project-openan/integration-test/issues/12)
