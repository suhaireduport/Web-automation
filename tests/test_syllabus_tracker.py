"""The Syllabus Tracker: how much of the course has actually been covered.

The entry is the More button on the Syllabus Tracker card on Analysis - the
third card down, which is only built once it is scrolled to - or a subject on
that card, which opens the tracker with that subject already showing. One call
draws everything behind it, analytics/ability/syllabus-tracker, and it takes
nothing at all: the course title and every subject on it come back in one
answer, each with its chapters and each chapter with its topics.

That is worth saying plainly, because it decides what subject-wise means here.
Changing subject is the screen sorting through an answer it already has; there
is no per subject call to capture and no second request when a tab is pressed.
So a subject-wise check is that the right slice of the one payload is on
screen - and, just as much, that no other subject's slice is.

Nothing on the screen is answered outright. Every count is worked out from the
topics, and a topic is covered when its progress reaches 100:

    the ring at the top   done / total over every subject, as a percentage
    the subject bar       done / total over the subject showing
    a chapter row         done / total over that chapter's topics
    a topic row           its own progress

so the checks here are as much that the arithmetic holds as that the numbers
came through. A topic can also carry a syllabus_label - Class Room, Home
Assignments - which the screen writes beside the title in the colour the label
came with.

Nothing about the numbers is written down. The student studies while the suite
runs and the dev course changes underneath it, so every subject, chapter, topic
and count is taken from the call at run time.
"""
import re

import pytest
from playwright.sync_api import expect

from conftest import STUDENT_MOBILE
from pages.analytics_page import AnalyticsPage
from pages.home_page import HomePage
from pages.question_library_section_page import normalise
from pages.syllabus_tracker_page import (
    SYLLABUS_API,
    SyllabusTrackerPage,
    chapter_progress,
    hex_to_rgb,
    ordered_topics,
    overall_progress,
    percent,
    read_count,
    subject_progress,
)

ANALYTICS_URL = "https://eduport-react.pages.dev/analytics"
SYLLABUS_CARD = "Syllabus Tracker"

PERCENTAGE = re.compile(r"^\d+%$")
COUNT = re.compile(r"^\d+/\d+$")

# The subject bar is drawn from a raw fraction rather than a rounded one, so a
# reading off it is compared to this much rather than exactly.
BAR_TOLERANCE = 0.01


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(STUDENT_MOBILE)


@pytest.fixture
def opened(page):
    """The tracker open on the first subject, and the answer it drew itself
    from.

    The two are taken together on purpose. The dev course this account is
    enrolled on changes on its own, so asking the call again after the screen
    is up can hand back a different course than the one on screen, and a
    comparison against it would be comparing two courses rather than checking
    one."""
    tracker = SyllabusTrackerPage(page)
    body = tracker.open().json()
    if not body.get("results"):
        pytest.skip("The syllabus call answers no subjects for this course")
    return tracker, body


@pytest.fixture
def syllabus(opened):
    return opened[0]


@pytest.fixture
def course(opened):
    """The whole answer: course_title and the subjects under results."""
    return opened[1]


@pytest.fixture
def subjects(course):
    return course["results"]


@pytest.fixture
def analytics(page):
    """Analysis, scrolled far enough down that the syllabus card is built.

    The ability and syllabus cards are only put up once they are scrolled
    near, so the syllabus card is not in the page at all until then."""
    home = HomePage(page)
    home.get_analysis_button().click()
    page.wait_for_url(ANALYTICS_URL)
    screen = AnalyticsPage(page)
    screen.wait_for_analytics_loaded()
    screen.scroll_to_bottom()
    return screen


# ---------------------------------------------------------------------------
# Opening it, and what is on the screen
# ---------------------------------------------------------------------------

def test_the_tracker_opens_from_the_syllabus_card_on_analysis(page, analytics):
    """The third card down is the way in, and it lands on a built screen
    rather than only on the route."""
    expect(analytics.get_syllabus_tracker_card()).to_be_visible()
    expect(analytics.get_syllabus_more_button()).to_be_visible()

    analytics.click_syllabus_more()

    expect(page).to_have_url(SyllabusTrackerPage.URL)
    tracker = SyllabusTrackerPage(page)
    tracker.wait_for_loaded()
    expect(tracker.get_title()).to_have_text("Syllabus Tracker")


def test_the_header_carries_a_way_back_and_a_way_to_the_help(syllabus):
    expect(syllabus.get_back_button()).to_be_visible()
    expect(syllabus.get_title()).to_have_text("Syllabus Tracker")
    expect(syllabus.get_info_button()).to_be_visible()


def test_a_spinner_stands_in_while_the_call_is_out(page):
    """Hold the syllabus call open so the loading state cannot be missed."""
    held = []
    page.route(SYLLABUS_API, lambda route: held.append(route))

    page.goto(SyllabusTrackerPage.URL, wait_until="commit")

    tracker = SyllabusTrackerPage(page)
    expect(tracker.get_loading()).to_be_visible(timeout=15000)
    expect(tracker.get_spinner()).to_be_visible()
    expect(tracker.get_overall()).to_have_count(0)


def test_the_top_of_the_screen_sums_up_the_whole_course(syllabus):
    expect(syllabus.get_overall()).to_be_visible()
    expect(syllabus.get_overall_course()).not_to_be_empty()
    expect(syllabus.get_overall_count()).to_have_text(COUNT)
    expect(syllabus.get_overall_ring()).to_be_visible()
    expect(syllabus.get_overall_percentage()).to_have_text(PERCENTAGE)

    done, total = syllabus.read_overall_count()
    assert done <= total, f"{done} of {total} covered"


def test_one_tab_a_subject_and_exactly_one_of_them_showing(syllabus, subjects):
    expect(syllabus.get_tabs()).to_have_count(len(subjects))
    expect(syllabus.get_active_tab()).to_have_count(1)
    expect(syllabus.get_active_tab()).to_have_text(normalise(subjects[0]["title"]))
    for name in syllabus.get_tab_names():
        assert name, "a subject tab was left blank"


def test_the_subject_summary_names_it_and_counts_it(syllabus):
    expect(syllabus.get_subject_summary()).to_be_visible()
    expect(syllabus.get_subject_name()).to_have_text(
        syllabus.get_active_tab().inner_text()
    )
    expect(syllabus.get_subject_count()).to_have_text(COUNT)

    done, total = syllabus.read_subject_count()
    assert done <= total, f"{done} of {total} covered"


def test_the_chapters_are_numbered_named_and_counted(syllabus):
    expect(syllabus.get_chapters().first).to_be_visible()
    count = syllabus.get_chapters().count()

    assert syllabus.get_chapter_numbers() == [str(n + 1) for n in range(count)]
    for title in syllabus.get_chapter_titles():
        assert title, "a chapter was left unnamed"
    for reading in syllabus.get_chapter_counts():
        assert COUNT.match(reading), f"a chapter read {reading!r}"
        done, total = read_count(reading)
        assert done <= total, f"a chapter read {reading!r}"


def test_a_chapter_opens_onto_its_topics_and_closes_again(syllabus):
    expect(syllabus.get_topics(0)).to_have_count(0)

    syllabus.expand_chapter(0)

    expect(syllabus.get_topics(0).first).to_be_visible()
    for index, title in enumerate(syllabus.get_topic_titles(0)):
        assert title.startswith(f"{index + 1}. "), f"a topic read {title!r}"
    for percentage in syllabus.get_topic_percentages(0):
        assert PERCENTAGE.match(percentage), f"a topic read {percentage!r}"

    syllabus.collapse_chapter(0)
    expect(syllabus.get_topics(0)).to_have_count(0)


def test_the_help_sheet_explains_this_tracker_and_only_this_one(syllabus):
    """Analysis explains all three trackers at once; a tracker's own sheet
    explains itself."""
    syllabus.click_info_button()

    expect(syllabus.get_info_sheet()).to_be_visible()
    expect(syllabus.get_info_sheet_title()).to_have_text("How syllabus tracker works?")
    expect(syllabus.get_info_sections()).to_have_count(1)
    expect(syllabus.get_info_headings()).to_have_text(["Syllabus Tracker"])
    expect(syllabus.get_info_bodies()).not_to_be_empty()

    syllabus.close_info_sheet()
    expect(syllabus.get_info_sheet()).to_have_count(0)


def test_back_returns_to_the_screen_it_was_opened_from(page, analytics):
    analytics.click_syllabus_more()
    tracker = SyllabusTrackerPage(page)
    tracker.wait_for_loaded()

    tracker.click_back()

    expect(page).to_have_url(ANALYTICS_URL)


# ---------------------------------------------------------------------------
# The overall reading, against the call it is drawn from
# ---------------------------------------------------------------------------

def test_opening_the_tracker_asks_for_the_syllabus_tracker_call(page):
    """One call, no query of its own, the course named in it and every subject
    on the course in it."""
    answer = SyllabusTrackerPage(page).open()

    assert answer.status == 200, f"syllabus-tracker answered {answer.status}"
    body = answer.json()
    assert set(body) >= {"results", "course_title"}, body.keys()
    assert body["course_title"].strip(), body["course_title"]

    for subject in body["results"]:
        assert subject["title"].strip(), subject
        for chapter in subject["chapters"]:
            for topic in chapter["topics"]:
                assert 0 <= topic["progress"] <= 100, topic
                assert topic["order"] is not None, topic


def test_the_course_progress_matches_the_call(syllabus, course, subjects):
    """The name, the count and the ring are all the same arithmetic over every
    topic on the course: covered at 100, and the percentage rounded."""
    done, total = overall_progress(subjects)

    expect(syllabus.get_overall_course()).to_have_text(normalise(course["course_title"]))
    expect(syllabus.get_overall_count()).to_have_text(f"{done}/{total}")
    expect(syllabus.get_overall_percentage()).to_have_text(f"{percent(done, total)}%")


def test_the_tabs_are_the_subjects_the_call_answered_in_its_own_order(syllabus, subjects):
    expect(syllabus.get_tabs()).to_have_text(
        [normalise(subject["title"]) for subject in subjects]
    )


def test_the_subject_summary_matches_the_subject_it_is_showing(syllabus, subjects):
    subject = subjects[0]
    done, total = subject_progress(subject)

    expect(syllabus.get_subject_name()).to_have_text(normalise(subject["title"]))
    expect(syllabus.get_subject_count()).to_have_text(f"{done}/{total}")

    if done:
        assert abs(syllabus.get_subject_bar_width() - done / total * 100) < BAR_TOLERANCE
    else:
        expect(syllabus.get_subject_bar_fill()).to_have_count(0)


def test_the_chapters_match_the_subject_the_call_answered(syllabus, subjects):
    """Every chapter of the subject showing, named and counted, and its bar
    drawn to the share of it that is covered."""
    chapters = subjects[0]["chapters"]

    expect(syllabus.get_chapters()).to_have_count(len(chapters))
    expect(syllabus.get_chapters().locator(".st-chapter-info strong")).to_have_text(
        [normalise(chapter["title"]) for chapter in chapters]
    )
    assert syllabus.get_chapter_counts() == [
        "{}/{}".format(*chapter_progress(chapter)) for chapter in chapters
    ]

    for index, chapter in enumerate(chapters):
        done, total = chapter_progress(chapter)
        fill = syllabus.get_chapter_bar_fill(index)
        if percent(done, total):
            assert fill.evaluate("el => el.style.width") == f"{percent(done, total)}%"
        else:
            expect(fill).to_have_count(0)


def test_an_opened_chapter_lists_the_topics_the_call_answered(syllabus, subjects):
    """Numbered from one and put in the topics' own order rather than the
    order they came back in, each showing its own progress."""
    chapter = subjects[0]["chapters"][0]
    topics = ordered_topics(chapter)

    syllabus.expand_chapter(0)

    expect(syllabus.get_topics(0)).to_have_count(len(topics))
    assert syllabus.get_topic_titles(0) == [
        normalise(f"{index + 1}. {topic['title']}") for index, topic in enumerate(topics)
    ]
    assert syllabus.get_topic_percentages(0) == [
        f"{topic['progress']}%" for topic in topics
    ]


def test_a_topic_label_is_written_in_the_colour_it_came_with(syllabus, subjects):
    """Class Room, Home Assignments and the like. Only the topics carrying one
    get one, so the labels on screen are the labelled topics in order."""
    found = next(
        (
            (tab, index, chapter)
            for tab, subject in enumerate(subjects)
            for index, chapter in enumerate(subject["chapters"])
            if any(topic["syllabus_label"] for topic in chapter["topics"])
        ),
        None,
    )
    if found is None:
        pytest.skip("No topic on this course carries a syllabus label")
    tab, index, chapter = found
    topics = ordered_topics(chapter)

    syllabus.click_tab(tab)
    syllabus.expand_chapter(index)

    labelled = [topic for topic in topics if topic["syllabus_label"]]
    assert syllabus.get_topic_labels(index) == [
        normalise(topic["syllabus_label"]["name"]) for topic in labelled
    ]

    at = topics.index(labelled[0])
    expect(syllabus.get_topic_label(index, at)).to_have_css(
        "color", hex_to_rgb(labelled[0]["syllabus_label"]["color"])
    )


# ---------------------------------------------------------------------------
# Subject by subject
# ---------------------------------------------------------------------------

def test_every_subject_tab_shows_its_own_slice_and_no_one_else_s(syllabus, subjects):
    """Walked over every subject on the course.

    Each tab has to put up its own name, its own count and its own chapters -
    and the chapters belonging only to the subject that was left have to be
    gone."""
    for index, subject in enumerate(subjects):
        syllabus.click_tab(index)
        done, total = subject_progress(subject)

        expect(syllabus.get_subject_name()).to_have_text(normalise(subject["title"]))
        expect(syllabus.get_subject_count()).to_have_text(f"{done}/{total}")
        expect(syllabus.get_chapters()).to_have_count(len(subject["chapters"]))

        mine = [normalise(chapter["title"]) for chapter in subject["chapters"]]
        shown = syllabus.get_chapter_titles()
        assert shown == mine

        elsewhere = {
            normalise(chapter["title"])
            for other in subjects
            if other["id"] != subject["id"]
            for chapter in other["chapters"]
        } - set(mine)
        assert not elsewhere & set(shown), (
            f"{subject['title'].strip()} is showing chapters that belong only "
            f"to another subject: {sorted(elsewhere & set(shown))}"
        )


def test_the_course_count_is_the_subjects_added_up(syllabus, subjects):
    """The ring at the top against the subjects underneath it, read off the
    screen a tab at a time - the screen has to agree with itself."""
    counted = [0, 0]
    for index in range(len(subjects)):
        syllabus.click_tab(index)
        done, total = syllabus.read_subject_count()
        counted = [counted[0] + done, counted[1] + total]

    assert tuple(counted) == syllabus.read_overall_count()
    assert tuple(counted) == overall_progress(subjects)


def test_the_screen_opens_on_the_subject_the_route_asks_for(page):
    """?subject= is an index into the answered list, not a subject id."""
    tracker = SyllabusTrackerPage(page)
    subjects = tracker.open().json()["results"]
    if len(subjects) < 2:
        pytest.skip("One subject on this course, so there is no index to prove")
    wanted = len(subjects) - 1

    subjects = tracker.open(subject=wanted).json()["results"]

    expect(tracker.get_subject_name()).to_have_text(normalise(subjects[wanted]["title"]))
    expect(tracker.get_active_tab()).to_have_text(normalise(subjects[wanted]["title"]))


def test_a_subject_on_the_analysis_card_opens_the_tracker_on_that_subject(
    page, analytics
):
    """The card's subject strip is a way in of its own, and it carries which
    subject was pressed through to the tracker.

    Which subject that is comes off the card rather than out of a fresh call,
    so the name being looked for is the name that was actually pressed."""
    if not analytics.card_subject_count(SYLLABUS_CARD):
        pytest.skip("The syllabus card carries no subjects for this course")
    named = analytics.get_card_subject_names(SYLLABUS_CARD)
    wanted = len(named) - 1
    counted = analytics.get_card_subject_values(SYLLABUS_CARD)[wanted]

    analytics.click_card_subject(SYLLABUS_CARD, wanted)

    expect(page).to_have_url(f"{SyllabusTrackerPage.URL}?subject={wanted}")
    tracker = SyllabusTrackerPage(page)
    tracker.wait_for_loaded()
    expect(tracker.get_subject_name()).to_have_text(named[wanted])
    expect(tracker.get_subject_count()).to_have_text(counted)


def test_the_card_on_analysis_and_the_tracker_read_the_same(page, analytics):
    """Two screens, one call. The strip on the card and the ring above the
    tabs are the same arithmetic and have to come out the same."""
    analytics.card_subject_count(SYLLABUS_CARD)
    course = analytics.get_syllabus_course().inner_text().strip()
    counted = analytics.get_syllabus_count().inner_text().strip()
    percentage = analytics.get_syllabus_percentage().inner_text().strip()
    named = analytics.get_card_subject_names(SYLLABUS_CARD)
    values = analytics.get_card_subject_values(SYLLABUS_CARD)

    analytics.click_syllabus_more()
    tracker = SyllabusTrackerPage(page)
    tracker.wait_for_loaded()

    expect(tracker.get_overall_course()).to_have_text(course)
    expect(tracker.get_overall_count()).to_have_text(counted)
    expect(tracker.get_overall_percentage()).to_have_text(percentage)
    expect(tracker.get_tabs()).to_have_text(named)

    for index, reading in enumerate(values):
        tracker.click_tab(index)
        expect(tracker.get_subject_count()).to_have_text(reading)


# ---------------------------------------------------------------------------
# Known defect: a subject index past the end of the list
#
# ?subject= is not checked against the list it indexes. A value past the end
# leaves the screen with its header, its course ring and its tabs but nothing
# under them - no subject summary, no chapters and nothing saying why - and no
# tab reads as selected. Anything below zero or unreadable is caught and falls
# back to the first subject, which is what this should do too. The ability
# tracker has the same fault, from the same guard.
#
# Left as xfail so the suite stays green and this reports XPASS the moment the
# app starts falling back.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="?subject= past the end of the subject list draws an empty screen "
    "instead of falling back to the first subject",
)
def test_a_subject_index_past_the_end_falls_back_to_the_first_subject(page):
    tracker = SyllabusTrackerPage(page)
    subjects = tracker.open().json()["results"]

    tracker.open(subject=len(subjects) + 50, wait=False)

    expect(tracker.get_subject_name()).to_have_text(normalise(subjects[0]["title"]))
