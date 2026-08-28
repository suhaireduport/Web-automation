"""A subject of the Question Library.

The subject list under the four section cards, and everything it leads to: the
chapters of a subject with what has been attempted in each, the questions of a
chapter behind their answer state tabs, a single question, and the study
recommendations the footer raises.

The last two tests follow the recommendations out of the Question Library and
into a practice - subject, topic, topic quiz - and check the quiz was built
from the chapter that was recommended.

Nothing here writes anything the account keeps. The one test that touches a
bookmark puts it back the way it found it, and the practice is started but not
answered, so its questions stay in the pool.
"""
import re

import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.practice_page import AddTopicsPage, PracticeConfigPage, PracticeQuestionPage
from pages.question_library_page import QuestionLibraryPage
from pages.question_library_section_page import searchable_snippet
from pages.question_library_subject_page import (
    StudyRecommendationsSheet,
    SubjectPage,
    SubjectQuestionPage,
    SubjectQuestionsPage,
    SubjectSearchPage,
)

MOBILE = "9876543210"

HOME_URL = "https://eduport-react.pages.dev/"
QUESTION_LIBRARY_URL = QuestionLibraryPage.URL

NO_SUBJECTS = (
    "This account has attempted no questions, so the Question Library lists no "
    "subject. Answer a practice question to give these tests something to read."
)


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture
def question_library(page):
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
def subject_name(question_library):
    """The first subject the library lists, whichever that is on the account."""
    if question_library.subject_count() == 0:
        pytest.skip(NO_SUBJECTS)
    return question_library.get_subject_names().first.inner_text().strip()


@pytest.fixture
def subject(page, question_library, subject_name):
    question_library.get_subject_cards().first.click()

    subject = SubjectPage(page)
    subject.wait_for_loaded()
    return subject


@pytest.fixture
def chapter_questions(page, subject):
    """The attempted questions of the subject's first chapter."""
    subject.open_chapter(0)

    questions = SubjectQuestionsPage(page)
    questions.wait_for_loaded()
    return questions


@pytest.fixture
def subject_question(page, chapter_questions):
    """One question, opened from the chapter."""
    chapter_questions.open_question(0)

    question = SubjectQuestionPage(page)
    question.wait_for_loaded()
    return question


@pytest.fixture
def recommendations(page, subject):
    subject.click_recommendations()

    sheet = StudyRecommendationsSheet(page)
    expect(sheet.get_overlay()).to_be_visible()
    if sheet.card_count() == 0:
        pytest.skip("Every chapter of this subject is already mastered")
    return sheet


@pytest.fixture
def recommended_chapter(recommendations):
    """The chapter the first recommendation names.

    Read here rather than in a test: Practice Now leaves the subject screen,
    and the sheet goes with it."""
    return recommendations.get_card_title_text(0)


@pytest.fixture
def topic_picker(page, recommendations, recommended_chapter):
    """Practice Now, which leaves the Question Library for the topic picker."""
    recommendations.click_practice(0)

    picker = AddTopicsPage(page)
    picker.wait_for_loaded()
    return picker


# ---------------------------------------------------------------------------
# Opening a subject
# ---------------------------------------------------------------------------

def test_subject_opens_from_the_question_library(page, subject):
    expect(page).to_have_url(SubjectPage.URL_PATTERN)
    expect(subject.get_page()).to_be_visible()
    expect(subject.get_header()).to_be_visible()


def test_subject_shows_its_name_as_the_title(subject, subject_name):
    expect(subject.get_title()).to_have_text(subject_name)


def test_subject_offers_back_and_search(subject):
    expect(subject.get_back_button()).to_be_enabled()
    expect(subject.get_search_button()).to_be_enabled()


def test_back_returns_to_the_question_library(page, subject):
    subject.click_back()

    expect(page).to_have_url(QUESTION_LIBRARY_URL)
    expect(QuestionLibraryPage(page).get_title()).to_have_text("Question Library")


# ---------------------------------------------------------------------------
# The chapter cards
# ---------------------------------------------------------------------------

def test_the_subject_lists_chapter_cards(subject):
    assert subject.chapter_count() > 0

    expect(subject.get_chapters().first).to_be_visible()
    expect(subject.get_chapter_numbers()).to_have_count(subject.chapter_count())

    for index in range(subject.chapter_count()):
        expect(subject.get_chapter_title(index)).not_to_be_empty()
        assert subject.get_chapter_title_text(index)


def test_every_chapter_shows_how_many_attempted_questions_it_holds(subject):
    for index in range(subject.chapter_count()):
        expect(subject.get_chapter_question_count(index)).to_have_text(
            re.compile(r"^\d+$")
        )
        assert subject.get_chapter_question_total(index) > 0


def test_the_chapters_add_up_to_the_count_on_the_library_card(
    page, question_library, subject_name
):
    """The subject card in the library counts questions; the chapters inside it
    have to come to the same number."""
    counted = int(
        re.search(
            r"(\d+)", question_library.get_subject_counts().first.inner_text()
        ).group(1)
    )

    question_library.get_subject_cards().first.click()
    subject = SubjectPage(page)
    subject.wait_for_loaded()

    assert subject.question_total() == counted


def test_every_chapter_breaks_its_questions_down_by_answer_state(subject):
    for index in range(subject.chapter_count()):
        expect(subject.get_statuses(index)).to_have_count(len(SubjectPage.STATUSES))
        expect(subject.get_status_dots(index)).to_have_count(len(SubjectPage.STATUSES))

        assert subject.get_status_names(index) == SubjectPage.STATUSES

        for name in SubjectPage.STATUSES:
            expect(subject.get_status_label(index, name)).to_have_text(
                re.compile(re.escape(name) + r"\s*\(\d+\)")
            )


def test_the_answer_states_account_for_every_question_of_a_chapter(subject):
    """A question in the library has been attempted, so it is correct, wrong or
    unknown. Bookmark is left out: it sits on top of one of those three rather
    than beside them."""
    for index in range(subject.chapter_count()):
        answered = sum(
            subject.get_status_count(index, name) for name in SubjectPage.ANSWER_STATES
        )

        assert answered == subject.get_chapter_question_total(index)
        assert (
            subject.get_status_count(index, "Bookmark")
            <= subject.get_chapter_question_total(index)
        )


def test_every_chapter_shows_the_mastery_it_reached(subject):
    for index in range(subject.chapter_count()):
        expect(subject.get_mastery(index)).to_be_visible()
        expect(subject.get_mastery_value(index)).to_have_text(
            re.compile(r"^\s*\d+\s*%\s*Mastery\s*$")
        )


# ---------------------------------------------------------------------------
# Searching the chapters
# ---------------------------------------------------------------------------

def test_subject_search_narrows_the_chapter_list(page, subject):
    wanted = subject.get_chapter_title_text(0)
    subject.click_search()

    search = SubjectSearchPage(page)
    expect(page).to_have_url(SubjectSearchPage.URL_PATTERN)
    search.wait_for_loaded()
    expect(search.get_search_input()).to_be_visible()

    snippet = wanted[:12]
    search.search(snippet)

    expect(search.get_results().first).to_be_visible()
    for title in search.get_result_title_texts():
        assert snippet.lower() in title.lower()


def test_subject_search_says_when_nothing_matches(page, subject):
    subject.click_search()

    search = SubjectSearchPage(page)
    search.wait_for_loaded()
    search.search("zzzznomatch")

    expect(search.get_no_result()).to_be_visible()
    expect(search.get_no_result_title()).to_have_text("No Matching Search Result")
    expect(search.get_results()).to_have_count(0)


# ---------------------------------------------------------------------------
# The questions of a chapter
# ---------------------------------------------------------------------------

def test_opening_a_chapter_lists_its_questions(page, subject, chapter_questions):
    expect(page).to_have_url(SubjectQuestionsPage.URL_PATTERN)
    expect(chapter_questions.get_page()).to_be_visible()
    expect(chapter_questions.get_title()).not_to_be_empty()

    assert chapter_questions.question_count() > 0


def test_the_chapter_lists_as_many_questions_as_its_card_counted(page, subject):
    counted = subject.get_chapter_question_total(0)

    subject.open_chapter(0)
    questions = SubjectQuestionsPage(page)
    questions.wait_for_loaded()

    expect(questions.get_questions()).to_have_count(counted)


def test_the_questions_screen_offers_search_and_a_topic_filter(chapter_questions):
    expect(chapter_questions.get_back_button()).to_be_enabled()
    expect(chapter_questions.get_search_button()).to_be_enabled()
    expect(chapter_questions.get_filter_button()).to_be_enabled()


def test_every_question_is_numbered(chapter_questions):
    total = chapter_questions.question_count()

    expect(chapter_questions.get_question_numbers()).to_have_count(total)
    for index in range(total):
        expect(chapter_questions.get_question_numbers().nth(index)).to_have_text(
            re.compile(r"^\d+$")
        )
        expect(chapter_questions.get_question_text(index)).not_to_be_empty()


# ---------------------------------------------------------------------------
# The answer state tabs
# ---------------------------------------------------------------------------

def test_the_chapter_offers_every_answer_state_tab(chapter_questions):
    expect(chapter_questions.get_state_tabs()).to_have_count(
        len(SubjectQuestionsPage.TABS)
    )

    assert chapter_questions.get_tab_names() == SubjectQuestionsPage.TABS


def test_all_is_the_tab_in_force_to_begin_with(chapter_questions):
    expect(chapter_questions.get_active_state_tab()).to_have_count(1)

    assert chapter_questions.get_active_tab_name() == "All"


def test_every_tab_carries_a_count(chapter_questions):
    for name in SubjectQuestionsPage.TABS:
        expect(chapter_questions.get_tab(name)).to_have_text(
            re.compile(re.escape(name) + r"\s*\(\s*\d+\s*\)")
        )


@pytest.mark.parametrize("state", SubjectQuestionsPage.TABS)
def test_each_tab_lists_exactly_as_many_questions_as_it_counts(
    chapter_questions, state
):
    """The tab is what filters the list, so what it counts and what it shows
    have to be the same thing."""
    expected = chapter_questions.get_tab_count(state)
    chapter_questions.open_tab(state)

    assert chapter_questions.get_active_tab_name() == state
    expect(chapter_questions.get_questions()).to_have_count(expected)

    if expected == 0:
        expect(chapter_questions.get_empty_state()).to_be_visible()


def test_the_answer_state_tabs_add_up_to_the_whole_chapter(chapter_questions):
    answered = sum(
        chapter_questions.get_tab_count(name)
        for name in ["Correct", "Wrong", "I don’t know"]
    )

    assert answered == chapter_questions.get_tab_count("All")


def test_searching_the_questions_narrows_the_list(chapter_questions):
    text = chapter_questions.get_question_text(0).inner_text()
    snippet = searchable_snippet(text)
    if not snippet or len(snippet) < 4:
        pytest.skip("The first question has no plain words to search with")

    chapter_questions.click_search()
    chapter_questions.search(snippet)

    expect(chapter_questions.get_questions().first).to_be_visible()
    assert chapter_questions.find_question(text) is not None

    for listed in chapter_questions.get_question_texts():
        assert snippet.lower() in listed.lower()


def test_the_topic_filter_lists_the_topics_of_the_chapter(chapter_questions):
    chapter_questions.click_filter()

    expect(chapter_questions.get_filter_sheet()).to_be_visible()
    expect(chapter_questions.get_filter_title()).to_have_text("Filter By Topic")
    expect(chapter_questions.get_filter_apply_button()).to_be_visible()
    expect(chapter_questions.get_filter_clear_button()).to_be_visible()

    assert chapter_questions.get_filter_options().count() > 0
    for name in chapter_questions.get_filter_option_names():
        assert name

    chapter_questions.close_filter()

    expect(chapter_questions.get_filter_overlay()).to_have_count(0)


# ---------------------------------------------------------------------------
# A single question
# ---------------------------------------------------------------------------

def test_the_question_opens_with_its_options(subject_question):
    expect(subject_question.get_page()).to_be_visible()
    expect(subject_question.get_question()).not_to_be_empty()
    expect(subject_question.get_choose_label()).to_be_visible()

    total = subject_question.get_options().count()
    assert total >= 2
    expect(subject_question.get_option_numbers()).to_have_count(total)
    for index in range(total):
        expect(subject_question.get_option_texts().nth(index)).not_to_be_empty()


def test_the_question_shows_where_it_sits_in_the_set(subject_question):
    expect(subject_question.get_counter()).to_be_visible()

    assert subject_question.get_current_number() >= 1
    assert subject_question.get_total_number() >= subject_question.get_current_number()


def test_the_question_offers_a_note(subject_question):
    subject_question.click_note()

    expect(subject_question.get_note_editor()).to_be_visible()
    expect(subject_question.get_note_save_button()).to_be_visible()

    subject_question.get_note_close_button().click()

    expect(subject_question.get_note_editor()).to_have_count(0)


def test_the_bookmark_can_be_turned_on_and_off(subject_question):
    """Put back the way it was found: nothing else here depends on a bookmark,
    and leaving one behind would change what the Bookmark tab lists."""
    was_bookmarked = subject_question.is_bookmarked()
    wanted = "Add bookmark" if was_bookmarked else "Remove bookmark"

    subject_question.click_bookmark()
    expect(subject_question.get_bookmark_button()).to_have_attribute(
        "aria-label", wanted
    )
    assert subject_question.is_bookmarked() is not was_bookmarked

    subject_question.click_bookmark()
    expect(subject_question.get_bookmark_button()).to_have_attribute(
        "aria-label", "Remove bookmark" if was_bookmarked else "Add bookmark"
    )


def test_view_solution_waits_for_an_answer(subject_question):
    expect(subject_question.get_view_solution_button()).to_be_visible()
    expect(subject_question.get_view_solution_button()).to_be_disabled()

    assert subject_question.is_solution_available() is False


def test_answering_the_question_enables_view_solution(subject_question):
    subject_question.select_option(0)

    expect(subject_question.get_option(0)).to_have_class(re.compile("qlr-opt-selected"))
    expect(subject_question.get_view_solution_button()).to_be_enabled()

    assert subject_question.is_solution_available()


def test_the_question_filter_offers_every_answer_state(subject_question):
    subject_question.click_filter()

    expect(subject_question.get_filter_sheet()).to_be_visible()
    expect(subject_question.get_filter_rows()).to_have_count(
        len(SubjectQuestionPage.FILTERS)
    )

    assert subject_question.get_filter_names() == SubjectQuestionPage.FILTERS


@pytest.mark.parametrize("state", SubjectQuestionPage.FILTERS)
def test_every_question_filter_can_be_selected(subject_question, state):
    subject_question.click_filter()
    subject_question.select_filter(state)

    expect(subject_question.get_active_filter()).to_contain_text(state)


def test_report_offers_the_reasons_to_choose_from(subject_question):
    subject_question.click_report()

    expect(subject_question.get_report_sheet()).to_be_visible()
    expect(subject_question.get_report_sheet()).to_contain_text("Report Issue")

    for reason in [
        "Incorrect question",
        "Incorrect options",
        "Wrong solution/explanation",
        "Others",
    ]:
        expect(subject_question.get_report_sheet()).to_contain_text(reason)

    # Not sent on purpose: it would raise a real report against the question.
    expect(subject_question.get_report_send_button()).to_be_visible()


# ---------------------------------------------------------------------------
# Study recommendations
# ---------------------------------------------------------------------------

def test_the_footer_offers_the_study_recommendations(subject):
    expect(subject.get_footer()).to_be_visible()
    expect(subject.get_recommendations_button()).to_be_enabled()
    expect(subject.get_recommendations_button()).to_contain_text(
        "Study Recommendations"
    )


def test_the_recommendations_open_in_a_sheet(recommendations):
    expect(recommendations.get_sheet()).to_be_visible()
    expect(recommendations.get_title()).to_have_text("Study Recommendations")
    expect(recommendations.get_subtitle()).to_contain_text("mastery")


def test_every_recommendation_names_a_chapter_of_the_subject(subject, recommendations):
    chapters = [
        subject.get_chapter_title_text(index)
        for index in range(subject.chapter_count())
    ]

    for index in range(recommendations.card_count()):
        expect(recommendations.get_card_title(index)).not_to_be_empty()
        assert recommendations.get_card_title_text(index) in chapters


def test_every_recommendation_counts_the_subtopics_that_are_behind(recommendations):
    for index in range(recommendations.card_count()):
        expect(recommendations.get_status_pill(index)).to_contain_text("Subtopics")

        assert recommendations.get_subtopic_count(index) > 0


def test_every_recommendation_shows_the_study_rate_reached(recommendations):
    for index in range(recommendations.card_count()):
        expect(recommendations.get_study_rate(index)).to_be_visible()
        expect(recommendations.get_study_rate(index)).to_have_text(
            re.compile(r".+\d+\s*%$")
        )


def test_every_recommendation_offers_a_practice(recommendations):
    expect(recommendations.get_practice_buttons()).to_have_count(
        recommendations.card_count()
    )

    for index in range(recommendations.card_count()):
        expect(recommendations.get_practice_button(index)).to_be_enabled()
        expect(recommendations.get_practice_button(index)).to_have_text("Practice Now")


def test_practice_now_opens_the_topic_picker_for_that_chapter(
    page, recommended_chapter, topic_picker
):
    """The practice is rooted at the chapter that was recommended, and opens
    with that chapter already unfolded."""
    recommended = recommended_chapter

    expect(page).to_have_url(AddTopicsPage.SUBJECT_URL_PATTERN)
    expect(topic_picker.get_page()).to_be_visible()
    expect(topic_picker.get_title()).to_have_text("Add topics")

    expect(page).to_have_url(re.compile(re.escape(recommended.replace(" ", "%20"))))
    expect(page.locator(".atp-chapter-open .atp-chapter-title")).to_have_text(
        recommended
    )


# ---------------------------------------------------------------------------
# Subject -> topic -> topic quiz
#
# Out of the Question Library and into a practice. The quiz is started but left
# unanswered, so the questions it drew stay in the pool for the next run.
# ---------------------------------------------------------------------------

def test_a_topic_quiz_carries_the_subject_topic_and_chapter_it_was_built_from(
    page, subject_name, recommended_chapter, topic_picker
):
    recommended = recommended_chapter
    if topic_picker.get_practicable_topics().count() == 0:
        pytest.skip("Every topic of the recommended chapter has been practised")

    topic = re.sub(
        r"^\d+\.\s*",
        "",
        topic_picker.get_practicable_topics()
        .first.locator(".atp-topic-title")
        .inner_text()
        .strip(),
    )
    topic_picker.get_practicable_topics().first.click()
    expect(topic_picker.get_selection_label()).to_contain_text("1")
    topic_picker.click_continue()

    config = PracticeConfigPage(page)
    config.wait_for_loaded()
    config.open_topic_summary()

    expect(config.get_topic_sheet_title()).to_have_text("Selected Topics")
    expect(config.get_sheet_subject()).to_have_text(subject_name)
    expect(config.get_sheet_chapter()).to_have_text(re.compile(re.escape(recommended)))

    assert config.get_sheet_topic_names() == [topic]


def test_the_topic_quiz_runs_as_a_problem_based_quick_practice(
    page, topic_picker
):
    if topic_picker.get_practicable_topics().count() == 0:
        pytest.skip("Every topic of the recommended chapter has been practised")

    topic = re.sub(
        r"^\d+\.\s*",
        "",
        topic_picker.get_practicable_topics()
        .first.locator(".atp-topic-title")
        .inner_text()
        .strip(),
    )
    topic_picker.get_practicable_topics().first.click()
    topic_picker.click_continue()

    config = PracticeConfigPage(page)
    config.wait_for_loaded()

    # Problem based is the route the picker came in on; quick practice is the
    # mode the setup screen offers under it.
    expect(page).to_have_url(re.compile(r"/addtopic/problemBased/practice"))
    expect(config.get_selected_mode()).to_have_count(1)
    assert config.get_selected_mode_name() == "Quick practice"
    expect(config.get_topic_summary()).to_contain_text("1 Topics")

    asked = config.select_smallest_count()
    config.start()

    quiz = PracticeQuestionPage(page)
    quiz.get_take_test_button().wait_for(timeout=30000)

    expect(page).to_have_url(PracticeQuestionPage.URL_PATTERN)
    expect(quiz.get_title()).to_have_text(topic)
    expect(quiz.get_subtitle()).to_have_text("Quick Practice")
    expect(quiz.get_question_total()).to_have_text(str(asked))
