"""Link Action Taken Reports (ATRs) to the reports they respond to.

An ATR names the original report in its title, for example "...Action Taken
by the Government on the Observations/Recommendations contained in the
Twenty-Third Report (18th Lok Sabha)...". This module reads that reference
from the title. Nothing is stored; links are computed from reports.json
whenever they're needed.

Adapted from commoner-probe's atr_linkage module
(https://github.com/CommonerLLP/commoner-probe).
"""

import html
import re

_UNITS = {
    "one": 1, "first": 1, "two": 2, "second": 2, "three": 3, "third": 3,
    "four": 4, "fourth": 4, "forth": 4, "five": 5, "fifth": 5, "six": 6, "sixth": 6,
    "seven": 7, "seventh": 7, "eight": 8, "eighth": 8, "nine": 9, "ninth": 9,
    "ten": 10, "tenth": 10, "eleven": 11, "eleventh": 11, "twelve": 12, "twelfth": 12,
    "thirteen": 13, "thirteenth": 13, "fourteen": 14, "fourteenth": 14,
    "fifteen": 15, "fifteenth": 15, "sixteen": 16, "sixteenth": 16,
    "seventeen": 17, "seventeenth": 17, "eighteen": 18, "eighteenth": 18,
    "nineteen": 19, "nineteenth": 19,
    "twenty": 20, "twentieth": 20, "thirty": 30, "thirtieth": 30,
    "forty": 40, "fortieth": 40, "fifty": 50, "fiftieth": 50, "sixty": 60, "sixtieth": 60,
    "seventy": 70, "seventieth": 70, "eighty": 80, "eightieth": 80,
    "ninety": 90, "ninetieth": 90,
}

# Longest first, so "fourteenth" wins over "fourteen" and "fourth".
_WORD = "|".join(sorted(list(_UNITS) + ["hundred", "hundredth", "and"], key=len, reverse=True))
# Cardinals count as endings too: some titles say "Ninety Two Report".
_NUMBER_END = "|".join(sorted(list(_UNITS) + ["hundredth"], key=len, reverse=True))
# A spelled-out ordinal ("Three Hundred and Sixteenth", "TwentyEighth",
# "Twenty- sixth", "one hundred –Fourteenth") or a numeric one ("14th").
_ORDINAL = rf"(?:\d+\s*(?:st|nd|rd|th)|(?:(?:{_WORD})[\s\-–—]*)*?(?:{_NUMBER_END}))"

# The referenced report follows "in" or "on" somewhere after "Action Taken":
# "contained in the/its/their ...", "Action Taken on ...", "... in the ...".
_REFERENCE_RE = re.compile(
    rf"\b(?:in|on)\s+(?:(?:the|its|their|committee\s*['’]?\s*s)\s+)*(?P<ordinal>{_ORDINAL})\s*Report\b",
    re.IGNORECASE,
)
_LOK_SABHA_RE = re.compile(rf"\(\s*(?P<ordinal>{_ORDINAL})\s*(?:Lok\s*Sabha|LS)\s*\)", re.IGNORECASE)
# How far after the referenced report to look for its Lok Sabha, which can
# follow the committee's name: "Seventh Report of the Standing Committee on
# Chemicals and Fertilizers (18th Lok Sabha)".
_LOK_SABHA_WINDOW = 120


def _clean(title):
    """Decode HTML entities (some titles are encoded several times) and collapse whitespace."""
    for _ in range(5):
        decoded = html.unescape(title)
        if decoded == title:
            break
        title = decoded
    return re.sub(r"\s+", " ", title)


def _ordinal_to_int(text):
    digits = re.match(r"\d+", text)
    if digits:
        return int(digits.group())
    total = 0
    for word in re.findall(_WORD, text.lower()):
        if word.startswith("hundred"):
            # A second "hundred" is a typo ("Two Hundred Two Hundred and ..."), not a number.
            if total >= 100:
                return None
            total = (total or 1) * 100
        elif word != "and":
            total += _UNITS[word]
    return total or None


def parse_atr_reference(title):
    """Return the report an ATR responds to, or None if the title isn't an ATR.

    Returns {"report_number": int, "lok_sabha": int or None}. lok_sabha is set
    only when the title names the referenced report's Lok Sabha.
    """
    text = _clean(title or "")
    anchor = re.search(r"action\s+taken", text, re.IGNORECASE)
    if not anchor:
        return None
    match = _REFERENCE_RE.search(text, anchor.end())
    if not match:
        return None
    report_number = _ordinal_to_int(match.group("ordinal"))
    if report_number is None:
        return None

    lok_sabha = None
    ls_match = _LOK_SABHA_RE.search(text[match.end():match.end() + _LOK_SABHA_WINDOW])
    if ls_match:
        lok_sabha = _ordinal_to_int(ls_match.group("ordinal"))
    return {"report_number": report_number, "lok_sabha": lok_sabha}



def _link_key(committee, report):
    """LS report numbers restart each Lok Sabha; RS numbers run continuously."""
    lok_sabha = None if report.get("house") == "R" else report.get("lok_sabha")
    return (committee, lok_sabha, report.get("report_number"))


def build_atr_links(reports):
    """Link every ATR in reports ({committee_key: [report, ...]}) to its original.

    Look up a report's links with get_atr_link(). Each link has "responds_to",
    which is None for reports that aren't ATRs and otherwise
    {"report_number", "lok_sabha", "in_data"}, and "action_taken_reports", a list
    of {"report_number", "lok_sabha"}. Links stay within one committee. An LS link
    must also match the Lok Sabha, taken from the title or else from the ATR. If
    neither can apply, the link's "lok_sabha" is None and "in_data" is False.
    """
    links = {}
    for committee, records in reports.items():
        for r in records:
            links.setdefault(_link_key(committee, r), {"responds_to": None, "action_taken_reports": []})

        for r in records:
            ref = parse_atr_reference(r.get("title", ""))
            if not ref:
                continue
            is_rs = r.get("house") == "R"
            lok_sabha = None if is_rs else ref["lok_sabha"]
            # A title that names no Lok Sabha means the ATR's own, unless it cites a number at
            # or above the ATR's: LS numbers restart each Lok Sabha, so that report is from an
            # earlier one, which is unknown.
            same_lok_sabha_possible = ref["report_number"] < (r.get("report_number") or 0)
            if not is_rs and lok_sabha is None and same_lok_sabha_possible:
                lok_sabha = r.get("lok_sabha")
            original_key = (committee, lok_sabha, ref["report_number"])
            in_data = (is_rs or lok_sabha is not None) and original_key in links
            links[_link_key(committee, r)]["responds_to"] = {
                "report_number": ref["report_number"], "lok_sabha": lok_sabha, "in_data": in_data,
            }
            if in_data:
                atr = {"report_number": r.get("report_number"), "lok_sabha": None if is_rs else r.get("lok_sabha")}
                responses = links[original_key]["action_taken_reports"]
                if atr not in responses:
                    responses.append(atr)

    for link in links.values():
        link["action_taken_reports"].sort(key=lambda a: (a["lok_sabha"] or 0, a["report_number"]))
    return links


def get_atr_link(links, report):
    """Return the links for one report, as built by build_atr_links()."""
    return links.get(_link_key(report.get("committee"), report),
                     {"responds_to": None, "action_taken_reports": []})


def format_report_ref(report_number, lok_sabha, own_lok_sabha):
    """'28', or '2 (18th Lok Sabha)' when the Lok Sabha differs from the reader's report."""
    if lok_sabha and lok_sabha != own_lok_sabha:
        return f"{report_number} ({lok_sabha}th Lok Sabha)"
    return str(report_number)


def atr_export_fields(report, links):
    """Return the ATR columns for one report's row in a CSV export."""
    link = get_atr_link(links, report)
    responds_to = link["responds_to"] or {}
    # Strings throughout, so the columns have one type for pandas and Arrow.
    return {
        "responds_to_report": str(responds_to.get("report_number") or ""),
        "responds_to_lok_sabha": str(responds_to.get("lok_sabha") or ""),
        "action_taken_reports": "; ".join(
            format_report_ref(a["report_number"], a["lok_sabha"], report.get("lok_sabha"))
            for a in link["action_taken_reports"]
        ),
    }
