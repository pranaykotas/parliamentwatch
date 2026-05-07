"""Scraper for sansad.in parliamentary committee reports using the REST API."""

import json
import os
import requests
from config import REPORTS_API, RS_REPORTS_API, CURRENT_LOK_SABHA, DRSC_COMMITTEES, REPORTS_JSON, DATA_DIR


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


_RS_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://sansad.in/rs/committees",
}


def _fetch_ls_committee_reports(committee_key, lok_sabha):
    """Fetch reports for an LS-chaired committee using the api_ls endpoint."""
    committee = DRSC_COMMITTEES[committee_key]
    print(f"  Fetching reports for {committee['name']} (LS {lok_sabha})...")

    params = {
        "house": "L",
        "committeeCode": committee["api_code"],
        "lsNo": lok_sabha,
        "page": 1,
        "size": 200,
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
        reports.append({
            "committee": committee_key,
            "committee_name": record.get("CommitteeName", committee["name"]).strip(),
            "report_number": record.get("reportNo"),
            "title": record.get("SubjectOfTheReport", ""),
            "presented_in_ls": record.get("PresentedInLS"),
            "laid_in_rs": record.get("LaidInRS"),
            "presented_to_speaker": record.get("PresentedToSpeaker"),
            "date_of_presentation": record.get("dateOfPresentation"),
            "date_of_adoption": record.get("dateOfAdoption"),
            "pdf_url": sanitize_url(record.get("url")),
            "pdf_url_hindi": sanitize_url(record.get("urlH")),
            "lok_sabha": record.get("Loksabha", lok_sabha),
            "house": "L",
        })
    print(f"  Found {len(reports)} / {total} reports for {committee['name']}")
    return reports


def _fetch_rs_committee_reports(committee_key, lok_sabha):
    """Fetch reports for an RS-chaired committee using the api_rs endpoint.

    The RS endpoint is term-agnostic — it returns all reports regardless of
    Lok Sabha number. We tag every record with the requested lok_sabha so
    the rest of the pipeline (which keys by report_number + lok_sabha) keeps
    working.
    """
    committee = DRSC_COMMITTEES[committee_key]
    mst_comm_id = committee.get("mst_comm_id")
    if not mst_comm_id:
        print(f"  Skipping {committee['name']}: no mst_comm_id configured")
        return []

    print(f"  Fetching reports for {committee['name']} (RS, all terms)...")
    all_records = []
    page = 1
    while True:
        params = {
            "mstCommId": mst_comm_id,
            "departmentId": "",
            "presentationYear": "",
            "search": "",
            "page": page,
            "size": 200,
            "sortOn": "reportNo",
            "sortBy": "desc",
            "locale": "en",
        }
        try:
            resp = requests.get(RS_REPORTS_API, params=params, headers=_RS_HEADERS, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  Error fetching {committee['name']}: {e}")
            break
        records = data.get("records", [])
        all_records.extend(records)
        total = data.get("_metadata", {}).get("totalElements", 0)
        if len(all_records) >= total or not records:
            break
        page += 1

    reports = []
    for record in all_records:
        reports.append({
            "committee": committee_key,
            "committee_name": record.get("committeeName") or committee["name"],
            "report_number": record.get("reportNo"),
            "title": record.get("subjectOfTheReport", ""),
            "presented_in_ls": None,
            "laid_in_rs": None,
            "presented_to_speaker": None,
            "date_of_presentation": record.get("dateOfPresentation"),
            "date_of_adoption": record.get("dateOfAdoption"),
            "pdf_url": sanitize_url(record.get("url")),
            "pdf_url_hindi": sanitize_url(record.get("urlHindi")),
            "lok_sabha": lok_sabha,
            "house": "R",
        })
    print(f"  Found {len(reports)} reports for {committee['name']}")
    return reports


def fetch_committee_reports(committee_key, lok_sabha=None, house=None):
    """Fetch report listings for a committee, dispatching to the right API."""
    if lok_sabha is None:
        lok_sabha = CURRENT_LOK_SABHA
    committee = DRSC_COMMITTEES[committee_key]
    if house is None:
        house = committee.get("house", "L")
    if house == "R":
        return _fetch_rs_committee_reports(committee_key, lok_sabha)
    return _fetch_ls_committee_reports(committee_key, lok_sabha)


def scrape_all_committees(committee_keys=None, lok_sabha=None, house=None, both_houses=False):
    """
    Fetch reports for specified committees (or all DRSCs).

    Each committee uses its own configured house from DRSC_COMMITTEES. The
    `house` arg can override that for a committee, but only if it matches.
    `both_houses` is kept for API compatibility but is now a no-op — different
    committees can share api_codes between LS/RS, so blindly fetching both
    causes cross-contamination.

    Args:
        committee_keys: List of committee short names, or None for all
        lok_sabha: Lok Sabha number (defaults to current)
        house: Override — only fetch committees whose configured house matches
        both_houses: Deprecated, ignored. Each committee uses its own house.

    Returns:
        Dict mapping committee_key -> list of reports
    """
    if committee_keys is None:
        committee_keys = list(DRSC_COMMITTEES.keys())

    all_reports = load_existing_reports()

    for key in committee_keys:
        if key not in DRSC_COMMITTEES:
            print(f"  Unknown committee: {key}")
            continue

        committee = DRSC_COMMITTEES[key]
        committee_house = committee.get("house", "L")

        # If user specified a house filter, skip committees that don't match
        if house is not None and house != committee_house:
            continue

        houses = [committee_house]

        # Build index of existing reports by (report_number, lok_sabha) for merging.
        # Filter out cross-contamination from the old `both_houses` bug: records
        # whose `house` doesn't match the committee's configured house.
        existing_reports = {
            (r.get("report_number"), r.get("lok_sabha")): r
            for r in all_reports.get(key, [])
            if r.get("house") == committee_house
        }

        for h in houses:
            reports = fetch_committee_reports(key, lok_sabha, h)
            for r in reports:
                # Fresh data from API is authoritative — always overwrite.
                # This ensures new fields added to the schema (e.g.
                # date_of_presentation) populate on existing records.
                rid = (r.get("report_number"), r.get("lok_sabha"))
                existing_reports[rid] = r

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
