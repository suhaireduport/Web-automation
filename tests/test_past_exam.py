"""Past Exams list: what each card offers for the state its exam is in.

Exams are always addressed by position, never by title, because the titles
differ from one account to the next.

A past exam card can be in one of four states, and the whole file turns on
telling them apart:

* not attempted, and the account is entitled to it - Attempt
* attempted and the result published - Review, beside the Attempted badge
* attempted and the result not published yet - the Attempted badge and a
  "result will be published soon" notice, with no action to take
* not entitled - a padlock, and no action at all

The instructions page each Attempt opens is covered in test_exam_start.py.
"""
import re
import pytest
from playwright.sync_api import expect

from conftest import STUDENT_MOBILE
from pages.home_page import HomePage
from pages.exam_page import ExamPage, ExamInstructionsPage, ExamResultPage


EXAMS_URL = ExamPage.URL
INSTRUCTIONS_URL_PATTERN = re.compile(
    r"https://eduport-react\.pages\.dev/exams/\d+/instructions.*"
)

NO_PAST_EXAMS = "No past exams for this user"
NONE_UNATTEMPTED = "Every past exam on this account has been attempted"
NONE_ATTEMPTED = "This account has no attempted exam"
NONE_REVIEWABLE = "No attempted exam on this account has its result published"
NONE_LOCKED = "This account is entitled to every past exam, so none is locked"


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(STUDENT_MOBILE)


@pytest.fixture
def past_exams(page):
    home_page = HomePage(page)
    home_page.get_exams_button().click()
    page.wait_for_url(EXAMS_URL)

    exams_page = ExamPage(page)
    exams_page.wait_for_exams_loaded()
    exams_page.click_past_tab()
    return exams_page


# ---------------------------------------------------------------------------
# Card content
# ---------------------------------------------------------------------------

def test_past_tab_lists_exam_cards(past_exams):
    if past_exams.get_tab_count_value("Past") == 0:
        pytest.skip(NO_PAST_EXAMS)

    expect(past_exams.get_exam_grid()).to_be_visible()
    expect(past_exams.get_exam_cards().first).to_be_visible()


def test_past_exam_card_shows_the_subject_title_and_schedule(past_exams):
    if past_exams.get_tab_count_value("Past") == 0:
        pytest.skip(NO_PAST_EXAMS)

    expect(past_exams.get_exam_subject(0)).to_be_visible()
    expect(past_exams.get_exam_title(0)).not_to_be_empty()
    expect(past_exams.get_exam_schedule(0)).to_be_visible()
    expect(past_exams.get_exam_duration_and_marks(0)).to_contain_text("Minutes")
    expect(past_exams.get_exam_duration_and_marks(0)).to_contain_text("Marks")


# ---------------------------------------------------------------------------
# Exams that have not been attempted
# ---------------------------------------------------------------------------

def test_unattempted_exam_offers_attempt_and_no_attempted_badge(past_exams):
    index = past_exams.find_unattempted_exam()
    if index is None:
        pytest.skip(NONE_UNATTEMPTED)

    expect(past_exams.get_attempt_button(index)).to_be_visible()
    expect(past_exams.get_attempt_button(index)).to_be_enabled()
    expect(past_exams.get_attempted_badge(index)).to_have_count(0)


def test_every_unattempted_card_offers_an_enabled_attempt(past_exams):
    if past_exams.exam_card_count() == 0:
        pytest.skip(NO_PAST_EXAMS)

    attempt_buttons = past_exams.get_attempt_buttons()
    if attempt_buttons.count() == 0:
        pytest.skip(NONE_UNATTEMPTED)

    for i in range(attempt_buttons.count()):
        expect(attempt_buttons.nth(i)).to_be_enabled()


def test_attempt_opens_the_exam_instructions_page(page, past_exams):
    index = past_exams.find_unattempted_exam()
    if index is None:
        pytest.skip(NONE_UNATTEMPTED)

    expected_title = past_exams.get_exam_title(index).inner_text().strip()
    past_exams.click_attempt(index)

    expect(page).to_have_url(INSTRUCTIONS_URL_PATTERN)

    instructions_page = ExamInstructionsPage(page)
    expect(instructions_page.get_header_title()).to_have_text("Exam")
    expect(instructions_page.get_exam_name()).to_have_text(expected_title)


# ---------------------------------------------------------------------------
# Exams that have been attempted
# ---------------------------------------------------------------------------

def test_reviewable_exam_offers_review_instead_of_attempt(past_exams):
    index = past_exams.find_reviewable_exam()
    if index is None:
        pytest.skip(NONE_REVIEWABLE)

    expect(past_exams.get_review_button(index)).to_be_visible()
    expect(past_exams.get_review_button(index)).to_be_enabled()
    expect(past_exams.get_attempt_button(index)).to_have_count(0)


def test_attempted_badge_is_shown_alongside_review(past_exams):
    index = past_exams.find_reviewable_exam()
    if index is None:
        pytest.skip(NONE_REVIEWABLE)

    expect(past_exams.get_attempted_badge(index)).to_be_visible()
    expect(past_exams.get_attempted_badge(index)).to_have_text("Attempted")
    expect(past_exams.get_review_button(index)).to_be_visible()


def test_every_attempted_card_carries_the_attempted_badge(past_exams):
    """Review is offered on a subset of the attempted exams, never beyond it:
    an exam whose result is still to come is attempted but not reviewable."""
    if past_exams.exam_card_count() == 0:
        pytest.skip(NO_PAST_EXAMS)

    attempted = past_exams.find_attempted_exams()
    if not attempted:
        pytest.skip(NONE_ATTEMPTED)

    assert set(past_exams.find_reviewable_exams()) <= set(attempted)

    for index in attempted:
        expect(past_exams.get_attempted_badge(index)).to_have_text("Attempted")
        expect(past_exams.get_attempt_button(index)).to_have_count(0)


def test_attempted_exam_awaiting_its_result_offers_no_review(past_exams):
    """The card says the result is coming rather than handing out a Review that
    would open an empty one."""
    index = next(
        (i for i in past_exams.find_attempted_exams() if past_exams.is_result_pending(i)),
        None,
    )
    if index is None:
        pytest.skip("Every attempted exam on this account has its result published")

    expect(past_exams.get_result_pending_notice(index)).to_be_visible()
    expect(past_exams.get_result_pending_notice(index)).to_contain_text(
        "Exam result will be published soon"
    )
    expect(past_exams.get_attempted_badge(index)).to_be_visible()
    expect(past_exams.get_review_button(index)).to_have_count(0)
    expect(past_exams.get_attempt_button(index)).to_have_count(0)


def test_review_opens_the_exam_result_page(page, past_exams):
    index = past_exams.find_reviewable_exam()
    if index is None:
        pytest.skip(NONE_REVIEWABLE)

    expected_title = past_exams.get_exam_title(index).inner_text().strip()
    past_exams.click_review(index)

    expect(page).to_have_url(ExamResultPage.URL_PATTERN)

    result_page = ExamResultPage(page)
    expect(result_page.get_header_title()).to_have_text("Exam result")
    expect(result_page.get_exam_name()).to_have_text(expected_title)
    expect(past_exams.get_exam_cards()).to_have_count(0)


# ---------------------------------------------------------------------------
# Access by entitlement
# ---------------------------------------------------------------------------

def test_exam_without_entitlement_is_locked(past_exams):
    index = past_exams.find_locked_exam()
    if index is None:
        pytest.skip(NONE_LOCKED)

    expect(past_exams.get_exam_card(index)).to_have_class(re.compile("ex-card-locked"))
    expect(past_exams.get_lock_badge(index)).to_be_visible()
    expect(past_exams.get_attempt_button(index)).to_have_count(0)
    expect(past_exams.get_review_button(index)).to_have_count(0)


def test_locked_exam_cannot_be_opened(page, past_exams):
    index = past_exams.find_locked_exam()
    if index is None:
        pytest.skip(NONE_LOCKED)

    past_exams.get_exam_card(index).click()
    page.wait_for_timeout(1500)

    expect(page).not_to_have_url(INSTRUCTIONS_URL_PATTERN)
    expect(past_exams.get_exam_grid()).to_be_visible()
    expect(ExamInstructionsPage(page).get_start_exam_button()).to_have_count(0)


def test_every_card_offers_the_action_its_state_calls_for(past_exams):
    """Each card lands in exactly one of the four states, and the four together
    account for the whole list."""
    total = past_exams.exam_card_count()
    if total == 0:
        pytest.skip(NO_PAST_EXAMS)

    attemptable = set(past_exams.find_unattempted_exams())
    reviewable = set(past_exams.find_reviewable_exams())
    pending = {i for i in range(total) if past_exams.is_result_pending(i)}
    locked = set(past_exams.find_locked_exams())

    states = [attemptable, reviewable, pending, locked]
    for index in range(total):
        matched = [state for state in states if index in state]
        assert len(matched) == 1, (
            f"card {index} ({past_exams.get_exam_title(index).inner_text().strip()!r}) "
            f"is in {len(matched)} states, not exactly one"
        )

    assert len(attemptable) + len(reviewable) + len(pending) + len(locked) == total
