"""Click-through navigation between ATRs and originals in the Committee Deep Dive.

These run the real app on data/reports.json, so they're slower than test_atr.py.
"""

import pytest
from streamlit.testing.v1 import AppTest


def _deep_dive(committee_name):
    at = AppTest.from_file("app.py", default_timeout=180)
    at.secrets["LLM_API_KEY"] = ""
    at.run()
    select = at.selectbox(key="dive_committee")
    select.select(next(o for o in select.options if committee_name in o)).run()
    return at


def _button(at, label):
    return next(b for b in at.button if b.label == label)


def _shown_reports(at):
    return [e.label.split("**")[1] for e in at.expander if e.label.startswith("**#")]


@pytest.fixture(scope="module")
def defence():
    return _deep_dive("Defence")


def test_clicking_original_report_focuses_it(defence):
    _button(defence, "Responds to Report #23").click().run()
    assert not defence.exception
    assert _shown_reports(defence) == ["#23"]
    assert next(e for e in defence.expander if e.label.startswith("**#23**")).proto.expanded


def test_show_all_reports_clears_focus(defence):
    _button(defence, "Show all reports").click().run()
    assert not defence.exception
    assert len(_shown_reports(defence)) > 1


def test_clicking_atr_focuses_it(defence):
    _button(defence, "Action taken: Report #28").click().run()
    assert _shown_reports(defence) == ["#28"]


def test_committee_with_duplicate_records_renders():
    # education has duplicate report numbers; each nav button still needs a unique key.
    at = _deep_dive("Education")
    assert not at.exception


def test_atr_links_have_arrow_icon():
    at = _deep_dive("Defence")
    atr_buttons = [b for b in at.button if (b.key or "").startswith("atr_nav_")]
    assert atr_buttons
    assert all(b.proto.icon == ":material/arrow_forward:" for b in atr_buttons)

