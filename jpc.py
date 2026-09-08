"""Discover and track Joint Parliamentary Committees / Select Committees.

Unlike DRSCs and the Financial Committees (fixed, hardcoded in config.py),
JPCs and Select Committees are ad hoc -- they form per Bill and dissolve
once their report is presented, so their committee codes on sansad.in
change over time (new ones appear every few months; old ones just stop
producing new reports but keep their history). Hardcoding a snapshot list
would silently go stale, so this module re-discovers the current list from
sansad.in on every call instead, caching the registry to
data/jpc_committees.json so old entries are never dropped even if they
later disappear from the hub page.

Found at https://sansad.in/ls/committee/other-committees -- same
api_ls/committee/lsRSAllReports endpoint and schema as the LS-chaired
DRSCs, just with committee codes 67+ instead of the DRSC/Financial
Committee codes.
"""

import json
import os
import re
from urllib.parse import unquote

import requests

from config import DATA_DIR, CURRENT_LOK_SABHA
from scraper import _fetch_ls_committee_reports, load_existing_reports, save_reports

JPC_HUB_URL = "https://sansad.in/ls/committee/other-committees"
JPC_REGISTRY_PATH = os.path.join(DATA_DIR, "jpc_committees.json")

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Matches href="/ls/committee/other-committees/{code}-{urlencoded name}-nameH=..."
_LINK_RE = re.compile(r'href="/ls/committee/other-committees/(\d+)-([^"]*?)-nameH=')


def discover_jpc_committees():
    """Fetch the current list of JPCs/Select Committees from sansad.in.

    Returns:
        Dict of {jpc_key: {"name", "api_code", "house", "category"}}, or {}
        on any fetch error -- callers should treat that as "try again
        later," not "there are no JPCs right now."
    """
    try:
        resp = requests.get(JPC_HUB_URL, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"  Error fetching JPC hub page: {e}")
        return {}

    registry = {}
    for code, encoded_name in _LINK_RE.findall(resp.text):
        name = unquote(encoded_name).strip()
        if not name or name.lower() == "undefined":
            continue
        key = f"jpc_{code}"
        registry[key] = {
            "name": name,
            "api_code": int(code),
            "house": "L",
            "category": "jpc",
        }
    return registry


def load_jpc_registry():
    """Load the cached JPC registry, or {} if never discovered yet."""
    if os.path.exists(JPC_REGISTRY_PATH):
        with open(JPC_REGISTRY_PATH, "r") as f:
            return json.load(f)
    return {}


def save_jpc_registry(registry):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(JPC_REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def refresh_jpc_registry():
    """Re-discover JPCs and merge into the cached registry.

    Never drops a committee that disappears from the hub page -- a
    dissolved JPC's report history should stay browsable even after
    sansad.in stops listing it.

    Returns:
        (registry, newly_found_keys)
    """
    discovered = discover_jpc_committees()
    existing = load_jpc_registry()
    new_keys = [k for k in discovered if k not in existing]
    existing.update(discovered)
    if discovered:
        save_jpc_registry(existing)
    return existing, new_keys


def fetch_jpc_reports(jpc_key, committee, lok_sabha=None):
    """Fetch reports for one JPC via the same endpoint as LS-chaired DRSCs."""
    if lok_sabha is None:
        lok_sabha = CURRENT_LOK_SABHA
    return _fetch_ls_committee_reports(jpc_key, lok_sabha, committee=committee)


def scrape_jpc_reports(registry=None):
    """Fetch reports for every known JPC and merge into data/reports.json.

    Returns:
        Dict of {jpc_key: [report, ...]} -- the freshly fetched reports.
    """
    if registry is None:
        registry = load_jpc_registry()

    fetched = {}
    for key, committee in registry.items():
        fetched[key] = fetch_jpc_reports(key, committee)

    all_reports = load_existing_reports()
    for key, fresh_reports in fetched.items():
        existing_reports = {
            (r.get("report_number"), r.get("lok_sabha")): r
            for r in all_reports.get(key, [])
        }
        for r in fresh_reports:
            rid = (r.get("report_number"), r.get("lok_sabha"))
            existing_reports[rid] = r
        all_reports[key] = sorted(
            existing_reports.values(),
            key=lambda r: (r.get("report_number") or 0),
            reverse=True,
        )
    save_reports(all_reports)
    return fetched


def detect_new_jpc_reports():
    """Discover current JPCs, fetch their reports, and return any new ones
    (including reports from newly-discovered committees). Mirrors
    scraper.detect_new_reports() for the fixed committees, but against the
    dynamic JPC registry instead of DRSC_COMMITTEES.

    Returns:
        List of new report dicts
    """
    old_reports = load_existing_reports()
    registry, new_committee_keys = refresh_jpc_registry()
    if new_committee_keys:
        names = ", ".join(registry[k]["name"] for k in new_committee_keys)
        print(f"  Discovered {len(new_committee_keys)} new JPC(s)/Select Committee(s): {names}")

    fetched = scrape_jpc_reports(registry)

    new_reports = []
    for key, fresh in fetched.items():
        old_ids = {
            (r.get("report_number"), r.get("lok_sabha"))
            for r in old_reports.get(key, [])
        }
        for report in fresh:
            report_id = (report.get("report_number"), report.get("lok_sabha"))
            if report_id not in old_ids:
                new_reports.append(report)
    return new_reports
