"""Learning progress down the syllabus: subject, chapter, topic, subtopic.

How progress is worked out, read off the running app rather than assumed:

  subtopic  watched_duration over video_duration, drawn as the ring on the
            topic list. The ring is two SVG circles, and a subtopic nobody has
            opened has no arc at all, so nought is the absence of the arc.
  topic     no percentage of its own at all. The number badge turns into a tick
            once every subtopic under it has been watched out AND every quiz
            the topic carries has been taken, and that tick is the whole of the
            state kept at this level. A part watched subtopic moves nothing
            here, and neither does watching all of the video of a topic that
            still owes a quiz.
  chapter   finished topics over its topics, shown twice - as the card fill on
            the subject page, which comes from the chapters call, and as the
            header bar on the topic list, which comes from the chapter content
            call.
  subject   no figure of its own anywhere in the app. The home card carries
            none and the home call serves none, so the subject page is its
            chapter list and subject progress is the sum of those cards.

The position is sent by POST video-progress-update, and only twice: when the
video ends, and when the player unmounts. Nothing goes out on pause or on a
timer, so a test that wants its progress recorded has to leave the player. What
is posted is not the media element's position either but a figure the player
samples for itself every second or two, which is why a mark is played up to
rather than jumped to.

The recorded mark only ever moves forward and nothing resets it, so none of
these tests assume a starting state. Each one asks the syllabus what is
currently in the state it needs and drives that. The run works in whichever
unlocked chapter has the most left to show - video still to watch, a topic that
watching alone can finish - so that repeated runs move on to fresh content
instead of fighting over the same subtopics, and it reads progress back from
whichever chapter shows the most of the states there are to read. A run that
finds nothing in the state a test needs says so and skips rather than inventing
one.

Playback itself - controls, seeking, the mini player - is covered in
test_video_player.py, and the shape of a subtopic, its pretest and its
checkpoint quiz in test_subtopic.py. What a checkpoint quiz pays in coins is in
test_daily_task_coins.py. What is asserted here is only the progress these
produce.
"""
import re
import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.chapter_page import ChapterPage
from pages.topic_page import TopicPage
from pages.subtopic_page import SubtopicPage

MOBILE = "9876543210"
OTP = "430582"

HOME_URL = "https://eduport-react.pages.dev/"

# How much of the course is looked at when deciding where to work. Only the
# unlocked chapters count, and a course can carry a lot of subjects, so the
# search is bounded rather than exhaustive.
SUBJECT_PROBE_LIMIT = 8
CHAPTER_PROBE_LIMIT = 4

CHAPTERS_API = "**/api/v3/syllabus/chapters?*"
CHAPTER_CONTENT_API = "**/api/v3/syllabus/chapter-content/?*"
PROGRESS_API = "**/api/v3/subtopic/video-progress-update"

# The app restores the recorded position a few seconds after the player
# renders, so a seek made before that lands is simply undone.
RESTORE_MS = 5000

# Playback carries on while a test works, so positions are compared with room
# to move rather than exactly.
RESUME_TOLERANCE = 15

# The ring and the payload are drawn from the same two numbers, so they are
# held to agreeing rather than to being close.
RING_MARGIN = 0.5

# How far a watch-up-to may come to rest from the fraction it was asked for:
# the position is recorded whole seconds and the video runs on while the player
# is being stopped.
POSITION_MARGIN = 6

# Room left under a target when picking a subtopic, so one that is already part
# way through can still be driven up to it.
PICK_MARGIN = 10

FINISH_TIMEOUT = 90000

# How long a pause is held while listening for a post that should never come.
PAUSE_QUIET_MS = 8000

# The listed length is written out to the second, and the player rounds the
# media element's own duration, so the two are held to the same second rather
# than to the same float.
DURATION_MARGIN = 1.5

# How much video a single test will sit through to watch a chapter out in full.
CHAPTER_COMPLETION_LIMIT = 20


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture(scope="session")
def content_survey(login_session):
    """What the unlocked chapters of this course hold, looked at once.

    Where it is worth working depends on what has already been watched in a
    chapter and on which of its topics still owe a quiz, and neither of those
    is in any list: both come from opening the chapter. So this looks once, for
    the whole run, and only at the first few subjects and the first few
    unlocked chapters of each, because a course carries far more than the
    answer needs."""
    page = login_session(MOBILE)

    home = HomePage(page)
    home.get_subjects().first.wait_for()
    subjects = home.get_subject_names()

    survey = []
    for subject in range(min(len(subjects), SUBJECT_PROBE_LIMIT)):
        page.goto(HOME_URL, wait_until="domcontentloaded")
        home.get_subjects().first.wait_for()
        home.open_subject(subject)

        chapters = ChapterPage(page)
        chapters.wait_for_chapters_loaded()
        subject_url = page.url

        looked_at = 0
        for chapter in range(chapters.chapter_count()):
            if looked_at >= CHAPTER_PROBE_LIMIT:
                break
            if chapters.is_chapter_locked(chapter):
                continue
            looked_at += 1

            with page.expect_response(CHAPTER_CONTENT_API) as answer:
                chapters.click_chapter(chapter)
            body = answer.value.json()
            subtopics = [subtopic for _, _, subtopic in flat_subtopics(body)]

            survey.append({
                "subject": subject,
                "subject_title": subjects[subject],
                "chapter": chapter,
                "title": body["chapter_data"]["title"],
                "topics": len(body["topics"]),
                "unwatched": sum(1 for s in subtopics if s["watched_duration"] == 0),
                "part_way": sum(
                    1
                    for s in subtopics
                    if 0 < s["watched_duration"] < s["video_duration"]
                ),
                "finished": sum(1 for s in subtopics if s["video_completed"]),
                "outstanding": sum(1 for s in subtopics if not s["video_completed"]),
                "completable": sum(
                    1
                    for topic in body["topics"]
                    if topic_can_be_finished_by_watching(topic)
                    and not topic_is_finished(topic)
                ),
                "quiz_free": all(
                    topic_quizzes_are_done(topic) for topic in body["topics"]
                ),
            })

            chapters.open(subject_url)

    if not survey:
        pytest.skip("No unlocked chapter anywhere in this course")

    for row in survey:
        print(
            f"  {row['subject_title']!r} chapter {row['chapter'] + 1} "
            f"{row['title']!r}: {row['topics']} topics, {row['unwatched']} unwatched, "
            f"{row['part_way']} part way, {row['finished']} finished, "
            f"{row['completable']} finishable by watching"
            f"{'' if row['quiz_free'] else ', quiz outstanding'}"
        )
    return survey


@pytest.fixture(scope="session")
def working_content(content_survey):
    """The subject and chapter this run works in.

    Watching cannot be undone and nothing resets it, so a chapter is used up as
    these tests run through it. Rather than settling on the first one and
    skipping most of this file once it has been worked through, a chapter is
    chosen for what it can still show: video left to watch, a topic that
    watching alone can finish, no quiz standing in the way, and something
    already finished to read progress back from."""
    chosen = max(
        content_survey,
        key=lambda row: (
            row["unwatched"] > 0,
            row["completable"] > 0,
            row["quiz_free"],
            row["finished"] > 0,
            row["unwatched"],
        ),
    )
    print(
        f"Working in {chosen['subject_title']!r}, chapter {chosen['chapter'] + 1} "
        f"{chosen['title']!r}"
    )
    return chosen


@pytest.fixture(scope="session")
def reading_content(content_survey, working_content):
    """The subject the tests that only read progress back are pointed at.

    Watching and reading want opposite things from a chapter: the watching
    tests need one with video left in it, while the tests that check how
    progress is reported need one that already carries some. They are rarely
    the same chapter, so rather than have half of them skip, the reading tests
    follow whichever unlocked chapter has the most watched behind it, and fall
    back to the working one when nothing has been watched anywhere."""
    watched = [row for row in content_survey if row["finished"] > 0]
    if not watched:
        return working_content

    chosen = max(watched, key=lambda row: row["finished"])
    print(
        f"Reading progress back from {chosen['subject_title']!r}, chapter "
        f"{chosen['chapter'] + 1} {chosen['title']!r}"
    )
    return chosen


@pytest.fixture(scope="session")
def mixed_content(content_survey, working_content):
    """The chapter the tests that read progress back are pointed at.

    Watching and reading want opposite things from a chapter, so rather than
    have the reading tests work in the one being watched through, they follow
    whichever unlocked chapter shows the most of the states there are to read -
    something finished, something part way through, something not started -
    and fall back to the working one when no chapter shows any."""
    def variety(row):
        return (
            sum(bool(row[state]) for state in ("finished", "part_way", "unwatched")),
            row["finished"] + row["part_way"],
        )

    chosen = max(content_survey, key=variety)
    if variety(chosen)[0] < 2:
        return working_content

    print(
        f"Reading progress back from {chosen['subject_title']!r}, chapter "
        f"{chosen['chapter'] + 1} {chosen['title']!r}: {chosen['finished']} finished, "
        f"{chosen['part_way']} part way, {chosen['unwatched']} unstarted"
    )
    return chosen


@pytest.fixture
def home_page(page):
    home = HomePage(page)
    home.get_subjects().first.wait_for()
    return home


@pytest.fixture
def subject_page(page, home_page, working_content):
    """The subject's chapter list, which is as close to a subject page as the
    app has."""
    home_page.open_subject(working_content["subject"])

    chapters = ChapterPage(page)
    chapters.wait_for_chapters_loaded()
    return chapters


def open_subject_with_payload(page, home_page, subject):
    """The chapter list together with the call it is drawn from. The call has to
    be listened for before the subject is opened, so this navigates itself."""
    with page.expect_response(CHAPTERS_API) as answer:
        home_page.open_subject(subject)
    assert answer.value.status == 200, f"chapters answered {answer.value.status}"

    chapters = ChapterPage(page)
    chapters.wait_for_chapters_loaded()
    return chapters, answer.value.json()


@pytest.fixture
def subject_with_payload(page, home_page, reading_content):
    """The chapter list of the subject progress is read back from."""
    return open_subject_with_payload(page, home_page, reading_content["subject"])


@pytest.fixture
def topic_page(page, subject_page, working_content):
    """The chapter this run works in, with every topic opened so that all of
    its subtopic rings are on screen and in one flat order."""
    if subject_page.is_chapter_locked(working_content["chapter"]):
        pytest.skip("The chapter this run works in is locked")
    subject_page.click_chapter(working_content["chapter"])

    topics = TopicPage(page)
    topics.wait_for_topics_loaded()
    topics.expand_all_topics()
    return topics


@pytest.fixture
def mixed_topic_page(page, home_page, mixed_content):
    """The topic list of the chapter progress is read back from, with every
    topic opened."""
    home_page.open_subject(mixed_content["subject"])

    chapters = ChapterPage(page)
    chapters.wait_for_chapters_loaded()
    if chapters.is_chapter_locked(mixed_content["chapter"]):
        pytest.skip("The chapter progress is read back from is locked")
    chapters.click_chapter(mixed_content["chapter"])

    topics = TopicPage(page)
    topics.wait_for_topics_loaded()
    topics.expand_all_topics()
    return topics


# ---------------------------------------------------------------------------
# Reading the syllabus
#
# The topic list, the header bar and every ring on it are drawn from one call,
# so the screen can be read back against it. Progress is written by the player
# rather than by this page, so the list has to be asked again after anything is
# watched instead of being read off a stale render.
# ---------------------------------------------------------------------------

def reload_syllabus(page, topic_page):
    """Reload the topic list and hand back the payload it was drawn from."""
    with page.expect_response(CHAPTER_CONTENT_API) as answer:
        page.reload()
    assert answer.value.status == 200, f"chapter-content answered {answer.value.status}"

    topic_page.wait_for_topics_loaded()
    topic_page.expand_all_topics()
    return answer.value.json()


def flat_subtopics(syllabus):
    """The subtopics in the order the opened topic list shows them, each tagged
    with the topic it sits under. The position in this list is the position of
    the matching ring on screen."""
    return [
        (topic_index, topic, subtopic)
        for topic_index, topic in enumerate(syllabus["topics"])
        for subtopic in topic["subtopics"]
    ]


def subtopic_percent(subtopic):
    """What the app has recorded for a subtopic, as a percentage."""
    return subtopic["watched_duration"] / subtopic["video_duration"] * 100


def topic_quizzes_are_done(topic):
    return set(topic["quiz_types"]) <= set(topic["completed_quizzes"])


def topic_is_finished(topic):
    """A topic counts as finished once every subtopic under it has been watched
    out and every quiz it carries has been taken.

    Watching all of the video is not enough on a topic that carries a quiz: it
    goes on reading as unfinished, and goes on counting for nothing towards its
    chapter, until the quiz is done too."""
    return (
        bool(topic["subtopics"])
        and all(subtopic["video_completed"] for subtopic in topic["subtopics"])
        and topic_quizzes_are_done(topic)
    )


def topic_can_be_finished_by_watching(topic):
    """Whether watching is enough to finish this topic, which it is not when a
    quiz on it is still outstanding."""
    return bool(topic["subtopics"]) and topic_quizzes_are_done(topic)


def finished_topic_count(syllabus):
    return sum(1 for topic in syllabus["topics"] if topic_is_finished(topic))


def pick_subtopic(syllabus, below=100.0, in_topic_of_at_least=1):
    """The shortest subtopic currently recorded under the given percentage.

    Nothing resets progress and the mark only moves forward, so a test that
    drives a subtopic to a position has to start from one that has not already
    passed it. The shortest is taken because the video still has to be played
    through the point it is seeked to."""
    candidates = [
        (index, subtopic)
        for index, (_, topic, subtopic) in enumerate(flat_subtopics(syllabus))
        if subtopic["video_duration"] > 0
        and subtopic_percent(subtopic) < below
        and len(topic["subtopics"]) >= in_topic_of_at_least
    ]
    if not candidates:
        return None, None
    return min(candidates, key=lambda found: found[1]["video_duration"])


# ---------------------------------------------------------------------------
# Driving the player
# ---------------------------------------------------------------------------

def open_player(page, topic_page, flat_index):
    """Open a subtopic from the list and let the player settle."""
    topic_page.open_subtopic_at(flat_index)

    player = SubtopicPage(page)
    player.wait_for_player_loaded()
    # Let the app put the video back where it was before anything is seeked,
    # otherwise the restore lands afterwards and undoes it.
    page.wait_for_timeout(RESTORE_MS)
    return player


def leave_player(page, player, timeout=15000):
    """Back out of the player and hand back what it posted on the way.

    The player says nothing while it is open and posts once, as it unmounts, so
    this is the only place a part watched video is recorded. It stays silent
    when it has nothing new to report, which reads back as None rather than as
    a failure: whether there was something to report is the caller's to judge."""
    try:
        with page.expect_response(PROGRESS_API, timeout=timeout) as answer:
            player.click_back()
    except Exception:
        return None

    assert answer.value.status == 200, (
        f"video-progress-update answered {answer.value.status}"
    )
    return answer.value.request.post_data_json


def watch_and_record(page, topic_page, flat_index, fraction, expected=None, attempts=3):
    """Take a subtopic up to a fraction of its video and leave, so that the
    position is recorded, and hand back what the player posted.

    Two things can leave a watch unrecorded, and neither shows up until the
    player posts: a restore arriving late drags the video off a mark that has
    already been set, and the figure the player samples for itself can still be
    behind the video when it is stopped. So the watch is repeated when the
    player reports nothing, or reports something that plainly missed the mark,
    rather than being asserted on."""
    posted = None
    for _ in range(attempts):
        player = open_player(page, topic_page, flat_index)
        player.watch_up_to(fraction)
        posted = leave_player(page, player)

        if posted and expected is not None:
            assert posted["subtopic"] == expected["id"], (
                f"position {flat_index} opened subtopic {posted['subtopic']}, "
                f"not {expected['id']} ({expected['title']!r})"
            )
        if posted and posted["progress"] >= posted["duration"] * fraction - 1:
            return posted

        topic_page.wait_for_topics_loaded()
        topic_page.expand_all_topics()

    raise AssertionError(
        f"the player would not record {fraction:.0%} of the subtopic at "
        f"position {flat_index}: it posted {posted}"
    )


def finish_video(page, player):
    """Play the video out and hand back what it posted at the end.

    A finished video posts as it ends and then has nothing left to send, so the
    trip out of the player afterwards is silent and is not waited on."""
    with page.expect_response(PROGRESS_API, timeout=FINISH_TIMEOUT) as answer:
        player.watch_to_the_end()
    assert answer.value.status == 200, (
        f"video-progress-update answered {answer.value.status}"
    )
    return answer.value.request.post_data_json


def last_subtopic_of_a_finishable_topic(syllabus):
    """A topic that one more watch would finish, as (topic position, subtopic
    position, topic).

    A topic still owing a quiz is no use here however much of it has been
    watched: watching cannot finish it, so it would never come to be ticked."""
    for topic_index, topic in enumerate(syllabus["topics"]):
        if not topic_can_be_finished_by_watching(topic):
            continue

        unfinished = [s for s in topic["subtopics"] if not s["video_completed"]]
        if len(unfinished) != 1:
            continue

        flat = [
            index
            for index, (owner, _, subtopic) in enumerate(flat_subtopics(syllabus))
            if owner == topic_index and subtopic["id"] == unfinished[0]["id"]
        ]
        return topic_index, flat[0], topic
    return None


# ---------------------------------------------------------------------------
# 1. Subtopic progress
# ---------------------------------------------------------------------------

def test_an_unstarted_subtopic_shows_no_progress(page, topic_page):
    """Nought is drawn as the absence of the arc rather than as an arc of no
    length, so the ring is checked for having only its grey track."""
    syllabus = reload_syllabus(page, topic_page)

    unstarted = [
        index
        for index, (_, _, subtopic) in enumerate(flat_subtopics(syllabus))
        if subtopic["watched_duration"] == 0
    ]
    if not unstarted:
        pytest.skip("Every subtopic in this chapter has been started")

    index = unstarted[0]

    assert topic_page.get_subtopic_progress(index) == 0
    expect(topic_page.get_ring_circles(index)).to_have_count(1)

    print("Unstarted subtopics:", len(unstarted), "of", len(flat_subtopics(syllabus)))


def test_watching_half_a_video_fills_half_the_ring(page, topic_page):
    """The ring is the watched fraction of the video and nothing else, so a
    video stopped half way shows about half a ring."""
    syllabus = reload_syllabus(page, topic_page)
    index, subtopic = pick_subtopic(syllabus, below=50 - PICK_MARGIN)
    if index is None:
        pytest.skip("No subtopic left that is under half watched")

    posted = watch_and_record(page, topic_page, index, 0.5, subtopic)

    assert posted["subtopic"] == subtopic["id"]
    assert posted["progress"] == pytest.approx(posted["duration"] * 0.5, abs=POSITION_MARGIN)

    syllabus = reload_syllabus(page, topic_page)
    recorded = flat_subtopics(syllabus)[index][2]

    assert recorded["watched_duration"] == posted["progress"]
    assert subtopic_percent(recorded) == pytest.approx(50, abs=POSITION_MARGIN)
    assert topic_page.get_subtopic_progress(index) == pytest.approx(
        subtopic_percent(recorded), abs=RING_MARGIN
    )

    print(
        subtopic["title"], "->", recorded["watched_duration"], "/",
        recorded["video_duration"], "=", round(subtopic_percent(recorded), 1), "%",
    )


def test_finishing_a_video_takes_the_subtopic_to_100(page, topic_page):
    syllabus = reload_syllabus(page, topic_page)
    index, subtopic = pick_subtopic(syllabus)
    if index is None:
        pytest.skip("Every subtopic in this chapter is already finished")

    player = open_player(page, topic_page, index)
    posted = finish_video(page, player)

    assert posted["subtopic"] == subtopic["id"]
    assert posted["progress"] == posted["duration"]
    expect(player.get_finished_video_item()).to_have_count(1)

    player.click_back()
    syllabus = reload_syllabus(page, topic_page)
    recorded = flat_subtopics(syllabus)[index][2]

    assert recorded["watched_duration"] == recorded["video_duration"]
    assert topic_page.get_subtopic_progress(index) == pytest.approx(100, abs=RING_MARGIN)

    print("Finished:", subtopic["title"])


def test_a_finished_subtopic_reads_as_complete_everywhere(page, topic_page):
    """Completion is held in three places - the payload, the ring on the topic
    list and the badge in the player - and they have to agree."""
    syllabus = reload_syllabus(page, topic_page)

    finished = [
        (index, subtopic)
        for index, (_, _, subtopic) in enumerate(flat_subtopics(syllabus))
        if subtopic["video_completed"]
    ]
    if not finished:
        pytest.skip("Nothing in this chapter has been finished yet")

    index, subtopic = finished[0]

    assert subtopic["watched_duration"] == subtopic["video_duration"]
    assert topic_page.get_subtopic_progress(index) == pytest.approx(100, abs=RING_MARGIN)

    player = open_player(page, topic_page, index)

    expect(player.get_finished_video_item()).to_have_count(1)
    expect(player.get_replay_overlay()).to_be_visible()


def test_progress_is_kept_when_a_subtopic_is_left_and_reopened(page, topic_page):
    """Stop part way, leave, come back: the ring still shows the recorded
    position and the player picks the video up there rather than at nought."""
    syllabus = reload_syllabus(page, topic_page)
    index, subtopic = pick_subtopic(syllabus, below=35 - PICK_MARGIN)
    if index is None:
        pytest.skip("No subtopic left that is under a third watched")

    left_at = watch_and_record(page, topic_page, index, 0.35, subtopic)["progress"]

    syllabus = reload_syllabus(page, topic_page)
    recorded = flat_subtopics(syllabus)[index][2]
    shown = topic_page.get_subtopic_progress(index)

    assert shown > 0, "the ring went back to nought"
    assert shown == pytest.approx(subtopic_percent(recorded), abs=RING_MARGIN)

    player = open_player(page, topic_page, index)
    player.wait_for_restore(left_at - RESUME_TOLERANCE)

    assert player.get_current_time() > 0, "the video restarted from the beginning"
    assert player.get_current_time() == pytest.approx(left_at, abs=RESUME_TOLERANCE)

    player.click_back()


def test_resuming_a_subtopic_carries_its_progress_on(page, topic_page):
    """Coming back and watching further moves the ring on from where it was
    rather than starting it again."""
    syllabus = reload_syllabus(page, topic_page)
    index, subtopic = pick_subtopic(syllabus, below=55 - PICK_MARGIN)
    if index is None:
        pytest.skip("No subtopic left that is under half watched")

    left_at = watch_and_record(page, topic_page, index, 0.55, subtopic)["progress"]

    reload_syllabus(page, topic_page)
    part_way = topic_page.get_subtopic_progress(index)
    assert part_way == pytest.approx(55, abs=POSITION_MARGIN)

    player = open_player(page, topic_page, index)
    player.wait_for_restore(left_at - RESUME_TOLERANCE)
    assert player.get_current_time() > 0, "the video restarted from the beginning"
    player.click_back()
    topic_page.wait_for_topics_loaded()
    topic_page.expand_all_topics()

    watch_and_record(page, topic_page, index, 0.8, subtopic)

    reload_syllabus(page, topic_page)
    resumed = topic_page.get_subtopic_progress(index)

    assert resumed > part_way
    assert resumed == pytest.approx(80, abs=POSITION_MARGIN)

    print(subtopic["title"], round(part_way, 1), "% ->", round(resumed, 1), "%")


def test_progress_does_not_reset_on_a_reload(page, topic_page):
    """Every ring on the page reads the same after a full reload."""
    syllabus = reload_syllabus(page, topic_page)
    before = topic_page.get_subtopic_progresses()

    if not any(shown > 0 for shown in before):
        pytest.skip("Nothing in this chapter has been started yet")

    reload_syllabus(page, topic_page)
    after = topic_page.get_subtopic_progresses()

    assert after == pytest.approx(before, abs=RING_MARGIN)
    assert any(shown > 0 for shown in after), "the rings went back to nought"


def test_progress_never_goes_past_100(page, topic_page):
    """Neither the recorded position nor any ring can go over the whole video."""
    syllabus = reload_syllabus(page, topic_page)

    for _, _, subtopic in flat_subtopics(syllabus):
        assert subtopic["watched_duration"] <= subtopic["video_duration"], subtopic["title"]

    for shown in topic_page.get_subtopic_progresses():
        assert 0 <= shown <= 100


def test_playing_a_finished_video_again_leaves_it_at_100(page, topic_page):
    """The one way progress could be pushed over is watching a video that is
    already finished, so it is watched out a second time."""
    syllabus = reload_syllabus(page, topic_page)

    finished = [
        index
        for index, (_, _, subtopic) in enumerate(flat_subtopics(syllabus))
        if subtopic["video_completed"]
    ]
    if not finished:
        pytest.skip("Nothing in this chapter has been finished yet")

    index = finished[0]
    player = open_player(page, topic_page, index)
    player.seek_to_end()
    page.wait_for_timeout(6000)
    player.click_back()

    syllabus = reload_syllabus(page, topic_page)
    recorded = flat_subtopics(syllabus)[index][2]

    assert recorded["watched_duration"] == recorded["video_duration"]
    assert topic_page.get_subtopic_progress(index) == pytest.approx(100, abs=RING_MARGIN)


def test_pausing_a_video_records_nothing_and_loses_nothing(page, topic_page):
    """Pause is not a save point.

    Nothing goes out while the player is open, so a pause posts nothing however
    long it is held. What is watched up to is still there when play is pressed
    again, and it is still there when the player is finally left - which is the
    one moment it is sent."""
    syllabus = reload_syllabus(page, topic_page)
    index, subtopic = pick_subtopic(syllabus, below=45 - PICK_MARGIN)
    if index is None:
        pytest.skip("No subtopic left that is under 45% watched")

    player = open_player(page, topic_page, index)
    paused_at = player.watch_up_to(0.35)

    assert player.is_paused(), "the video would not hold still"
    posted = None
    try:
        with page.expect_response(PROGRESS_API, timeout=PAUSE_QUIET_MS) as answer:
            page.wait_for_timeout(PAUSE_QUIET_MS)
        posted = answer.value.request.post_data_json
    except Exception:
        pass
    assert posted is None, f"a pause posted progress on its own: {posted}"

    # Picked up again, from where it was left rather than from the beginning.
    player.play()
    player.wait_for_time_past(paused_at)
    assert player.get_current_time() >= paused_at

    carried_on = player.get_current_time()
    player.pause()
    left = leave_player(page, player)

    assert left is not None, "the player left without posting what was watched"
    assert left["subtopic"] == subtopic["id"]
    assert left["progress"] >= paused_at - POSITION_MARGIN, (
        f"paused at {paused_at:.0f}s, carried on to {carried_on:.0f}s, "
        f"posted {left['progress']}s"
    )

    syllabus = reload_syllabus(page, topic_page)
    recorded = flat_subtopics(syllabus)[index][2]

    assert recorded["watched_duration"] == left["progress"]
    assert topic_page.get_subtopic_progress(index) == pytest.approx(
        subtopic_percent(recorded), abs=RING_MARGIN
    )


def test_the_length_shown_against_a_subtopic_is_the_length_of_its_video(
    page, topic_page
):
    """The time on the topic list is video_duration written out, and it is what
    the ring is a fraction of."""
    syllabus = reload_syllabus(page, topic_page)
    subtopics = flat_subtopics(syllabus)

    checked = 0
    for index, (_, _, subtopic) in enumerate(subtopics):
        if not subtopic["video_duration"]:
            continue
        shown = topic_page.get_subtopic_duration_seconds(index)
        assert shown == pytest.approx(subtopic["video_duration"], abs=DURATION_MARGIN), (
            f"{subtopic['title']!r} is listed as {shown}s and served as "
            f"{subtopic['video_duration']}s"
        )
        checked += 1

    assert checked, "no subtopic in this chapter carries a video"
    print("Durations checked:", checked)


def test_the_player_picks_up_at_the_watch_time_the_api_holds(page, mixed_topic_page):
    """The recorded watch time is a position in the video, not just a number
    behind a ring: reopening a part watched subtopic puts the video back at it,
    and the player's own clock reads it back."""
    syllabus = reload_syllabus(page, mixed_topic_page)

    part_way = [
        (index, subtopic)
        for index, (_, _, subtopic) in enumerate(flat_subtopics(syllabus))
        if 0 < subtopic["watched_duration"] < subtopic["video_duration"]
    ]
    if not part_way:
        pytest.skip("Nothing in this chapter is part way through")

    index, subtopic = max(part_way, key=lambda found: found[1]["watched_duration"])
    watched = subtopic["watched_duration"]

    player = open_player(page, mixed_topic_page, index)
    player.wait_for_restore(watched - RESUME_TOLERANCE)

    assert player.get_current_time() == pytest.approx(watched, abs=RESUME_TOLERANCE), (
        f"{subtopic['title']!r} is recorded at {watched}s and opened at "
        f"{player.get_current_time():.0f}s"
    )
    assert player.get_duration() == pytest.approx(
        subtopic["video_duration"], abs=DURATION_MARGIN
    )

    # The control bar clock is deliberately left out of this. It does not
    # follow the media element closely enough to be read as the position:
    # against a video restored to 402s of 501s it was seen reading 25 seconds
    # left, so it says something of its own about where the player is rather
    # than what the recorded watch time is. Its shape is checked in
    # test_video_player.py.

    player.click_back()


def test_finished_part_watched_and_unstarted_subtopics_each_read_their_own_way(
    page, mixed_topic_page
):
    """A chapter holding all three states at once: every ring is its own
    subtopic's figure, and none of the three is confused for another."""
    syllabus = reload_syllabus(page, mixed_topic_page)
    shown = mixed_topic_page.get_subtopic_progresses()
    subtopics = flat_subtopics(syllabus)

    states = {"finished": [], "part way": [], "unstarted": []}
    for index, (_, _, subtopic) in enumerate(subtopics):
        if subtopic["video_completed"]:
            states["finished"].append(index)
        elif subtopic["watched_duration"] > 0:
            states["part way"].append(index)
        else:
            states["unstarted"].append(index)

    missing = [state for state, found in states.items() if not found]
    if missing:
        pytest.skip(f"This chapter holds nothing {' or '.join(missing)}")

    print({state: len(found) for state, found in states.items()})

    for index in states["finished"]:
        assert shown[index] == pytest.approx(100, abs=RING_MARGIN), index
        expect(mixed_topic_page.get_ring_circles(index)).to_have_count(2)

    for index in states["part way"]:
        recorded = subtopic_percent(subtopics[index][2])
        assert 0 < shown[index] < 100, index
        assert shown[index] == pytest.approx(recorded, abs=RING_MARGIN), index
        expect(mixed_topic_page.get_ring_circles(index)).to_have_count(2)

    for index in states["unstarted"]:
        assert shown[index] == 0, index
        expect(mixed_topic_page.get_ring_circles(index)).to_have_count(1)


# ---------------------------------------------------------------------------
# 2. Topic progress
#
# A topic has no percentage. Everything a topic says about itself is the tick
# on its number badge, so what is asserted here is when that tick is and is not
# there, and that the subtopics under it keep their own separate figures.
# ---------------------------------------------------------------------------

def test_a_topic_is_ticked_exactly_when_its_video_and_quizzes_are_done(page, topic_page):
    """The tick and the topic being finished are the same thing, in both
    directions, and finished means the watching and the quizzes."""
    syllabus = reload_syllabus(page, topic_page)

    for index, topic in enumerate(syllabus["topics"]):
        if not topic["subtopics"]:
            continue
        assert topic_page.is_topic_complete(index) is topic_is_finished(topic), (
            f"{topic['title']!r} is shown as "
            f"{'finished' if topic_page.is_topic_complete(index) else 'unfinished'}"
        )

    expect(topic_page.get_completed_topics()).to_have_count(finished_topic_count(syllabus))


def test_a_finished_topic_shows_a_tick_on_its_number(page, topic_page):
    syllabus = reload_syllabus(page, topic_page)

    finished = [i for i, topic in enumerate(syllabus["topics"]) if topic_is_finished(topic)]
    if not finished:
        pytest.skip("No finished topic in this chapter")

    expect(topic_page.get_topic_tick(finished[0])).to_be_visible()


def test_watching_all_the_video_does_not_finish_a_topic_that_still_owes_a_quiz(
    page, topic_page
):
    """A topic whose video has all been watched but whose quiz is outstanding
    stays unticked and goes on counting for nothing towards its chapter."""
    syllabus = reload_syllabus(page, topic_page)

    owing = [
        index
        for index, topic in enumerate(syllabus["topics"])
        if topic["subtopics"]
        and all(subtopic["video_completed"] for subtopic in topic["subtopics"])
        and not topic_quizzes_are_done(topic)
    ]
    if not owing:
        pytest.skip("No topic here has all its video watched and a quiz outstanding")

    index = owing[0]
    topic = syllabus["topics"][index]

    for offset in range(len(topic["subtopics"])):
        flat = sum(len(t["subtopics"]) for t in syllabus["topics"][:index]) + offset
        assert topic_page.get_subtopic_progress(flat) == pytest.approx(100, abs=RING_MARGIN)

    assert topic_page.is_topic_complete(index) is False
    expect(topic_page.get_topic_tick(index)).to_have_count(0)

    print(
        topic["title"], "- all video watched, quizzes",
        topic["completed_quizzes"], "of", topic["quiz_types"],
    )


def test_a_topic_carries_no_progress_of_its_own(page, topic_page):
    """A topic holding a part watched subtopic shows no figure for itself: the
    progress lives on the subtopic, and the topic stays plainly unfinished."""
    syllabus = reload_syllabus(page, topic_page)

    part_way = [
        index
        for index, topic in enumerate(syllabus["topics"])
        if not topic_is_finished(topic)
        and any(0 < subtopic_percent(s) < 100 for s in topic["subtopics"])
    ]
    if not part_way:
        pytest.skip("No topic in this chapter has a part watched subtopic")

    index = part_way[0]

    expect(topic_page.get_topic_header(index).locator(".tp-progress-bar")).to_have_count(0)
    expect(topic_page.get_topic_header(index).locator(".tp-progress-ring-wrap")).to_have_count(0)
    assert topic_page.is_topic_complete(index) is False


def test_subtopics_of_one_topic_keep_their_own_separate_progress(page, topic_page):
    """Several subtopics under one topic, each at a different position: every
    ring is its own subtopic's figure and none of them is averaged together."""
    syllabus = reload_syllabus(page, topic_page)
    shown = topic_page.get_subtopic_progresses()

    mixed = None
    start = 0
    for topic in syllabus["topics"]:
        positions = shown[start:start + len(topic["subtopics"])]
        if len(topic["subtopics"]) > 1 and len(set(round(p) for p in positions)) > 1:
            mixed = (topic, start, positions)
            break
        start += len(topic["subtopics"])

    if mixed is None:
        pytest.skip("No topic here holds subtopics at different positions")

    topic, start, positions = mixed
    for offset, subtopic in enumerate(topic["subtopics"]):
        assert positions[offset] == pytest.approx(
            subtopic_percent(subtopic), abs=RING_MARGIN
        ), subtopic["title"]

    print(topic["title"], [round(p, 1) for p in positions])


def test_a_part_watched_subtopic_does_not_finish_its_topic(page, topic_page):
    """One subtopic taken to half leaves its topic unfinished while every other
    subtopic under it is still outstanding."""
    syllabus = reload_syllabus(page, topic_page)
    index, subtopic = pick_subtopic(
        syllabus, below=50 - PICK_MARGIN, in_topic_of_at_least=2
    )
    if index is None:
        pytest.skip("No under-watched subtopic in a topic that holds several")

    topic_index = flat_subtopics(syllabus)[index][0]

    watch_and_record(page, topic_page, index, 0.5, subtopic)

    syllabus = reload_syllabus(page, topic_page)

    assert topic_page.get_subtopic_progress(index) > 0
    assert topic_page.is_topic_complete(topic_index) is False
    expect(topic_page.get_topic_tick(topic_index)).to_have_count(0)


def test_finishing_the_last_subtopic_finishes_its_topic(page, topic_page):
    """The topic flips only once the last outstanding subtopic under it is
    finished, and the chapter's lesson count moves with it."""
    syllabus = reload_syllabus(page, topic_page)

    outstanding = last_subtopic_of_a_finishable_topic(syllabus)
    if outstanding is None:
        pytest.skip(
            "No topic here is one subtopic away from being finished with no "
            "quiz outstanding"
        )

    topic_index, flat_index, topic = outstanding
    before, total = topic_page.get_lessons_completed_counts()

    player = open_player(page, topic_page, flat_index)
    finish_video(page, player)
    player.click_back()

    syllabus = reload_syllabus(page, topic_page)

    assert topic_page.is_topic_complete(topic_index) is True
    expect(topic_page.get_topic_tick(topic_index)).to_be_visible()
    assert topic_page.get_lessons_completed_counts() == (before + 1, total)

    print("Finished topic:", topic["title"], f"{before} -> {before + 1} of {total}")


def test_topic_completion_is_kept_after_a_reload(page, topic_page):
    syllabus = reload_syllabus(page, topic_page)
    before = [topic_page.is_topic_complete(i) for i in range(topic_page.topic_count())]

    if not any(before):
        pytest.skip("No finished topic in this chapter")

    reload_syllabus(page, topic_page)
    after = [topic_page.is_topic_complete(i) for i in range(topic_page.topic_count())]

    assert after == before


# ---------------------------------------------------------------------------
# 3. Chapter progress
#
# The chapter figure shows up twice - on the card on the subject page and on
# the header of the topic list - and each is checked against the call it is
# drawn from. The cards are read in whichever subject carries the most watched
# video, which is not necessarily the one being watched in: see
# reading_content.
# ---------------------------------------------------------------------------

def test_chapter_cards_match_the_chapters_api(page, subject_with_payload):
    """The card fill is the chapter's finished topics over its topics, exactly
    as the payload reports them."""
    chapters, body = subject_with_payload

    for index, chapter in enumerate(body["chapters"]):
        done, total = chapter["progress"], chapter["child_count"]

        assert chapters.get_completed_counts(index) == (done, total), chapter["title"]
        assert chapters.get_progress_percent(index) == pytest.approx(
            done / total * 100 if total else 0, abs=RING_MARGIN
        ), chapter["title"]

    expect(chapters.get_completed_texts()).to_have_count(len(body["chapters"]))


def test_the_topic_list_header_counts_the_finished_topics(page, topic_page):
    """The bar over the topic list is the chapter's progress, and it counts the
    topics the chapter content call returns."""
    syllabus = reload_syllabus(page, topic_page)

    finished = finished_topic_count(syllabus)
    total = len(syllabus["topics"])

    assert topic_page.get_lessons_completed_counts() == (finished, total)
    assert topic_page.get_progress_percent() == pytest.approx(
        finished / total * 100, abs=RING_MARGIN
    )
    expect(topic_page.get_lessons_completed()).to_have_text(
        re.compile(rf"^{finished}/{total} Lessons Completed$")
    )


def test_part_finished_chapters_show_a_part_filled_bar(page, subject_with_payload):
    """A chapter with some but not all of its topics finished sits strictly
    between the two ends rather than rounding to one of them."""
    chapters, body = subject_with_payload

    part_way = [
        index
        for index, chapter in enumerate(body["chapters"])
        if 0 < chapter["progress"] < chapter["child_count"]
    ]
    if not part_way:
        pytest.skip("No chapter in this subject is part finished")

    for index in part_way:
        assert 0 < chapters.get_progress_percent(index) < 100, body["chapters"][index]["title"]

    print("Part finished chapters:", [body["chapters"][i]["title"] for i in part_way])


def test_a_chapter_is_only_full_when_none_of_its_topics_are_left(page, subject_with_payload):
    """The bar reaching the end and every topic being finished are the same
    thing, in both directions."""
    chapters, body = subject_with_payload

    for index, chapter in enumerate(body["chapters"]):
        everything_done = chapter["progress"] == chapter["child_count"]
        shows_full = chapters.get_progress_percent(index) == 100

        assert shows_full is everything_done, chapter["title"]


# Watching a chapter out in full is the last thing this file does, because it
# uses up whatever is left in the chapter: see
# test_finishing_every_video_in_a_chapter_takes_it_to_100 at the end.

def test_chapter_progress_is_kept_after_a_reload(page, subject_with_payload):
    chapters, body = subject_with_payload
    before = [
        (chapters.get_completed_counts(i), chapters.get_progress_percent(i))
        for i in range(chapters.chapter_count())
    ]

    chapters.open(page.url)

    after = [
        (chapters.get_completed_counts(i), chapters.get_progress_percent(i))
        for i in range(chapters.chapter_count())
    ]
    assert after == before


# ---------------------------------------------------------------------------
# 4. Subject progress
#
# A subject publishes no figure of its own: the home card carries none and the
# home call serves none, so the chapter list is the only place a subject says
# anything about how far through it is. What is asserted is the sum of those
# cards.
# ---------------------------------------------------------------------------

def test_the_subject_card_on_home_carries_no_progress(page, home_page, working_content):
    """Kept as a statement of where subject progress is and is not shown, so
    that a figure appearing on the card is noticed rather than assumed."""
    card = home_page.get_subjects().nth(working_content["subject"])

    expect(card.locator(".ch-item-progress-bar")).to_have_count(0)
    expect(card.locator(".tp-progress-ring-wrap")).to_have_count(0)
    assert not re.search(r"\d+%|\d+/\d+", card.inner_text())


def test_subject_progress_is_the_sum_of_its_chapters(page, subject_with_payload):
    chapters, body = subject_with_payload

    served = (
        sum(chapter["progress"] for chapter in body["chapters"]),
        sum(chapter["child_count"] for chapter in body["chapters"]),
    )

    assert chapters.get_subject_totals() == served

    print("Subject total:", served, "=", round(chapters.get_subject_percent(), 1), "%")


def test_partly_finished_chapters_show_up_in_the_subject_total(page, subject_with_payload):
    chapters, body = subject_with_payload
    done, total = chapters.get_subject_totals()

    if done == 0:
        pytest.skip("Nothing in this subject has been finished yet")
    if done == total:
        pytest.skip("This subject is already finished")

    assert 0 < chapters.get_subject_percent() < 100
    assert any(chapter["progress"] > 0 for chapter in body["chapters"])


def test_a_subject_is_not_finished_while_a_chapter_is_left(page, subject_with_payload):
    chapters, body = subject_with_payload

    everything_done = all(
        chapter["progress"] == chapter["child_count"] for chapter in body["chapters"]
    )

    assert (chapters.get_subject_percent() == 100) is everything_done

    if not everything_done:
        left = [
            chapter["title"]
            for chapter in body["chapters"]
            if chapter["progress"] < chapter["child_count"]
        ]
        assert chapters.get_subject_percent() < 100, f"still outstanding: {left}"


def test_subject_progress_is_kept_after_a_reload(page, subject_with_payload):
    chapters, _ = subject_with_payload
    before = chapters.get_subject_totals()

    chapters.open(page.url)

    assert chapters.get_subject_totals() == before


# ---------------------------------------------------------------------------
# 5. Progress state transitions
#
# One subtopic taken the whole way, so the states are seen in the order a
# student would meet them rather than one at a time.
# ---------------------------------------------------------------------------

def test_a_subtopic_from_nothing_through_part_way_to_finished(page, topic_page):
    """Not started, part way, nearly there, finished - with the subtopic left
    and reopened between each step, so every reading is one the app has been
    asked for again rather than one still on screen."""
    syllabus = reload_syllabus(page, topic_page)

    unstarted = [
        (index, subtopic)
        for index, (_, _, subtopic) in enumerate(flat_subtopics(syllabus))
        if subtopic["watched_duration"] == 0 and subtopic["video_duration"] > 0
    ]
    if not unstarted:
        pytest.skip("No unstarted subtopic left in this chapter")

    index, subtopic = min(unstarted, key=lambda found: found[1]["video_duration"])
    print("Walking:", subtopic["title"], subtopic["video_duration"], "seconds")

    # Not started.
    assert topic_page.get_subtopic_progress(index) == 0
    expect(topic_page.get_ring_circles(index)).to_have_count(1)

    for fraction in (0.4, 0.9):
        posted = watch_and_record(page, topic_page, index, fraction, subtopic)

        syllabus = reload_syllabus(page, topic_page)
        recorded = flat_subtopics(syllabus)[index][2]

        assert recorded["watched_duration"] == posted["progress"]
        assert recorded["video_completed"] is False
        assert topic_page.get_subtopic_progress(index) == pytest.approx(
            fraction * 100, abs=POSITION_MARGIN
        )
        expect(topic_page.get_ring_circles(index)).to_have_count(2)
        print(" at", round(fraction * 100), "% ->", round(topic_page.get_subtopic_progress(index), 1))

    # Finished.
    player = open_player(page, topic_page, index)
    posted = finish_video(page, player)
    assert posted["progress"] == posted["duration"]
    player.click_back()

    syllabus = reload_syllabus(page, topic_page)
    recorded = flat_subtopics(syllabus)[index][2]

    assert recorded["video_completed"] is True
    assert topic_page.get_subtopic_progress(index) == pytest.approx(100, abs=RING_MARGIN)


def test_finishing_a_topic_carries_up_to_the_chapter_card(page, subject_page, working_content):
    """The whole chain in one pass: the last subtopic of a topic is finished,
    the topic is ticked, the header on the topic list counts one more lesson,
    and the card back on the subject page moves with it."""
    if subject_page.is_chapter_locked(working_content["chapter"]):
        pytest.skip("The chapter this run works in is locked")

    subject_url = page.url
    card_index = working_content["chapter"]
    chapter_before = subject_page.get_completed_counts(card_index)

    subject_page.click_chapter(card_index)
    topics = TopicPage(page)
    topics.wait_for_topics_loaded()
    topics.expand_all_topics()
    syllabus = reload_syllabus(page, topics)

    outstanding = last_subtopic_of_a_finishable_topic(syllabus)
    if outstanding is None:
        pytest.skip(
            "No topic here is one subtopic away from being finished with no "
            "quiz outstanding"
        )

    topic_index, flat_index, topic = outstanding
    lessons_before, lesson_total = topics.get_lessons_completed_counts()

    player = open_player(page, topics, flat_index)
    finish_video(page, player)
    player.click_back()

    reload_syllabus(page, topics)

    assert topics.is_topic_complete(topic_index) is True
    assert topics.get_lessons_completed_counts() == (lessons_before + 1, lesson_total)

    with page.expect_response(CHAPTERS_API) as answer:
        page.goto(subject_url)
    served = answer.value.json()["chapters"][card_index]
    subject_page.wait_for_chapters_loaded()

    done, total = chapter_before

    assert served["progress"] == done + 1
    assert subject_page.get_completed_counts(card_index) == (done + 1, total)
    assert subject_page.get_progress_percent(card_index) == pytest.approx(
        (done + 1) / total * 100, abs=RING_MARGIN
    )

    print(topic["title"], "finished ->", f"chapter {done + 1}/{total}")


def test_finishing_every_video_in_a_chapter_takes_it_to_100(
    page, home_page, content_survey, working_content
):
    """A chapter watched out in full, end to end.

    It has to be a chapter that watching can actually finish - one with no quiz
    outstanding on any of its topics - and a small enough one to sit through.
    Whatever is still outstanding in it is watched, so this reports the same on
    a chapter that was already complete as on one it completes itself."""
    finishable = [
        row for row in content_survey
        if row["subject"] == working_content["subject"]
        and row["quiz_free"]
        and row["topics"] > 0
        and row["outstanding"] <= CHAPTER_COMPLETION_LIMIT
    ]
    if not finishable:
        pytest.skip(
            "No unlocked chapter in this subject is both short enough to watch "
            "out and free of outstanding quizzes"
        )

    index = min(finishable, key=lambda row: row["outstanding"])["chapter"]

    chapters, body = open_subject_with_payload(page, home_page, working_content["subject"])
    chapter = body["chapters"][index]
    subject_url = page.url
    chapters.click_chapter(index)

    topics = TopicPage(page)
    topics.wait_for_topics_loaded()
    topics.expand_all_topics()
    syllabus = reload_syllabus(page, topics)

    outstanding = [
        flat_index
        for flat_index, (_, _, subtopic) in enumerate(flat_subtopics(syllabus))
        if not subtopic["video_completed"]
    ]
    print(chapter["title"], "-", len(outstanding), "videos left to watch")

    for flat_index in outstanding:
        player = open_player(page, topics, flat_index)
        finish_video(page, player)
        player.click_back()
        topics.wait_for_topics_loaded()
        topics.expand_all_topics()

    syllabus = reload_syllabus(page, topics)
    total = len(syllabus["topics"])

    assert finished_topic_count(syllabus) == total
    assert topics.get_lessons_completed_counts() == (total, total)
    assert topics.get_progress_percent() == 100

    with page.expect_response(CHAPTERS_API) as answer:
        page.goto(subject_url)
    served = answer.value.json()["chapters"][index]
    chapters.wait_for_chapters_loaded()

    assert served["progress"] == served["child_count"]
    assert chapters.get_completed_counts(index) == (served["child_count"],) * 2
    assert chapters.get_progress_percent(index) == 100


def test_finishing_a_chapter_moves_the_subject_total(page, subject_with_payload):
    """The top of the chain: a chapter that is complete counts in full towards
    the subject, and the subject stays short of the end while another chapter
    is still outstanding."""
    chapters, body = subject_with_payload

    finished = [
        chapter for chapter in body["chapters"]
        if chapter["child_count"] > 0 and chapter["progress"] == chapter["child_count"]
    ]
    if not finished:
        pytest.skip("No chapter in this subject has been finished")

    done, total = chapters.get_subject_totals()

    assert done >= sum(chapter["child_count"] for chapter in finished)
    assert chapters.get_subject_percent() == pytest.approx(done / total * 100, abs=RING_MARGIN)

    if len(finished) < len(body["chapters"]):
        assert chapters.get_subject_percent() < 100

    print(
        "Finished chapters:", [chapter["title"] for chapter in finished],
        "-> subject", f"{done}/{total}",
    )
