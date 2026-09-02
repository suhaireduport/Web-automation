"""The Mistake Book, the third section of the Question Library.

The mistake these tests read is made the way a student makes one: a quick
practice reached from Home, a wrong answer, the practice carried through to its
result. The section is then checked for that same question.

Which option is the wrong one is not known before the answer is marked, so the
practice is asked for the fewest questions the topic will allow and every one
of them is answered; whichever came back wrong is what the tests then look for.

Unlike a bookmark, a mistake cannot be taken back: the run leaves one behind.
"""
import re

import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.mistake_book_page import (
    MistakeBookPage,
    MistakeQuestionsPage,
    MistakeQuestionPage,
)
from pages.practice_page import start_quick_practice
from pages.question_library_page import QuestionLibraryPage
from pages.question_library_section_page import (
    normalise,
    read_section_count,
    searchable_snippet,
)

MOBILE = "8893963137"

HOME_URL = "https://eduport-react.pages.dev/"
QUESTION_LIBRARY_URL = QuestionLibraryPage.URL
MISTAKE_BOOK_URL = MistakeBookPage.URL

SECTION_CARD = "Mistake Book"

# How many practices to run before giving up on getting a question wrong.
ATTEMPTS = 2

NO_QUESTIONS = (
    "No topic on this account has an unpractised question left, so there is "
    "nothing to answer wrong."
)
NEVER_WRONG = (
    f"{ATTEMPTS} practices were answered correctly throughout, so no mistake "
    "was made to check the Mistake Book with."
)


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture(scope="session")
def _mistake_state():
    return {}


@pytest.fixture(scope="session")
def mistaken(login_session, _mistake_state):
    """Answer a practice question wrong, once for the whole run.

    Subject -> topic -> topic quiz -> quick practice -> open question ->
    answer wrong -> on to the result. Which option is the wrong one only comes
    out with the marking, so every question of the set is answered and what
    came back is read afterwards; the practice is short because the setup
    screen is asked for the fewest questions it offers.

    What the practice showed is recorded rather than asserted, because the
    practice is over by the time the tests run."""
    if "reason" in _mistake_state:
        pytest.skip(_mistake_state["reason"])
    if "question" in _mistake_state:
        return _mistake_state

    page = login_session(MOBILE)
    before = read_section_count(page.context, SECTION_CARD)

    for attempt in range(ATTEMPTS):
        page.goto(HOME_URL, wait_until="domcontentloaded")
        practice, practised = start_quick_practice(page)
        if practice is None:
            _mistake_state["reason"] = NO_QUESTIONS
            pytest.skip(NO_QUESTIONS)

        total = practice.question_total()
        wrong = []
        for index in range(total):
            question = practice.get_question_text()
            options = practice.get_option_text_values()
            choice = index % practice.get_options().count()

            practice.select_option(choice)
            practice.submit()
            if practice.answered_wrong():
                wrong.append(
                    {
                        "question": question,
                        "options": options,
                        "marked_option_class": practice.get_option(
                            choice
                        ).get_attribute("class"),
                        "palette_dot_class": practice.get_strip_dot_class(index),
                    }
                )

            practice.next_question()
            if index < total - 1:
                practice.wait_for_next_question()

        practice.wait_for_result()
        result = normalise(practice.get_result_stats().inner_text())
        practice.close_result()

        if wrong:
            _mistake_state.update(practised)
            _mistake_state.update(wrong[0])
            _mistake_state.update(
                count_before=before,
                wrong_answers=len(wrong),
                questions_asked=total,
                result=result,
            )
            return _mistake_state

    _mistake_state["reason"] = NEVER_WRONG
    pytest.skip(NEVER_WRONG)


@pytest.fixture
def question_library(mistaken, page):
    """Opened the way a student reaches it, from the Home resources."""
    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()
    home_page.get_question_library().scroll_into_view_if_needed()
    home_page.get_question_library().click()
    page.wait_for_url(QUESTION_LIBRARY_URL)

    library = QuestionLibraryPage(page)
    library.wait_for_loaded()
    return library


@pytest.fixture
def mistake_book(page, question_library):
    question_library.open_card(SECTION_CARD)
    page.wait_for_url(MISTAKE_BOOK_URL)

    mistake_book = MistakeBookPage(page)
    mistake_book.wait_for_loaded()
    return mistake_book


@pytest.fixture
def mistaken_subject(mistaken, mistake_book):
    """The section showing the subject the wrong answer was given in."""
    mistake_book.open_subject(mistaken["subject"])
    return mistake_book


@pytest.fixture
def mistake_questions(page, mistaken, mistaken_subject):
    """The mistaken questions of the chapter that was practised."""
    index = mistaken_subject.find_chapter(mistaken["chapter"])
    assert index is not None, f"{mistaken['chapter']} is not listed in the Mistake Book"

    mistaken_subject.open_chapter(index)

    questions = MistakeQuestionsPage(page)
    questions.wait_for_loaded()
    return questions


@pytest.fixture
def mistaken_question(page, mistaken, mistake_questions):
    """The very question that was answered wrong, opened."""
    index = mistake_questions.find_question(mistaken["question"])
    assert index is not None, "the question answered wrong is not listed"

    mistake_questions.open_question(index)

    question = MistakeQuestionPage(page)
    question.wait_for_loaded()
    return question


# ---------------------------------------------------------------------------
# The practice that made the mistake
# ---------------------------------------------------------------------------

def test_the_practice_marked_the_answer_wrong(mistaken):
    assert "tq-opt-wrong" in mistaken["marked_option_class"]


def test_the_practice_marked_the_question_wrong_in_the_palette(mistaken):
    assert "tq-dot-wrong" in mistaken["palette_dot_class"]


def test_the_practice_result_counted_the_wrong_answers(mistaken):
    expected = f"{mistaken['wrong_answers']}/{mistaken['questions_asked']} Wrong"

    assert expected in mistaken["result"]


# ---------------------------------------------------------------------------
# From the practice to the section
# ---------------------------------------------------------------------------

def test_the_wrongly_answered_question_reaches_the_mistake_book(
    mistaken, mistake_questions
):
    index = mistake_questions.find_question(mistaken["question"])

    assert index is not None, "the question answered wrong is not in the Mistake Book"
    expect(mistake_questions.get_question(index)).to_be_visible()


def test_the_mistake_is_filed_under_the_subject_it_was_practised_in(
    mistaken, mistaken_subject
):
    expect(mistaken_subject.get_tab(mistaken["subject"])).to_have_count(1)
    expect(mistaken_subject.get_active_tab()).to_contain_text(mistaken["subject"])


def test_the_mistake_is_filed_under_the_chapter_it_was_practised_in(
    mistaken, mistake_questions
):
    expect(mistake_questions.get_title()).to_have_text(mistaken["chapter"])


def test_the_library_card_counts_the_new_mistakes(mistaken, question_library):
    """Every question the practice got wrong is one more in the book."""
    after = int(question_library.get_card_count(SECTION_CARD).inner_text().strip())

    assert after == mistaken["count_before"] + mistaken["wrong_answers"]


def test_opening_the_mistake_shows_the_same_question(mistaken, mistaken_question):
    assert mistaken_question.get_question_text() == mistaken["question"]
    assert mistaken_question.get_option_text_values() == mistaken["options"]


def test_the_question_is_marked_as_a_wrong_attempt(mistaken_question):
    """Recent attempts is how the screen says the question was got wrong."""
    expect(mistaken_question.get_recent_attempts_label()).to_have_text(
        "Recent attempts:"
    )
    expect(mistaken_question.get_wrong_attempts().first).to_be_visible()

    assert mistaken_question.get_wrong_attempts().count() >= 1


# ---------------------------------------------------------------------------
# The section screen
# ---------------------------------------------------------------------------

def test_the_section_opens_from_the_question_library(page, mistake_book):
    expect(page).to_have_url(MISTAKE_BOOK_URL)
    expect(mistake_book.get_page()).to_be_visible()
    expect(mistake_book.get_title()).to_have_text(SECTION_CARD)


def test_the_section_offers_back_and_search(mistake_book):
    expect(mistake_book.get_back_button()).to_be_enabled()
    expect(mistake_book.get_search_button()).to_be_enabled()


def test_back_returns_to_the_question_library(page, mistake_book):
    mistake_book.click_back()

    expect(page).to_have_url(QUESTION_LIBRARY_URL)
    expect(QuestionLibraryPage(page).get_title()).to_have_text("Question Library")


def test_subject_tabs_count_the_chapters_they_hold(mistake_book):
    """A tab reads "Chemistry (1)", where the number is chapters and not
    questions: one chapter holding four mistakes still reads (1)."""
    assert mistake_book.get_tabs().count() >= 1

    for index in range(mistake_book.get_tabs().count()):
        mistake_book.click_tab(index)

        expect(mistake_book.get_active_tab()).to_have_count(1)
        assert mistake_book.chapter_count() == mistake_book.get_tab_count(index)


def test_chapters_show_a_number_a_title_and_a_count(mistake_book):
    total = mistake_book.chapter_count()

    expect(mistake_book.get_chapter_numbers()).to_have_count(total)
    expect(mistake_book.get_chapter_titles()).to_have_count(total)

    for index in range(total):
        expect(mistake_book.get_chapter_titles().nth(index)).not_to_be_empty()
        expect(mistake_book.get_chapter_mistake_count(index)).to_have_text(
            re.compile(r"^\d+$")
        )


def test_a_chapter_count_matches_the_questions_it_lists(page, mistake_book):
    expected = int(mistake_book.get_chapter_mistake_count(0).inner_text().strip())

    mistake_book.open_chapter(0)
    questions = MistakeQuestionsPage(page)
    questions.wait_for_loaded()

    assert questions.question_count() == expected


def test_the_section_total_matches_the_library_card(page, question_library):
    """Every chapter of every subject added up is what the card counts."""
    total = int(question_library.get_card_count(SECTION_CARD).inner_text().strip())

    question_library.open_card(SECTION_CARD)
    page.wait_for_url(MISTAKE_BOOK_URL)
    mistake_book = MistakeBookPage(page)
    mistake_book.wait_for_loaded()

    counted = 0
    for index in range(mistake_book.get_tabs().count()):
        mistake_book.click_tab(index)
        mistake_book.chapter_count()
        counted += mistake_book.chapter_question_total()

    assert counted == total


def test_search_narrows_the_chapter_list(mistaken, mistake_book):
    """Search leaves the section behind for the subject's own chapter search,
    so what it lists is chapters, not only mistaken ones."""
    mistake_book.open_subject(mistaken["subject"])
    mistake_book.click_search()
    mistake_book.wait_for_search_loaded()

    expect(mistake_book.get_search_input()).to_be_visible()

    mistake_book.search(mistaken["chapter"][:12])

    expect(mistake_book.get_search_results().first).to_be_visible()
    expect(mistake_book.get_search_result_titles().first).to_contain_text(
        mistaken["chapter"][:12]
    )


def test_search_says_when_nothing_matches(mistaken, mistake_book):
    # On the subject the flow used: a subject with nothing attempted serves an
    # entirely blank search screen, which is not the state under test.
    mistake_book.open_subject(mistaken["subject"])
    mistake_book.click_search()
    mistake_book.wait_for_search_loaded()
    mistake_book.search("zzzznomatch")

    expect(mistake_book.get_no_search_result()).to_be_visible()
    expect(mistake_book.get_no_search_result_title()).to_have_text(
        "No Matching Search Result"
    )
    expect(mistake_book.get_search_results()).to_have_count(0)


# ---------------------------------------------------------------------------
# The questions of a chapter
# ---------------------------------------------------------------------------

def test_the_chapter_lists_its_mistaken_questions(mistake_questions):
    total = mistake_questions.question_count()

    assert total > 0
    expect(mistake_questions.get_question_numbers()).to_have_count(total)


def test_every_listed_question_can_be_dropped_from_the_book(mistake_questions):
    """The control the other sections do not have. It is not used: dropping a
    question is not something the account can be given back."""
    total = mistake_questions.question_count()

    expect(mistake_questions.get_remove_buttons()).to_have_count(total)
    expect(mistake_questions.get_remove_button(0)).to_have_attribute(
        "aria-label", "Remove from Mistake Book"
    )


def test_every_listed_question_offers_a_bookmark(mistake_questions):
    total = mistake_questions.question_count()

    expect(mistake_questions.get_bookmark_buttons()).to_have_count(total)
    expect(mistake_questions.get_bookmark_button(0)).to_have_attribute(
        "aria-label", re.compile("bookmark")
    )


def test_the_questions_screen_offers_search_and_a_topic_filter(mistake_questions):
    expect(mistake_questions.get_back_button()).to_be_enabled()
    expect(mistake_questions.get_search_button()).to_be_enabled()
    expect(mistake_questions.get_filter_button()).to_be_enabled()


def test_searching_the_questions_narrows_the_list(mistaken, mistake_questions):
    snippet = searchable_snippet(mistaken["question"])
    assert snippet, "the question has no plain words to search with"

    mistake_questions.click_search()
    mistake_questions.search(snippet)

    expect(mistake_questions.get_questions().first).to_be_visible()
    assert mistake_questions.find_question(mistaken["question"]) is not None


def test_the_topic_filter_lists_the_topics_that_were_got_wrong(
    mistaken, mistake_questions
):
    mistake_questions.click_filter()

    expect(mistake_questions.get_filter_sheet()).to_be_visible()
    expect(mistake_questions.get_filter_title()).to_have_text("Filter By Topic")
    assert mistaken["topic"] in mistake_questions.get_filter_option_names()

    mistake_questions.close_filter()

    expect(mistake_questions.get_filter_overlay()).to_have_count(0)


# ---------------------------------------------------------------------------
# A single mistaken question
# ---------------------------------------------------------------------------

def test_the_question_opens_with_its_options(mistaken_question):
    expect(mistaken_question.get_page()).to_be_visible()
    expect(mistaken_question.get_question()).not_to_be_empty()
    expect(mistaken_question.get_choose_label()).to_be_visible()

    total = mistaken_question.get_options().count()
    assert total >= 2
    expect(mistaken_question.get_option_numbers()).to_have_count(total)


def test_the_question_offers_a_note(mistaken_question):
    mistaken_question.click_note()

    expect(mistaken_question.get_note_editor()).to_be_visible()
    expect(mistaken_question.get_note_save_button()).to_be_visible()

    mistaken_question.get_note_close_button().click()

    expect(mistaken_question.get_note_editor()).to_have_count(0)


def test_the_question_offers_a_bookmark(mistaken_question):
    expect(mistaken_question.get_bookmark_button()).to_be_enabled()
    expect(mistaken_question.get_bookmark_button()).to_have_attribute(
        "aria-label", re.compile("bookmark")
    )


def test_view_solution_waits_for_an_answer(mistaken_question):
    expect(mistaken_question.get_view_solution_button()).to_be_visible()
    expect(mistaken_question.get_view_solution_button()).to_be_disabled()

    assert mistaken_question.is_solution_available() is False


def test_answering_the_question_enables_view_solution(mistaken_question):
    mistaken_question.select_option(0)

    expect(mistaken_question.get_option(0)).to_have_class(
        re.compile("qlr-opt-selected")
    )
    expect(mistaken_question.get_view_solution_button()).to_be_enabled()

    assert mistaken_question.is_solution_available()


def test_the_filter_offers_every_answer_state(mistaken_question):
    mistaken_question.click_filter()

    expect(mistaken_question.get_filter_sheet()).to_be_visible()
    assert mistaken_question.get_filter_names() == MistakeQuestionPage.FILTERS

    for name in MistakeQuestionPage.FILTERS:
        expect(mistaken_question.get_filter_row(name)).to_have_text(
            re.compile(re.escape(name) + r"\s*\(\d+\)")
        )


@pytest.mark.parametrize("state", MistakeQuestionPage.FILTERS)
def test_every_filter_can_be_selected(mistaken_question, state):
    mistaken_question.click_filter()
    mistaken_question.select_filter(state)

    expect(mistaken_question.get_active_filter()).to_contain_text(state)


def test_the_wrong_filter_counts_the_answer_that_was_got_wrong(mistaken_question):
    mistaken_question.click_filter()

    assert mistaken_question.get_filter_count("Wrong") >= 1


# ---------------------------------------------------------------------------
# API verification
#
# The section is served by one call keyed on its type. Navigated directly with
# nothing but a signed in page, so this reads whatever the account already
# holds rather than the mistake the fixtures above make.
# ---------------------------------------------------------------------------

MISTAKE_PROGRESS_API = "**/api/v3/question-bank/progress?type=mistaken"


def test_mistake_book_chapters_match_the_progress_api(page):
    with page.expect_response(MISTAKE_PROGRESS_API) as answer:
        page.goto(MISTAKE_BOOK_URL, wait_until="domcontentloaded")
    assert answer.value.status == 200, f"progress answered {answer.value.status}"
    subjects = answer.value.json()["subjects"]

    mistake_book = MistakeBookPage(page)
    mistake_book.wait_for_loaded()

    if not subjects:
        expect(mistake_book.get_empty_state()).to_be_visible()
        return

    expect(mistake_book.get_tabs()).to_have_count(len(subjects))
    for index, subject in enumerate(subjects):
        expect(mistake_book.get_tabs().nth(index)).to_contain_text(
            subject["title"].strip()
        )
        assert mistake_book.get_tab_count(index) == len(subject["chapters"])

    # Chapter titles are numbered on this screen - "1. Laws of Motion" -
    # where the payload carries the title on its own.
    chapters = subjects[0]["chapters"]
    shown = [
        re.sub(r"^\d+\.\s*", "", text)
        for text in mistake_book.get_chapter_title_texts()
    ]

    assert shown == [chapter["title"].strip() for chapter in chapters]
    for index, chapter in enumerate(chapters):
        expect(mistake_book.get_chapter_mistake_count(index)).to_have_text(
            str(chapter["question_count"])
        )
