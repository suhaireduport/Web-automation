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
