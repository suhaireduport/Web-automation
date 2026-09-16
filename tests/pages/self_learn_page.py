"""Self Learn: the timer a student studies against, and the screen it is set on.

Daily Tasks "+" -> Self Learn opens the setup at /tasks/selfLearn: a study type
picked from a sheet drawn from studytype, a duration picked on a wheel of 5 to
90 minutes, a Keep Screen-On switch and a play button. Play routes to the timer
at /tasks/selfLearn/timer, and everything the timer needs travels in its query
string:

    totalTime   seconds the session is set for
    timeTaken   seconds already spent, when a task is being resumed
    taskId      the self-learn task being resumed, 0 for a new session
    studyType   the study type id
    studyTitle  its name, written under the clock

The timer counts down from totalTime - timeTaken the moment it opens. Closing it
saves the session through dailytasks/create-selflearn and goes back, and so
does leaving the page any other way, from a beforeunload handler. That save is
the only write on either screen.
"""
import re
from urllib.parse import urlencode

from pages.leaderboard_page import call_api
from pages.question_library_section_page import BASE_URL

# The wheel, in minutes, and where it starts.
DURATIONS = list(range(5, 95, 5))
DEFAULT_DURATION = 25

# How tall one row of the wheel is. The wheel picks the row its scroll position
# rounds to, so a duration is chosen by scrolling to its row.
PICKER_ROW = 80

SAVE_API = "**/api/v3/dailytasks/create-selflearn"
DAILY_TASKS_API = "**/api/v3/dailytasks/list**"

SAVED_TOAST = "Time updated successfully"
SAVE_FAILED_TOAST = "Something went wrong! Can't update time."
TIME_UP_TOAST = "Timeup"
ALREADY_DONE_TOAST = "The task is already done."

# The ring's gradient, running and paused.
RUNNING_COLOURS = ["#FB6514", "#D8257C"]
PAUSED_COLOURS = ["#ABABAB", "#ABABAB"]


def study_types(page):
    """The study types the setup sheet is drawn from, in its order."""
    return call_api(page, "/studytype")["results"]


def parse_clock(text):
    """"24:59" or "01:04:59" as seconds."""
    seconds = 0
    for part in text.strip().split(":"):
        seconds = seconds * 60 + int(part)
    return seconds


def timer_route(total, taken=0, task_id=0, study_type=1, study_title="Study"):
    """The timer as the setup screen or a Daily Tasks card routes to it."""
    query = urlencode(
        {
            "totalTime": total,
            "timeTaken": taken,
            "taskId": task_id,
            "studyType": study_type,
            "studyTitle": study_title,
        }
    )
    return f"{SelfLearnTimerPage.URL}?{query}"


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


# The clock read in the browser, so a reading and whatever is compared with it
# are taken in the same instant.
READ_CLOCK = (
    "() => { const clock = document.querySelector('.slt-time');"
    " return clock ? clock.textContent.trim().split(':')"
    ".reduce((seconds, part) => seconds * 60 + Number(part), 0) : null; }"
)


class SelfLearnPage:
    URL = f"{BASE_URL}/tasks/selfLearn"

    def __init__(self, page):
        self.page = page

    def open(self):
        self.page.goto(self.URL, wait_until="domcontentloaded")
        self.wait_for_loaded()

    def wait_for_loaded(self, timeout=30000):
        self.get_active_duration_item().wait_for(timeout=timeout)
        self.get_start_button().wait_for(timeout=timeout)

    def get_title(self):
        return self.page.locator(".sl-title")

    def get_back_button(self):
        """The header carries a second .sl-back as a spacer; the button is the
        one to press."""
        return self.page.locator("button.sl-back")

    # ---------- study type ----------

    def get_study_pill(self):
        return self.page.locator(".sl-study-pill")

    def get_study_name(self):
        return self.page.locator(".sl-study-text")

    def open_study_sheet(self):
        self.get_study_pill().click()
        self.get_study_sheet().wait_for()

    def get_study_sheet(self):
        return self.page.locator(".sl-sheet")

    def get_study_sheet_overlay(self):
        return self.page.locator(".sl-sheet-overlay")

    def get_study_sheet_title(self):
        return self.page.locator(".sl-sheet-title")

    def get_study_items(self):
        return self.page.locator(".sl-sheet-item")

    def get_study_item_titles(self):
        return [t.strip() for t in self.page.locator(".sl-sheet-item strong").all_inner_texts()]

    def get_active_study_item(self):
        return self.page.locator(".sl-sheet-item-active")

    def choose_study(self, title):
        """Pick a study type by name. Picking one is also what closes the sheet."""
        self.open_study_sheet()
        pattern = re.compile(r"^\s*" + re.escape(title) + r"\s*$")
        self.get_study_items().filter(
            has=self.page.locator("strong").filter(has_text=pattern)
        ).click()
        self.get_study_sheet().wait_for(state="detached")

    def close_study_sheet_outside(self):
        """The sheet sits at the foot of the overlay, so the tap is aimed at a
        corner of the overlay above it."""
        self.get_study_sheet_overlay().click(position={"x": 5, "y": 5})

    # ---------- duration ----------

    def get_duration_picker(self):
        return self.page.locator(".sl-picker")

    def get_duration_labels(self):
        return [t.strip() for t in self.page.locator(".sl-pick-item").all_inner_texts()]

    def get_active_duration_item(self):
        return self.page.locator(".sl-pick-active")

    def get_active_duration(self):
        return int(self.get_active_duration_item().inner_text().strip())

    def choose_duration(self, minutes):
        """Scroll the wheel to a duration's row and wait for the wheel to take
        it. Setting the scroll position fires the same scroll event a swipe
        does."""
        row = DURATIONS.index(minutes)
        self.get_duration_picker().evaluate(f"picker => {{ picker.scrollTop = {row * PICKER_ROW}; }}")
        self.page.wait_for_function(
            "wanted => document.querySelector('.sl-pick-active')?.textContent.trim() === wanted",
            arg=f"{minutes:02d}",
        )

    def get_minutes_label(self):
        return self.page.locator(".sl-min")

    # ---------- keep screen on ----------

    def get_keep_screen_on(self):
        return self.page.locator(".sl-wake")

    def get_keep_screen_on_indicator(self):
        """Present only while Keep screen on is switched on."""
        return self.page.locator(".sl-wake-on")

    def is_keep_screen_on(self):
        return self.page.locator(".sl-wake-text.sl-wake-on").count() > 0

    def toggle_keep_screen_on(self):
        self.get_keep_screen_on().click()

    # ---------- start ----------

    def get_start_button(self):
        return self.page.locator(".sl-play-fab")

    def start(self):
        self.get_start_button().click()


class SelfLearnTimerPage:
    URL = f"{BASE_URL}/tasks/selfLearn/timer"
    URL_PATTERN = re.compile(r"https://eduport-react\.pages\.dev/tasks/selfLearn/timer\?.+")

    def __init__(self, page):
        self.page = page

    def open(self, url):
        self.page.goto(url, wait_until="domcontentloaded")
        self.wait_for_loaded()

    def wait_for_loaded(self, timeout=30000):
        self.get_clock().wait_for(timeout=timeout)

    def get_title(self):
        return self.page.locator(".slt-title")

    def get_close_button(self):
        return self.page.locator(".slt-close")

    def close(self):
        self.get_close_button().click()

    def get_toast(self):
        """react-hot-toast renders every message into this one container, which
        is always in the DOM, so assert on its text rather than its presence."""
        return self.page.locator("[data-rht-toaster]")

    # ---------- the clock ----------

    def get_clock(self):
        return self.page.locator(".slt-time")

    def read_remaining(self):
        return self.page.evaluate(READ_CLOCK)

    def wait_for_remaining_at_most(self, seconds, timeout=15000):
        self.page.wait_for_function(
            "limit => { const clock = document.querySelector('.slt-time');"
            " if (!clock) return false;"
            " const left = clock.textContent.trim().split(':')"
            ".reduce((total, part) => total * 60 + Number(part), 0);"
            " return left <= limit; }",
            arg=seconds,
            timeout=timeout,
        )

    def get_end_time(self):
        """When the session will end if left running: "12:03 PM"."""
        return self.page.locator(".slt-endtime span")

    def read_end_times(self):
        """The end time on screen, and what it should read give or take two
        seconds, both worked out in the browser: {end, expected: [...]}."""
        return self.page.evaluate(END_TIMES)

    def get_study(self):
        return self.page.locator(".slt-study")

    # ---------- the ring ----------

    def get_ring(self):
        return self.page.locator(".slt-ring-svg circle")

    def ring_elapsed(self):
        """How far round the ring is drawn, as a fraction. The ring is one
        circle whose dash offset grows with the time spent."""
        whole, offset = self.get_ring().evaluate(
            "c => [c.getAttribute('stroke-dasharray'), c.getAttribute('stroke-dashoffset')]"
        )
        return float(offset) / float(whole)

    def ring_colours(self):
        return self.page.locator(".slt-ring-svg stop").evaluate_all(
            "stops => stops.map(stop => stop.getAttribute('stop-color'))"
        )

    # ---------- play, pause and restart ----------

    def get_play_pause_button(self):
        """One button, labelled for what it will do: Pause while running."""
        return self.page.locator(".slt-fab").first

    def is_running(self):
        return self.get_play_pause_button().get_attribute("aria-label") == "Pause"

    def tap_play_pause(self):
        self.get_play_pause_button().click()

    def pause(self):
        if self.is_running():
            self.tap_play_pause()
        self.page.locator(".slt-fab[aria-label='Play']").wait_for()

    def play(self):
        if not self.is_running():
            self.tap_play_pause()
        self.page.locator(".slt-fab[aria-label='Pause']").wait_for()

    def get_restart_button(self):
        return self.page.locator(".slt-fab[aria-label='Restart']")

    def restart(self):
        self.get_restart_button().click()

    # ---------- keep screen on ----------

    def get_keep_screen_on(self):
        return self.page.locator(".slt-wake")

    def get_keep_screen_on_indicator(self):
        """Present only while Keep screen on is switched on."""
        return self.page.locator(".slt-wake-on")

    def is_keep_screen_on(self):
        return self.page.locator(".slt-wake-text.slt-wake-on").count() > 0

    def toggle_keep_screen_on(self):
        self.get_keep_screen_on().click()
