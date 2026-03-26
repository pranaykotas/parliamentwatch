"""Export scraped report data to CSV or Markdown."""

import csv
import os
from scraper import load_existing_reports
from config import DATA_DIR


def export_csv(committee_key=None, output_path=None):
    """
    Export report metadata to CSV.

    Args:
        committee_key: Optional committee to filter by (None = all)
        output_path: Output file path (default: data/reports.csv)
    """
    reports = load_existing_reports()
    if not reports:
        print("No data to export. Run --scrape first.")
        return

    if output_path is None:
        output_path = os.path.join(DATA_DIR, "reports.csv")

    rows = []
    committees = [committee_key] if committee_key else reports.keys()

    for key in committees:
        for r in reports.get(key, []):
            pdf_url = r.get("pdf_url", "")
            safe_pdf_url = pdf_url.replace(" ", "%20") if pdf_url else ""

            rows.append({
                "committee": r.get("committee", key),
                "committee_name": r.get("committee_name", ""),
                "report_number": r.get("report_number", ""),
                "title": r.get("title", ""),
                "presented_in_ls": r.get("presented_in_ls", ""),
                "laid_in_rs": r.get("laid_in_rs", ""),
                "lok_sabha": r.get("lok_sabha", ""),
                "pdf_url": safe_pdf_url,
            })

    if not rows:
        print("No reports found for the specified committee.")
        return

    fieldnames = ["committee", "committee_name", "report_number", "title",
                  "presented_in_ls", "laid_in_rs", "lok_sabha", "pdf_url"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {len(rows)} reports to {output_path}")


def export_markdown(committee_key=None, output_path=None):
    """
    Export report metadata as a Markdown table.

    Args:
        committee_key: Optional committee to filter by (None = all)
        output_path: Output file path (default: data/reports.md)
    """
    reports = load_existing_reports()
    if not reports:
        print("No data to export. Run --scrape first.")
        return

    if output_path is None:
        output_path = os.path.join(DATA_DIR, "reports.md")

    lines = ["# Parliamentary Committee Reports\n"]
    committees = [committee_key] if committee_key else sorted(reports.keys())

    for key in committees:
        committee_reports = reports.get(key, [])
        if not committee_reports:
            continue

        name = committee_reports[0].get("committee_name", key)
        lines.append(f"\n## {name}\n")
        lines.append("| # | Title | Presented | LS |")
        lines.append("|---|-------|-----------|-----|")

        for r in committee_reports:
            num = r.get("report_number", "?")
            title = r.get("title", "No title")
            # Truncate long titles for readability
            if len(title) > 80:
                title = title[:77] + "..."
            date = r.get("presented_in_ls", r.get("laid_in_rs", ""))
            ls = r.get("lok_sabha", "")
            # Escape pipes in title
            title = title.replace("|", "\\|")
            lines.append(f"| {num} | {title} | {date} | {ls} |")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    total = sum(len(reports.get(k, [])) for k in committees)
    print(f"Exported {total} reports to {output_path}")
