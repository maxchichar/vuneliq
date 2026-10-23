# Vuneliq — team ownership and four-day MVP delivery

**Status: provisional; source verification required.** Prepared 23 October 2026.

## 1. Evidence and limits

This document uses the cached request from “Create Team Roles MD” and the current instruction. Initial access failed, then GitHub access recovered. The referenced conversation remains unavailable. The project brief, delivery plan and collaborator screenshot were not accessible. Verified main-branch recursive tree and README: only README.md and LICENSE exist; no application, tests, CI or repository instructions exist in that tree. Default branch is main and the connection reports push/admin permissions. Uploaded requirements and collaborator identities remain unverified. This document is proposed on a draft review branch.

Target repository: <https://github.com/maxchichar/vuneliq>. Intended repository path: `docs/TEAM_ROLES_AND_MVP_DELIVERY.md` after source verification.

The requested team is eight people: seven displayed collaborators plus owner `maxchichar`. Four collaborators are named in the cached request, including the incomplete identifier “olayinka”. Three account names remain unknown. Slots below are deliberately placeholders, not invented GitHub accounts. Responsibilities for newcomers are recommendations, subject to confirming their availability and experience.

Before treating this as the final plan, obtain the brief, delivery plan, screenshot and repository access; replace all three account placeholders; verify Olayinka’s exact handle; map the proposed workflow to actual product requirements; reconcile existing code and delivery commitments. Day 1–4 are relative working days, not calendar dates or a promise of four-day production readiness.

## 2. Delivery objective and scope rule

The verified README describes donations, contribution tracking and impact visibility. Proposed journey: a donor browses a seeded cause, makes a sandbox donation, retrieves its authoritative status/history after refresh and reads a source-linked impact update. AI may summarize published updates; it must not invent impact or determine payment success. This is a proposed planning scaffold; the brief must establish the actual journey and whether authentication, history or AI processing is required in this form.

At kickoff, owner records: target user; problem; exact input and output; three representative examples; supported input limits; demo environment; provider budget; and explicit exclusions. Acceptance criteria below are engineering gates, not a substitute for those product requirements.

**P0:** agreed primary journey, access control wherever user data exists, validated API, persisted state, bounded AI calls, usable error states, migration, repeatable deployment, tests and demo evidence.

**P1 only after P0 passes:** extra screens, secondary workflows, richer history or export, additional prompt variants.

**Deferred by default:** multiple AI providers, autonomous agents, microservices, Kubernetes, advanced analytics, complex roles, custom model training and vector search without a demonstrated retrieval requirement. Use sandbox payments for a donation demo. Live payments and sensitive document ingestion require confirmed scope and appropriate verification.

## 3. People, responsibilities and completion evidence

| Person/account | Primary role | Owns and delivers | Reviewer / support | Completion evidence |
|---|---|---|---|---|
| `maxchichar` — owner | Technical/product lead and AI integration co-owner | Scope, architecture decisions, API/AI contracts, provider configuration, merge decisions, deployment and rollback, release decision; pairs on AI implementation | `michael-tech-create` for AI; backend lead for integration; security lead for release | Agreed scope, working environment, reviewed AI integration, deployment and rollback record |
| `divineexcel` | UI/UX owner | Primary flow, wireframes, small design system, responsive layouts, accessible labels/focus, loading/empty/error/success states; frontend implementation paired with newcomer A | Owner accepts flow; newcomer A implements; QA checks usability | Approved screen/state checklist and working primary flow at mobile and desktop widths |
| `michael-tech-create` | AI engineering co-owner | Provider adapter, prompt and structured output contract, validation, timeout, retry policy, bounded token/cost settings, evaluation fixtures; pairs with owner | Owner reviews AI; backend lead reviews service integration | Mocked integration tests, small representative evaluation set, authorized live smoke test |
| Olayinka — exact handle unverified | Security owner | Threat checklist, auth and per-object authorization review, secrets handling, CORS, input limits, abuse controls, dependency findings, privacy/logging review | Backend lead implements related API controls; owner resolves release risks | Tests for unauthenticated/cross-user access, documented findings and closure evidence |
| `osazuwamatthewogbebor` | Backend lead | FastAPI modules, Pydantic schemas, SQLAlchemy models, Alembic migrations, transaction handling, OpenAPI, job persistence and worker integration if needed | AI co-owners for worker integration; security lead for data access | Migrated test database, passing API tests, generated contract, complete browser-to-database journey |
| Collaborator A — account pending screenshot | Frontend implementation apprentice | App shell, React Router routes, form and result/history views, TanStack Query integration, generated client usage, component tests | `divineexcel` pairs on UI; backend lead on API | Primary flow works against real API; failures and pending states visible; no hand-written duplicate API types |
| Collaborator B — account pending screenshot | QA and acceptance apprentice | Acceptance checklist, test data, Playwright happy path and failure cases, exploratory testing, reproducible bug reports, final regression evidence | Backend lead and owner mentor; security lead supplies abuse cases | Test results tied to acceptance IDs, defect list, regression report on release candidate |
| Collaborator C — account pending screenshot | Delivery/documentation apprentice | Setup guide, environment-variable names without values, seed/demo instructions, CI setup with owner, release checklist and evidence index | Owner pairs on CI/deployment; QA verifies instructions | Another teammate completes fresh setup using guide; CI evidence; reproducible demo steps |

Beginners own bounded outputs, not sole accountability for security, database migrations, AI reliability or production operations. Each takes one small task at a time and opens an early draft PR. Mentors review the first task before assigning the next.

## 4. Decision and review ownership

| Area | Accountable decision maker | Implementer | Required consulted reviewer |
|---|---|---|---|
| Product scope and priority | Owner | Relevant task owner | UI/UX and QA |
| UX and visual consistency | `divineexcel` | UI/UX + A | Owner |
| API/schema/migration | Backend lead | Backend lead | Security for access/data changes; owner for contract changes |
| AI behavior and spending | Owner | Owner + `michael-tech-create` | Backend lead; QA for evaluation |
| Security release gate | Owner | Security lead + affected implementer | Security lead documents disposition |
| Tests and release evidence | Owner | B + each feature author | Relevant technical owner |
| Deployment/rollback | Owner | Owner + C | Backend lead and QA |

Every PR needs a reviewer other than its author. The owner assigns an alternative reviewer when unavailable. QA reports readiness; the owner makes the final release decision using evidence. Critical access-control failures, exposed secrets, destructive migration failures and broken P0 journeys block release.

## 5. Architecture recommendation

The modular monolith is appropriate for a small team on a four-day deadline: one backend codebase, explicit module ownership and a single PostgreSQL database. Deploy the web API and, only if justified, a Celery worker from the same backend codebase. Workers are execution processes, not independent microservices. The React frontend is a separate build artifact.

```text
React + Vite + TypeScript + Tailwind
  React Router / TanStack Query / generated TypeScript API client
                    | HTTPS
FastAPI: identity/access | causes | donations | impact | AI orchestration
  Pydantic contracts -> service layer -> SQLAlchemy 2 -> PostgreSQL
                    |
      optional Redis broker -> Celery worker -> AI provider SDK
                    |                 |
                    +------ durable job/result state in PostgreSQL
```

| Choice | Four-day implementation boundary |
|---|---|
| FastAPI + Pydantic | Versioned API, input/output validation and documented errors; authorization in reusable dependencies/services |
| SQLAlchemy 2 + PostgreSQL | One database; modules own their tables and service interfaces; explicit transaction boundaries |
| Alembic | Version every schema change; backend lead controls migration order and checks clean-database upgrade |
| React + Vite + TypeScript | One frontend; feature folders; responsive core flow |
| Tailwind CSS | Styling tool for the frontend; Python is the backend language |
| React Router | Small explicit route set, protected where needed; configure hosting fallback for direct navigation |
| TanStack Query | Server data, mutations, invalidation and bounded polling; local component state for transient UI |
| OpenAPI-generated TypeScript client | Backend owns schema; regenerate after contract changes; compile/check drift in CI; never edit generated files manually |
| Python provider SDKs | One provider behind an adapter; keys stay server-side; mocked provider in ordinary CI |
| Celery + Redis | Use when jobs must outlive HTTP requests or take too long; decide on Day 1. A worker adds provisioning, retries and observability work |
| pgvector | Defer unless the brief requires similarity retrieval; do not introduce embeddings for ordinary structured filtering |
| pytest / Vitest / Playwright | API/service/security tests, meaningful UI behavior tests and a few complete browser journeys |

Suggested layout, to reconcile with the existing repository before implementation:

```text
backend/app/modules/{identity,causes,donations,impact,ai}/  # routers, schemas, services, models
backend/app/shared/                    # configuration, DB, errors, logging
backend/app/workers/                   # optional Celery entrypoint/tasks
backend/alembic/
backend/tests/
frontend/src/{app,features,components}/
frontend/src/api/generated/
frontend/tests/
docs/
```

Module rules: routers translate HTTP; services enforce business rules; persistence stays behind module services. Avoid direct cross-module table updates and circular imports. Shared code contains infrastructure, not a miscellaneous collection of product logic. Keep business logic usable by HTTP and worker entrypoints.

### AI and asynchronous job contract

Choose synchronous processing only when observed latency fits the hosting/request budget and durable execution is unnecessary. Always bound provider timeout and present a recoverable failure. If queued processing is required, implement this proposed contract:

1. Authorized submission validates ownership/input and persists a job in a database transaction. Return a job identifier and `202 Accepted` once accepted durably.
2. Track `queued`, `running`, `succeeded`, `failed`; store result or a safe error code. Exact route names and schemas are frozen on Day 1.
3. Enqueue after commit; if broker publication fails, mark/reconcile dispatch failure so accepted jobs never disappear silently. An outbox or a small explicit recovery mechanism must be selected and tested.
4. Workers use a conditional state transition or lock to prevent duplicate execution from corrupting results. Assume redelivery; do not promise exactly-once provider billing. Persist correlation IDs and attempt counts.
5. Retry only transient failures with bounded attempts/backoff; do not blindly retry invalid input or authentication failures. Coordinate SDK and Celery retries to avoid multiplying calls.
6. Job reads enforce per-user ownership. The browser polls with backoff and stops at terminal state; refresh resumes from the saved job ID/history.
7. Never pass ORM sessions into worker tasks; load by identifier. Do not hold a database transaction open during a provider call. Document recovery for interrupted/stuck jobs.

For both paths: treat user/model content as untrusted, validate output against a schema, escape rendered content, limit input/output size and concurrency, redact sensitive logs, and record provider usage without recording secrets. A mocked/demo response must be visibly identified and never presented as a live AI result.

## 6. Four-day plan and task breakdown

Timeboxes are estimates for a narrow MVP with available mentors. If the brief is larger, cut scope at kickoff. Each row is an issue-sized unit with one owner; supporting people do not dilute ownership. These are proposed tasks, not created GitHub issues.

| ID / day | Owner | Task and dependency | Required output / acceptance |
|---|---|---|---|
| T01 / D1 morning | Owner | Verify brief, repository and all eight identities; no dependency | Written primary journey, P0 exclusions, named owners, agreed demo scenario |
| T02 / D1 morning | `divineexcel` | Design core flow; depends T01 | Screen/state checklist and minimal visual tokens, reviewed by owner |
| T03 / D1 | Backend lead | Scaffold modules, schema, migration and API contract; depends T01 | API runs, clean database migrates, example payloads and errors documented |
| T04 / D1 | `michael-tech-create` | Provider spike with owner; depends T01 | Measured representative latency/cost, validated sample output, sync/queue decision |
| T05 / D1 | Olayinka | Review data/access threats; depends T01/T03 draft | Security requirements and negative test cases agreed before feature completion |
| T06 / D1 | A | App shell and mocked core states; depends T02/T03 draft | Routes and form/result states work with agreed payloads |
| T07 / D1 | B | Write acceptance matrix and seed scenarios; depends T01 | Happy path, invalid input, access denial and provider failure cases |
| T08 / D1 | C | Fresh setup guide + CI with owner; depends T03/T06 | Reproducible local startup and initial backend/frontend checks |
| T09 / D2 | Backend lead | Persist input/result and enforce access; depends T03/T05 | API success and ownership tests; errors stable; migration reviewed |
| T10 / D2 | `michael-tech-create` | Real AI adapter, validation and bounded failure handling; depends T04/T09 | Mocked tests plus authorized live smoke; safe provider-error behavior |
| T11 / D2 | Owner | Worker/broker/recovery integration if selected; depends T04/T09 | Durable submission, duplicate/restart tests and job status, or documented synchronous decision |
| T12 / D2 | A | Generated client + real API flow; depends T06/T09/T10 | Browser submits and displays persisted result, with UI/UX review |
| T13 / D2 | B | First end-to-end test and bug triage; depends T12 | Browser-to-DB journey evidence; all blockers have an owner |
| T14 / D2 | C | Staging deployment with owner; depends T08–T12 | Stable URL, runtime services configured, health check and demo data |
| T15 / D3 | Olayinka | Security verification and remediation pairing; depends T09–T14 | Cross-user tests pass; secrets/log/CORS checks; blockers closed |
| T16 / D3 | `divineexcel` | Accessibility/responsive/error-state review with A; depends T12 | Core journey keyboard-usable and readable at agreed widths |
| T17 / D3 | B | Failure/recovery regression; depends T10–T14 | Invalid inputs, refresh, provider timeout and optional worker redelivery tested |
| T18 / D3 | Backend lead | Fix integration/data defects; depends T13/T15/T17 | Passing migrations and API suite on release candidate |
| T19 / D3 | C | Verify setup, demo and rollback guide with owner | Another teammate can follow instructions; rollback rehearsed in staging |
| T20 / D4 first half | All, owner coordinates | Fix P0/P1 blockers only; depends D3 gates | Tagged/referenced release candidate; freeze feature scope |
| T21 / D4 second half | B | Full acceptance on deployed candidate; depends T20 | Matrix with pass/fail, environment, revision and evidence links |
| T22 / D4 second half | Owner | Release decision + demo; depends T21/security review | Release notes, known limitations, backup/rollback record and demonstrated P0 journey |

Daily exit gates:

- **D1:** contract, UI states, security assumptions and processing model frozen; everyone can run the app. If this slips, reduce scope immediately.
- **D2:** a complete deployed journey works with the real API, database and provider; no separate unintegrated feature branches counted as completion.
- **D3:** negative cases, security checks, recovery and deployment rehearsal pass; no new features after this gate.
- **D4:** regression, targeted fixes and demonstration. Leave the final quarter of the day for stabilization and rollback buffer.

## 7. Coordination and integration rules

- Kickoff: 30 minutes to agree scope and contracts. Daily: 15-minute start check and 15-minute integration check, with one owner for every blocker. Use the team’s agreed timezone; times are to be scheduled after availability is known.
- Board columns: Ready → In progress → Review → Verify → Done. Each issue carries owner, dependency, acceptance IDs, reviewer and evidence. Limit each person to one active implementation task.
- Report blockers after 30 minutes of focused investigation; include expected behavior, observed behavior, minimal reproduction and needed decision. Mentor pairs immediately if the critical path is blocked.
- Use short branches such as `docs/team-plan` or `feat/<task-id>-<topic>` and small PRs. Target integration at least twice per working day. Owner resolves merge conflicts with the affected author.
- PR body: purpose, task/acceptance IDs, screenshots for UI, tests run, schema/API changes, environment changes and rollback implications. Never put credentials or production data in a PR.
- Backend lead publishes contract changes with example payloads; A regenerates the client in the same integration window. Owner resolves incompatible changes before merge.
- Backend lead sequences migrations; newcomers do not independently rewrite shared migrations. Review generated migrations before applying them.
- Keep a short decision log in this file: date, decision, owner, reason, impact. Only owner changes committed MVP scope after D1.
- Required merge checks: applicable tests, frontend type/build check, migration check for schema changes and generated-client consistency for contract changes. Configure branch protection where permissions allow; do not claim it exists until verified.

## 8. Acceptance matrix

Product examples and any numerical performance budgets must be filled from the brief on Day 1. QA records results against a specific revision and environment. A checkbox without evidence is not a pass.

| ID | Acceptance criterion | Verification / accountable implementer |
|---|---|---|
| AC01 | All eight account identities are confirmed and the actual product journey/scope is documented | Source comparison and kickoff record / owner |
| AC02 | A fresh environment starts using documented steps; database upgrades to current revision without manual edits | Independent setup and migration run / C + backend lead |
| AC03 | Valid representative input completes the agreed journey and persists a retrievable result | Playwright plus DB/API check, refresh included / A + backend lead |
| AC04 | Missing, malformed and oversized input returns documented validation errors; UI preserves useful input | API and UI tests / backend lead + A |
| AC05 | Unauthorized requests are denied; user A cannot read or mutate user B’s objects/jobs | API negative tests using two users / backend lead, security verifies |
| AC06 | AI output matches the agreed schema and meets the agreed representative examples; unsafe/malformed output fails cleanly | Fixture evaluation plus authorized live smoke / AI co-owners |
| AC07 | Provider timeout, quota/auth failures and transient errors have bounded handling; no endless UI spinner | Mocked provider failures and UI test / AI co-owners + A |
| AC08 | If queued, accepted jobs remain visible across refresh/restart; redelivery does not corrupt persisted results; dispatch failures are recoverable | Worker interruption, duplicate delivery and broker-failure tests / owner + backend lead |
| AC09 | Primary flow works with keyboard navigation, visible focus, labels and readable mobile/desktop layouts | Manual review at agreed viewports / `divineexcel`, B verifies |
| AC10 | Client code compiles against current OpenAPI; no secret values enter frontend bundles or repository | Generation/build checks and targeted review / A + security lead |
| AC11 | HTTPS deployment supports deep links and allowed origins; health/readiness checks reveal dependency failures safely | Deployed smoke and dependency failure check / owner + C |
| AC12 | Logs have correlation IDs and useful safe failures; provider budgets/input limits are configured; sensitive payloads and keys are redacted | Configuration and log review / owner + security lead |
| AC13 | Relevant pytest, Vitest and Playwright checks pass on the candidate; no unresolved critical/high security issue or broken P0 case | CI + deployed regression evidence / B, owner accepts |
| AC14 | Backup/restore or disposable-demo-data policy is documented; rollback is rehearsed; limitations are disclosed | Staging rehearsal and release checklist / owner + C |

AC08 may be marked N/A only with the documented synchronous-processing decision. Other criteria may be adapted only through an explicit product/architecture decision with equivalent evidence.

## 9. Release runbook and risk controls

1. Freeze a candidate revision; record environment and dependency versions, outstanding defects and test evidence.
2. Confirm configuration privately: database URL, provider key, allowed origins and auth/session settings; Redis/worker settings only if selected. Commit an example containing names and placeholders only.
3. Back up any non-disposable data and inspect migration compatibility. Prefer additive schema changes; application rollback alone cannot undo an incompatible migration.
4. Apply reviewed migration, deploy API/worker and frontend, check health and run deployed acceptance smoke tests.
5. If smoke fails, stop rollout. Owner restores the prior compatible application version; use a rehearsed data restore if required. Record recovery steps and effects on any jobs/provider calls.
6. Demonstrate the primary journey and a recoverable failure. Publish limitations and handoff notes with links to evidence.

| Risk | Trigger | Response / owner |
|---|---|---|
| Scope exceeds four days | No end-to-end path by end of D2 | Remove P1 and secondary flows; owner protects one P0 journey |
| Senior owners overloaded | Newcomers blocked or reviews waiting | Pair on small tasks, reassign documentation/test work; owner limits simultaneous changes |
| Provider credentials/budget unavailable | D1 spike cannot run | Owner resolves access; use clearly labeled mocked development mode; live AI acceptance stays pending |
| Queue complexity consumes schedule | Durable processing not working by D2 | Owner reevaluates only against measured latency/durability requirements; never silently drop accepted work |
| API/UI drift | Client generation or integration fails | Backend lead and A fix contract together before unrelated work |
| Deployment surprises | No staging journey by D2 | Owner prioritizes hosting/dependencies and cuts features |
| Unknown source requirements | Brief/screenshot still missing | Keep this document provisional; do not claim complete product or eight-account allocation |

## 10. Source-verification and finalization checklist

- [ ] Read the project brief and delivery plan; record filenames/revisions and reconcile their scope with this plan.
- [ ] Read the collaborator screenshot; replace A/B/C with exact handles and verify Olayinka’s handle.
- [ ] Inspect default branch, README, directory tree, manifests, existing architecture docs, CI, issues/PRs and repository instructions.
- [ ] Distinguish existing implementation from proposed work; revise task dependencies and estimates accordingly.
- [ ] Verify collaborator permissions separately from commit contributions; commit authors are not a complete collaborator list.
- [ ] Confirm all eight people’s availability and acknowledge proposed assignments.
- [ ] Set actual dates, timezone, checkpoints, demo environment, product examples and measurable budgets.
- [ ] Add the verified document at the intended repository path through a reviewable branch/PR if write access permits.

### Decision log

| Date | Decision | Owner | Reason / follow-up |
|---|---|---|---|
| 2026-10-23 | Prepare provisional local planning document | Document preparation | Required remote sources unavailable; verify before representing as repository-specific final plan |

## 11. Giving-platform implementation and acceptance

These proposed requirements follow the README and must be reconciled with the brief. Backend lead owns causes, donation records and impact updates. A implements cause listing/detail, checkout return/status, donor history and impact views. Divineexcel owns screen states. Security reviews payment/data access; B tests the complete journey. AI co-owners add a small source-grounded summary only after the donation journey works.

- **D1:** Owner chooses one sandbox provider and currency; backend lead defines schemas and seeds clearly labeled demo causes. Store amounts in integer minor units plus currency.
- **D2:** Backend lead integrates server-created provider-hosted checkout and verified webhooks; A implements checkout/status/history. Server selects authoritative amount and currency. A browser return URL never marks a donation paid.
- **D3:** Security and B verify webhook signatures, duplicate-event idempotency, invalid amount/currency rejection, failed/cancelled payments, delayed processing and cross-user access denial. Owner reconciles provider records with local state.
- **D4:** Demonstrate sandbox success, refresh/history, failure recovery and a published impact update. Clearly label sandbox payments and illustrative data.

| ID | Acceptance criterion | Owner / evidence |
|---|---|---|
| AC15 | Donor can browse seeded causes, purpose, currency and published updates | A / deployed browser test |
| AC16 | Only a verified provider event or authoritative server reconciliation confirms payment; replay cannot double-count a contribution | Backend lead / signature, replay and reconciliation tests; security review |
| AC17 | Pending, failed and cancelled donations remain distinct; history survives refresh with authoritative status | Backend lead + A / sandbox end-to-end tests |
| AC18 | Impact claims link to published sources; labeled AI summaries do not fabricate amounts, beneficiaries or outcomes | AI co-owners / source-grounded evaluation fixtures |
| AC19 | Application does not store raw card data; checkout is provider-hosted | Security lead / integration review |

If provider setup is unavailable, owner may explicitly rescope to a labeled donation-intent demo. This does not satisfy payment acceptance or justify claims of completed donations. Core giving functionality takes priority over optional AI.
