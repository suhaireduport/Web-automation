"""Video player: how it is reached, its controls, and what it remembers.

The player object lives in pages/subtopic_page.py, because a subtopic is the
only thing that opens it; SubtopicPage is the existing player implementation and
is reused here rather than duplicated. What stays in test_subtopic.py is the
subtopic itself: the item strip, the pretest and the checkpoint quiz.

Playback is asserted from the <video> element's own currentTime, paused and
muted rather than from the look of the progress bar.
"""
import re
import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.chapter_page import ChapterPage
from pages.topic_page import TopicPage
from pages.subtopic_page import SubtopicPage, MiniPlayer

MOBILE = "9876543210"

HOME_URL = "https://eduport-react.pages.dev/"
TOPICS_URL_PATTERN = re.compile(
    r"https://eduport-react\.pages\.dev/home/subject/\d+/.+/topics/\d+$"
)
PLAYER_URL_PATTERN = re.compile(
    r"https://eduport-react\.pages\.dev/home/subject/\d+/.+/topics/\d+/player/\d+/.+"
)

DEFAULT_SUBJECT = 0

# Playback keeps running while a test works, so positions are compared with room
# to move rather than exactly.
RESUME_TOLERANCE = 15

# The saved position only ever moves forward: seeking back and leaving does not
# lower it, and a video watched to the end always reopens at the end.
SETTLE_MS = 2500

# Long enough for the app to restore the saved position before a test starts.
RESTORE_MS = 5000
START_POSITION = 5


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture
def topic_page(page):
    """Walk down to a chapter's topic list: subject, chapter, topics."""
    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()
    home_page.open_subject(DEFAULT_SUBJECT)

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
def video_page(page, topic_page):
    """A subtopic that holds nothing but a video, opened at its player."""
    index = topic_page.find_video_only_subtopic()
    if index is None:
        pytest.skip("No video-only subtopic in this chapter")

    topic_page.open_subtopic_at(index)

    video_page = SubtopicPage(page)
    video_page.wait_for_player_loaded()

    # The app restores the saved position a few seconds after the player
    # renders. On a video already watched to the end that restore drops the
    # player onto the replay overlay, which covers every control - and it lands
    # part way through whichever test is running. Let the restore happen, then
    # rewind to a known point so each test starts from the same playing state.
    page.wait_for_timeout(RESTORE_MS)
    for _ in range(3):
        video_page.seek_to(START_POSITION)
        video_page.wait_until_playing()
        # A restore landing late would undo the rewind, so check it held.
        page.wait_for_timeout(1500)
        if video_page.get_replay_overlay().count() == 0:
            break
    expect(video_page.get_replay_overlay()).to_have_count(0)
    return video_page


# ---------------------------------------------------------------------------
# 1. Access paths
# ---------------------------------------------------------------------------

def test_video_player_opens_by_navigating_down_to_a_subtopic(page, topic_page):
    """Subject, chapter, topic, subtopic, and the video that opens is the one
    that was picked."""
    index = topic_page.find_video_only_subtopic()
    if index is None:
        pytest.skip("No video-only subtopic in this chapter")

    expected_title = topic_page.get_all_subtopics().nth(index).inner_text()
    topic_page.open_subtopic_at(index)

    video_page = SubtopicPage(page)
    video_page.wait_for_player_loaded()

    expect(page).to_have_url(PLAYER_URL_PATTERN)
    expect(video_page.get_page()).to_be_visible()
    assert video_page.get_video_title().inner_text().strip() in expected_title


def test_video_player_reopens_the_same_video_from_the_mini_player(page, video_page):
    """Home, mini player, back into the player on the same video."""
    title = video_page.get_video_title().inner_text()
    video_page.seek_to(50)
    video_page.pause()
    left_at = video_page.get_current_time()
    page.wait_for_timeout(4000)

    video_page.click_back()
    page.wait_for_url(TOPICS_URL_PATTERN)
    page.goto(HOME_URL)

    mini_player = MiniPlayer(page)
    expect(mini_player.get_tile()).to_be_visible()
    mini_player.click()

    page.wait_for_url(PLAYER_URL_PATTERN)
    video_page.wait_for_player_loaded()

    expect(page).to_have_url(PLAYER_URL_PATTERN)
    assert video_page.get_video_title().inner_text() == title
    assert video_page.get_current_time() >= left_at - RESUME_TOLERANCE


# ---------------------------------------------------------------------------
# 2. Player UI
# ---------------------------------------------------------------------------

def test_player_shows_the_video(video_page):
    expect(video_page.get_video()).to_be_visible()

    assert video_page.get_duration() > 0


def test_player_shows_video_title(video_page):
    expect(video_page.get_video_title()).not_to_be_empty()


def test_player_has_playback_controls(video_page):
    expect(video_page.get_play_button()).to_be_visible()
    expect(video_page.get_seek_slider()).to_be_attached()
    expect(video_page.get_volume_slider()).to_be_attached()
    expect(video_page.get_mute_button()).to_be_attached()
    expect(video_page.get_settings_button()).to_be_attached()
    expect(video_page.get_fullscreen_button()).to_be_attached()


def test_player_shows_the_current_playback_time(video_page):
    """The readout toggles between time elapsed and time remaining, and the
    remaining form is signed, so both are accepted."""
    expect(video_page.get_current_time_display()).to_have_text(
        re.compile(r"^-?\d{1,2}:\d{2}$")
    )


def test_player_reports_a_total_duration(video_page):
    """The control bar has no duration readout, so the length of the video is
    only available from the media element itself."""
    state = video_page.get_playback_state()

    assert state["duration"] > 0
    assert state["currentTime"] <= state["duration"]


def test_report_issue_button_visible(video_page):
    expect(video_page.get_report_issue_button()).to_be_visible()


def test_rate_now_button_visible(video_page):
    expect(video_page.get_rate_now_button()).to_be_visible()


# ---------------------------------------------------------------------------
# 3. Play and pause
# ---------------------------------------------------------------------------

def test_video_starts_playing_on_its_own(page, topic_page):
    """Opened directly rather than through the video_page fixture, which puts
    the player into a known state and would mask autoplay."""
    index = topic_page.find_video_only_subtopic()
    if index is None:
        pytest.skip("No video-only subtopic in this chapter")

    topic_page.open_subtopic_at(index)

    video_page = SubtopicPage(page)
    video_page.wait_for_player_loaded()
    video_page.wait_until_playing()

    assert video_page.is_paused() is False


def test_pause_stops_playback_where_it_is(video_page):
    video_page.wait_for_time_past(1)
    video_page.pause()

    stopped_at = video_page.get_current_time()
    video_page.page.wait_for_timeout(3000)

    assert video_page.is_paused()
    assert video_page.get_current_time() == pytest.approx(stopped_at, abs=0.5)


def test_play_resumes_from_the_paused_position(video_page):
    video_page.wait_for_time_past(1)
    video_page.pause()
    paused_at = video_page.get_current_time()

    video_page.play()
    video_page.wait_for_time_past(paused_at + 1)

    assert video_page.is_paused() is False
    assert video_page.get_current_time() > paused_at


# ---------------------------------------------------------------------------
# 4. Progress
# ---------------------------------------------------------------------------

def test_progress_advances_stops_and_continues(video_page):
    """The whole cycle in one pass: playing moves, pausing freezes, resuming
    carries on from where it stopped rather than starting over."""
    video_page.wait_until_playing()
    started_at = video_page.get_current_time()

    video_page.wait_for_time_past(started_at + 2)
    playing_at = video_page.get_current_time()
    assert playing_at > started_at

    video_page.pause()
    paused_at = video_page.get_current_time()
    video_page.page.wait_for_timeout(3000)
    assert video_page.get_current_time() == pytest.approx(paused_at, abs=0.5)

    video_page.play()
    video_page.wait_for_time_past(paused_at + 1)

    assert video_page.get_current_time() > paused_at


def test_the_seek_bar_follows_playback(video_page):
    """Plyr drives the seek input from the media element, so its value tracks
    the position as a percentage."""
    video_page.seek_to(60)
    video_page.page.wait_for_timeout(1500)

    seek_value = float(video_page.get_seek_slider().input_value())
    expected = 60 / video_page.get_duration() * 100

    assert seek_value == pytest.approx(expected, abs=2)


# ---------------------------------------------------------------------------
# 5. Pause, leave, reopen
# ---------------------------------------------------------------------------

def test_reopening_a_video_resumes_where_it_was_left(page, video_page):
    """Leaving the player part way through and coming back picks the video up
    again rather than starting it over.

    The mark the app keeps is the furthest point reached, so leaving the video
    earlier than it has already been watched to resumes at that further point,
    not at the spot it was left."""
    player_url = page.url

    # What the backend already holds, read from a fresh load of the player:
    # arriving through the topic list starts the video at nought instead.
    page.goto(player_url)
    video_page.wait_for_player_loaded()
    page.wait_for_timeout(SETTLE_MS)
    already_watched_to = video_page.get_current_time()

    duration = video_page.get_duration()
    target = min(already_watched_to + 60, duration - 20)
    video_page.seek_to(target)
    video_page.pause()
    left_at = video_page.get_current_time()

    # The position reaches the backend a moment after playback settles.
    page.wait_for_timeout(4000)

    video_page.click_back()
    page.wait_for_url(TOPICS_URL_PATTERN)

    page.goto(player_url)
    video_page.wait_for_player_loaded()
    page.wait_for_timeout(SETTLE_MS)
    resumed_at = video_page.get_current_time()

    assert resumed_at > 0, "the video restarted from the beginning"
    assert resumed_at == pytest.approx(
        max(left_at, already_watched_to), abs=RESUME_TOLERANCE
    )


# ---------------------------------------------------------------------------
# 6. Seeking
# ---------------------------------------------------------------------------

def test_seeking_forward_moves_playback_on(video_page):
    """Absolute marks, not an offset: the video reopens wherever it was last
    left, so a relative jump could land past the end."""
    video_page.seek_to(30)
    video_page.page.wait_for_timeout(1500)

    video_page.seek_to(150)
    video_page.page.wait_for_timeout(1500)

    assert video_page.get_current_time() > 140


def test_seeking_backward_moves_playback_back(video_page):
    video_page.seek_to(150)
    video_page.page.wait_for_timeout(1500)

    video_page.seek_to(20)
    video_page.page.wait_for_timeout(1500)

    assert video_page.get_current_time() < 40


def test_playback_carries_on_after_seeking(video_page):
    video_page.seek_to(40)
    video_page.play()
    video_page.wait_for_time_past(42)

    state = video_page.get_playback_state()

    assert state["paused"] is False
    assert state["currentTime"] > 40


# ---------------------------------------------------------------------------
# 7. Volume
# ---------------------------------------------------------------------------

def test_volume_control_is_available(video_page):
    video_page.show_controls()

    expect(video_page.get_volume_slider()).to_be_visible()


def test_volume_can_be_lowered_and_raised(video_page):
    video_page.set_volume(0.3)
    assert video_page.get_volume() == pytest.approx(0.3, abs=0.05)

    video_page.set_volume(0.9)
    assert video_page.get_volume() == pytest.approx(0.9, abs=0.05)


# ---------------------------------------------------------------------------
# 10. Mute and unmute
# ---------------------------------------------------------------------------

def test_mute_and_unmute_the_video(video_page):
    video_page.wait_until_playing()
    assert video_page.is_muted() is False

    video_page.click_mute()
    assert video_page.is_muted()

    video_page.click_mute()
    assert video_page.is_muted() is False


def test_muting_does_not_stop_playback(video_page):
    video_page.wait_until_playing()
    before = video_page.get_current_time()

    video_page.click_mute()
    video_page.wait_for_time_past(before + 1)

    assert video_page.is_muted()
    assert video_page.is_paused() is False


# ---------------------------------------------------------------------------
# 8. Quality
# ---------------------------------------------------------------------------

def test_quality_options_are_offered(video_page):
    labels = video_page.get_quality_labels()

    assert "Auto" in labels
    assert len(labels) > 1


def test_choosing_another_quality_is_applied(video_page):
    labels = video_page.get_quality_labels()
    if len(labels) < 2:
        pytest.skip("This video is served at a single quality")

    video_page.wait_until_playing()
    video_page.select_quality("480")
    video_page.close_settings()

    assert video_page.get_submenu_value("Quality") == "480p"


def test_playback_survives_a_quality_change(video_page):
    if len(video_page.get_quality_labels()) < 2:
        pytest.skip("This video is served at a single quality")

    video_page.close_settings()
    video_page.seek_to(30)
    video_page.wait_until_playing()

    video_page.select_quality("360")
    video_page.close_settings()
    video_page.page.wait_for_timeout(2500)

    state = video_page.get_playback_state()

    assert state["currentTime"] > 25
    assert state["duration"] > 0


# ---------------------------------------------------------------------------
# 9. Playback speed
# ---------------------------------------------------------------------------

def test_speed_options_are_offered(video_page):
    labels = video_page.get_speed_labels()

    assert "Normal" in labels
    assert len(labels) > 1


def test_choosing_another_speed_is_applied_and_can_be_restored(video_page):
    video_page.select_speed("1.5")
    video_page.close_settings()
    assert video_page.get_playback_rate() == pytest.approx(1.5)

    video_page.close_settings()
    video_page.select_speed("1")
    video_page.close_settings()

    assert video_page.get_playback_rate() == pytest.approx(1.0)


def test_the_settings_menu_reports_the_chosen_speed(video_page):
    video_page.select_speed("2")
    video_page.close_settings()

    assert video_page.get_submenu_value("Speed") == "2×"

    video_page.close_settings()
    video_page.select_speed("1")
    video_page.close_settings()


# ---------------------------------------------------------------------------
# 11. Fullscreen
# ---------------------------------------------------------------------------

def test_fullscreen_control_is_available(video_page):
    video_page.show_controls()

    expect(video_page.get_fullscreen_button()).to_be_visible()
    expect(video_page.get_fullscreen_button()).to_be_enabled()


def test_fullscreen_keeps_the_video_playing(video_page):
    """Chromium refuses the fullscreen request without a real window, so the
    state itself is only asserted when the browser actually grants it. What is
    checked either way is that the video is not disturbed."""
    video_page.wait_until_playing()
    before = video_page.get_current_time()

    video_page.click_fullscreen()
    if video_page.is_fullscreen():
        expect(video_page.get_plyr()).to_have_class(re.compile("plyr--fullscreen"))

    video_page.wait_for_time_past(before + 1)
    assert video_page.is_paused() is False

    video_page.click_fullscreen()

    assert video_page.is_fullscreen() is False
    assert video_page.get_current_time() > before


# ---------------------------------------------------------------------------
# 12. Notes
# ---------------------------------------------------------------------------

def test_notes_opens_the_document_in_a_new_tab(page, video_page):
    notes = video_page.get_notes_link()
    if notes.count() == 0:
        pytest.skip("This lesson has no notes attachment")

    expect(notes.first).to_have_attribute("target", "_blank")
    href = notes.first.get_attribute("href")
    assert href.startswith("http")

    video_page.wait_until_playing()
    before = video_page.get_current_time()

    with page.context.expect_page() as new_tab:
        notes.first.click()
    notes_tab = new_tab.value
    notes_tab.wait_for_load_state("domcontentloaded")

    assert notes_tab.url == href
    assert len(page.context.pages) == 2

    notes_tab.close()
    page.bring_to_front()

    # The player tab is untouched by the trip to the notes.
    expect(page).to_have_url(PLAYER_URL_PATTERN)
    assert video_page.get_current_time() >= before
    assert video_page.is_paused() is False


# ---------------------------------------------------------------------------
# 13. Mini player
# ---------------------------------------------------------------------------

def test_mini_player_hidden_while_on_the_player(video_page):
    expect(MiniPlayer(video_page.page).get_tile()).to_have_count(0)


def test_mini_player_appears_after_leaving_the_player(page, video_page):
    """The tile lives in the main app shell, so it shows up on Home rather than
    on the topic list you land on when you back out of the player."""
    video_page.click_back()
    page.wait_for_url(TOPICS_URL_PATTERN)
    page.goto(HOME_URL)

    expect(MiniPlayer(page).get_tile()).to_be_visible()


def test_mini_player_shows_the_video_it_is_holding(page, video_page):
    title = video_page.get_video_title().inner_text()

    video_page.click_back()
    page.wait_for_url(TOPICS_URL_PATTERN)
    page.goto(HOME_URL)

    mini_player = MiniPlayer(page)

    expect(mini_player.get_title()).to_have_text(title)
    # The type label varies with the content ("Subtopic", "Adaptive Video", ...)
    expect(mini_player.get_type()).not_to_be_empty()


def test_mini_player_not_shown_on_the_topic_list(page, video_page):
    """The topic list has its own shell and deliberately has no mini player."""
    video_page.click_back()
    page.wait_for_url(TOPICS_URL_PATTERN)

    expect(MiniPlayer(page).get_tile()).to_have_count(0)


def test_mini_player_can_be_closed(page, video_page):
    video_page.click_back()
    page.wait_for_url(TOPICS_URL_PATTERN)
    page.goto(HOME_URL)

    mini_player = MiniPlayer(page)
    expect(mini_player.get_tile()).to_be_visible()

    mini_player.close()

    expect(mini_player.get_tile()).to_be_hidden()


# ---------------------------------------------------------------------------
# 14. Navigation and state
# ---------------------------------------------------------------------------

def test_back_returns_to_the_topic_list(page, video_page):
    video_page.click_back()

    expect(page).to_have_url(TOPICS_URL_PATTERN)


def test_the_video_survives_a_trip_to_home_and_back(page, video_page):
    """Player, home, mini player, player: same video, no lost progress."""
    title = video_page.get_video_title().inner_text()
    video_page.seek_to(70)
    video_page.pause()
    left_at = video_page.get_current_time()
    page.wait_for_timeout(4000)

    video_page.click_back()
    page.wait_for_url(TOPICS_URL_PATTERN)
    page.goto(HOME_URL)
    MiniPlayer(page).click()

    page.wait_for_url(PLAYER_URL_PATTERN)
    video_page.wait_for_player_loaded()

    assert video_page.get_video_title().inner_text() == title
    assert video_page.get_current_time() >= left_at - RESUME_TOLERANCE
