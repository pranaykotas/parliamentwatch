"""Summarize committee report text using a configurable LLM provider."""

import os
from dotenv import load_dotenv
from config import SUMMARIES_DIR, LLM_PROVIDER, LLM_MODEL, LLM_API_KEY, LLM_BASE_URL

load_dotenv()


def ensure_dirs(committee_key):
    """Create summaries directory for a committee."""
    os.makedirs(os.path.join(SUMMARIES_DIR, committee_key), exist_ok=True)


def get_cached_summary(committee_key, report_number):
    """Return cached summary if it exists."""
    ensure_dirs(committee_key)
    safe_name = report_number.replace("/", "-").replace(" ", "_")
    summary_path = os.path.join(SUMMARIES_DIR, committee_key, f"{safe_name}.md")

    if os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            return f.read()
    return None


def _call_llm(prompt, provider=None, api_key=None, model=None, base_url=None):
    """
    Call the configured LLM provider and return the response text.

    Accepts optional overrides (for BYOK); falls back to config/.env values.
    """
    effective_key = api_key or LLM_API_KEY
    effective_provider = (provider or LLM_PROVIDER).lower()
    effective_model = model or LLM_MODEL
    effective_base_url = base_url or LLM_BASE_URL

    if not effective_key or effective_key == "your-api-key-here":
        return None

    if effective_provider == "anthropic":
        from anthropic import Anthropic
        m = effective_model or "claude-sonnet-4-20250514"
        print(f"  Using Anthropic ({m})...")
        client = Anthropic(api_key=effective_key)
        message = client.messages.create(
            model=m,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    elif effective_provider == "openai":
        from openai import OpenAI
        m = effective_model or "gpt-4o"
        print(f"  Using OpenAI-compatible ({m})...")
        client_kwargs = {"api_key": effective_key}
        if effective_base_url:
            client_kwargs["base_url"] = effective_base_url
        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=m,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    else:
        print(f"  Unknown LLM_PROVIDER: {effective_provider}. Use 'anthropic' or 'openai'.")
        return None


def summarize_report(text, committee_name, report_number, committee_key,
                     api_key=None, provider=None, model=None, base_url=None):
    """
    Summarize a report using the configured LLM.

    Accepts optional BYOK credentials that override config/.env values.
    CLI usage (no overrides) falls back to .env configuration.
    """
    # Check cache first
    cached = get_cached_summary(committee_key, report_number)
    if cached:
        print(f"  Summary already cached for {committee_key}/{report_number}")
        return cached

    effective_key = api_key or LLM_API_KEY
    if not effective_key or effective_key == "your-api-key-here":
        print("  No LLM API key set. Showing text preview instead.")
        preview_len = 2000
        preview = text[:preview_len]
        if len(text) > preview_len:
            preview += f"\n\n[... showing {preview_len} of {len(text)} characters. Provide an API key for full summary ...]"
        return preview

    # Truncate very long reports to fit context window
    max_chars = 400000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... text truncated due to length ...]"

    prompt = f"""You are analyzing an Indian Parliamentary Committee report.

Committee: {committee_name}
Report Number: {report_number}

Below is the full text of the report. Please provide a structured summary with:

1. **Subject/Topic**: What is this report about?
2. **Key Findings**: The main observations and findings (bullet points)
3. **Recommendations**: Key recommendations made by the committee (bullet points)
4. **Ministries/Departments Involved**: Which government bodies are addressed
5. **Notable Observations**: Any particularly interesting or surprising findings

Keep the summary concise but comprehensive — aim for 500-800 words.

Report text:
{text}"""

    print(f"  Summarizing report {report_number}...")
    try:
        summary = _call_llm(prompt, provider=provider, api_key=api_key,
                            model=model, base_url=base_url)

        if not summary:
            print("  LLM returned no response.")
            return None

        # Cache the summary
        ensure_dirs(committee_key)
        safe_name = report_number.replace("/", "-").replace(" ", "_")
        summary_path = os.path.join(SUMMARIES_DIR, committee_key, f"{safe_name}.md")
        with open(summary_path, "w") as f:
            f.write(summary)

        print(f"  Summary saved to {summary_path}")
        return summary
    except Exception as e:
        print(f"  Error summarizing report: {e}")
        return None
