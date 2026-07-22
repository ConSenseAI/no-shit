#!/usr/bin/env python3
"""Domain validator for post-build fixture manifests (FIXTURES.md §8).

Usage: python3 validate_fixture.py <manifest.yaml> [more.yaml ...]
Exit 0 iff every file passes. Errors name the offending field.

Companion to validate.py (which validates Lane-1 *dossiers*). A dossier is the
build spec; a fixture manifest is the as-built record hashed into the sealed
manifest at freeze. The two schemas are distinct — this enforces §8's shape and
the honesty rules that outlive the sketch: a builder is recorded, the builder is
never also the labeler or a verifier, every label carries its deciding facts and
scope, and the census/QA fields are present rather than implied.
"""
import re
import sys

import yaml

CRITERIA = {"no-subscription-trap", "no-dark-patterns", "no-lock-in"}
VERDICTS = {"PASS", "CONDITIONAL", "FAIL", "INDETERMINATE"}
BASES = {"enforcement-exhibit", "construction", "execution-verified", "inspection"}
LANES = {1, 2, 3, 4, 5, 6}
QA_KEYS = {"indistinguishability", "fidelity", "construction_check", "live_recheck"}
CHANNEL_RE = re.compile(r"^(ui\*?|acct\*?|pay|t:[\w<>-]+|msg|sup|multi|org|net|art|terms|code)$")
DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)+$")


def err(errors, path, msg):
    errors.append(f"  {path}: {msg}")


def need(errors, obj, key, typ, path):
    v = obj.get(key) if isinstance(obj, dict) else None
    if v is None or (typ in (str,) and isinstance(v, str) and not v.strip()):
        err(errors, f"{path}.{key}", "missing or empty")
        return None
    if typ and not isinstance(v, typ):
        err(errors, f"{path}.{key}", f"expected {typ.__name__}, got {type(v).__name__}")
        return None
    return v


def check_date(errors, val, path):
    if val in (None, "") or not DATE_RE.match(str(val)):
        err(errors, path, f"not YYYY[-MM[-DD]]: {val!r}")


def name_list(errors, roles, key, path):
    v = roles.get(key)
    if not isinstance(v, list):
        err(errors, f"{path}.{key}", "must be a list (may be empty for labelers/verifiers)")
        return []
    return [str(x) for x in v]


def validate(doc, fname):
    errors = []
    if not isinstance(doc, dict):
        return [f"  {fname}: top level is not a mapping"]

    fid = need(errors, doc, "fixture_id", str, "$")
    if fid and not SLUG_RE.match(fid):
        err(errors, "$.fixture_id", f"not a kebab-case slug: {fid!r}")

    host = need(errors, doc, "host", dict, "$") or {}
    for k in ("name", "version_pin", "license"):
        need(errors, host, k, str, "$.host")

    lane = doc.get("lane")
    if lane not in LANES:
        err(errors, "$.lane", f"not one of {sorted(LANES)}")

    # §8: diff_ref is the violation diff — implant lanes (1/2/5/6) must carry it;
    # implant-free lanes (3 unmodified-baseline cleans, 4 live services) must NOT.
    diff_ref = doc.get("diff_ref")
    if lane in (3, 4):
        if isinstance(diff_ref, str) and diff_ref.strip():
            err(errors, "$.diff_ref", f"lane {lane} is implant-free; diff_ref must be empty or absent")
    else:
        need(errors, doc, "diff_ref", str, "$")

    labels = need(errors, doc, "labels", list, "$") or []
    if not labels:
        err(errors, "$.labels", "at least one criterion label is required")
    for i, lb in enumerate(labels):
        p = f"$.labels[{i}]"
        if not isinstance(lb, dict):
            err(errors, p, "not a mapping")
            continue
        lc = need(errors, lb, "criterion", str, p)
        if lc and lc not in CRITERIA:
            err(errors, f"{p}.criterion", f"unknown criterion {lc!r}")
        need(errors, lb, "version", str, p)
        v = need(errors, lb, "expected_verdict", str, p)
        if v and v not in VERDICTS:
            err(errors, f"{p}.expected_verdict", f"not one of {sorted(VERDICTS)}")
        need(errors, lb, "deciding_facts", str, p)
        b = need(errors, lb, "basis", str, p)
        if b and b not in BASES:
            err(errors, f"{p}.basis", f"not one of {sorted(BASES)}")
        check_date(errors, lb.get("basis_date"), f"{p}.basis_date")
        need(errors, lb, "scope", str, p)

    chans = doc.get("channels")
    if not isinstance(chans, list) or not chans:
        err(errors, "$.channels", "missing or empty list")
    else:
        for c in chans:
            if not CHANNEL_RE.match(str(c)):
                err(errors, "$.channels", f"unknown channel token {c!r}")

    census = doc.get("census")
    if not isinstance(census, list) or not census:
        err(errors, "$.census", "surfaces must be enumerated (non-empty list) — §6 gate 5")

    if not isinstance(doc.get("time_script"), list):
        err(errors, "$.time_script", "must be a list (empty for single-sitting E2)")
    if not isinstance(doc.get("seed_spec"), dict):
        err(errors, "$.seed_spec", "must be a mapping")
    if not isinstance(doc.get("canaries"), list):
        err(errors, "$.canaries", "must be a list (may be empty)")

    roles = need(errors, doc, "roles", dict, "$") or {}
    builders = name_list(errors, roles, "builders", "$.roles")
    labelers = name_list(errors, roles, "labelers", "$.roles")
    verifiers = name_list(errors, roles, "verifiers", "$.roles")
    if not builders:
        err(errors, "$.roles.builders", "at least one builder must be recorded")
    overlap_l = set(builders) & set(labelers)
    overlap_v = set(builders) & set(verifiers)
    if overlap_l:
        err(errors, "$.roles", f"builder is also a labeler (§8: builder != labeler): {sorted(overlap_l)}")
    if overlap_v:
        err(errors, "$.roles", f"builder is also a verifier (independence): {sorted(overlap_v)}")

    qa = need(errors, doc, "qa", dict, "$") or {}
    missing = QA_KEYS - set(qa)
    if missing:
        err(errors, "$.qa", f"missing gate keys: {sorted(missing)}")

    return errors


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    rc = 0
    for fname in argv:
        try:
            with open(fname) as fh:
                doc = yaml.safe_load(fh)
        except (OSError, yaml.YAMLError) as e:
            print(f"FAIL  {fname}\n  unreadable/unparseable: {e}")
            rc = 1
            continue
        errors = validate(doc, fname)
        if errors:
            print(f"FAIL  {fname}")
            print("\n".join(errors))
            rc = 1
        else:
            print(f"OK    {fname}")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
