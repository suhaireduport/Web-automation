"""The Effort Tracker screen behind the Daily Effort Tracker card on Analysis.

One call draws the whole screen, analytics/effort/list, and it is asked for a
date and a span of days:

    day tab    date=<the day being shown>  range=1   one entry back
    week tab   date=<today>                range=7   seven entries back

An entry is a day: its effort_index and the seconds spent under study,
practice, revision and exams. The day tab draws the gauge from that one entry
and the ring from its seconds; the week tab draws a bar per entry and adds the
seconds of all seven into the same ring.

Revision is behind a remote config flag. Where it is off the ring leaves it out
of both the legend and the total, so what the legend carries has to be read
rather than assumed - LEGEND_FIELDS says which API field each row is drawn
from.
"""

import math

URL = "https://eduport-react.pages.dev/analysis/effort-tracker"

# The call the screen is drawn from, as a route pattern for expect_response.
EFFORT_API = "**/api/v3/analytics/effort/list?*"

# The seconds field behind each row of the ring legend, in the order the ring
# lays them out. Revision only appears when the remote config allows it.
LEGEND_FIELDS = {
    "Study": "study_time_in_seconds",
    "Practice": "practice_time_in_seconds",
    "Revision": "revision_time_in_seconds",
    "Exams": "exam_time_in_seconds",
}

# The bar chart's y axis, top down.
GRID_LABELS = ["100", "80", "60", "40", "20", "0"]

DAY_TAB = "Day"
WEEK_TAB = "Week"


def format_secs(seconds):
    """Seconds as the screen writes them: 29s, 3m 9s, 5m, 1h 4m.

    The app's own rule, mirrored so an API reading can be compared with what
    the ring and the legend show. Whole minutes drop the seconds; once it runs
    to hours the seconds go entirely."""
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s" if secs else f"{minutes}m"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m"


def gauge_reading(effort_index):
    """The number the gauge writes for an effort index.

    Clamped to the dial and then rounded the way the app rounds rather than
    the way Python does: a half goes up, where Python would send it to the
    nearest even."""
    return math.floor(min(100.0, max(0.0, effort_index)) + 0.5)


def bar_reading(effort_index):
    """The number written over a bar on the week chart. Cut down rather than
    rounded, which is the app's own doing."""
    return math.floor(effort_index)


def to_api_date(day):
    """A date as the app puts it in the query string: 2026-9-4, unpadded."""
    return f"{day.year}-{day.month}-{day.day}"


def total_seconds(entry, fields):
    """What the ring adds up over one entry, counting only the fields the
    legend is showing."""
    return sum(entry.get(field, 0) for field in fields)


class EffortTrackerPage:
    URL = URL

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def open(self):
        """Open the screen and hand back the answer it drew itself from.

        The gauge and the ring are both drawn at zero before the call comes
        back, and zero is a real reading, so there is nothing on the screen
        that says the numbers have arrived. The call itself is what is waited
        for."""
        with self.page.expect_response(EFFORT_API) as answer:
            self.page.goto(self.URL, wait_until="domcontentloaded")
        self.wait_for_loaded()
        return answer.value

    def wait_for_loaded(self, timeout=30000):
        """The ring is on both tabs, so it is what says the screen is up."""
        self.get_ring().wait_for(timeout=timeout)

    def show_week(self):
        """Move to the Week tab and hand back the answer it drew itself from.

        The chart puts its grid up before there is anything to plot, so the
        tab being active is not enough to read bars off it."""
        with self.page.expect_response(EFFORT_API) as answer:
            self.click_tab(WEEK_TAB)
        self.wait_for_bars()
        return answer.value

    def wait_for_bars(self, timeout=30000):
        self.get_bar_labels_locator().first.wait_for(timeout=timeout)

    def get_page(self):
        return self.page.locator(".et-page")

    # ---------- header ----------

    def get_title(self):
        return self.page.locator(".et-title")

    def get_back_button(self):
        return self.page.locator(".et-back")

    def click_back(self):
        self.get_back_button().click()

    def get_info_button(self):
        return self.page.get_by_role("button", name="How effort tracker works")

    def click_info_button(self):
        self.get_info_button().click()

    # ---------- day / week tabs ----------

    def get_tabs(self):
        return self.page.locator(".et-tab")

    def get_tab_names(self):
        return [name.strip() for name in self.get_tabs().all_inner_texts()]

    def get_active_tab(self):
        return self.page.locator(".et-tab-active")

    def click_tab(self, name):
        self.get_tabs().filter(has_text=name).click()

    # ---------- the day being shown ----------

    def get_date_nav(self):
        return self.page.locator(".et-date-nav")

    def get_date_label(self):
        return self.page.locator(".et-date-label")

    def get_previous_day_button(self):
        return self.page.get_by_role("button", name="Previous day")

    def get_next_day_button(self):
        return self.page.get_by_role("button", name="Next day")

    def click_previous_day(self):
        self.get_previous_day_button().click()

    def click_next_day(self):
        self.get_next_day_button().click()

    # ---------- the gauge ----------

    def get_gauge(self):
        return self.page.locator(".et-gauge-svg")

    def get_gauge_texts(self):
        """The two words in the gauge: the index, then what it is called."""
        return self.get_gauge().locator("text")

    def get_gauge_value(self):
        # SVG text is not an HTML element, so it is read through textContent
        # rather than innerText.
        return int(self.get_gauge_texts().first.text_content().strip())

    def get_gauge_caption(self):
        return self.get_gauge_texts().last

    def get_gauge_arc(self):
        """How much of the dial is filled in, as (filled, whole).

        The gauge is one arc laid over another and the dash pattern on the top
        one is what makes it stop where it does. Read from the arc rather than
        from the number written under it, which is rounded."""
        pattern = (
            self.get_gauge()
            .locator('path[stroke="url(#etGaugeFill)"]')
            .get_attribute("stroke-dasharray")
        )
        filled, whole = pattern.split()
        return float(filled), float(whole)

    # ---------- the time ring ----------

    def get_ring(self):
        return self.page.locator(".et-ring-svg")

    def get_ring_texts(self):
        return self.get_ring().locator("text")

    def get_total_time(self):
        return self.get_ring_texts().first.text_content().strip()

    def get_total_caption(self):
        return self.get_ring_texts().last

    def get_legend_items(self):
        return self.page.locator(".et-legend-item")

    def get_legend_names_locator(self):
        return self.page.locator(".et-legend-name")

    def get_legend_values_locator(self):
        return self.page.locator(".et-legend-val")

    def get_legend_names(self):
        return [name.strip() for name in self.get_legend_names_locator().all_inner_texts()]

    def get_legend_values(self):
        return [value.strip() for value in self.get_legend_values_locator().all_inner_texts()]

    def get_legend(self):
        """The legend as {row name: what it reads}."""
        return dict(zip(self.get_legend_names(), self.get_legend_values()))

    def shown_fields(self):
        """The API fields the ring is currently adding up.

        Revision is dropped from the legend where the remote config has it off,
        and dropped from the total with it, so the total can only be worked out
        from the rows that are actually there."""
        return [LEGEND_FIELDS[name] for name in self.get_legend_names()]

    # ---------- the week bar chart ----------

    def get_barchart(self):
        return self.page.locator(".et-barchart")

    def get_barchart_title(self):
        return self.page.locator(".et-barchart-title")

    def get_grid_labels(self):
        """The y axis down the left of the chart."""
        return [
            label.strip()
            for label in self.page.locator(
                '.et-barchart-svg text[text-anchor="end"]'
            ).all_text_contents()
        ]

    def get_bar_values_locator(self):
        return self.page.locator('.et-barchart-svg text[font-weight="600"]')

    def get_bar_labels_locator(self):
        return self.page.locator('.et-barchart-svg text[fill="#6b7280"]')

    def get_bar_values(self):
        """The number written over each bar, left to right."""
        return [int(value.strip()) for value in self.get_bar_values_locator().all_text_contents()]

    def get_bar_labels(self):
        """The day under each bar: a weekday initial, or Today for the last."""
        return [label.strip() for label in self.get_bar_labels_locator().all_text_contents()]

    def get_bars(self):
        """Only the drawn bars. A day with no effort is left as bare axis."""
        return self.page.locator(".et-barchart-svg rect")

    # ---------- the info sheet ----------

    def get_info_sheet(self):
        return self.page.locator(".ais-overlay")

    def get_info_sheet_title(self):
        return self.page.locator(".ais-title")

    def get_info_sections(self):
        return self.page.locator(".ais-section")

    def get_info_headings(self):
        return self.page.locator(".ais-heading")

    def get_info_bodies(self):
        return self.page.locator(".ais-text")

    def close_info_sheet(self):
        self.page.get_by_role("button", name="Close").click()
