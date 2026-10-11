"""Tests for atr.py. Titles are real ones from data/reports.json."""

import pytest

from atr import atr_export_fields, build_atr_links, get_atr_link, parse_atr_reference


@pytest.mark.parametrize("title, expected", [
    # "contained in the <words> Report"
    ("Twenty-Eighth Report (18th Lok Sabha) of the Standing Committee on Defence on Action Taken by the "
     "Government on the Observations/Recommendations contained in the Twenty-Third Report (18th Lok Sabha) "
     "on the subject 'Review of Sainik Schools'",
     (23, 18)),
    # "contained in its", RS hundreds
    ("Action Taken by the Government on the Recommendations of the Committee contained in its Three Hundred "
     "and Sixteenth Report on Issues Related to Safety of Women",
     (316, None)),
    # "contained in their", earlier Lok Sabha
    ("Action Taken by the Government on the Observations/Recommendations of the Committee contained in their "
     "Fiftieth Report (Seventeenth Lok Sabha) on 'Promotion of Medical Device Industry'",
     (50, 17)),
    # no article
    ("Eighteenth Report (18th Lok Sabha) on Action Taken by the Government on the Observation/Recommendation "
     "contained in Thirteenth Report (18th Lok Sabha) on the subject 'Health hazards'",
     (13, 18)),
    # digits
    ("18th Report on Action Taken on the Observations/ Recommendations contained in the 14th Report of the "
     "Committee on Demands for Grants (2026-27)",
     (14, None)),
    # "Action Taken on <words> Report", own number comes first
    ("159th Report on Action Taken on One Hundred Forty Fifth Report of the Committee on Demands for Grants (2025-26)",
     (145, None)),
    # "Action Taken Notes on Nth Report"
    ("Action Taken Notes on 313th Report of the Department-related Parliamentary Standing Committee on Education",
     (313, None)),
    # "in the" without "contained", "Hundred-" without "One"
    ("Hundred-Fifteenth Report Action Taken by Government on the Recommendations/Observations in the Thirty "
     "First Report on Functioning of Central Government Hospitals",
     (31, None)),
    ("Action Taken by the Government on the Observations/ Recommendations of the Public Accounts Committee "
     "contained in their Hundred and Third Report (Seventeenth Lok Sabha) on the subject",
     (103, 17)),
    # run together
    ("Forty Third Report on Action Taken by the Government on the Observations/Recommendations contained in the "
     "TwentyEighth Report (Eighteenth Lok Sabha) of the Standing Committee on Agriculture",
     (28, 18)),
    # misspelling seen in the data
    ("Report on Action Taken by the Government on the Recommendations contained in the Two Hundred forty-forth "
     "Report on Demands for Grants",
     (244, None)),
    # spaced hyphen
    ("Thirty- fourth Report on Action Taken by the Government on the Observations/Recommendations of the "
     "Committee contained in their Twenty- sixth Report (18th Lok Sabha) on Demands for Grants",
     (26, 18)),
    # Lok Sabha after the committee name, short "LS"
    ("Action Taken by the Government on the Observation/Recommendation contained in Seventh Report of the "
     "Standing Committee on Chemicals and Fertilizers (18th Lok Sabha) on 'Demands for Grants'",
     (7, 18)),
    ("Action Taken by the Government on the Observations/Recommendations of the Committee contained in their "
     "119th Report (17th LS) on \"Loss of Revenue\"",
     (119, 17)),
    # entities, encoded more than once, and line breaks
    ("Three hundred and Second Report on Action Taken Notes furnished by the Department of Heavy Industry on the "
     "recommendations contained in the Committee&amp;#39;s Two Hundred Ninety Fifth Report",
     (295, None)),
    ("Thirteenth Report (18th Lok Sabha) of the Committee on Action Taken by the Government on the \r\n"
     "Observations/Recommendations contained in the Third Report of Standing Committee on Defence",
     (3, None)),
    # spaced apostrophe
    ("Action taken by the Government on recommendations contained in Committee &#39; s 88th report on "
     "performance review of Rashtriya Ispat Nigam ltd.",
     (88, None)),
    # cardinal used as an ordinal
    ("Action Taken by the Government on the Recommendations/Observations of the Committee contained in its One "
     "Hundred and Ninety Two Report on the Demands for Grants (2013-14) of the Ministry of Culture",
     (192, None)),
    # en dash
    ("Action  taken   by  the  department  of  science &amp; technology on  the recommendations contained in "
     "the one hundred &#8211;Seventeenth report of the department related Parliamentary standing committee",
     (117, None)),
])
def test_parses_referenced_report(title, expected):
    ref = parse_atr_reference(title)
    assert ref is not None
    assert (ref["report_number"], ref["lok_sabha"]) == expected


@pytest.mark.parametrize("title", [
    "DISASTER MANAGEMENT",
    "Demands for Grants (2026-27) of the Ministry of Defence",
    # mentions Action Taken Notes but responds to no report
    "\"Non-Compliance in timely submission of Action Taken Notes on Non-selected Audit Paragraphs\r\n"
    "& Excess Expenditure\" relating to various Ministries",
])
def test_returns_none_for_non_atr(title):
    assert parse_atr_reference(title) is None


def test_returns_none_for_repeated_hundred():
    # A typo in the data; reading it would give report 20221.
    assert parse_atr_reference(
        "Action Taken by the Government on the Observations/Recommendations of the Committee contained in its "
        "Two Hundred Two Hundred and Twenty First Report on the Demands for Grants") is None


def _report(committee, number, title, house="R", lok_sabha=18):
    return {"committee": committee, "report_number": number, "title": title,
            "house": house, "lok_sabha": lok_sabha}


ORIGINAL = "Demands for Grants (2026-27) of the Ministry of Defence"


def test_links_atr_to_original_both_ways():
    reports = {"education": [
        _report("education", 316, "Safety of Women"),
        _report("education", 334, "Action Taken by the Government on the Recommendations contained in its "
                                  "Three Hundred and Sixteenth Report on Safety of Women"),
    ]}
    links = build_atr_links(reports)
    assert get_atr_link(links, reports["education"][1])["responds_to"] == {"report_number": 316, "lok_sabha": None, "in_data": True}
    assert get_atr_link(links, reports["education"][0])["action_taken_reports"] == [
        {"report_number": 334, "lok_sabha": None}]


def test_ls_atr_without_lok_sabha_uses_its_own():
    reports = {"defence": [
        _report("defence", 3, ORIGINAL, house="L"),
        _report("defence", 13, "Thirteenth Report of the Committee on Action Taken by the Government on the "
                               "Recommendations contained in the Third Report of Standing Committee on Defence",
                house="L"),
    ]}
    links = build_atr_links(reports)
    assert get_atr_link(links, reports["defence"][1])["responds_to"] == {"report_number": 3, "lok_sabha": 18, "in_data": True}
    assert get_atr_link(links, reports["defence"][0])["action_taken_reports"] == [
        {"report_number": 13, "lok_sabha": 18}]


def test_ls_atr_on_earlier_lok_sabha_does_not_link_to_same_number():
    # Report 50 of the 18th Lok Sabha exists, but the ATR responds to report 50 of the 17th.
    reports = {"chemicals": [
        _report("chemicals", 50, ORIGINAL, house="L"),
        _report("chemicals", 2, "Action Taken by the Government on the Recommendations of the Committee contained "
                                "in their Fiftieth Report (Seventeenth Lok Sabha) on Medical Devices", house="L"),
    ]}
    links = build_atr_links(reports)
    assert get_atr_link(links, reports["chemicals"][1])["responds_to"] == {"report_number": 50, "lok_sabha": 17, "in_data": False}
    assert get_atr_link(links, reports["chemicals"][0])["action_taken_reports"] == []


def test_ls_atr_citing_a_later_number_leaves_lok_sabha_unknown():
    # LS numbers restart each Lok Sabha, so report 3 can't respond to the same Lok Sabha's report 28.
    reports = {"external_affairs": [
        _report("external_affairs", 28, ORIGINAL, house="L"),
        _report("external_affairs", 3, "Action taken by the Government on the observations/recommendations "
                                       "contained in the Twenty Eighth Report of the Committee", house="L"),
    ]}
    links = build_atr_links(reports)
    assert get_atr_link(links, reports["external_affairs"][1])["responds_to"] == {
        "report_number": 28, "lok_sabha": None, "in_data": False}
    assert get_atr_link(links, reports["external_affairs"][0])["action_taken_reports"] == []
    assert atr_export_fields(reports["external_affairs"][1], links)["responds_to_lok_sabha"] == ""


def test_does_not_link_across_committees():
    reports = {
        "health": [_report("health", 14, ORIGINAL)],
        "home_affairs": [_report("home_affairs", 20, "Action Taken on the 14th Report of the Committee")],
    }
    links = build_atr_links(reports)
    assert get_atr_link(links, reports["home_affairs"][0])["responds_to"]["in_data"] is False
    assert get_atr_link(links, reports["health"][0])["action_taken_reports"] == []


def test_duplicate_records_are_listed_once():
    atr = "Action Taken Notes on 313th Report of the Committee"
    reports = {"education": [
        _report("education", 313, ORIGINAL),
        _report("education", 322, atr),
        _report("education", 322, atr, lok_sabha=None),
    ]}
    links = build_atr_links(reports)
    assert get_atr_link(links, reports["education"][0])["action_taken_reports"] == [
        {"report_number": 322, "lok_sabha": None}]


def test_export_fields():
    reports = {"chemicals": [
        _report("chemicals", 7, ORIGINAL, house="L"),
        _report("chemicals", 17, "Action Taken by the Government on the Recommendation contained in Seventh "
                                 "Report (18th Lok Sabha) on Demands for Grants", house="L"),
    ]}
    links = build_atr_links(reports)
    assert atr_export_fields(reports["chemicals"][1], links) == {
        "responds_to_report": "7", "responds_to_lok_sabha": "18", "action_taken_reports": ""}
    assert atr_export_fields(reports["chemicals"][0], links) == {
        "responds_to_report": "", "responds_to_lok_sabha": "", "action_taken_reports": "17"}


def test_cli_csv_export_includes_atr_columns(tmp_path, monkeypatch):
    import csv
    import exporter

    reports = {"education": [
        _report("education", 316, "Safety of Women"),
        _report("education", 334, "Action Taken by the Government on the Recommendations contained in its "
                                  "Three Hundred and Sixteenth Report on Safety of Women"),
    ]}
    monkeypatch.setattr(exporter, "load_existing_reports", lambda: reports)
    out = tmp_path / "reports.csv"
    exporter.export_csv(output_path=str(out))

    rows = {r["report_number"]: r for r in csv.DictReader(out.open())}
    assert rows["334"]["responds_to_report"] == "316"
    assert rows["316"]["action_taken_reports"] == "334"


def test_same_number_in_two_lok_sabhas_links_to_the_right_one():
    # The sidebar can merge reports from several Lok Sabhas into one committee.
    old = _report("chemicals", 50, ORIGINAL, house="L", lok_sabha=17)
    new = _report("chemicals", 50, ORIGINAL, house="L", lok_sabha=18)
    cross = _report("chemicals", 2, "Action Taken by the Government on the Recommendations of the Committee "
                                    "contained in their Fiftieth Report (Seventeenth Lok Sabha)", house="L")
    reports = {"chemicals": [old, new, cross]}
    links = build_atr_links(reports)

    assert get_atr_link(links, cross)["responds_to"]["in_data"] is True
    assert get_atr_link(links, old)["action_taken_reports"] == [{"report_number": 2, "lok_sabha": 18}]
    assert get_atr_link(links, new)["action_taken_reports"] == []
    assert atr_export_fields(old, links)["action_taken_reports"] == "2 (18th Lok Sabha)"
