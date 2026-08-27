import re


class LiveExamPage:
    """The exam player reached by starting an exam.

    Every selector here was read off a live attempt. Note that the player has no
    Previous button: forward movement is the Continue button and backward
    movement is the question palette strip along the top.
    """

    URL_PATTERN = re.compile(r"https://eduport-react\.pages\.dev/exams/\d+/take.*")

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def get_page(self):
        return self.page.locator(".ep-page")

    def is_open(self):
        return self.get_page().count() > 0

    def wait_for_question(self, timeout=15000):
        self.get_question_text().wait_for(timeout=timeout)

    def get_close_button(self):
        return self.page.locator(".ep-close-btn")

    # ---------- header ----------

    def get_question_counter(self):
        return self.page.locator(".ep-q-count")

    def get_counter_numbers(self):
        """'12/75' -> (12, 75)"""
        current, total = self.get_question_counter().inner_text().split("/")
        return int(current), int(total)

    def get_current_question_number(self):
        return self.get_counter_numbers()[0]

    def get_total_questions(self):
        return self.get_counter_numbers()[1]

    def get_palette_button(self):
        return self.page.locator(".ep-icon-btn[aria-label='Question palette']")

    def get_report_issue_button(self):
        return self.page.locator(".ep-icon-btn[aria-label='Report issue']")

    # ---------- question palette strip ----------

    def get_palette_strip(self):
        return self.page.locator(".ep-palette-strip")

    def get_strip_dots(self):
        return self.page.locator(".ep-strip-dot")

    def get_strip_dot(self, number):
        """Dots are labelled from 1, matching the question numbers."""
        return self.get_strip_dots().nth(number - 1)

    def get_active_strip_dot(self):
        return self.page.locator(".ep-strip-dot.ep-strip-active")

    def get_strip_dot_state(self, number):
        """One of not_visited, unanswered, answered or marked_answered."""
        classes = self.get_strip_dot(number).get_attribute("class").split()
        for state in ("marked_answered", "answered", "unanswered", "not_visited"):
            if state in classes:
                return state
        return None

    def go_to_question(self, number):
        self.get_strip_dot(number).click()

    # ---------- timer ----------

    def get_timer(self):
        return self.page.locator(".ep-timer-tap")

    def get_timer_text(self):
        return self.page.locator(".ep-timer-text")

    def get_timer_seconds(self):
        """The header counts down in minutes:seconds, so 179:54 is 179 minutes."""
        minutes, seconds = self.get_timer_text().inner_text().strip().split(":")
        return int(minutes) * 60 + int(seconds)

    # ---------- bookmark ----------

    def get_bookmark_button(self):
        return self.page.locator(".ep-bookmark-btn")

    def is_bookmarked(self):
        return "ep-bookmarked" in self.get_bookmark_button().get_attribute("class")

    def click_bookmark(self):
        self.get_bookmark_button().click()

    # ---------- question ----------

    def get_question_text(self):
        return self.page.locator(".ep-question-text")

    def get_question_body(self):
        return self.page.locator(".ep-html").first

    def get_choose_label(self):
        return self.page.locator(".ep-choose-label")

    def get_choose_count(self):
        return self.page.locator(".ep-choose-num")

    # ---------- options ----------

    def get_options(self):
        return self.page.locator(".ep-option")

    def get_option(self, index):
        return self.get_options().nth(index)

    def get_option_letters(self):
        return self.page.locator(".ep-opt-letter")

    def select_option(self, index):
        self.get_option(index).click()

    def get_selected_options(self):
        return self.page.locator(".ep-option-selected")

    def is_option_selected(self, index):
        return "ep-option-selected" in self.get_option(index).get_attribute("class")

    # ---------- actions ----------

    def get_note_button(self):
        return self.page.locator(".ep-note-fab")

    def get_mark_button(self):
        return self.page.locator(".ep-mark-btn")

    def click_mark_for_review(self):
        """Marks the question and moves on to the next one in a single step."""
        self.get_mark_button().click()

    def get_continue_button(self):
        return self.page.locator(".ep-continue-btn")

    def click_continue(self):
        self.get_continue_button().click()

    # ---------- submit sheet, opened by tapping the timer ----------

    def open_submit_sheet(self):
        self.get_timer().click()

    def get_submit_sheet(self):
        return self.page.locator(".ep-inst-overlay")

    def get_submit_button(self):
        return self.page.locator(".ep-inst-submit")

    def get_back_to_exam_button(self):
        return self.page.locator(".ep-inst-back")

    def close_submit_sheet(self):
        """Escape does not dismiss this sheet, so use its own button."""
        self.get_back_to_exam_button().click()

    def get_status_row(self, label):
        return self.get_submit_sheet().get_by_text(label, exact=True)
