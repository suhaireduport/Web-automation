"""The Syllabus Tracker screen behind the Syllabus Tracker card on Analysis.

One call draws the whole screen, analytics/ability/syllabus-tracker, and it
takes nothing: it answers the course title and every subject on it, each with
its chapters and each chapter with its topics. Every count on the screen is
worked out from those topics rather than answered outright - a topic is done
when its progress reaches 100, and:

    the ring at the top   done / total over every subject, as a percentage
    the subject bar       done / total over the selected subject
    a chapter row         done / total over that chapter's topics

Which subject is shown is a tab across the top, and ?subject=<index> on the way
in picks the tab the screen opens on - an index into the answered list, not an
id. Changing tab calls nothing further.

A topic can also carry a syllabus_label - Class Room, Home Assignments - which
the screen writes beside the title in the colour the label came with.
"""

import math

from pages.question_library_section_page import normalise

URL = "https://eduport-react.pages.dev/analysis/syllabus-tracker"

# The call the screen is drawn from, as a route pattern for expect_response.
SYLLABUS_API = "**/api/v3/analytics/ability/syllabus-tracker"

# The path behind that pattern, for reading the same answer through call_api.
SYLLABUS_PATH = "/analytics/ability/syllabus-tracker"

# A topic counts as covered at this much progress and not before.
DONE = 100


def topics_of(subject):
    """Every topic under a subject, chapter by chapter."""
    return [topic for chapter in subject["chapters"] for topic in chapter["topics"]]


def progress_of(topics):
    """How many of a run of topics are done, and how many there are."""
    topics = list(topics)
    return sum(1 for topic in topics if topic["progress"] >= DONE), len(topics)


def subject_progress(subject):
    return progress_of(topics_of(subject))


def chapter_progress(chapter):
    return progress_of(chapter["topics"])


def overall_progress(subjects):
    return progress_of(topic for subject in subjects for topic in topics_of(subject))


def percent(done, total):
    """The percentage the ring is drawn at.

    Rounded the way the app rounds rather than the way Python does: a half
    goes up, where Python would send it to the nearest even. Nothing over
    nothing is nothing rather than an error."""
    return math.floor(done / total * 100 + 0.5) if total else 0


def ordered_topics(chapter):
    """A chapter's topics as the screen lists them, by their own order."""
    return sorted(chapter["topics"], key=lambda topic: topic["order"])


def hex_to_rgb(colour):
    """A label's colour as the browser gives it back.

    The call answers a bare six digit hex, the app writes it with a hash in
    front, and the style property reads back as rgb()."""
    red, green, blue = (int(colour[at:at + 2], 16) for at in (0, 2, 4))
    return f"rgb({red}, {green}, {blue})"


def read_count(text):
    """A "2/295" reading off the screen, as the two numbers it holds."""
    done, total = text.strip().split("/")
    return int(done), int(total)


class SyllabusTrackerPage:
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
        with self.page.expect_response(SYLLABUS_API) as answer:
            self.page.goto(url, wait_until="domcontentloaded")
        if wait:
            self.wait_for_loaded()
        return answer.value

    def wait_for_loaded(self, timeout=30000):
        self.get_overall_count().wait_for(timeout=timeout)

    def get_page(self):
        return self.page.locator(".st-page")

    def get_loading(self):
        return self.page.locator(".st-loading")

    def get_spinner(self):
        return self.page.locator(".st-spinner")

    # ---------- header ----------

    def get_title(self):
        return self.page.locator(".st-title")

    def get_back_button(self):
        return self.page.locator(".st-back")

    def click_back(self):
        self.get_back_button().click()

    def get_info_button(self):
        return self.page.get_by_role("button", name="How syllabus tracker works")

    def click_info_button(self):
        self.get_info_button().click()

    # ---------- the whole course ----------

    def get_overall(self):
        return self.page.locator(".st-overall")

    def get_overall_course(self):
        return self.page.locator(".st-overall-course")

    def get_overall_count(self):
        return self.page.locator(".st-overall-count")

    def read_overall_count(self):
        return read_count(self.get_overall_count().inner_text())

    def get_overall_ring(self):
        return self.page.locator(".st-overall-ring")

    def get_overall_percentage(self):
        return self.page.locator(".st-overall-pct")

    # ---------- subject tabs ----------

    def get_tabs(self):
        return self.page.locator(".st-tab")

    def get_tab_names(self):
        return [normalise(name) for name in self.get_tabs().all_inner_texts()]

    def get_active_tab(self):
        return self.page.locator(".st-tab-active")

    def click_tab(self, index):
        self.get_tabs().nth(index).click()

    # ---------- the selected subject ----------

    def get_subject_summary(self):
        return self.page.locator(".st-subject-summary")

    def get_subject_name(self):
        return self.page.locator(".st-subject-name")

    def get_subject_count(self):
        return self.page.locator(".st-subject-count")

    def read_subject_count(self):
        return read_count(self.get_subject_count().inner_text())

    def get_subject_bar(self):
        return self.page.locator(".st-subject-bar")

    def get_subject_bar_fill(self):
        return self.page.locator(".st-subject-bar-fill")

    def get_subject_bar_width(self):
        """How far along the subject bar is drawn, as a number of percent.

        The subject bar is the one place the app does not round before it
        draws, so what comes back is a raw fraction rather than a whole
        number."""
        return float(self.get_subject_bar_fill().evaluate("el => el.style.width").rstrip("%"))

    # ---------- chapters and topics ----------

    def get_chapters(self):
        return self.page.locator(".st-chapter")

    def get_chapter(self, index):
        return self.get_chapters().nth(index)

    def get_chapter_numbers(self):
        return [num.strip() for num in self.page.locator(".st-chapter-num").all_inner_texts()]

    def get_chapter_titles(self):
        return [
            normalise(title)
            for title in self.page.locator(".st-chapter-info strong").all_inner_texts()
        ]

    def get_chapter_counts(self):
        return [count.strip() for count in self.page.locator(".st-chapter-pct").all_inner_texts()]

    def get_chapter_bar_fill(self, index):
        return self.get_chapter(index).locator(".st-chapter-bar-fill")

    def expand_chapter(self, index):
        self.get_chapter(index).locator(".st-chapter-header").click()
        self.get_chapter(index).locator(".st-topics").wait_for()

    def collapse_chapter(self, index):
        self.get_chapter(index).locator(".st-chapter-header").click()
        self.get_chapter(index).locator(".st-topics").wait_for(state="detached")

    def get_topics(self, chapter_index):
        return self.get_chapter(chapter_index).locator(".st-topic-card")

    def get_topic_titles(self, chapter_index):
        return [
            normalise(title)
            for title in self.get_chapter(chapter_index)
            .locator(".st-topic-title")
            .all_inner_texts()
        ]

    def get_topic_percentages(self, chapter_index):
        return [
            pct.strip()
            for pct in self.get_chapter(chapter_index)
            .locator(".st-topic-pct")
            .all_inner_texts()
        ]

    def get_topic_labels(self, chapter_index):
        """The label beside a title, for the topics that carry one. Shorter
        than the topic list where some do not."""
        return [
            normalise(label)
            for label in self.get_chapter(chapter_index)
            .locator(".st-topic-label")
            .all_inner_texts()
        ]

    def get_topic_label(self, chapter_index, topic_index):
        return self.get_topics(chapter_index).nth(topic_index).locator(".st-topic-label")

    def get_topic_bar_fill(self, chapter_index, topic_index):
        return self.get_topics(chapter_index).nth(topic_index).locator(".st-topic-bar-fill")

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
