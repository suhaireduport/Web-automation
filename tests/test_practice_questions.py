"""Practice Questions: the quick practice, from both screens that offer one.

A practice is reached two ways - the Practice button on Home, and the "+" on
Daily Tasks, whose Practice card opens the same topic picker. From there the
picker, the setup screen, the rules screen and the questions themselves are one
flow, which is what this file walks.

What the flow calls, read off the running app rather than assumed:

  create        POST practice-quiz/create makes the task the practice runs as,
                and answers with the task it made.
  questions     GET practice-quiz/non-adaptive-quiz?task_id=..&task_type=custom
                serves the whole set at once, each question with its options,
                its right_answers and its solution.
  submit        POST practice-quiz/submit/non-adaptive-quiz marks an answer,
                and the last one answers with the tally for the whole set.

Note these are the non-adaptive endpoints. PROBLEM_QUIZ_API and SUBMIT_API in
pages/practice_page.py name the problem-quiz pair instead, which this flow never
calls. The setup screen can offer both modes and preselects Problem based where
it does, so Quick practice is asked for by name.

What is deliberately not here, because it is covered already:

  the coin rates    test_daily_task_coins.py drives a practice every way and
                    holds what it paid against the published rule, and checks
                    the result tally against the submit it came from.
  the balance       test_coins.py follows the chip and the coin log.
  the other entry   test_ql_subject.py reaches the same picker from a Question
                    Library recommendation.
  the "+" modal     test_daily_tasks.py opens and closes it; only the journey
                    through its Practice card is taken here.
"""
import re

import pytest
from playwright.sync_api import expect

from conftest import SECOND_STUDENT_MOBILE
from pages.daily_tasks_page import DailyTasksPage
from pages.home_page import HomePage
from pages.practice_page import (
    AddTopicsPage,
    QUICK_PRACTICE,
    answer_key,
    answer_question,
    open_practice_from_home,
    right_answers,
    signature,
    start_quick_practice,
    CORRECT,
    DONT_KNOW,
    TYPED_INPUTS,
    WRONG,
)

HOME_URL = "https://eduport-react.pages.dev/"

# The calls the flow makes, taken from the network rather than guessed at.
CREATE_API = "practice-quiz/create"
QUIZ_API = "practice-quiz/non-adaptive-quiz"
SUBMIT_API = "practice-quiz/submit/non-adaptive-quiz"

NO_TOPIC = (
    "No topic on this account has a question left to practise, so no quick "
    "practice can be started"
)
NO_LONG_TOPIC = (
    "No topic on this account has enough questions left for a set of more "
    "than one"
)


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test.

    The second student, because answering a practice question takes it out of
    the pool for good and the main student already carries the coins files,
    which draw on the same pool."""
    return login_as(SECOND_STUDENT_MOBILE)


def start_practice(page, questions=1, minimum=1):
    """Home -> Practice -> a topic -> the rules screen of a set.

    Collects the questions the set was served with on the way, because the
    right answer is not on screen until one has been given. Hands back the
    question page, what was practised, and the payloads collected.
    """
    served = []
    page.on(
        "response",
        lambda response: served.append(response.json())
        if QUIZ_API in response.url and SUBMIT_API not in response.url
        else None,
    )

    # Quick practice is asked for by name: the setup screen preselects Problem
    # based on topics that offer both, and that is a different quiz served
    # through a different call.
    practice, practised = start_quick_practice(
        page, questions=questions, minimum=minimum, mode=QUICK_PRACTICE, take_test=False
    )
    if practice is None:
        if practised:
            pytest.skip(practised["reason"])
        pytest.skip(NO_TOPIC if minimum == 1 else NO_LONG_TOPIC)
    return practice, practised, served


@pytest.fixture
def rules_screen(page):
    """A started practice, held at the rules screen before any question."""
    practice, practised, served = start_practice(page)
    return practice, practised, served


@pytest.fixture
def question_screen(rules_screen):
    """The first question of a one question set."""
    practice, practised, served = rules_screen
    practice.take_test()
    return practice, practised, served


@pytest.fixture
def long_question_screen(page):
    """The first question of a set with more than one question in it."""
    practice, practised, served = start_practice(page, questions=5, minimum=5)
    practice.take_test()
    return practice, practised, served


def key_from(served):
    key = {}
    for payload in served:
        key.update(answer_key(payload))
    return key


def answer(practice, served, how):
    """Answer the question on screen the way asked for, and wait for marking.

    Hands back what was given: the option picked, the number typed, or None.
    Passing on a question needs no answer key, so served may be None then."""
    if how is None:
        return answer_question(practice, {}, DONT_KNOW)
    return answer_question(practice, key_from(served), how)


def first_question(served):
    """The question a set opens on, as it was served."""
    return served[0]["questions"][0]


def is_typed(question):
    """Whether a question is answered by typing rather than by choosing."""
    return question["input_type"] in TYPED_INPUTS


# ---------------------------------------------------------------------------
# Getting there
# ---------------------------------------------------------------------------

def test_practice_opens_the_topic_picker_from_home(page):
    """Home -> Practice lands on a picker ready to choose a topic in."""
    page.goto(HOME_URL, wait_until="domcontentloaded")
    add_topics = open_practice_from_home(page)

    expect(page).to_have_url(AddTopicsPage.URL)
    expect(add_topics.get_page()).to_be_visible()
    expect(add_topics.get_title()).to_have_text("Add topics")
    expect(add_topics.get_tabs().first).to_be_visible()
    expect(add_topics.get_footer()).to_be_visible()

    assert add_topics.chapter_count() > 0


def test_practice_opens_the_topic_picker_from_the_daily_tasks_plus_button(page):
    """Daily Tasks -> "+" -> Practice reaches the same picker Home does."""
    daily_tasks = DailyTasksPage(page)
    daily_tasks.open()
    daily_tasks.click_fab()

    expect(daily_tasks.get_add_task_modal()).to_be_visible()
    expect(daily_tasks.get_practice_card()).to_contain_text("Practice")

    daily_tasks.get_practice_card().click()
    page.wait_for_url(AddTopicsPage.URL)

    add_topics = AddTopicsPage(page)
    add_topics.wait_for_loaded()

    expect(add_topics.get_title()).to_have_text("Add topics")
    assert add_topics.chapter_count() > 0


def test_both_entry_points_open_the_same_topic_picker(page):
    """The two routes are one screen, so a practice runs the same either way."""
    page.goto(HOME_URL, wait_until="domcontentloaded")
    open_practice_from_home(page)
    from_home = page.url

    daily_tasks = DailyTasksPage(page)
    daily_tasks.open()
    daily_tasks.click_fab()
    daily_tasks.get_practice_card().click()
    page.wait_for_url(AddTopicsPage.URL)

    assert page.url == from_home == AddTopicsPage.URL


# ---------------------------------------------------------------------------
# The rules screen
# ---------------------------------------------------------------------------

def test_the_rules_screen_names_the_topic_and_counts_the_questions(rules_screen):
    practice, practised, _ = rules_screen

    expect(practice.get_title()).to_have_text(practised["topic"])
    expect(practice.get_subtitle()).to_have_text("Quick Practice")
    expect(practice.get_question_total()).to_have_text(re.compile(r"^\d+$"))
    expect(practice.get_take_test_button()).to_be_enabled()

    assert int(practice.get_question_total().inner_text()) > 0


def test_the_rules_screen_publishes_the_scoring(rules_screen):
    """What an answer is worth is said before the set is taken. The rates
    themselves are earned and checked in test_daily_task_coins.py; this is
    only that the screen publishes them."""
    practice, _, _ = rules_screen

    expect(practice.get_scoring()).to_have_count(3)

    published = " ".join(practice.get_scoring().all_inner_texts())
    for bucket in ("Correct", "I don't know", "Wrong"):
        assert bucket in published, f"{bucket!r} is not published: {published!r}"
    assert re.search(r"[-+]\d+", published), (
        f"no rate is published beside the buckets: {published!r}"
    )


# ---------------------------------------------------------------------------
# The question screen
# ---------------------------------------------------------------------------

def test_the_question_screen_shows_the_question_and_how_to_answer_it(question_screen):
    """A question is answered by choosing among options or by typing a number,
    whichever it was served as, and the screen offers that and only that."""
    practice, _, served = question_screen

    expect(practice.get_question()).to_be_visible()
    expect(practice.get_primary_button()).to_have_text("Submit")

    # A question, and an option under it, can be a picture rather than words,
    # so what is asked for is that something was drawn - not that it reads.
    assert practice.get_question_text() != "" or practice.get_question_images().count(), (
        "the question is neither text nor a picture"
    )

    if is_typed(first_question(served)):
        expect(practice.get_type_answer_label()).to_have_text("Type answer")
        expect(practice.get_numeric_input()).to_be_editable()
        expect(practice.get_numeric_input()).to_have_value("")
        expect(practice.get_choose_label()).to_have_count(0)
        expect(practice.get_options()).to_have_count(0)
        return

    expect(practice.get_choose_label()).to_be_visible()
    expect(practice.get_options().first).to_be_visible()
    expect(practice.get_numeric_input()).to_have_count(0)

    assert practice.get_options().count() >= 2
    assert practice.get_option_letters().count() == practice.get_options().count()

    for index in range(practice.get_options().count()):
        option = practice.get_option(index)
        assert option.inner_text().strip() or practice.get_option_images(index).count(), (
            f"option {index} is neither text nor a picture"
        )


def test_the_question_screen_offers_its_controls(question_screen):
    practice, _, _ = question_screen

    expect(practice.get_back_button()).to_be_visible()
    expect(practice.get_bookmark_button()).to_be_enabled()
    expect(practice.get_note_button()).to_be_enabled()
    expect(practice.get_palette_button()).to_be_enabled()
    expect(practice.get_report_button()).to_be_enabled()
    expect(practice.get_dont_know_button()).to_have_text("I don't know")


def test_the_progress_strip_carries_one_dot_per_question(question_screen):
    practice, _, served = question_screen

    expect(practice.get_strip_dots().first).to_be_visible()

    assert practice.question_total() == len(served[0]["questions"])
    assert "tq-dot-current" in practice.get_strip_dot_class(0)


# ---------------------------------------------------------------------------
# Answering
# ---------------------------------------------------------------------------

def test_an_answer_is_held_until_it_is_submitted(question_screen):
    """A chosen option is the only one picked out; a typed answer stays in its
    box, which takes digits and turns letters away."""
    practice, _, served = question_screen

    if is_typed(first_question(served)):
        practice.get_numeric_input().press_sequentially("12a")

        expect(practice.get_numeric_input()).to_have_value("12")
        expect(practice.get_numeric_mark()).to_have_count(0)
        expect(practice.get_primary_button()).to_have_text("Submit")
        return

    practice.select_option(0)

    assert practice.is_option_selected(0)
    for index in range(1, practice.get_options().count()):
        assert not practice.is_option_selected(index)


def test_a_correct_answer_is_marked_correct(question_screen):
    practice, _, served = question_screen
    answer(practice, served, CORRECT)

    if is_typed(first_question(served)):
        expect(practice.get_numeric_marked_correct()).to_have_count(1)
        expect(practice.get_numeric_marked_wrong()).to_have_count(0)
        expect(practice.get_numeric_mark()).to_be_visible()
        expect(practice.get_numeric_input()).to_be_disabled()
        # Nothing to put right, so the right answer is not spelled out.
        expect(practice.get_correct_answer_box()).to_have_count(0)
    else:
        expect(practice.get_correct_options()).to_have_count(1)
        expect(practice.get_wrong_options()).to_have_count(0)
    expect(practice.get_primary_button()).to_have_text("Next")

    assert practice.answered_wrong() is False


def test_a_wrong_answer_marks_the_choice_and_reveals_the_right_one(question_screen):
    practice, _, served = question_screen
    answer(practice, served, WRONG)

    question = first_question(served)
    if is_typed(question):
        expect(practice.get_numeric_marked_wrong()).to_have_count(1)
        expect(practice.get_numeric_marked_correct()).to_have_count(0)
        expect(practice.get_numeric_mark()).to_be_visible()
        expect(practice.get_correct_answer_label()).to_have_text("The correct answer is :")
        expect(practice.get_correct_answer_box()).to_have_text(
            str(question["right_answers"])
        )
    else:
        expect(practice.get_wrong_options()).to_have_count(1)
        expect(practice.get_correct_options()).to_have_count(1)
    expect(practice.get_primary_button()).to_have_text("Next")

    assert practice.answered_wrong() is True


def test_i_dont_know_reveals_the_answer_without_marking_one_wrong(question_screen):
    practice, _, served = question_screen
    answer(practice, None, None)

    question = first_question(served)
    if is_typed(question):
        expect(practice.get_correct_answer_box()).to_have_text(
            str(question["right_answers"])
        )
        expect(practice.get_numeric_marked_wrong()).to_have_count(0)
    else:
        expect(practice.get_correct_options()).to_have_count(1)
        expect(practice.get_wrong_options()).to_have_count(0)
    expect(practice.get_primary_button()).to_have_text("Next")

    assert practice.answered_wrong() is False
    assert "tq-dot-skipped" in practice.get_strip_dot_class(0)


def test_the_explanation_opens_once_the_question_is_answered(question_screen):
    """The same button that passed on the question offers its explanation
    afterwards."""
    practice, _, served = question_screen

    expect(practice.get_dont_know_button()).to_have_text("I don't know")

    answer(practice, served, CORRECT)

    expect(practice.get_explanation_button()).to_have_text("Explanation")

    practice.get_explanation_button().click()

    expect(practice.get_explanation_body()).to_be_visible()

    # A typed question has no option to pick out, so the explanation spells
    # its answer out instead.
    question = first_question(served)
    if is_typed(question):
        expect(practice.get_correct_answer_box()).to_have_text(
            str(question["right_answers"])
        )


# ---------------------------------------------------------------------------
# Moving through the set
# ---------------------------------------------------------------------------

def test_next_moves_to_the_following_question(long_question_screen):
    practice, _, served = long_question_screen
    first = practice.get_question_text()

    answer(practice, served, CORRECT)
    practice.next_question()
    practice.wait_for_next_question()

    expect(practice.get_primary_button()).to_have_text("Submit")
    expect(practice.get_options().first).to_be_visible()

    assert practice.get_question_text() != first
    assert "tq-dot-current" in practice.get_strip_dot_class(1)


def test_the_strip_records_the_question_that_was_answered(long_question_screen):
    """A question that has been answered is no longer drawn as unvisited."""
    practice, _, served = long_question_screen

    assert "tq-dot-not_visited" in practice.get_strip_dot_class(1)

    answer(practice, served, CORRECT)
    practice.next_question()
    practice.wait_for_next_question()

    assert "tq-dot-not_visited" not in practice.get_strip_dot_class(0)


def test_finishing_the_practice_shows_the_result(question_screen):
    """The result is what the set ends on, once every question in it has been
    answered. How many that is comes from the strip rather than from what the
    setup screen was asked for: a topic is only offered the set sizes it can
    fill, so a request for one question is met with the smallest it has."""
    practice, _, served = question_screen
    total = practice.question_total()

    for number in range(total):
        answer(practice, served, CORRECT)
        practice.next_question()
        if number < total - 1:
            practice.wait_for_next_question()

    practice.wait_for_result()

    expect(practice.get_result_title()).to_be_visible()
    expect(practice.get_result_message()).not_to_be_empty()
    expect(practice.get_result_stats()).to_be_visible()
    expect(practice.get_close_button()).to_be_enabled()

    stats = practice.get_result_stat_values()
    assert set(stats) == {"Correct", "I don't know", "Wrong"}
    assert sum(stats.values()) == practice.get_result_stat_total()


# ---------------------------------------------------------------------------
# Coming back to a practice
# ---------------------------------------------------------------------------

def test_reloading_a_practice_returns_to_its_rules_screen(question_screen):
    """The set is kept - the route still names the same task - but the screen
    is handed back at the rules rather than at the question that was open, so
    a reload is a restart of the set rather than a resume."""
    practice, practised, _ = question_screen
    url = practice.page.url

    practice.page.reload(wait_until="domcontentloaded")

    expect(practice.get_take_test_button()).to_be_visible()
    expect(practice.get_title()).to_have_text(practised["topic"])
    expect(practice.get_answer_controls()).to_have_count(0)

    assert practice.page.url == url


# ---------------------------------------------------------------------------
# API verification
# ---------------------------------------------------------------------------

def test_the_practice_is_created_for_the_topic_that_was_picked(page):
    """The task the picker makes carries the topic it was made from, and the
    set is then served for that task."""
    with page.expect_response(lambda r: CREATE_API in r.url) as created:
        practice, practised, served = start_practice(page)

    # Creating the task answers 201, not 200.
    assert created.value.status == 201
    task = created.value.json()["task"]

    # The API pads topic titles with a trailing space; the picker shows them
    # trimmed.
    assert task["topic_title"].strip() == practised["topic"]
    assert task["questions_count"] == int(practice.get_question_total().inner_text())
    assert task["is_completed"] is False
    assert str(task["id"]) in page.url, (
        f"the route does not carry the task that was created: {page.url}"
    )


def test_the_question_on_screen_matches_the_quiz_api(question_screen):
    """The question, and every option under it, is what the set was served."""
    practice, _, served = question_screen

    assert served, "the set was served no questions payload"
    payload = served[0]
    first = payload["questions"][0]

    assert len(payload["questions"]) == practice.question_total()
    assert practice.get_options().count() == first["no_of_options"]
    assert practice.get_options().count() == len(first["options"])

    assert [signature(source) for source in practice.get_option_sources()] == [
        signature(option["value"]) for option in first["options"]
    ]

    # A typed question is served as one, and its box takes the kind of number
    # it was served for: a whole one, or a decimal.
    if is_typed(first):
        expect(practice.get_numeric_input()).to_have_attribute(
            "inputmode", TYPED_INPUTS[first["input_type"]]
        )
    else:
        expect(practice.get_numeric_input()).to_have_count(0)

    # Read back with each typeset formula swapped for its source, as the options
    # are: the rendered maths is nothing like the markup it was served as.
    shown = signature(practice.get_question_source())
    assert shown == signature(first["question_description"])


def test_the_marking_follows_the_right_answer_the_api_served(question_screen):
    """The answer the payload names as right is the one the screen marks."""
    practice, _, served = question_screen
    first = first_question(served)

    if is_typed(first):
        typed = answer(practice, served, CORRECT)

        assert typed in right_answers(first)
        expect(practice.get_numeric_input()).to_have_value(typed)
        expect(practice.get_numeric_marked_correct()).to_have_count(1)
        return

    right = [int(n) - 1 for n in re.findall(r"\d+", str(first["right_answers"]))]

    answer(practice, served, CORRECT)

    marked = [
        index
        for index in range(practice.get_options().count())
        if "tq-opt-correct" in (
            practice.get_option(index).get_attribute("class") or ""
        )
    ]

    assert marked == right


def test_the_answer_is_sent_to_the_submit_api(question_screen):
    """Answering posts the choice that was made, against the question it was
    made on.

    A submit that does not end the set is answered with an acknowledgement
    rather than a tally; the tally comes with the last one, and what it pays
    is checked in test_daily_task_coins.py."""
    practice, _, served = question_screen
    first = first_question(served)
    right = re.findall(r"\d+", str(first["right_answers"]))

    with practice.page.expect_response(lambda r: SUBMIT_API in r.url) as sent:
        given = answer(practice, served, CORRECT)

    assert sent.value.status == 200

    posted = sent.value.request.post_data_json
    assert posted["question_id"] == first["id"]
    if is_typed(first):
        # A typed answer is posted as it was typed.
        assert posted["answer"] == given
    else:
        assert re.findall(r"\d+", str(posted["answer"])) == right
    assert posted["task_id"] == int(re.search(r"/(\d+)\?", practice.page.url).group(1))
    assert posted["completed"] is (practice.question_total() == 1)
    assert sent.value.json()
