"""My Notes, the first section of the Question Library.

Covers the chapter list, the questions of a chapter and a single question
opened from it. The other three sections are not covered here.

Every test needs the account to hold at least one note; see the module docstring
note below for how one is made.

Notes are written from a question, not from the Question Library: open a
question and use its pen button. The tests skip with that instruction rather
than fail when an account has none.
"""
import re
import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.my_notes_page import MyNotesPage, NoteQuestionsPage, NoteQuestionPage
from pages.question_library_page import QuestionLibraryPage

MOBILE = "9876543210"

QUESTION_LIBRARY_URL = QuestionLibraryPage.URL
MY_NOTES_URL = MyNotesPage.URL

NO_NOTES = (
    "This account has no notes yet. Open a question from the Question Library "
    "and save one with its pen button to give these tests something to read."
)


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture
def question_library(page):
    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()
    home_page.get_question_library().scroll_into_view_if_needed()
    home_page.get_question_library().click()
    page.wait_for_url(QUESTION_LIBRARY_URL)

    question_library = QuestionLibraryPage(page)
    question_library.wait_for_loaded()
    return question_library


@pytest.fixture
def my_notes(page, question_library):
    """Opened the way a student reaches it, from the Question Library card."""
    question_library.open_card("My Notes")
    page.wait_for_url(MY_NOTES_URL)

    my_notes = MyNotesPage(page)
    my_notes.wait_for_loaded()
    return my_notes


@pytest.fixture
def populated_notes(my_notes):
    if not my_notes.has_notes():
        pytest.skip(NO_NOTES)
    return my_notes


@pytest.fixture
def note_questions(page, populated_notes):
    """The questions of the first chapter that holds a note."""
    populated_notes.open_chapter(0)

    note_questions = NoteQuestionsPage(page)
    note_questions.wait_for_loaded()
    return note_questions


@pytest.fixture
def note_question(page, note_questions):
    """One question, opened from the chapter list."""
    note_questions.open_question(0)

    note_question = NoteQuestionPage(page)
    note_question.wait_for_loaded()
    return note_question


# ---------------------------------------------------------------------------
# Opening My Notes
# ---------------------------------------------------------------------------

def test_my_notes_opens_from_the_question_library(page, my_notes):
    expect(page).to_have_url(MY_NOTES_URL)
    expect(my_notes.get_page()).to_be_visible()
    expect(my_notes.get_header()).to_be_visible()


def test_my_notes_shows_its_title(my_notes):
    expect(my_notes.get_title()).to_have_text("My Notes")


def test_my_notes_offers_back_and_search(my_notes):
    expect(my_notes.get_back_button()).to_be_visible()
    expect(my_notes.get_back_button()).to_be_enabled()
    expect(my_notes.get_search_button()).to_be_visible()
    expect(my_notes.get_search_button()).to_be_enabled()


def test_back_returns_to_the_question_library(page, my_notes):
    my_notes.click_back()

    expect(page).to_have_url(QUESTION_LIBRARY_URL)
    expect(QuestionLibraryPage(page).get_title()).to_have_text("Question Library")


def test_my_notes_total_matches_the_library_card(page, question_library):
    """The count on the Question Library card is the number of notes held, so
    the tabs inside have to add up to it."""
    total = int(question_library.get_card_count("My Notes").inner_text().strip())

    question_library.open_card("My Notes")
    page.wait_for_url(MY_NOTES_URL)
    my_notes = MyNotesPage(page)
    my_notes.wait_for_loaded()

    if not my_notes.has_notes():
        assert total == 0
        return

    per_subject = sum(
        my_notes.get_tab_count(index) for index in range(my_notes.get_tabs().count())
    )
    assert per_subject == total


def test_my_notes_says_so_when_there_is_nothing_to_show(my_notes):
    if my_notes.has_notes():
        pytest.skip("This account has notes, so the empty state does not apply")

    expect(my_notes.get_empty_state()).to_be_visible()
    expect(my_notes.get_empty_message()).to_have_text("No notes yet")


# ---------------------------------------------------------------------------
# Subject tabs and chapters
# ---------------------------------------------------------------------------

def test_my_notes_lists_subject_tabs(populated_notes):
    expect(populated_notes.get_tabs().first).to_be_visible()
    expect(populated_notes.get_active_tab()).to_have_count(1)

    assert populated_notes.get_tabs().count() >= 1


def test_every_subject_tab_carries_a_count(populated_notes):
    for index in range(populated_notes.get_tabs().count()):
        expect(populated_notes.get_tabs().nth(index)).to_have_text(
            re.compile(r".+\(\d+\)$")
        )


def test_selecting_a_subject_shows_its_chapters(populated_notes):
    for index in range(populated_notes.get_tabs().count()):
        populated_notes.click_tab(index)

        expect(populated_notes.get_active_tab()).to_have_count(1)
        assert populated_notes.chapter_count() > 0


def test_chapters_show_a_number_and_a_title(populated_notes):
    total = populated_notes.chapter_count()

    expect(populated_notes.get_chapter_numbers()).to_have_count(total)
    expect(populated_notes.get_chapter_titles()).to_have_count(total)

    for index in range(total):
        expect(populated_notes.get_chapter_titles().nth(index)).not_to_be_empty()


def test_chapters_show_how_many_notes_they_hold(populated_notes):
    total = populated_notes.chapter_count()

    for index in range(total):
        expect(populated_notes.get_chapter_note_count(index)).to_have_text(
            re.compile(r"^\d+$")
        )

    counted = sum(
        int(populated_notes.get_chapter_note_count(index).inner_text().strip())
        for index in range(total)
    )
    assert counted == populated_notes.get_tab_count(0)


# ---------------------------------------------------------------------------
# The questions of a chapter
# ---------------------------------------------------------------------------

def test_opening_a_chapter_shows_its_noted_questions(page, note_questions):
    expect(page).to_have_url(NoteQuestionsPage.URL_PATTERN)
    expect(note_questions.get_page()).to_be_visible()
    expect(note_questions.get_title()).not_to_be_empty()

    assert note_questions.question_count() > 0


def test_each_question_shows_the_note_saved_against_it(note_questions):
    total = note_questions.question_count()

    expect(note_questions.get_note_previews()).to_have_count(total)

    for index in range(total):
        expect(note_questions.get_note_preview(index)).to_be_visible()
        expect(note_questions.get_note_text(index)).not_to_be_empty()


def test_questions_screen_offers_search_and_filter(note_questions):
    expect(note_questions.get_search_button()).to_be_enabled()
    expect(note_questions.get_filter_button()).to_be_enabled()
    expect(note_questions.get_back_button()).to_be_enabled()


def test_search_opens_a_search_field(note_questions):
    note_questions.click_search()

    expect(note_questions.get_search_input()).to_be_visible()
    expect(note_questions.get_search_input()).to_have_attribute("placeholder", "Search..")


def test_filter_offers_the_chapter_topics(note_questions):
    note_questions.click_filter()

    expect(note_questions.get_filter_sheet()).to_be_visible()
    expect(note_questions.get_filter_title()).to_have_text("Filter By Topic")
    expect(note_questions.get_filter_apply_button()).to_be_visible()
    expect(note_questions.get_filter_clear_button()).to_be_visible()

    note_questions.close_filter()

    expect(note_questions.get_filter_overlay()).to_have_count(0)


# ---------------------------------------------------------------------------
# A single question
# ---------------------------------------------------------------------------

def test_opening_a_question_shows_it_in_full(note_question):
    expect(note_question.get_page()).to_be_visible()
    expect(note_question.get_question()).not_to_be_empty()
    expect(note_question.get_choose_label()).to_be_visible()

    assert note_question.get_options().count() >= 2


def test_question_options_are_numbered(note_question):
    total = note_question.get_options().count()

    expect(note_question.get_option_numbers()).to_have_count(total)
    expect(note_question.get_option_texts()).to_have_count(total)

    for index in range(total):
        expect(note_question.get_option_texts().nth(index)).not_to_be_empty()


def test_question_shows_where_it_sits_in_the_set(note_question):
    expect(note_question.get_counter()).to_be_visible()

    assert note_question.get_current_number() >= 1
    assert note_question.get_total_number() >= note_question.get_current_number()


def test_question_offers_notes_and_bookmark(note_question):
    expect(note_question.get_note_button()).to_be_visible()
    expect(note_question.get_note_button()).to_be_enabled()
    expect(note_question.get_bookmark_button()).to_be_visible()
    expect(note_question.get_bookmark_button()).to_be_enabled()


def test_the_note_button_opens_the_note_editor(note_question):
    note_question.click_note()

    expect(note_question.get_note_editor()).to_be_visible()
    expect(note_question.get_note_save_button()).to_be_visible()

    note_question.get_note_close_button().click()

    expect(note_question.get_note_editor()).to_have_count(0)


def test_view_solution_waits_for_an_answer(note_question):
    """The button is dead until the question has been answered."""
    expect(note_question.get_view_solution_button()).to_be_visible()
    expect(note_question.get_view_solution_button()).to_be_disabled()

    assert note_question.is_solution_available() is False


def test_answering_a_question_enables_view_solution(note_question):
    note_question.select_option(0)

    expect(note_question.get_option(0)).to_have_class(re.compile("qlr-opt-selected"))
    expect(note_question.get_view_solution_button()).to_be_enabled()

    assert note_question.is_option_selected(0)
    assert note_question.is_solution_available()


# ---------------------------------------------------------------------------
# Filters on a question
# ---------------------------------------------------------------------------

def test_question_filter_offers_every_answer_state(note_question):
    note_question.click_filter()

    expect(note_question.get_filter_sheet()).to_be_visible()
    expect(note_question.get_filter_rows()).to_have_count(len(NoteQuestionPage.FILTERS))

    assert note_question.get_filter_names() == NoteQuestionPage.FILTERS


def test_every_filter_shows_how_many_it_covers(note_question):
    note_question.click_filter()

    for name in NoteQuestionPage.FILTERS:
        expect(note_question.get_filter_row(name)).to_have_text(
            re.compile(re.escape(name) + r"\s*\(\d+\)")
        )


def test_all_is_the_filter_in_force_to_begin_with(note_question):
    note_question.click_filter()

    expect(note_question.get_active_filter()).to_have_count(1)
    expect(note_question.get_active_filter()).to_contain_text("All")


@pytest.mark.parametrize("state", NoteQuestionPage.FILTERS)
def test_each_filter_can_be_selected(note_question, state):
    note_question.click_filter()
    note_question.select_filter(state)

    expect(note_question.get_active_filter()).to_contain_text(state)


def test_the_filter_sheet_lists_the_questions_it_matches(note_question):
    note_question.click_filter()

    expect(note_question.get_question_cells().first).to_be_visible()

    note_question.close_filter()

    expect(note_question.get_filter_overlay()).to_have_count(0)


# ---------------------------------------------------------------------------
# Reporting a question
# ---------------------------------------------------------------------------

def test_report_offers_the_reasons_to_choose_from(note_question):
    note_question.click_report()

    expect(note_question.get_report_sheet()).to_be_visible()
    expect(note_question.get_report_sheet()).to_contain_text("Report Issue")

    for reason in [
        "Incorrect question",
        "Incorrect options",
        "Wrong solution/explanation",
        "Others",
    ]:
        expect(note_question.get_report_sheet()).to_contain_text(reason)

    # Not sent on purpose: it would raise a real report against the question.
    expect(note_question.get_report_send_button()).to_be_visible()
