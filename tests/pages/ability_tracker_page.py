"""The Ability Tracker screen behind the Ability Tracker card on Analysis.

One call draws the whole screen, analytics/ability/list, and it takes nothing:
it answers every subject on the course at once and the screen picks one of them
to show. Which one is a tab across the top, and ?subject=<index> on the way in
picks the tab the screen opens on - an index into the answered list, not an id.
Changing tab is the screen's own doing and calls nothing further, so all four
subjects on a course are one payload and one comparison.

A subject holds chapters, a chapter holds topics, and every level down carries
an ability_index; a topic and a chapter also carry a category - Strong,
Average, Weak, Poor or Not Started. The filter counts topics by that category
over the whole selected subject and keeps the chapters that hold one.
"""

from pages.question_library_section_page import normalise

URL = "https://eduport-react.pages.dev/analysis/ability-tracker"

# The call the screen is drawn from, as a route pattern for expect_response.
ABILITY_API = "**/api/v3/analytics/ability/list"

# The path behind that pattern, for reading the same answer through call_api.
ABILITY_PATH = "/analytics/ability/list"

# The filter's rows, in the order it lays them out. Only Not Started is
# written differently on screen than it comes back from the call.
CATEGORIES = ["Strong", "Average", "Weak", "Poor", "Not Started"]
CATEGORY_LABELS = {category: category for category in CATEGORIES}
CATEGORY_LABELS["Not Started"] = "Not started"


def bar_colour_class(index, category=None):
    """Which band the app paints a bar in.

    Mirrors the app's own rule so a painted bar can be read back against the
    index it was painted from. Category wins where it is one of the strong
    ones; otherwise it comes down to where the index falls."""
    if category in ("Average", "Good", "Excellent") or index >= 60:
        return "at-bar-green"
    if category == "Weak" or 20 < index < 60:
        return "at-bar-orange"
    if 0 < index <= 20 or index <= 0:
        return "at-bar-red"
    return "at-bar-blue"


def topics_of(subject):
    """Every topic under a subject, chapter by chapter."""
    return [topic for chapter in subject["chapters"] for topic in chapter["topics"]]


def category_counts(subject):
    """How many topics the subject holds in each of the filter's categories."""
    counts = {category: 0 for category in CATEGORIES}
    for topic in topics_of(subject):
        if topic["category"] in counts:
            counts[topic["category"]] += 1
    return counts


def chapters_holding(subject, categories):
    """The chapters the filter keeps for a set of categories.

    Nothing ticked keeps everything; otherwise a chapter stays if any topic
    under it is in one of the ticked categories."""
    if not categories:
        return subject["chapters"]
    return [
        chapter
        for chapter in subject["chapters"]
        if any(topic["category"] in categories for topic in chapter["topics"])
    ]


def ordered_topics(chapter):
    """A chapter's topics as the screen lists them, by their own order."""
    return sorted(chapter["topics"], key=lambda topic: topic["order"])


class AbilityTrackerPage:
    URL = URL

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def open(self, subject=None, wait=True):
        """Open the screen and hand back the answer it drew itself from.

        The answer is taken as the screen took it rather than asked for again
        afterwards. The dev course this account is enrolled on changes on its
        own, so a second reading is not necessarily the reading the screen was
        built from, and a comparison against it would be comparing two
        different courses.

        wait=False opens it without waiting for the screen to fill, for the
        cases where it never will."""
        url = self.URL if subject is None else f"{self.URL}?subject={subject}"
        with self.page.expect_response(ABILITY_API) as answer:
            self.page.goto(url, wait_until="domcontentloaded")
        if wait:
            self.wait_for_loaded()
        return answer.value

    def wait_for_loaded(self, timeout=30000):
        """The summary is the first thing the call fills in."""
        self.get_summary_name().wait_for(timeout=timeout)

    def get_page(self):
        return self.page.locator(".at-page")

    def get_loading(self):
        return self.page.locator(".at-loading")

    def get_spinner(self):
        return self.page.locator(".at-spinner")

    # ---------- header ----------

    def get_title(self):
        return self.page.locator(".at-title")

    def get_back_button(self):
        return self.page.locator(".at-back")

    def click_back(self):
        self.get_back_button().click()

    def get_info_button(self):
        return self.page.get_by_role("button", name="How ability tracker works")

    def click_info_button(self):
        self.get_info_button().click()

    # ---------- subject tabs ----------

    def get_tabs(self):
        return self.page.locator(".at-tab")

    def get_tab_names(self):
        return [normalise(name) for name in self.get_tabs().all_inner_texts()]

    def get_active_tab(self):
        return self.page.locator(".at-tab-active")

    def click_tab(self, index):
        self.get_tabs().nth(index).click()

    # ---------- the selected subject ----------

    def get_summary(self):
        return self.page.locator(".at-summary")

    def get_summary_name(self):
        return self.page.locator(".at-summary-name")

    def get_summary_percentage(self):
        return self.page.locator(".at-summary-pct")

    def get_summary_bar(self):
        return self.page.locator(".at-summary-bar")

    def get_summary_bar_fill(self):
        return self.page.locator(".at-summary-bar-fill")

    def get_summary_bar_width(self):
        return self.get_summary_bar_fill().evaluate("el => el.style.width")

    # ---------- the filter ----------

    def get_filter_button(self):
        return self.page.locator(".at-filter")

    def get_filter_label(self):
        """What the button reads: All, or the ticked categories joined."""
        return self.get_filter_button().inner_text().strip()

    def open_filter(self):
        self.get_filter_button().click()
        self.get_filter_modal().wait_for()

    def get_filter_modal(self):
        return self.page.locator(".at-filter-modal")

    def get_filter_heading(self):
        return self.page.locator(".at-filter-header h3")

    def get_filter_rows(self):
        return self.page.locator(".at-filter-row")

    def get_filter_row(self, category):
        return self.get_filter_rows().nth(CATEGORIES.index(category))

    def get_filter_names(self):
        return [name.strip() for name in self.page.locator(".at-filter-cat-name").all_inner_texts()]

    def get_filter_counts(self):
        return [int(count.strip()) for count in self.page.locator(".at-filter-count").all_inner_texts()]

    def get_filter_checkbox(self, category):
        return self.get_filter_row(category).locator(".at-filter-check")

    def tick_filter(self, category):
        self.get_filter_checkbox(category).check()

    def get_clear_button(self):
        return self.page.locator(".at-filter-clear")

    def get_apply_button(self):
        return self.page.locator(".at-filter-apply")

    def apply_filter(self):
        self.get_apply_button().click()
        self.get_filter_modal().wait_for(state="detached")

    def clear_filter(self):
        self.get_clear_button().click()

    # ---------- chapters and topics ----------

    def get_chapters(self):
        return self.page.locator(".at-chapter")

    def get_chapter(self, index):
        return self.get_chapters().nth(index)

    def get_chapter_numbers(self):
        return [num.strip() for num in self.page.locator(".at-chapter-num").all_inner_texts()]

    def get_chapter_titles(self):
        return [
            normalise(title)
            for title in self.page.locator(".at-chapter-info strong").all_inner_texts()
        ]

    def get_chapter_title_labels(self):
        """The chapter titles as elements, one per chapter card, for assertions
        that wait on the text."""
        return self.get_chapters().locator(".at-chapter-info strong")

    def get_chapter_percentages(self):
        return [pct.strip() for pct in self.page.locator(".at-chapter-pct").all_inner_texts()]

    def get_chapter_bar_fill(self, index):
        return self.get_chapter(index).locator(".at-chapter-bar-fill")

    def get_chapter_bar_width(self, index):
        """The fill's inline width as written, e.g. "42%"."""
        return self.get_chapter_bar_fill(index).evaluate("el => el.style.width")

    def expand_chapter(self, index):
        self.get_chapter(index).locator(".at-chapter-header").click()
        self.get_chapter(index).locator(".at-topics").wait_for()

    def collapse_chapter(self, index):
        self.get_chapter(index).locator(".at-chapter-header").click()
        self.get_chapter(index).locator(".at-topics").wait_for(state="detached")

    def get_topics(self, chapter_index):
        return self.get_chapter(chapter_index).locator(".at-topic-card")

    def get_topic_titles(self, chapter_index):
        return [
            normalise(title)
            for title in self.get_chapter(chapter_index)
            .locator(".at-topic-title")
            .all_inner_texts()
        ]

    def get_topic_percentages(self, chapter_index):
        return [
            pct.strip()
            for pct in self.get_chapter(chapter_index)
            .locator(".at-topic-pct")
            .all_inner_texts()
        ]

    def get_topic_bar_fill(self, chapter_index, topic_index):
        return self.get_topics(chapter_index).nth(topic_index).locator(".at-topic-bar-fill")

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
