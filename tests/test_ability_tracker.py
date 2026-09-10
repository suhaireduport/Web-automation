"""The Ability Tracker: how well the student answers, subject by subject.

The entry is the More button on the Ability Tracker card on Analysis, or a
subject on that card, which opens the tracker with that subject already
showing. One call draws everything behind it - analytics/ability/list - and it
takes nothing at all: every subject on the course comes back in one answer,
each with its chapters and each chapter with its topics.

That is worth saying plainly, because it decides what subject-wise means here.
Changing subject is the screen sorting through an answer it already has; there
is no per subject call to capture and no second request when a tab is pressed.
So a subject-wise check is that the right slice of the one payload is on
screen - and, just as much, that no other subject's slice is.

Every level carries an ability_index, and a topic and a chapter also carry a
category: Strong, Average, Weak, Poor or Not Started. The filter counts topics
by category over the selected subject and keeps the chapters holding one.

Nothing about the numbers is written down here. The student practises while the
suite runs and the dev course changes underneath it, so every subject, chapter,
topic and percentage is taken from the call at run time.

What is deliberately not here: the ability card on Analysis - its subject strip
against the same call, and its More button going where it says - stays in
test_analytics.py. What is here is the screen behind it.
"""
import re

import pytest
from playwright.sync_api import expect

from conftest import STUDENT_MOBILE
from pages.ability_tracker_page import (
    ABILITY_API,
    AbilityTrackerPage,
    CATEGORIES,
    CATEGORY_LABELS,
    bar_colour_class,
    category_counts,
    chapters_holding,
    ordered_topics,
    topics_of,
)
from pages.analytics_page import AnalyticsPage
from pages.home_page import HomePage
from pages.question_library_section_page import normalise

ANALYTICS_URL = "https://eduport-react.pages.dev/analytics"
ABILITY_CARD = "Ability Tracker"

PERCENTAGE = re.compile(r"^\d+%$")


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
    tracker = AbilityTrackerPage(page)
    answered = tracker.open().json()["subjects"]
    if not answered:
        pytest.skip("The ability call answers no subjects for this course")
    return tracker, answered


@pytest.fixture
def ability(opened):
    return opened[0]


@pytest.fixture
def subjects(opened):
    return opened[1]


@pytest.fixture
def analytics(page):
    """Analysis, the screen the tracker is opened from."""
    home = HomePage(page)
    home.get_analysis_button().click()
    page.wait_for_url(ANALYTICS_URL)
    screen = AnalyticsPage(page)
    screen.wait_for_analytics_loaded()
    return screen


def a_filled_category(subject):
    """A category the selected subject actually has topics in.

    Ticking one it has none of is refused by the screen, so a filter test has
    to be told which one to reach for."""
    counts = category_counts(subject)
    return next((category for category in CATEGORIES if counts[category]), None)


# ---------------------------------------------------------------------------
# Opening it, and what is on the screen
# ---------------------------------------------------------------------------

def test_the_tracker_opens_from_the_ability_card_on_analysis(page, analytics):
    """The card's More button is the way in, and it lands on a built screen
    rather than only on the route."""
    analytics.click_ability_more()

    expect(page).to_have_url(AbilityTrackerPage.URL)
    tracker = AbilityTrackerPage(page)
    tracker.wait_for_loaded()
    expect(tracker.get_title()).to_have_text("Ability Tracker")


def test_the_header_carries_a_way_back_and_a_way_to_the_help(ability):
    expect(ability.get_back_button()).to_be_visible()
    expect(ability.get_title()).to_have_text("Ability Tracker")
    expect(ability.get_info_button()).to_be_visible()


def test_a_spinner_stands_in_while_the_call_is_out(page):
    """Hold the ability call open so the loading state cannot be missed."""
    held = []
    page.route(ABILITY_API, lambda route: held.append(route))

    page.goto(AbilityTrackerPage.URL, wait_until="commit")

    tracker = AbilityTrackerPage(page)
    expect(tracker.get_loading()).to_be_visible(timeout=15000)
    expect(tracker.get_spinner()).to_be_visible()
    expect(tracker.get_summary()).to_have_count(0)


def test_one_tab_a_subject_and_exactly_one_of_them_showing(ability, subjects):
    expect(ability.get_tabs()).to_have_count(len(subjects))
    expect(ability.get_active_tab()).to_have_count(1)
    expect(ability.get_active_tab()).to_have_text(normalise(subjects[0]["title"]))
    for name in ability.get_tab_names():
        assert name, "a subject tab was left blank"


def test_the_summary_names_the_subject_and_rates_it(ability):
    expect(ability.get_summary()).to_be_visible()
    expect(ability.get_summary_name()).to_have_text(ability.get_active_tab().inner_text())
    expect(ability.get_summary_percentage()).to_have_text(PERCENTAGE)


def test_the_chapters_are_numbered_named_and_rated(ability):
    expect(ability.get_chapters().first).to_be_visible()
    count = ability.get_chapters().count()

    assert ability.get_chapter_numbers() == [str(n + 1) for n in range(count)]
    for title in ability.get_chapter_titles():
        assert title, "a chapter was left unnamed"
    for percentage in ability.get_chapter_percentages():
        assert PERCENTAGE.match(percentage), f"a chapter read {percentage!r}"


def test_a_chapter_opens_onto_its_topics_and_closes_again(ability):
    expect(ability.get_topics(0)).to_have_count(0)

    ability.expand_chapter(0)

    expect(ability.get_topics(0).first).to_be_visible()
    for index, title in enumerate(ability.get_topic_titles(0)):
        assert title.startswith(f"{index + 1}. "), f"a topic read {title!r}"
    for percentage in ability.get_topic_percentages(0):
        assert PERCENTAGE.match(percentage), f"a topic read {percentage!r}"

    ability.collapse_chapter(0)
    expect(ability.get_topics(0)).to_have_count(0)


def test_the_filter_opens_on_the_five_categories_and_starts_off_all(ability):
    expect(ability.get_filter_button()).to_be_visible()
    assert ability.get_filter_label() == "All"

    ability.open_filter()

    expect(ability.get_filter_heading()).to_have_text("Topics")
    expect(ability.get_filter_rows()).to_have_count(len(CATEGORIES))
    assert ability.get_filter_names() == [CATEGORY_LABELS[c] for c in CATEGORIES]
    expect(ability.get_clear_button()).to_have_text("CLEAR")
    expect(ability.get_apply_button()).to_have_text("Apply")


def test_the_help_sheet_explains_this_tracker_and_only_this_one(ability):
    """Analysis explains all three trackers at once; a tracker's own sheet
    explains itself."""
    ability.click_info_button()

    expect(ability.get_info_sheet()).to_be_visible()
    expect(ability.get_info_sheet_title()).to_have_text("How ability tracker works?")
    expect(ability.get_info_sections()).to_have_count(1)
    expect(ability.get_info_headings()).to_have_text(["Ability Tracker"])
    expect(ability.get_info_bodies()).not_to_be_empty()

    ability.close_info_sheet()
    expect(ability.get_info_sheet()).to_have_count(0)


def test_back_returns_to_the_screen_it_was_opened_from(page, analytics):
    analytics.click_ability_more()
    tracker = AbilityTrackerPage(page)
    tracker.wait_for_loaded()

    tracker.click_back()

    expect(page).to_have_url(ANALYTICS_URL)


# ---------------------------------------------------------------------------
# The overall reading, against the call it is drawn from
# ---------------------------------------------------------------------------

def test_opening_the_tracker_asks_for_the_ability_list(page):
    """One call, no query of its own, and every subject on the course in it."""
    answer = AbilityTrackerPage(page).open()

    assert answer.status == 200, f"ability answered {answer.status}"
    body = answer.json()
    assert list(body) == ["subjects"], body.keys()

    for subject in body["subjects"]:
        assert subject["title"].strip(), subject
        assert 0 <= subject["ability_index"] <= 100, subject
        for chapter in subject["chapters"]:
            assert 0 <= chapter["ability_index"] <= 100, chapter
            for topic in chapter["topics"]:
                assert topic["category"] in CATEGORIES, topic


def test_the_tabs_are_the_subjects_the_call_answered_in_its_own_order(ability, subjects):
    expect(ability.get_tabs()).to_have_text(
        [normalise(subject["title"]) for subject in subjects]
    )


def test_the_summary_matches_the_subject_it_is_showing(ability, subjects):
    subject = subjects[0]

    expect(ability.get_summary_name()).to_have_text(normalise(subject["title"]))
    expect(ability.get_summary_percentage()).to_have_text(f"{subject['ability_index']}%")


def test_the_chapters_match_the_subject_the_call_answered(ability, subjects):
    chapters = subjects[0]["chapters"]

    expect(ability.get_chapters()).to_have_count(len(chapters))
    expect(ability.get_chapters().locator(".at-chapter-info strong")).to_have_text(
        [normalise(chapter["title"]) for chapter in chapters]
    )
    assert ability.get_chapter_percentages() == [
        f"{chapter['ability_index']}%" for chapter in chapters
    ]


def test_an_opened_chapter_lists_the_topics_the_call_answered(ability, subjects):
    """Numbered from one and put in the order the call gave them, which is the
    topics' own order rather than the order they came back in."""
    chapter = subjects[0]["chapters"][0]
    topics = ordered_topics(chapter)

    ability.expand_chapter(0)

    expect(ability.get_topics(0)).to_have_count(len(topics))
    assert ability.get_topic_titles(0) == [
        normalise(f"{index + 1}. {topic['title']}") for index, topic in enumerate(topics)
    ]
    assert ability.get_topic_percentages(0) == [
        f"{topic['ability_index']}%" for topic in topics
    ]


def test_a_chapter_bar_is_drawn_to_its_own_index_and_band(ability, subjects):
    """A chapter with no ability yet is left as an empty trough rather than a
    bar of zero width, and one with ability is painted to its index in the
    colour its band calls for."""
    for index, chapter in enumerate(subjects[0]["chapters"]):
        fill = ability.get_chapter_bar_fill(index)
        if chapter["ability_index"] <= 0:
            expect(fill).to_have_count(0)
            continue

        assert fill.evaluate("el => el.style.width") == (
            f"{min(chapter['ability_index'], 100)}%"
        )
        expect(fill).to_have_class(
            re.compile(bar_colour_class(chapter["ability_index"], chapter["category"]))
        )


# ---------------------------------------------------------------------------
# Subject by subject
# ---------------------------------------------------------------------------

def test_every_subject_tab_shows_its_own_slice_and_no_one_else_s(ability, subjects):
    """Walked over every subject on the course.

    Each tab has to put up its own name, its own rating and its own chapters -
    and, where the course gives two subjects different chapters, the chapters
    of the subject that was left have to be gone."""
    for index, subject in enumerate(subjects):
        ability.click_tab(index)

        expect(ability.get_summary_name()).to_have_text(normalise(subject["title"]))
        expect(ability.get_summary_percentage()).to_have_text(
            f"{subject['ability_index']}%"
        )
        expect(ability.get_chapters()).to_have_count(len(subject["chapters"]))

        mine = [normalise(chapter["title"]) for chapter in subject["chapters"]]
        shown = ability.get_chapter_titles()
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


def test_the_screen_opens_on_the_subject_the_route_asks_for(page):
    """?subject= is an index into the answered list, not a subject id."""
    tracker = AbilityTrackerPage(page)
    subjects = tracker.open().json()["subjects"]
    if len(subjects) < 2:
        pytest.skip("One subject on this course, so there is no index to prove")
    wanted = len(subjects) - 1

    subjects = tracker.open(subject=wanted).json()["subjects"]

    expect(tracker.get_summary_name()).to_have_text(normalise(subjects[wanted]["title"]))
    expect(tracker.get_active_tab()).to_have_text(normalise(subjects[wanted]["title"]))


def test_a_route_asking_for_nothing_readable_opens_on_the_first_subject(page):
    tracker = AbilityTrackerPage(page)

    subjects = tracker.open(subject="not-a-number").json()["subjects"]

    expect(tracker.get_summary_name()).to_have_text(normalise(subjects[0]["title"]))


def test_a_subject_on_the_analysis_card_opens_the_tracker_on_that_subject(
    page, analytics
):
    """The card's subject strip is a way in of its own, and it carries which
    subject was pressed through to the tracker.

    Which subject that is comes off the card rather than out of a fresh call,
    so the name being looked for is the name that was actually pressed."""
    if not analytics.card_subject_count(ABILITY_CARD):
        pytest.skip("The ability card carries no subjects for this course")
    named = analytics.get_card_subject_names(ABILITY_CARD)
    wanted = len(named) - 1

    analytics.click_card_subject(ABILITY_CARD, wanted)

    expect(page).to_have_url(f"{AbilityTrackerPage.URL}?subject={wanted}")
    tracker = AbilityTrackerPage(page)
    tracker.wait_for_loaded()
    expect(tracker.get_summary_name()).to_have_text(named[wanted])
    expect(tracker.get_active_tab()).to_have_text(named[wanted])


# ---------------------------------------------------------------------------
# The filter, which is what makes this tracker its own thing
# ---------------------------------------------------------------------------

def test_the_filter_counts_the_selected_subject_s_topics_by_category(ability, subjects):
    """Counted over the whole subject rather than a chapter, and a category the
    subject has none of cannot be ticked."""
    counts = category_counts(subjects[0])

    ability.open_filter()

    assert ability.get_filter_counts() == [counts[category] for category in CATEGORIES]
    assert sum(counts.values()) == len(topics_of(subjects[0]))
    for category in CATEGORIES:
        checkbox = ability.get_filter_checkbox(category)
        if counts[category]:
            expect(checkbox).to_be_enabled()
        else:
            expect(checkbox).to_be_disabled()


def test_the_filter_counts_follow_the_subject_that_is_showing(ability, subjects):
    """The counts belong to the selected subject, so changing subject has to
    change them - not for a course whose subjects happen to match, which is
    said rather than asserted."""
    for index, subject in enumerate(subjects):
        ability.click_tab(index)
        ability.open_filter()

        assert ability.get_filter_counts() == [
            category_counts(subject)[category] for category in CATEGORIES
        ], f"the filter is not counting {subject['title'].strip()}"

        ability.apply_filter()


def test_ticking_a_category_keeps_the_chapters_holding_it(ability, subjects):
    """The filter works on chapters: one stays if any topic under it is in a
    ticked category. Clearing puts them all back."""
    subject = subjects[0]
    category = a_filled_category(subject)
    if category is None:
        pytest.skip("This subject has no topics in any category to filter on")

    ability.open_filter()
    ability.tick_filter(category)
    ability.apply_filter()

    assert ability.get_filter_label() == category
    kept = chapters_holding(subject, {category})
    expect(ability.get_chapters()).to_have_count(len(kept))
    assert ability.get_chapter_titles() == [normalise(c["title"]) for c in kept]

    ability.open_filter()
    ability.clear_filter()
    ability.apply_filter()

    assert ability.get_filter_label() == "All"
    expect(ability.get_chapters()).to_have_count(len(subject["chapters"]))


# ---------------------------------------------------------------------------
# Known defect: a subject index past the end of the list
#
# ?subject= is not checked against the list it indexes. A value past the end
# leaves the screen with its header, its tabs and its filter but nothing under
# them - no summary, no chapters and nothing saying why - and no tab reads as
# selected, so there is no sign the route was the problem. Anything below zero
# or unreadable is caught and falls back to the first subject, which is what
# this should do too.
#
# Left as xfail so the suite stays green and this reports XPASS the moment the
# app starts falling back.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="?subject= past the end of the subject list draws an empty screen "
    "instead of falling back to the first subject",
)
def test_a_subject_index_past_the_end_falls_back_to_the_first_subject(page):
    tracker = AbilityTrackerPage(page)
    subjects = tracker.open().json()["subjects"]

    tracker.open(subject=len(subjects) + 50, wait=False)

    expect(tracker.get_summary_name()).to_have_text(normalise(subjects[0]["title"]))
