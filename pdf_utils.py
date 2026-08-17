"""Download report PDFs and extract text."""

import os
import requests
from pypdf import PdfReader
from config import PDFS_DIR, TEXT_DIR

# sansad.in requires a browser-like User-Agent or returns 403
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def ensure_dirs(committee_key):
    """Create PDF and text directories for a committee."""
    os.makedirs(os.path.join(PDFS_DIR, committee_key), exist_ok=True)
    os.makedirs(os.path.join(TEXT_DIR, committee_key), exist_ok=True)


def download_pdf(pdf_url, committee_key, report_number):
    """
    Download a report PDF if not already cached.

    Returns:
        Path to the downloaded PDF, or None on failure.
    """
    ensure_dirs(committee_key)
    # Sanitize report number for use as filename
    safe_name = report_number.replace("/", "-").replace(" ", "_")
    pdf_path = os.path.join(PDFS_DIR, committee_key, f"{safe_name}.pdf")

    if os.path.exists(pdf_path):
        print(f"  PDF already cached: {pdf_path}")
        return pdf_path

    # Safety net: fix backslashes in URLs from sansad.in API
    pdf_url = pdf_url.replace("\\", "/")

    print(f"  Downloading PDF from {pdf_url}...")
    try:
        resp = requests.get(pdf_url, timeout=120, stream=True, headers=_HEADERS)
        resp.raise_for_status()
        with open(pdf_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"  Saved to {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"  Failed to download PDF: {e}")
        return None


def extract_text(pdf_path, committee_key, report_number):
    """
    Extract text from a PDF. Uses cached text if available.

    Returns:
        Extracted text as a string, or None on failure.
    """
    ensure_dirs(committee_key)
    safe_name = report_number.replace("/", "-").replace(" ", "_")
    text_path = os.path.join(TEXT_DIR, committee_key, f"{safe_name}.txt")

    if os.path.exists(text_path):
        print(f"  Text already cached: {text_path}")
        with open(text_path, "r") as f:
            return f.read()

    print(f"  Extracting text from {pdf_path}...")
    try:
        reader = PdfReader(pdf_path)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        full_text = "\n\n".join(text_parts)

        if not full_text.strip():
            print(f"  No extractable text in {len(reader.pages)} pages — likely a scanned/image-only PDF")
            return None

        # Cache the extracted text
        with open(text_path, "w") as f:
            f.write(full_text)

        print(f"  Extracted {len(full_text)} characters from {len(reader.pages)} pages")
        return full_text
    except Exception as e:
        print(f"  Failed to extract text: {e}")
        return None


def get_report_text(pdf_url, committee_key, report_number):
    """
    Download PDF and extract text (with caching at both steps).

    Returns:
        Extracted text string, or None on failure.
    """
    pdf_path = download_pdf(pdf_url, committee_key, report_number)
    if not pdf_path:
        return None
    return extract_text(pdf_path, committee_key, report_number)
