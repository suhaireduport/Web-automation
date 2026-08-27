"""Past Exams list - PE_001 to PE_008.

Exams are always addressed by position, never by title, because the titles
differ from one account to the next.
"""
import re
import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.exam_page import ExamPage, ExamInstructionsPage

MOBILE = "9876543210"

EXAMS_URL = "https://eduport-react.pages.dev/exams"
INSTRUCTIONS_URL_PATTERN = re.compile(
    r"https://eduport-react\.pages\.dev/exams/\d+/instructions.*"
)
REVIEW_URL_PATTERN = re.compile(r"https://eduport-react\.pages\.dev/exams/\d+/.+")


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


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

def test_past_exam_cards_visible(past_exams):
    if past_exams.get_tab_count_value("Past") == 0:
        pytest.skip("No past exams for this user")

    expect(past_exams.get_exam_grid()).to_be_visible()
    expect(past_exams.get_exam_cards().first).to_be_visible()


def test_past_exam_card_details(past_exams):
    if past_exams.get_tab_count_value("Past") == 0:
        pytest.skip("No past exams for this user")

    expect(past_exams.get_exam_subject(0)).to_be_visible()
    expect(past_exams.get_exam_title(0)).not_to_be_empty()
    expect(past_exams.get_exam_schedule(0)).to_be_visible()
    expect(past_exams.get_exam_duration_and_marks(0)).to_contain_text("Minutes")
    expect(past_exams.get_exam_duration_and_marks(0)).to_contain_text("Marks")


# ---------------------------------------------------------------------------
# PE_001 / PE_002 - unattempted exams
# ---------------------------------------------------------------------------

def test_pe_001_attempt_button_shown_for_an_unattempted_exam(past_exams):
    index = past_exams.find_unattempted_exam()
    if index is None:
        pytest.skip("Every past exam on this account has been attempted")

    expect(past_exams.get_attempt_button(index)).to_be_visible()
    expect(past_exams.get_attempt_button(index)).to_be_enabled()
    expect(past_exams.get_attempted_badge(index)).to_have_count(0)


def test_pe_001_every_unattempted_card_offers_an_enabled_attempt(past_exams):
    if past_exams.exam_card_count() == 0:
        pytest.skip("No past exams for this user")

    attempt_buttons = past_exams.get_attempt_buttons()
    if attempt_buttons.count() == 0:
        pytest.skip("Every past exam on this account has been attempted")

    for i in range(attempt_buttons.count()):
        expect(attempt_buttons.nth(i)).to_be_enabled()


def test_pe_002_attempt_opens_the_exam_instructions_page(page, past_exams):
    index = past_exams.find_unattempted_exam()
    if index is None:
        pytest.skip("Every past exam on this account has been attempted")

    expected_title = past_exams.get_exam_title(index).inner_text().strip()
    past_exams.click_attempt(index)

    expect(page).to_have_url(INSTRUCTIONS_URL_PATTERN)

    instructions_page = ExamInstructionsPage(page)
    expect(instructions_page.get_header_title()).to_have_text("Exam")
    expect(instructions_page.get_exam_name()).to_have_text(expected_title)


# ---------------------------------------------------------------------------
# PE_003 / PE_004 / PE_005 - attempted exams
# ---------------------------------------------------------------------------

def test_pe_003_review_button_replaces_attempt_for_an_attempted_exam(past_exams):
    index = past_exams.find_attempted_exam()
    if index is None:
        pytest.skip("This account has no attempted exam")

    expect(past_exams.get_review_button(index)).to_be_visible()
    expect(past_exams.get_review_button(index)).to_be_enabled()
    expect(past_exams.get_attempt_button(index)).to_have_count(0)


def test_pe_004_attempted_tag_shown_alongside_review(past_exams):
    index = past_exams.find_attempted_exam()
    if index is None:
        pytest.skip("This account has no attempted exam")

    expect(past_exams.get_attempted_badge(index)).to_be_visible()
    expect(past_exams.get_attempted_badge(index)).to_have_text("Attempted")
    expect(past_exams.get_review_button(index)).to_be_visible()


def test_pe_004_every_attempted_card_carries_the_tag(past_exams):
    if past_exams.exam_card_count() == 0:
        pytest.skip("No past exams for this user")

    review_buttons = past_exams.get_review_buttons()
    if review_buttons.count() == 0:
        pytest.skip("This account has no attempted exam")

    expect(past_exams.get_attempted_badges()).to_have_count(review_buttons.count())


def test_pe_005_review_opens_the_exam_review_page(page, past_exams):
    index = past_exams.find_attempted_exam()
    if index is None:
        pytest.skip("This account has no attempted exam")

    past_exams.click_review(index)

    expect(page).to_have_url(REVIEW_URL_PATTERN)
    expect(past_exams.get_exam_cards()).to_have_count(0)


# ---------------------------------------------------------------------------
# PE_006 / PE_007 / PE_008 - access by entitlement
# ---------------------------------------------------------------------------

def test_pe_006_trial_user_without_permission_sees_a_locked_exam(past_exams):
    pytest.skip(
        "Needs a trial-course account without exam permission. This build also "
        "renders no lock element on .ex-card - only Attempt, Review and the "
        "Attempted badge exist - so the locked state has no selector yet."
    )


def test_pe_007_locked_exam_cannot_be_opened(past_exams):
    pytest.skip(
        "Blocked by PE_006: no locked exam is reachable with these credentials."
    )


def test_pe_008_permitted_user_gets_attempt_or_review_on_every_exam(past_exams):
    """The account under test holds the entitlement, so no card may be locked
    and every one must offer the action its status calls for."""
    total = past_exams.exam_card_count()
    if total == 0:
        pytest.skip("No past exams for this user")

    attempt = past_exams.get_attempt_buttons().count()
    review = past_exams.get_review_buttons().count()

    assert attempt + review == total

    for i in range(total):
        expect(past_exams.get_exam_card(i)).not_to_have_class(re.compile("locked"))
