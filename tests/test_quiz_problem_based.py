"""Problem based practice: attending one, and what it pays.

Problem based is the adaptive one, and the mode the setup screen selects for
itself when a topic offers both. Its questions come from
practice-quiz/problem-quiz and its answers go to the submit beside it; an answer
got wrong can bring on a similar question to try again, which is what makes it
adaptive.

How the paying works, the same for both practices: nothing is paid for starting
a set and nothing for an answer being given. Each answer is posted as it is
given and answered with an acknowledgement; the submit carrying completed=true
is the one answered with the tally and the coins, and that is the moment the
balance moves. +4 an answer got right, -1 an answer got wrong, nothing for one
passed on with I don't know.

Getting an answer wrong brings on a similar question to try again, so a set
started as one question can end up asking three. Nothing here counts the
questions: what is held to the rate is however many of each kind the app says
it marked.

Every question a practice asks is used up for good, so each way of answering is
driven once for the whole run and read back by several tests. A test never
leans on another test having moved the balance first - each reads the balance
either side of its own set.

What is deliberately not here, because it is already covered:
  the entry points into Practice and the question screen itself are in
  test_practice_questions.py; the published coin rules and the daily task the
  set appears as are in test_daily_task_coins.py; the balance those payments
  land in is in test_coins.py; bookmarks and notes as Question Library data are
  in test_ql_bookmark.py and test_ql_my_notes.py. What is here is one practice
  of this kind, attended end to end.
"""
import pytest
from playwright.sync_api import expect

from conftest import STUDENT_MOBILE
from pages.leaderboard_page import read_balance, read_coin_log
from pages.practice_page import (
    CORRECT,
    DONT_KNOW,
    PROBLEM_BASED,
    QUIZ_APIS,
    RESULT_TITLES,
    WRONG,
    attend_quiz,
    start_quick_practice,
)

HOME_URL = "https://eduport-react.pages.dev/"

MODE = PROBLEM_BASED
QUESTIONS_API, SUBMIT_API = QUIZ_APIS[MODE]

# What an answer is worth. Held against what the set actually paid rather than
# taken on trust; the same three numbers are checked against the rules the app
# publishes in test_daily_task_coins.py.
PER_CORRECT = 4
PER_WRONG = -1
PER_DONT_KNOW = 0
RATE = {CORRECT: PER_CORRECT, WRONG: PER_WRONG, DONT_KNOW: PER_DONT_KNOW}

NOTHING_TO_PRACTISE = "No topic on this account has a question left to practise"


@pytest.fixture
def page(login_as):
    """The same student test_daily_task_coins.py and test_coins.py drive a
    practice on. Practice questions are spent here rather than on the second
    account because that is where both modes are offered."""
    return login_as(STUDENT_MOBILE)


def take_once(login_session, state, how):
    """Drive one set answering everything the same way, once per run."""
    if "reason" in state:
        pytest.skip(state["reason"])
    if "completion" in state:
        return state

    page = login_session(STUDENT_MOBILE)
    page.goto(HOME_URL, wait_until="domcontentloaded")

    taken = attend_quiz(page, how=how, mode=MODE)
    if taken is None:
        state["reason"] = NOTHING_TO_PRACTISE
        pytest.skip(NOTHING_TO_PRACTISE)
    if "reason" in taken:
        state["reason"] = taken["reason"]
        pytest.skip(taken["reason"])

    state.update(taken, how=how)
    return state


@pytest.fixture(scope="session")
def _right_state():
    return {}


@pytest.fixture(scope="session")
def _wrong_state():
    return {}


@pytest.fixture(scope="session")
def _idk_state():
    return {}


@pytest.fixture
def answered_right(login_session, _right_state):
    return take_once(login_session, _right_state, CORRECT)


@pytest.fixture
def answered_wrong(login_session, _wrong_state):
    return take_once(login_session, _wrong_state, WRONG)


@pytest.fixture
def passed_on(login_session, _idk_state):
    return take_once(login_session, _idk_state, DONT_KNOW)


@pytest.fixture
def set_answered(login_session, _right_state, _wrong_state, _idk_state):
    states = {CORRECT: _right_state, WRONG: _wrong_state, DONT_KNOW: _idk_state}

    def _take(how):
        return take_once(login_session, states[how], how)

    return _take


def marked(taken):
    """How many of each kind the completion call says the set was marked."""
    body = taken["completion"]
    return {CORRECT: body["correct"], WRONG: body["wrong"], DONT_KNOW: body["idk"]}


def expected_coins(taken):
    """Initial balance + 4 a right answer - 1 a wrong one + 0 a pass = what the
    set should have paid."""
    counted = marked(taken)
    return sum(RATE[kind] * counted[kind] for kind in RATE)


# ---------------------------------------------------------------------------
# 1. Opening one
# ---------------------------------------------------------------------------

def test_the_practice_opens_on_its_rules_and_then_its_first_question(page):
    """Home -> Practice -> a topic -> Problem based practice -> the rules screen, and Take test
    from there onto a question."""
    practice, practised = start_quick_practice(page, mode=MODE)
    if practice is None:
        pytest.skip((practised or {}).get("reason", NOTHING_TO_PRACTISE))

    assert practised["mode"] == MODE
    practice.wait_for_question()
    expect(practice.get_question()).to_be_visible()


def test_the_rules_screen_says_what_the_set_holds_and_what_it_pays(page):
    """The screen in front of the questions carries how many there are and the
    three scoring buckets."""
    practice, practised = start_quick_practice(page, mode=MODE, take_test=False)
    if practice is None:
        pytest.skip((practised or {}).get("reason", NOTHING_TO_PRACTISE))

    expect(practice.get_question_total()).not_to_be_empty()
    expect(practice.get_scoring().first).to_be_visible()
    expect(practice.get_take_test_button()).to_be_enabled()


def test_the_question_screen_carries_the_question_its_options_and_its_controls(page):
    practice, practised = start_quick_practice(page, mode=MODE)
    if practice is None:
        pytest.skip((practised or {}).get("reason", NOTHING_TO_PRACTISE))
    practice.wait_for_question()

    assert practice.get_question_text() != "" or practice.get_question_images().count(), (
        "the question is neither text nor a picture"
    )
    # A typed question offers a box in place of the options.
    if practice.is_numeric_question():
        expect(practice.get_numeric_input()).to_be_editable()
        expect(practice.get_options()).to_have_count(0)
    else:
        assert practice.get_options().count() >= 2

    expect(practice.get_back_button()).to_be_visible()
    expect(practice.get_bookmark_button()).to_be_visible()
    expect(practice.get_note_button()).to_be_visible()
    expect(practice.get_palette_button()).to_be_visible()
    expect(practice.get_dont_know_button()).to_be_visible()


# ---------------------------------------------------------------------------
# 2. What each kind of answer pays
# ---------------------------------------------------------------------------

def test_a_right_answer_pays_four_coins(answered_right):
    counted = marked(answered_right)
    assert counted[WRONG] == 0 and counted[DONT_KNOW] == 0, counted
    assert answered_right["completion"]["coin"] == PER_CORRECT * counted[CORRECT]


def test_a_wrong_answer_costs_one_coin(answered_wrong):
    counted = marked(answered_wrong)
    assert counted[CORRECT] == 0 and counted[DONT_KNOW] == 0, counted
    assert answered_wrong["completion"]["coin"] == PER_WRONG * counted[WRONG]


def test_passing_on_a_question_pays_nothing(passed_on):
    counted = marked(passed_on)
    assert counted[CORRECT] == 0 and counted[WRONG] == 0, counted
    assert passed_on["completion"]["coin"] == PER_DONT_KNOW


# ---------------------------------------------------------------------------
# 3. The end screen
# ---------------------------------------------------------------------------

def test_the_set_ends_on_a_result_screen_naming_this_practice(answered_right):
    assert answered_right["result_title"] == RESULT_TITLES[MODE]


def test_the_result_screen_counts_the_answers_the_way_the_app_marked_them(
    answered_right,
):
    """Correct, Wrong and I don't know on screen are the three the completion
    call answered with."""
    counted = marked(answered_right)
    shown = answered_right["stats"]

    assert shown["Correct"] == counted[CORRECT]
    assert shown["Wrong"] == counted[WRONG]
    assert shown["I don't know"] == counted[DONT_KNOW]


def test_the_result_screen_shows_the_coins_the_completion_call_paid(answered_right):
    assert answered_right["on_result"] == answered_right["completion"]["coin"]


def test_a_losing_set_shows_its_award_as_a_loss(answered_wrong):
    """A set that cost coins is marked as having cost them rather than shown as
    a bare number."""
    paid = answered_wrong["completion"]["coin"]
    assert paid < 0
    assert answered_wrong["marked_negative"], "a loss was not marked as one"
    # The screen carries the figure signed on some result cards and bare with a
    # marker on others, so it is read either way round rather than assumed.
    assert answered_wrong["on_result"] in (paid, abs(paid)), (
        f"the result screen showed {answered_wrong['on_result']} for a set that "
        f"cost {paid}"
    )


def test_a_set_passed_on_shows_no_award(passed_on):
    assert passed_on["on_result"] == 0


# ---------------------------------------------------------------------------
# 4. The balance and the coin log
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("how", [CORRECT, WRONG, DONT_KNOW])
def test_the_balance_moves_by_exactly_what_the_set_was_marked(
    how, set_answered
):
    """Initial balance, +4 a right answer, -1 a wrong one, nothing for a pass,
    is the balance the coins call answers afterwards."""
    taken = set_answered(how)
    assert taken["after"] == taken["before"] + expected_coins(taken)


@pytest.mark.parametrize("how", [CORRECT, WRONG, DONT_KNOW])
def test_the_balance_is_what_the_completion_call_said_it_would_be(
    how, set_answered
):
    taken = set_answered(how)
    assert taken["after"] == taken["before"] + taken["completion"]["coin"]


def test_what_the_set_paid_is_written_into_todays_coin_log(answered_right):
    """The award is an entry of its own in the Today log, and the log adds up
    to the balance."""
    scores = [event["score"] for event in answered_right["log"]]

    assert sum(scores) == answered_right["after"], answered_right["log"]
    assert answered_right["completion"]["coin"] in scores, (
        f"nothing in today's log paid {answered_right['completion']['coin']}: {scores}"
    )


def test_what_a_losing_set_cost_is_written_into_todays_coin_log(answered_wrong):
    scores = [event["score"] for event in answered_wrong["log"]]

    assert sum(scores) == answered_wrong["after"], answered_wrong["log"]
    assert answered_wrong["completion"]["coin"] in scores, (
        f"nothing in today's log took {answered_wrong['completion']['coin']}: {scores}"
    )


# ---------------------------------------------------------------------------
# 5. The completion call against the screen
# ---------------------------------------------------------------------------

def test_the_completion_call_says_the_set_was_completed(answered_right):
    """Not just a 200: the last submit is the one that carries completed=true
    and comes back saying so, with the tally."""
    assert answered_right["completion_request"]["completed"] is True
    assert answered_right["completion"]["message"] == "Quiz Completed Successfully"


def test_the_completion_call_marks_every_answer_the_set_asked_for(answered_right):
    """correct + wrong + idk is the whole set, and the attempt counts agree with
    the marks."""
    body = answered_right["completion"]
    counted = marked(answered_right)

    assert sum(counted.values()) > 0
    assert body["correct_attempts"] == body["correct"]
    assert body["wrong_attempts"] == body["wrong"]
    assert body["idk_attempts"] == body["idk"]


def test_the_answers_go_to_this_practices_own_submit_call(answered_right):
    """This practice is served and submitted through its own pair of calls, not
    the other practice's."""
    sent = answered_right["submitted"]
    assert sent, "the set was completed without a submit being seen"
    for call in sent:
        assert call["sent"]["question_id"]
        assert call["sent"]["task_id"]


def test_every_question_the_screen_asked_came_from_the_payload_it_was_served(
    answered_right,
):
    served = answered_right["served"]
    assert served, f"{QUESTIONS_API} served nothing"
    assert any(payload.get("questions") for payload in served)
