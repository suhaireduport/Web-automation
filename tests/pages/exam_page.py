import re


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
