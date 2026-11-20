# Registry Center Test Plan

> Version: v0.2 | Date: 2026-11-19 | Author: Zhoujie628 | Review status: Pending review
> Related feature proposal: [integration-test#3](https://github.com/project-openan/integration-test/issues/3) · [#5](https://github.com/project-openan/integration-test/issues/5) · [#6](https://github.com/project-openan/integration-test/issues/6) · [#7](https://github.com/project-openan/integration-test/issues/7) · [#8](https://github.com/project-openan/integration-test/issues/8) · [#9](https://github.com/project-openan/integration-test/issues/9) | Version milestone: `26-winter`
> Archive path: `docs/plans/26-winter/`

---

## 1. Overview

### 1.1 Purpose

Verify that the Registry Center (`registry-center`) delivers the six 26-winter capabilities tracked by integration-test issues #3, #5, #6, #7, #8 and #9 in a real deployment, and meets the Feature Integration Test (FIT) entry and exit quality requirements: config-driven heterogeneous database adaptation, third-party relational and vector storage access, heartbeat detection with change broadcast, knowledge-graph management and retrieval data contracts, the standalone management frontend, and the publication-status filter in front of semantic search.

### 1.2 Scope

**In scope** (aligned with the integration testing boundaries in Framework §5.2):

- Config-driven storage switching driven by `etc/conf/persistence.conf` (`persistence.mode=file|sqlite|postgresql|gauss|mysql`) and `etc/conf/server.conf` (`use_vectordb`), and the AgentCard create/query/update/delete path on **every supported mode**: `file`, `sqlite`, `postgresql`, `gauss` and `mysql` each have their own `db-adaptation` row
- Third-party database access: external PostgreSQL/MySQL instances, connection profiles under `etc/conf/db/<brand>.json` with `password_env` secret references, and the Milvus vector backend (`common/vector_db`)
- Heartbeat liveness detection with configurable failure thresholds (`heartbeat.*` in `etc/conf/server.properties`), unhealthy-agent marking, health history, and change broadcast (`broadcast.*`) to webhook subscribers plus the `/changes` reconciliation feed
- Knowledge-graph entity/relation management through `/rest/v1/registry-center/knowledge-graph/*` and the `/graph` visualisation data contract
- The standalone management web application (`registry-center-web`): agent list with publish status, publish review flow, review trail, heartbeat monitor, and frontend-backend integration
- Semantic search publication filtering on both the built-in and custom retrieval handler paths, plus the publish-filter regression on the list/detail/manage endpoints

**Out of scope**:

- Boundary conditions of individual functions already covered by module unit tests in `registry-center/tests/`
- DFX capabilities: probes/logs/metrics, self-healing/restart recovery, performance, security (mTLS/JWS/Authorization-T), compatibility matrices — these belong to the corresponding specialized plans
- Pure UI layout and styling; only behaviour that depends on backend data is covered (Playwright, `e2e-frontend/`)
- Online hot migration between database backends (excluded by issue #3 for this release)
- Automatic graph construction from unstructured data and the agent-to-graph export pipeline (excluded by issue #7; `agent_to_graph_enabled` today only emits a startup log line)
- Semantic-search latency/throughput measurement (deferred to the DFX performance plan; this plan asserts correctness only)

### 1.3 References

| Document | Link/Path |
|------|----------|
| OpenAN Integration Testing Process and Framework | `docs/OpenAN Integration Testing Process and Framework.md` |
| Feature tracking issues | [integration-test#3](https://github.com/project-openan/integration-test/issues/3), [#5](https://github.com/project-openan/integration-test/issues/5), [#6](https://github.com/project-openan/integration-test/issues/6), [#7](https://github.com/project-openan/integration-test/issues/7), [#8](https://github.com/project-openan/integration-test/issues/8), [#9](https://github.com/project-openan/integration-test/issues/9) |
| Component requirement issues | [#26](https://github.com/project-openan/registry-center/issues/26) (db-adaptation), [#28](https://github.com/project-openan/registry-center/issues/28) (third-party-db), [#29](https://github.com/project-openan/registry-center/issues/29) (heartbeat), [#30](https://github.com/project-openan/registry-center/issues/30) (mgmt-frontend); no requirement issue exists yet for #7 (knowledge-graph) and #9 (semantic-search) |
| Component API documentation | `registry-center/docs/en/Registry Center API Reference.md` |
| Database configuration | `registry-center/docs/database-configuration.md` |
| Knowledge graph API contract | `registry-center/knowledge-graph-openapi.yaml` |
| Transport/runtime policies | `registry-center/docs/transport-runtime.md`, `registry-center/etc/conf/server.conf.example`, `registry-center/etc/conf/server.properties` |
| Management frontend | `registry-center/registry-center-web/README.md`, `registry-center/registry-center-web/plugin.manifest.js` |
| Case table | [`testcases-registry-center.csv`](testcases-registry-center.csv) (40 cases) |
| Deployment contract | `openan-installation` online Helm / offline compose lines |

---

## 2. Objects Under Test

| Component | Repository | Version/Build | Test Layer | Notes |
|------|------|----------|----------|------|
| Registry Center backend | `registry-center` | `<tag/image digest>` | FIT | FastAPI main port `5000` (HTTPS by default), `/rest/v1/registry-center/*`, `/health` |
| Management frontend | `registry-center/registry-center-web` | `<tag/build id>` | FIT (UI automation) | Standalone shell (`npm run dev`, port 3004) or plugin bundle; deployed under the `/registry/` entry |
| Storage backends | PostgreSQL 14+, MySQL 8, SQLite, GaussDB, Milvus (milvus-lite/standalone) | per deployment values | Verification vehicle | Selected by `persistence.mode` / `use_vectordb` |
| Knowledge graph store | Neo4j | per `neo4j.uri` | Verification vehicle | Reached only through the knowledge-graph API |
| LLM / embedding endpoint | OpenAI-compatible chat + embedding model | `etc/config/models.yaml` + named secret | Verification vehicle | Used by semantic search and vector writes; assertions stay deterministic |
| Test HTTP receiver | test harness (session fixture) | `<tag>` | Dependency | Records webhook deliveries for broadcast cases; the heartbeat topic drives the API directly |
| Chromium (Playwright) | `e2e-frontend/` | `@playwright/test` pinned in the repo | FIT (UI) | Browser profile must be able to authenticate (see risk R-6) |

---

## 3. Test Strategy

### 3.1 Test Layers

| Layer | Executor | Scope |
|------|--------|------|
| FIT | Registry Center WG | Integration correctness of the six capabilities against real services and real databases |
| FIT (UI) | Registry Center WG | Frontend-backend integration of the management app and its dashboards |
| SIT | Integration Testing WG | Release-level combinations (registry + orchestration + portal), upgrade/rollback, compatibility |

### 3.2 Test Types

Aligned with Framework §10; applicable to this feature:

- [x] Functional testing (API integration, config change effects, business state transitions)
- [x] Exception testing (business-level negatives only: invalid profile, invalid query input, unlisted callback host, deletion conflicts)
- [ ] A2A-T protocol testing (the registry exposes REST only; protocol primitives are covered by the SDK plans)
- [ ] Performance testing (registration/query P99, semantic search latency — specialized plan)
- [ ] Stress/capacity testing
- [ ] Long-duration stability testing (7×24h)
- [ ] Reliability/fault injection (restart recovery, dependency outage, self-healing — DFX, deliberately not in this table)
- [ ] Security testing (mTLS, JWS validation, owner isolation, graph authorization — DFNS plan)
- [ ] Compatibility testing (database backends × browser — specialized plan; backend matrix is partially exercised through `db-adaptation` / `third-party-db`)
- [x] Deployment-mode testing (online Helm and offline compose deployments of the registry with a chosen backend)

### 3.3 Test Method

- Real-environment execution: services under test are not mocked at the integration layer. Storage backends (PostgreSQL, MySQL, GaussDB, SQLite, Milvus, Neo4j) are real instances or real local database files; the external ones are provisioned by the Integration Testing WG.
- Semantic search and vector writes depend on an LLM/embedding model. Cases assert status codes, JSON shape, set membership and ordering only — never model-generated text. Publication filtering is asserted as *absence* of unpublished cards, which is deterministic regardless of model output.
- Time-dependent cases (heartbeat) shorten the detection window through documented keys (`heartbeat.interval`, `heartbeat.failure.threshold`, `heartbeat.grace.period`, `heartbeat.sweep.interval`) and assert the **recorded transition sequence** through `/rest/v1/registry-center/agents/health/history` rather than any wall-clock bound. No `sleep`-based synchronization; no fixed-delay assertions.
- Broadcast assertions use a controlled HTTP receiver that records bodies and `X-Registry-*` headers; `/rest/v1/registry-center/changes` provides a deterministic fallback for the same change.
- UI cases drive the real deployed frontend with Playwright against seeded backend data; they assert rendered state (status pills, toast text, counters) and intercepted network requests, not CSS.
- Prohibitions: no shared mutable state between cases, no missing assertions, no self-healing/restart-recovery scenarios.

### 3.4 Automation Strategy

- P0/P1 are 100% automated. Automation totals from the CSV: **37 of 40 cases automated**, 3 P2 cases intentionally not automated because the promised surface does not exist yet (see §10 R-2, R-3, R-5).
- `execution` label layering: `smoke` (13 cases — deployment readiness and core paths, PR gate) / `full` (27 cases, Daily). No `slow` cases in this table.
- Backend automation lives in `e2e/registry-center/` (`test_db_adaptation.py`, `test_third_party_db.py`, `test_heartbeat.py`, `test_knowledge_graph.py`, `test_semantic_search.py`); UI automation lives in `e2e-frontend/` as Playwright specs (`test-registry-center-mgmt.spec.ts`).
- Failed cases preserve the scene: service logs (`log/`), DB row dumps, webhook receiver captures, Playwright trace/screenshots.

---

## 4. Test Scenarios

| Scenario ID | Scenario Description | Components | Priority | Notes |
|---------|---------|----------|--------|------|
| SCN-registry-center-001 | Storage backend adaptation: `persistence.mode` selects file/SQLite/PostgreSQL/GaussDB/MySQL; AgentCard register/query/update/delete and profile secret handling per backend; the switch takes effect only after a restart | registry-center, SQLite, PostgreSQL, GaussDB, MySQL | P0–P2 | Issue #3, `db-adaptation` (one row per supported mode) |
| SCN-registry-center-002 | Third-party storage: external MySQL/PostgreSQL instances (including automatic database creation) and the Milvus vector backend with embedding writes; the vector-only read contract (503) is pinned | registry-center, external MySQL/PostgreSQL, Milvus | P0–P2 | Issue #5, `third-party-db` |
| SCN-registry-center-003 | Heartbeat detection: heartbeat reply carries detection config, agents age through healthy→suspect→offline (asserted via health history), history is recorded, unhealthy cards leave discovery | registry-center, mockagent | P0–P1 | Issue #6 |
| SCN-registry-center-004 | Change broadcast: subscriptions with type/organization filters receive registration changes as signed webhooks, `/changes` reconciles by `registry_version`, unauthorized callback hosts are rejected | registry-center, mockagent, HTTP receiver | P0–P2 | Issue #6 |
| SCN-registry-center-005 | Knowledge-graph management: node/relation CRUD, bulk load, label-filtered export, force-delete conflict, disabled-switch behaviour | registry-center, Neo4j | P0–P2 | Issue #7 |
| SCN-registry-center-006 | Graph-enhanced semantic retrieval — promised, not shipped: single probe proves no traversal route exists (404 on candidate routes, `/graph` still 200) and retrieval is not graph-aware | registry-center, Neo4j, LLM | P2 | Issue #7; see R-3 |
| SCN-registry-center-007 | Semantic search publication filter on the built-in path: pending cards never reach the selection model or the response; layer-aware query applies the same rule | registry-center, LLM | P0 | Issue #9 |
| SCN-registry-center-008 | Semantic search publication filter on the custom handler path plus response-format/order preservation and publish-filter regression on list/detail/manage | registry-center, LLM | P1 | Issue #9 |
| SCN-registry-center-009 | Management frontend integration: agent list with publish status, publish review with mandatory remark, review trail, heartbeat monitor, list search/tabs/view toggle, unreachable-backend error state | registry-center, registry-center-web | P0–P2 | Issue #8 |
| SCN-registry-center-010 | Operations metrics and audit-log dashboards — promised, not shipped: single probe proves the built app has no such view and issues no `/operation-logs` request | registry-center-web | P2 | Issue #8; see R-5 |

---

## 5. Test Case Design

### 5.1 Numbering Rules

- FIT cases: `FIT-registry-center-<topic>-<3-digit number>`, topics `db-adaptation`, `third-party-db`, `heartbeat`, `knowledge-graph`, `mgmt-frontend`, `semantic-search` (e.g. `FIT-registry-center-heartbeat-003`).
- Each topic starts at `001` and is continuous; the topic also drives the automation file name (`test_<topic with underscores>.py`).

### 5.2 Priority Definitions

| Priority | Definition | Pass Rate Requirement |
|--------|------|-----------|
| P0 | Deployment readiness and the core closed loop of the tracked capability (backend round-trip, heartbeat state machine, change delivery, graph CRUD, publication filter, management app load) | 100% (TRR entry and release gate) |
| P1 | Main functionality coverage (history, filters, external database bootstrap, custom handler, regression surfaces, dashboards) | 100% |
| P2 | Business negatives and complex variants (invalid profile/input, callback allowlist, delete conflict, disabled switches, promised-but-absent surfaces) | ≥80% |

### 5.3 Label Dimensions

Every case carries in code: `feature` (`registry-center`), `environment` (`with-workload-cluster` for 30 deployed-service cases, `docker-compose` for 10 local-only cases), `components` (from the CSV `Component Deps` column, `mockagent` for heartbeat/broadcast cases), `priority`, `execution` (`smoke`/`full`), and `skip` (only with an issue link). `language_profile` is `python` for the 33 backend cases and `js` for the 7 Playwright cases.

### 5.4 Case Table

Cases are carried in the 16-column CSV archived in the same directory as this plan: [`testcases-registry-center.csv`](testcases-registry-center.csv) — **40 cases, of which 37 are automated**.

| Topic | Issue | Cases | P0 | P1 | P2 | Automated | Runtime (`environment`) | Automation |
|---|---|---:|---:|---:|---:|---:|---|---|
| `db-adaptation` | #3 | 7 | 2 | 4 | 1 | 7 | with-workload-cluster (4), docker-compose (3) | `e2e/registry-center/test_db_adaptation.py` |
| `third-party-db` | #5 | 6 | 2 | 2 | 2 | 5 | with-workload-cluster (3), docker-compose (3) | `e2e/registry-center/test_third_party_db.py` |
| `heartbeat` | #6 | 7 | 3 | 2 | 2 | 7 | with-workload-cluster (6), docker-compose (1) | `e2e/registry-center/test_heartbeat.py` |
| `knowledge-graph` | #7 | 7 | 2 | 2 | 3 | 6 | with-workload-cluster (7) | `e2e/registry-center/test_knowledge_graph.py` |
| `mgmt-frontend` | #8 | 7 | 2 | 2 | 3 | 6 | with-workload-cluster (5), docker-compose (2) | `e2e-frontend/test-registry-center-mgmt.spec.ts` |
| `semantic-search` | #9 | 6 | 2 | 3 | 1 | 6 | with-workload-cluster (5), docker-compose (1) | `e2e/registry-center/test_semantic_search.py` |
| **Total** | | **40** | **13** | **15** | **12** | **37** | 30 / 10 | 37 test functions/specs |

Coverage notes:

- `db-adaptation` carries one row per supported `persistence.mode`: `postgresql` (001), `mysql` (002), `file` (003), `sqlite` (005) and `gauss` (006), so the issue #3 promise "default AgentCard storage/query/update operations for each supported database type" is not partially covered. `SQLiteStorage` and `GaussDBStorage` are real `SqlStorageBackend` subclasses registered in `agent_registry/persistence/__init__.py#L83-L88`, so both are exercised end to end, not assumed.
- Profile-validation negatives (literal secret, missing secret reference, unknown field) are covered once, by `third-party-db-006`; `db-adaptation` therefore spends its rows on supported modes instead of duplicating that negative.
- Not automated (3 cases, all P2, reason recorded in the CSV `Notes`): `third-party-db-005` (vector similarity ranking), `knowledge-graph-007` (graph-traversal retrieval), `mgmt-frontend-007` (operations/audit dashboards). Each of the three is written as a **promised, not shipped** probe: the precondition names the upstream issue and the code evidence, the step set is one probe plus the cleanup, and the expected result is a single deterministic statement a test author can assert today (candidate route → 404 while a registered route still answers; or the built app exposes only two views and issues no `/operation-logs` request).

### 5.5 Case Design Requirements

- Every case has numbered preconditions, numbered steps whose last step is a cleanup with its own assertion, and one expected result per `see result N` reference.
- Cases are independently repeatable: each seeds its own cards, subscriptions, graph nodes or configuration backup and removes them in the cleanup step; no case depends on another case's leftovers.
- Parameterized inputs (`<CARD_FILE>`, `<org>`, `<DB_NAME>`, `<MYSQL_HOST>`, `<GAUSS_HOST>`, `<GAUSS_USER>`, `<RECEIVER_HOST>`, `<WEB_URL>`) are supplied through `e2e/.env` at automation time, never hardcoded.
- Backend negatives stay at business level (invalid profile field, invalid query input, unlisted callback host, delete conflict); dependency outages, restarts and resource limits are excluded. The only restart in the table is `db-adaptation-007`, where the restart is the documented way to apply a `persistence.mode` change — not a recovery assertion.

---

## 6. Test Environment and Data

### 6.1 Environment Topology

| Item | Value |
|----|------|
| Deployment mode | Online Helm (K8s cluster) or offline compose stack, per the modes supported in this release; `with-workload-cluster` cases run against the deployed stack, `docker-compose` cases against a single-host compose stack |
| Registry endpoint | `https://<host>:5000` (main port; `IP`/`PORT`/`enable_https` in `etc/conf/server.conf`), health probe `GET /health` |
| Management frontend | Deployed `/registry/` entry, or standalone `npm run dev` on port 3004 with the Vite proxy `/rest/v1/registry-center → http://127.0.0.1:5000` (`VITE_BACKEND_TARGET` overrides the target) |
| Cluster / host size | TBD by the Integration Testing WG allocation |
| Environment provider | Integration Testing WG |

### 6.2 Dependent Services

| Dependency | Configuration | Notes |
|------|---------|------|
| PostgreSQL | `etc/conf/db/postgresql.json` (`host`, `port`, `database`, `user`, `password_env`) + `persistence.mode=postgresql` | Used by `db-adaptation-001/004/007` and `third-party-db-002/004/006` |
| MySQL | `etc/conf/db/mysql.json` + `persistence.mode=mysql` | `db-adaptation-002`, `third-party-db-001`; dialect differences are asserted (changed-row update reporting) |
| GaussDB | `etc/conf/db/gaussdb.json` (`gauss.host`, `gauss.port`, `gauss.database`, `gauss.username`, `password_env`) + `persistence.mode=gauss` | `db-adaptation-006`; PostgreSQL-protocol instance provisioned by the WG (P2 so an unavailable instance does not block TRR) |
| SQLite | `etc/conf/db/sqlite.json` (`path`, default `data/agents.db`) + `persistence.mode=sqlite` | `db-adaptation-005`; local database file, no server needed |
| Milvus | `etc/conf/db/milvus.json` (`uri`, `version`) + `use_vectordb=true`; collection `agent_card_collection`, 1024-dim embeddings, FLAT/L2 index | `third-party-db-003/004/005` |
| Neo4j | `persistence.conf`: `neo4j.uri`, `neo4j.username`, `neo4j.password`; `knowledge_graph.enabled=true` | `knowledge-graph` topic; API answers 404 while disabled |
| LLM / embedding endpoint | `etc/config/models.yaml` + `api_key_env` secret (or `USE_MOCK_LLM=true` for structure-only runs) | `semantic-search`, `third-party-db-003/005` |
| Webhook receiver | Plain HTTP receiver recording bodies/headers; host listed in `broadcast.callback.allowlist`, `broadcast.allow.http.callbacks=true` | `heartbeat-003/005/006` |
| Test HTTP receiver | test harness | Records webhook deliveries for the `heartbeat` topic broadcast cases (not an OpenAN component) |

### 6.3 Test Data

- Signed AgentCard samples for each seeded card name (`test-pg-agent`, `test-mysql-agent`, `test-file-agent`, `test-sqlite-agent`, `test-gauss-agent`, `test-secret-agent`, `hb-agent-1..3`, `ss-pending-ran`, `ss-published-ran`, `ui-agent-1..3`, …), with distinct descriptions for semantic-search cases
- Connection profile fixtures: valid `password_env` profiles for `postgresql.json`, `mysql.json`, `gaussdb.json`, `sqlite.json`; one literal-secret profile and one profile with an unknown field for the negative case (`third-party-db-006`); every fixture is restored in the cleanup step
- Configuration backups for every edited key (`etc/conf/persistence.conf`, `etc/conf/server.conf`, `etc/conf/server.properties`, `etc/conf/db/*.json`) — cases restore the pre-test file content
- Review remarks for publish/reject/deprecate transitions (mandatory by API contract) and their expected status-history entries

### 6.4 Environment Variables

Base contract is `e2e/.env.template` (`REGISTRY_CENTER_URL`, `REGISTRY_CLIENT_CERT`, `REGISTRY_CLIENT_KEY`, `REGISTRY_CA_CERT`, `DB_BACKEND`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `LLM_CHAT_*`, `USE_MOCK_LLM`, `MOCK_AGENTS_HOST`).

This plan adds the following variables, which must be synchronized to `e2e/.env.template` and documented in the README before the automation PR is merged:

| Variable | Purpose |
|------|---------|
| `REGISTRY_WEB_URL` | Management frontend entry used by the Playwright cases |
| `REGISTRY_BACKEND_HTTP_URL` | Plain-HTTP backend base URL for the `verify_client=false` + `owner.identity.mode=token` UI profile |
| `REGISTRY_DB_SECRET` | Value injected for the `password_env` reference of the PostgreSQL profile |
| `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER` | External MySQL instance for `db-adaptation-002` / `third-party-db-001` |
| `GAUSS_HOST`, `GAUSS_PORT`, `GAUSS_USER`, `GAUSS_PASSWORD` | GaussDB instance for `db-adaptation-006` (aliases accepted by the `gauss` profile) |
| `SQLITE_PATH` | SQLite database file used by `db-adaptation-005` (default `data/agents.db`) |
| `MILVUS_URI`, `MILVUS_TOKEN` | Milvus target for the vector cases |
| `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` | Knowledge-graph backing store |
| `REGISTRY_KG_OPERATOR_OWNER` | Verified identity allowed to call the graph API (`knowledge_graph.allowed.owners`) |
| `REGISTRY_HEARTBEAT_PROFILE` | Named detection profile (`interval`/`threshold`/`grace`/`sweep`) applied to the heartbeat environment |
| `REGISTRY_WEBHOOK_RECEIVER_URL` | Receiver endpoint used by the broadcast cases |

---

## 7. Entry and Exit Criteria

| Gate | Criteria | Source |
|------|------|------|
| TRR entry (into FIT) | P0/P1 pass rate = 100%, P2 ≥ 80%, UT coverage not decreasing, registry-center image deployable with each supported backend | Framework §8.1 |
| FIT exit | Overall pass rate ≥ 95%, failed cases archived as issue + `skip-temporarily`, no open P0/P1, publication-filter regression on list/detail/manage green, report reviewed by the Integration Testing WG | Framework §8.2 |
| SIT exit / release entry | SIT pass rate = 100% with no skips, 7×24h without P0/P1 failures, install/upgrade/rollback passed, compatibility matrix (database backends × browser) passed | Framework §8.3 |

---

## 8. Defect Management

- Severity classification and SLA per Framework §9.1 (P0: 24h response / fix in current release; P1: 3 business days; P2: next release).
- Failed cases are archived as issues with service logs (`log/`), database row dumps, webhook captures, Playwright traces/screenshots and the effective configuration files attached.
- Fix PRs must add a regression case in the same topic and rerun all `registry-center` FIT cases.

---

## 9. Schedule and Responsibilities

| Milestone | Date | Owner | Deliverable |
|------|------|--------|--------|
| Test plan + case table review | 2026-11-25 | Integration Testing WG | This plan and [`testcases-registry-center.csv`](testcases-registry-center.csv) merged into `docs/plans/26-winter/` |
| Case writing / automation completed | 2026-12-05 | Zhoujie628 | `e2e/registry-center/` + `e2e-frontend/` automation, `smoke` green |
| TRR review | 2026-12-12 | Integration Testing WG | TRR conclusion (Test Checklist Chapter 1) |
| FIT execution + self-test report / report review | 2026-12-18 | Zhoujie628 | `docs/reports/26-winter/` report reviewed by the Integration Testing WG |

---

## 10. Risks and Mitigations

| ID | Risk | Impact | Mitigation |
|----|------|------|---------|
| R-1 | Issue #3 excludes online hot migration, and the implementation confirms it: a SQL backend instance owns a fixed connection and dialect, and a change requires a restart (`docs/database-configuration.md`). | A reviewer may expect data migration coverage. | `db-adaptation-007` asserts exactly the supported behaviour — the switch affects a restarted process only, and no data is migrated. The restart there applies a configuration change, not failure recovery, and is annotated as such in the case `Notes` so it is not counted as a DFR scenario. Migration remains explicitly out of scope. |
| R-2 | **Source gap (issue #5):** `use_vectordb=true` replaces the authoritative record store rather than adding a searchable projection (`agent_registry/core.py#L137-L156`, `agent_registry/errors.py#L20-L41`). In that mode the API answers 503 for approval/ownership-dependent reads and for `POST /agent-cards/semantic-query`, so *embedding similarity retrieval* has no reachable surface. | The promised vector-search behaviour cannot be exercised end to end. | `third-party-db-003` verifies embedding writes through the collection; `third-party-db-004` locks the documented 503 contract; `third-party-db-005` is a **promised, not shipped** probe (`Automatable=No`): it asserts today's deterministic facts — the 503 message and the 404 on the candidate `/agent-cards/similarity-search` route — so it turns green the day a projection mode ships and that route starts answering. |
| R-3 | **Source gap (issue #7):** no graph-traversal semantic retrieval endpoint exists. The graph API ships node/relationship CRUD, `/graph`, `/bulk/nodes`, `/bulk/relationships`, `/import`, `/export` and `/sync` only; semantic search does not consult the graph. | The "retrieval enhancement" half of issue #7 is unverified. | `knowledge-graph-001..006` cover everything that shipped; `knowledge-graph-007` is a **promised, not shipped** probe (`Automatable=No`) asserting that the candidate `/traverse` and `/nodes/<id>/neighbors` routes return 404 while the registered `/graph` route returns 200, and that the semantic-query result set is unchanged by adding a relation. The gap is raised against #7 with this plan. |
| R-4 | Custom handlers are registered in code (`HandlerRegistry.register(InterfaceType.RETRIEVE, …)` in `common/custom/custom_handle.py`); there is no configuration switch. | `semantic-search-003` cannot be run against a stock image. | The WG provisions one site-specific build/overlay that mounts the fixed-order retrieval handler; the case asserts the handler order is observable, so a mis-provisioned run fails loudly instead of passing silently. |
| R-5 | **Source gap (issue #8):** the shipped web app has no visual agent registration form (registration stays REST/SDK-only) and no operations-metrics or audit-log view; `getOperationLogs` in `src/service/api.js#L116-L120` has no component consumer. | Two promises of issue #8 are uncovered by UI cases. | `mgmt-frontend-001..006` cover what shipped (list/publish/trail/monitor/settings); `mgmt-frontend-007` is a **promised, not shipped** probe (`Automatable=No`) asserting that the built app exposes exactly the Agent Registry and Heartbeat Monitor views and issues no `/operation-logs` request while the API returns entries. Both gaps raised against #8. |
| R-6 | Browser sessions cannot satisfy the mTLS client-certificate requirement in every CI runner. | UI cases could fail on identity, not on behaviour. | UI cases target the documented browser profile: `REGISTRY_VERIFY_CLIENT=false` with `owner.identity.mode=token` (as `docker-compose.yml` does) or a trusted proxy identity; if the environment forces mTLS, Playwright `clientCertificates` must be configured before the cases are enabled. |
| R-7 | Heartbeat thresholds are time-sensitive: with `interval` 3–5 s and `threshold` 2 the suspect window is only `interval × 1 + grace` wide (`agent_registry/health/state.py#L29-L43`), so a snapshot poll can miss it. | Flaky `heartbeat-002/003/004`. | The cases assert the **recorded transition sequence** through `GET /rest/v1/registry-center/agents/health/history` (pairs of `previous_health_status` → `health_status`) instead of sampling live state, and no wall-clock bound is asserted. Cases use a shortened window (`interval` 3–5 s, `threshold` 2, `grace` 0, `sweep` 1) and framework retries, never fixed sleeps. |
| R-8 | Semantic search and vector writes depend on an LLM/embedding endpoint; model output is not deterministic. | Unstable assertions. | Cases assert status codes, response shape, set membership and ordering only. The filter cases assert the *absence* of pending cards, which holds for any model output. `USE_MOCK_LLM=true` can be used for structure-only reruns. |
| R-9 | Heartbeat/broadcast state lives in the service process (in-memory store in `file` persistence mode). | Restarting the service mid-case loses health/delivery state. | Cases never restart the service between seeding and assertion; restart-recovery scenarios belong to DFX. The only restart in the table (`db-adaptation-007`) is a configuration-application step, not a recovery assertion. |
| R-10 | The knowledge-graph API requires Neo4j **and** an authenticated graph operator (`knowledge_graph.allowed.owners`); unauthenticated callers get 401 and unauthorized callers 403. | Graph cases blocked if the allowlist is not prepared. | The operator identity is provisioned up front (`REGISTRY_KG_OPERATOR_OWNER`); 401/403 authorization coverage stays with security testing (DFNS). |
| R-11 | External database instances (PostgreSQL, MySQL, GaussDB, Milvus, Neo4j) must be provisioned per run. | Case delays; `db-adaptation-006` (GaussDB) cannot run at all without one. | Request the instances from the Integration Testing WG before RC-0; each case validates connectivity in its first step so a missing instance fails fast and visibly. GaussDB coverage is P2 precisely so an unavailable instance does not block the TRR gate while the mode still stays covered. |

---

## 11. Deliverables and Archive

| Deliverable | Archive Path |
|--------|---------|
| Test plan (this document) | `docs/plans/26-winter/` |
| Case table CSV | `docs/plans/26-winter/testcases-registry-center.csv` |
| Test code | `e2e/registry-center/` (pytest) and `e2e-frontend/` (Playwright) |
| Test report | `docs/reports/26-winter/` (template: [test-report-template.md](../../templates/test-report-template.md)) |

---

## Appendix

- Test Checklist: `docs/openan-test-checklist.md`
- Framework document: `docs/OpenAN Integration Testing Process and Framework.md`
- Field rules: `docs/templates/testcases-template-fields.md`
- Endpoint inventory verified in source: `agent_registry/server.py` (agent-cards CRUD, `manage`, `publish`/`reject`/`deprecate`, `review-status`, `operation-logs`, `semantic-query`, `agent-cards-with-layer[/semantic-query]`, `heartbeat`, `agents/health[/history|/stream]`, `subscriptions`, `changes`, `keys`, `health`) and `agent_registry/knowledge_graph_api/router.py` (prefix `/rest/v1/registry-center/knowledge-graph`).
