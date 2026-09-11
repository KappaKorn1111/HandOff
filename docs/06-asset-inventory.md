# Asset Inventory

What exists, who is responsible for it, and what it is worth protecting. The
categorization in `controls/sctm.yaml` rests on the data assets listed here.

## Software components

| Component | Version | Role | In the boundary |
|---|---|---|---|
| `@evergreen/api` | 0.1.0 | HTTP API | Yes |
| `@evergreen/core` | 0.1.0 | Shared schemas, error codes, points rules | Yes |
| `@evergreen/db` | 0.1.0 | Schema, migrations, seed | Yes |
| `@evergreen/mobile` | 0.1.0 | Expo client | Data in transit only |

## Runtime dependencies

The API's production closure is **36 packages**, resolved exactly from the
lockfile rather than from the hoisted workspace tree. Currently zero open
advisories. Re-check with `npm run scan:deps`.

| Package | Version | Purpose | Security relevance |
|---|---|---|---|
| `hono` | 4.13.7 | HTTP router and middleware | Request handling boundary |
| `@hono/node-server` | 1.19.17 | Node adapter | Exposes the peer address used for rate limiting |
| `bcryptjs` | 2.4.3 | Password hashing | Credential storage |
| `jsonwebtoken` | 9.0.3 | Token signing and verification | Authentication |
| `zod` | 3.25.76 | Schema validation | Every input boundary |
| `drizzle-orm` | 0.45.2 | Database access | Upgraded past GHSA-gpj5-g38j-94v9 |
| `pg` | 8.23.0 | PostgreSQL driver | Database connection |

The mobile closure is **690 packages** with 30 open advisories, including
critical `node-tar`. None of it is installed in the API container; it executes
on developer machines and CI runners. Tracked as POAM-006.

## Infrastructure

| Asset | Description | Owner |
|---|---|---|
| Container image | `apps/api/Dockerfile`, non-root, digest-pinned base | Engineering |
| PostgreSQL 16 | Persistent store | Hosting provider |
| Container platform | Scheduling, isolation, networking | Hosting provider |
| TLS termination | Edge certificates and ciphers | Hosting provider |
| Log pipeline | Collection and retention of the audit stream | Hosting provider |
| CI pipeline | GitHub Actions workflows | Engineering |

## Data assets

| Asset | Classification | Store | Retention |
|---|---|---|---|
| Account credentials | Sensitive | `users.password_hash` | Life of account |
| Email addresses | Personal data | `users.email` | Life of account |
| Impact history | Personal data | `impact_entries` | Life of account — **no policy set** |
| Points ledger | Personal, value-bearing | `points_ledger` | Life of account — append-only |
| Redemptions | Personal, value-bearing | `redemptions` | Life of account |
| Reference content | Public | `tips`, `products`, `rewards`, `places` | Indefinite |
| Audit events | Operational, pseudonymised | Platform log stream | **Provider default — not set deliberately** |

Two retention gaps are recorded above rather than left implicit. Personal data
held indefinitely by default is a policy decision nobody has made, and audit
retention that defaults to whatever the provider does is not a retention
decision either. Both belong in the ISSO's review; neither is a code change.

## Secrets

| Secret | Where it lives | Rotation |
|---|---|---|
| `JWT_SECRET` | Platform secret store | Invalidates all tokens; also the only revocation mechanism today (POAM-007) |
| `POSTGRES_PASSWORD` | Platform secret store | Brief connection failure window; drain first |
| Registry credentials | CI secret store | Per provider policy |

No secret is committed, baked into an image layer, or written to a log. The
compose file takes both as required inputs and refuses to start without them;
`scripts/secret_scan.py` enforces this on every pull request.

## Interfaces

| Interface | Direction | Authentication |
|---|---|---|
| `/health`, `/readyz` | Inbound | None — probes are never rate limited |
| `/v1/auth/*` | Inbound | None to obtain a token; stricter rate-limit bucket |
| `/v1/impact/*`, `/v1/rewards/balance`, `/v1/rewards/:id/redeem`, `/v1/scan/:barcode` | Inbound | Bearer token |
| `/v1/tips`, `/v1/places`, `/v1/rewards` | Inbound | None — public content |
| PostgreSQL | Outbound | Password, container network only |

There are no outbound third-party integrations. Every external interface is
inbound HTTP, which keeps the attack surface to one protocol and one boundary.
