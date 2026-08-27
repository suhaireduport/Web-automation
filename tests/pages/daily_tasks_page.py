class DailyTasksPage:
    URL = "https://eduport-react.pages.dev/daily-tasks"

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def open(self):
        self.page.goto(self.URL)
        self.wait_for_tasks_loaded()

    def wait_for_tasks_loaded(self):
        """The date strip is built from the API response, so it is the signal
        that the page has finished loading."""
        self.page.locator(".dt-date-cell").first.wait_for()

    def _count_when_ready(self, locator, timeout):
        """count() does not auto-wait, so give the locator a chance to appear
        before treating it as absent."""
        try:
            locator.first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return locator.count()

    def get_page_title(self):
        return self.page.locator(".dt-page-title")

    # ---------- header stats ----------

    def get_stat_chips(self):
        return self.page.locator(".dt-stat-chip")

    def get_coin_button(self):
        return self.page.get_by_role("button", name="Open leaderboard")

    def get_streak_button(self):
        return self.page.get_by_role("button", name="Open streak")

    def click_coin_button(self):
        self.get_coin_button().click()

    def click_streak_button(self):
        self.get_streak_button().click()

    # ---------- calendar ----------

    def get_calendar(self):
        return self.page.locator(".dt-calendar")

    def get_month_year(self):
        return self.page.locator(".dt-month-year")

    def get_date_strip(self):
        return self.page.locator(".dt-date-strip")

    def get_date_cells(self):
        return self.page.locator(".dt-date-cell")

    def get_date_cell(self, index):
        return self.get_date_cells().nth(index)

    def get_selected_date(self):
        return self.page.locator(".dt-date-selected")

    def get_day_name(self, index):
        return self.get_date_cell(index).locator(".dt-day-name")

    def get_day_number(self, index):
        return self.get_date_cell(index).locator(".dt-day-num")

    def get_day_numbers(self):
        return self.page.locator(".dt-day-num")

    def click_date(self, index):
        self.get_date_cell(index).click()

    def get_pending_date_badges(self):
        return self.page.locator(".dt-date-badge-pending")

    def get_nav_arrows(self):
        return self.page.locator(".dt-nav-arrow")

    def get_previous_arrow(self):
        return self.get_nav_arrows().nth(0)

    def get_next_arrow(self):
        return self.get_nav_arrows().nth(1)

    def click_previous_arrow(self):
        self.get_previous_arrow().click()

    def click_next_arrow(self):
        self.get_next_arrow().click()

    # ---------- pending tasks ----------

    def get_pending_tasks_badge(self):
        return self.page.get_by_role("button", name="View pending tasks")

    def has_pending_tasks(self, timeout=10000):
        return self._count_when_ready(self.get_pending_tasks_badge(), timeout) > 0

    def click_pending_tasks(self):
        self.get_pending_tasks_badge().click()

    # ---------- task list ----------

    def get_tasks_list(self):
        return self.page.locator(".dt-tasks-list")

    def get_task_groups(self):
        return self.page.locator(".dt-task-group")

    def task_group_count(self, timeout=10000):
        """Tasks for the selected date load after the calendar, so wait briefly
        before counting. Returns 0 when the date has no tasks."""
        return self._count_when_ready(self.get_task_groups(), timeout)

    def get_task_group_titles(self):
        return self.page.locator(".dt-task-group-title")

    def get_task_group(self, title):
        return self.page.locator(".dt-task-group").filter(has_text=title)

    def get_live_cards(self):
        return self.page.locator(".dt-live-card")

    def live_card_count(self, timeout=10000):
        return self._count_when_ready(self.get_live_cards(), timeout)

    def get_live_card(self, index):
        return self.get_live_cards().nth(index)

    def get_live_title(self, index):
        return self.get_live_card(index).locator(".dt-live-title")

    def get_live_subject(self, index):
        return self.get_live_card(index).locator(".dt-live-subject")

    def get_live_badge(self, index):
        return self.get_live_card(index).locator(".dt-live-badge")

    def get_watch_now_button(self, index):
        return self.get_live_card(index).locator(".dt-live-watch")

    # ---------- add task ----------

    def get_fab(self):
        return self.page.locator(".dt-fab")

    def click_fab(self):
        self.get_fab().click()

    def get_add_task_modal(self):
        return self.page.locator(".dt-addtask-modal")

    def get_add_task_title(self):
        return self.page.locator(".dt-addtask-title")

    def get_add_task_cards(self):
        return self.page.locator(".dt-addtask-card")

    def get_catch_up_card(self):
        return self.page.locator(".dt-addtask-catchup")

    def get_practice_card(self):
        return self.page.locator(".dt-addtask-practice")

    def get_self_learn_card(self):
        return self.page.locator(".dt-addtask-selflearn")

    def get_add_task_overlay(self):
        return self.page.locator(".dt-addtask-overlay")

    def get_close_add_task_button(self):
        return self.page.locator(".dt-fab-close")

    def close_add_task_modal(self):
        """Tapping outside the modal closes it. The rotated FAB (.dt-fab-close)
        renders on top visually but the overlay swallows the pointer event, so
        clicking the overlay is the path a real tap takes."""
        self.get_add_task_overlay().click(position={"x": 5, "y": 5})
