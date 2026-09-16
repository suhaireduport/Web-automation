"""The Daily Effort Tracker: time spent, read a day and a week at a time.

The entry is the More button on the Daily Effort Tracker card on Analysis, and
one call draws everything behind it - analytics/effort/list, asked for a date
and a span:

    Day tab    date=<the day being shown>  range=1
    Week tab   date=<today>                range=7

It answers a list of days, each carrying an effort_index and the seconds spent
under study, practice, revision and exams. The Day tab draws its gauge from
that one day's index and its ring from that day's seconds. The Week tab draws a
bar per day and puts the seconds of all seven through the same ring.

Two things are read off the screen rather than written down here. Revision is
behind a remote config flag, and where it is off it leaves both the legend and
the total, so the total is only ever added up over the rows the legend is
actually showing. And nothing about the numbers themselves is fixed: the
student studies while the suite runs, so every figure is compared against what
the call answered at the moment it was read.

What is deliberately not here: the effort card on Analysis - the gauge, the
quote, the two slides and the More button going where it says - stays in
test_analytics.py. What is here is the screen behind it.

There is no subject-wise effort. The call carries no subject dimension and the
screen offers no subject strip, tabs or filter; the way it divides effort up is
by day and by activity. test_the_effort_tracker_is_not_divided_by_subject
holds that down so a later subject breakdown cannot arrive unnoticed.
"""
import datetime
import math
import re

import pytest
from playwright.sync_api import expect

from conftest import STUDENT_MOBILE
from pages.analytics_page import AnalyticsPage
from pages.effort_tracker_page import (
    DAY_TAB,
    EFFORT_API,
    EffortTrackerPage,
    GRID_LABELS,
    LEGEND_FIELDS,
    WEEK_TAB,
    bar_reading,
    format_secs,
    gauge_reading,
    to_api_date,
    total_seconds,
)
from pages.home_page import HomePage
from pages.leaderboard_page import call_api

ANALYTICS_URL = "https://eduport-react.pages.dev/analytics"

# How far back the day arrows go. The sixth step back is the last one the
# Previous arrow will take.
OLDEST_DAY = -6

# The dial is a half circle of this radius, so a full sweep is pi times it.
GAUGE_RADIUS = 100

# A time as the ring and the legend write it: 29s, 3m 9s, 5m, 1h 4m.
TIME_READING = re.compile(r"^\d+s$|^\d+m(\s\d+s)?$|^\d+h\s\d+m$")

# The legend either carries revision or it does not, depending on the remote
# config the app was served. Nothing else about it moves.
LEGEND_SHAPES = [
    ["Study", "Practice", "Exams"],
    ["Study", "Practice", "Revision", "Exams"],
]


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(STUDENT_MOBILE)


@pytest.fixture
def effort(page):
    """The tracker open on the Day tab, which is where it starts."""
    tracker = EffortTrackerPage(page)
    tracker.open()
    return tracker


@pytest.fixture
def analytics(page):
    """Analysis, the screen the tracker is opened from."""
    home = HomePage(page)
    home.get_analysis_button().click()
    page.wait_for_url(ANALYTICS_URL)
    screen = AnalyticsPage(page)
    screen.wait_for_analytics_loaded()
    return screen


def effort_for(page, day, span):
    """The call the screen would make for a day and a span, made again.

    Read through the app's own token rather than listened for, so a comparison
    can be taken at the moment the screen is read instead of only at the
    moment it was opened."""
    return call_api(page, f"/analytics/effort/list?date={to_api_date(day)}&range={span}")


def day_label(day, today):
    """What the date strip calls a day."""
    if day == today:
        return "Today"
    if day == today - datetime.timedelta(days=1):
        return "Yesterday"
    return f"{day:%b} {day.day}, {day.year}"


# ---------------------------------------------------------------------------
# Opening it, and what is on the screen
# ---------------------------------------------------------------------------

def test_the_tracker_opens_from_the_effort_card_on_analysis(page, analytics):
    """The card's More button is the way in, and it lands on a built screen
    rather than only on the route."""
    analytics.click_effort_more()

    expect(page).to_have_url(EffortTrackerPage.URL)
    tracker = EffortTrackerPage(page)
    tracker.wait_for_loaded()
    expect(tracker.get_title()).to_have_text("Effort Tracker")


def test_the_header_carries_a_way_back_and_a_way_to_the_help(effort):
    expect(effort.get_back_button()).to_be_visible()
    expect(effort.get_title()).to_have_text("Effort Tracker")
    expect(effort.get_info_button()).to_be_visible()


def test_day_and_week_are_the_two_tabs_and_it_opens_on_day(effort):
    expect(effort.get_tabs()).to_have_count(2)
    assert effort.get_tab_names() == [DAY_TAB, WEEK_TAB]
    expect(effort.get_active_tab()).to_have_count(1)
    expect(effort.get_active_tab()).to_have_text(DAY_TAB)


def test_the_day_view_shows_a_gauge_and_a_time_ring(effort):
    expect(effort.get_gauge()).to_be_visible()
    expect(effort.get_gauge_caption()).to_have_text("Effort index")
    assert 0 <= effort.get_gauge_value() <= 100

    expect(effort.get_ring()).to_be_visible()
    expect(effort.get_total_caption()).to_have_text("Total time spend")
    assert TIME_READING.match(effort.get_total_time())


def test_the_legend_names_the_kinds_of_effort_the_ring_is_made_of(effort):
    """Study, practice and exams always; revision only where it is switched
    on. Nothing else is ever a row."""
    names = effort.get_legend_names()

    assert names in LEGEND_SHAPES, f"the legend read {names}"
    expect(effort.get_legend_items()).to_have_count(len(names))
    for name, value in effort.get_legend().items():
        assert TIME_READING.match(value), f"{name} read {value!r}"


def test_the_day_being_shown_walks_back_a_week_and_stops(page, effort):
    """Today at the front with nowhere forward to go, a week of steps back,
    and the arrow gives out at the seventh day."""
    today = datetime.date.today()

    expect(effort.get_date_label()).to_have_text("Today")
    expect(effort.get_next_day_button()).to_be_disabled()
    expect(effort.get_previous_day_button()).to_be_enabled()

    for step in range(1, -OLDEST_DAY + 1):
        effort.click_previous_day()
        expect(effort.get_date_label()).to_have_text(
            day_label(today - datetime.timedelta(days=step), today)
        )
        expect(effort.get_next_day_button()).to_be_enabled()

    expect(effort.get_previous_day_button()).to_be_disabled()


def test_the_week_view_shows_the_effort_index_bar_chart(page, effort):
    effort.show_week()

    expect(effort.get_barchart()).to_be_visible()
    expect(effort.get_barchart_title()).to_have_text("Effort index")
    assert effort.get_grid_labels() == GRID_LABELS
    assert effort.get_bar_labels()[-1] == "Today"
    expect(effort.get_ring()).to_be_visible()


def test_the_week_view_puts_the_day_controls_away(effort):
    """A week is not a day, so the gauge and the date strip go."""
    expect(effort.get_date_nav()).to_be_visible()

    effort.click_tab(WEEK_TAB)

    expect(effort.get_date_nav()).to_have_count(0)
    expect(effort.get_gauge()).to_have_count(0)
    expect(effort.get_active_tab()).to_have_text(WEEK_TAB)


def test_the_help_sheet_explains_this_tracker_and_only_this_one(effort):
    """Analysis explains all three trackers at once; a tracker's own sheet
    explains itself."""
    effort.click_info_button()

    expect(effort.get_info_sheet()).to_be_visible()
    expect(effort.get_info_sheet_title()).to_have_text("How effort tracker works?")
    expect(effort.get_info_sections()).to_have_count(1)
    expect(effort.get_info_headings()).to_have_text(["Effort Tracker"])
    expect(effort.get_info_bodies()).not_to_be_empty()

    effort.close_info_sheet()
    expect(effort.get_info_sheet()).to_have_count(0)


def test_back_returns_to_the_screen_it_was_opened_from(page, analytics):
    analytics.click_effort_more()
    tracker = EffortTrackerPage(page)
    tracker.wait_for_loaded()

    tracker.click_back()

    expect(page).to_have_url(ANALYTICS_URL)


# ---------------------------------------------------------------------------
# The overall reading, against the call it is drawn from
# ---------------------------------------------------------------------------

def test_opening_the_tracker_asks_for_one_day_and_shows_what_came_back(page):
    """The gauge, the ring and every legend row read against the one entry the
    Day tab was answered with."""
    tracker = EffortTrackerPage(page)
    with page.expect_response(EFFORT_API) as answer:
        page.goto(EffortTrackerPage.URL, wait_until="domcontentloaded")
    tracker.wait_for_loaded()

    assert answer.value.status == 200, f"effort answered {answer.value.status}"
    assert "range=1" in answer.value.url, answer.value.url
    assert f"date={to_api_date(datetime.date.today())}" in answer.value.url, answer.value.url

    entries = answer.value.json()
    assert len(entries) == 1, f"one day was asked for and {len(entries)} came back"
    entry = entries[0]

    expect(tracker.get_gauge_texts().first).to_have_text(
        str(gauge_reading(entry["effort_index"]))
    )
    expect(tracker.get_legend_values_locator()).to_have_text(
        [format_secs(entry[LEGEND_FIELDS[name]]) for name in tracker.get_legend_names()]
    )
    expect(tracker.get_ring_texts().first).to_have_text(
        format_secs(total_seconds(entry, tracker.shown_fields()))
    )


def test_walking_back_a_day_asks_for_that_day_and_shows_that_day(page, effort):
    """Each step back is a call of its own, and the screen redraws from it."""
    yesterday = datetime.date.today() - datetime.timedelta(days=1)

    with page.expect_response(EFFORT_API) as answer:
        effort.click_previous_day()
    expect(effort.get_date_label()).to_have_text("Yesterday")

    assert answer.value.status == 200, f"effort answered {answer.value.status}"
    assert f"date={to_api_date(yesterday)}" in answer.value.url, answer.value.url
    assert "range=1" in answer.value.url, answer.value.url

    entry = answer.value.json()[0]
    assert entry["date"] == f"{yesterday:%Y-%m-%d}"
    expect(effort.get_gauge_texts().first).to_have_text(
        str(gauge_reading(entry["effort_index"]))
    )
    expect(effort.get_ring_texts().first).to_have_text(
        format_secs(total_seconds(entry, effort.shown_fields()))
    )


def test_the_week_bars_are_the_seven_days_the_call_answered(page, effort):
    """A bar per day, oldest to newest, each written with its own index cut
    down to a whole number, and only the days with effort are drawn."""
    answer = effort.show_week()

    assert answer.status == 200, f"effort answered {answer.status}"
    assert "range=7" in answer.url, answer.url

    entries = sorted(answer.json(), key=lambda entry: entry["date"])
    expect(effort.get_bar_values_locator()).to_have_text(
        [str(bar_reading(entry["effort_index"])) for entry in entries]
    )
    expect(effort.get_bars()).to_have_count(
        sum(1 for entry in entries if bar_reading(entry["effort_index"]) > 0)
    )


def test_the_week_ring_adds_up_the_whole_week(page, effort):
    """The Day ring is one day; the Week ring is the same rows added over
    every day that came back."""
    entries = effort.show_week().json()
    fields = effort.shown_fields()

    expect(effort.get_legend_values_locator()).to_have_text(
        [
            format_secs(sum(entry[LEGEND_FIELDS[name]] for entry in entries))
            for name in effort.get_legend_names()
        ]
    )
    expect(effort.get_ring_texts().first).to_have_text(
        format_secs(sum(total_seconds(entry, fields) for entry in entries))
    )


def test_the_effort_call_answers_one_entry_a_day_over_the_span_asked_for(page):
    """Read against the call rather than the screen: seven days back from
    today, one entry each, nothing missing and nothing counted twice."""
    today = datetime.date.today()
    entries = effort_for(page, today, 7)

    assert len(entries) == 7, f"seven days were asked for and {len(entries)} came back"
    assert sorted(entry["date"] for entry in entries) == sorted(
        f"{today - datetime.timedelta(days=step):%Y-%m-%d}" for step in range(7)
    )

    for entry in entries:
        assert 0 <= entry["effort_index"] <= 100, entry
        for field in LEGEND_FIELDS.values():
            assert entry[field] >= 0, entry


# ---------------------------------------------------------------------------
# What the screen says on its own
# ---------------------------------------------------------------------------

def test_the_gauge_is_drawn_to_the_index_it_writes(effort):
    """The dial against the number in the middle of it, without going near the
    call - the screen has to agree with itself.

    Read off the arc rather than compared to a reading taken again afterwards:
    the student is studying while the suite runs, so a second reading of the
    call is not necessarily the reading the dial was drawn from."""
    filled, whole = effort.get_gauge_arc()

    assert whole == pytest.approx(math.pi * GAUGE_RADIUS, abs=0.01)
    # The number under the dial is rounded and the arc is not, so the two
    # agree to within half a percent rather than exactly.
    assert filled / whole == pytest.approx(effort.get_gauge_value() / 100, abs=0.005)


def test_the_effort_tracker_is_not_divided_by_subject(page, effort):
    """Effort is divided by day and by activity, never by subject.

    Both halves are held down: the screen offers no subject strip, tabs or
    filter to pick one with, and the call carries no subject to pick. A
    subject breakdown arriving later should fail here and be given tests of
    its own."""
    for subject_control in effort.get_subject_controls():
        expect(subject_control).to_have_count(0)

    entry = effort_for(page, datetime.date.today(), 1)[0]
    assert set(entry) == {"date", "effort_index"} | set(LEGEND_FIELDS.values()), entry
