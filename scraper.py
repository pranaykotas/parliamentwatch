"""Scraper for sansad.in parliamentary committee reports using the REST API."""

import json
import os
import requests
from config import REPORTS_API, CURRENT_LOK_SABHA, DRSC_COMMITTEES, REPORTS_JSON, DATA_DIR


def ensure_data_dir():
    """Create data directory if it doesn't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)


def load_existing_reports():
    """Load previously scraped reports from JSON file."""
    if os.path.exists(REPORTS_JSON):
        with open(REPORTS_JSON, "r") as f:
            return json.load(f)
    return {}


def save_reports(reports):
    """Save reports to JSON file."""
    ensure_data_dir()
    with open(REPORTS_JSON, "w") as f:
        json.dump(reports, f, indent=2, ensure_ascii=False)


def sanitize_url(url):
    """Fix backslashes in URLs returned by sansad.in API."""
    if url:
        return url.replace("\\", "/")
    return url


def fetch_committee_reports(committee_key, lok_sabha=None, house="L"):
    """
    Fetch report listings for a single committee from the sansad.in API.

    Args:
        committee_key: Short name key from DRSC_COMMITTEES
        lok_sabha: Lok Sabha number (defaults to CURRENT_LOK_SABHA)
        house: "L" for Lok Sabha, "R" for Rajya Sabha

    Returns:
        List of report dicts with standardized keys.
    """
    if lok_sabha is None:
        lok_sabha = CURRENT_LOK_SABHA

    committee = DRSC_COMMITTEES[committee_key]
    house_label = "LS" if house == "L" else "RS"
    print(f"  Fetching reports for {committee['name']} ({house_label} {lok_sabha})...")

    params = {
        "house": house,
        "committeeCode": committee["api_code"],
        "lsNo": lok_sabha,
        "page": 1,
        "size": 200,  # Fetch all at once
        "sortOn": "reportNo",
        "sortBy": "desc",
    }

    try:
        resp = requests.get(REPORTS_API, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  Error fetching {committee['name']}: {e}")
        return []

    records = data.get("records", [])
    total = data.get("_metadata", {}).get("totalElements", len(records))

    reports = []
    for record in records:
        report = {
            "committee": committee_key,
            "committee_name": record.get("CommitteeName", committee["name"]).strip(),
            "report_number": record.get("reportNo"),
            "title": record.get("SubjectOfTheReport", ""),
            "presented_in_ls": record.get("PresentedInLS"),
            "laid_in_rs": record.get("LaidInRS"),
            "presented_to_speaker": record.get("PresentedToSpeaker"),
            "pdf_url": sanitize_url(record.get("url")),
            "pdf_url_hindi": sanitize_url(record.get("urlH")),
            "lok_sabha": record.get("Loksabha", lok_sabha),
            "house": house,
        }
        reports.append(report)

    print(f"  Found {len(reports)} / {total} reports for {committee['name']}")
    return reports


def scrape_all_committees(committee_keys=None, lok_sabha=None, house="L", both_houses=False):
    """
    Fetch reports for specified committees (or all DRSCs).

    Args:
        committee_keys: List of committee short names, or None for all
        lok_sabha: Lok Sabha number (defaults to current)
        house: "L" for Lok Sabha, "R" for Rajya Sabha
        both_houses: If True, fetch from both LS and RS and merge (dedup by report_number)

    Returns:
        Dict mapping committee_key -> list of reports
    """
    if committee_keys is None:
        committee_keys = list(DRSC_COMMITTEES.keys())

    all_reports = load_existing_reports()

    houses = ["L", "R"] if both_houses else [house]

    for key in committee_keys:
        if key not in DRSC_COMMITTEES:
            print(f"  Unknown committee: {key}")
            continue

        # Build index of existing reports by (report_number, lok_sabha) for merging
        existing_reports = {
            (r.get("report_number"), r.get("lok_sabha")): r
            for r in all_reports.get(key, [])
        }

        for h in houses:
            reports = fetch_committee_reports(key, lok_sabha, h)
            for r in reports:
                rid = (r.get("report_number"), r.get("lok_sabha"))
                if rid not in existing_reports:
                    existing_reports[rid] = r
                else:
                    # Merge date info from both houses
                    existing = existing_reports[rid]
                    if not existing.get("presented_in_ls") and r.get("presented_in_ls"):
                        existing["presented_in_ls"] = r["presented_in_ls"]
                    if not existing.get("laid_in_rs") and r.get("laid_in_rs"):
                        existing["laid_in_rs"] = r["laid_in_rs"]

        all_reports[key] = sorted(
            existing_reports.values(),
            key=lambda x: (x.get("lok_sabha") or 0, x.get("report_number") or 0),
            reverse=True,
        )

    save_reports(all_reports)
    return all_reports


def detect_new_reports(committee_keys=None):
    """
    Fetch latest data and compare against stored data to find new reports.

    Returns:
        List of new report dicts
    """
    old_reports = load_existing_reports()

    if committee_keys is None:
        committee_keys = list(DRSC_COMMITTEES.keys())

    new_reports = []
    updated = {}

    for key in committee_keys:
        if key not in DRSC_COMMITTEES:
            continue

        fresh = fetch_committee_reports(key)
        old_list = old_reports.get(key, [])

        # Build set of known report identifiers
        old_ids = {
            (r.get("report_number"), r.get("lok_sabha", CURRENT_LOK_SABHA))
            for r in old_list
        }

        for report in fresh:
            report_id = (report.get("report_number"), report.get("lok_sabha"))
            if report_id not in old_ids:
                new_reports.append(report)

        updated[key] = fresh

    # Merge new data without overwriting other Lok Sabhas
    all_reports = load_existing_reports()
    for key, fresh_list in updated.items():
        existing = {
            (r.get("report_number"), r.get("lok_sabha")): r
            for r in all_reports.get(key, [])
        }
        for r in fresh_list:
            existing[(r.get("report_number"), r.get("lok_sabha"))] = r
        all_reports[key] = sorted(
            existing.values(),
            key=lambda x: (x.get("lok_sabha") or 0, x.get("report_number") or 0),
            reverse=True,
        )
    save_reports(all_reports)

    return new_reports


def search_reports(query, committee_key=None):
    """
    Search report titles for a keyword/phrase.

    Args:
        query: Search term (case-insensitive)
        committee_key: Optional committee to restrict search to

    Returns:
        List of matching report dicts
    """
    all_reports = load_existing_reports()
    if not all_reports:
        print("No local data. Run --scrape first.")
        return []

    query_lower = query.lower()
    results = []

    committees_to_search = [committee_key] if committee_key else all_reports.keys()

    for key in committees_to_search:
        for report in all_reports.get(key, []):
            title = report.get("title", "")
            if query_lower in title.lower():
                results.append(report)

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        keys = sys.argv[1].split(",")
    else:
        keys = ["defence"]

    print("Scraping committee reports...")
    results = scrape_all_committees(keys)
    total = sum(len(v) for v in results.values())
    print(f"\nDone. {total} reports across {len(results)} committees.")
    print(json.dumps(results, indent=2, ensure_ascii=False)[:2000])
