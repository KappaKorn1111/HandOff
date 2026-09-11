# Operations Runbook

Deploying, configuring and recovering the Evergreen API.

## Configuration

Every setting is validated at startup. The process exits **78** (`EX_CONFIG`)
with the specific reason rather than serving traffic under a configuration that
cannot be trusted. A failed deploy that says why beats a running service with
forgeable tokens.

| Variable | Required in production | Notes |
|---|---|---|
| `NODE_ENV` | yes | `production` enables HSTS and the strict CORS rules |
| `DATABASE_URL` | yes | Refuses to start without it; the in-memory store loses data on restart |
| `JWT_SECRET` | yes | ≥ 32 bytes, and not a placeholder published in the repository |
| `PORT` | no | Default 3000 |
| `TOKEN_TTL_SECONDS` | no | Default 7 days, capped at 30 |
| `CORS_ALLOWED_ORIGINS` | no | Exact origins, comma-separated. `*` and `http://` are rejected in production |
| `TRUST_PROXY` | no | Default `false`. Only enable behind a proxy that **overwrites** `X-Forwarded-For` |
| `MAX_BODY_BYTES` | no | Default 64 KiB |
| `RATE_LIMIT_*` | no | Window, auth limit, global limit |
| `HSTS_MAX_AGE_SECONDS` | no | Default 180 days |

```bash
openssl rand -base64 48     # JWT_SECRET
openssl rand -base64 24     # POSTGRES_PASSWORD
```

### TRUST_PROXY is a security decision

With `TRUST_PROXY=true` the API believes `X-Forwarded-For` when identifying a
caller. If nothing in front of the service overwrites that header, any client
can set it freely, rotate it per request, and walk straight around the rate
limiter. Enable it only when a proxy you control terminates every request.

## Deploying

Migrations run as a **separate step that completes before the service starts**.
They are deliberately not in the container's `CMD`: every replica starting at
once would race on the same schema.

```bash
node packages/db/dist/migrate.js    # once, to completion
node apps/api/dist/index.js         # then start replicas
```

`docker-compose.yml` encodes this: the `migrate` service runs to completion and
`api` waits on `service_completed_successfully`.

```bash
cp .env.example .env        # fill in JWT_SECRET and POSTGRES_PASSWORD
docker compose up --build   # compose refuses to start if either is unset
```

Deploy by image **digest**, never by tag. A tag can be moved; a digest is the
artifact that was tested.

## Health

| Endpoint | Purpose | Behaviour |
|---|---|---|
| `/health` | Liveness | Returns 200 while the process is serving. Never rate limited |
| `/readyz` | Readiness | Also reports which persistence backend is in use |

`/readyz` reporting `"persistence": "memory"` in production means
`DATABASE_URL` was not set. In production the process would have refused to
start, so seeing this means `NODE_ENV` is not `production` either. Treat it as
an incident: the service is running unhardened and losing data on restart.

## Rollback

The service is stateless, so rolling back is redeploying the previous image
digest.

Migrations are the exception and need thought **before** deploying:

- **Additive** — new table, new nullable column, new index. Safe to roll back;
  the old code ignores what it does not know about.
- **Destructive** — dropped or renamed column, narrowed type, tightened
  constraint. **Not reversible by redeploying.** Use an expand/contract
  sequence: add the new shape, deploy code that writes both, backfill, deploy
  code that reads the new shape, and only then drop the old one in a later
  release. Each step is independently reversible.

Never write a `DROP COLUMN` into the same release that stops using it.

## Recovery

> **Unverified.** No restore has been performed from this system's backups, so
> the recovery time below is an estimate and the integrity of a restored points
> ledger is unconfirmed. An untested restore is not a recovery capability.
> Tracked as **POAM-004**.

1. Provision a PostgreSQL instance and restore the most recent backup.
2. Apply migrations — they are idempotent and will no-op if the restore is
   current.
3. Point `DATABASE_URL` at the restored instance and start the service.
4. Verify with `/readyz` and by running the integration suite against it:
   `TEST_DATABASE_URL=... npx vitest run src/__tests__/postgres.integration.test.ts --root apps/api`
5. Record the measured recovery time here, replacing this warning.

## Rotating secrets

**`JWT_SECRET`** — rotating invalidates every issued token immediately and all
users re-authenticate. This is disruptive, and it is also the only revocation
mechanism the system currently has (POAM-007), so it is the correct response to
a suspected key disclosure.

**`POSTGRES_PASSWORD`** — change it at the database, then restart the service
with the new value. There is a brief window where connections fail; drain
traffic first if that matters.

## Reading the audit trail

Security events are single-line JSON on stdout, tagged
`"kind":"security_audit"`.

```bash
docker compose logs api | grep security_audit | jq 'select(.event=="auth.login" and .outcome=="failure")'
```

`subject` is a SHA-256 digest of the email address, not the address itself. To
find a specific user's events, hash theirs and match:

```bash
printf '%s' 'user@example.com' | sha256sum | cut -c1-16
```

This is why addresses are not written to logs: the records stay useful for
tracing an incident without the log stream itself becoming a store of personal
data.
