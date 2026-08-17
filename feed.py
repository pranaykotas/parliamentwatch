"""Generate an RSS feed of committee reports for RSS-to-email subscription services."""

import html
import os
from datetime import datetime, timezone
from email.utils import format_datetime
from scraper import load_existing_reports
from config import DATA_DIR

FEED_TITLE = "ParliamentWatch — New Committee Reports"
FEED_LINK = "https://parliamentcommittee.streamlit.app/"
FEED_DESCRIPTION = (
    "New Indian Parliamentary Committee reports as they're published, "
    "tracked across all 24 Departmentally Related Standing Committees."
)
MAX_ITEMS = 100

_DATE_FIELDS = (
    "presented_in_ls",
    "laid_in_rs",
    "presented_to_speaker",
    "date_of_presentation",
    "date_of_adoption",
)
_DATE_FORMATS = ("%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")


def _parse_date(date_str):
    """Parse date strings like '18-Mar-2026' into datetime objects."""
    if not date_str:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _report_date(report):
    """Get the best available date for a report."""
    for field in _DATE_FIELDS:
        parsed = _parse_date(report.get(field))
        if parsed:
            return parsed
    return None


def _feed_items(committee_key=None):
    """Return (date, report) tuples for the most recent reports, newest first."""
    reports = load_existing_reports()
    committees = [committee_key] if committee_key else reports.keys()

    dated = []
    for key in committees:
        for r in reports.get(key, []):
            date = _report_date(r)
            if date:
                dated.append((date, r))

    dated.sort(key=lambda pair: pair[0], reverse=True)
    return dated[:MAX_ITEMS]


def generate_rss(output_path=None, committee_key=None):
    """
    Write an RSS 2.0 feed of the most recent committee reports.

    Args:
        output_path: Output file path (default: data/feed.xml)
        committee_key: Optional committee to filter by (None = all)

    Returns:
        Path to the written feed file.
    """
    if output_path is None:
        output_path = os.path.join(DATA_DIR, "feed.xml")

    items = _feed_items(committee_key)

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "<channel>",
        f"<title>{html.escape(FEED_TITLE)}</title>",
        f"<link>{html.escape(FEED_LINK)}</link>",
        f"<description>{html.escape(FEED_DESCRIPTION)}</description>",
        f"<lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>",
    ]

    for date, r in items:
        committee_name = r.get("committee_name", "Unknown Committee")
        title = f"{committee_name}: {r.get('title', 'Untitled report')}"
        link = r.get("pdf_url", "").replace(" ", "%20") or FEED_LINK
        guid = f"{r.get('committee', '')}-{r.get('lok_sabha', '')}-{r.get('report_number', '')}"
        description = f"Report No. {r.get('report_number', '?')} — {r.get('title', '')}"

        parts.append("<item>")
        parts.append(f"<title>{html.escape(title)}</title>")
        parts.append(f"<link>{html.escape(link)}</link>")
        parts.append(f'<guid isPermaLink="false">{html.escape(guid)}</guid>')
        parts.append(f"<pubDate>{format_datetime(date.replace(tzinfo=timezone.utc))}</pubDate>")
        parts.append(f"<description>{html.escape(description)}</description>")
        parts.append("</item>")

    parts.append("</channel>")
    parts.append("</rss>")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")

    print(f"Wrote {len(items)} items to {output_path}")
    return output_path
