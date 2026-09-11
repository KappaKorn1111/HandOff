#!/usr/bin/env python3
"""Export the control matrix and POA&M as CSV for a legacy GRC tool.

eMASS and comparable systems ingest CSV rather than YAML. Producing these from
the same source that `validate_package.py` checks means the record uploaded to
the tool of record cannot quietly diverge from the record in version control.

Column names follow the conventional eMASS import shape. Confirm them against
the importing instance before a real submission -- these layouts vary by
deployment and version, and this script does not talk to eMASS.

Usage:
  python3 tools/export_emass.py --out-dir export/
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    raise SystemExit("PyYAML is required: pip install pyyaml")

PACKAGE_ROOT = Path(__file__).resolve().parent.parent

# eMASS distinguishes compliance from applicability; "Not Applicable" is a
# compliance state, so inherited and system-provided controls both map to
# Compliant with the responsibility carried in its own column.
COMPLIANCE = {
    "implemented": "Compliant",
    "partial": "Non-Compliant",
    "planned": "Non-Compliant",
    "inherited": "Compliant",
    "not-applicable": "Not Applicable",
}

IMPLEMENTATION_STATUS = {
    "implemented": "Implemented",
    "partial": "Partially Implemented",
    "planned": "Planned",
    "inherited": "Inherited",
    "not-applicable": "Not Applicable",
}


def flatten(text: object) -> str:
    return " ".join(str(text or "").split())


def export_controls(sctm: dict, out: Path) -> int:
    controls = sctm.get("controls", [])
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "Control Acronym", "Control Name", "Compliance Status",
            "Implementation Status", "Responsible Entity",
            "Implementation Narrative", "Known Limitations",
            "Evidence", "Automated Checks", "Related POA&M",
        ])
        for control in sorted(controls, key=lambda c: c["id"]):
            evidence = "; ".join(
                f"{entry.get('repo', 'evergreen')}:{entry['path']}"
                for entry in (control.get("evidence") or [])
            )
            writer.writerow([
                control["id"],
                flatten(control.get("title")),
                COMPLIANCE.get(control["status"], "Non-Compliant"),
                IMPLEMENTATION_STATUS.get(control["status"], control["status"]),
                flatten(control.get("responsibility")),
                flatten(control.get("implementation")),
                flatten(control.get("limitation")),
                evidence,
                ", ".join(control.get("automated_checks") or []),
                ", ".join(control.get("poam") or []),
            ])
    return len(controls)


def export_poam(poam: dict, out: Path) -> int:
    items = poam.get("items", [])
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "POAM Item ID", "Control Acronym", "Weakness Description",
            "Weakness Source", "Severity", "Likelihood", "Impact",
            "Residual Risk", "Mitigation / Remediation", "Milestones",
            "Resources Required", "Point of Contact",
            "Scheduled Completion Date", "Status",
        ])
        for item in sorted(items, key=lambda i: i["id"]):
            milestones = "; ".join(
                f"{m.get('date')}: {flatten(m.get('description'))}"
                for m in (item.get("milestones") or [])
            )
            writer.writerow([
                item["id"],
                ", ".join(item.get("controls") or []),
                flatten(item.get("weakness")),
                flatten(item.get("how_found")),
                flatten(item.get("severity")),
                flatten(item.get("likelihood")),
                flatten(item.get("impact")),
                flatten(item.get("risk")),
                flatten(item.get("remediation")),
                milestones,
                "Engineering effort; no procurement identified",
                flatten(item.get("owner")),
                flatten(item.get("scheduled_completion")),
                flatten(item.get("status")).title(),
            ])
    return len(items)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=PACKAGE_ROOT / "export")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    sctm = yaml.safe_load((PACKAGE_ROOT / "controls" / "sctm.yaml").read_text(encoding="utf-8"))
    poam = yaml.safe_load((PACKAGE_ROOT / "controls" / "poam.yaml").read_text(encoding="utf-8"))

    controls_csv = args.out_dir / "emass-controls.csv"
    poam_csv = args.out_dir / "emass-poam.csv"

    n_controls = export_controls(sctm, controls_csv)
    n_items = export_poam(poam, poam_csv)

    print(f"Wrote {controls_csv} ({n_controls} controls)")
    print(f"Wrote {poam_csv} ({n_items} POA&M items)")
    print("\nConfirm the column layout against the importing eMASS instance "
          "before submission; import shapes vary by deployment.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
