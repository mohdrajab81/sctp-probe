#!/usr/bin/env python3
"""Fixture validation CLI.

Usage:
    python tests/validate_fixtures.py --fixtures-dir /path/to/fixtures

Reads all *.bin files paired with *.expected.json files, runs decode(),
compares key fields, prints a pass/fail table, and exits non-zero if any
fixture fails.

Known failures are documented and treated as expected-fail (xfail) — they
appear in the table as XFAIL rather than FAIL and do not affect the exit code.
"""
import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root without installing the package
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sctp_probe.decoder import decode  # noqa: E402

# -----------------------------------------------------------------------
# Fixtures with known decode limitations — pycrate cannot parse them.
# These are treated as expected failures (xfail) and documented below.
# -----------------------------------------------------------------------
_KNOWN_FAILURES: dict[str, str] = {
    "swi_cancelled_and_empty": (
        "pycrate error: invalid undef count value (54). "
        "SWI PDU with both BroadcastCancelledAreaList and BroadcastEmptyAreaList "
        "triggers an unhandled count constraint in pycrate 0.7.11."
    ),
}

# PDU type inferred from fixture name prefix
_FILENAME_TO_PDU_TYPE: dict[str, str] = {
    "wrr_req": "WRR_REQ",
    "wrr_resp": "WRR_RESP",
    "swr_req": "SWR_REQ",
    "swr_resp": "SWR_RESP",
    "err_ind": "ERR_IND",
    "wrwi":    "WRWI",
    "swi":     "SWI",
}


def _expected_pdu_type(stem: str) -> str | None:
    for prefix, pdu in _FILENAME_TO_PDU_TYPE.items():
        if stem.startswith(prefix):
            return pdu
    return None


def _mi_int(expected: dict) -> int | None:
    v = expected.get("MessageIdentifier")
    return int(v) if isinstance(v, int) else None


def _sn_int(expected: dict) -> int | None:
    v = expected.get("SerialNumber")
    if isinstance(v, int):
        return v
    if isinstance(v, dict):
        raw = v.get("Raw")
        return int(raw) if isinstance(raw, int) else None
    return None


def _hex_to_int(hex_str: str | None) -> int | None:
    if hex_str is None:
        return None
    try:
        return int(hex_str, 16)
    except (ValueError, TypeError):
        return None


def _run_fixture(bin_path: Path, json_path: Path) -> dict:
    stem = bin_path.stem
    raw = bin_path.read_bytes()
    expected = json.loads(json_path.read_text())

    result = {
        "name": stem,
        "status": "PASS",
        "failures": [],
        "xfail_reason": None,
    }

    is_known_failure = stem in _KNOWN_FAILURES
    if is_known_failure:
        result["xfail_reason"] = _KNOWN_FAILURES[stem]

    decoded = decode(raw)

    # --- check 1: protocol field
    if decoded.protocol == "raw":
        if is_known_failure:
            result["status"] = "XFAIL"
            return result
        result["status"] = "FAIL"
        result["failures"].append("decode fell back to raw (pycrate error)")
        return result

    # --- check 2: pdu_type
    expected_pdu = _expected_pdu_type(stem)
    if expected_pdu and decoded.pdu_type != expected_pdu:
        result["failures"].append(
            f"pdu_type: expected {expected_pdu!r}, got {decoded.pdu_type!r}"
        )

    # --- check 3: message_identifier (if present in expected)
    exp_mi = _mi_int(expected)
    if exp_mi is not None:
        got_mi = _hex_to_int(decoded.message_identifier)
        if got_mi != exp_mi:
            result["failures"].append(
                f"message_identifier: expected {exp_mi} (0x{exp_mi:04x}), "
                f"got {decoded.message_identifier!r}"
            )

    # --- check 4: serial_number (if present in expected as int or {Raw:int})
    exp_sn = _sn_int(expected)
    if exp_sn is not None:
        got_sn = _hex_to_int(decoded.serial_number)
        if got_sn != exp_sn:
            result["failures"].append(
                f"serial_number: expected {exp_sn} (0x{exp_sn:04x}), "
                f"got {decoded.serial_number!r}"
            )

    if result["failures"]:
        result["status"] = "XFAIL" if is_known_failure else "FAIL"

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate sctp-probe decoder against fixtures")
    parser.add_argument(
        "--fixtures-dir",
        required=True,
        type=Path,
        help="Directory containing .bin and .expected.json fixture pairs",
    )
    args = parser.parse_args()

    fixtures_dir: Path = args.fixtures_dir
    if not fixtures_dir.is_dir():
        print(f"ERROR: fixtures-dir does not exist: {fixtures_dir}", file=sys.stderr)
        return 2

    bin_files = sorted(fixtures_dir.glob("*.bin"))
    if not bin_files:
        print(f"ERROR: no .bin files found in {fixtures_dir}", file=sys.stderr)
        return 2

    results = []
    for bin_path in bin_files:
        json_path = bin_path.with_suffix(".expected.json")
        if not json_path.exists():
            results.append({
                "name": bin_path.stem,
                "status": "SKIP",
                "failures": ["no .expected.json file"],
                "xfail_reason": None,
            })
            continue
        results.append(_run_fixture(bin_path, json_path))

    # Print table
    col = max(len(r["name"]) for r in results) + 2
    header = f"{'Fixture':<{col}} {'Result':<8}  Notes"
    print(header)
    print("-" * len(header))
    for r in results:
        status = r["status"]
        notes = "; ".join(r["failures"]) if r["failures"] else (
            r["xfail_reason"] if r["xfail_reason"] else ""
        )
        print(f"{r['name']:<{col}} {status:<8}  {notes}")

    # Summary
    counts = {s: sum(1 for r in results if r["status"] == s)
              for s in ("PASS", "FAIL", "XFAIL", "SKIP")}
    print()
    print(
        f"Total: {len(results)}  "
        f"PASS={counts['PASS']}  "
        f"FAIL={counts['FAIL']}  "
        f"XFAIL={counts['XFAIL']}  "
        f"SKIP={counts['SKIP']}"
    )

    return 0 if counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
