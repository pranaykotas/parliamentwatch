"""CLI interface for ParliamentWatch."""

import argparse
import json
import os
from config import DRSC_COMMITTEES, REPORTS_JSON
from scraper import scrape_all_committees, search_reports, load_existing_reports
from pdf_utils import get_report_text
from summarizer import summarize_report
from notifier import check_for_new_reports, save_notification
from exporter import export_csv, export_markdown
from committee_members import fetch_all_committee_members


def list_committees():
    """Print all tracked committees."""
    print("\nDepartmentally Related Standing Committees (DRSCs)")
    print("=" * 55)
    for key, info in sorted(DRSC_COMMITTEES.items()):
        print(f"  {key:<20} {info['name']}")
    print(f"\nTotal: {len(DRSC_COMMITTEES)} committees")


def browse_committee(committee_key):
    """List all reports for a committee."""
    if committee_key not in DRSC_COMMITTEES:
        print(f"Unknown committee: {committee_key}")
        print("Use --list-committees to see available options.")
        return

    reports_data = load_existing_reports()
    committee_reports = reports_data.get(committee_key, [])

    if not committee_reports:
        print(f"No local data for {committee_key}. Scraping...")
        scrape_all_committees([committee_key])
        reports_data = load_existing_reports()
        committee_reports = reports_data.get(committee_key, [])

    if not committee_reports:
        print(f"No reports found for {DRSC_COMMITTEES[committee_key]['name']}.")
        return

    name = DRSC_COMMITTEES[committee_key]["name"]
    print(f"\n{name}")
    print("=" * len(name))
    print(f"{'#':<6} {'Date':<14} Title")
    print(f"{'---':<6} {'---':<14} ---")

    for r in committee_reports:
        num = str(r.get("report_number", "?"))
        date = r.get("presented_in_ls") or r.get("laid_in_rs") or ""
        title = r.get("title", "No title")
        # Truncate long titles
        if len(title) > 80:
            title = title[:77] + "..."
        print(f"{num:<6} {date:<14} {title}")

    print(f"\nTotal: {len(committee_reports)} reports")
    print(f"Query a report: python cli.py --committee {committee_key} --report <number>")


def do_search(query, committee_key=None):
    """Search report titles for a keyword."""
    results = search_reports(query, committee_key)

    if not results:
        scope = f"in {committee_key}" if committee_key else "across all committees"
        print(f"No reports matching '{query}' found {scope}.")
        print("Tip: run --scrape first to download report metadata.")
        return

    print(f"\nSearch results for '{query}': {len(results)} match(es)\n")
    print(f"{'Committee':<20} {'#':<6} Title")
    print(f"{'---':<20} {'---':<6} ---")

    for r in results:
        committee = r.get("committee", "?")
        num = str(r.get("report_number", "?"))
        title = r.get("title", "No title")
        if len(title) > 70:
            title = title[:67] + "..."
        print(f"{committee:<20} {num:<6} {title}")


def query_report(committee_key, report_number):
    """Fetch and summarize a specific committee report."""
    if committee_key not in DRSC_COMMITTEES:
        print(f"Unknown committee: {committee_key}")
        print("Use --list-committees to see available options.")
        return

    committee = DRSC_COMMITTEES[committee_key]
    print(f"\nLooking up Report #{report_number} from {committee['name']}...")

    reports_data = {}
    if os.path.exists(REPORTS_JSON):
        with open(REPORTS_JSON, "r") as f:
            reports_data = json.load(f)

    # Find the matching report
    committee_reports = reports_data.get(committee_key, [])
    target_report = None
    for r in committee_reports:
        if str(r.get("report_number", "")).strip() == str(report_number).strip():
            target_report = r
            break

    if not target_report:
        # Report not in our data — scrape the committee first
        print("Report not found in local data. Scraping committee page...")
        scrape_all_committees([committee_key])

        # Reload and search again
        if os.path.exists(REPORTS_JSON):
            with open(REPORTS_JSON, "r") as f:
                reports_data = json.load(f)
        committee_reports = reports_data.get(committee_key, [])
        for r in committee_reports:
            if str(r.get("report_number", "")).strip() == str(report_number).strip():
                target_report = r
                break

    if not target_report:
        print(f"Could not find Report #{report_number} for {committee['name']}.")
        if committee_reports:
            print("\nAvailable reports:")
            for r in committee_reports[:10]:
                print(f"  #{r.get('report_number', '?')} - {r.get('title', 'No title')}")
        return

    print(f"\nFound: {target_report.get('title', 'No title')}")
    date = target_report.get("presented_in_ls") or target_report.get("laid_in_rs") or "Unknown"
    print(f"Presented: {date}")

    pdf_url = target_report.get("pdf_url")
    if not pdf_url:
        print("No PDF URL available for this report.")
        return

    # Download PDF and extract text
    text = get_report_text(pdf_url, committee_key, str(report_number))
    if not text:
        print("Could not extract text from the report PDF.")
        return

    # Summarize (or show preview if no API key)
    summary = summarize_report(text, committee["name"], str(report_number), committee_key)
    if summary:
        print("\n" + "=" * 60)
        print(f"SUMMARY: Report #{report_number} — {committee['name']}")
        print("=" * 60)
        print(summary)


def check_new(committee_keys):
    """Check for new reports across specified committees."""
    result = check_for_new_reports(committee_keys)
    if result:
        print("\n" + result["email_body"])
        # Save notification file for GitHub Actions
        save_notification(result)
        print(f"\nNotification saved to data/notification.txt")
    else:
        print("No new reports detected.")


def send_test_email():
    """Send a test email to verify SMTP configuration."""
    import smtplib
    from email.mime.text import MIMEText

    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    recipient = os.getenv("NOTIFICATION_EMAIL", "")

    if not all([smtp_username, smtp_password, recipient]):
        print("Missing SMTP config. Set these in .env:")
        print("  SMTP_SERVER=smtp.gmail.com")
        print("  SMTP_PORT=587")
        print("  SMTP_USERNAME=your-email@gmail.com")
        print("  SMTP_PASSWORD=your-app-specific-password")
        print("  NOTIFICATION_EMAIL=recipient@example.com")
        return

    msg = MIMEText("This is a test email from ParliamentWatch.\n\nIf you received this, your email notifications are configured correctly.")
    msg["Subject"] = "ParliamentWatch: Test Email"
    msg["From"] = smtp_username
    msg["To"] = recipient

    print(f"Sending test email from {smtp_username} to {recipient}...")
    print(f"SMTP server: {smtp_server}:{smtp_port}")
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        print("Test email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="ParliamentWatch — Track Indian Parliamentary Committee Reports",
        epilog="Examples:\n"
               "  python cli.py --list-committees\n"
               "  python cli.py --committee defence\n"
               "  python cli.py --committee defence --report 23\n"
               "  python cli.py --search semiconductor\n"
               "  python cli.py --scrape --lok-sabha 17\n"
               "  python cli.py --export csv\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--list-committees",
        action="store_true",
        help="List all tracked committees",
    )
    parser.add_argument(
        "--committee",
        type=str,
        help="Committee short name (e.g., 'defence', 'finance')",
    )
    parser.add_argument(
        "--report",
        type=str,
        help="Report number to query (use with --committee)",
    )
    parser.add_argument(
        "--search",
        type=str,
        help="Search report titles for a keyword (e.g., --search 'budget')",
    )
    parser.add_argument(
        "--check-new",
        action="store_true",
        help="Check for new reports and notify",
    )
    parser.add_argument(
        "--committees",
        type=str,
        help="Comma-separated list of committees (used with --check-new or --scrape)",
    )
    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Scrape reports for specified committees (or all)",
    )
    parser.add_argument(
        "--lok-sabha",
        type=int,
        help="Lok Sabha number to query (default: current, 18)",
    )
    parser.add_argument(
        "--house",
        type=str,
        choices=["L", "R"],
        default="L",
        help="House: L=Lok Sabha (default), R=Rajya Sabha",
    )
    parser.add_argument(
        "--export",
        type=str,
        choices=["csv", "markdown"],
        help="Export report data to CSV or Markdown",
    )
    parser.add_argument(
        "--fetch-members",
        action="store_true",
        help="Fetch committee membership data and resolve MP profiles",
    )
    parser.add_argument(
        "--test-email",
        action="store_true",
        help="Send a test email to verify SMTP configuration",
    )

    args = parser.parse_args()

    if args.fetch_members:
        print("Fetching committee membership data...")
        fetch_all_committee_members(lok_sabha=args.lok_sabha)
        return
    elif args.test_email:
        send_test_email()
        return
    elif args.list_committees:
        list_committees()
    elif args.export:
        committee = args.committee if args.committee else None
        if args.export == "csv":
            export_csv(committee)
        elif args.export == "markdown":
            export_markdown(committee)
    elif args.search:
        do_search(args.search, args.committee)
    elif args.committee and args.report:
        query_report(args.committee, args.report)
    elif args.committee and not args.report:
        browse_committee(args.committee)
    elif args.check_new:
        keys = args.committees.split(",") if args.committees else None
        check_new(keys)
    elif args.scrape:
        keys = args.committees.split(",") if args.committees else None
        print("Scraping committee reports...")
        results = scrape_all_committees(keys, lok_sabha=args.lok_sabha, house=args.house)
        total = sum(len(v) for v in results.values())
        print(f"\nDone. {total} reports across {len(results)} committees.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
