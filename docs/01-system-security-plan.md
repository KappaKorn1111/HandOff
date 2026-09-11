# System Security Plan

**System:** Evergreen (EVG-001)
**Baseline date:** 2026-09-11

## 1. System description

Evergreen helps people reduce household waste. Someone logs the waste they
avoided, scans a product to see lower-impact alternatives, reads guidance in
English or Chinese, finds local refill stations, and redeems accumulated points
for rewards.

The system is an Expo/React Native client, a Hono HTTP API on Node.js 20, and
PostgreSQL 16. All four workspaces live in one repository; the API and its
shared packages are built into a single OCI container image.

## 2. Categorization

Rated under FIPS 199 against the data actually held.

| Objective | Level | Basis |
|---|---|---|
| Confidentiality | **Moderate** | Stores authentication credentials and a per-user behavioural history that is personal data |
| Integrity | **Moderate** | The points ledger is money-like; an unauthorised credit or debit has direct value |
| Availability | **Low** | Discretionary service; an outage causes inconvenience, not harm |

No financial instrument, health record, or government information is processed.
Adding payment or location data would change the confidentiality rating and
require reassessment.

## 3. Authorization boundary

**Inside.** The API process; the PostgreSQL database and its schema; the
container image; the CI pipeline that builds and scans it. The mobile client is
in scope for the data it handles in transit.

**Outside, inherited.** TLS termination and certificate management; the
container platform and host operating system; network edge protection; the log
collection and retention service; database backup infrastructure.

Inherited controls are marked as such in the traceability matrix and must be
confirmed against the hosting provider's own attestation. They are not assumed
satisfied because they are someone else's.

## 4. Architecture

See `03-architecture-views.md` for the operational concept, interface
description, resource flows, standards profile, and logical data model.

Two design decisions carry most of the security weight:

**Configuration fails closed.** Every setting is validated before the process
serves traffic, and an unsafe production configuration exits 78 with the reason
named. This is what stands between a forgotten environment variable and a
deployment signing tokens with a key printed in the repository — the exact
condition that existed before this baseline.

**Contracts are shared, not duplicated.** Request and response shapes are zod
schemas in `@evergreen/core`, used by the API for validation and by the client
for types. The two cannot drift into disagreeing about what input is valid.

## 5. Control implementation

The authoritative record is `controls/sctm.yaml`. `docs/CONTROL-MATRIX.md` is
rendered from it and should not be edited directly.

**30 controls documented:** 17 implemented, 8 partial, 2 planned, 2 inherited, 1 not applicable.

Summarised by family:

| Family | Position |
|---|---|
| **AC** Access control | Queries scoped to the authenticated principal; exact-origin CORS allowlist; least privilege in container and pipeline. Session termination is not implemented (POAM-007) |
| **AU** Audit | A closed set of security events carrying the six facts AU-3 requires, with addresses pseudonymised. Retention is inherited |
| **CA** Assessment | Gates run per change and weekly; each writes machine-readable evidence |
| **CM** Configuration | Lockfile plus `npm ci`; base image pinned by digest; settings validated at startup; runtime image carries no build tooling |
| **CP** Contingency | Application state reproduces from image and migrations. Backup and restore are inherited and unexercised (POAM-004) |
| **IA** Identification | bcrypt cost 12; no default signing key anywhere in the tree; HS256 pinned with issuer checked; login does not disclose which accounts exist |
| **IR** Incident response | Procedure written and audit data available. No alerting, no exercise (POAM-003) |
| **RA** Risk assessment | Shipped dependency closure resolved exactly and gated; image and IaC scanning in the pipeline |
| **SA** Acquisition | 95 automated tests, 47 covering security behaviour; database behaviour verified against real PostgreSQL |
| **SC** Communications | Response hardening headers; bounded bodies; rate limiting; only reviewed cryptographic primitives. Field-level encryption not implemented (POAM-005) |
| **SI** Integrity | Shared-schema validation with database constraints behind it; errors disclose nothing across the trust boundary |

## 6. Risk

Ten POA&M items, in `controls/poam.yaml`. Each was reproduced or is a stated
limitation of a control that was implemented; none is hypothetical.

| Residual risk | Items |
|---|---|
| High | POAM-003 (no alerting or exercised incident response) |
| Medium | POAM-001, 002, 004, 005, 006, 007, 010 |
| Low | POAM-008, 009 |

The highest residual risk is not a missing technical control — it is that
nobody would currently notice an attack in progress. The system produces the
evidence; nothing consumes it.

## 7. Assessment

Continuous, not periodic. Every pull request runs the tests, integration
against a real database, secret scanning, dependency audit of the shipped
closure, the control baseline, an image build with a non-root assertion, image
and IaC scanning, and static analysis. The same gates re-run weekly, because
advisories are published against code that has not changed.

`tools/validate_package.py` ties this document to reality: it fails if any
evidence path no longer exists, if any control claiming *implemented* is backed
by an automated check that has started failing, or if any weakness is recorded
without being tracked. Run it before any authorization decision.

## 8. Known weaknesses in this plan

Stated here rather than left for an assessor to find.

- **The container image has never been built.** The Dockerfile was authored
  without a Docker daemon available. Each stage was replicated on disk and the
  assembled runtime layer was booted successfully, but that is not a real build
  (POAM-010).
- **Pipeline actions resolve by mutable tag.** SHAs could not be resolved in
  the authoring environment, and inventing them would have been worse than
  leaving them (POAM-002).
- **Inherited controls rest on assumption.** No provider attestation has been
  obtained for encryption at rest, backup retention, or TLS configuration.
- **STIG rule identifiers are absent by design.** They are re-numbered between
  releases; binding them belongs with the ISSO against the release in force at
  assessment. The matrix carries the field to hold them.
- **POA&M owners are unassigned.** Every item carries `UNASSIGNED`, and the
  validator reports each one. A milestone with no owner is a wish.
