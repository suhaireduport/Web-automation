import re
import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.chapter_page import ChapterPage
from pages.topic_page import TopicPage

MOBILE = "8893963137"
OTP = "430582"

OTP_URL = "https://eduport-react.pages.dev/otp"
HOME_URL = "https://eduport-react.pages.dev/"

CHAPTER_URL_PATTERN = re.compile(
    r"https://eduport-react\.pages\.dev/home/subject/\d+/[^/]+$"
)
TOPICS_URL_PATTERN = re.compile(
    r"https://eduport-react\.pages\.dev/home/subject/\d+/.+/topics/\d+$"
)
PLAYER_URL_PATTERN = re.compile(
    r"https://eduport-react\.pages\.dev/home/subject/\d+/.+/topics/\d+/player/\d+/.+"
)

# Which subject to walk into. int = position on Home, str = exact subject name.
DEFAULT_SUBJECT = 0


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture
def subject(request):
    return getattr(request, "param", DEFAULT_SUBJECT)


@pytest.fixture
def topic_page(page, subject):

    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()
    home_page.open_subject(subject)

    chapter_page = ChapterPage(page)
    chapter_page.wait_for_chapters_loaded()

    unlocked = chapter_page.get_unlocked_chapters()
    if unlocked.count() == 0:
        pytest.skip("Every chapter is locked for this subject")
    unlocked.first.click()

    topics = TopicPage(page)
    topics.wait_for_topics_loaded()
    return topics


def test_topic_page_opens(page, topic_page):
    expect(page).to_have_url(TOPICS_URL_PATTERN)
    expect(topic_page.get_page()).to_be_visible()
    expect(topic_page.get_title()).not_to_be_empty()

    print("Chapter:", topic_page.get_title().inner_text())


def test_header_shows_subject_icon(topic_page):
    expect(topic_page.get_subject_icon()).to_be_visible()


def test_back_button_returns_to_chapter_page(page, topic_page):
    topic_page.click_back()

    expect(page).to_have_url(CHAPTER_URL_PATTERN)


def test_progress_bar_visible(topic_page):
    expect(topic_page.get_progress_bar()).to_be_visible()
    assert re.fullmatch(r"\d+(\.\d+)?%", topic_page.get_progress_width())


def test_lessons_completed_format(topic_page):
    expect(topic_page.get_lessons_completed()).to_have_text(
        re.compile(r"^\d+/\d+ Lessons Completed$")
    )


def test_topics_listed(topic_page):
    count = topic_page.topic_count()

    assert count > 0
    expect(topic_page.get_topics().first).to_be_visible()

    print("Topic count:", count)


def test_topic_numbers_are_sequential(topic_page):
    count = topic_page.topic_count()

    expect(topic_page.get_topic_numbers()).to_have_text(
        [str(i + 1) for i in range(count)]
    )


def test_every_topic_has_a_title(topic_page):
    count = topic_page.topic_count()

    for i in range(count):
        expect(topic_page.get_topic_title(i)).not_to_be_empty()

    print("Topics:", topic_page.get_topic_titles().all_inner_texts()[:5])


def test_one_topic_expanded_by_default(topic_page):
    """The app opens the topic to continue from, not necessarily the first."""
    expanded = topic_page.get_expanded_topic_index()

    assert expanded is not None
    expect(topic_page.get_expanded_topics()).to_have_count(1)
    expect(topic_page.get_topic_content(expanded)).to_be_visible()

    print("Auto-expanded topic:", expanded,
          topic_page.get_topic_title(expanded).inner_text())


def test_collapse_the_expanded_topic(topic_page):
    expanded = topic_page.get_expanded_topic_index()
    assert expanded is not None

    topic_page.toggle_topic(expanded)

    expect(topic_page.get_topic_content(expanded)).to_have_count(0)


def test_expand_a_collapsed_topic(topic_page):
    collapsed = topic_page.get_collapsed_topic_index()

    if collapsed is None:
        pytest.skip("Every topic is already expanded")

    topic_page.toggle_topic(collapsed)

    expect(topic_page.get_topic_content(collapsed)).to_be_visible()


def test_topics_are_independent_not_an_accordion(topic_page):
    """Opening a second topic leaves the already-open one open."""
    expanded = topic_page.get_expanded_topic_index()
    collapsed = topic_page.get_collapsed_topic_index()

    if expanded is None or collapsed is None:
        pytest.skip("Need one open and one closed topic")

    expect(topic_page.get_expanded_topics()).to_have_count(1)

    topic_page.toggle_topic(collapsed)

    expect(topic_page.get_expanded_topics()).to_have_count(2)
    expect(topic_page.get_topic_content(expanded)).to_be_visible()


def test_expanded_topic_shows_subtopics(topic_page):
    expanded = topic_page.get_expanded_topic_index()
    subtopics = topic_page.get_subtopics(expanded)

    expect(subtopics.first).to_be_visible()
    assert subtopics.count() > 0

    print("Subtopics in topic", expanded, ":", subtopics.count())


def test_subtopic_has_title_and_duration(topic_page):
    expanded = topic_page.get_expanded_topic_index()

    expect(topic_page.get_subtopic_title(expanded)).not_to_be_empty()
    expect(topic_page.get_subtopic_duration(expanded)).to_have_text(
        re.compile(r"^(\d+:)?\d{1,2}:\d{2}$")
    )


def test_subtopic_shows_progress_ring(topic_page):
    expect(topic_page.get_progress_rings().first).to_be_visible()


def test_start_here_button_visible(topic_page):
    expect(topic_page.get_start_here_button()).to_be_visible()
    expect(topic_page.get_start_here_button()).to_be_enabled()


def test_open_subtopic_opens_player(page, topic_page):
    topic_page.click_subtopic(topic_page.get_expanded_topic_index())

    expect(page).to_have_url(PLAYER_URL_PATTERN)


def test_start_here_opens_player(page, topic_page):
    topic_page.click_start_here()

    expect(page).to_have_url(PLAYER_URL_PATTERN)


def test_open_topics_page_directly(page, topic_page):
    topics_url = page.url
    expected_titles = topic_page.get_topic_titles().all_inner_texts()

    topic_page.open(topics_url)

    expect(page).to_have_url(topics_url)
    expect(topic_page.get_topic_titles()).to_have_text(expected_titles)
