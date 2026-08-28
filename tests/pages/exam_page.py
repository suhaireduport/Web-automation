import re

from pages.question_library_section_page import normalise


class ExamPage:
    URL = "https://eduport-react.pages.dev/exams"

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def open(self, tab=None):
        if tab:
            self.page.goto(f"{self.URL}?tab={tab}")
        else:
            self.page.goto(self.URL)
        self.wait_for_exams_loaded()

    def get_page_title(self):
        return self.page.locator(".ex-page-title")

    def wait_for_exams_loaded(self):
        """Exams and the tab counts arrive from the API a moment after the route
        renders. Either the card grid or the empty state shows up once loaded."""
        self.page.locator(".ex-grid, .ex-empty").first.wait_for()

    # ---------- tabs ----------

    def get_tabs(self):
        return self.page.locator(".ex-tab")

    def get_tab(self, name):
        return self.page.locator(".ex-tab").filter(has_text=re.compile("^" + name))

    def get_current_tab(self):
        return self.get_tab("Current")

    def get_upcoming_tab(self):
        return self.get_tab("Upcoming")

    def get_past_tab(self):
        return self.get_tab("Past")

    def get_active_tab(self):
        return self.page.locator(".ex-tab-active")

    def click_tab(self, name):
        self.get_tab(name).click()
        self.wait_for_exams_loaded()

    def click_current_tab(self):
        self.click_tab("Current")

    def click_upcoming_tab(self):
        self.click_tab("Upcoming")

    def click_past_tab(self):
        self.click_tab("Past")

    def get_tab_count(self, name):
        return self.get_tab(name).locator(".ex-tab-count")

    def get_tab_count_value(self, name):
        return int(self.get_tab_count(name).inner_text().strip())

    # ---------- exam cards ----------

    def get_exam_grid(self):
        return self.page.locator(".ex-grid")

    def get_exam_cards(self):
        return self.page.locator(".ex-card")

    def get_exam_card(self, index):
        return self.get_exam_cards().nth(index)

    def exam_card_count(self, timeout=10000):
        """count() does not auto-wait, and switching tabs leaves the previous
        tab's empty state on screen for a moment, so wait for a card first."""
        try:
            self.get_exam_cards().first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_exam_cards().count()

    def get_exam_card_by_title(self, title):
        return self.get_exam_cards().filter(has_text=title)

    def get_exam_titles(self):
        return self.page.locator(".ex-title")

    def get_exam_title(self, index):
        return self.get_exam_card(index).locator(".ex-title")

    def get_exam_subject(self, index):
        return self.get_exam_card(index).locator(".ex-subject")

    def get_exam_meta_rows(self, index):
        return self.get_exam_card(index).locator(".ex-meta-row")

    def get_exam_schedule(self, index):
        return self.get_exam_meta_rows(index).nth(0)

    def get_exam_duration_and_marks(self, index):
        return self.get_exam_meta_rows(index).nth(1)

    # ---------- attempt ----------

    def get_attempt_buttons(self):
        return self.page.locator(".ex-attempt-btn")

    def get_attempt_button(self, index=0):
        return self.get_exam_card(index).locator(".ex-attempt-btn")

    def click_attempt(self, index=0):
        self.get_attempt_button(index).click()

    # ---------- attempted exams ----------

    def get_attempted_badges(self):
        return self.page.locator(".ex-badge-attended")

    def get_review_buttons(self):
        return self.page.locator(".ex-review-btn")

    def get_review_button(self, index):
        return self.get_exam_card(index).locator(".ex-review-btn")

    def click_review(self, index):
        self.get_review_button(index).click()

    def get_attempted_badge(self, index):
        return self.get_exam_card(index).locator(".ex-badge-attended")

    def is_exam_attempted(self, index):
        return self.get_attempted_badge(index).count() > 0

    def find_unattempted_exam(self):
        """Index of the first exam still offering Attempt, or None."""
        for i in range(self.exam_card_count()):
            if self.get_attempt_button(i).count() > 0:
                return i
        return None

    def find_attempted_exam(self):
        """Index of the first exam already attempted, or None."""
        for i in range(self.exam_card_count()):
            if self.get_review_button(i).count() > 0:
                return i
        return None

    # ---------- start confirmation ----------
    # A live exam warns before it lets you through to the instructions page.
    # Past exams go straight there without asking.

    def get_confirm_modal(self):
        return self.page.locator(".ex-modal")

    def get_confirm_overlay(self):
        return self.page.locator(".ex-modal-overlay")

    def get_confirm_title(self):
        return self.page.locator(".ex-modal-title")

    def get_confirm_body(self):
        return self.page.locator(".ex-modal-body")

    def get_confirm_start_button(self):
        return self.get_confirm_modal().get_by_role(
            "button", name="Start Exam", exact=True
        )

    def get_confirm_cancel_button(self):
        return self.get_confirm_modal().get_by_role("button", name="Cancel", exact=True)

    def confirm_start(self):
        self.get_confirm_start_button().click()

    def cancel_start(self):
        self.get_confirm_cancel_button().click()

    # ---------- locked exams ----------

    def get_locked_cards(self):
        """An exam the account is not entitled to: the API sends
        subscription_status false and the card loses its action button."""
        return self.page.locator(".ex-card-locked")

    def get_lock_badge(self, index):
        return self.get_exam_card(index).locator(".ex-lock-badge")

    def is_exam_locked(self, index):
        return self.get_lock_badge(index).count() > 0

    def find_locked_exam(self):
        """Index of the first locked exam, or None."""
        for i in range(self.exam_card_count()):
            if self.is_exam_locked(i):
                return i
        return None

    # ---------- loading ----------

    def get_loading_indicator(self):
        """Whatever the page shows while the exam list is still in flight."""
        return self.page.locator(
            ".ex-loading, .ex-skeleton, [class*='skeleton'], [class*='spinner']"
        )

    # ---------- empty state ----------

    def get_empty_state(self):
        return self.page.locator(".ex-empty")

    def get_empty_message(self):
        return self.page.locator(".ex-empty-title")


class ExamInstructionsPage:
    def __init__(self, page):
        self.page = page

    def get_page(self):
        return self.page.locator(".ei-page")

    def get_header_title(self):
        return self.page.locator(".ei-title")

    def get_exam_name(self):
        return self.page.locator(".ei-exam-name")

    def get_back_button(self):
        return self.page.locator(".ei-back")

    def click_back(self):
        self.get_back_button().click()

    def get_stats(self):
        return self.page.locator(".ei-stat")

    def get_stat_value(self, label):
        return self.page.locator(".ei-stat").filter(has_text=label).locator(".ei-stat-value")

    def get_total_questions(self):
        return self.get_stat_value("Total Questions")

    def get_duration(self):
        return self.get_stat_value("Duration")

    def get_total_questions_count(self):
        return int(self.get_total_questions().inner_text().strip())

    def get_duration_minutes(self):
        return int(re.search(r"\d+", self.get_duration().inner_text()).group())

    def get_instructions_title(self):
        return self.page.locator(".ei-inst-title")

    def get_instructions_box(self):
        return self.page.locator(".ei-inst-box")

    def get_instruction_items(self):
        return self.page.locator(".ei-inst-item")

    def get_important_note(self):
        return self.page.locator(".ei-important")

    def get_start_exam_button(self):
        return self.page.locator(".ei-start-btn")

    def click_start_exam(self):
        self.get_start_exam_button().click()

    # ---------- feedback ----------

    def get_toast(self):
        """react-hot-toast renders every message into this one container.

        The container is always in the DOM and empty until a message fires,
        so assert on its text rather than its presence."""
        return self.page.locator("[data-rht-toaster]")

    def get_error_message(self):
        """Any inline error the page renders for a start that cannot proceed."""
        return self.page.locator(".ei-error, .ei-message, [class*='error']")


class ExamResultPage:
    """The result an attempted exam opens into.

    Review on this screen does not leave it: it swaps the marks summary for a
    grid of the questions, one cell per question, and renames itself Back to
    Result. A cell is what opens the question itself.
    """

    URL_PATTERN = re.compile(r"https://eduport-react\.pages\.dev/exams/\d+/result.*")

    def __init__(self, page):
        self.page = page

    def get_page(self):
        return self.page.locator(".er-page")

    def get_header_title(self):
        return self.page.locator(".er-header-title")

    def get_exam_name(self):
        return self.page.locator(".er-exam-name")

    def get_exam_date(self):
        return self.page.locator(".er-exam-date")

    def wait_for_loaded(self):
        self.get_review_button().wait_for()

    def get_back_button(self):
        return self.page.locator(".er-back-btn")

    # ---------- marks ----------

    def get_marks(self):
        return self.page.locator(".er-stat-marks .er-stat-value")

    def get_answer_column(self, label):
        return self.page.locator(".er-answer-col").filter(has_text=label)

    def get_answer_count(self, label):
        return int(
            self.get_answer_column(label).locator(".er-answer-value").inner_text().strip()
        )

    # ---------- question grid ----------

    def get_review_button(self):
        return self.page.locator(".er-review-btn")

    def open_review_grid(self):
        """Only opens it: a second click would fold it away again."""
        if self.get_question_cells().count() == 0:
            self.get_review_button().click()
            self.get_question_cells().first.wait_for()

    def get_question_cells(self):
        return self.page.locator(".er-indicator")

    def get_legend_items(self):
        return self.page.locator(".er-legend-item")

    def open_question(self, number=1):
        """Questions are numbered from 1, matching the cells."""
        self.open_review_grid()
        self.get_question_cells().nth(number - 1).click()


class ExamReviewPage:
    """One question of an attempted exam, opened from the result.

    This is where an exam question is bookmarked or given a note, which is what
    files it into the Exams section of the Question Library. The screen is read
    only otherwise: the answer has already been marked, so the options carry
    their marking rather than taking a new one.
    """

    URL_PATTERN = re.compile(r"https://eduport-react\.pages\.dev/exams/\d+/review.*")

    def __init__(self, page):
        self.page = page

    def get_page(self):
        return self.page.locator(".erp-page")

    def wait_for_loaded(self, timeout=30000):
        self.page.locator(".erp-card").wait_for(timeout=timeout)

    def get_close_button(self):
        return self.page.locator(".erp-close-btn")

    def click_close(self):
        self.get_close_button().click()

    # ---------- counter and palette ----------

    def get_counter(self):
        return self.page.locator(".erp-q-count")

    def get_counter_numbers(self):
        """'1 / 10' -> (1, 10)"""
        current, total = self.get_counter().inner_text().split("/")
        return int(current.strip()), int(total.strip())

    def get_current_question_number(self):
        return self.get_counter_numbers()[0]

    def get_total_questions(self):
        return self.get_counter_numbers()[1]

    def get_strip_dots(self):
        return self.page.locator(".erp-strip-dot")

    def get_active_strip_dot(self):
        return self.page.locator(".erp-strip-active")

    def go_to_question(self, number):
        """Dots are labelled from 1, matching the question numbers.

        The card stays on screen right through the move, so waiting for it
        proves nothing: the counter and the strip are what say the next
        question has actually arrived. Reading the question any earlier gives
        back the one being left, which is how a bookmark ends up recorded
        against the wrong text."""
        self.get_strip_dots().nth(number - 1).click()
        self.page.wait_for_function(
            "n => { const counter = document.querySelector('.erp-q-count');"
            " const active = document.querySelector('.erp-strip-active');"
            " return counter && active"
            " && parseInt(counter.textContent.trim(), 10) === n"
            " && active.textContent.trim() === String(n); }",
            arg=number,
            timeout=15000,
        )

    def get_palette_button(self):
        return self.page.locator(".erp-icon-btn[aria-label='Question palette']")

    def get_report_button(self):
        return self.page.locator(".erp-icon-btn[aria-label='Report issue']")

    # ---------- question ----------

    def get_choose_label(self):
        return self.page.locator(".erp-choose-label")

    def get_question(self):
        return self.page.locator(".erp-question-text")

    def get_question_text(self):
        return normalise(self.get_question().inner_text())

    def get_options(self):
        return self.page.locator(".erp-option")

    def get_option_letters(self):
        return self.page.locator(".erp-opt-letter")

    def get_option_texts(self):
        return self.page.locator(".erp-opt-text")

    def get_option_text_values(self):
        return [text.strip() for text in self.get_option_texts().all_inner_texts()]

    def get_correct_options(self):
        return self.page.locator(".erp-option-correct")

    def find_substantial_question(self, minimum=12, limit=6):
        """Move to the first question with enough text to be told apart later.

        Exam questions are whatever the paper was written with, and a paper set
        up for testing can hold questions a single character long. One of those
        cannot be searched for, and matches every other question on the screen,
        so a longer one is looked for first. Falls back to wherever it started
        when the whole paper is like that."""
        start = self.get_current_question_number()
        for number in range(start, min(self.get_total_questions(), limit) + 1):
            if number != self.get_current_question_number():
                self.go_to_question(number)
            if len(self.get_question_text()) >= minimum:
                return number
        if self.get_current_question_number() != start:
            self.go_to_question(start)
        return start

    # ---------- bookmark ----------

    def get_bookmark_button(self):
        return self.page.locator(".erp-bookmark")

    def is_bookmarked(self):
        return self.get_bookmark_button().get_attribute("aria-label") == "Remove bookmark"

    def click_bookmark(self):
        self.get_bookmark_button().click()

    # ---------- note ----------

    def get_note_button(self):
        return self.page.locator(".erp-note-fab")

    def click_note(self):
        self.get_note_button().click()

    def get_note_sheet(self):
        return self.page.locator(".nes-overlay")

    def get_note_editor(self):
        return self.page.locator("div.tiptap")

    def get_note_save_button(self):
        return self.page.locator(".nes-save")

    def get_note_close_button(self):
        return self.page.locator(".nes-close")

    def write_note(self, text):
        """Replace whatever the question already holds with text.

        A run that was interrupted can leave a note behind, and the editor opens
        on it rather than empty, so it is cleared before typing."""
        self.click_note()
        editor = self.get_note_editor()
        editor.wait_for()
        editor.click()
        self.page.keyboard.press("ControlOrMeta+a")
        self.page.keyboard.press("Backspace")
        self.page.keyboard.type(text)

    # ---------- moving on ----------

    def get_explanation_button(self):
        return self.page.locator(".erp-btn-outline")

    def get_next_button(self):
        return self.page.locator(".erp-btn-primary")
