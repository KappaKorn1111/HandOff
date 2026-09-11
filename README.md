# HandOff — Evergreen Authorization Package

The security documentation for [Evergreen](https://github.com/KappaKorn1111/evergreen),
structured for Risk Management Framework use and built so it can be checked by
a machine rather than only read.

Control packages rot. Someone deletes the file an evidence line points at, a
control keeps claiming *implemented* after its automated check started failing,
a weakness gets referenced but never written down — and the document still reads
as though everything is fine. This package is arranged so those failures are
caught instead of accumulating.

## How it fits together

```
controls/sctm.yaml    ← source of truth for control implementation
controls/poam.yaml    ← every known weakness, with a plan
       │
       ├── tools/validate_package.py   checks claims against the real repository
       ├── tools/render_sctm.py        → docs/CONTROL-MATRIX.md
       └── tools/export_emass.py       → CSV for eMASS or another GRC tool
```

Edit the YAML. Everything else is generated from it or checked against it.

## Validating

```bash
pip install pyyaml

# Generate the compliance report from the Evergreen repository
cd ../evergreen && python3 scripts/compliance_scan.py --json-out ../HandOff/evidence/compliance.json

cd ../HandOff
python3 tools/validate_package.py --compliance evidence/compliance.json
python3 tools/render_sctm.py --check
```

`validate_package.py` fails when:

- an evidence path no longer exists in the repository it names
- a control claiming *implemented* is backed by an automated check that is not
  passing
- a control is partial or planned without citing a POA&M item, or without
  stating its limitation
- a cited POA&M item does not exist, or a POA&M item has no milestones

It warns — without failing — on unassigned owners, past-due milestones, and
POA&M items referencing controls the matrix does not document, so a package can
be validated while it is still being filled in.

## Contents

| Document | What it answers |
|---|---|
| [`docs/01-system-security-plan.md`](docs/01-system-security-plan.md) | What the system is, how it is categorized, where the boundary runs, and what the residual risk is |
| [`docs/02-threat-model.md`](docs/02-threat-model.md) | What an attacker would try, what stops them today, and what is still open |
| [`docs/03-architecture-views.md`](docs/03-architecture-views.md) | DODAF viewpoints: OV-1, SV-1, SV-2, StdV-1, DIV-2 |
| [`docs/04-continuous-monitoring.md`](docs/04-continuous-monitoring.md) | What is re-checked, how often, by whom |
| [`docs/05-incident-response.md`](docs/05-incident-response.md) | What to do at 3am, written for someone who did not build it |
| [`docs/06-asset-inventory.md`](docs/06-asset-inventory.md) | What exists and what it is worth protecting |
| [`docs/07-operations-runbook.md`](docs/07-operations-runbook.md) | Configuring, deploying, rolling back, recovering |
| [`docs/CONTROL-MATRIX.md`](docs/CONTROL-MATRIX.md) | Generated — every control, status, evidence and limitation |
| [`controls/sctm.yaml`](controls/sctm.yaml) | The control record itself |
| [`controls/poam.yaml`](controls/poam.yaml) | The weakness record itself |

## Current position

**30 controls** — 17 implemented, 8 partial, 2 planned, 2 inherited, 1 not applicable. **10 POA&M items**, one at high residual risk.

That high item is worth stating plainly: the system produces a well-structured
audit trail and nothing consumes it. There is no alerting and no exercised
response procedure, so an attack in progress would not currently be noticed.
That is a larger risk than any single missing technical control.

## What this package does not do

- **STIG rule identifiers are deliberately absent.** They are re-numbered
  between STIG releases, so a number frozen into a file is wrong as soon as the
  next release ships. `controls/sctm.yaml` carries the field; the ISSO binds it
  against the release in force at assessment.
- **Inherited controls are not verified.** Encryption at rest, backup retention
  and TLS configuration are the hosting provider's and are recorded as
  assumptions until a written attestation exists.
- **It does not grant an authorization.** It is the evidence an authorizing
  official would need, assembled and kept honest.
