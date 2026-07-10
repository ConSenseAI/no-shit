#!/usr/bin/env python3
"""Domain validator for Lane-1 exhibit dossiers (platform/manifest/README.md).

Usage: python3 validate.py <dossier.yaml> [more.yaml ...]
Exit 0 iff every file passes. Errors name the offending field.

Deliberately domain-aware rather than generic JSON Schema: it enforces the
enums and honesty rules the format exists for (confidence tags, citation per
flow step, the mandatory gaps field, check numbers only on FAIL verdicts).
The post-build fixture-manifest schema is a freeze-time artifact; until then
this validator is normative for dossiers.
"""
import re
import sys

import yaml

CRITERIA = {"no-subscription-trap", "no-dark-patterns", "no-lock-in"}
STATUSES = {"draft-dossier", "build-ready", "built"}
AUTHORITIES = {"FTC", "CFPB", "CPPA", "CA-AG", "CNIL", "AGCM", "CMA", "EC-DSA",
               "DPC", "AEPD", "court", "other"}
ACTION_TYPES = {"fined", "adjudicated", "settlement", "commitment", "complaint-filed"}
CONFIDENCE = {"confirmed", "reported"}
VERDICTS = {"PASS", "CONDITIONAL", "FAIL", "INDETERMINATE"}
BASES = {"enforcement-exhibit", "construction", "execution-verified", "inspection"}
TIERS = {"E1", "E2", "E3", "E4"}
ESTIMATES = {"S", "M", "L"}
CHANNEL_RE = re.compile(r"^(ui\*?|acct\*?|pay|t:[\w<>-]+|msg|sup|multi|org|net|art|terms|code)$")
DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
DATE_RANGE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?(\.\.\d{4}(-\d{2}(-\d{2})?)?)?$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)+$")


def err(errors, path, msg):
    errors.append(f"  {path}: {msg}")


def need(errors, obj, key, typ, path):
    v = obj.get(key)
    if v is None or (typ in (str, list) and not v and not (typ is list and v == [] and key in ("artifacts", "open_questions", "channels"))):
        err(errors, f"{path}.{key}", "missing or empty")
        return None
    if typ and not isinstance(v, typ):
        err(errors, f"{path}.{key}", f"expected {typ.__name__}, got {type(v).__name__}")
        return None
    return v


def check_date(errors, val, path, required=True):
    if val in (None, ""):
        if required:
            err(errors, path, "missing date")
        return
    if not DATE_RE.match(str(val)):
        err(errors, path, f"not YYYY[-MM[-DD]]: {val!r}")


def validate(doc, fname):
    errors = []
    if not isinstance(doc, dict):
        return [f"  {fname}: top level is not a mapping"]

    slug = need(errors, doc, "dossier", str, "$")
    if slug and not SLUG_RE.match(slug):
        err(errors, "$.dossier", f"not a kebab-case slug: {slug!r}")
    crit = need(errors, doc, "criterion", str, "$")
    if crit and crit not in CRITERIA:
        err(errors, "$.criterion", f"unknown criterion {crit!r}")
    status = need(errors, doc, "status", str, "$")
    if status and status not in STATUSES:
        err(errors, "$.status", f"not one of {sorted(STATUSES)}")

    # anchor
    a = need(errors, doc, "anchor", dict, "$") or {}
    need(errors, a, "case", str, "$.anchor")
    auth = need(errors, a, "authority", str, "$.anchor")
    if auth and auth not in AUTHORITIES:
        err(errors, "$.anchor.authority", f"not one of {sorted(AUTHORITIES)}")
    at = need(errors, a, "action_type", str, "$.anchor")
    if at and at not in ACTION_TYPES:
        err(errors, "$.anchor.action_type", f"not one of {sorted(ACTION_TYPES)}")
    d = need(errors, a, "dates", dict, "$.anchor") or {}
    # conduct may be a period: "YYYY[-MM[-DD]]" or "YYYY[-MM[-DD]]..YYYY[-MM[-DD]]"
    cv = d.get("conduct")
    if cv in (None, ""):
        err(errors, "$.anchor.dates.conduct", "missing date")
    elif not DATE_RANGE_RE.match(str(cv)):
        err(errors, "$.anchor.dates.conduct", f"not YYYY[-MM[-DD]] or a '..' range: {cv!r}")
    check_date(errors, d.get("filed"), "$.anchor.dates.filed", required=False)
    check_date(errors, d.get("order"), "$.anchor.dates.order", required=False)

    # exhibit
    e = need(errors, doc, "exhibit", dict, "$") or {}
    sources = need(errors, e, "sources", list, "$.exhibit") or []
    for i, s in enumerate(sources):
        p = f"$.exhibit.sources[{i}]"
        if not isinstance(s, dict):
            err(errors, p, "not a mapping")
            continue
        need(errors, s, "url", str, p)
        need(errors, s, "what", str, p)
        c = need(errors, s, "confidence", str, p)
        if c and c not in CONFIDENCE:
            err(errors, f"{p}.confidence", f"not one of {sorted(CONFIDENCE)}")
        check_date(errors, s.get("retrieved"), f"{p}.retrieved")
    flow = need(errors, e, "flow_documented", list, "$.exhibit") or []
    for i, st in enumerate(flow):
        p = f"$.exhibit.flow_documented[{i}]"
        if not isinstance(st, dict):
            err(errors, p, "not a mapping")
            continue
        need(errors, st, "step", str, p)
        need(errors, st, "cite", str, p)  # the citation-per-step rule
    if "gaps" not in e or not isinstance(e.get("gaps"), str) or not e["gaps"].strip():
        err(errors, "$.exhibit.gaps", "mandatory honesty field — state what the exhibit does NOT establish")

    # fixture_spec
    f = need(errors, doc, "fixture_spec", dict, "$") or {}
    need(errors, f, "host", str, "$.fixture_spec")
    need(errors, f, "implant_outline", str, "$.fixture_spec")
    chans = f.get("channels")
    if not isinstance(chans, list) or not chans:
        err(errors, "$.fixture_spec.channels", "missing or empty list")
    else:
        for c in chans:
            if not CHANNEL_RE.match(str(c)):
                err(errors, "$.fixture_spec.channels", f"unknown channel token {c!r}")
    tier = need(errors, f, "tier", str, "$.fixture_spec")
    if tier and tier not in TIERS:
        err(errors, "$.fixture_spec.tier", f"not one of {sorted(TIERS)}")
    for k in ("time_script_needs", "seeding_needs"):
        if not isinstance(f.get(k), str):
            err(errors, f"$.fixture_spec.{k}", "must be a string (may be empty)")

    # expected_labels
    labels = need(errors, doc, "expected_labels", list, "$") or []
    crits_labeled = set()
    for i, lb in enumerate(labels):
        p = f"$.expected_labels[{i}]"
        if not isinstance(lb, dict):
            err(errors, p, "not a mapping")
            continue
        lc = need(errors, lb, "criterion", str, p)
        if lc:
            crits_labeled.add(lc)
            if lc not in CRITERIA:
                err(errors, f"{p}.criterion", f"unknown criterion {lc!r}")
        need(errors, lb, "version", str, p)
        v = need(errors, lb, "expected_verdict", str, p)
        if v and v not in VERDICTS:
            err(errors, f"{p}.expected_verdict", f"not one of {sorted(VERDICTS)}")
        fc = lb.get("failing_checks")
        if v == "FAIL":
            if not isinstance(fc, list) or not fc or not all(isinstance(x, int) for x in fc):
                err(errors, f"{p}.failing_checks", "FAIL verdicts need a non-empty list of SPEC check numbers (ints)")
        elif fc:
            err(errors, f"{p}.failing_checks", f"must be empty unless verdict is FAIL (got {v})")
        b = need(errors, lb, "basis", str, p)
        if b and b not in BASES:
            err(errors, f"{p}.basis", f"not one of {sorted(BASES)}")
        check_date(errors, lb.get("basis_date"), f"{p}.basis_date")
        need(errors, lb, "scope", str, p)
    if crit and labels and crit not in crits_labeled:
        err(errors, "$.expected_labels", f"primary criterion {crit!r} carries no label")

    be = need(errors, doc, "build_estimate", str, "$")
    if be and be not in ESTIMATES:
        err(errors, "$.build_estimate", f"not one of {sorted(ESTIMATES)}")
    if not isinstance(doc.get("open_questions"), list):
        err(errors, "$.open_questions", "must be a list (may be empty)")

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
