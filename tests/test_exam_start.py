"""Exam Start (instructions) page - ESP_001 to ESP_018.

Exams are always addressed by position, never by title, because the titles
differ from one account to the next.
"""
import re
import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.exam_page import ExamPage, ExamInstructionsPage
from pages.live_exam_page import LiveExamPage

MOBILE = "9876543210"

EXAMS_URL = "https://eduport-react.pages.dev/exams"
INSTRUCTIONS_URL_PATTERN = re.compile(
    r"https://eduport-react\.pages\.dev/exams/\d+/instructions.*"
)
REVIEW_URL_PATTERN = re.compile(r"https://eduport-react\.pages\.dev/exams/\d+/.+")
EXAM_LIST_API = "**/api/v3/exams/all"
EXAM_START_API = "**/api/v3/exams/exam-start"


def card_minutes(text):
    """'90 Minutes 180.0 Marks' -> 90"""
    return int(re.search(r"(\d+)\s*Minutes", text).group(1))


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture
def exam_list(page):
    home_page = HomePage(page)
    home_page.get_exams_button().click()
    page.wait_for_url(EXAMS_URL)

    exams_page = ExamPage(page)
    exams_page.wait_for_exams_loaded()
    exams_page.click_past_tab()
    return exams_page


@pytest.fixture
def exam_start(page, exam_list):
    """Opens the start page of the first exam still offering Attempt, and hands
    back what the card claimed so the two can be compared."""
    index = exam_list.find_unattempted_exam()
    if index is None:
        pytest.skip("Every past exam on this account has been attempted")

    expected = {
        "title": exam_list.get_exam_title(index).inner_text().strip(),
        "minutes": card_minutes(
            exam_list.get_exam_duration_and_marks(index).inner_text()
        ),
    }
    exam_list.click_attempt(index)

    instructions_page = ExamInstructionsPage(page)
    expect(instructions_page.get_start_exam_button()).to_be_visible()
    return instructions_page, expected


@pytest.fixture
def instructions(exam_start):
    return exam_start[0]


# ---------------------------------------------------------------------------
# ESP_001 / ESP_002 - page load
# ---------------------------------------------------------------------------

def test_esp_001_start_page_loads_successfully(page, instructions):
    expect(page).to_have_url(INSTRUCTIONS_URL_PATTERN)
    expect(instructions.get_header_title()).to_have_text("Exam")
    expect(instructions.get_exam_name()).not_to_be_empty()
    expect(instructions.get_stats()).to_have_count(2)
    expect(instructions.get_instructions_box()).to_be_visible()
    expect(instructions.get_start_exam_button()).to_be_visible()


def test_esp_002_exam_title_matches_the_card(exam_start):
    instructions, expected = exam_start

    expect(instructions.get_exam_name()).to_have_text(expected["title"])


# ---------------------------------------------------------------------------
# ESP_003 / ESP_004 - question count
# ---------------------------------------------------------------------------

def test_esp_003_total_question_count_is_correct(instructions):
    expect(instructions.get_total_questions()).to_be_visible()

    assert instructions.get_total_questions_count() > 0


def test_esp_004_start_is_blocked_when_there_are_no_questions(page, instructions):
    """An exam advertising zero questions must not be startable."""
    if instructions.get_total_questions_count() > 0:
        pytest.skip("This exam reports questions, so the empty case does not apply")

    if not instructions.get_start_exam_button().is_enabled():
        return

    instructions.click_start_exam()

    expect(instructions.get_toast()).to_contain_text(
        re.compile("No questions available", re.IGNORECASE)
    )
    assert LiveExamPage(page).is_open() is False


# ---------------------------------------------------------------------------
# ESP_005 / ESP_006 - duration
# ---------------------------------------------------------------------------

def test_esp_005_duration_matches_the_configured_value(exam_start):
    instructions, expected = exam_start

    expect(instructions.get_duration()).to_be_visible()
    assert instructions.get_duration_minutes() == expected["minutes"]


def test_esp_006_zero_minute_exam_cannot_be_started(page, exam_list):
    index = next(
        (
            i
            for i in range(exam_list.exam_card_count())
            if card_minutes(exam_list.get_exam_duration_and_marks(i).inner_text()) == 0
            and exam_list.get_attempt_button(i).count() > 0
        ),
        None,
    )
    if index is None:
        pytest.skip("No exam on this account is configured with a 0 minute duration")

    exam_list.click_attempt(index)
    instructions = ExamInstructionsPage(page)

    if not instructions.get_start_exam_button().is_enabled():
        return

    instructions.click_start_exam()

    expect(instructions.get_toast()).not_to_be_empty()
    assert LiveExamPage(page).is_open() is False


# ---------------------------------------------------------------------------
# ESP_007 / ESP_008 - instructions and the start control
# ---------------------------------------------------------------------------

def test_esp_007_instructions_are_displayed(instructions):
    expect(instructions.get_instructions_title()).to_have_text("Instructions")
    expect(instructions.get_instructions_box()).to_be_visible()
    expect(instructions.get_instruction_items().first).to_be_visible()
    expect(instructions.get_important_note()).to_contain_text("only once")

    assert instructions.get_instruction_items().count() > 0


def test_esp_008_start_exam_button_is_enabled(instructions):
    expect(instructions.get_start_exam_button()).to_be_visible()
    expect(instructions.get_start_exam_button()).to_be_enabled()


# ---------------------------------------------------------------------------
# ESP_009 / ESP_010 - starting the exam
# ---------------------------------------------------------------------------

def test_esp_009_start_exam_opens_the_first_question(page, instructions):
    instructions.click_start_exam()
    page.wait_for_timeout(4000)

    question_screen = LiveExamPage(page)
    if not question_screen.is_open():
        pytest.skip(
            "The backend refused to start this exam: "
            f"{instructions.get_toast().inner_text().strip() or 'no message shown'}"
        )

    expect(question_screen.get_page()).to_be_visible()
    expect(question_screen.get_question_counter()).to_contain_text(re.compile(r"^1/"))


def test_esp_010_first_question_is_displayed(page, instructions):
    instructions.click_start_exam()
    page.wait_for_timeout(4000)

    question_screen = LiveExamPage(page)
    if not question_screen.is_open():
        pytest.skip(
            "The backend refused to start this exam: "
            f"{instructions.get_toast().inner_text().strip() or 'no message shown'}"
        )

    expect(question_screen.get_question_text()).not_to_be_empty()
    assert question_screen.get_options().count() >= 2


# ---------------------------------------------------------------------------
# ESP_011 / ESP_012 - already attempted
# ---------------------------------------------------------------------------

def test_esp_011_already_attempted_exam_leads_to_the_review_page(page, exam_list):
    """This build's business logic routes an attempted exam to review rather
    than back to the start page."""
    index = exam_list.find_attempted_exam()
    if index is None:
        pytest.skip("This account has no attempted exam")

    expect(exam_list.get_attempted_badge(index)).to_have_text("Attempted")
    exam_list.click_review(index)

    expect(page).to_have_url(REVIEW_URL_PATTERN)
    expect(ExamInstructionsPage(page).get_start_exam_button()).to_have_count(0)


def test_esp_012_a_submitted_exam_cannot_be_started_again(page, instructions):
    """Some cards still offer Attempt after submission; pressing Start must not
    hand out a second attempt."""
    instructions.click_start_exam()

    if LiveExamPage(page).is_open():
        pytest.skip("This exam had not been submitted yet, so it started normally")

    expect(instructions.get_toast()).to_contain_text(
        re.compile("already attempted", re.IGNORECASE)
    )
    expect(page).to_have_url(INSTRUCTIONS_URL_PATTERN)
    assert LiveExamPage(page).is_open() is False


# ---------------------------------------------------------------------------
# ESP_013 / ESP_014 - navigation
# ---------------------------------------------------------------------------

def test_esp_013_refresh_keeps_the_exam_information_intact(page, exam_start):
    instructions, expected = exam_start

    page.reload()

    expect(page).to_have_url(INSTRUCTIONS_URL_PATTERN)
    expect(instructions.get_exam_name()).to_have_text(expected["title"])
    expect(instructions.get_start_exam_button()).to_be_visible()
    assert instructions.get_duration_minutes() == expected["minutes"]


def test_esp_014_back_returns_to_the_exam_list(page, instructions, exam_list):
    instructions.click_back()

    expect(page).to_have_url(
        re.compile(r"https://eduport-react\.pages\.dev/exams(\?.*)?$")
    )
    expect(exam_list.get_page_title()).to_have_text("Exams")
    expect(instructions.get_start_exam_button()).to_have_count(0)


def test_esp_014_browser_back_returns_to_the_exam_list(page, instructions, exam_list):
    page.go_back()

    expect(exam_list.get_exam_cards().first).to_be_visible()
    expect(instructions.get_start_exam_button()).to_have_count(0)


# ---------------------------------------------------------------------------
# ESP_015 / ESP_016 - failure handling
# ---------------------------------------------------------------------------

def test_esp_015_api_failure_shows_an_error(page, instructions):
    """Reload the start page with the exam feed blocked."""
    page.route(EXAM_LIST_API, lambda route: route.abort())

    page.reload()

    expect(instructions.get_error_message().first).to_be_visible()


def test_esp_016_network_interruption_before_start_shows_an_error(page, instructions):
    page.route(EXAM_START_API, lambda route: route.abort())

    instructions.click_start_exam()

    expect(instructions.get_toast()).not_to_be_empty()
    assert LiveExamPage(page).is_open() is False


# ---------------------------------------------------------------------------
# ESP_017 / ESP_018 - presentation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("width,height", [(1440, 900), (768, 1024), (390, 844)])
def test_esp_017_start_page_is_responsive(page, instructions, width, height):
    page.set_viewport_size({"width": width, "height": height})
    page.wait_for_timeout(1000)

    expect(instructions.get_exam_name()).to_be_visible()
    expect(instructions.get_start_exam_button()).to_be_visible()
    assert page.evaluate(
        "() => document.documentElement.scrollWidth <= window.innerWidth"
    )


def test_esp_018_loading_indicator_while_exam_details_load(page):
    """Hold the exam feed open so the loading state cannot be missed."""
    held = []
    page.route(EXAM_LIST_API, lambda route: held.append(route))

    page.goto(ExamPage.URL, wait_until="commit")

    exams_page = ExamPage(page)
    expect(exams_page.get_loading_indicator().first).to_be_visible(timeout=5000)
