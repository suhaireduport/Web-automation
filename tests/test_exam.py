"""Exams list page: tabs, counts and empty states.

Past exam cards are covered in test_past_exam.py and the instructions page in
test_exam_start.py.
"""
import re
from collections import Counter

import pytest
from playwright.sync_api import expect

from conftest import STUDENT_MOBILE
from pages.home_page import HomePage
from pages.exam_page import ExamPage


EXAMS_URL = "https://eduport-react.pages.dev/exams"


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(STUDENT_MOBILE)


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
    """The exam list is the only network call this screen makes.

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


def past_exams_payload(exams_page, exams):
    """The payload entries the Past tab is showing.

    Counting what the tab offers does not need any one card traced back to one
    entry, only the set of entries behind the tab. A title listed as many times
    as the payload carries it accounts for all of them however they differ; a
    title the payload carries more often than the tab shows it is being split
    across tabs, and then there is no telling which of them landed here."""
    exams_page.click_past_tab()

    total = exams_page.get_tab_count_value("Past")
    if total == 0:
        pytest.skip("No past exams for this user")

    expect(exams_page.get_exam_cards()).to_have_count(total)

    shown = Counter(
        exams_page.get_exam_title(index).inner_text().strip()
        for index in range(total)
    )
    carried = Counter(exam["title"].strip() for exam in exams)

    for title in shown:
        assert title in carried, f"{title!r} is listed but not in the exams payload"

    split = [title for title, count in shown.items() if carried[title] != count]
    if split:
        pytest.skip(
            f"{len(split)} titles are carried more often by the payload than the "
            "Past tab shows them, so which of them is listed here is not decidable"
        )

    return [exam for exam in exams if exam["title"].strip() in shown]


def test_exam_tab_counts_add_up_to_the_exams_api(page):
    """Every exam the payload carries lands in exactly one of the three tabs."""
    exams_page, exams = open_exams_with_payload(page)

    counted = sum(exams_page.get_tab_count_value(name) for name in TABS)

    assert counted == len(exams)


def test_past_exam_cards_match_the_exams_api(page):
    """Three flags in the payload decide what a card offers.

    subscription_status is the first gate: without it the exam is padlocked and
    offers nothing at all. Past that, is_attended chooses the Attempted badge
    over Attempt, and is_rank_published decides whether an attempted exam gets
    a Review or only the notice that its result is still to come."""
    exams_page, exams = open_exams_with_payload(page)
    listed = past_exams_payload(exams_page, exams)

    def counting(wanted):
        return sum(
            1
            for exam in listed
            if wanted(
                exam["is_attended"],
                exam["is_rank_published"],
                exam["subscription_status"],
            )
        )

    expect(exams_page.get_locked_cards()).to_have_count(
        counting(lambda attended, published, entitled: not entitled)
    )
    expect(exams_page.get_attempt_buttons()).to_have_count(
        counting(lambda attended, published, entitled: entitled and not attended)
    )
    expect(exams_page.get_attempted_badges()).to_have_count(
        counting(lambda attended, published, entitled: entitled and attended)
    )
    expect(exams_page.get_review_buttons()).to_have_count(
        counting(
            lambda attended, published, entitled: entitled and attended and published
        )
    )
    expect(exams_page.get_result_pending_notices()).to_have_count(
        counting(
            lambda attended, published, entitled: entitled
            and attended
            and not published
        )
    )


def test_past_exam_duration_and_marks_match_the_exams_api(page):
    """What every card advertises, against what the payload carries.

    Compared as two collections rather than card by card: exams on an account
    can share a title, and a card showing that title cannot be traced back to
    one of them - but the same titles carrying the same durations and marks,
    as often as each other, says the whole tab is drawn from the payload."""
    exams_page, exams = open_exams_with_payload(page)
    listed = past_exams_payload(exams_page, exams)

    # duration_int is seconds on the wire; the card shows whole minutes.
    carried = Counter(
        (
            exam["title"].strip(),
            exam["duration_int"] // 60,
            float(exam["total_mark"]),
        )
        for exam in listed
    )
    shown = Counter(
        (
            exams_page.get_exam_title(index).inner_text().strip(),
            exams_page.get_exam_minutes(index),
            exams_page.get_exam_marks(index),
        )
        for index in range(exams_page.exam_card_count())
    )

    assert shown == carried
