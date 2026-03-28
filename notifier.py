"""Detect new reports and format email notifications."""

import os
from urllib.parse import quote
from scraper import detect_new_reports
from config import DATA_DIR


def encode_pdf_url(url):
    """Percent-encode spaces and special characters in a sansad.in PDF URL path."""
    if not url:
        return url
    # Split on '?' to avoid encoding the query string
    parts = url.split("?", 1)
    # Encode only the path portion, preserving slashes and colons
    parts[0] = quote(parts[0], safe="/:.")
    return "?".join(parts)


def check_for_new_reports(committee_keys=None):
    """
    Check for new reports and return formatted notification data.

    Args:
        committee_keys: List of committee short names, or None for all DRSCs

    Returns:
        Dict with 'new_reports' list and 'email_body' string, or None if no new reports.
    """
    print("Checking for new committee reports...")
    new_reports = detect_new_reports(committee_keys)

    if not new_reports:
        print("No new reports found.")
        return None

    print(f"Found {len(new_reports)} new report(s)!")

    # Format email body
    lines = [
        "New Parliamentary Committee Reports Detected",
        "=" * 45,
        "",
    ]

    for report in new_reports:
        lines.append(f"Committee: {report.get('committee_name', report.get('committee', 'Unknown'))}")
        if report.get("report_number"):
            lines.append(f"Report Number: {report['report_number']}")
        if report.get("title"):
            lines.append(f"Subject: {report['title']}")
        date = report.get("presented_in_ls") or report.get("laid_in_rs") or report.get("date")
        if date:
            lines.append(f"Date: {date}")
        if report.get("pdf_url"):
            lines.append(f"PDF: {encode_pdf_url(report['pdf_url'])}")
        lines.append("")
        lines.append("-" * 40)
        lines.append("")

    email_body = "\n".join(lines)

    return {
        "new_reports": new_reports,
        "email_subject": f"ParliamentWatch: {len(new_reports)} new committee report(s)",
        "email_body": email_body,
    }


def save_notification(result, filepath=None):
    """
    Save notification subject and body to a file for GitHub Actions to pick up.

    Args:
        result: Dict from check_for_new_reports()
        filepath: Path to write to (defaults to data/notification.txt)
    """
    if filepath is None:
        filepath = os.path.join(DATA_DIR, "notification.txt")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(f"SUBJECT: {result['email_subject']}\n\n")
        f.write(result["email_body"])
