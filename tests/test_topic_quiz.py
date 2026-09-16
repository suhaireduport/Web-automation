"""The topic quiz: the quiz a topic carries, opened from the topic list.

A topic that carries quizzes lists one row per quiz under its subtopics -
Problem Based Questions, Quick Practice Questions, or both - and the row opens
the quiz on a route of its own:

    /home/subject/<id>/<subject>/topics/<chapter>/topic_quiz/<topic>/<title>?qt=

qt names which quiz is being taken, numbered the way the chapter call numbers
it in a topic's quiz_types: 1 for problem based, 5 for quick practice. That one
number decides the rest of the screen - the call the questions come from, what
the quiz calls itself, and what it says about the way it behaves - so the rows,
the route and the screen are all held against the chapter call.

Nothing here answers a question. Submitting an answer is the first thing that
writes: it records the answer against the topic and moves the coin balance, and
a topic's quiz cannot be taken twice. So these tests go as far as the first
question and no further, and every topic is left as it was found.

What is deliberately not here: how a quiz is answered and what it pays, which
is covered on the same .tq-* screen against practice quizzes in
test_quiz_problem_based.py and test_quiz_quick_practice.py, and the subtopic's
own checkpoint quiz, which is test_quiz_checkpoint.py.
"""
import pytest
from playwright.sync_api import expect

from conftest import HOME_URL, STUDENT_MOBILE
from pages.chapter_page import ChapterPage
from pages.home_page import HomePage
from pages.question_library_section_page import normalise
from pages.topic_page import (
    QUIZ_APIS,
    QUIZ_MODES,
    QUIZ_NOTES,
    QUIZ_ROW_LABELS,
    QUIZ_RULES_HEADINGS,
    REWARD_ROWS,
    TopicPage,
    TopicQuizPage,
)

# How much of the course is walked when hunting for a topic that carries a
# quiz. A course runs to far more subjects and chapters than the answer needs.
SUBJECT_PROBE_LIMIT = 6
CHAPTER_PROBE_LIMIT = 3

CHAPTER_CONTENT_API = "**/api/v3/syllabus/chapter-content/?*"

# Where an answer would be sent. Listened for to prove none is.
SUBMIT_API = "/study-quiz/submit/"

# What the intro publishes an answer is worth, in the order it lays them out.
SCORING = ["Correct +4", "I don't know +0", "Wrong -1"]


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(STUDENT_MOBILE)


@pytest.fixture(scope="session")
def quiz_survey(login_session):
    """A chapter whose topics carry quizzes, looked at once for the whole run.

    Which chapters carry quizzes is in no list the app serves up front - it
    comes from opening the chapter - so the first few subjects and the first
    few unlocked chapters of each are walked until one turns up. Hands back the
    chapter's topic list, the call it was drawn from, and the quizzes on it
    nobody has finished: a finished quiz opens on Review rather than on Take
    test, and those are not the same screen."""
    page = login_session(STUDENT_MOBILE)

    home = HomePage(page)
    home.get_subjects().first.wait_for(timeout=30000)
    subjects = home.get_subject_names()
    looked_at = []

    for index in range(min(len(subjects), SUBJECT_PROBE_LIMIT)):
        page.goto(HOME_URL, wait_until="domcontentloaded")
        home.get_subjects().first.wait_for(timeout=30000)
        home.open_subject(index)

        chapters = ChapterPage(page)
        chapters.wait_for_chapters_loaded()
        subject_url = page.url
        unlocked = chapters.get_unlocked_chapters().count()
        looked_at.append(f"{subjects[index]} ({unlocked} unlocked)")

        for chapter in range(min(unlocked, CHAPTER_PROBE_LIMIT)):
            if chapter:
                page.goto(subject_url, wait_until="domcontentloaded")
                chapters.wait_for_chapters_loaded()

            with page.expect_response(CHAPTER_CONTENT_API) as answer:
                chapters.get_unlocked_chapters().nth(chapter).click()
            assert answer.value.status == 200, (
                f"chapter-content answered {answer.value.status}"
            )
            body = answer.value.json()
            TopicPage(page).wait_for_topics_loaded()

            unfinished = [
                (topic, quiz)
                for topic in body["topics"]
                for quiz in sorted(topic.get("quiz_types") or [])
                if quiz not in (topic.get("completed_quizzes") or [])
            ]
            if unfinished:
                return {"topics_url": page.url, "body": body, "quizzes": unfinished}

    pytest.skip(
        "No topic in the chapters looked at carries a quiz that is still open: "
        + ", ".join(looked_at)
    )


def open_topics(page, survey):
    """The topic list of the chapter the survey found, with every topic open so
    that the quiz rows are on screen."""
    page.goto(survey["topics_url"], wait_until="domcontentloaded")
    topics = TopicPage(page)
    topics.wait_for_topics_loaded()
    topics.expand_all_topics()
    return topics


@pytest.fixture
def topics(page, quiz_survey):
    return open_topics(page, quiz_survey)


def a_quiz(survey, kind=None):
    """A topic and one of its unfinished quizzes, of a given kind if asked."""
    for topic, quiz in survey["quizzes"]:
        if kind is None or quiz == kind:
            return topic, quiz
    return None, None


def kinds_carried(survey):
    """The quizzes this chapter has open, lowest numbered first."""
    return sorted({quiz for _, quiz in survey["quizzes"]})


@pytest.fixture
def quiz(quiz_survey):
    """The first unfinished quiz the survey found, as (topic, quiz type)."""
    return a_quiz(quiz_survey)


def open_quiz(topics, topic, kind):
    """Open a topic's quiz the way a student does: from its row."""
    topics.open_quiz(normalise(topic["title"]), QUIZ_ROW_LABELS[kind])
    quiz_page = TopicQuizPage(topics.page)
    quiz_page.wait_for_intro()
    return quiz_page


# ---------------------------------------------------------------------------
# 1. The rows on the topic list  (API + UI)
# ---------------------------------------------------------------------------

def test_the_quiz_rows_are_the_quizzes_the_chapter_call_lists(topics, quiz_survey):
    """A topic lists a row per quiz the call files under it, named for which
    quiz it is, and a topic the call gives no quiz lists none."""
    expected = {
        normalise(topic["title"]): [
            QUIZ_ROW_LABELS[quiz] for quiz in sorted(topic["quiz_types"])
        ]
        for topic in quiz_survey["body"]["topics"]
        if topic.get("quiz_types")
    }
    shown = {
        normalise(title): rows
        for title, rows in topics.get_quiz_rows_by_topic().items()
    }

    assert shown == expected


# ---------------------------------------------------------------------------
# 2. Opening the quiz
# ---------------------------------------------------------------------------

def test_a_quiz_row_opens_the_topic_quiz_on_its_own_route(page, topics, quiz):
    """The route names the topic the quiz belongs to and carries the quiz it is
    in qt."""
    topic, kind = quiz

    quiz_page = open_quiz(topics, topic, kind)

    expect(page).to_have_url(TopicQuizPage.URL_PATTERN)
    assert TopicQuizPage.route_parts(page.url) == (topic["id"], kind)
    expect(quiz_page.get_title()).to_have_text(normalise(topic["title"]))


def test_the_quiz_asks_for_the_questions_of_the_quiz_the_row_names(page, topics, quiz):
    """Each quiz has its own call, and the one the row opens is the one asked
    for, against that topic."""
    topic, kind = quiz

    with page.expect_response(lambda response: QUIZ_APIS[kind] in response.url) as answer:
        topics.open_quiz(normalise(topic["title"]), QUIZ_ROW_LABELS[kind])

    assert answer.value.status == 200, (
        f"{QUIZ_APIS[kind]} answered {answer.value.status}"
    )
    assert f"topic_id={topic['id']}" in answer.value.url, answer.value.url


def test_the_intro_counts_the_questions_the_call_served(page, topics, quiz):
    """The number on the intro is how many questions came back, not a figure of
    its own."""
    topic, kind = quiz

    with page.expect_response(lambda response: QUIZ_APIS[kind] in response.url) as answer:
        topics.open_quiz(normalise(topic["title"]), QUIZ_ROW_LABELS[kind])
    served = answer.value.json()["questions"]

    quiz_page = TopicQuizPage(page)
    quiz_page.wait_for_intro()
    expect(quiz_page.get_question_total()).to_have_text(str(len(served)))
    expect(quiz_page.get_take_test_button()).to_have_text("Take test")


def test_the_intro_names_the_quiz_and_how_it_behaves(page, quiz_survey):
    """Each quiz calls itself by name and says how it treats a wrong answer.
    Every kind the chapter carries is opened."""
    for kind in kinds_carried(quiz_survey):
        topic, _ = a_quiz(quiz_survey, kind)
        topics = open_topics(page, quiz_survey)

        quiz_page = open_quiz(topics, topic, kind)

        expect(quiz_page.get_subtitle()).to_have_text(QUIZ_MODES[kind])
        expect(quiz_page.get_info_box()).to_contain_text(QUIZ_NOTES[kind])


def test_the_intro_publishes_what_an_answer_is_worth(topics, quiz):
    topic, kind = quiz

    quiz_page = open_quiz(topics, topic, kind)

    expect(quiz_page.get_scoring()).to_have_count(len(SCORING))
    assert [
        normalise(text) for text in quiz_page.get_scoring().all_inner_texts()
    ] == SCORING


def test_the_rules_sheet_explains_the_quiz(page, quiz_survey):
    """The help button opens the rules of whichever quiz is being taken, with
    what each answer pays underneath."""
    for kind in kinds_carried(quiz_survey):
        topic, _ = a_quiz(quiz_survey, kind)
        topics = open_topics(page, quiz_survey)
        quiz_page = open_quiz(topics, topic, kind)

        quiz_page.open_rules()

        expect(quiz_page.get_rules_heading()).to_have_text(QUIZ_RULES_HEADINGS[kind])
        expect(quiz_page.get_rules_note()).not_to_be_empty()
        expect(quiz_page.get_rules_rewards()).to_have_count(REWARD_ROWS)

        quiz_page.close_rules()
        expect(quiz_page.get_rules_overlay()).to_have_count(0)
        expect(quiz_page.get_take_test_button()).to_be_visible()


# ---------------------------------------------------------------------------
# 3. The first question
#
# Taken as far as the question and no further: an answer is a write, and a
# topic's quiz cannot be taken again.
# ---------------------------------------------------------------------------

def test_taking_the_test_opens_the_first_question(page, topics, quiz):
    topic, kind = quiz
    quiz_page = open_quiz(topics, topic, kind)
    submitted = []
    page.on(
        "request",
        lambda request: submitted.append(request.url) if SUBMIT_API in request.url else None,
    )

    quiz_page.take_test()

    expect(quiz_page.get_quiz_title()).to_have_text(normalise(topic["title"]))
    expect(quiz_page.get_strip_dots().first).to_be_visible()
    expect(quiz_page.get_question()).to_be_visible()
    assert quiz_page.get_answer_controls().count() >= 1
    expect(quiz_page.get_primary_button()).to_have_text("Submit")
    expect(quiz_page.get_dont_know_button()).to_have_text("I don't know")
    expect(quiz_page.get_bookmark_button()).to_be_visible()
    expect(quiz_page.get_note_button()).to_be_visible()
    expect(quiz_page.get_palette_button()).to_be_visible()
    expect(quiz_page.get_report_button()).to_be_visible()

    assert submitted == [], "opening the question sent an answer"


def test_a_question_asks_to_be_answered_the_way_it_is_built(page, topics, quiz):
    """A question is answered either by choosing options or by typing, and the
    card says which: options carry how many to choose, a numeric one carries a
    box."""
    topic, kind = quiz
    quiz_page = open_quiz(topics, topic, kind)

    quiz_page.take_test()

    if quiz_page.get_options().count():
        expect(quiz_page.get_choose_label()).to_be_visible()
        assert int(quiz_page.get_choose_count().inner_text().strip()) >= 1
        assert quiz_page.get_numeric_input().count() == 0
    else:
        expect(quiz_page.get_numeric_input()).to_be_visible()
        expect(quiz_page.get_numeric_input()).to_have_value("")


# ---------------------------------------------------------------------------
# 4. Getting back out
# ---------------------------------------------------------------------------

def test_leaving_the_questions_returns_to_the_intro(page, topics, quiz):
    """Back from a question is not back out of the quiz: it returns to the
    intro, which is still on the same route."""
    topic, kind = quiz
    quiz_page = open_quiz(topics, topic, kind)
    quiz_page.take_test()
    route = page.url

    quiz_page.get_back_button().click()

    expect(quiz_page.get_take_test_button()).to_be_visible()
    expect(page).to_have_url(route)


def test_leaving_the_intro_returns_to_the_topic_list(page, topics, quiz, quiz_survey):
    topic, kind = quiz
    quiz_page = open_quiz(topics, topic, kind)

    quiz_page.get_back_button().click()

    expect(page).to_have_url(quiz_survey["topics_url"])
    topics.wait_for_topics_loaded()
