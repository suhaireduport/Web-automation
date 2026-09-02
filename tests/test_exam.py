"""Exams list page: tabs, counts and empty states.

Past exam cards are covered in test_past_exam.py and the instructions page in
test_exam_start.py.
"""
import re
import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.exam_page import ExamPage

MOBILE = "9876543210"

EXAMS_URL = "https://eduport-react.pages.dev/exams"


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture
def exam_page(page):

    home_page = HomePage(page)
    home_page.get_exams_button().click()
    page.wait_for_url(EXAMS_URL)

    exams_page = ExamPage(page)
    exams_page.wait_for_exams_loaded()
    return exams_page


def test_exams_page_opens(page, exam_page):
    expect(page).to_have_url(EXAMS_URL)
    expect(exam_page.get_page_title()).to_have_text("Exams")


def test_exam_tabs_visible(exam_page):
    expect(exam_page.get_tabs()).to_have_count(3)
    expect(exam_page.get_current_tab()).to_be_visible()
    expect(exam_page.get_upcoming_tab()).to_be_visible()
    expect(exam_page.get_past_tab()).to_be_visible()


def test_current_tab_active_by_default(exam_page):
    expect(exam_page.get_active_tab()).to_have_count(1)
    expect(exam_page.get_active_tab()).to_contain_text("Current")


def test_switch_to_upcoming_tab(page, exam_page):
    exam_page.click_upcoming_tab()

    expect(page).to_have_url(EXAMS_URL + "?tab=upcoming")
    expect(exam_page.get_active_tab()).to_contain_text("Upcoming")


def test_switch_to_past_tab(page, exam_page):
    exam_page.click_past_tab()

    expect(page).to_have_url(EXAMS_URL + "?tab=past")
    expect(exam_page.get_active_tab()).to_contain_text("Past")


def test_switch_back_to_current_tab(page, exam_page):
    exam_page.click_past_tab()
    expect(exam_page.get_active_tab()).to_contain_text("Past")

    exam_page.click_current_tab()

    expect(page).to_have_url(EXAMS_URL)
    expect(exam_page.get_active_tab()).to_contain_text("Current")


def test_open_exams_directly_on_past_tab(page, exam_page):
    exam_page.open(tab="past")

    expect(page).to_have_url(EXAMS_URL + "?tab=past")
    expect(exam_page.get_active_tab()).to_contain_text("Past")


def test_tab_counts_are_numeric(exam_page):
    # The badge is display:none on wide viewports, so assert its text, not visibility.
    for tab in ["Current", "Upcoming", "Past"]:
        expect(exam_page.get_tab_count(tab)).to_have_text(re.compile(r"^\d+$"))


def test_past_tab_count_matches_card_count(exam_page):
    exam_page.click_past_tab()

    expected_count = exam_page.get_tab_count_value("Past")

    expect(exam_page.get_exam_cards()).to_have_count(expected_count)


def test_current_tab_empty_state(exam_page):
    if exam_page.get_tab_count_value("Current") == 0:
        expect(exam_page.get_empty_state()).to_be_visible()
        expect(exam_page.get_empty_message()).to_have_text("No exams to attempt")
    else:
        expect(exam_page.get_exam_cards().first).to_be_visible()


def test_upcoming_tab_empty_state(exam_page):
    exam_page.click_upcoming_tab()

    if exam_page.get_tab_count_value("Upcoming") == 0:
        expect(exam_page.get_empty_state()).to_be_visible()
        expect(exam_page.get_empty_message()).to_have_text("No upcoming exams")
    else:
        expect(exam_page.get_exam_cards().first).to_be_visible()


def test_exam_list_shows_no_content_when_the_api_fails(page):
    """The exam list is the only network call in this flow; the instructions
    page renders entirely from the list payload and the route query string.

    Blocking it leaves the page with neither exams nor an error or empty state,
    so this pins the current behaviour: a blank list body under the heading."""
    page.route("**/api/v3/exams/all", lambda route: route.abort())

    exams_page = ExamPage(page)
    page.goto(ExamPage.URL)

    expect(exams_page.get_page_title()).to_have_text("Exams")
    expect(exams_page.get_exam_cards()).to_have_count(0)
    expect(exams_page.get_empty_state()).to_have_count(0)


# ---------------------------------------------------------------------------
# API verification
#
# The exam list is the only call this screen makes, and every tab is filled
# from the same payload, so the tabs and the cards can be read back against it.
# ---------------------------------------------------------------------------

EXAMS_API = "**/api/v3/exams/all"

TABS = ["Current", "Upcoming", "Past"]


def open_exams_with_payload(page):
    with page.expect_response(EXAMS_API) as answer:
        page.goto(EXAMS_URL, wait_until="domcontentloaded")
    assert answer.value.status == 200, f"exams answered {answer.value.status}"

    exams_page = ExamPage(page)
    exams_page.wait_for_exams_loaded()
    return exams_page, answer.value.json()["exams"]


def exams_by_title(exams, fields):
    """The payload keyed by title, carrying only the fields being compared.

    Two exams on an account can share a title, and a card showing that title
    cannot then be traced back to one of them - unless both say the same thing
    about what is being checked, which is what a None here rules out."""
    keyed = {}
    for exam in exams:
        title = exam["title"].strip()
        wanted = tuple(exam[field] for field in fields)
        if title in keyed and keyed[title] != wanted:
            keyed[title] = None
        else:
            keyed.setdefault(title, wanted)
    return keyed


def listed_past_exams(exams_page, exams, fields):
    """The Past tab's titles, with the payload values each one stands for."""
    exams_page.click_past_tab()

    total = exams_page.get_tab_count_value("Past")
    if total == 0:
        pytest.skip("No past exams for this user")

    # The tab being left stays on screen until the new one is built, so the
    # grid is held at the count the tab claims before any of it is read.
    expect(exams_page.get_exam_cards()).to_have_count(total)

    keyed = exams_by_title(exams, fields)
    # Read card by card. The title class is used elsewhere on the screen too,
    # so collecting it in one go picks up more than the cards themselves.
    shown = [
        exams_page.get_exam_title(index).inner_text().strip()
        for index in range(total)
    ]

    for title in shown:
        assert title in keyed, f"{title!r} is listed but not in the exams payload"

    unclear = [title for title in shown if keyed[title] is None]
    if unclear:
        pytest.skip(
            f"{len(unclear)} listed exams share a title with an exam the payload "
            "describes differently, so no card can be matched to one"
        )

    return shown, keyed


def test_exam_tab_counts_add_up_to_the_exams_api(page):
    """Every exam the payload carries lands in exactly one of the three tabs."""
    exams_page, exams = open_exams_with_payload(page)

    counted = sum(exams_page.get_tab_count_value(name) for name in TABS)

    assert counted == len(exams)


def test_past_exam_cards_match_the_exams_api(page):
    exams_page, exams = open_exams_with_payload(page)
    shown, keyed = listed_past_exams(
        exams_page, exams, ("is_attended", "subscription_status")
    )

    # is_attended decides Review over Attempt, and the badge beside it. An exam
    # the account is not entitled to offers neither, so the three do not add up
    # to the number of cards on their own.
    attended = [title for title in shown if keyed[title][0]]
    attemptable = [
        title for title in shown if not keyed[title][0] and keyed[title][1]
    ]

    expect(exams_page.get_attempted_badges()).to_have_count(len(attended))
    expect(exams_page.get_review_buttons()).to_have_count(len(attended))
    expect(exams_page.get_attempt_buttons()).to_have_count(len(attemptable))


def test_past_exam_duration_and_marks_match_the_exams_api(page):
    exams_page, exams = open_exams_with_payload(page)
    shown, keyed = listed_past_exams(
        exams_page, exams, ("duration_int", "total_mark")
    )

    for index, title in enumerate(shown):
        duration, total_mark = keyed[title]
        meta = exams_page.get_exam_duration_and_marks(index).inner_text()

        # duration_int is seconds on the wire; the card shows whole minutes.
        assert f"{duration // 60} Minutes" in meta, (
            f"{meta!r} does not carry the duration"
        )
        assert str(total_mark) in meta, f"{meta!r} does not carry the marks"
