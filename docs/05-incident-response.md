# Incident Response Procedure

Written to be usable at 3am by someone who did not build the system.

> **Current state.** The detection half of this procedure is not yet in place:
> there is no alerting and no on-call rotation, and this procedure has never
> been exercised. Tracked as **POAM-003**. Today, detection depends on someone
> reading logs or receiving a report. Everything below the detection step works
> now.

## Severity

| Level | Meaning | Examples |
|---|---|---|
| **SEV-1** | Confirmed unauthorized access to data or credentials | Signing key disclosed; database copied; account takeover confirmed |
| **SEV-2** | Credible path to SEV-1, not yet confirmed exploited | Exploitable vulnerability in the shipped closure; suspected credential stuffing succeeding |
| **SEV-3** | Control failure with no evidence of exploitation | Rate limiting ineffective; audit trail stopped; a scan gate disabled |
| **SEV-4** | Weakness found through review | Scanner finding; dependency advisory with no reachable path |

SEV-1 and SEV-2 are handled immediately. SEV-3 is handled within one working
day. SEV-4 becomes a POA&M item.

## Response

### 1. Detect and record
Note the time, what was seen, and where. Open an incident record immediately —
before investigating, so the timeline is real rather than reconstructed.

Signals worth treating as an incident until proven otherwise:
- A spike in `auth.login` failures against one `subject`, which is one account
  under attack. Across many subjects from one `sourceIp`, it is credential
  stuffing.
- `auth.token.rejected` in volume, which suggests forged or replayed tokens.
- A `config.loaded` record reporting an unexpected `env`, `persistence`, or a
  `trustProxy=true` that nobody enabled.
- Any secret-scan finding on the default branch.

### 2. Contain
Containment precedes diagnosis. Ordered by what is usually fastest:

| Situation | Action |
|---|---|
| Signing key suspected disclosed | Rotate `JWT_SECRET` and restart. Every issued token becomes invalid immediately — this is the one revocation mechanism the system has today (POAM-007). Users re-authenticate. |
| Single account compromised | No per-account revocation exists. Rotating the signing key is currently the only way to invalidate that account's token. Record the gap against POAM-007. |
| Credential stuffing in progress | Lower `RATE_LIMIT_AUTH_MAX` and restart; the limit is configuration, not a code change. Block the source at the edge if it is concentrated. |
| Vulnerable dependency being exploited | Deploy the patched version through the normal pipeline; the gates are the safety net, not an obstacle. Roll back to the previous image digest if no patch exists. |
| Database compromise suspected | Rotate `POSTGRES_PASSWORD`, restart, and preserve a snapshot before any remediation touches the data. |

### 3. Preserve evidence
Do this before remediating; remediation destroys the record.

- Export the audit stream for the window, plus a generous margin either side.
- Capture the running image **digest**, not the tag — tags move.
- Snapshot the database before any schema or data change.
- Record the commit SHA deployed at the time of the incident.

The audit trail is designed for this: records carry a correlation id, the
source address, the outcome, and a pseudonymous subject. The subject is a
SHA-256 digest of the address, so an affected account can be traced through the
logs, and matched to a real user by hashing their address — without any log
line ever containing one.

### 4. Eradicate and recover
Fix the cause, not the symptom. Deploy through the normal pipeline so every
gate runs. Confirm recovery with `/readyz`, which reports the persistence
backend actually in use, and by watching the audit stream for a return to
baseline.

### 5. Review
Within five working days, and never as a search for someone to blame:

- What was the root cause, not the trigger?
- What would have detected this sooner?
- Which control was supposed to prevent it, and why did it not?
- What POA&M items does this create?

Update this procedure with what the incident taught. A procedure that never
changes after an incident was not used.

## Notification

Placeholders until the ISSO binds them:

| Role | Contact | When |
|---|---|---|
| Incident lead | UNASSIGNED | All SEV-1 and SEV-2 |
| System owner | UNASSIGNED | All SEV-1; SEV-2 within 4 hours |
| ISSO | UNASSIGNED | All SEV-1 and SEV-2 |
| Affected users | Per legal guidance | Confirmed disclosure of personal data |

Personal data disclosure carries statutory notification deadlines that vary by
jurisdiction. Involve counsel at the point of confirmation, not after.
