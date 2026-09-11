# Continuous Monitoring Plan

Authorization is a point-in-time judgement about a system that keeps changing.
This plan states what is re-checked, how often, and who acts on the result, so
the authorization stays connected to the system as it actually is.

## What runs automatically

| Activity | Frequency | Mechanism | Fails the build |
|---|---|---|---|
| Unit and behaviour tests | Every push and PR | `ci.yml` → `verify` | Yes |
| Integration against PostgreSQL | Every push and PR | `ci.yml` → `integration` | Yes |
| Migration applies to an empty database | Every push and PR | `ci.yml` → `integration` | Yes |
| Secret scanning, full history | Every push and PR | `security.yml` → `secrets` | Yes |
| Dependency audit of the shipped closure | Every push and PR, plus weekly | `security.yml` → `dependencies` | Yes, at high |
| Mobile dependency risk report | Every push and PR, plus weekly | `security.yml` → `dependencies` | Yes, at critical |
| SBOM generation | Every push and PR | `security.yml` → `dependencies` | No — artifact |
| Control baseline | Every push and PR | `security.yml` → `compliance` | Yes, at high |
| Image build and non-root assertion | Every push and PR | `security.yml` → `container` | Yes |
| Image package scan (Trivy) | Every push and PR, plus weekly | `security.yml` → `container` | Yes, at high |
| IaC misconfiguration scan (Trivy config) | Every push and PR, plus weekly | `security.yml` → `container` | Yes, at high |
| Static analysis (CodeQL) | Every push and PR | `security.yml` → `codeql` | Findings to Security tab |

The weekly schedule exists because advisories are published against code that
has not changed. A repository with no commits for a month is not a repository
with no new vulnerabilities.

## What requires a person

| Activity | Frequency | Owner | Output |
|---|---|---|---|
| Review POA&M items and milestone dates | Monthly | ISSO | Updated `controls/poam.yaml` |
| Re-run `tools/validate_package.py` against the current repository | Monthly, and before any authorization decision | ISSO | Pass, or corrections |
| Review audit-trail coverage against incidents seen | Quarterly | ISSO + engineering | New event types, or a finding |
| Re-confirm inherited controls with the hosting provider | Annually, or on provider change | ISSO | Provider attestation |
| Reassess the threat model | On architecture change, else annually | Engineering | Updated `docs/02-threat-model.md` |
| Restore rehearsal | Annually | Operations | Measured recovery time in the runbook |

## Triggers for reassessment

Any of these invalidates the current assessment until it has been reviewed:

- A new trust boundary: an additional external integration, a new client type,
  or a second service reading the database directly.
- A change in what is stored. The moderate confidentiality rating is based on
  credentials plus behavioural history; adding payment or location data changes
  it.
- Authentication changes, including adopting a hosted identity provider through
  `AUTH_PROVIDER`.
- A critical advisory in the shipped closure.
- Any confirmed incident.

## Reporting

Each pipeline run leaves machine-readable evidence as build artifacts:
`secrets.json`, `deps-api.json`, `deps-mobile.json`, `compliance.json`,
`image-scan.json`, `config-scan.json` and the SBOM. These are the evidence
trail for this package — an assessor reads what the scans actually found rather
than trusting a green check mark.

`compliance.json` feeds `tools/validate_package.py`, which fails if any control
claiming *implemented* is backed by an automated check that is no longer
passing. That is the specific drift this plan exists to prevent.
