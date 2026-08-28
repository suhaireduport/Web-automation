import re

from pages.question_library_section_page import (
    BASE_URL,
    SectionQuestionPage,
    normalise,
)


class ExamsSectionPage:
    """Exams, the fourth section of the Question Library.

    The other three sections file their questions under a subject and a
    chapter; this one files them under the exam they were met in, and splits
    them across two tabs: the questions bookmarked during an exam, and the
    questions a note was written on. Both tabs share one list, one search and
    one filter, so the tab in force is what decides which questions are shown.
    """

    URL = f"{BASE_URL}/home/questionLibrary/exams"

    # The tabs, in the order the screen shows them. The card on the Question
    # Library landing screen says Exams; this screen calls itself Exam.
    TABS = ["Bookmarks", "Exam Notes"]

    # What each tab asks the server for. Both tabs render into the same list,
    # so this is what tells one fetch from the other.
    TAB_TYPES = {"Bookmarks": "bookmarked", "Exam Notes": "note"}

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def get_page(self):
        return self.page.locator(".qle-page")

    def get_header(self):
        return self.page.locator(".qle-header")

    def get_title(self):
        return self.page.locator(".qle-title")

    def wait_for_loaded(self):
        """Either the question list or the empty state shows up once loaded."""
        self.page.locator(".qle-list, .qle-no-data").first.wait_for()

    def get_back_button(self):
        return self.page.locator(".qle-icon-btn[aria-label='Back']")

    def click_back(self):
        self.get_back_button().click()

    def get_search_button(self):
        return self.page.locator(".qle-icon-btn[aria-label='Search']")

    def click_search(self):
        self.get_search_button().click()

    def get_filter_button(self):
        return self.page.locator(".qle-icon-btn[aria-label='Filter by exam']")

    def click_filter(self):
        self.get_filter_button().click()

    # ---------- empty state ----------

    def get_empty_state(self):
        return self.page.locator(".qle-no-data")

    def get_empty_message(self):
        return self.page.locator(".qle-no-data-msg")

    def has_questions(self):
        return self.get_empty_state().count() == 0

    # ---------- tabs ----------

    def get_tabs(self):
        return self.page.locator(".qle-tab")

    def get_tab(self, name):
        """Exact match: "Bookmarks" must not also hit a longer tab name."""
        pattern = re.compile(r"^\s*" + re.escape(name) + r"\s*$")
        return self.get_tabs().filter(has_text=pattern)

    def get_active_tab(self):
        return self.page.locator(".qle-tab-active")

    def get_tab_names(self):
        return [text.strip() for text in self.get_tabs().all_inner_texts()]

    def open_tab(self, name):
        """The list of the tab being left stays on screen until the answer for
        the new one comes back, so the fetch is waited for rather than the
        list, and then the screen is held until it shows as many questions as
        that answer carried."""
        if self.get_active_tab().count() and self.get_active_tab().inner_text().strip() == name:
            self.wait_for_loaded()
            return

        with self.page.expect_response(
            f"**/question-bank/exam-questions?type={self.TAB_TYPES[name]}"
        ) as answer:
            self.get_tab(name).click()

        self.wait_for_questions(len(answer.value.json().get("questions", [])))
        self.wait_for_loaded()

    def wait_for_questions(self, total, timeout=15000):
        """Hold until the screen shows exactly that many question cards."""
        self.page.wait_for_function(
            "total => document.querySelectorAll('.qle-card').length === total",
            arg=total,
            timeout=timeout,
        )

    # ---------- questions ----------

    def get_questions(self):
        return self.page.locator(".qle-card")

    def get_question(self, index):
        return self.get_questions().nth(index)

    def question_count(self, timeout=10000):
        """count() does not auto-wait, and switching tabs re-fetches the list."""
        try:
            self.get_questions().first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_questions().count()

    def get_question_numbers(self):
        return self.page.locator(".qle-num")

    def get_question_bodies(self):
        return self.page.locator(".qle-question")

    def get_question_body(self, index):
        return self.get_question(index).locator(".qle-question")

    def get_question_text(self, index):
        return normalise(self.get_question_body(index).inner_text())

    def get_question_texts(self):
        return [
            normalise(text) for text in self.get_question_bodies().all_inner_texts()
        ]

    def find_question(self, text, exam=None):
        """Index of the card holding that question, or None.

        Exam questions can be a single character long - a paper written for
        testing holds ten of them - so an exact match is tried before falling
        back to containment, and naming the exam narrows it further: "a" is
        inside almost every other question on the screen and would otherwise
        match the wrong card.
        """
        wanted = normalise(text)
        if not wanted:
            return None

        listed = self.get_question_texts()
        exams = self.get_exam_title_texts() if exam else None

        def belongs(index):
            return exams is None or exams[index] == exam

        for index, shown in enumerate(listed):
            if shown == wanted and belongs(index):
                return index
        for index, shown in enumerate(listed):
            if wanted in shown and belongs(index):
                return index
        return None

    # ---------- the exam a question came from ----------

    def get_exam_titles(self):
        return self.page.locator(".qle-exam-title")

    def get_exam_title(self, index):
        return self.get_question(index).locator(".qle-exam-title")

    def get_exam_title_texts(self):
        return [text.strip() for text in self.get_exam_titles().all_inner_texts()]

    # ---------- bookmark ----------

    def get_bookmark_buttons(self):
        return self.page.locator(".qle-bookmark-btn")

    def get_bookmark_button(self, index):
        return self.get_question(index).locator(".qle-bookmark-btn")

    def is_bookmarked(self, index):
        return (
            self.get_bookmark_button(index).get_attribute("aria-label")
            == "Remove bookmark"
        )

    def open_question(self, index):
        self.get_question(index).click()

    # ---------- filter by exam ----------

    def get_filter_sheet(self):
        return self.page.locator(".qlef-sheet")

    def get_filter_overlay(self):
        return self.page.locator(".qlef-overlay")

    def get_filter_title(self):
        return self.page.locator(".qlef-title")

    def get_filter_rows(self):
        return self.page.locator(".qlef-row")

    def get_filter_row(self, exam):
        pattern = re.compile(r"^\s*" + re.escape(exam) + r"\s*$")
        return self.get_filter_rows().filter(
            has=self.page.locator(".qlef-label").filter(has_text=pattern)
        )

    def get_filter_labels(self):
        return self.page.locator(".qlef-label")

    def get_filter_exam_names(self):
        return [text.strip() for text in self.get_filter_labels().all_inner_texts()]

    def select_filter_exam(self, exam):
        self.get_filter_row(exam).click()

    def get_selected_filters(self):
        return self.page.locator(".qlef-check-on")

    def get_filter_apply_button(self):
        return self.page.locator(".qlef-apply")

    def apply_filter(self):
        """Applying is also what dismisses the sheet: it has no close button."""
        self.get_filter_apply_button().click()
        self.get_filter_overlay().wait_for(state="detached")
        self.wait_for_loaded()

    def get_filter_clear_button(self):
        return self.page.locator(".qlef-clear")

    def clear_filter(self):
        """Clear empties the selection and leaves the sheet standing, so it is
        still Apply that carries the cleared selection back to the list."""
        self.get_filter_clear_button().click()
        self.get_selected_filters().first.wait_for(state="detached")


class ExamsSearchPage(ExamsSectionPage):
    """The search over the exam questions of the tab that opened it.

    The results are the same cards the section lists, with the note saved
    against a question shown underneath it, so the reading helpers are
    inherited rather than written again.
    """

    URL_PATTERN = re.compile(
        r"https://eduport-react\.pages\.dev/home/questionLibrary/exams/search.*"
    )

    def wait_for_loaded(self):
        self.page.locator(".qles-card, .qles-no-result").first.wait_for()

    def get_search_input(self):
        return self.page.locator(".qles-input")

    def search(self, text):
        self.get_search_input().fill(text)

    def get_clear_button(self):
        return self.page.locator(".qle-icon-btn[aria-label='Clear search']")

    def clear_search(self):
        self.get_clear_button().click()

    # ---------- the note a result carries ----------

    def get_note_previews(self):
        return self.page.locator(".qles-note")

    def get_note_preview(self, index):
        return self.get_question(index).locator(".qles-note")

    def get_note_text(self, index):
        return self.get_question(index).locator(".qles-note-text")

    # ---------- nothing matched ----------

    def get_no_result(self):
        return self.page.locator(".qles-no-result")

    def get_no_result_title(self):
        return self.page.locator(".qles-no-result-title")

    def get_no_result_message(self):
        return self.page.locator(".qles-no-result-msg")


class ExamQuestionPage(SectionQuestionPage):
    """A single exam question opened from the section.

    The same reader the other sections open, so the options, the note, the
    bookmark, the solution, the answer state filter and the report sheet all
    behave as they do everywhere else.
    """

    URL_PATTERN = re.compile(
        r"https://eduport-react\.pages\.dev/home/questionLibrary/exams/\d+/.+/question/\d+.*"
    )
