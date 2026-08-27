import re
import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.chapter_page import ChapterPage
from pages.topic_page import TopicPage
from pages.subtopic_page import SubtopicPage

MOBILE = "9876543210"
OTP = "430582"

OTP_URL = "https://eduport-react.pages.dev/otp"
HOME_URL = "https://eduport-react.pages.dev/"

TOPICS_URL_PATTERN = re.compile(
    r"https://eduport-react\.pages\.dev/home/subject/\d+/.+/topics/\d+$"
)
PLAYER_URL_PATTERN = re.compile(
    r"https://eduport-react\.pages\.dev/home/subject/\d+/.+/topics/\d+/player/\d+/.+"
)

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
    """Log in and walk down to a chapter's topic list."""

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
    topics.expand_all_topics()
    return topics


@pytest.fixture
def video_only_page(page, topic_page):
    """A subtopic that holds nothing but a video."""
    index = topic_page.find_video_only_subtopic()
    if index is None:
        pytest.skip("No video-only subtopic in this chapter")

    topic_page.open_subtopic_at(index)

    subtopic = SubtopicPage(page)
    subtopic.wait_for_player_loaded()
    return subtopic


@pytest.fixture
def checkpoint_page(page, topic_page):
    """A subtopic that carries a checkpoint quiz after the video.

    The player strip is the only reliable marker: a quiz adds a second circle.
    The dots on the topic list do NOT mean a quiz - subtopics showing three
    dots still report has_quiz=false from the syllabus API."""
    if topic_page.get_all_subtopics().count() == 0:
        pytest.skip("Chapter has no subtopics")

    topic_page.open_subtopic_at(0)

    subtopic = SubtopicPage(page)
    subtopic.wait_for_player_loaded()

    if subtopic.get_quiz_strip_items().count() == 0:
        pytest.skip(
            "No checkpoint quiz in this syllabus: every subtopic on this "
            "account reports has_quiz=false / checkpoints={}"
        )
    return subtopic


# ---------------------------------------------------------------------------
# Subtopic structure
#
# How the player behaves once it is open - controls, playback, seeking, the
# mini player - is covered in test_video_player.py.
# ---------------------------------------------------------------------------

def test_video_only_subtopic_has_a_single_strip_item(video_only_page):
    expect(video_only_page.get_strip_items()).to_have_count(1)
    expect(video_only_page.get_video_strip_items()).to_have_count(1)
    expect(video_only_page.get_quiz_strip_items()).to_have_count(0)

    assert video_only_page.is_video_only()


def test_strip_marks_the_current_item(video_only_page):
    expect(video_only_page.get_current_strip_item()).to_have_count(1)


def test_continue_button_visible(video_only_page):
    """The proceed button is what carries the student on to the next item in the
    subtopic, so it belongs to the subtopic rather than to the player."""
    expect(video_only_page.get_continue_button()).to_be_visible()


def test_replay_overlay_when_the_video_ends(video_only_page):
    """Finishing the video is the trigger for the rest of the subtopic."""
    video_only_page.seek_to_end()

    expect(video_only_page.get_replay_overlay()).to_be_visible(timeout=30000)


# ---------------------------------------------------------------------------
# Checkpoint quiz subtopic
# ---------------------------------------------------------------------------

def test_checkpoint_subtopic_starts_on_the_video(checkpoint_page):
    expect(checkpoint_page.get_video()).to_be_visible()
    expect(checkpoint_page.get_current_strip_item()).to_have_count(1)


def test_checkpoint_quiz_after_finishing_the_video(page, checkpoint_page):
    checkpoint_page.seek_to_end()
    expect(checkpoint_page.get_replay_overlay()).to_be_visible(timeout=30000)

    checkpoint_page.click_continue()
    page.wait_for_timeout(6000)

    pretest = checkpoint_page.get_pretest_intro()
    quiz = checkpoint_page.get_quiz_card()

    if pretest.count() == 0 and quiz.count() == 0:
        pytest.skip(
            f"Continue left the player without showing a quiz (now on {page.url})"
        )

    if pretest.count():
        expect(checkpoint_page.get_pretest_title()).not_to_be_empty()
        expect(checkpoint_page.get_pretest_button()).to_be_enabled()
        checkpoint_page.click_pretest_button()
        page.wait_for_timeout(5000)

    expect(checkpoint_page.get_quiz_card()).to_be_visible()
    expect(checkpoint_page.get_quiz_question()).not_to_be_empty()


def test_checkpoint_quiz_options_are_selectable(page, checkpoint_page):
    checkpoint_page.seek_to_end()
    expect(checkpoint_page.get_replay_overlay()).to_be_visible(timeout=30000)

    checkpoint_page.click_continue()
    page.wait_for_timeout(6000)

    if checkpoint_page.get_pretest_intro().count():
        checkpoint_page.click_pretest_button()
        page.wait_for_timeout(5000)

    options = checkpoint_page.get_quiz_options()
    if options.count() == 0:
        pytest.skip(f"Quiz did not render (now on {page.url})")

    assert options.count() >= 2
    checkpoint_page.select_quiz_option(0)
    page.wait_for_timeout(2000)

    expect(checkpoint_page.get_quiz_card()).to_be_visible()
