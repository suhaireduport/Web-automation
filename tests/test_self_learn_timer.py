"""The Self Learn timer, and the setup screen it is started from.

The setup is checked against studytype, the call its sheet is drawn from, and
the timer against the query string it is opened with, which is everything it
knows. Closing the timer saves the session, and that save is checked by the
request it makes: every call to dailytasks/create-selflearn in this module is
answered here instead of by the backend.

That is on purpose rather than for speed. A saved session puts a Self Learn
card on the account's Daily Tasks for today, and test_course_switch.py counts
the cards on that screen against the study, practice, revision and exam tasks
alone, so a real save would break it. Leaving the timer any other way saves
too, from a beforeunload handler, so the interception is installed for every
test here, not only the ones that close the timer.

For the same reason, the Self Learn card on Daily Tasks is checked against a
task added to the list call's response here, not against one the account holds.
"""
import datetime
import re
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import expect

from conftest import HOME_URL, STUDENT_MOBILE
from pages.daily_tasks_page import DailyTasksPage
from pages.self_learn_page import (
    ALREADY_DONE_TOAST,
    DAILY_TASKS_API,
    DEFAULT_DURATION,
    DURATIONS,
    PAUSED_COLOURS,
    RUNNING_COLOURS,
    SAVE_API,
    SAVE_FAILED_TOAST,
    SAVED_TOAST,
    TIME_UP_TOAST,
    SelfLearnPage,
    SelfLearnTimerPage,
    parse_clock,
    study_types,
    timer_route,
)

SELF_LEARN_GROUP = "Self Learn"

# The id given to the task added to Daily Tasks. Nothing is saved against it:
# the save it would make is answered here like every other.
SERVED_TASK_ID = 990001

# The browser works out when a session ends from its own clock, so the reading
# on screen is held against the same working-out done in the browser, a moment
# either side, rather than against the machine running the test.
END_TIMES = """() => {
    const clock = document.querySelector('.slt-time').textContent.trim();
    const end = document.querySelector('.slt-endtime span').textContent.trim();
    const left = clock.split(':').reduce((seconds, part) => seconds * 60 + Number(part), 0);
    const at = offset => {
        const when = new Date(Date.now() + (left + offset) * 1000);
        const minutes = String(when.getMinutes()).padStart(2, '0');
        const half = when.getHours() >= 12 ? 'PM' : 'AM';
        const hours = String(when.getHours() % 12 || 12).padStart(2, '0');
        return `${hours}:${minutes} ${half}`;
    };
    return {end, expected: [at(-2), at(0), at(2)]};
}"""


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(STUDENT_MOBILE)


@pytest.fixture(autouse=True)
def saves(page):
    """Every session save the page makes, answered here instead of by the
    backend, and kept for a test to read."""
    held = []

    def hold(route):
        held.append(route.request.post_data_json)
        route.fulfill(status=200, json={"id": 0})

    page.route(SAVE_API, hold)
    return held


def query_of(url):
    return {key: values[0] for key, values in parse_qs(urlparse(url).query).items()}


def wait_for_saves(page, saves, count=1, timeout_ms=5000):
    """A save fired on the way out of a page lands a moment after the page
    has gone, so it is waited for rather than read straight away."""
    waited = 0
    while len(saves) < count and waited < timeout_ms:
        page.wait_for_timeout(250)
        waited += 250


@pytest.fixture
def setup(page):
    self_learn = SelfLearnPage(page)
    self_learn.open()
    return self_learn


@pytest.fixture
def timer(page, setup):
    """Started from the setup as it opens: the first study type, 25 minutes."""
    setup.start()
    expect(page).to_have_url(SelfLearnTimerPage.URL_PATTERN)
    timer = SelfLearnTimerPage(page)
    timer.wait_for_loaded()
    return timer


def open_timer(page, **route):
    timer = SelfLearnTimerPage(page)
    timer.open(timer_route(**route))
    return timer


# ---------------------------------------------------------------------------
# 1. The setup
# ---------------------------------------------------------------------------


def test_the_self_learn_tile_on_daily_tasks_opens_the_setup(page):
    page.goto(DailyTasksPage.URL, wait_until="domcontentloaded")
    tasks = DailyTasksPage(page)
    tasks.wait_for_tasks_loaded()
    tasks.click_fab()

    tasks.get_self_learn_card().click()

    expect(page).to_have_url(SelfLearnPage.URL)
    self_learn = SelfLearnPage(page)
    self_learn.wait_for_loaded()
    expect(self_learn.get_title()).to_have_text("Timer")
    expect(self_learn.get_start_button()).to_be_visible()


def test_the_setup_opens_on_25_minutes_of_the_first_study_type(page, setup):
    first = study_types(page)[0]

    expect(setup.get_study_name()).to_have_text(first["title"])
    assert setup.get_active_duration() == DEFAULT_DURATION
    expect(setup.get_minutes_label()).to_have_text("min")


def test_the_durations_run_from_5_to_90_minutes_in_fives(setup):
    assert setup.get_duration_labels() == [f"{minutes:02d}" for minutes in DURATIONS]


def test_the_study_sheet_lists_the_study_types_the_api_serves(page, setup):
    served = study_types(page)

    setup.open_study_sheet()

    expect(setup.get_study_sheet_title()).to_have_text("Tasks")
    assert setup.get_study_item_titles() == [one["title"].strip() for one in served]
    expect(setup.get_active_study_item()).to_contain_text(served[0]["title"])


def test_choosing_a_study_type_puts_it_on_the_pill(page, setup):
    served = study_types(page)
    if len(served) < 2:
        pytest.skip("There is only one study type to choose")

    setup.choose_study(served[1]["title"])

    expect(setup.get_study_name()).to_have_text(served[1]["title"])
    expect(setup.get_study_sheet()).to_have_count(0)


def test_tapping_outside_the_study_sheet_closes_it(setup):
    setup.open_study_sheet()

    setup.close_study_sheet_outside()

    expect(setup.get_study_sheet_overlay()).to_have_count(0)


@pytest.mark.parametrize("minutes", [DURATIONS[0], 10, DURATIONS[-1]])
def test_turning_the_wheel_picks_the_duration(setup, minutes):
    setup.choose_duration(minutes)

    assert setup.get_active_duration() == minutes


def test_keep_screen_on_turns_over_on_the_setup(setup):
    assert setup.is_keep_screen_on() is False

    setup.toggle_keep_screen_on()
    expect(setup.page.locator(".sl-wake-on")).to_have_count(1)

    setup.toggle_keep_screen_on()
    expect(setup.page.locator(".sl-wake-on")).to_have_count(0)


def test_play_opens_the_timer_for_the_chosen_duration_and_study(page, setup):
    served = study_types(page)
    chosen = served[1] if len(served) > 1 else served[0]
    setup.choose_study(chosen["title"])
    setup.choose_duration(10)

    setup.start()

    expect(page).to_have_url(SelfLearnTimerPage.URL_PATTERN)
    assert query_of(page.url) == {
        "totalTime": "600",
        "timeTaken": "0",
        "taskId": "0",
        "studyType": str(chosen["id"]),
        "studyTitle": chosen["title"],
    }


# ---------------------------------------------------------------------------
# 2. The timer running
# ---------------------------------------------------------------------------


def test_the_timer_counts_down_from_the_duration_it_was_set_for(page, timer):
    total = DEFAULT_DURATION * 60
    expect(timer.get_title()).to_have_text("Timer")

    first = timer.read_remaining()
    assert total - 3 <= first <= total

    page.wait_for_timeout(2500)
    assert timer.read_remaining() < first
    assert timer.is_running() is True


def test_the_timer_names_the_study_it_is_timing(page, timer):
    expect(timer.get_study()).to_have_text(study_types(page)[0]["title"])


def test_the_end_time_is_now_plus_what_is_left(timer):
    reading = timer.page.evaluate(END_TIMES)

    assert reading["end"] in reading["expected"], reading


def test_the_ring_is_drawn_in_colour_while_running(timer):
    assert timer.ring_colours() == RUNNING_COLOURS


def test_the_ring_fills_with_the_time_spent(timer):
    total = DEFAULT_DURATION * 60
    timer.wait_for_remaining_at_most(total - 3)
    timer.pause()

    spent = total - timer.read_remaining()

    assert timer.ring_elapsed() == pytest.approx(spent / total, abs=0.002)


def test_a_timer_of_an_hour_or_more_reads_hours_minutes_and_seconds(page):
    timer = open_timer(page, total=4000, taken=100)

    expect(timer.get_clock()).to_have_text(re.compile(r"^\d{2}:\d{2}:\d{2}$"))
    assert 3895 <= parse_clock(timer.get_clock().inner_text()) <= 3900


def test_a_resumed_session_counts_down_only_what_is_left(page):
    timer = open_timer(page, total=600, taken=240)

    assert 356 <= timer.read_remaining() <= 360


def test_keep_screen_on_turns_over_on_the_timer(timer):
    assert timer.is_keep_screen_on() is False

    timer.toggle_keep_screen_on()
    expect(timer.page.locator(".slt-wake-on")).to_have_count(1)

    timer.toggle_keep_screen_on()
    expect(timer.page.locator(".slt-wake-on")).to_have_count(0)


# ---------------------------------------------------------------------------
# 3. Pause, play and restart
# ---------------------------------------------------------------------------


def test_pausing_holds_the_clock_and_greys_the_ring(page, timer):
    timer.pause()
    page.wait_for_timeout(300)
    held = timer.read_remaining()

    page.wait_for_timeout(2500)

    assert timer.read_remaining() == held
    expect(timer.get_play_pause_button()).to_have_attribute("aria-label", "Play")
    assert timer.ring_colours() == PAUSED_COLOURS


def test_play_carries_on_from_where_it_was_paused(page, timer):
    timer.pause()
    page.wait_for_timeout(300)
    held = timer.read_remaining()

    timer.play()
    timer.wait_for_remaining_at_most(held - 1)

    assert held - 3 <= timer.read_remaining() < held
    assert timer.ring_colours() == RUNNING_COLOURS


def test_restart_puts_the_whole_duration_back_and_waits(page, timer):
    total = DEFAULT_DURATION * 60
    timer.wait_for_remaining_at_most(total - 2)

    timer.restart()

    expect(timer.get_clock()).to_have_text(f"{DEFAULT_DURATION}:00")
    expect(timer.get_play_pause_button()).to_have_attribute("aria-label", "Play")
    assert timer.ring_elapsed() == 0

    page.wait_for_timeout(2000)
    expect(timer.get_clock()).to_have_text(f"{DEFAULT_DURATION}:00")


def test_restart_on_a_resumed_session_goes_back_to_what_was_left(page):
    timer = open_timer(page, total=600, taken=240)
    timer.wait_for_remaining_at_most(358)

    timer.restart()

    expect(timer.get_clock()).to_have_text("06:00")


# ---------------------------------------------------------------------------
# 4. Running out
# ---------------------------------------------------------------------------


def test_a_session_that_runs_out_stops_at_zero(page):
    timer = open_timer(page, total=3)

    expect(timer.get_clock()).to_have_text("00:00", timeout=10000)
    expect(timer.get_play_pause_button()).to_have_attribute("aria-label", "Play")

    page.wait_for_timeout(1500)
    expect(timer.get_clock()).to_have_text("00:00")
    assert timer.ring_elapsed() == pytest.approx(1)


def test_play_once_the_time_is_up_says_so(page):
    timer = open_timer(page, total=2)
    expect(timer.get_clock()).to_have_text("00:00", timeout=10000)

    timer.tap_play_pause()

    expect(timer.get_toast()).to_contain_text(TIME_UP_TOAST)
    expect(timer.get_clock()).to_have_text("00:00")


# ---------------------------------------------------------------------------
# 5. Saving the session
# ---------------------------------------------------------------------------


def test_closing_saves_the_time_spent_and_goes_back(page, timer, saves):
    total = DEFAULT_DURATION * 60
    timer.wait_for_remaining_at_most(total - 2)
    timer.pause()
    page.wait_for_timeout(300)
    spent = total - timer.read_remaining()

    timer.close()

    expect(timer.get_toast()).to_contain_text(SAVED_TOAST)
    expect(page).to_have_url(SelfLearnPage.URL)
    assert saves == [
        {
            "study_type": study_types(page)[0]["id"],
            "time_taken": spent,
            "total_study_time": total,
        }
    ]


def test_closing_while_running_saves_up_to_the_moment_of_closing(page, timer, saves):
    total = DEFAULT_DURATION * 60
    timer.wait_for_remaining_at_most(total - 2)
    left_before = timer.read_remaining()

    timer.close()

    expect(page).to_have_url(SelfLearnPage.URL)
    assert len(saves) == 1, saves
    assert total - left_before <= saves[0]["time_taken"] <= total - left_before + 2


def test_a_resumed_task_is_saved_against_that_task(page, saves):
    """The time saved is the whole of what the task has been given - what it
    came in with and what was added - and it is saved against the task."""
    timer = open_timer(page, total=600, taken=240, task_id=SERVED_TASK_ID, study_type=2, study_title="Home Work")
    timer.wait_for_remaining_at_most(358)
    timer.pause()
    page.wait_for_timeout(300)
    left = timer.read_remaining()

    timer.close()

    # This timer was opened by a page load from Home, so going back after the
    # save is a page load too, and the toast goes with the page it was shown
    # on. Arriving back on Home is what says the save came back.
    expect(page).to_have_url(HOME_URL)
    assert saves == [
        {
            "study_type": 2,
            "time_taken": 600 - left,
            "total_study_time": 600,
            "task_id": SERVED_TASK_ID,
        }
    ]


def test_leaving_the_timer_without_closing_it_still_saves(page, timer, saves):
    timer.wait_for_remaining_at_most(DEFAULT_DURATION * 60 - 1)

    page.goto(HOME_URL, wait_until="domcontentloaded")
    wait_for_saves(page, saves)

    assert len(saves) == 1, saves
    assert saves[0]["total_study_time"] == DEFAULT_DURATION * 60
    assert 0 < saves[0]["time_taken"] <= DEFAULT_DURATION * 60


def test_closing_saves_once_even_though_the_page_is_left_after(page, timer, saves):
    """Close marks the session saved before it goes, so the beforeunload
    handler has nothing left to send when the page is left afterwards."""
    timer.close()
    expect(page).to_have_url(SelfLearnPage.URL)

    page.goto(HOME_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)

    assert len(saves) == 1, saves


def test_a_save_that_fails_says_so_and_still_leaves(page, timer):
    page.unroute(SAVE_API)
    page.route(SAVE_API, lambda route: route.fulfill(status=500, json={"message": "server error"}))

    timer.close()

    expect(timer.get_toast()).to_contain_text(SAVE_FAILED_TOAST)
    expect(page).to_have_url(SelfLearnPage.URL)


# ---------------------------------------------------------------------------
# 6. A Self Learn task on Daily Tasks
# ---------------------------------------------------------------------------


def serve_self_learn_task(page, taken, total, study):
    """Put a self-learn task on today's Daily Tasks by adding it to the list
    call's response, and hand the task back."""
    today = datetime.date.today().isoformat()
    task = {
        "id": SERVED_TASK_ID,
        "date": today,
        "study_title": study["title"],
        "study_type": study["id"],
        "time_taken": taken,
        "total_study_time": total,
    }

    def add(route):
        response = route.fetch()
        body = response.json()
        for day in body.get("results", []):
            if day.get("date") == today:
                day["selflearn_tasks"] = [task]
        route.fulfill(response=response, json=body)

    page.route(DAILY_TASKS_API, add)
    return task


def open_daily_tasks_with_the_task(page, taken, total):
    study = study_types(page)[-1]
    task = serve_self_learn_task(page, taken, total, study)
    page.goto(DailyTasksPage.URL, wait_until="domcontentloaded")
    tasks = DailyTasksPage(page)
    tasks.wait_for_tasks_loaded()
    if tasks.task_card_count(SELF_LEARN_GROUP) == 0:
        pytest.skip("Today is not the day Daily Tasks opens on, so the task is not shown")
    return tasks, task


@pytest.mark.parametrize(
    "taken, shown",
    [(240, "4 Minutes"), (60, "1 Minutes"), (45, "45 Seconds"), (5, "05 Seconds")],
)
def test_a_self_learn_card_shows_the_time_already_spent(page, taken, shown):
    tasks, task = open_daily_tasks_with_the_task(page, taken=taken, total=600)

    expect(tasks.get_task_card_title(0, SELF_LEARN_GROUP)).to_have_text(task["study_title"])
    expect(tasks.get_task_card_sub(0, SELF_LEARN_GROUP)).to_have_text(shown)


def test_a_self_learn_card_resumes_the_timer_where_it_was_left(page, saves):
    tasks, task = open_daily_tasks_with_the_task(page, taken=240, total=600)

    tasks.click_task_card(0, SELF_LEARN_GROUP)

    expect(page).to_have_url(SelfLearnTimerPage.URL_PATTERN)
    carried = query_of(page.url)
    assert {key: carried.get(key) for key in ("totalTime", "timeTaken", "taskId", "studyType", "studyTitle")} == {
        "totalTime": "600",
        "timeTaken": "240",
        "taskId": str(task["id"]),
        "studyType": str(task["study_type"]),
        "studyTitle": task["study_title"],
    }

    timer = SelfLearnTimerPage(page)
    timer.wait_for_loaded()
    assert 356 <= timer.read_remaining() <= 360
    expect(timer.get_study()).to_have_text(task["study_title"])


def test_a_finished_self_learn_card_does_not_reopen(page):
    tasks, _ = open_daily_tasks_with_the_task(page, taken=600, total=600)

    tasks.click_task_card(0, SELF_LEARN_GROUP)

    expect(page.locator("[data-rht-toaster]")).to_contain_text(ALREADY_DONE_TOAST)
    expect(page).to_have_url(DailyTasksPage.URL)
