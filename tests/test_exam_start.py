"""Exam Start: the instructions page an Attempt opens, and starting from it.

Exams are always addressed by position, never by title, because the titles
differ from one account to the next.

Starting an exam consumes it: the backend answers a second exam-start for the
same exam with 406, while the card goes on offering Attempt regardless. Tests
that only read the instructions therefore share the first exam on offer, and
tests that press Start take one of their own through the fresh_attempt fixture,
so that one test cannot spend the exam the next one needs.
"""
import re
import pytest
from playwright.sync_api import expect

from conftest import STUDENT_MOBILE
from pages.home_page import HomePage
from pages.exam_page import ExamPage, ExamInstructionsPage, ExamResultPage
from pages.live_exam_page import LiveExamPage


EXAMS_URL = ExamPage.URL
EXAMS_URL_PATTERN = re.compile(r"https://eduport-react\.pages\.dev/exams(\?.*)?$")
INSTRUCTIONS_URL_PATTERN = re.compile(
    r"https://eduport-react\.pages\.dev/exams/\d+/instructions.*"
)
EXAM_LIST_API = "**/api/v3/exams/all"
EXAM_START_API = "**/api/v3/exams/exam-start"

NONE_UNATTEMPTED = "Every past exam on this account has been attempted"
NONE_LEFT_TO_START = (
    "Every past exam on this account has already been attempted. Publish more "
    "exams for the account to keep going."
)


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(STUDENT_MOBILE)


@pytest.fixture
def exam_list(page):
    home_page = HomePage(page)
    home_page.get_exams_button().click()
    page.wait_for_url(EXAMS_URL)

    exams_page = ExamPage(page)
    exams_page.wait_for_exams_loaded()
    exams_page.click_past_tab()
    return exams_page


def open_instructions(page, exam_list, index):
    """Open that exam's instructions, with what its card claimed alongside so
    the two can be compared."""
    expected = {
        "index": index,
        "title": exam_list.get_exam_title(index).inner_text().strip(),
        "minutes": exam_list.get_exam_minutes(index),
        "marks": exam_list.get_exam_marks(index),
    }
    exam_list.click_attempt(index)

    instructions_page = ExamInstructionsPage(page)
    instructions_page.wait_for_loaded()
    return instructions_page, expected


@pytest.fixture
def exam_start(page, exam_list):
    """The instructions of the first exam still offering Attempt.

    Read only: nothing reached through this fixture may press Start, because
    every test sharing it lands on the same exam."""
    index = exam_list.find_unattempted_exam()
    if index is None:
        pytest.skip(NONE_UNATTEMPTED)
    return open_instructions(page, exam_list, index)


@pytest.fixture
def instructions(exam_start):
    return exam_start[0]


@pytest.fixture(scope="session")
def _spent_exams():
    """Positions in the Attempt list this run has already used up."""
    return set()


@pytest.fixture
def fresh_attempt(page, exam_list, _spent_exams):
    """Start an exam that has not been attempted before, and hand back the
    player it opened along with what its card claimed.

    A card goes on offering Attempt after the exam behind it has been started,
    so offering Attempt is no proof of an unspent exam - neither this run nor
    an earlier one leaves a mark on the card. The only way to find one is to
    ask, so exams are tried in turn until one is granted, and the ones that
    come back refused are remembered for the rest of the run."""
    candidates = exam_list.find_unattempted_exams()
    if not candidates:
        pytest.skip(NONE_UNATTEMPTED)

    refusals = []
    for position, index in enumerate(candidates):
        if position in _spent_exams:
            continue
        _spent_exams.add(position)

        instructions, expected = open_instructions(page, exam_list, index)
        with page.expect_response(EXAM_START_API) as answer:
            instructions.click_start_exam()

        if answer.value.status == 200:
            page.wait_for_url(LiveExamPage.URL_PATTERN)
            player = LiveExamPage(page)
            player.wait_for_question()
            return player, expected

        refusals.append(f"{expected['title']!r} answered {answer.value.status}")
        page.goto(EXAMS_URL, wait_until="domcontentloaded")
        exam_list.wait_for_exams_loaded()
        exam_list.click_past_tab()

    pytest.skip(f"{NONE_LEFT_TO_START} Refused: {'; '.join(refusals) or 'none left'}")


# ---------------------------------------------------------------------------
# The instructions page
# ---------------------------------------------------------------------------

def test_instructions_page_loads_with_its_stats_and_start_button(page, instructions):
    expect(page).to_have_url(INSTRUCTIONS_URL_PATTERN)
    expect(instructions.get_header_title()).to_have_text("Exam")
    expect(instructions.get_exam_name()).not_to_be_empty()
    expect(instructions.get_stats()).to_have_count(2)
    expect(instructions.get_instructions_box()).to_be_visible()
    expect(instructions.get_start_exam_button()).to_be_visible()


def test_instructions_name_the_exam_the_card_named(exam_start):
    instructions, expected = exam_start

    expect(instructions.get_exam_name()).to_have_text(expected["title"])


def test_instructions_duration_matches_the_card(exam_start):
    instructions, expected = exam_start

    expect(instructions.get_duration()).to_be_visible()
    assert instructions.get_duration_minutes() == expected["minutes"]


def test_instructions_list_the_exam_rules(instructions):
    expect(instructions.get_instructions_title()).to_have_text("Instructions")
    expect(instructions.get_instructions_box()).to_be_visible()
    expect(instructions.get_instruction_items().first).to_be_visible()
    expect(instructions.get_important_note()).to_contain_text("only once")

    assert instructions.get_instruction_items().count() > 0


def test_start_exam_button_is_enabled(instructions):
    expect(instructions.get_start_exam_button()).to_be_visible()
    expect(instructions.get_start_exam_button()).to_be_enabled()


def test_instructions_report_the_number_of_questions_in_the_exam(exam_start):
    """An exam that can be started holds questions, so the stat above the
    instructions has to be able to say so."""
    instructions, expected = exam_start

    expect(instructions.get_total_questions()).to_be_visible()

    assert instructions.get_total_questions_count() > 0, (
        f"{expected['title']!r} offers Attempt but its instructions advertise no "
        f"questions. The stat tracks the total marks the card carries "
        f"({expected['marks']}) rather than the paper itself."
    )


def test_exam_with_no_questions_cannot_be_started():
    pytest.skip(
        "The question count on the instructions page is worked out from the "
        "exam's total marks, not from the paper, so an exam advertising 0 "
        "questions is not necessarily empty - one was started from this "
        "account and opened a player holding three. Nothing on the exam list "
        "or the instructions page can pick out a genuinely empty exam until "
        "that count comes from the paper."
    )


def test_zero_minute_exam_cannot_be_started(page, exam_list):
    index = next(
        (
            i
            for i in exam_list.find_unattempted_exams()
            if exam_list.get_exam_minutes(i) == 0
        ),
        None,
    )
    if index is None:
        pytest.skip("No exam on this account is configured with a 0 minute duration")

    exam_list.click_attempt(index)
    instructions = ExamInstructionsPage(page)

    if not instructions.is_start_enabled():
        return

    instructions.click_start_exam()

    expect(instructions.get_toast()).not_to_be_empty()
    assert LiveExamPage(page).is_open() is False


# ---------------------------------------------------------------------------
# Starting the exam
# ---------------------------------------------------------------------------

def test_start_exam_opens_the_player_on_the_first_question(page, fresh_attempt):
    player, _ = fresh_attempt

    expect(page).to_have_url(LiveExamPage.URL_PATTERN)
    expect(player.get_page()).to_be_visible()
    expect(player.get_question_counter()).to_contain_text(re.compile(r"^1/"))


def test_started_exam_shows_the_first_question_and_a_way_to_answer_it(fresh_attempt):
    """A paper carries multiple choice questions and numeric ones, and the
    first question is whichever the paper opens with."""
    player, _ = fresh_attempt

    expect(player.get_question_text()).not_to_be_empty()

    if player.is_numeric_question():
        expect(player.get_numeric_input()).to_be_visible()
    else:
        assert player.get_options().count() >= 2


def test_exam_cannot_be_started_a_second_time(page, exam_list, fresh_attempt):
    """An attempt is spent the moment it is handed out, so coming back to the
    same exam must not hand out another one."""
    _, expected = fresh_attempt

    page.goto(EXAMS_URL, wait_until="domcontentloaded")
    exam_list.wait_for_exams_loaded()
    exam_list.click_past_tab()
    second_try, _ = open_instructions(page, exam_list, expected["index"])
    second_try.click_start_exam()

    expect(second_try.get_toast()).to_contain_text(
        re.compile("already attempted", re.IGNORECASE)
    )
    expect(page).to_have_url(INSTRUCTIONS_URL_PATTERN)
    assert LiveExamPage(page).is_open() is False


def test_attempted_exam_opens_its_result_instead_of_the_instructions(page, exam_list):
    """An exam that has been attempted and had its result published offers
    Review, and that goes to the result rather than back to the start page."""
    index = exam_list.find_reviewable_exam()
    if index is None:
        pytest.skip("No attempted exam on this account has its result published")

    expect(exam_list.get_attempted_badge(index)).to_have_text("Attempted")
    exam_list.click_review(index)

    expect(page).to_have_url(ExamResultPage.URL_PATTERN)
    expect(ExamInstructionsPage(page).get_start_exam_button()).to_have_count(0)


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

def test_reload_keeps_the_exam_information_intact(page, exam_start):
    instructions, expected = exam_start

    page.reload()

    expect(page).to_have_url(INSTRUCTIONS_URL_PATTERN)
    expect(instructions.get_exam_name()).to_have_text(expected["title"])
    expect(instructions.get_start_exam_button()).to_be_visible()
    assert instructions.get_duration_minutes() == expected["minutes"]


def test_back_button_returns_to_the_exam_list(page, instructions, exam_list):
    instructions.click_back()

    expect(page).to_have_url(EXAMS_URL_PATTERN)
    expect(exam_list.get_page_title()).to_have_text("Exams")
    expect(instructions.get_start_exam_button()).to_have_count(0)


def test_browser_back_returns_to_the_exam_list(page, instructions, exam_list):
    page.go_back()

    expect(exam_list.get_exam_cards().first).to_be_visible()
    expect(instructions.get_start_exam_button()).to_have_count(0)


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------

def test_instructions_survive_a_blocked_exam_feed(page, exam_start):
    """The page is built entirely from the route it was opened with - title,
    marks and duration all ride in the query string and it calls nothing of its
    own - so the exam feed going away has to leave it standing."""
    instructions, expected = exam_start
    page.route(EXAM_LIST_API, lambda route: route.abort())

    page.reload()

    expect(page).to_have_url(INSTRUCTIONS_URL_PATTERN)
    expect(instructions.get_exam_name()).to_have_text(expected["title"])
    expect(instructions.get_instructions_box()).to_be_visible()
    expect(instructions.get_start_exam_button()).to_be_enabled()


def test_failed_exam_start_leaves_the_player_closed(page, instructions):
    page.route(EXAM_START_API, lambda route: route.abort())

    instructions.click_start_exam()

    expect(instructions.get_toast()).not_to_be_empty()
    assert LiveExamPage(page).is_open() is False


# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("width,height", [(1440, 900), (768, 1024), (390, 844)])
def test_instructions_page_is_responsive(page, instructions, width, height):
    page.set_viewport_size({"width": width, "height": height})
    page.wait_for_timeout(1000)

    expect(instructions.get_exam_name()).to_be_visible()
    expect(instructions.get_start_exam_button()).to_be_visible()
    assert instructions.fits_viewport_width()


def test_exam_list_shows_a_loading_indicator_while_it_loads(page):
    """Hold the exam feed open so the loading state cannot be missed."""
    held = []
    page.route(EXAM_LIST_API, lambda route: held.append(route))

    page.goto(ExamPage.URL, wait_until="commit")

    exams_page = ExamPage(page)
    expect(exams_page.get_loading_indicator()).to_be_visible(timeout=5000)
    expect(exams_page.get_loading_spinner()).to_be_visible()
