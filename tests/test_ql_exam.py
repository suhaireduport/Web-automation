"""Exams, the fourth section of the Question Library.

Where the other three sections file questions under a subject and a chapter,
this one files them under the exam they were met in and splits them across a
Bookmarks tab and an Exam Notes tab.

Nothing here is written from the Question Library. Both tabs are filled the way
a student fills them: an attempted exam is reopened from its result, a question
of it is bookmarked, another has a note saved on it, and the section is then
checked for those questions. Which exam and which question that was comes back
from the review rather than being written down here, because the papers on an
account differ from one to the next.

The setup runs once for the whole file through the session scoped
marked_questions fixture. Two exams are marked when the account has two
attempted, so that filtering by one of them has something to exclude; with only
one attempted exam the filter is still checked, but only for what it keeps.

The bookmarks are taken off again at the end. The note is left: there is no
control that deletes one, and a second run writes over it rather than adding to
it.
"""
import re

import pytest
from playwright.sync_api import expect

from pages.exam_page import ExamPage, ExamResultPage, ExamReviewPage
from pages.home_page import HomePage
from pages.question_library_exams_page import (
    ExamQuestionPage,
    ExamsSearchPage,
    ExamsSectionPage,
)
from pages.question_library_page import QuestionLibraryPage
from pages.question_library_section_page import searchable_snippet

MOBILE = "9876543210"

HOME_URL = "https://eduport-react.pages.dev/"
EXAMS_URL = ExamPage.URL
QUESTION_LIBRARY_URL = QuestionLibraryPage.URL
SECTION_URL = ExamsSectionPage.URL

# The card on the landing screen names the section in the plural; the screen it
# opens calls itself Exam.
SECTION_CARD = "Exams"
SECTION_TITLE = "Exam"

# The calls the marking is supposed to make. They are waited for rather than
# assumed: the screen flips its own control either way, so a click on its own
# proves nothing, and navigating away before the response lands cancels it.
ADD_API = "**/question-bank/bookmarks/add"
REMOVE_API = "**/question-bank/bookmarks/remove"
NOTE_API = "**/question-bank/notes/add"
API_TIMEOUT = 20000

NOTE_TEXT = "Revisit this one before the next attempt"

NO_ATTEMPTED_EXAM = (
    "This account has no attempted exam, so no exam question can be bookmarked "
    "or given a note. Attempt a past exam to give these tests something to read."
)


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


# ---------------------------------------------------------------------------
# Filling the section
# ---------------------------------------------------------------------------

def open_past_exams(page):
    """Home -> Exams -> Past."""
    page.goto(HOME_URL, wait_until="domcontentloaded")

    home_page = HomePage(page)
    home_page.get_exams_button().click()
    page.wait_for_url(EXAMS_URL)

    exams = ExamPage(page)
    exams.wait_for_exams_loaded()
    exams.click_past_tab()
    return exams


def open_exam_review(page, index):
    """The attempted exam at that position, opened at its first question."""
    exams = open_past_exams(page)
    title = exams.get_exam_title(index).inner_text().strip()
    exams.click_review(index)

    result = ExamResultPage(page)
    result.wait_for_loaded()
    result.open_question(1)

    review = ExamReviewPage(page)
    review.wait_for_loaded()
    return review, title


def mark_one_exam(page, index, with_note):
    """Bookmark a question of that exam, and give it a note when asked to.

    Hands back what was marked so the section can be checked for it: the exam
    it belongs to, the question itself and the options it was asked with."""
    review, title = open_exam_review(page, index)
    review.find_substantial_question()

    if not review.is_bookmarked():
        with page.expect_response(ADD_API, timeout=API_TIMEOUT) as added:
            review.click_bookmark()
        assert added.value.status == 200, f"bookmark answered {added.value.status}"
        page.locator(".erp-bookmark[aria-label='Remove bookmark']").wait_for()

    marked = {
        "exam": title,
        "question": review.get_question_text(),
        "options": review.get_option_text_values(),
        "bookmarked_in_review": review.is_bookmarked(),
    }

    if with_note:
        review.write_note(NOTE_TEXT)
        with page.expect_response(NOTE_API, timeout=API_TIMEOUT) as saved:
            review.get_note_save_button().click()
        assert saved.value.status == 200, f"note answered {saved.value.status}"
        review.get_note_sheet().wait_for(state="detached")
        marked["note"] = NOTE_TEXT

    return marked


@pytest.fixture(scope="session")
def _exam_state():
    return {}


@pytest.fixture(scope="session")
def marked_questions(login_session, _exam_state):
    """Bookmark and note exam questions, once for the whole run.

    Exams -> Past -> Review -> a question -> bookmark and note. A second
    attempted exam is marked as well when the account has one, so that the exam
    filter has more than a single exam to choose between."""
    if "reason" in _exam_state:
        pytest.skip(_exam_state["reason"])
    if _exam_state:
        yield _exam_state
        return

    page = login_session(MOBILE)
    exams = open_past_exams(page)

    attempted = [
        index
        for index in range(exams.exam_card_count())
        if exams.get_review_button(index).count() > 0
    ]
    if not attempted:
        _exam_state["reason"] = NO_ATTEMPTED_EXAM
        pytest.skip(NO_ATTEMPTED_EXAM)

    marked = [mark_one_exam(page, attempted[0], with_note=True)]
    if len(attempted) > 1:
        marked.append(mark_one_exam(page, attempted[1], with_note=False))

    _exam_state.update(noted=marked[0], marked=marked, exams=[one["exam"] for one in marked])

    yield _exam_state

    # Tidy up, best effort: removal is not what this file is about, and a
    # failure here must never fail a run.
    try:
        section = open_section(page)
        section.open_tab("Bookmarks")
        for one in marked:
            index = section.find_question(one["question"], one["exam"])
            if index is not None and section.is_bookmarked(index):
                with page.expect_response(REMOVE_API, timeout=API_TIMEOUT):
                    section.get_bookmark_button(index).click()
                section.wait_for_loaded()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Reaching the section
# ---------------------------------------------------------------------------

def open_section(page):
    """Home -> Question Library -> Exams, the way a student reaches it."""
    page.goto(HOME_URL, wait_until="domcontentloaded")

    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()
    home_page.get_question_library().scroll_into_view_if_needed()
    home_page.get_question_library().click()
    page.wait_for_url(QUESTION_LIBRARY_URL)

    library = QuestionLibraryPage(page)
    library.wait_for_loaded()
    library.open_card(SECTION_CARD)
    page.wait_for_url(SECTION_URL)

    section = ExamsSectionPage(page)
    section.wait_for_loaded()
    return section


@pytest.fixture
def question_library(page):
    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()
    home_page.get_question_library().scroll_into_view_if_needed()
    home_page.get_question_library().click()
    page.wait_for_url(QUESTION_LIBRARY_URL)

    library = QuestionLibraryPage(page)
    library.wait_for_loaded()
    return library


@pytest.fixture
def exams_section(page, marked_questions, question_library):
    question_library.open_card(SECTION_CARD)
    page.wait_for_url(SECTION_URL)

    section = ExamsSectionPage(page)
    section.wait_for_loaded()
    return section


@pytest.fixture
def bookmarks_tab(exams_section):
    exams_section.open_tab("Bookmarks")
    return exams_section


@pytest.fixture
def notes_tab(exams_section):
    exams_section.open_tab("Exam Notes")
    return exams_section


@pytest.fixture
def exam_question(page, marked_questions, notes_tab):
    """The question the note was written on, opened from the section."""
    index = notes_tab.find_question(
        marked_questions["noted"]["question"], marked_questions["noted"]["exam"]
    )
    assert index is not None, "the noted exam question is not listed"

    notes_tab.open_question(index)

    question = ExamQuestionPage(page)
    question.wait_for_loaded()
    return question


@pytest.fixture
def search(page, exams_section):
    exams_section.click_search()

    search = ExamsSearchPage(page)
    search.get_search_input().wait_for()
    return search


# ---------------------------------------------------------------------------
# Opening Exams
# ---------------------------------------------------------------------------

def test_exams_opens_from_the_question_library(page, exams_section):
    expect(page).to_have_url(SECTION_URL)
    expect(exams_section.get_page()).to_be_visible()
    expect(exams_section.get_header()).to_be_visible()


def test_exams_shows_its_title(exams_section):
    expect(exams_section.get_title()).to_have_text(SECTION_TITLE)


def test_exams_offers_back_search_and_the_exam_filter(exams_section):
    expect(exams_section.get_back_button()).to_be_enabled()
    expect(exams_section.get_search_button()).to_be_enabled()
    expect(exams_section.get_filter_button()).to_be_enabled()


def test_back_returns_to_the_question_library(page, exams_section):
    exams_section.click_back()

    expect(page).to_have_url(QUESTION_LIBRARY_URL)
    expect(QuestionLibraryPage(page).get_title()).to_have_text("Question Library")


# ---------------------------------------------------------------------------
# The two tabs
# ---------------------------------------------------------------------------

def test_exams_splits_its_questions_into_bookmarks_and_exam_notes(exams_section):
    expect(exams_section.get_tabs()).to_have_count(len(ExamsSectionPage.TABS))

    assert exams_section.get_tab_names() == ExamsSectionPage.TABS


def test_bookmarks_is_the_tab_in_force_to_begin_with(exams_section):
    expect(exams_section.get_active_tab()).to_have_count(1)
    expect(exams_section.get_active_tab()).to_have_text("Bookmarks")


@pytest.mark.parametrize("tab", ExamsSectionPage.TABS)
def test_each_tab_can_be_opened(exams_section, tab):
    exams_section.open_tab(tab)

    expect(exams_section.get_active_tab()).to_have_text(tab)


# ---------------------------------------------------------------------------
# From an exam to the Bookmarks tab
# ---------------------------------------------------------------------------

def test_the_review_marked_the_question_as_bookmarked(marked_questions):
    assert marked_questions["noted"]["bookmarked_in_review"] is True


def test_the_bookmarked_exam_question_is_listed_under_bookmarks(
    marked_questions, bookmarks_tab
):
    index = bookmarks_tab.find_question(
        marked_questions["noted"]["question"], marked_questions["noted"]["exam"]
    )

    assert index is not None, "the question bookmarked in the review is not listed"
    expect(bookmarks_tab.get_question(index)).to_be_visible()


def test_the_listed_question_names_the_exam_it_came_from(
    marked_questions, bookmarks_tab
):
    index = bookmarks_tab.find_question(
        marked_questions["noted"]["question"], marked_questions["noted"]["exam"]
    )

    expect(bookmarks_tab.get_exam_title(index)).to_have_text(
        marked_questions["noted"]["exam"]
    )


def test_the_listed_question_still_shows_as_bookmarked(
    marked_questions, bookmarks_tab
):
    index = bookmarks_tab.find_question(
        marked_questions["noted"]["question"], marked_questions["noted"]["exam"]
    )

    expect(bookmarks_tab.get_bookmark_button(index)).to_have_attribute(
        "aria-label", "Remove bookmark"
    )


def test_every_listed_question_is_numbered_and_named(bookmarks_tab):
    total = bookmarks_tab.question_count()

    assert total > 0
    expect(bookmarks_tab.get_question_numbers()).to_have_count(total)
    expect(bookmarks_tab.get_exam_titles()).to_have_count(total)
    expect(bookmarks_tab.get_bookmark_buttons()).to_have_count(total)

    for index in range(total):
        expect(bookmarks_tab.get_question_numbers().nth(index)).to_have_text(
            re.compile(r"^\d+$")
        )
        expect(bookmarks_tab.get_exam_titles().nth(index)).not_to_be_empty()
        expect(bookmarks_tab.get_question_body(index)).not_to_be_empty()


# ---------------------------------------------------------------------------
# From an exam to the Exam Notes tab
# ---------------------------------------------------------------------------

def test_the_noted_exam_question_is_listed_under_exam_notes(
    marked_questions, notes_tab
):
    index = notes_tab.find_question(
        marked_questions["noted"]["question"], marked_questions["noted"]["exam"]
    )

    assert index is not None, "the question a note was saved on is not listed"
    expect(notes_tab.get_question(index)).to_be_visible()
    expect(notes_tab.get_exam_title(index)).to_have_text(
        marked_questions["noted"]["exam"]
    )


def test_opening_the_noted_question_shows_the_same_question(
    marked_questions, exam_question
):
    assert exam_question.get_question_text() == marked_questions["noted"]["question"]
    assert exam_question.get_option_text_values() == marked_questions["noted"]["options"]


def test_the_note_written_in_the_exam_is_kept_against_the_question(
    marked_questions, exam_question
):
    exam_question.click_note()

    expect(exam_question.get_note_editor()).to_be_visible()
    expect(exam_question.get_note_editor()).to_have_text(marked_questions["noted"]["note"])


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def test_search_opens_a_search_field(page, search):
    expect(page).to_have_url(ExamsSearchPage.URL_PATTERN)
    expect(search.get_search_input()).to_be_visible()


def searchable_marked_question(marked_questions):
    """The first marked question with enough plain words to search with.

    A paper written for testing holds questions a single character long, and
    those cannot be typed into a search and told apart from everything else, so
    whichever of the marked questions can be is the one used."""
    for marked in marked_questions["marked"]:
        snippet = searchable_snippet(marked["question"])
        if snippet and len(snippet) >= 4:
            return marked, snippet
    return None, None


def test_search_narrows_the_listed_questions(marked_questions, search):
    """The question searched for stays, and nothing that does not hold it."""
    marked, snippet = searchable_marked_question(marked_questions)
    if marked is None:
        pytest.skip("No marked exam question has plain words to search with")

    search.search(snippet)
    search.wait_for_loaded()

    expect(search.get_questions().first).to_be_visible()
    assert search.find_question(marked["question"], marked["exam"]) is not None

    for text in search.get_question_texts():
        assert snippet.lower() in text.lower(), f"{text!r} does not hold {snippet!r}"


def test_search_says_when_nothing_matches(search):
    search.search("zzzznomatch")
    search.wait_for_loaded()

    expect(search.get_no_result()).to_be_visible()
    expect(search.get_no_result_title()).to_have_text("No Matching Search Result")
    expect(search.get_questions()).to_have_count(0)


def test_search_shows_the_note_saved_against_a_result(marked_questions, page, search):
    """The note is not on the section's own cards; the search results carry it."""
    search.search("")
    search.wait_for_loaded()

    index = search.find_question(
        marked_questions["noted"]["question"], marked_questions["noted"]["exam"]
    )
    if index is None:
        pytest.skip("The noted question is not among the bookmarked results")

    expect(search.get_note_preview(index)).to_be_visible()
    expect(search.get_note_text(index)).to_have_text(marked_questions["noted"]["note"])


# ---------------------------------------------------------------------------
# Filter by exam
# ---------------------------------------------------------------------------

def test_the_filter_lists_the_exams_that_hold_a_marked_question(
    marked_questions, bookmarks_tab
):
    bookmarks_tab.click_filter()

    expect(bookmarks_tab.get_filter_sheet()).to_be_visible()
    expect(bookmarks_tab.get_filter_title()).to_have_text("Filter By Exam")

    listed = bookmarks_tab.get_filter_exam_names()
    for exam in bookmarks_tab.get_exam_title_texts():
        assert exam in listed, f"{exam!r} holds a bookmark but is not offered"


def test_the_filter_offers_apply_and_clear(marked_questions, bookmarks_tab):
    """Clear empties the selection and leaves the sheet standing; Apply is what
    closes it."""
    bookmarks_tab.click_filter()

    expect(bookmarks_tab.get_filter_apply_button()).to_be_visible()
    expect(bookmarks_tab.get_filter_clear_button()).to_be_visible()

    bookmarks_tab.select_filter_exam(marked_questions["noted"]["exam"])
    expect(bookmarks_tab.get_selected_filters()).to_have_count(1)

    bookmarks_tab.clear_filter()

    expect(bookmarks_tab.get_selected_filters()).to_have_count(0)
    expect(bookmarks_tab.get_filter_sheet()).to_be_visible()

    bookmarks_tab.apply_filter()

    expect(bookmarks_tab.get_filter_overlay()).to_have_count(0)


def test_filtering_by_an_exam_keeps_only_that_exams_questions(
    marked_questions, bookmarks_tab
):
    exam = marked_questions["noted"]["exam"]
    before = bookmarks_tab.question_count()
    others = [
        title for title in bookmarks_tab.get_exam_title_texts() if title != exam
    ]

    bookmarks_tab.click_filter()
    bookmarks_tab.select_filter_exam(exam)
    bookmarks_tab.apply_filter()

    kept = bookmarks_tab.question_count()
    assert kept > 0, f"filtering by {exam!r} left nothing"
    assert bookmarks_tab.get_exam_title_texts() == [exam] * kept

    # Only provable when another exam had something to drop.
    if others:
        assert kept < before, "the filter kept questions from the other exams"


def test_clearing_the_exam_filter_brings_every_question_back(
    marked_questions, bookmarks_tab
):
    before = bookmarks_tab.question_count()

    bookmarks_tab.click_filter()
    bookmarks_tab.select_filter_exam(marked_questions["noted"]["exam"])
    bookmarks_tab.apply_filter()

    bookmarks_tab.click_filter()
    bookmarks_tab.clear_filter()
    bookmarks_tab.apply_filter()

    expect(bookmarks_tab.get_questions()).to_have_count(before)


# ---------------------------------------------------------------------------
# A single exam question
# ---------------------------------------------------------------------------

def test_the_question_opens_with_its_options(page, exam_question):
    expect(page).to_have_url(ExamQuestionPage.URL_PATTERN)
    expect(exam_question.get_page()).to_be_visible()
    expect(exam_question.get_question()).not_to_be_empty()
    expect(exam_question.get_choose_label()).to_be_visible()

    total = exam_question.get_options().count()
    assert total >= 2
    expect(exam_question.get_option_numbers()).to_have_count(total)
    for index in range(total):
        expect(exam_question.get_option_texts().nth(index)).not_to_be_empty()


def test_the_question_shows_where_it_sits_in_the_set(exam_question):
    expect(exam_question.get_counter()).to_be_visible()

    assert exam_question.get_current_number() >= 1
    assert exam_question.get_total_number() >= exam_question.get_current_number()


def test_the_question_shows_it_is_bookmarked(exam_question):
    expect(exam_question.get_bookmark_button()).to_have_attribute(
        "aria-label", "Remove bookmark"
    )
    assert exam_question.is_bookmarked()


def test_the_question_offers_a_note(exam_question):
    exam_question.click_note()

    expect(exam_question.get_note_editor()).to_be_visible()
    expect(exam_question.get_note_save_button()).to_be_visible()

    exam_question.get_note_close_button().click()

    expect(exam_question.get_note_editor()).to_have_count(0)


def test_view_solution_waits_for_an_answer(exam_question):
    expect(exam_question.get_view_solution_button()).to_be_visible()
    expect(exam_question.get_view_solution_button()).to_be_disabled()

    assert exam_question.is_solution_available() is False


def test_answering_the_question_enables_view_solution(exam_question):
    exam_question.select_option(0)

    expect(exam_question.get_option(0)).to_have_class(re.compile("qlr-opt-selected"))
    expect(exam_question.get_view_solution_button()).to_be_enabled()

    assert exam_question.is_solution_available()


# ---------------------------------------------------------------------------
# Filters on a question
# ---------------------------------------------------------------------------

def test_the_filter_offers_every_answer_state(exam_question):
    exam_question.click_filter()

    expect(exam_question.get_filter_sheet()).to_be_visible()
    expect(exam_question.get_filter_rows()).to_have_count(len(ExamQuestionPage.FILTERS))

    assert exam_question.get_filter_names() == ExamQuestionPage.FILTERS


def test_every_filter_shows_how_many_it_covers(exam_question):
    exam_question.click_filter()

    for name in ExamQuestionPage.FILTERS:
        expect(exam_question.get_filter_row(name)).to_have_text(
            re.compile(re.escape(name) + r"\s*\(\d+\)")
        )


def test_all_is_the_filter_in_force_to_begin_with(exam_question):
    exam_question.click_filter()

    expect(exam_question.get_active_filter()).to_have_count(1)
    expect(exam_question.get_active_filter()).to_contain_text("All")


@pytest.mark.parametrize("state", ExamQuestionPage.FILTERS)
def test_every_filter_can_be_selected(exam_question, state):
    exam_question.click_filter()
    exam_question.select_filter(state)

    expect(exam_question.get_active_filter()).to_contain_text(state)


def test_the_bookmark_filter_counts_the_question_that_was_bookmarked(exam_question):
    """The question reached here was bookmarked in the exam, so the Bookmark
    row cannot be empty."""
    exam_question.click_filter()

    assert exam_question.get_filter_count("Bookmark") >= 1


# ---------------------------------------------------------------------------
# Reporting a question
# ---------------------------------------------------------------------------

def test_report_offers_the_reasons_to_choose_from(exam_question):
    exam_question.click_report()

    expect(exam_question.get_report_sheet()).to_be_visible()
    expect(exam_question.get_report_sheet()).to_contain_text("Report Issue")

    for reason in [
        "Incorrect question",
        "Incorrect options",
        "Wrong solution/explanation",
        "Others",
    ]:
        expect(exam_question.get_report_sheet()).to_contain_text(reason)

    # Not sent on purpose: it would raise a real report against the question.
    expect(exam_question.get_report_send_button()).to_be_visible()


# ---------------------------------------------------------------------------
# API verification
#
# Each tab is served by its own call, and the screen is held until it shows as
# many cards as the answer carried, so the two can be read against each other.
# ---------------------------------------------------------------------------

BOOKMARKED_QUESTIONS_API = "**/api/v3/question-bank/exam-questions?type=bookmarked"
NOTE_QUESTIONS_API = "**/api/v3/question-bank/exam-questions?type=note"


def test_bookmarks_tab_matches_the_exam_questions_api(page):
    with page.expect_response(BOOKMARKED_QUESTIONS_API) as answer:
        page.goto(SECTION_URL, wait_until="domcontentloaded")
    assert answer.value.status == 200, f"exam-questions answered {answer.value.status}"
    questions = answer.value.json()["questions"]

    section = ExamsSectionPage(page)
    section.wait_for_loaded()

    expect(section.get_questions()).to_have_count(len(questions))
    if questions:
        expect(section.get_exam_titles()).to_have_count(len(questions))


def test_exam_notes_tab_matches_the_exam_questions_api(page):
    page.goto(SECTION_URL, wait_until="domcontentloaded")
    section = ExamsSectionPage(page)
    section.wait_for_loaded()

    with page.expect_response(NOTE_QUESTIONS_API) as answer:
        section.open_tab("Exam Notes")
    assert answer.value.status == 200, f"exam-questions answered {answer.value.status}"

    expect(section.get_questions()).to_have_count(
        len(answer.value.json()["questions"])
    )
