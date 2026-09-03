"""Daily tasks and what they pay: the reward rules, read off the running app.

A quick practice is a daily task. Starting one posts practice-quiz/create and
the task it answers with is the card that appears under Practice on the Daily
Tasks screen for today, so the two are one thing seen from two screens.

How the paying works, as the app does it rather than as it might:

  when      nothing is paid for starting a quiz and nothing for giving an
            answer. Every answer is posted to practice-quiz/submit/problem-quiz
            as it is given, and each of those is answered "Question Submitted
            Successfully" and nothing else. The last one carries completed=true
            and is answered with the tally and the coins - correct, wrong, idk,
            coin - and that is the moment the balance moves.
  how much  +4 for each answer got right, -1 for each got wrong, nothing for
            each passed on with I don't know. That is what the rules screen in
            front of the quiz says, what the leaderboard publishes, and what
            these tests hold the app to.
  again     a quiz that has been completed is finished with. Reopening it from
            the Daily Tasks screen lands on its instructions rather than on a
            question, and neither reopening it nor sending its last submit
            again pays anything more.

Getting an answer wrong brings on a similar question to try again, so a set
started as one question can end up asking three. Nothing here counts on how
many were asked: what is asserted is the rate, against however many of each
kind the app says it marked.

Every quiz taken uses up questions the account cannot get back, so each way of
answering is driven once for the whole run and read back by several tests.

The Daily Tasks calendar, its date strip and its task groups are covered in
test_daily_tasks.py; the balance those payments land in is covered in
test_coins.py.
"""
import pytest
from playwright.sync_api import expect

from pages.daily_tasks_page import DailyTasksPage
from pages.leaderboard_page import (
    LeaderboardPage,
    post_api,
    read_balance,
    read_coin_log,
)
from pages.practice_page import (
    CORRECT,
    DONT_KNOW,
    WRONG,
    PracticeQuestionPage,
    start_quick_practice,
    take_practice_quiz,
)

MOBILE = "9876543210"

HOME_URL = "https://eduport-react.pages.dev/"
DAILY_TASKS_API = "**/api/v3/dailytasks/list"

NOTHING_TO_PRACTISE = "No topic on this account has a question left to practise"

# What the app says an answer is worth. Held against what it actually pays
# rather than assumed: test_the_published_rules_are_what_a_quiz_pays checks the
# same three numbers against the rules the leaderboard publishes.
PER_CORRECT = 4
PER_WRONG = -1
PER_DONT_KNOW = 0

# The heading the practice_tasks bucket of a day is drawn under.
PRACTICE = "Practice"


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


def take_quiz_once(login_session, state, how):
    """Complete one quick practice answering everything the same way, and
    record what it paid.

    Driven once per run and shared, because the questions it uses are gone
    afterwards. The balance is read from inside the page: the before reading is
    taken with a quiz on screen that cannot be navigated away from and back
    to."""
    if "reason" in state:
        pytest.skip(state["reason"])
    if "completion" in state:
        return state

    page = login_session(MOBILE)
    page.goto(HOME_URL, wait_until="domcontentloaded")

    before = read_balance(page)
    taken = take_practice_quiz(page, how=how, questions=1)
    if taken is None:
        state["reason"] = NOTHING_TO_PRACTISE
        pytest.skip(NOTHING_TO_PRACTISE)

    practice = taken["practice"]
    state.update(
        taken,
        before=before,
        after=read_balance(page),
        on_result=practice.get_awarded_coins(),
        marked_negative=practice.award_is_marked_negative(),
        stats=practice.get_result_stat_values(),
    )
    practice.close_result()
    return state


@pytest.fixture(scope="session")
def _right_state():
    return {}


@pytest.fixture(scope="session")
def _wrong_state():
    return {}


@pytest.fixture(scope="session")
def _passed_state():
    return {}


@pytest.fixture(scope="session")
def answered_right(login_session, _right_state):
    return take_quiz_once(login_session, _right_state, CORRECT)


@pytest.fixture(scope="session")
def answered_wrong(login_session, _wrong_state):
    return take_quiz_once(login_session, _wrong_state, WRONG)


@pytest.fixture(scope="session")
def passed_on_everything(login_session, _passed_state):
    return take_quiz_once(login_session, _passed_state, DONT_KNOW)


# ---------------------------------------------------------------------------
# 1. What each kind of answer pays
#
# Each of these drives a quiz one way and holds the coins it came to against
# the tally the app itself reports, so nothing depends on how many questions
# the set ended up asking.
# ---------------------------------------------------------------------------

def test_a_right_answer_pays_four_coins(answered_right):
    marked = answered_right["completion"]

    assert marked["wrong"] == 0 and marked["idk"] == 0, marked
    assert marked["correct"] > 0, "the set was answered right but nothing was marked so"
    assert marked["coin"] == PER_CORRECT * marked["correct"], marked


def test_a_wrong_answer_costs_one_coin(answered_wrong):
    marked = answered_wrong["completion"]

    assert marked["correct"] == 0 and marked["idk"] == 0, marked
    assert marked["wrong"] > 0, "the set was answered wrong but nothing was marked so"
    assert marked["coin"] == PER_WRONG * marked["wrong"], marked


def test_i_dont_know_pays_nothing(passed_on_everything):
    marked = passed_on_everything["completion"]

    assert marked["correct"] == 0 and marked["wrong"] == 0, marked
    assert marked["idk"] > 0, "every question was passed on but none was marked so"
    assert marked["coin"] == PER_DONT_KNOW, marked


@pytest.mark.parametrize(
    "taken", ["answered_right", "answered_wrong", "passed_on_everything"]
)
def test_the_balance_moves_by_what_the_quiz_paid(request, taken):
    """Whatever the set came to, the balance moved by exactly that, and what
    it came to is the rate the answers were given at."""
    quiz = request.getfixturevalue(taken)
    marked = quiz["completion"]

    assert marked["coin"] == (
        PER_CORRECT * marked["correct"]
        + PER_WRONG * marked["wrong"]
        + PER_DONT_KNOW * marked["idk"]
    ), marked
    assert quiz["after"] == quiz["before"] + marked["coin"], (
        f"{quiz['before']} -> {quiz['after']} on a quiz that paid {marked['coin']}"
    )


@pytest.mark.parametrize(
    "taken", ["answered_right", "answered_wrong", "passed_on_everything"]
)
def test_the_result_screen_shows_what_the_api_marked(request, taken):
    """The result screen is the same tally the submit was answered with: the
    coins, and how many questions fell into each bucket."""
    quiz = request.getfixturevalue(taken)
    marked = quiz["completion"]

    assert quiz["on_result"] == marked["coin"]
    assert quiz["marked_negative"] is (marked["coin"] < 0), (
        "the result screen is styled the opposite way to the figure it shows"
    )
    assert quiz["stats"] == {
        "Correct": marked["correct"],
        "I don't know": marked["idk"],
        "Wrong": marked["wrong"],
    }


def test_the_published_rules_are_what_a_quiz_pays(
    page, answered_right, answered_wrong, passed_on_everything
):
    """The leaderboard publishes what an answer is worth. The three quizzes
    taken here are held to those numbers rather than to numbers written down
    in this file."""
    page.goto(LeaderboardPage.URL, wait_until="domcontentloaded")
    leaderboard = LeaderboardPage(page)
    leaderboard.wait_for_loaded()
    leaderboard.open_info()
    rules = leaderboard.get_rules()

    published = {
        "For each correct answer": PER_CORRECT,
        "For an incorrect answer": PER_WRONG,
    }
    for what, coins in published.items():
        assert rules.get(what) == coins, rules

    for quiz in (answered_right, answered_wrong, passed_on_everything):
        marked = quiz["completion"]
        assert marked["coin"] == (
            rules["For each correct answer"] * marked["correct"]
            + rules["For an incorrect answer"] * marked["wrong"]
        ), marked


@pytest.mark.parametrize(
    "taken", ["answered_right", "answered_wrong", "passed_on_everything"]
)
def test_a_completed_quiz_is_written_into_the_coin_log(request, page, taken):
    """The award is a coin event of its own in today's ledger, worth what the
    quiz came to."""
    quiz = request.getfixturevalue(taken)
    page.goto(LeaderboardPage.URL, wait_until="domcontentloaded")
    LeaderboardPage(page).wait_for_loaded()

    events = read_coin_log(page, "log-today")
    practice_events = [
        event for event in events if event["tag"] == "practice_problem_quiz_completed"
    ]

    assert practice_events, [event["tag"] for event in events]
    assert quiz["completion"]["coin"] in [
        event["score"] for event in practice_events
    ], practice_events


# ---------------------------------------------------------------------------
# 2. Being paid once
# ---------------------------------------------------------------------------

def test_starting_a_quiz_pays_nothing(page):
    """A set is created and its first question put up without a coin changing
    hands: the paying happens on the way out, not on the way in.

    The quiz started here is left unanswered on purpose, so it is still there
    to be finished and nothing is used up."""
    page.goto(HOME_URL, wait_until="domcontentloaded")
    before = read_balance(page)

    practice, _ = start_quick_practice(page, questions=1)
    if practice is None:
        pytest.skip(NOTHING_TO_PRACTISE)

    expect(practice.get_options().first).to_be_visible()
    assert read_balance(page) == before, "starting a quiz moved the balance"

    practice.select_option(0)
    practice.submit()
    assert read_balance(page) == before, "giving an answer moved the balance"


def test_reopening_a_completed_quiz_does_not_pay_again(page, answered_right):
    """The finished set is still on the Daily Tasks screen. Opening it lands
    on its instructions rather than on a question, and the balance stays where
    the quiz left it."""
    page.goto(DailyTasksPage.URL, wait_until="domcontentloaded")
    daily_tasks = DailyTasksPage(page)
    daily_tasks.wait_for_tasks_loaded()

    finished = [
        index
        for index in range(daily_tasks.task_card_count(PRACTICE))
        if daily_tasks.is_task_complete(index, PRACTICE)
    ]
    if not finished:
        pytest.skip("No finished practice task on today's list")

    before = read_balance(page)
    daily_tasks.click_task_card(finished[0], PRACTICE)

    practice = PracticeQuestionPage(page)
    expect(practice.get_take_test_button()).to_be_visible(timeout=30000)

    assert read_balance(page) == before, "reopening a finished quiz paid again"


def test_sending_the_last_submit_again_does_not_pay_again(page, answered_right):
    """The submit that finished the set, posted a second time exactly as it
    was, leaves the balance alone. Sending it again is what a retried request
    or a double tap would do."""
    sent = answered_right["completion_request"]

    page.goto(HOME_URL, wait_until="domcontentloaded")
    before = read_balance(page)

    again = post_api(page, "/practice-quiz/submit/problem-quiz", sent)
    print("the same submit again:", again)

    assert read_balance(page) == before, (
        f"the submit paid a second time: {again}"
    )


def test_reloading_the_task_list_does_not_pay_again(page, answered_right):
    """The finished task is still finished after a refresh and still worth
    what it was worth: nothing about the reward is redone by asking for the
    screen again."""
    page.goto(DailyTasksPage.URL, wait_until="domcontentloaded")
    daily_tasks = DailyTasksPage(page)
    daily_tasks.wait_for_tasks_loaded()

    before = read_balance(page)
    finished_before = daily_tasks.get_task_completed_marks(PRACTICE).count()

    page.reload(wait_until="domcontentloaded")
    daily_tasks.wait_for_tasks_loaded()
    daily_tasks.task_card_count(PRACTICE)

    assert read_balance(page) == before, "a refresh paid for the quiz again"
    assert daily_tasks.get_task_completed_marks(PRACTICE).count() == finished_before


# ---------------------------------------------------------------------------
# 3. The task list the quizzes land on
#
# The calendar and the task groups are checked in test_daily_tasks.py. What is
# checked here is the cards themselves: what each one says it is, how far
# through it is and whether it is finished.
# ---------------------------------------------------------------------------

def open_daily_tasks_with_payload(page):
    """The Daily Tasks screen together with the day it is drawn from."""
    with page.expect_response(DAILY_TASKS_API) as answer:
        page.goto(DailyTasksPage.URL, wait_until="domcontentloaded")
    assert answer.value.status == 200, f"dailytasks answered {answer.value.status}"

    daily_tasks = DailyTasksPage(page)
    daily_tasks.wait_for_tasks_loaded()

    selected = int(
        daily_tasks.get_selected_date().locator(".dt-day-num").inner_text().strip()
    )
    day = next(
        (
            entry
            for entry in answer.value.json()["results"]
            if int(entry["date"].split("-")[2]) == selected
        ),
        None,
    )
    return daily_tasks, day


def test_the_practice_cards_match_the_daily_tasks_api(page):
    """One card under Practice per practice task the day was served with,
    titled with the topic it is on.

    Scoped to Practice because that is the group a quick practice lands in and
    the one this account is served; the other groups are drawn by the same list
    but from buckets nothing here fills."""
    daily_tasks, day = open_daily_tasks_with_payload(page)
    if day is None:
        pytest.skip("The selected date is outside the range the API answered for")

    tasks = day["practice_tasks"]
    if not tasks:
        pytest.skip("No practice task on the selected date")

    cards = daily_tasks.get_task_cards(PRACTICE)
    expect(cards).to_have_count(len(tasks))

    expected = [task["topic_title"].strip() for task in tasks]
    assert daily_tasks.get_task_card_titles(PRACTICE) == expected


def test_the_card_counts_match_the_progress_the_api_reports(page):
    """A practice card reads "2/3 Questions": how many of the set have been
    answered, over how many it holds."""
    daily_tasks, day = open_daily_tasks_with_payload(page)
    if day is None or not day["practice_tasks"]:
        pytest.skip("No practice task on the selected date")

    for index, task in enumerate(day["practice_tasks"]):
        shown = daily_tasks.get_task_card_counts(index, PRACTICE)
        assert shown == (task["progress"], task["questions_count"]), task["topic_title"]


def test_a_finished_task_carries_the_tick_and_an_unfinished_one_does_not(page):
    """The tick where the coin marker sits is the app's own answer to
    is_completed, so the payload decides which cards carry one."""
    daily_tasks, day = open_daily_tasks_with_payload(page)
    if day is None or not day["practice_tasks"]:
        pytest.skip("No practice task on the selected date")

    tasks = day["practice_tasks"]
    shown = [
        daily_tasks.is_task_complete(index, PRACTICE) for index in range(len(tasks))
    ]
    expected = [bool(task["is_completed"]) for task in tasks]

    assert shown == expected
    expect(daily_tasks.get_task_completed_marks(PRACTICE)).to_have_count(sum(expected))


def test_the_quiz_that_was_taken_shows_up_finished_on_todays_list(page, answered_right):
    """The set completed for its coins is a task of today, and the list says
    so: every question answered, and the tick against it."""
    daily_tasks, day = open_daily_tasks_with_payload(page)
    if day is None:
        pytest.skip("Today is outside the range the API answered for")

    task_id = answered_right["completion_request"]["task_id"]
    ids = [task["id"] for task in day["practice_tasks"]]
    assert task_id in ids, (
        f"the quiz that was taken (task {task_id}) is not on today's list: {ids}"
    )

    index = ids.index(task_id)
    task = day["practice_tasks"][index]

    assert task["is_completed"] is True
    assert task["progress"] == task["questions_count"]
    assert daily_tasks.get_task_card_counts(index, PRACTICE) == (
        task["progress"],
        task["questions_count"],
    )
    assert daily_tasks.is_task_complete(index, PRACTICE)


def test_the_daily_task_rate_the_app_publishes(page):
    """The leaderboard publishes a daily task rate of its own, for a study
    task rather than for the practice ones these tests take.

    Recorded rather than earned: the account is served no study task to
    complete, so what it pays cannot be driven from here."""
    page.goto(LeaderboardPage.URL, wait_until="domcontentloaded")
    leaderboard = LeaderboardPage(page)
    leaderboard.wait_for_loaded()
    leaderboard.open_info()

    assert "Daily Tasks" in leaderboard.get_rule_section_titles()
    rules = leaderboard.get_rules()
    study = "For completing a study task from your daily tasks"

    assert study in rules, rules
    assert rules[study] == 10
    print("published daily task rate:", rules[study])
