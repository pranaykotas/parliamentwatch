"""ParliamentWatch — Streamlit GUI for exploring Indian Parliamentary Committee reports."""

import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from config import DRSC_COMMITTEES, CURRENT_LOK_SABHA, REPORTS_JSON, SUMMARIES_DIR, TEXT_DIR
from scraper import (
    load_existing_reports,
    fetch_committee_reports,
    scrape_all_committees,
    search_reports,
    save_reports,
)
from pdf_utils import get_report_text
from summarizer import summarize_report

# --- Page config ---
st.set_page_config(
    page_title="ParliamentWatch",
    page_icon="🏛️",
    layout="wide",
)

# --- Custom CSS ---
st.markdown("""
<style>
    h1 {
        color: #1B4F72;
        border-bottom: 3px solid #1B4F72;
        padding-bottom: 0.3em;
    }
    [data-testid="stMetric"] {
        background-color: #F4F6F9;
        border: 1px solid #D5DBDB;
        border-radius: 8px;
        padding: 12px 16px;
    }
    [data-testid="stSidebar"] {
        border-right: 2px solid #1B4F72;
    }
    .attribution {
        text-align: center;
        padding: 2em 0 1em 0;
        color: #6C757D;
        font-size: 0.85em;
        border-top: 1px solid #DEE2E6;
        margin-top: 3em;
    }
    .attribution a { color: #1B4F72; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

st.title("ParliamentWatch")
st.caption("Track Indian Parliamentary Committee reports from sansad.in")


# --- Helper functions ---
def parse_date(date_str):
    """Parse date strings like '18-Mar-2026' into datetime objects."""
    if not date_str:
        return None
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def get_report_date(report):
    """Get the best available date for a report."""
    return (
        parse_date(report.get("presented_in_ls"))
        or parse_date(report.get("laid_in_rs"))
        or parse_date(report.get("presented_to_speaker"))
    )


def classify_report(title):
    """Classify a report into a category based on its title."""
    t = title.lower()
    if "demand" in t or "grant" in t or "budget" in t:
        return "Demand for Grants"
    if "action taken" in t:
        return "Action Taken"
    if "assurance" in t:
        return "Assurances"
    if "bill" in t:
        return "Bills"
    return "Subject Report"


def has_data():
    """Check if we have any scraped data."""
    return os.path.exists(REPORTS_JSON) and os.path.getsize(REPORTS_JSON) > 10


def has_summary(committee_key, report_number):
    """Check if a summary exists for this report."""
    safe_name = str(report_number).replace("/", "-").replace(" ", "_")
    path = os.path.join(SUMMARIES_DIR, committee_key, f"{safe_name}.md")
    return os.path.exists(path)


def has_text(committee_key, report_number):
    """Check if extracted text exists for this report."""
    safe_name = str(report_number).replace("/", "-").replace(" ", "_")
    path = os.path.join(TEXT_DIR, committee_key, f"{safe_name}.txt")
    return os.path.exists(path)


def get_all_reports_flat():
    """Return all reports as a flat list with dates parsed."""
    all_reports = load_existing_reports()
    flat = []
    for reports in all_reports.values():
        flat.extend(reports)
    return flat



@st.dialog("Report Details", width="large")
def show_report_dialog(r):
    """Show report details in a modal dialog with extract & summarize capability."""
    committee_key = r.get("committee", "")
    committee_name = r.get("committee_name", "")
    report_num = r.get("report_number", "?")
    report_num_str = str(report_num)
    pdf_url = r.get("pdf_url", "")

    st.markdown(f"### {r.get('title', 'No title')}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.write(f"**Committee:** {committee_name}")
        st.write(f"**Report #:** {report_num}")
        st.write(f"**Category:** {classify_report(r.get('title', ''))}")
        house = "Lok Sabha" if r.get("house") == "L" else ("Rajya Sabha" if r.get("house") == "R" else "—")
        st.write(f"**House:** {house} | **Lok Sabha:** {r.get('lok_sabha', '—')}")
    with col_b:
        if r.get("presented_in_ls"):
            st.write(f"**Presented in LS:** {r['presented_in_ls']}")
        if r.get("laid_in_rs"):
            st.write(f"**Laid in RS:** {r['laid_in_rs']}")
        link_parts = []
        if pdf_url:
            link_parts.append(f"[PDF (English)]({pdf_url})")
        pdf_hindi = r.get("pdf_url_hindi", "")
        if pdf_hindi:
            link_parts.append(f"[PDF (Hindi)]({pdf_hindi})")
        if link_parts:
            st.markdown(" | ".join(link_parts))

    st.divider()

    # Show summary if available, or extracted text, or offer to extract
    if has_summary(committee_key, report_num):
        safe_name = report_num_str.replace("/", "-").replace(" ", "_")
        summary_path = os.path.join(SUMMARIES_DIR, committee_key, f"{safe_name}.md")
        with open(summary_path, "r") as f:
            st.markdown(f.read())
        # Also show full text in an expander if available
        if has_text(committee_key, report_num):
            text_path = os.path.join(TEXT_DIR, committee_key, f"{safe_name}.txt")
            with st.expander("Full extracted text"):
                with open(text_path, "r") as f:
                    st.text_area("", f.read(), height=400, disabled=True, label_visibility="collapsed")

    elif has_text(committee_key, report_num):
        safe_name = report_num_str.replace("/", "-").replace(" ", "_")
        text_path = os.path.join(TEXT_DIR, committee_key, f"{safe_name}.txt")
        with open(text_path, "r") as f:
            full_text = f.read()
        st.info("Text extracted but not yet summarized.")
        if _has_api_key():
            if st.button("Generate Summary", key="dialog_gen_summary", type="primary"):
                with st.status("Summarizing...", expanded=True) as status:
                    summary = summarize_report(full_text, committee_name, report_num_str, committee_key, **_get_byok_kwargs())
                    status.update(label="Done", state="complete")
                if summary:
                    st.markdown(summary)
                    st.rerun()
        else:
            st.info("Enter your LLM API key in the sidebar to generate a summary.")
        with st.expander("Full extracted text"):
            st.text_area("", full_text, height=400, disabled=True, label_visibility="collapsed")

    else:
        if not pdf_url:
            st.warning("No PDF URL available for this report.")
        elif _has_api_key():
            if st.button("Extract Text & Summarize", key="dialog_extract", type="primary"):
                with st.status("Processing...", expanded=True) as status:
                    st.write("Downloading PDF...")
                    text = get_report_text(pdf_url, committee_key, report_num_str)
                    if not text:
                        status.update(label="Failed to extract text from PDF", state="error")
                    else:
                        st.write(f"Extracted {len(text):,} characters")
                        st.write("Generating summary...")
                        summary = summarize_report(text, committee_name, report_num_str, committee_key, **_get_byok_kwargs())
                        status.update(label="Done", state="complete")
                        if summary:
                            st.markdown(summary)
        else:
            st.info("Enter your LLM API key in the sidebar to extract and summarize this report.")


def clickable_report_table(reports_list, table_key, show_committee=True):
    """Render a report table with clickable titles that open a details dialog."""
    if not reports_list:
        return

    for i, r in enumerate(reports_list):
        report_num = r.get("report_number", "?")
        title = r.get("title", "No title")
        date = r.get("presented_in_ls") or r.get("laid_in_rs") or "—"
        category = classify_report(title)

        if show_committee:
            cols = st.columns([2, 0.5, 4, 1, 1])
            cols[0].caption(r.get("committee_name", ""))
            cols[1].caption(str(report_num))
            if cols[2].button(title[:120], key=f"{table_key}_{i}", type="tertiary"):
                show_report_dialog(r)
            cols[3].caption(date)
            cols[4].caption(category)
        else:
            cols = st.columns([0.5, 5, 1, 1])
            cols[0].caption(str(report_num))
            if cols[1].button(title[:120], key=f"{table_key}_{i}", type="tertiary"):
                show_report_dialog(r)
            cols[2].caption(date)
            cols[3].caption(category)


# --- Sidebar: Data controls ---
st.sidebar.header("Data Controls")

if has_data():
    all_reports = load_existing_reports()
    total = sum(len(v) for v in all_reports.values())
    committees_with_data = sum(1 for v in all_reports.values() if v)
    st.sidebar.metric("Reports in database", total)
    st.sidebar.caption(f"{committees_with_data} of {len(DRSC_COMMITTEES)} committees")
else:
    st.sidebar.warning("No data yet. Fetch reports to get started.")

with st.sidebar.expander("Fetch / Refresh Data"):
    fetch_house = st.radio("House", ["Both", "Lok Sabha only", "Rajya Sabha only"], key="fetch_house")
    fetch_ls = st.number_input("Lok Sabha #", value=CURRENT_LOK_SABHA, min_value=1, max_value=20, key="fetch_ls")

    if st.button("Fetch All Committees", type="primary"):
        both = fetch_house == "Both"
        house_code = "L" if fetch_house == "Lok Sabha only" else "R"
        with st.status("Fetching from sansad.in...", expanded=True) as status:
            if both:
                results = scrape_all_committees(lok_sabha=fetch_ls, both_houses=True)
            else:
                results = scrape_all_committees(lok_sabha=fetch_ls, house=house_code)
            total = sum(len(v) for v in results.values())
            status.update(label=f"Done — {total} reports fetched", state="complete")
        st.rerun()


# --- Sidebar: BYOK LLM API Key ---
st.sidebar.header("AI Summarization")
st.sidebar.caption("Enter your own API key to enable AI-powered summaries. Your key is used only for this session and is never stored.")

# Provider presets: (display_name, backend, default_model, base_url, needs_key)
_PROVIDER_PRESETS = {
    "Anthropic (Claude)": ("anthropic", "claude-sonnet-4-20250514", "", True),
    "OpenAI (GPT)": ("openai", "gpt-4o", "", True),
    "Google Gemini (free tier)": ("openai", "gemini-2.0-flash", "https://generativelanguage.googleapis.com/v1beta/openai/", True),
    "Groq (free tier)": ("openai", "llama-3.3-70b-versatile", "https://api.groq.com/openai/v1", True),
    "OpenRouter (free models)": ("openai", "meta-llama/llama-4-maverick:free", "https://openrouter.ai/api/v1", True),
    "Ollama (local, no key)": ("openai", "llama3.2", "http://localhost:11434/v1", False),
    "Custom (OpenAI-compatible)": ("openai", "", "", True),
}

byok_preset = st.sidebar.selectbox(
    "LLM Provider",
    list(_PROVIDER_PRESETS.keys()),
    key="byok_preset",
)
_backend, _default_model, _default_url, _needs_key = _PROVIDER_PRESETS[byok_preset]

# Show help text for specific providers
if byok_preset == "Ollama (local, no key)":
    st.sidebar.info("Requires [Ollama](https://ollama.com) running locally. Run `ollama pull llama3.2` first.")
elif byok_preset == "Google Gemini (free tier)":
    st.sidebar.info("Get a free API key at [Google AI Studio](https://aistudio.google.com/apikey). 15 requests/min, 1M tokens/day.")
elif byok_preset == "Groq (free tier)":
    st.sidebar.info("Get a free API key at [groq.com/keys](https://console.groq.com/keys). Very fast inference.")
elif byok_preset == "OpenRouter (free models)":
    st.sidebar.info("Get a free API key at [openrouter.ai/keys](https://openrouter.ai/keys). Access free open-source models.")

if _needs_key:
    byok_api_key = st.sidebar.text_input(
        "API Key",
        type="password",
        key="byok_api_key",
        placeholder="Enter your API key",
    )
else:
    byok_api_key = "ollama"  # Ollama doesn't validate keys but the client needs a non-empty string

byok_model = st.sidebar.text_input(
    "Model (optional)",
    key="byok_model",
    placeholder=_default_model,
)

if byok_preset == "Custom (OpenAI-compatible)":
    byok_base_url = st.sidebar.text_input(
        "Base URL",
        key="byok_base_url",
        placeholder="https://your-api-endpoint.com/v1",
    )
else:
    byok_base_url = _default_url


def _get_byok_kwargs():
    """Return BYOK credentials dict to pass to summarize_report."""
    _backend, _def_model, _def_url, _needs_key = _PROVIDER_PRESETS[
        st.session_state.get("byok_preset", "Anthropic (Claude)")
    ]
    api_key = st.session_state.get("byok_api_key", "") if _needs_key else "ollama"
    return {
        "api_key": api_key,
        "provider": _backend,
        "model": st.session_state.get("byok_model", "") or _def_model,
        "base_url": st.session_state.get("byok_base_url", "") or _def_url,
    }


def _has_api_key():
    """Check if user has entered an API key or is using a keyless provider."""
    _backend, _def_model, _def_url, needs_key = _PROVIDER_PRESETS[
        st.session_state.get("byok_preset", "Anthropic (Claude)")
    ]
    if not needs_key:
        return True  # Ollama doesn't need a key
    return bool(st.session_state.get("byok_api_key"))


# --- Main content: Tabs ---
if not has_data():
    st.info("No data available yet. Use **Fetch All Committees** in the sidebar to download report listings from sansad.in.")
    st.stop()

all_reports = load_existing_reports()

tab_dashboard, tab_committee, tab_search, tab_export = st.tabs([
    "Dashboard", "Committee Deep Dive", "Search", "Export"
])


# ============================================================
# TAB 1: Dashboard
# ============================================================
with tab_dashboard:
    # Top-level metrics
    total_reports = sum(len(v) for v in all_reports.values())
    committees_with_data = sum(1 for v in all_reports.values() if v)

    # Find recent reports (last 60 days)
    recent_cutoff = datetime.now() - timedelta(days=60)
    recent_reports = []
    for reports in all_reports.values():
        for r in reports:
            d = get_report_date(r)
            if d and d >= recent_cutoff:
                recent_reports.append(r)
    recent_reports.sort(key=lambda r: get_report_date(r) or datetime.min, reverse=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Reports", total_reports)
    with col2:
        st.metric("Committees", f"{committees_with_data}/{len(DRSC_COMMITTEES)}")
    with col3:
        st.metric("Recent (60 days)", len(recent_reports))
    with col4:
        st.metric("Lok Sabha", CURRENT_LOK_SABHA)

    # What's New section
    st.subheader("Recent Reports")
    if recent_reports:
        st.caption(f"{len(recent_reports)} reports from the last 60 days")
        clickable_report_table(recent_reports, "recent")
    else:
        st.info("No reports found in the last 60 days. Try fetching fresh data.")

    # Committee overview grid
    st.subheader("All Committees")

    # Build committee summary data
    committee_rows = []
    for key in sorted(DRSC_COMMITTEES.keys()):
        info = DRSC_COMMITTEES[key]
        reports = all_reports.get(key, [])
        if not reports:
            committee_rows.append({
                "Committee": info["name"],
                "Reports": 0,
                "Latest": "—",
                "DFG Reports": 0,
            })
            continue

        dates = [get_report_date(r) for r in reports]
        valid_dates = [d for d in dates if d]
        latest = max(valid_dates).strftime("%d %b %Y") if valid_dates else "—"
        dfg_count = sum(1 for r in reports if classify_report(r.get("title", "")) == "Demand for Grants")

        committee_rows.append({
            "Committee": info["name"],
            "Reports": len(reports),
            "Latest": latest,
            "DFG Reports": dfg_count,
        })

    df_committees = pd.DataFrame(committee_rows)
    st.dataframe(
        df_committees,
        hide_index=True,
        column_config={
            "Reports": st.column_config.NumberColumn(width="small"),
            "DFG Reports": st.column_config.NumberColumn(label="Demand for Grants", width="small"),
        },
    )


# ============================================================
# TAB 2: Committee Deep Dive
# ============================================================
with tab_committee:
    # Committee selector
    committee_options = {
        DRSC_COMMITTEES[k]["name"]: k
        for k in sorted(DRSC_COMMITTEES.keys())
        if k in all_reports and all_reports[k]
    }

    if not committee_options:
        st.warning("No committee data found. Fetch data using the sidebar.")
        st.stop()

    selected_name = st.selectbox("Select Committee", list(committee_options.keys()), key="dive_committee")
    selected_key = committee_options[selected_name]
    reports = all_reports[selected_key]

    # Committee stats
    col1, col2, col3, col4 = st.columns(4)
    dates = [get_report_date(r) for r in reports]
    valid_dates = [d for d in dates if d]
    with col1:
        st.metric("Total Reports", len(reports))
    with col2:
        st.metric("Latest", max(valid_dates).strftime("%d %b %Y") if valid_dates else "—")
    with col3:
        st.metric("Earliest", min(valid_dates).strftime("%d %b %Y") if valid_dates else "—")
    with col4:
        ls_reports = [r for r in reports if r.get("house") == "L"]
        rs_reports = [r for r in reports if r.get("house") == "R"]
        st.metric("LS / RS", f"{len(ls_reports)} / {len(rs_reports)}")

    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        categories = sorted(set(classify_report(r.get("title", "")) for r in reports))
        selected_category = st.selectbox("Filter by type", ["All"] + categories, key="dive_category")
    with filter_col2:
        keyword_filter = st.text_input("Filter by keyword", key="dive_keyword", placeholder="e.g. procurement, DRDO")
    with filter_col3:
        sort_order = st.selectbox("Sort by", ["Date (newest first)", "Date (oldest first)", "Report # (desc)", "Report # (asc)"], key="dive_sort")

    # Apply filters
    filtered = reports
    if selected_category != "All":
        filtered = [r for r in filtered if classify_report(r.get("title", "")) == selected_category]
    if keyword_filter:
        kw = keyword_filter.lower()
        filtered = [r for r in filtered if kw in r.get("title", "").lower()]

    # Apply sorting
    if sort_order == "Date (newest first)":
        filtered = sorted(filtered, key=lambda r: get_report_date(r) or datetime.min, reverse=True)
    elif sort_order == "Date (oldest first)":
        filtered = sorted(filtered, key=lambda r: get_report_date(r) or datetime.min)
    elif sort_order == "Report # (asc)":
        filtered = sorted(filtered, key=lambda r: r.get("report_number", 0))
    # "Report # (desc)" is the default storage order, no re-sort needed

    st.caption(f"Showing {len(filtered)} of {len(reports)} reports")

    # Display reports with expandable details
    for r in filtered:
        date = r.get("presented_in_ls") or r.get("laid_in_rs") or "—"
        category = classify_report(r.get("title", ""))
        house_label = "LS" if r.get("house") == "L" else ("RS" if r.get("house") == "R" else "")
        report_num = r.get("report_number", "?")

        # Status indicators
        status_parts = []
        if has_summary(selected_key, report_num):
            status_parts.append("summarized")
        elif has_text(selected_key, report_num):
            status_parts.append("text extracted")
        status_str = f" [{', '.join(status_parts)}]" if status_parts else ""

        header = f"**#{report_num}** | {category} | {house_label} | {date}{status_str}"

        with st.expander(header):
            st.write(r.get("title", "No title"))

            col_a, col_b = st.columns(2)
            with col_a:
                if r.get("presented_in_ls"):
                    st.write(f"**Presented in LS:** {r['presented_in_ls']}")
                if r.get("laid_in_rs"):
                    st.write(f"**Laid in RS:** {r['laid_in_rs']}")
                st.write(f"**Lok Sabha:** {r.get('lok_sabha', '—')}")
            with col_b:
                pdf_url = r.get("pdf_url", "")
                if pdf_url:
                    st.markdown(f"[PDF (English)]({pdf_url})")
                pdf_hindi = r.get("pdf_url_hindi", "")
                if pdf_hindi:
                    st.markdown(f"[PDF (Hindi)]({pdf_hindi})")

            # Summarize button inline
            btn_key = f"summarize_{selected_key}_{report_num}"
            if _has_api_key():
                if st.button("Extract & Summarize", key=btn_key, type="secondary"):
                    if not pdf_url:
                        st.error("No PDF URL available.")
                    else:
                        with st.status("Processing...", expanded=True) as status:
                            st.write("Downloading PDF...")
                            text = get_report_text(pdf_url, selected_key, str(report_num))
                            if not text:
                                status.update(label="Failed to extract text", state="error")
                            else:
                                st.write(f"Extracted {len(text):,} characters")
                                st.write("Generating summary...")
                                summary = summarize_report(text, selected_name, str(report_num), selected_key, **_get_byok_kwargs())
                                status.update(label="Done", state="complete")
                                if summary:
                                    st.markdown(summary)
            else:
                st.caption("Enter your LLM API key in the sidebar to enable summarization.")

            # Show cached summary if available
            if has_summary(selected_key, report_num):
                safe_name = str(report_num).replace("/", "-").replace(" ", "_")
                summary_path = os.path.join(SUMMARIES_DIR, selected_key, f"{safe_name}.md")
                with open(summary_path, "r") as f:
                    st.markdown(f.read())


# ============================================================
# TAB 3: Search
# ============================================================
with tab_search:
    st.subheader("Search Reports")

    search_col1, search_col2, search_col3 = st.columns([3, 1, 1])
    with search_col1:
        query = st.text_input("Search reports", placeholder="e.g. semiconductor, grants, procurement, border roads", key="search_query")
    with search_col2:
        committee_filter = st.selectbox(
            "Committee",
            ["All Committees"] + [DRSC_COMMITTEES[k]["name"] for k in sorted(DRSC_COMMITTEES.keys())],
            key="search_committee",
        )
    with search_col3:
        search_scope = st.selectbox("Search in", ["Titles only", "Titles + Full text"], key="search_scope")

    if query:
        filter_key = None
        if committee_filter != "All Committees":
            filter_key = next(k for k, v in DRSC_COMMITTEES.items() if v["name"] == committee_filter)

        # Title search
        title_results = search_reports(query, filter_key)
        title_ids = {(r.get("committee"), r.get("report_number")) for r in title_results}

        # Full-text search
        fulltext_results = []
        if search_scope == "Titles + Full text" and os.path.exists(TEXT_DIR):
            query_lower = query.lower()
            committees_to_search = [filter_key] if filter_key else list(DRSC_COMMITTEES.keys())

            for ckey in committees_to_search:
                committee_text_dir = os.path.join(TEXT_DIR, ckey)
                if not os.path.isdir(committee_text_dir):
                    continue
                for txt_file in os.listdir(committee_text_dir):
                    if not txt_file.endswith(".txt"):
                        continue
                    report_num_str = txt_file.replace(".txt", "").replace("-", "/").replace("_", " ")
                    # Skip if already found by title search
                    try:
                        report_num = int(report_num_str)
                    except ValueError:
                        report_num = report_num_str
                    if (ckey, report_num) in title_ids:
                        continue
                    # Search file content
                    filepath = os.path.join(committee_text_dir, txt_file)
                    try:
                        with open(filepath, "r") as f:
                            content = f.read()
                        if query_lower in content.lower():
                            # Find the matching report in our data
                            for r in all_reports.get(ckey, []):
                                if r.get("report_number") == report_num:
                                    fulltext_results.append(r)
                                    break
                    except Exception:
                        continue

        total_results = len(title_results) + len(fulltext_results)
        if total_results > 0:
            st.success(f"Found {total_results} report(s) matching **\"{query}\"**")

            if title_results:
                st.write(f"**Title matches** ({len(title_results)})")
                clickable_report_table(title_results, "search_title")

            if fulltext_results:
                st.write(f"**Full-text matches** ({len(fulltext_results)})")
                clickable_report_table(fulltext_results, "search_ft")

            if search_scope == "Titles + Full text":
                # Count how many reports have extracted text
                text_count = 0
                committees_to_count = [filter_key] if filter_key else list(DRSC_COMMITTEES.keys())
                for ckey in committees_to_count:
                    cdir = os.path.join(TEXT_DIR, ckey)
                    if os.path.isdir(cdir):
                        text_count += len([f for f in os.listdir(cdir) if f.endswith(".txt")])
                total_report_count = sum(len(all_reports.get(k, [])) for k in committees_to_count)
                st.caption(f"Full-text search covers {text_count} of {total_report_count} reports. Extract more reports in Committee Deep Dive to expand coverage.")
        else:
            st.warning(f"No reports matching \"{query}\".")


# ============================================================
# TAB 4: Export
# ============================================================
with tab_export:
    st.subheader("Export Data")

    export_col1, export_col2 = st.columns(2)
    with export_col1:
        export_committee_filter = st.selectbox(
            "Committee",
            ["All Committees"] + [DRSC_COMMITTEES[k]["name"] for k in sorted(DRSC_COMMITTEES.keys())],
            key="export_committee",
        )
    with export_col2:
        export_type = st.selectbox(
            "What to export",
            ["Report metadata", "Summaries", "Extracted text"],
            key="export_type",
        )

    if export_committee_filter == "All Committees":
        export_keys = list(DRSC_COMMITTEES.keys())
    else:
        export_keys = [next(k for k, v in DRSC_COMMITTEES.items() if v["name"] == export_committee_filter)]

    if export_type == "Report metadata":
        flat = []
        for k in export_keys:
            flat.extend(all_reports.get(k, []))

        if not flat:
            st.warning("No reports found.")
        else:
            df = pd.DataFrame(flat)
            display_cols = [
                "committee_name", "report_number", "title",
                "presented_in_ls", "laid_in_rs", "lok_sabha", "house", "pdf_url",
            ]
            available_cols = [c for c in display_cols if c in df.columns]
            df_export = df[available_cols]

            st.write(f"**{len(df_export)} reports** ready for download")
            st.dataframe(df_export.head(20), hide_index=True)

            csv_data = df_export.to_csv(index=False)
            st.download_button(
                "Download CSV",
                data=csv_data,
                file_name="parliamentwatch_reports.csv",
                mime="text/csv",
            )

    elif export_type == "Summaries":
        # Collect all available summaries
        summary_entries = []
        for ckey in export_keys:
            cdir = os.path.join(SUMMARIES_DIR, ckey)
            if not os.path.isdir(cdir):
                continue
            for fname in sorted(os.listdir(cdir)):
                if not fname.endswith(".md"):
                    continue
                filepath = os.path.join(cdir, fname)
                try:
                    with open(filepath, "r") as f:
                        content = f.read()
                except Exception:
                    continue
                report_num_str = fname.replace(".md", "").replace("-", "/").replace("_", " ")
                try:
                    report_num = int(report_num_str)
                except ValueError:
                    report_num = report_num_str
                # Find report title from metadata
                title = ""
                for r in all_reports.get(ckey, []):
                    if r.get("report_number") == report_num:
                        title = r.get("title", "")
                        break
                committee_name = DRSC_COMMITTEES.get(ckey, {}).get("name", ckey)
                summary_entries.append({
                    "committee": committee_name,
                    "report_number": report_num,
                    "title": title,
                    "summary": content,
                })

        if not summary_entries:
            st.warning("No summaries available. Extract and summarize reports in the Committee Deep Dive tab first.")
        else:
            st.write(f"**{len(summary_entries)} summaries** available for download")
            for entry in summary_entries[:5]:
                with st.expander(f"{entry['committee']} — #{entry['report_number']}: {entry['title'][:80]}"):
                    st.markdown(entry["summary"][:500] + ("..." if len(entry["summary"]) > 500 else ""))

            # Combine all summaries into one markdown file
            md_lines = ["# Parliamentary Committee Report Summaries\n"]
            for entry in summary_entries:
                md_lines.append(f"## {entry['committee']} — Report #{entry['report_number']}")
                md_lines.append(f"**{entry['title']}**\n")
                md_lines.append(entry["summary"])
                md_lines.append("\n---\n")
            md_data = "\n".join(md_lines)

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "Download all summaries (Markdown)",
                    data=md_data,
                    file_name="parliamentwatch_summaries.md",
                    mime="text/markdown",
                )
            with col2:
                # CSV with summary column
                df_summaries = pd.DataFrame(summary_entries)
                csv_data = df_summaries.to_csv(index=False)
                st.download_button(
                    "Download all summaries (CSV)",
                    data=csv_data,
                    file_name="parliamentwatch_summaries.csv",
                    mime="text/csv",
                )

    elif export_type == "Extracted text":
        # Collect all available extracted text
        text_entries = []
        for ckey in export_keys:
            cdir = os.path.join(TEXT_DIR, ckey)
            if not os.path.isdir(cdir):
                continue
            for fname in sorted(os.listdir(cdir)):
                if not fname.endswith(".txt"):
                    continue
                filepath = os.path.join(cdir, fname)
                try:
                    with open(filepath, "r") as f:
                        content = f.read()
                except Exception:
                    continue
                report_num_str = fname.replace(".txt", "").replace("-", "/").replace("_", " ")
                try:
                    report_num = int(report_num_str)
                except ValueError:
                    report_num = report_num_str
                title = ""
                for r in all_reports.get(ckey, []):
                    if r.get("report_number") == report_num:
                        title = r.get("title", "")
                        break
                committee_name = DRSC_COMMITTEES.get(ckey, {}).get("name", ckey)
                text_entries.append({
                    "committee": committee_name,
                    "report_number": report_num,
                    "title": title,
                    "char_count": len(content),
                    "_content": content,
                    "_committee_key": ckey,
                })

        if not text_entries:
            st.warning("No extracted text available. Extract reports in the Committee Deep Dive tab first.")
        else:
            st.write(f"**{len(text_entries)} reports** with extracted text")
            df_text = pd.DataFrame([{k: v for k, v in e.items() if not k.startswith("_")} for e in text_entries])
            st.dataframe(df_text, hide_index=True)

            # Download individual texts as a combined file
            combined = []
            for entry in text_entries:
                combined.append(f"={'=' * 60}")
                combined.append(f"COMMITTEE: {entry['committee']}")
                combined.append(f"REPORT #: {entry['report_number']}")
                combined.append(f"TITLE: {entry['title']}")
                combined.append(f"={'=' * 60}\n")
                combined.append(entry["_content"])
                combined.append("\n")
            combined_text = "\n".join(combined)

            st.download_button(
                "Download all extracted text",
                data=combined_text,
                file_name="parliamentwatch_fulltext.txt",
                mime="text/plain",
            )

# --- Attribution footer ---
st.markdown(
    '<div class="attribution">'
    'Created by <strong>Pranay Kotasthane</strong> using Claude Opus &nbsp;|&nbsp; '
    '<a href="https://github.com/pranaykotas/parliamentwatch" target="_blank">GitHub</a>'
    '</div>',
    unsafe_allow_html=True,
)
