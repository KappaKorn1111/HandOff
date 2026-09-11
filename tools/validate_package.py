#!/usr/bin/env python3
"""Check that this authorization package describes the system that exists.

A control package rots quietly. Someone deletes the file an evidence line
points at, a control keeps claiming "implemented" after its automated check
started failing, a POA&M item is referenced but never written -- and the
document still reads as though everything is fine.

This validates the parts a machine can check:

  * every evidence path resolves to a real file or directory in the Evergreen
    repository
  * every control that is partial or planned cites a POA&M item, and every
    cited item exists
  * every automated check named by a control exists in the compliance scan
    output, and is passing wherever the control claims to be implemented
  * required fields are present and statuses are from the allowed set

Warnings (owners still unassigned, milestones past due) are reported but do not
fail the run, so a draft package can be validated while it is being filled in.

Usage:
  python3 tools/validate_package.py
  python3 tools/validate_package.py --evergreen ../evergreen --compliance report.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    raise SystemExit("PyYAML is required: pip install pyyaml")

PACKAGE_ROOT = Path(__file__).resolve().parent.parent

VALID_STATUSES = {"implemented", "partial", "planned", "inherited", "not-applicable"}
NEEDS_POAM = {"partial", "planned"}
VALID_RESPONSIBILITY = {"system", "provider", "shared"}
VALID_RISK = {"low", "medium", "high", "critical"}

# NIST SP 800-53 control identifier, with optional enhancement: AC-7, SC-28(1)
CONTROL_ID_RE = re.compile(r"^[A-Z]{2}-\d{1,2}(\(\d{1,2}\))?$")
POAM_ID_RE = re.compile(r"^POAM-\d{3}$")


class Report:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_controls(
    sctm: Dict[str, Any],
    poam_ids: set,
    evergreen: Optional[Path],
    checks: Dict[str, str],
    report: Report,
) -> None:
    controls = sctm.get("controls") or []
    if not controls:
        report.error("sctm.yaml defines no controls")
        return

    seen: set = set()
    for control in controls:
        ident = control.get("id", "<missing id>")

        if not CONTROL_ID_RE.match(str(ident)):
            report.error(f"{ident}: not a valid NIST SP 800-53 control identifier")
        if ident in seen:
            report.error(f"{ident}: duplicated in the matrix")
        seen.add(ident)

        for field in ("title", "status", "responsibility", "implementation"):
            if not control.get(field):
                report.error(f"{ident}: missing required field '{field}'")

        status = control.get("status")
        if status not in VALID_STATUSES:
            report.error(f"{ident}: status {status!r} is not one of {sorted(VALID_STATUSES)}")
        if control.get("responsibility") not in VALID_RESPONSIBILITY:
            report.error(f"{ident}: responsibility must be one of {sorted(VALID_RESPONSIBILITY)}")

        # A control that is not fully satisfied has to say what is being done
        # about it, and point at the item that tracks it.
        cited = control.get("poam") or []
        if status in NEEDS_POAM and not cited:
            report.error(f"{ident}: status '{status}' but cites no POA&M item")
        if (status in NEEDS_POAM or cited) and not control.get("limitation"):
            report.error(
                f"{ident}: cites a weakness or is not fully satisfied, but states no limitation"
            )
        for item in cited:
            if not POAM_ID_RE.match(str(item)):
                report.error(f"{ident}: malformed POA&M reference {item!r}")
            elif item not in poam_ids:
                report.error(f"{ident}: cites {item}, which does not exist in poam.yaml")

        # Evidence has to point at something real.
        evidence = control.get("evidence") or []
        if status in {"implemented", "partial"} and not evidence:
            report.error(f"{ident}: status '{status}' but cites no evidence")
        for entry in evidence:
            path = entry.get("path")
            if not path:
                report.error(f"{ident}: evidence entry has no path")
                continue
            if not entry.get("note"):
                report.warn(f"{ident}: evidence '{path}' has no note explaining what it shows")

            # Evidence lives in the implementing repository or in this package.
            where = entry.get("repo", "evergreen")
            if where == "handoff":
                if not (PACKAGE_ROOT / path).exists():
                    report.error(f"{ident}: evidence path does not exist in this package: {path}")
            elif where == "evergreen":
                if evergreen and not (evergreen / path).exists():
                    report.error(f"{ident}: evidence path does not exist in Evergreen: {path}")
            else:
                report.error(f"{ident}: evidence repo {where!r} must be 'evergreen' or 'handoff'")

        # An implemented control whose own automated check is failing is the
        # exact drift this validator exists to catch.
        for check_id in control.get("automated_checks") or []:
            if not checks:
                continue
            if check_id not in checks:
                report.error(f"{ident}: names automated check {check_id}, which the compliance scan does not define")
            elif status == "implemented" and checks[check_id] != "PASS":
                report.error(
                    f"{ident}: claims 'implemented' but automated check {check_id} reports {checks[check_id]}"
                )


def validate_poam(poam: Dict[str, Any], control_ids: set, report: Report) -> set:
    items = poam.get("items") or []
    if not items:
        report.warn("poam.yaml lists no items")
    today = dt.date.today()
    seen: set = set()

    for item in items:
        ident = item.get("id", "<missing id>")
        if not POAM_ID_RE.match(str(ident)):
            report.error(f"{ident}: POA&M id must look like POAM-001")
        if ident in seen:
            report.error(f"{ident}: duplicated in the POA&M")
        seen.add(ident)

        for field in ("title", "weakness", "remediation", "severity", "risk", "status"):
            if not item.get(field):
                report.error(f"{ident}: missing required field '{field}'")

        if item.get("risk") not in VALID_RISK:
            report.error(f"{ident}: risk must be one of {sorted(VALID_RISK)}")

        for control in item.get("controls") or []:
            if control not in control_ids:
                report.warn(f"{ident}: references control {control}, which is not in the matrix")

        milestones = item.get("milestones") or []
        if not milestones:
            report.error(f"{ident}: has no milestones, so there is no plan of action")
        for milestone in milestones:
            if not milestone.get("date") or not milestone.get("description"):
                report.error(f"{ident}: milestone needs both a date and a description")

        if item.get("owner") in (None, "", "UNASSIGNED"):
            report.warn(f"{ident}: owner is unassigned")

        due = item.get("scheduled_completion")
        if due and item.get("status") == "open":
            try:
                if dt.date.fromisoformat(str(due)) < today:
                    report.warn(f"{ident}: scheduled completion {due} has passed and the item is still open")
            except ValueError:
                report.error(f"{ident}: scheduled_completion {due!r} is not an ISO date")

    return seen


def resolve_evergreen(path: Optional[Path], report: Report) -> Optional[Path]:
    """Return the Evergreen checkout, or None when it is not really there.

    A failed `actions/checkout` still leaves the target directory behind, with
    a .git and nothing else. Treating that as a present repository made every
    evidence path look missing and produced "the package does not match the
    system it describes" -- a confident, wrong answer that took a CI log to
    disprove. A tool that cannot verify must say so, not invent 59 failures.
    """
    if path is None or not path.exists():
        report.warn(f"Evergreen repository not found at {path}; evidence paths were NOT verified")
        return None

    # Sentinel: the repository root manifest. Present in any real checkout,
    # absent from an empty directory left by a failed one.
    manifest = path / "package.json"
    if not manifest.exists():
        report.warn(
            f"{path} exists but holds no Evergreen checkout (package.json missing) — "
            "evidence paths were NOT verified. If this is CI, the repository is private "
            "and the workflow token cannot read it; supply a read token."
        )
        return None

    if '"name": "evergreen"' not in manifest.read_text(encoding="utf-8", errors="replace"):
        report.warn(f"{path} does not look like the Evergreen repository — evidence paths were NOT verified")
        return None

    return path


def load_compliance(path: Optional[Path], report: Report) -> Dict[str, str]:
    if path is None:
        return {}
    if not path.exists():
        report.warn(f"compliance report not found at {path}; control/check cross-checks were skipped")
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {check["id"]: check["status"] for check in data.get("checks", [])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evergreen", type=Path, default=PACKAGE_ROOT.parent / "evergreen",
                        help="path to the Evergreen repository (evidence paths resolve against it)")
    parser.add_argument("--compliance", type=Path,
                        help="compliance_scan.py --json-out report, for control/check cross-checks")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = parser.parse_args()

    report = Report()

    evergreen = resolve_evergreen(args.evergreen, report)

    sctm = load_yaml(PACKAGE_ROOT / "controls" / "sctm.yaml")
    poam = load_yaml(PACKAGE_ROOT / "controls" / "poam.yaml")
    checks = load_compliance(args.compliance, report)

    control_ids = {c.get("id") for c in (sctm.get("controls") or [])}
    poam_ids = validate_poam(poam, control_ids, report)
    validate_controls(sctm, poam_ids, evergreen, checks, report)

    # Prose that states control counts drifts the moment a control is added.
    # Catch it here rather than letting the narrative disagree with the matrix.
    counts = Counter(c.get("status") for c in (sctm.get("controls") or []))
    expected = (
        f"{counts['implemented']} implemented, {counts['partial']} partial, "
        f"{counts['planned']} planned, {counts['inherited']} inherited, "
        f"{counts['not-applicable']} not applicable"
    )
    for doc in ("docs/01-system-security-plan.md", "README.md"):
        path = PACKAGE_ROOT / doc
        if not path.exists():
            continue
        text = " ".join(path.read_text(encoding="utf-8").split())
        if "implemented," in text and expected not in text:
            report.error(
                f"{doc}: states control counts that disagree with the matrix; expected \"{expected}\""
            )

    # Every recorded weakness should be visible from the control it weakens.
    cited_anywhere = {p for c in (sctm.get("controls") or []) for p in (c.get("poam") or [])}
    for orphan in sorted(poam_ids - cited_anywhere):
        report.warn(f"{orphan}: not referenced by any control in the matrix")

    controls = sctm.get("controls") or []
    print(f"Package  : {sctm.get('system', {}).get('name', '?')} ({sctm.get('system', {}).get('identifier', '?')})")
    print(f"Controls : {len(controls)}")
    print(f"POA&M    : {len(poam_ids)} item(s)")
    print(f"Evidence : {'verified against ' + str(evergreen) if evergreen else 'NOT VERIFIED — see warnings'}")
    print(f"Checks   : {len(checks) or 'none supplied'}")

    if report.warnings:
        print(f"\n{len(report.warnings)} warning(s):")
        for warning in report.warnings:
            print(f"  warn  {warning}")

    if report.errors:
        print(f"\n{len(report.errors)} error(s):")
        for error in report.errors:
            print(f"  ERROR {error}")
        print("\nFAIL: the package does not match the system it describes.")
        return 1

    if args.strict and report.warnings:
        print("\nFAIL: warnings present and --strict was requested.")
        return 1

    # Say exactly what was checked. "every evidence path resolves" is a lie
    # when the repository holding those paths was never read.
    if evergreen:
        print("\nPASS: every evidence path resolves, every claim is backed, every weakness is tracked.")
    else:
        print("\nPARTIAL PASS: structure, claims and weakness tracking are sound, "
              "but evidence paths were NOT verified — see the warnings above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
