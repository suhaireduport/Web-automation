"""Live Exam: subscription access, the question page, bookmarks, the timer and
question navigation.

A live exam is one whose window covers now, which is exactly what the Current
tab lists. Exams are addressed by position, never by title.

Two facts about the backend shape this file:

* Starting an exam consumes it. A second exam-start for the same exam comes
  back 406, and there is no resume - opening /exams/<id>/take directly bounces
  to the instructions page. The question page tests therefore share a single
  attempt for the whole run through the session scoped live_exam fixture,
  instead of burning one exam per test.
* No account has an exam it is not entitled to, so the restriction tests drive
  the subscription_status flag the exam feed already sends, through the same
  page.route interception the rest of the suite uses for failure injection.
"""
import datetime
import re

import pytest
from playwright.sync_api import expect

from pages.exam_page import ExamPage, ExamInstructionsPage
from pages.live_exam_page import LiveExamPage

# This account still holds unattempted exams; 9876543210 has none left.
MOBILE = "8893963137"

EXAMS_URL = "https://eduport-react.pages.dev/exams"
EXAM_LIST_API = "**/api/v3/exams/all"
INSTRUCTIONS_URL_PATTERN = re.compile(
    r"https://eduport-react\.pages\.dev/exams/\d+/instructions.*"
)
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def card_minutes(text):
    """'90 Minutes 180.0 Marks' -> 90"""
    return int(re.search(r"(\d+)\s*Minutes", text).group(1))


def make_exams_live(page, subscribed=True, positions=None):
    """Rewrite the exam feed so the chosen exams are running right now.

    Nothing on the account is naturally live, and an exam's window is the only
    thing that decides which tab it lands in. positions maps a position in the
    feed to the subscription_status it should be served with; the default moves
    every exam into the Current tab."""
    now = datetime.datetime.now()
    from_time = (now - datetime.timedelta(hours=1)).strftime(TIME_FORMAT)
    to_time = (now + datetime.timedelta(hours=3)).strftime(TIME_FORMAT)

    def handler(route):
        response = route.fetch()
        body = response.json()
        wanted = positions
        if wanted is None:
            wanted = {index: subscribed for index in range(len(body["exams"]))}
        for index, is_subscribed in wanted.items():
            exam = body["exams"][index]
            exam["from_time"] = from_time
            exam["to_time"] = to_time
            exam["subscription_status"] = is_subscribed
        route.fulfill(response=response, json=body)

    page.route(EXAM_LIST_API, handler)


def open_live_exams(page):
    """The Current tab, which is where a running exam is listed."""
    exams_page = ExamPage(page)
    page.goto(EXAMS_URL)
    exams_page.wait_for_exams_loaded()
    return exams_page


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


# ---------------------------------------------------------------------------
# Scenario 1: a subscription exam without a subscription
# ---------------------------------------------------------------------------

@pytest.fixture
def locked_live_exams(page):
    """One live exam the account may not attend, and one it may.

    The list puts entitled exams first and locked ones last, so the locked card
    is found by its lock rather than by a fixed position."""
    make_exams_live(page, positions={0: False, 1: True})
    return open_live_exams(page)


def test_live_exam_without_a_subscription_is_locked(locked_live_exams):
    index = locked_live_exams.find_locked_exam()
    assert index is not None, "the unsubscribed exam was not listed at all"

    expect(locked_live_exams.get_exam_card(index)).to_have_class(
        re.compile("ex-card-locked")
    )
    expect(locked_live_exams.get_lock_badge(index)).to_be_visible()


def test_live_exam_without_a_subscription_offers_no_attempt(locked_live_exams):
    index = locked_live_exams.find_locked_exam()
    assert index is not None, "the unsubscribed exam was not listed at all"

    expect(locked_live_exams.get_attempt_button(index)).to_have_count(0)
    expect(locked_live_exams.get_review_button(index)).to_have_count(0)


def test_live_exam_without_a_subscription_cannot_be_opened(page, locked_live_exams):
    index = locked_live_exams.find_locked_exam()
    assert index is not None, "the unsubscribed exam was not listed at all"

    locked_live_exams.get_exam_card(index).click()
    page.wait_for_timeout(1500)

    expect(page).not_to_have_url(INSTRUCTIONS_URL_PATTERN)
    expect(locked_live_exams.get_confirm_modal()).to_have_count(0)
    expect(locked_live_exams.get_exam_grid()).to_be_visible()
    expect(ExamInstructionsPage(page).get_start_exam_button()).to_have_count(0)


def test_only_the_unsubscribed_live_exam_is_locked(locked_live_exams):
    """The entitled exam beside it keeps its Attempt button."""
    expect(locked_live_exams.get_locked_cards()).to_have_count(1)

    entitled = locked_live_exams.find_unattempted_exam()
    assert entitled is not None
    expect(locked_live_exams.get_attempt_button(entitled)).to_be_enabled()
    assert locked_live_exams.is_exam_locked(entitled) is False


# ---------------------------------------------------------------------------
# Scenarios 2, 3 and 4: an exam the account is entitled to
#
# The feed carries one entitlement flag per exam and no separate "free" marker,
# so a free exam and a paid exam the student has bought are indistinguishable
# to the client: both arrive with subscription_status true. All three scenarios
# are therefore driven through that flag.
# ---------------------------------------------------------------------------

ENTITLED_SCENARIOS = [
    "subscription exam, subscription held",
    "free exam, no subscription",
    "free exam, subscription held",
]


@pytest.fixture
def entitled_live_exams(page):
    make_exams_live(page, subscribed=True)
    return open_live_exams(page)


@pytest.mark.parametrize("scenario", ENTITLED_SCENARIOS)
def test_entitled_live_exam_can_be_opened(entitled_live_exams, scenario):
    index = entitled_live_exams.find_unattempted_exam()
    assert index is not None

    expect(entitled_live_exams.get_locked_cards()).to_have_count(0)
    expect(entitled_live_exams.get_attempt_button(index)).to_be_visible()
    expect(entitled_live_exams.get_attempt_button(index)).to_be_enabled()


@pytest.mark.parametrize("scenario", ENTITLED_SCENARIOS)
def test_entitled_live_exam_shows_the_instructions_page(page, entitled_live_exams, scenario):
    index = entitled_live_exams.find_unattempted_exam()
    entitled_live_exams.click_attempt(index)
    entitled_live_exams.confirm_start()

    expect(page).to_have_url(INSTRUCTIONS_URL_PATTERN)

    instructions_page = ExamInstructionsPage(page)
    expect(instructions_page.get_header_title()).to_have_text("Exam")
    expect(instructions_page.get_exam_name()).not_to_be_empty()
    expect(instructions_page.get_instructions_box()).to_be_visible()
    expect(instructions_page.get_instruction_items().first).to_be_visible()
    expect(instructions_page.get_start_exam_button()).to_be_enabled()


def test_live_exam_warns_before_opening_the_instructions(entitled_live_exams):
    """Only live exams ask first; from the Past tab Attempt goes straight
    through to the instructions page."""
    index = entitled_live_exams.find_unattempted_exam()
    entitled_live_exams.click_attempt(index)

    expect(entitled_live_exams.get_confirm_modal()).to_be_visible()
    expect(entitled_live_exams.get_confirm_title()).to_have_text(
        "Important Announcement!"
    )
    expect(entitled_live_exams.get_confirm_body()).to_contain_text("reattempt")
    expect(entitled_live_exams.get_confirm_start_button()).to_be_enabled()
    expect(entitled_live_exams.get_confirm_cancel_button()).to_be_enabled()


def test_cancelling_the_warning_keeps_the_exam_unstarted(page, entitled_live_exams):
    index = entitled_live_exams.find_unattempted_exam()
    entitled_live_exams.click_attempt(index)
    expect(entitled_live_exams.get_confirm_modal()).to_be_visible()

    entitled_live_exams.cancel_start()

    expect(entitled_live_exams.get_confirm_modal()).to_have_count(0)
    expect(page).to_have_url(re.compile(r"https://eduport-react\.pages\.dev/exams(\?.*)?$"))
    expect(entitled_live_exams.get_attempt_button(index)).to_be_enabled()


# ---------------------------------------------------------------------------
# The shared attempt
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _live_exam_state():
    """Holds the one started attempt, or the reason there is not one."""
    return {}


@pytest.fixture(scope="session")
def live_exam(login_session, _live_exam_state):
    """Start one live exam for the whole run and hand back its question page."""
    if "reason" in _live_exam_state:
        pytest.skip(_live_exam_state["reason"])
    if "player" in _live_exam_state:
        return _live_exam_state["player"]

    page = login_session(MOBILE)
    make_exams_live(page, subscribed=True)
    exams_page = open_live_exams(page)

    # The attempt has to outlive every test in the run, and it dies when its
    # own clock runs out, so try the roomiest exam first. Each candidate is
    # still tried in turn, because a card can offer Attempt and be refused.
    candidates = sorted(
        (
            (
                card_minutes(exams_page.get_exam_duration_and_marks(index).inner_text()),
                index,
            )
            for index in range(exams_page.exam_card_count())
            if exams_page.get_attempt_button(index).count() > 0
        ),
        reverse=True,
    )

    refusals = []
    for minutes, index in candidates:
        exams_page.click_attempt(index)
        exams_page.confirm_start()
        ExamInstructionsPage(page).click_start_exam()
        page.wait_for_timeout(5000)

        player = LiveExamPage(page)
        if player.is_open():
            player.wait_for_question()
            _live_exam_state["player"] = player
            return player

        message = page.locator("[data-rht-toaster]").inner_text().strip()
        refusals.append(f"[{index}] {minutes}min: {message or 'no message'}")
        page.goto(EXAMS_URL)
        exams_page.wait_for_exams_loaded()

    _live_exam_state["reason"] = (
        "No live exam could be started on " + MOBILE + ". Every exam offering "
        "Attempt was refused: " + "; ".join(refusals or ["none offered Attempt"])
    )
    pytest.skip(_live_exam_state["reason"])


@pytest.fixture
def question_page(live_exam):
    """Each test starts from question 1 so the order they run in does not
    matter. Nothing here may leave the player: navigating away ends the attempt
    and there is no way back into it."""
    live_exam.go_to_question(1)
    live_exam.page.wait_for_timeout(1200)
    return live_exam


def test_starting_a_live_exam_opens_the_question_page(live_exam):
    expect(live_exam.page).to_have_url(LiveExamPage.URL_PATTERN)
    expect(live_exam.get_page()).to_be_visible()
    expect(live_exam.get_question_text()).not_to_be_empty()


# ---------------------------------------------------------------------------
# Scenario 5: question page validation
# ---------------------------------------------------------------------------

def test_question_page_shows_the_question(question_page):
    expect(question_page.get_question_text()).to_be_visible()
    expect(question_page.get_question_text()).not_to_be_empty()


def test_question_page_shows_the_question_count(question_page):
    expect(question_page.get_question_counter()).to_be_visible()
    expect(question_page.get_question_counter()).to_have_text(re.compile(r"^\d+/\d+$"))

    current, total = question_page.get_counter_numbers()
    assert current == 1
    assert total > 0


def test_question_page_shows_answer_options(question_page):
    expect(question_page.get_options().first).to_be_visible()
    expect(question_page.get_choose_label()).to_be_visible()

    assert question_page.get_options().count() >= 2
    assert question_page.get_option_letters().count() == question_page.get_options().count()


def test_question_page_options_are_selectable(question_page):
    question_page.select_option(0)
    question_page.page.wait_for_timeout(1500)

    expect(question_page.get_option(0)).to_have_class(re.compile("ep-option-selected"))
    assert question_page.is_option_selected(0)
    assert question_page.get_strip_dot_state(1) == "answered"


def test_question_page_shows_the_bookmark_control(question_page):
    expect(question_page.get_bookmark_button()).to_be_visible()
    expect(question_page.get_bookmark_button()).to_be_enabled()


def test_question_page_shows_the_timer(question_page):
    expect(question_page.get_timer()).to_be_visible()
    expect(question_page.get_timer_text()).to_have_text(re.compile(r"^\d+:\d{2}$"))


def test_question_page_shows_the_navigation_controls(question_page):
    expect(question_page.get_continue_button()).to_be_visible()
    expect(question_page.get_continue_button()).to_be_enabled()
    expect(question_page.get_palette_strip()).to_be_visible()

    assert question_page.get_strip_dots().count() == question_page.get_total_questions()


def test_question_page_shows_the_remaining_controls(question_page):
    expect(question_page.get_palette_button()).to_be_enabled()
    expect(question_page.get_report_issue_button()).to_be_enabled()
    expect(question_page.get_note_button()).to_be_enabled()
    expect(question_page.get_mark_button()).to_be_enabled()
    # Not clicked: leaving the player ends the attempt for the rest of the run.
    expect(question_page.get_close_button()).to_be_visible()


def test_question_palette_marks_the_current_question(question_page):
    expect(question_page.get_active_strip_dot()).to_have_count(1)
    expect(question_page.get_active_strip_dot()).to_have_text("1")


def test_submit_sheet_reports_the_answer_status(question_page):
    question_page.open_submit_sheet()

    expect(question_page.get_submit_sheet()).to_be_visible()
    expect(question_page.get_status_row("Answered")).to_be_visible()
    expect(question_page.get_status_row("Not Answered")).to_be_visible()
    expect(question_page.get_status_row("Marked for review")).to_be_visible()
    expect(question_page.get_status_row("Not Visited")).to_be_visible()
    # Not submitted on purpose: the attempt is shared by the whole run.
    expect(question_page.get_submit_button()).to_be_visible()

    question_page.close_submit_sheet()

    expect(question_page.get_submit_sheet()).to_have_count(0)


# ---------------------------------------------------------------------------
# Scenario 6: bookmark
# ---------------------------------------------------------------------------

def test_bookmarking_a_question_and_removing_it(question_page):
    if question_page.is_bookmarked():
        question_page.click_bookmark()
        question_page.page.wait_for_timeout(1500)

    expect(question_page.get_bookmark_button()).to_have_attribute(
        "aria-label", "Add bookmark"
    )

    question_page.click_bookmark()
    question_page.page.wait_for_timeout(1500)

    expect(question_page.get_bookmark_button()).to_have_class(re.compile("ep-bookmarked"))
    expect(question_page.get_bookmark_button()).to_have_attribute(
        "aria-label", "Remove bookmark"
    )
    assert question_page.is_bookmarked()

    question_page.click_bookmark()
    question_page.page.wait_for_timeout(1500)

    expect(question_page.get_bookmark_button()).not_to_have_class(
        re.compile("ep-bookmarked")
    )
    expect(question_page.get_bookmark_button()).to_have_attribute(
        "aria-label", "Add bookmark"
    )
    assert question_page.is_bookmarked() is False


def test_bookmark_survives_moving_between_questions(question_page):
    if not question_page.is_bookmarked():
        question_page.click_bookmark()
        question_page.page.wait_for_timeout(1500)

    question_page.click_continue()
    question_page.page.wait_for_timeout(1500)
    question_page.go_to_question(1)
    question_page.page.wait_for_timeout(1500)

    assert question_page.is_bookmarked()

    question_page.click_bookmark()
    question_page.page.wait_for_timeout(1500)


# ---------------------------------------------------------------------------
# Scenario 7: timer
# ---------------------------------------------------------------------------

def test_timer_is_displayed_when_the_exam_begins(question_page):
    expect(question_page.get_timer_text()).to_be_visible()

    assert question_page.get_timer_seconds() > 0


def test_timer_counts_down(question_page):
    before = question_page.get_timer_seconds()
    question_page.page.wait_for_timeout(4000)
    after = question_page.get_timer_seconds()

    assert after < before


def test_timer_expiry_submits_the_exam(question_page):
    remaining = question_page.get_timer_seconds()
    pytest.skip(
        "Would need to hold the attempt open for the full exam duration "
        f"({remaining // 60} minutes left). Needs a short exam published for "
        "the test account to be checked in a run."
    )


# ---------------------------------------------------------------------------
# Scenario 8: question navigation
# ---------------------------------------------------------------------------

def test_continue_moves_to_the_next_question(question_page):
    first = question_page.get_question_text().inner_text()

    question_page.click_continue()
    question_page.page.wait_for_timeout(1500)

    assert question_page.get_current_question_number() == 2
    expect(question_page.get_active_strip_dot()).to_have_text("2")
    assert question_page.get_question_text().inner_text() != first


def test_palette_returns_to_the_previous_question(question_page):
    """The player has no Previous button: the palette strip is how you go back."""
    first = question_page.get_question_text().inner_text()

    question_page.click_continue()
    question_page.page.wait_for_timeout(1500)
    assert question_page.get_current_question_number() == 2

    question_page.go_to_question(1)
    question_page.page.wait_for_timeout(1500)

    assert question_page.get_current_question_number() == 1
    assert question_page.get_question_text().inner_text() == first


def test_question_content_changes_across_questions(question_page):
    seen = []
    for number in range(1, 4):
        question_page.go_to_question(number)
        question_page.page.wait_for_timeout(1500)
        assert question_page.get_current_question_number() == number
        seen.append(question_page.get_question_text().inner_text())

    assert len(set(seen)) == len(seen)


def test_marking_for_review_moves_on_and_flags_the_question(question_page):
    """Mark for review both flags the question and advances in one step."""
    question_page.click_mark_for_review()
    question_page.page.wait_for_timeout(2000)

    assert question_page.get_current_question_number() == 2
    assert question_page.get_strip_dot_state(1) in ("marked_answered", "marked")


def test_answering_updates_the_palette_state(question_page):
    assert question_page.get_strip_dot_state(1) != "not_visited"

    last = question_page.get_total_questions()
    assert question_page.get_strip_dot_state(last) == "not_visited"
