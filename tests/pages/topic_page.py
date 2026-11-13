import re

from pages.practice_page import PracticeQuestionPage


# The subtopic ring is two SVG circles: a grey track that is always drawn, and
# an arc for the watched part whose stroke-dasharray is "<filled> <gap>" over
# the circumference. A subtopic that has never been opened has no arc at all,
# which is what reads back as nought.
RING_PERCENT = (
    "svg => { const arc = svg.querySelectorAll('circle')[1];"
    " if (!arc) return 0;"
    " const filled = parseFloat(arc.getAttribute('stroke-dasharray'));"
    " return filled / (2 * Math.PI * arc.r.baseVal.value) * 100; }"
)


class TopicPage:
    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def open(self, url):
        self.page.goto(url)
        self.wait_for_topics_loaded()

    def wait_for_topics_loaded(self):
        """Topics are fetched per chapter, so the first row is the signal that
        the page has finished loading."""
        self.page.locator(".tp-topic").first.wait_for()

    def get_page(self):
        return self.page.locator(".tp-page")

    def get_title(self):
        return self.page.locator(".tp-title")

    def get_subject_icon(self):
        return self.page.locator(".tp-header img.subject-icon-tile")

    def get_back_button(self):
        return self.page.locator(".tp-back")

    def click_back(self):
        self.get_back_button().click()

    # ---------- progress ----------

    def get_progress_bar(self):
        return self.page.locator(".tp-progress-bar")

    def get_progress_fill(self):
        return self.page.locator(".tp-progress-fill")

    def get_progress_width(self):
        return self.get_progress_fill().evaluate("el => el.style.width")

    def get_lessons_completed(self):
        return self.page.locator(".tp-progress-label")

    def get_progress_percent(self):
        """The header bar as a number.

        It is the chapter's own figure rather than the topic's: the bar and the
        label next to it count finished topics, not anything per topic."""
        return float(self.get_progress_width().rstrip("%"))

    def get_lessons_completed_counts(self):
        """The "3/22 Lessons Completed" line as (completed, total)."""
        match = re.search(r"(\d+)\s*/\s*(\d+)", self.get_lessons_completed().inner_text())
        return int(match.group(1)), int(match.group(2))

    # ---------- topics ----------

    def get_topics(self):
        return self.page.locator(".tp-topic")

    def topic_count(self, timeout=10000):
        """count() does not auto-wait, so give the list a chance to render."""
        try:
            self.get_topics().first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_topics().count()

    def get_topic(self, index):
        return self.get_topics().nth(index)

    def get_topic_header(self, index):
        return self.get_topic(index).locator(".tp-topic-header")

    def get_topic_header_progress_bar(self, index):
        return self.get_topic_header(index).locator(".tp-progress-bar")

    def get_topic_header_progress_ring(self, index):
        return self.get_topic_header(index).locator(".tp-progress-ring-wrap")

    def get_topic_number(self, index):
        return self.get_topic(index).locator(".tp-topic-num")

    def get_topic_title(self, index):
        return self.get_topic(index).locator(".tp-topic-title")

    def get_topic_numbers(self):
        return self.page.locator(".tp-topic-num")

    def get_topic_titles(self):
        return self.page.locator(".tp-topic-title")

    def get_topic_tick(self, index):
        return self.get_topic_number(index).locator(".tp-topic-num-tick")

    def get_completed_topics(self):
        return self.page.locator(".tp-topic-num-done")

    def is_topic_complete(self, index):
        """A topic carries no percentage of its own. Its number badge turns
        into a tick once every subtopic under it is finished, and that is the
        whole of the state kept at this level."""
        classes = self.get_topic_number(index).get_attribute("class") or ""
        return "tp-topic-num-done" in classes

    # ---------- expand / collapse ----------

    def toggle_topic(self, index):
        """Topics are independent, not an accordion: opening one does not
        close the others, and clicking an open one collapses it."""
        self.get_topic_header(index).click()

    def get_topic_content(self, index):
        return self.get_topic(index).locator(".tp-topic-content")

    def get_expanded_topics(self):
        return self.page.locator(".tp-topic-content")

    def is_topic_expanded(self, index):
        return self.get_topic_content(index).count() > 0

    def get_expanded_topic_index(self):
        """The app auto-expands the topic the user should continue from, which
        is not necessarily the first one. Returns None if nothing is open."""
        for i in range(self.get_topics().count()):
            if self.is_topic_expanded(i):
                return i
        return None

    def get_collapsed_topic_index(self):
        """Index of any topic that is currently closed."""
        for i in range(self.get_topics().count()):
            if not self.is_topic_expanded(i):
                return i
        return None

    # ---------- subtopics ----------

    def get_subtopics(self, index=None):
        if index is None:
            return self.page.locator(".tp-subtopic")
        return self.get_topic(index).locator(".tp-subtopic")

    def get_subtopic(self, topic_index, subtopic_index=0):
        return self.get_subtopics(topic_index).nth(subtopic_index)

    def get_subtopic_title(self, topic_index, subtopic_index=0):
        return self.get_subtopic(topic_index, subtopic_index).locator(".tp-subtopic-title")

    def get_subtopic_duration(self, topic_index, subtopic_index=0):
        return self.get_subtopic(topic_index, subtopic_index).locator(".tp-subtopic-duration")

    def get_subtopic_duration_at(self, flat_index):
        """The length shown against the subtopic at that position in the
        expanded list, drawn "12:34" or "1:12:34"."""
        return self.get_all_subtopics().nth(flat_index).locator(".tp-subtopic-duration")

    def get_subtopic_duration_seconds(self, flat_index):
        parts = [
            int(part)
            for part in self.get_subtopic_duration_at(flat_index).inner_text().split(":")
        ]
        seconds = 0
        for part in parts:
            seconds = seconds * 60 + part
        return seconds

    def get_progress_rings(self):
        return self.page.locator(".tp-progress-ring-wrap")

    def get_progress_ring(self, flat_index):
        """The ring of the subtopic at that position in the expanded list."""
        return self.get_all_subtopics().nth(flat_index).locator(".tp-progress-ring-svg")

    def get_ring_circles(self, flat_index):
        return self.get_progress_ring(flat_index).locator("circle")

    def get_subtopic_progress(self, flat_index):
        """How full one subtopic's ring is, as a percentage."""
        return self.get_progress_ring(flat_index).evaluate(RING_PERCENT)

    def get_subtopic_progresses(self):
        """Every ring on the page, in the order the subtopics are listed.

        Read in one hop rather than one call per ring, because a chapter can
        carry a few dozen subtopics."""
        return self.page.locator(".tp-subtopic .tp-progress-ring-svg").evaluate_all(
            f"svgs => svgs.map({RING_PERCENT})"
        )

    def click_subtopic(self, topic_index, subtopic_index=0):
        self.get_subtopic(topic_index, subtopic_index).click()

    # ---------- subtopic types ----------

    def expand_all_topics(self, attempts=3):
        """Open every topic, so that all of the subtopics are on screen in one
        flat order.

        A topic that does not take its click keeps its subtopics out of the
        list and quietly shifts the position of every subtopic after it, so the
        topics are checked for having opened rather than the clicks being
        assumed to have landed."""
        for _ in range(attempts):
            for i in range(self.get_topics().count()):
                if not self.is_topic_expanded(i):
                    self.toggle_topic(i)
            self.page.wait_for_timeout(1000)
            if self.get_expanded_topics().count() == self.get_topics().count():
                return
        raise AssertionError("not every topic would open")

    def get_all_subtopics(self):
        return self.page.locator(".tp-subtopic")

    def get_subtopic_dots(self, flat_index):
        """Decorative indicator only. It is NOT an item count: subtopics showing
        three dots still report has_quiz=false from the syllabus API."""
        return self.get_all_subtopics().nth(flat_index).locator(".tp-dot")

    def find_video_only_subtopic(self):
        """Flat index of the first subtopic, which is a plain video unless the
        player strip says otherwise."""
        return 0 if self.get_all_subtopics().count() else None

    def open_subtopic_at(self, flat_index):
        self.get_all_subtopics().nth(flat_index).click()

    # ---------- continue ----------

    def get_start_here_button(self):
        return self.page.locator(".tp-continue-btn")

    def click_start_here(self):
        self.get_start_here_button().click()

    # ---------- topic quizzes ----------
    #
    # A topic that carries quizzes lists one row per quiz under its subtopics,
    # and the row names which quiz it is. Tapping one opens the topic quiz on a
    # route of its own.

    def get_quiz_rows(self, index=None):
        if index is None:
            return self.page.locator(".tp-quiz-item")
        return self.get_topic(index).locator(".tp-quiz-item")

    def get_quiz_row_labels(self, index=None):
        return [text.strip() for text in self.get_quiz_rows(index).all_inner_texts()]

    def get_quiz_rows_by_topic(self):
        """Which quizzes each topic lists, as {topic title: [label, ...]}.

        Read in one hop rather than a call per topic, and the number a topic is
        drawn with is dropped, because the chapter call gives the same topic
        without one. Topics listing no quiz are left out."""
        listed = self.page.evaluate(
            """() => [...document.querySelectorAll('.tp-topic')].map(topic => [
                topic.querySelector('.tp-topic-title')?.textContent ?? '',
                [...topic.querySelectorAll('.tp-quiz-item')].map(row => row.textContent.trim()),
            ])"""
        )
        return {
            re.sub(r"^\s*\d+\.\s*", "", title).strip(): rows
            for title, rows in listed
            if rows
        }

    def get_quiz_row(self, topic_title, label):
        """One topic's quiz row, by the label it carries.

        The title is matched inside the card rather than as all of it, because
        the card carries the topic's number and its subtopics as well."""
        return (
            self.page.locator(".tp-topic")
            .filter(has_text=topic_title.strip())
            .first.locator(".tp-quiz-item")
            .filter(has_text=label)
            .first
        )

    def open_quiz(self, topic_title, label):
        self.get_quiz_row(topic_title, label).click()


# ---------------------------------------------------------------------------
# The topic quiz a quiz row opens
# ---------------------------------------------------------------------------

# The two quizzes a topic can carry, numbered as the chapter call numbers them
# in quiz_types and as the route names them in qt.
PROBLEM_BASED = 1
QUICK_PRACTICE = 5

# What each is called on the topic list and on the quiz itself, what the rules
# sheet heads itself with, and the call its questions come from.
QUIZ_ROW_LABELS = {
    PROBLEM_BASED: "Problem Based Questions",
    QUICK_PRACTICE: "Quick Practice Questions",
}
QUIZ_MODES = {PROBLEM_BASED: "Problem Practice", QUICK_PRACTICE: "Quick Practice"}
QUIZ_RULES_HEADINGS = {
    PROBLEM_BASED: "Problem-Based Questions",
    QUICK_PRACTICE: "Quick practice",
}
QUIZ_APIS = {
    PROBLEM_BASED: "/study-quiz/problem-quiz",
    QUICK_PRACTICE: "/study-quiz/non-adaptive-quiz",
}

# What the intro says about the way each quiz behaves.
QUIZ_NOTES = {
    PROBLEM_BASED: "Get one right, and you move forward",
    QUICK_PRACTICE: "These questions are not adaptive",
}

# How many rewards the rules sheet publishes.
REWARD_ROWS = 5


class TopicQuizPage(PracticeQuestionPage):
    """The quiz a topic carries, opened from its row on the topic list.

    It is the screen a practice runs on - the intro, the questions and the
    result are the same .tq-* markup - so the reading of it is inherited. What
    is its own is the route, which names the topic and carries the quiz in qt,
    and where the questions come from: a study-quiz call against the topic
    rather than a practice-quiz call against a task.

    Opening it writes nothing. The first answer submitted is the first write,
    so a test that only reads the screen leaves the topic as it found it.
    """

    URL_PATTERN = re.compile(
        r"https://eduport-react\.pages\.dev/home/subject/\d+/[^/]+/topics/\d+"
        r"/topic_quiz/(\d+)/[^/?]+\?.*qt=(\d+)"
    )

    @staticmethod
    def route_parts(url):
        """The topic and the quiz a route names, as (topic id, quiz type)."""
        found = TopicQuizPage.URL_PATTERN.search(url)
        return (int(found.group(1)), int(found.group(2))) if found else (None, None)

    # ---------- the intro ----------

    def wait_for_intro(self, timeout=30000):
        self.get_take_test_button().wait_for(timeout=timeout)

    def get_info_box(self):
        """The note under the scoring, which says how the quiz behaves."""
        return self.page.locator(".tq-info-box")

    # ---------- the rules sheet ----------

    def get_help_button(self):
        return self.page.locator(".tq-help")

    def open_rules(self):
        self.get_help_button().click()
        self.get_rules_sheet().wait_for()

    def get_rules_overlay(self):
        return self.page.locator(".qrs-overlay")

    def get_rules_sheet(self):
        return self.page.locator(".qrs-sheet")

    def get_rules_heading(self):
        return self.page.locator(".qrs-heading")

    def get_rules_note(self):
        return self.page.locator(".qrs-bullet-text")

    def get_rules_rewards(self):
        return self.page.locator(".qrs-reward-row")

    def get_rules_reward_texts(self):
        return [text.strip() for text in self.page.locator(".qrs-reward-text").all_inner_texts()]

    def close_rules(self):
        """The sheet carries no close button of its own; tapping the overlay
        beside it is what dismisses it."""
        self.get_rules_overlay().click(position={"x": 5, "y": 5})
        self.get_rules_overlay().wait_for(state="detached")

    # ---------- the questions ----------

    def get_quiz_title(self):
        """The topic the questions belong to, in the header of the quiz."""
        return self.page.locator(".tq-quiz-title")

    def get_choose_count(self):
        return self.page.locator(".tq-choose-num")
