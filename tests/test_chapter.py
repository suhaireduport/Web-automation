import re
import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.chapter_page import ChapterPage

MOBILE = "8893963137"
OTP = "430582"

OTP_URL = "https://eduport-react.pages.dev/otp"
HOME_URL = "https://eduport-react.pages.dev/"

CHAPTER_URL_PATTERN = re.compile(
    r"https://eduport-react\.pages\.dev/home/subject/\d+/.+"
)
TOPICS_URL_PATTERN = re.compile(
    r"https://eduport-react\.pages\.dev/home/subject/\d+/.+/topics/\d+"
)


# Which subject the tests open. Override per test with
# @pytest.mark.parametrize("subject", ["Physics"], indirect=True)
#   int  -> position on Home (0 = first)
#   str  -> exact subject name, e.g. "Physics"
DEFAULT_SUBJECT = 0


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture
def subject(request):
    return getattr(request, "param", DEFAULT_SUBJECT)


@pytest.fixture
def logged_in_home(page):

    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()
    return home_page


@pytest.fixture
def chapter_page(page, logged_in_home, subject):
    logged_in_home.open_subject(subject)
    page.wait_for_url(CHAPTER_URL_PATTERN)

    chapters = ChapterPage(page)
    chapters.wait_for_chapters_loaded()
    return chapters


def test_chapter_page_opens(page, chapter_page):
    expect(page).to_have_url(CHAPTER_URL_PATTERN)
    expect(chapter_page.get_shell()).to_be_visible()
    expect(chapter_page.get_title()).not_to_be_empty()


def test_chapter_page_title_matches_subject(page, chapter_page):
    subject_name = chapter_page.get_title().inner_text().strip()

    # The subject name is carried in the URL, so the header and route agree.
    assert subject_name.replace(" ", "%20") in page.url or subject_name in page.url

    print("Subject:", subject_name)


def test_back_button_visible(chapter_page):
    expect(chapter_page.get_back_button()).to_be_visible()
    expect(chapter_page.get_back_button()).to_be_enabled()


def test_chapters_listed(chapter_page):
    count = chapter_page.chapter_count()

    assert count > 0
    expect(chapter_page.get_chapters().first).to_be_visible()

    print("Chapter count:", count)


def test_chapter_numbers_are_sequential(chapter_page):
    count = chapter_page.chapter_count()

    expect(chapter_page.get_chapter_numbers()).to_have_text(
        [str(i + 1) for i in range(count)]
    )


def test_every_chapter_has_a_title(chapter_page):
    count = chapter_page.chapter_count()

    for i in range(count):
        expect(chapter_page.get_chapter_title(i)).not_to_be_empty()

    print("Chapters:", chapter_page.get_chapter_titles().all_inner_texts())


def test_every_chapter_has_a_progress_bar(chapter_page):
    count = chapter_page.chapter_count()

    for i in range(count):
        expect(chapter_page.get_progress_bar(i)).to_be_visible()


def test_progress_fill_is_a_percentage(chapter_page):
    count = chapter_page.chapter_count()

    for i in range(count):
        assert re.fullmatch(r"\d+(\.\d+)?%", chapter_page.get_progress_width(i))


def test_completed_count_format(chapter_page):
    count = chapter_page.chapter_count()

    for i in range(count):
        expect(chapter_page.get_completed_text(i)).to_have_text(
            re.compile(r"^\d+/\d+ Completed$")
        )


def test_locked_chapters_show_lock_icon(chapter_page):
    locked = chapter_page.get_locked_chapters()

    if locked.count() == 0:
        pytest.skip("No locked chapters for this subject")

    expect(chapter_page.get_lock_icons()).to_have_count(locked.count())

    print("Locked chapters:", locked.count())


def test_unlocked_chapters_have_no_lock_icon(chapter_page):
    unlocked = chapter_page.get_unlocked_chapters()

    if unlocked.count() == 0:
        pytest.skip("Every chapter is locked for this subject")

    for i in range(unlocked.count()):
        expect(unlocked.nth(i).locator(".ch-item-lock")).to_have_count(0)


def test_locked_and_unlocked_add_up(chapter_page):
    total = chapter_page.chapter_count()
    locked = chapter_page.get_locked_chapters().count()
    unlocked = chapter_page.get_unlocked_chapters().count()

    assert locked + unlocked == total


def test_open_unlocked_chapter(page, chapter_page):
    unlocked = chapter_page.get_unlocked_chapters()

    if unlocked.count() == 0:
        pytest.skip("Every chapter is locked for this subject")

    unlocked.first.click()

    expect(page).to_have_url(TOPICS_URL_PATTERN)


def test_locked_chapter_does_not_open(page, chapter_page):
    locked = chapter_page.get_locked_chapters()

    if locked.count() == 0:
        pytest.skip("No locked chapters for this subject")

    current_url = page.url
    locked.first.click()
    page.wait_for_timeout(2000)

    expect(page).to_have_url(current_url)
    expect(chapter_page.get_chapters().first).to_be_visible()


def test_open_chapter_page_directly(page, chapter_page):
    chapter_url = page.url
    expected_titles = chapter_page.get_chapter_titles().all_inner_texts()

    chapter_page.open(chapter_url)

    expect(page).to_have_url(chapter_url)
    expect(chapter_page.get_chapter_titles()).to_have_text(expected_titles)


def test_back_button_returns_to_home(page, chapter_page):
    chapter_page.click_back()

    expect(page).to_have_url(HOME_URL)


# ---------------------------------------------------------------------------
# Selecting which subject to open
# ---------------------------------------------------------------------------

def test_select_subject_by_position(page, logged_in_home):
    """By order on Home: 0 is the first subject card."""
    logged_in_home.open_subject(0)
    page.wait_for_url(CHAPTER_URL_PATTERN)

    chapters = ChapterPage(page)
    chapters.wait_for_chapters_loaded()

    expect(chapters.get_chapters().first).to_be_visible()
    print("first subject ->", page.url)


def test_select_subject_by_name(page, logged_in_home):
    """By exact name. Subjects differ per course, so pick one that exists."""
    names = logged_in_home.get_subject_names()
    print("Available subjects:", names)

    logged_in_home.open_subject(names[-1])
    page.wait_for_url(CHAPTER_URL_PATTERN)

    chapters = ChapterPage(page)
    chapters.wait_for_chapters_loaded()

    expect(chapters.get_chapters().first).to_be_visible()


def test_select_subject_by_id(page, logged_in_home):
    """By id: read it off the URL once, then deep link straight there."""
    logged_in_home.open_subject(0)
    page.wait_for_url(CHAPTER_URL_PATTERN)

    chapters = ChapterPage(page)
    chapters.wait_for_chapters_loaded()

    subject_id = chapters.get_subject_id()
    expected_titles = chapters.get_chapter_titles().all_inner_texts()
    assert subject_id is not None

    chapters.open_by_id(subject_id, "Chapters")

    expect(chapters.get_chapter_titles()).to_have_text(expected_titles)
    print("subject id", subject_id, "->", page.url)


@pytest.mark.parametrize("subject", [0, 1], indirect=True)
def test_chapters_load_for_several_subjects(chapter_page, subject):
    """The same fixture, pointed at a different subject per run."""
    assert chapter_page.chapter_count() > 0
    print("subject", subject, "chapters:", chapter_page.chapter_count())
