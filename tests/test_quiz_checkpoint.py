"""The checkpoint quiz: the question a subtopic puts after its video.

Not a practice. It is part of the subtopic rather than something started from
the Practice screen, it is reached by watching the video to the end, and it has
no rules screen, no submit button and no I don't know: picking an option is the
answer, and the card freezes on the spot with the right option marked and the
solution offered.

Each checkpoint is answered once and stays answered. Reopening the subtopic
shows the same card frozen, which means the answering half of this file needs a
checkpoint nobody has reached yet - and on an account the suite has been run
against, there may not be one. Those tests look for a fresh checkpoint across
the subjects and stand down naming what they found when every one is spent. The
frozen card is always there to be read, so what a checkpoint looks like once
answered is checked whatever state the account is in.

What is deliberately not here, because it is already covered:
  the video player and the strip are in test_video_player.py; the subtopic's
  own structure and its pretest are in test_subtopic.py; bookmarks and notes as
  Question Library data are in test_ql_bookmark.py and test_ql_my_notes.py.
  What is here is the quiz card itself.
"""
import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect

from conftest import STUDENT_MOBILE
from pages.chapter_page import ChapterPage
from pages.home_page import HomePage
from pages.leaderboard_page import read_balance, read_coin_log
from pages.subtopic_page import SubtopicPage
from pages.topic_page import TopicPage

HOME_URL = "https://eduport-react.pages.dev/"

# How far to look for a checkpoint. A course carries far more subtopics than a
# test can open, so the search is bounded and says so when it gives up.
SUBJECTS_TO_TRY = 3
SUBTOPICS_TO_TRY = 6

PER_CORRECT = 4
PER_WRONG = -1


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(STUDENT_MOBILE)


def walk_to_subtopics(page, subject_index):
    """Home -> a subject -> its first unlocked chapter -> the topic list."""
    page.goto(HOME_URL, wait_until="domcontentloaded")
    home = HomePage(page)
    home.get_subjects().first.wait_for(timeout=30000)
    if subject_index >= home.get_subjects().count():
        return None
    home.open_subject(subject_index)

    chapters = ChapterPage(page)
    chapters.wait_for_chapters_loaded()
    unlocked = chapters.get_unlocked_chapters()
    if unlocked.count() == 0:
        return None
    unlocked.first.click()

    topics = TopicPage(page)
    topics.wait_for_topics_loaded()
    topics.expand_all_topics()
    return topics


def find_checkpoint(page, answered=None):
    """A subtopic carrying a checkpoint quiz, opened on its card.

    answered says which kind is wanted - True for one already taken, False for
    one nobody has reached, None for either. Returns the subtopic page, or a
    string saying what the search turned up instead."""
    looked_at = 0
    with_quiz = 0
    pretests = 0
    not_loading = 0

    for subject_index in range(SUBJECTS_TO_TRY):
        topics = walk_to_subtopics(page, subject_index)
        if topics is None:
            continue

        subtopics = topics.get_all_subtopics()
        for index in range(min(subtopics.count(), SUBTOPICS_TO_TRY)):
            if index:
                page.go_back()
                topics.wait_for_topics_loaded()
                topics.expand_all_topics()

            topics.open_subtopic_at(index)
            subtopic = SubtopicPage(page)
            looked_at += 1

            try:
                on_video = opens_on_the_video(subtopic)
            except PlaywrightTimeoutError:
                not_loading += 1
                continue
            if not on_video:
                pretests += 1
                continue

            if subtopic.get_quiz_strip_items().count() == 0:
                continue

            with_quiz += 1
            found = open_quiz_card(subtopic)
            if found and (answered is None or subtopic.quiz_is_answered() == answered):
                return subtopic

    wanted = {True: "an answered", False: "an unanswered", None: "a"}[answered]
    return (
        f"No subtopic offered {wanted} checkpoint quiz: {looked_at} subtopics "
        f"opened across {SUBJECTS_TO_TRY} subjects, {with_quiz} of them carrying "
        f"a quiz at all, {pretests} opening on a pretest and {not_loading} whose "
        f"video would not load"
    )


def opens_on_the_video(subtopic):
    """Wait for the player, or for the pretest screen some subtopics open on
    instead. A pretest is a quiz of its own, with I don't know and Submit, and
    not the checkpoint this file is about, so it is passed over."""
    subtopic.page.locator("video.pl-video, .pl-pretest-intro").first.wait_for(
        timeout=30000
    )
    if subtopic.get_pretest_intro().count():
        return False
    subtopic.wait_for_player_loaded()
    return True


def open_quiz_card(subtopic):
    """Bring the quiz card up in a subtopic that has one.

    The strip circles are status only - tapping one does nothing - so the card
    is reached the way a student reaches it: Proceed to Quiz under a finished
    video. A video not finished yet is played out first."""
    if subtopic.get_quiz_card().count():
        return True

    try:
        subtopic.get_replay_overlay().wait_for(timeout=5000)
    except PlaywrightTimeoutError:
        subtopic.watch_to_the_end()

    subtopic.click_continue()
    try:
        subtopic.get_quiz_card().wait_for(timeout=10000)
    except PlaywrightTimeoutError:
        return False
    return True


@pytest.fixture
def answered_checkpoint(page):
    """A checkpoint that has already been taken, frozen as it was left."""
    found = find_checkpoint(page, answered=True)
    if isinstance(found, str):
        pytest.skip(found)
    return found


@pytest.fixture
def fresh_checkpoint(page):
    """A checkpoint nobody has reached yet.

    There is at most a handful on an account and every run uses one up, so this
    stands down cleanly far more often than it finds one."""
    found = find_checkpoint(page, answered=False)
    if isinstance(found, str):
        pytest.skip(found)
    return found


# ---------------------------------------------------------------------------
# 1. Opening one
# ---------------------------------------------------------------------------

def test_a_subtopic_with_a_checkpoint_carries_it_on_the_item_strip(page):
    """The strip is what says a subtopic has a quiz at all: a checkpoint adds
    its own item beside the video's."""
    found = find_checkpoint(page, answered=None)
    if isinstance(found, str):
        pytest.skip(found)

    assert found.get_quiz_strip_items().count() >= 1
    assert found.get_strip_items().count() > found.get_quiz_strip_items().count(), (
        "a subtopic is a video and then its checkpoints, so the strip has to "
        "carry more than the quizzes"
    )


def test_the_checkpoint_opens_on_a_question_card(page):
    found = find_checkpoint(page, answered=None)
    if isinstance(found, str):
        pytest.skip(found)

    expect(found.get_quiz_card()).to_be_visible()


# ---------------------------------------------------------------------------
# 2. What the card shows
# ---------------------------------------------------------------------------

def test_the_card_shows_a_question_and_its_options(page):
    found = find_checkpoint(page, answered=None)
    if isinstance(found, str):
        pytest.skip(found)

    question = found.get_quiz_question()
    assert question.inner_text().strip() != "" or found.get_quiz_question_images().count(), (
        "the question is neither text nor a picture"
    )
    assert found.get_quiz_options().count() >= 2
    expect(found.get_quiz_option_letters().first).not_to_be_empty()


def test_the_card_says_how_many_answers_to_choose(page):
    found = find_checkpoint(page, answered=None)
    if isinstance(found, str):
        pytest.skip(found)

    expect(found.get_quiz_choose_label()).not_to_be_empty()


def test_the_card_offers_a_bookmark_and_a_note(page):
    """Both are on the card itself, so a question can be kept or written on
    without leaving the quiz."""
    found = find_checkpoint(page, answered=None)
    if isinstance(found, str):
        pytest.skip(found)

    expect(found.get_quiz_bookmark()).to_be_visible()
    expect(found.get_quiz_note_button()).to_be_visible()


def test_the_checkpoint_offers_no_way_to_pass_on_a_question(page):
    """Unlike a practice, a checkpoint has no I don't know: the only way past it
    is to pick an option. Written to what the app does today, so it will fail if
    one is ever added."""
    found = find_checkpoint(page, answered=None)
    if isinstance(found, str):
        pytest.skip(found)

    assert found.get_quiz_dont_know_button().count() == 0


# ---------------------------------------------------------------------------
# 3. A checkpoint that has been answered
# ---------------------------------------------------------------------------

def test_an_answered_checkpoint_is_frozen(answered_checkpoint):
    """Every option is disabled, so the question cannot be answered twice."""
    options = answered_checkpoint.get_quiz_options()
    for index in range(options.count()):
        assert options.nth(index).get_attribute("disabled") is not None


def test_an_answered_checkpoint_marks_the_right_option(answered_checkpoint):
    """Exactly one option is shown as the right one, whatever was picked."""
    assert answered_checkpoint.get_correct_quiz_option().count() == 1


def test_an_answered_checkpoint_marks_a_wrong_choice_separately(answered_checkpoint):
    """A wrong pick is marked as well as the right answer, and never instead of
    it; a right pick leaves nothing marked wrong."""
    wrong = answered_checkpoint.get_wrong_quiz_option().count()
    assert wrong <= 1
    if wrong:
        assert answered_checkpoint.get_correct_quiz_option().count() == 1


def test_an_answered_checkpoint_survives_leaving_and_coming_back(page, answered_checkpoint):
    """The answer belongs to the account and not to the tab: the card comes back
    frozen after a reload."""
    marked = answered_checkpoint.get_correct_quiz_option().inner_text().strip()

    page.reload(wait_until="domcontentloaded")
    subtopic = SubtopicPage(page)
    subtopic.wait_for_player_loaded()
    assert open_quiz_card(subtopic), "the checkpoint would not come back after a reload"

    assert subtopic.quiz_is_answered()
    assert subtopic.get_correct_quiz_option().inner_text().strip() == marked


# ---------------------------------------------------------------------------
# 4. Bookmarking and noting from the card
# ---------------------------------------------------------------------------

def test_the_bookmark_on_the_card_turns_on_and_off(page, answered_checkpoint):
    """The integration this file owns: that the control on the quiz card works
    at all. What a bookmark then is, and where it shows up, is
    test_ql_bookmark.py's."""
    bookmark = answered_checkpoint.get_quiz_bookmark()
    before = bookmark.get_attribute("aria-label")

    bookmark.click()
    page.wait_for_timeout(2500)
    after = answered_checkpoint.get_quiz_bookmark().get_attribute("aria-label")
    assert after != before, f"the bookmark stayed {before!r} after being tapped"

    answered_checkpoint.get_quiz_bookmark().click()
    page.wait_for_timeout(2500)
    assert answered_checkpoint.get_quiz_bookmark().get_attribute("aria-label") == before


def test_the_note_control_on_the_card_opens_something_to_write_in(
    page, answered_checkpoint
):
    """Again only the integration: writing, editing and finding notes again is
    test_ql_my_notes.py's."""
    answered_checkpoint.get_quiz_note_button().click()
    page.wait_for_timeout(2500)

    assert answered_checkpoint.get_note_editor().count(), (
        "the note control opened nothing that can be written in"
    )


# ---------------------------------------------------------------------------
# 5. Answering a fresh one
#
# A checkpoint is answered once and there is no second chance at it, so these
# spend the last unanswered one on the account and stand down when there is
# none. No endpoint is named: what the app calls when an option is picked is
# read off the network as it happens, and the balance and the coin log are what
# the payment is held to.
# ---------------------------------------------------------------------------

def test_answering_a_checkpoint_freezes_it_and_shows_the_right_answer(
    page, fresh_checkpoint
):
    fresh_checkpoint.answer_quiz_option(0)

    assert fresh_checkpoint.quiz_is_answered()
    assert fresh_checkpoint.get_correct_quiz_option().count() == 1


def test_answering_a_checkpoint_moves_the_balance_by_what_it_is_worth(
    page, fresh_checkpoint
):
    """A right answer is worth +4 and a wrong one -1, the same as a practice.
    Which was given is read from the card afterwards rather than assumed, since
    the right option is not on screen until it has been answered."""
    before = read_balance(page)

    fresh_checkpoint.answer_quiz_option(0)

    got_it_right = fresh_checkpoint.get_wrong_quiz_option().count() == 0
    expected = before + (PER_CORRECT if got_it_right else PER_WRONG)

    assert read_balance(page) == expected, (
        f"answering {'right' if got_it_right else 'wrong'} moved the balance "
        f"from {before} to {read_balance(page)}, not to {expected}"
    )


def test_what_a_checkpoint_paid_is_written_into_todays_coin_log(page, fresh_checkpoint):
    before = read_balance(page)

    fresh_checkpoint.answer_quiz_option(0)

    after = read_balance(page)
    events = read_coin_log(page, "log-today")

    assert sum(event["score"] for event in events) == after, events
    assert (after - before) in [event["score"] for event in events], (
        f"nothing in today's log accounts for the {after - before} the "
        f"checkpoint paid: {[e['score'] for e in events]}"
    )
