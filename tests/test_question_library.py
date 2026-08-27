"""Question Library landing screen.

Only the screen you arrive at: its header, the Info dialog, the four section
cards and the subject list. What each section leads to is not covered here.

test_home.py already checks that the Home resource button routes here, so that
is not repeated; these start from the landing screen itself.
"""
import re
import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.question_library_page import QuestionLibraryPage

MOBILE = "9876543210"

HOME_URL = "https://eduport-react.pages.dev/"
QUESTION_LIBRARY_URL = QuestionLibraryPage.URL

# The four cards above the subject list, in the order the screen shows them.
SECTIONS = ["My Notes", "Bookmarks", "Mistake Book", "Exams"]

# The areas the Info dialog explains. It names Bookmark in the singular, where
# the card on the screen behind it says Bookmarks.
INFO_TOPICS = ["Question Library", "Mistake book", "Bookmark", "My Notes"]


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture
def question_library(page):
    """Opened the way a student reaches it, from the Home resources."""
    home_page = HomePage(page)
    # Home is handed over on domcontentloaded, so wait for it to render before
    # reaching for a resource button near the bottom of it.
    home_page.get_subjects().first.wait_for()
    home_page.get_question_library().scroll_into_view_if_needed()
    home_page.get_question_library().click()
    page.wait_for_url(QUESTION_LIBRARY_URL)

    question_library = QuestionLibraryPage(page)
    question_library.wait_for_loaded()
    return question_library


@pytest.fixture
def info_dialog(question_library):
    question_library.click_info()
    expect(question_library.get_info_dialog()).to_be_visible()
    return question_library


# ---------------------------------------------------------------------------
# Reaching the screen
# ---------------------------------------------------------------------------

def test_question_library_opens_from_home(page, question_library):
    expect(page).to_have_url(QUESTION_LIBRARY_URL)
    expect(question_library.get_page()).to_be_visible()
    expect(question_library.get_header()).to_be_visible()


def test_question_library_shows_its_title(question_library):
    expect(question_library.get_title()).to_have_text("Question Library")


def test_question_library_header_offers_back_and_info(question_library):
    expect(question_library.get_back_button()).to_be_visible()
    expect(question_library.get_back_button()).to_be_enabled()
    expect(question_library.get_info_button()).to_be_visible()
    expect(question_library.get_info_button()).to_be_enabled()


def test_back_returns_to_home(page, question_library):
    question_library.click_back()

    expect(page).to_have_url(HOME_URL)
    expect(HomePage(page).get_subjects().first).to_be_visible()


# ---------------------------------------------------------------------------
# Info dialog
# ---------------------------------------------------------------------------

def test_info_button_opens_the_how_it_works_dialog(question_library):
    question_library.click_info()

    expect(question_library.get_info_dialog()).to_be_visible()
    expect(question_library.get_info_dialog()).to_have_attribute("role", "dialog")
    expect(question_library.get_info_title()).to_have_text("How it works?")
    expect(question_library.get_info_close_button()).to_be_visible()


def test_info_dialog_describes_each_area(info_dialog):
    expect(info_dialog.get_info_cards()).to_have_count(len(INFO_TOPICS))

    assert info_dialog.get_info_card_title_texts() == INFO_TOPICS

    for topic in INFO_TOPICS:
        expect(info_dialog.get_info_card(topic)).to_be_visible()


def test_info_dialog_explains_what_the_library_holds(info_dialog):
    description = info_dialog.get_info_card("Question Library").locator(".qlh-card-desc")

    expect(description).to_contain_text("questions")
    expect(description).to_contain_text("previously attempted")


def test_every_info_topic_carries_a_description(info_dialog):
    descriptions = info_dialog.get_info_card_descriptions()

    expect(descriptions).to_have_count(len(INFO_TOPICS))
    for index in range(descriptions.count()):
        expect(descriptions.nth(index)).not_to_be_empty()


def test_closing_the_info_dialog_leaves_the_screen_usable(page, info_dialog):
    info_dialog.close_info()

    expect(info_dialog.get_info_dialog()).to_have_count(0)
    expect(page).to_have_url(QUESTION_LIBRARY_URL)
    expect(info_dialog.get_title()).to_have_text("Question Library")
    expect(info_dialog.get_cards()).to_have_count(len(SECTIONS))

    # Still interactive rather than merely still on screen.
    expect(info_dialog.get_info_button()).to_be_enabled()
    info_dialog.click_info()
    expect(info_dialog.get_info_dialog()).to_be_visible()


# ---------------------------------------------------------------------------
# Section cards
# ---------------------------------------------------------------------------

def test_question_library_shows_its_main_sections(question_library):
    expect(question_library.get_cards()).to_have_count(len(SECTIONS))

    assert question_library.get_card_title_texts() == SECTIONS


@pytest.mark.parametrize("section", SECTIONS)
def test_section_card_is_shown_and_clickable(question_library, section):
    card = question_library.get_card(section)

    expect(card).to_have_count(1)
    expect(card).to_be_visible()
    expect(card).to_be_enabled()
    expect(question_library.get_card_icon(section)).to_be_visible()


@pytest.mark.parametrize("section", SECTIONS)
def test_section_card_shows_how_many_it_holds(question_library, section):
    expect(question_library.get_card_count(section)).to_have_text(re.compile(r"^\d+$"))


# ---------------------------------------------------------------------------
# Subjects
# ---------------------------------------------------------------------------

def test_question_library_lists_subjects(question_library):
    expect(question_library.get_subjects_section_title()).to_have_text("Subjects")

    if question_library.subject_count() == 0:
        pytest.skip("This account has no subject questions yet")

    expect(question_library.get_subject_cards().first).to_be_visible()


def test_every_subject_shows_a_name_and_a_question_count(question_library):
    total = question_library.subject_count()
    if total == 0:
        pytest.skip("This account has no subject questions yet")

    expect(question_library.get_subject_names()).to_have_count(total)
    expect(question_library.get_subject_counts()).to_have_count(total)

    for index in range(total):
        expect(question_library.get_subject_names().nth(index)).not_to_be_empty()
        expect(question_library.get_subject_counts().nth(index)).to_have_text(
            re.compile(r"Questions:\s*\d+")
        )
