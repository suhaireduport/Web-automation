"""Bookmarks, the second section of the Question Library.

The bookmark these tests read is not made in the Question Library: it is made
where a student makes one, in a quick practice reached from Home, and the
section is then checked for it. Subject, chapter, topic and question all come
back from that practice rather than being written down here, because which of
them still has an unanswered question left changes as the account is used.

The practice is run once for the whole file through the session scoped
bookmarked fixture. The question it bookmarks is also answered, because an
unanswered question is served again in the next run, by then already
bookmarked.

Removal is checked last, and not against that shared bookmark. Each removal
test makes one of its own through the same practice flow, so neither can decide
what the other finds, and neither leans on a count some earlier test left
behind: both measure the move from a reading they take themselves.

Removing is also watched at the wire. The screen drops the card whether or not
the server was ever told, so a click alone proves nothing; both tests wait for
the POST to /bookmarks/remove to come back before believing the screen. If the
request never goes out, they fail on that rather than pass on a vanished card.

The count test keeps an xfail while the app is intermittent, narrowed to the
assertion it is about: anything else - a request that never lands, a chapter
that is not listed - is a different fault and is left to fail out loud.
"""
import re

import pytest
from playwright.sync_api import expect

from pages.bookmark_page import BookmarkPage, BookmarkQuestionsPage, BookmarkQuestionPage
from pages.home_page import HomePage
from pages.practice_page import start_quick_practice
from pages.question_library_page import QuestionLibraryPage
from pages.question_library_section_page import read_section_count, searchable_snippet

MOBILE = "8893963137"

HOME_URL = "https://eduport-react.pages.dev/"
QUESTION_LIBRARY_URL = QuestionLibraryPage.URL
BOOKMARK_URL = BookmarkPage.URL

# The call the remove button is supposed to make. Waiting for it is the whole
# point: the card leaves the list either way.
REMOVE_API = "**/question-bank/bookmarks/remove"
REMOVE_TIMEOUT = 15000

# The two calls the practice makes on the way to a bookmark. They are waited
# for as well: leaving either in flight lets the next navigation cancel it, and
# a bookmark whose question was never really answered is one the app then
# refuses to take off again.
ADD_API = "**/question-bank/bookmarks/add"
SUBMIT_API = "**/practice-quiz/submit/**"

# The card on the landing screen, which names the section in the plural.
SECTION_CARD = "Bookmarks"

NO_QUESTIONS = (
    "No topic on this account has an unpractised question left, so there is "
    "nothing to bookmark from a quick practice."
)


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture(scope="session")
def _bookmark_state():
    return {}


@pytest.fixture(scope="session")
def bookmarked(login_session, _bookmark_state):
    """Bookmark one question through the practice flow, once for the whole run.

    Subject -> topic -> topic quiz -> quick practice -> open question ->
    bookmark. What was practised and what the question said is handed back, so
    every test can look for that same question in the section afterwards."""
    if "reason" in _bookmark_state:
        pytest.skip(_bookmark_state["reason"])

    page = login_session(MOBILE)
    practice, practised = start_quick_practice(page)
    if practice is None:
        _bookmark_state["reason"] = NO_QUESTIONS
        pytest.skip(NO_QUESTIONS)

    # A run that was interrupted before its last test can leave the question it
    # bookmarked behind, and the count would then not move.
    if practice.is_bookmarked():
        practice.click_bookmark()
        page.locator(".tq-bookmark[aria-label='Add bookmark']").wait_for()

    # Read on a page of its own: the practice cannot be navigated away from and
    # come back to.
    before = read_section_count(page.context, SECTION_CARD)

    with page.expect_response(ADD_API, timeout=REMOVE_TIMEOUT):
        practice.click_bookmark()
    page.locator(".tq-bookmark[aria-label='Remove bookmark']").wait_for()

    _bookmark_state.update(practised)
    _bookmark_state.update(
        question=practice.get_question_text(),
        options=practice.get_option_text_values(),
        bookmarked_in_practice=practice.is_bookmarked(),
        count_before=before,
    )

    # Answer it before leaving. Nothing is read from the answer: it is what
    # takes the question out of the pool a practice draws from, and a question
    # left unanswered comes back in the next run already bookmarked, where a
    # second bookmark of it would move no count at all. The rest of the set is
    # left alone so the account keeps them.
    practice.select_option(0)
    with page.expect_response(SUBMIT_API, timeout=REMOVE_TIMEOUT):
        practice.submit()
    practice.get_back_button().click()

    yield _bookmark_state

    # Tidy up. The removal tests take bookmarks of their own now, so nothing
    # else would ever take this one off the account. It is a best effort and
    # not a check - removal is tested above - so it must never fail a run.
    try:
        questions, index, _ = open_bookmarked_chapter(page, _bookmark_state)
        with page.expect_response(REMOVE_API, timeout=REMOVE_TIMEOUT):
            questions.remove_bookmark(index)
    except Exception:
        pass


@pytest.fixture
def own_bookmark(page):
    """A bookmark belonging to this test alone, made the way the flow makes one.

    The removal tests take one each rather than sharing the session bookmark:
    a removal is not allowed to decide what another test finds, and a count
    another test moved is not something to measure against."""
    practice, practised = start_quick_practice(page)
    if practice is None:
        pytest.skip(NO_QUESTIONS)

    # An interrupted run can leave a question bookmarked, and bookmarking it a
    # second time would move no count at all.
    if practice.is_bookmarked():
        practice.click_bookmark()
        page.locator(".tq-bookmark[aria-label='Add bookmark']").wait_for()

    with page.expect_response(ADD_API, timeout=REMOVE_TIMEOUT) as added:
        practice.click_bookmark()
    assert added.value.status == 200, f"bookmark answered {added.value.status}"
    page.locator(".tq-bookmark[aria-label='Remove bookmark']").wait_for()
    question = practice.get_question_text()

    # Answer it before leaving, and wait for the answer to be saved. A question
    # left unattempted is served again to the next test, which would then be
    # working on the same bookmark as this one.
    practice.select_option(0)
    with page.expect_response(SUBMIT_API, timeout=REMOVE_TIMEOUT):
        practice.submit()
    practice.get_back_button().click()

    return dict(practised, question=question)


def open_bookmarked_chapter(page, bookmark):
    """Home -> Question Library -> Bookmarks -> the chapter holding a bookmark.

    Hands back the questions screen, where that bookmark sits on it, and what
    the library card counted on the way in, so a test can check the count moved
    by one from a reading of its own.

    The two "not listed" faults raise rather than assert on purpose: an xfail
    marked test folds an AssertionError into its own expected failure, and
    neither of these is the defect that marker is about."""
    page.goto(HOME_URL, wait_until="domcontentloaded")

    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()
    home_page.get_question_library().scroll_into_view_if_needed()
    home_page.get_question_library().click()
    page.wait_for_url(QUESTION_LIBRARY_URL)

    library = QuestionLibraryPage(page)
    library.wait_for_loaded()
    counted = int(library.get_card_count(SECTION_CARD).inner_text().strip())

    library.open_card(SECTION_CARD)
    page.wait_for_url(BOOKMARK_URL)
    bookmarks = BookmarkPage(page)
    bookmarks.wait_for_loaded()
    bookmarks.open_subject(bookmark["subject"])

    chapter = bookmarks.find_chapter(bookmark["chapter"])
    if chapter is None:
        raise LookupError(f"{bookmark['chapter']} is not listed in Bookmarks")
    bookmarks.open_chapter(chapter)

    questions = BookmarkQuestionsPage(page)
    questions.wait_for_loaded()

    index = questions.find_question(bookmark["question"])
    if index is None:
        raise LookupError("the bookmark is not listed in its chapter")
    return questions, index, counted


@pytest.fixture
def question_library(bookmarked, page):
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
def bookmarks(page, question_library):
    question_library.open_card(SECTION_CARD)
    page.wait_for_url(BOOKMARK_URL)

    bookmarks = BookmarkPage(page)
    bookmarks.wait_for_loaded()
    return bookmarks


@pytest.fixture
def bookmarked_subject(bookmarked, bookmarks):
    """The section showing the subject the bookmarked question came from."""
    bookmarks.open_subject(bookmarked["subject"])
    return bookmarks


@pytest.fixture
def bookmark_questions(page, bookmarked, bookmarked_subject):
    """The bookmarked questions of the chapter that was practised."""
    index = bookmarked_subject.find_chapter(bookmarked["chapter"])
    assert index is not None, f"{bookmarked['chapter']} is not listed in Bookmarks"

    bookmarked_subject.open_chapter(index)

    questions = BookmarkQuestionsPage(page)
    questions.wait_for_loaded()
    return questions


@pytest.fixture
def bookmarked_question(page, bookmarked, bookmark_questions):
    """The very question the practice bookmarked, opened."""
    index = bookmark_questions.find_question(bookmarked["question"])
    assert index is not None, "the bookmarked question is not listed in Bookmarks"

    bookmark_questions.open_question(index)

    question = BookmarkQuestionPage(page)
    question.wait_for_loaded()
    return question


# ---------------------------------------------------------------------------
# From the practice to the section
# ---------------------------------------------------------------------------

def test_the_practice_marked_the_question_as_bookmarked(bookmarked):
    assert bookmarked["bookmarked_in_practice"] is True


def test_the_bookmarked_question_is_listed_in_the_section(bookmarked, bookmark_questions):
    index = bookmark_questions.find_question(bookmarked["question"])

    assert index is not None, "the question bookmarked in the practice is not listed"
    expect(bookmark_questions.get_question(index)).to_be_visible()


def test_the_bookmark_is_filed_under_the_subject_it_was_practised_in(
    bookmarked, bookmarked_subject
):
    expect(bookmarked_subject.get_tab(bookmarked["subject"])).to_have_count(1)
    expect(bookmarked_subject.get_active_tab()).to_contain_text(bookmarked["subject"])


def test_the_bookmark_is_filed_under_the_chapter_it_was_practised_in(
    bookmarked, bookmark_questions
):
    expect(bookmark_questions.get_title()).to_have_text(bookmarked["chapter"])


def test_the_library_card_counts_the_new_bookmark(bookmarked, question_library):
    after = int(question_library.get_card_count(SECTION_CARD).inner_text().strip())

    assert after == bookmarked["count_before"] + 1


def test_the_listed_question_still_shows_as_bookmarked(bookmarked, bookmark_questions):
    index = bookmark_questions.find_question(bookmarked["question"])

    expect(bookmark_questions.get_bookmark_button(index)).to_have_attribute(
        "aria-label", "Remove bookmark"
    )


def test_opening_the_bookmark_shows_the_same_question(bookmarked, bookmarked_question):
    assert bookmarked_question.get_question_text() == bookmarked["question"]
    assert bookmarked_question.get_option_text_values() == bookmarked["options"]


# ---------------------------------------------------------------------------
# The section screen
# ---------------------------------------------------------------------------

def test_the_section_opens_from_the_question_library(page, bookmarks):
    expect(page).to_have_url(BOOKMARK_URL)
    expect(bookmarks.get_page()).to_be_visible()
    expect(bookmarks.get_title()).to_have_text(SECTION_CARD)


def test_the_section_offers_back_and_search(bookmarks):
    expect(bookmarks.get_back_button()).to_be_enabled()
    expect(bookmarks.get_search_button()).to_be_enabled()


def test_back_returns_to_the_question_library(page, bookmarks):
    bookmarks.click_back()

    expect(page).to_have_url(QUESTION_LIBRARY_URL)
    expect(QuestionLibraryPage(page).get_title()).to_have_text("Question Library")


def test_subject_tabs_count_the_chapters_they_hold(bookmarks):
    """A tab reads "Chemistry (1)", where the number is chapters and not
    bookmarks: one chapter holding four of them still reads (1)."""
    assert bookmarks.get_tabs().count() >= 1

    for index in range(bookmarks.get_tabs().count()):
        bookmarks.click_tab(index)

        expect(bookmarks.get_active_tab()).to_have_count(1)
        assert bookmarks.chapter_count() == bookmarks.get_tab_count(index)


def test_chapters_show_a_number_a_title_and_a_count(bookmarks):
    total = bookmarks.chapter_count()

    expect(bookmarks.get_chapter_numbers()).to_have_count(total)
    expect(bookmarks.get_chapter_titles()).to_have_count(total)

    for index in range(total):
        expect(bookmarks.get_chapter_titles().nth(index)).not_to_be_empty()
        expect(bookmarks.get_chapter_bookmark_count(index)).to_have_text(
            re.compile(r"^\d+$")
        )


def test_a_chapter_count_matches_the_questions_it_lists(page, bookmarks):
    expected = int(bookmarks.get_chapter_bookmark_count(0).inner_text().strip())

    bookmarks.open_chapter(0)
    questions = BookmarkQuestionsPage(page)
    questions.wait_for_loaded()

    assert questions.question_count() == expected


def test_the_section_total_matches_the_library_card(question_library, page):
    """Every chapter of every subject added up is what the card counts."""
    total = int(question_library.get_card_count(SECTION_CARD).inner_text().strip())

    question_library.open_card(SECTION_CARD)
    page.wait_for_url(BOOKMARK_URL)
    bookmarks = BookmarkPage(page)
    bookmarks.wait_for_loaded()

    counted = 0
    for index in range(bookmarks.get_tabs().count()):
        bookmarks.click_tab(index)
        bookmarks.chapter_count()
        counted += bookmarks.chapter_question_total()

    assert counted == total


def test_search_narrows_the_chapter_list(bookmarked, bookmarks):
    """Search leaves the section behind for the subject's own chapter search,
    so what it lists is chapters, not only bookmarked ones."""
    bookmarks.open_subject(bookmarked["subject"])
    bookmarks.click_search()
    bookmarks.wait_for_search_loaded()

    expect(bookmarks.get_search_input()).to_be_visible()

    bookmarks.search(bookmarked["chapter"][:12])

    expect(bookmarks.get_search_results().first).to_be_visible()
    expect(bookmarks.get_search_result_titles().first).to_contain_text(
        bookmarked["chapter"][:12]
    )


def test_search_says_when_nothing_matches(bookmarked, bookmarks):
    # On the subject the flow used: a subject with nothing attempted serves an
    # entirely blank search screen, which is not the state under test.
    bookmarks.open_subject(bookmarked["subject"])
    bookmarks.click_search()
    bookmarks.wait_for_search_loaded()
    bookmarks.search("zzzznomatch")

    expect(bookmarks.get_no_search_result()).to_be_visible()
    expect(bookmarks.get_no_search_result_title()).to_have_text(
        "No Matching Search Result"
    )
    expect(bookmarks.get_search_results()).to_have_count(0)


# ---------------------------------------------------------------------------
# The questions of a chapter
# ---------------------------------------------------------------------------

def test_the_chapter_lists_only_bookmarked_questions(bookmark_questions):
    total = bookmark_questions.question_count()

    assert total > 0
    expect(bookmark_questions.get_bookmark_buttons()).to_have_count(total)

    for index in range(total):
        assert bookmark_questions.is_bookmarked(index)


def test_the_questions_screen_offers_search_and_a_topic_filter(bookmark_questions):
    expect(bookmark_questions.get_back_button()).to_be_enabled()
    expect(bookmark_questions.get_search_button()).to_be_enabled()
    expect(bookmark_questions.get_filter_button()).to_be_enabled()


def test_searching_the_questions_narrows_the_list(bookmarked, bookmark_questions):
    snippet = searchable_snippet(bookmarked["question"])
    assert snippet, "the question has no plain words to search with"

    bookmark_questions.click_search()
    bookmark_questions.search(snippet)

    expect(bookmark_questions.get_questions().first).to_be_visible()
    assert bookmark_questions.find_question(bookmarked["question"]) is not None


def test_the_topic_filter_lists_the_topics_that_were_bookmarked(
    bookmarked, bookmark_questions
):
    bookmark_questions.click_filter()

    expect(bookmark_questions.get_filter_sheet()).to_be_visible()
    expect(bookmark_questions.get_filter_title()).to_have_text("Filter By Topic")
    assert bookmarked["topic"] in bookmark_questions.get_filter_option_names()

    bookmark_questions.close_filter()

    expect(bookmark_questions.get_filter_overlay()).to_have_count(0)


# ---------------------------------------------------------------------------
# A single bookmarked question
# ---------------------------------------------------------------------------

def test_the_question_opens_with_its_options(bookmarked_question):
    expect(bookmarked_question.get_page()).to_be_visible()
    expect(bookmarked_question.get_question()).not_to_be_empty()
    expect(bookmarked_question.get_choose_label()).to_be_visible()

    total = bookmarked_question.get_options().count()
    assert total >= 2
    expect(bookmarked_question.get_option_numbers()).to_have_count(total)


def test_the_question_shows_it_is_bookmarked(bookmarked_question):
    expect(bookmarked_question.get_bookmark_button()).to_have_attribute(
        "aria-label", "Remove bookmark"
    )
    assert bookmarked_question.is_bookmarked()


def test_the_question_offers_a_note(bookmarked_question):
    bookmarked_question.click_note()

    expect(bookmarked_question.get_note_editor()).to_be_visible()
    expect(bookmarked_question.get_note_save_button()).to_be_visible()

    bookmarked_question.get_note_close_button().click()

    expect(bookmarked_question.get_note_editor()).to_have_count(0)


def test_view_solution_waits_for_an_answer(bookmarked_question):
    expect(bookmarked_question.get_view_solution_button()).to_be_visible()
    expect(bookmarked_question.get_view_solution_button()).to_be_disabled()

    assert bookmarked_question.is_solution_available() is False


def test_answering_the_question_enables_view_solution(bookmarked_question):
    bookmarked_question.select_option(0)

    expect(bookmarked_question.get_option(0)).to_have_class(
        re.compile("qlr-opt-selected")
    )
    expect(bookmarked_question.get_view_solution_button()).to_be_enabled()

    assert bookmarked_question.is_solution_available()


def test_the_filter_offers_every_answer_state(bookmarked_question):
    bookmarked_question.click_filter()

    expect(bookmarked_question.get_filter_sheet()).to_be_visible()
    assert bookmarked_question.get_filter_names() == BookmarkQuestionPage.FILTERS

    for name in BookmarkQuestionPage.FILTERS:
        expect(bookmarked_question.get_filter_row(name)).to_have_text(
            re.compile(re.escape(name) + r"\s*\(\d+\)")
        )


@pytest.mark.parametrize("state", BookmarkQuestionPage.FILTERS)
def test_every_filter_can_be_selected(bookmarked_question, state):
    bookmarked_question.click_filter()
    bookmarked_question.select_filter(state)

    expect(bookmarked_question.get_active_filter()).to_contain_text(state)


def test_the_bookmark_filter_counts_the_chapters_bookmarks(
    page, bookmarked, bookmarked_subject
):
    """The Bookmark row of the question filter and the chapter card are two
    readings of the same thing."""
    index = bookmarked_subject.find_chapter(bookmarked["chapter"])
    listed = int(
        bookmarked_subject.get_chapter_bookmark_count(index).inner_text().strip()
    )

    bookmarked_subject.open_chapter(index)
    questions = BookmarkQuestionsPage(page)
    questions.wait_for_loaded()
    questions.open_question(0)

    question = BookmarkQuestionPage(page)
    question.wait_for_loaded()
    question.click_filter()

    assert question.get_filter_count("Bookmark") == listed


# ---------------------------------------------------------------------------
# Taking a bookmark away
#
# Each of these makes its own bookmark, removes that one, and measures against
# a count it read itself, so neither can be answered by what the other did.
# ---------------------------------------------------------------------------

def test_removing_a_bookmark_calls_the_api_and_drops_it_from_the_list(
    page, own_bookmark
):
    questions, index, _ = open_bookmarked_chapter(page, own_bookmark)
    before = questions.question_count()

    # Listening starts before the click, so nothing can slip through in
    # between, and the response is waited for rather than assumed - navigating
    # away any earlier cancels the very request being checked. A card that
    # disappears on its own proves nothing.
    with page.expect_response(REMOVE_API, timeout=REMOVE_TIMEOUT) as removal:
        questions.remove_bookmark(index)

    assert removal.value.request.method == "POST"
    assert removal.value.status == 200, f"remove answered {removal.value.status}"

    expect(questions.get_questions()).to_have_count(before - 1)
    assert questions.find_question(own_bookmark["question"]) is None


@pytest.mark.xfail(
    raises=AssertionError,
    reason=(
        "Removing a bookmark is only sometimes saved: the card leaves the "
        "list every time, but the count on the Question Library card does "
        "not always come back down. Narrowed to AssertionError on purpose - a "
        "removal that never reaches the server raises instead, and is meant "
        "to fail"
    ),
)
def test_removing_a_bookmark_takes_it_off_the_library_count(page, own_bookmark):
    questions, index, counted = open_bookmarked_chapter(page, own_bookmark)

    with page.expect_response(REMOVE_API, timeout=REMOVE_TIMEOUT) as removal:
        questions.remove_bookmark(index)

    # Raised, not asserted: the xfail above is about the count, and a refused
    # removal is a different fault that should not hide behind it.
    if removal.value.status != 200:
        raise RuntimeError(f"remove answered {removal.value.status}, not 200")

    library = QuestionLibraryPage(page)
    page.goto(QUESTION_LIBRARY_URL, wait_until="domcontentloaded")
    library.wait_for_loaded()

    # One fewer than this test counted on its way in, not an absolute another
    # test settled.
    expect(library.get_card_count(SECTION_CARD)).to_have_text(str(counted - 1))
