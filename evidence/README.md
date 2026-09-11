# Evidence

Point-in-time output from the automated gates, kept so an assessor can read
what the scans actually found rather than trusting a green check mark.

| File | Produced by | Regenerate |
|---|---|---|
| `compliance.json` | `scripts/compliance_scan.py` in Evergreen | `cd ../evergreen && python3 scripts/compliance_scan.py --json-out ../HandOff/evidence/compliance.json` |

Evidence is a snapshot, not a live view. `compliance.json` here reflects the
Evergreen commit it was generated from; the pipeline regenerates it on every
run and `tools/validate_package.py` reads it to confirm that no control
claiming *implemented* is backed by a check that has since started failing.

Reports produced only in CI — dependency closure audits, the SBOM, image and
IaC scans — are retained as build artifacts rather than committed here, because
they change on every run and are large. `docs/04-continuous-monitoring.md`
lists them.
