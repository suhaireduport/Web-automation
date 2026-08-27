class AnalyticsPage:
    URL = "https://eduport-react.pages.dev/analytics"

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def open(self):
        self.page.goto(self.URL)
        self.wait_for_analytics_loaded()

    def wait_for_analytics_loaded(self):
        """Both tracker cards render only after the analytics API responds."""
        self.page.locator(".an-card").nth(1).wait_for()

    def get_page_title(self):
        return self.page.locator(".an-page-title")

    # ---------- header stats ----------

    def get_stat_chips(self):
        return self.page.locator(".an-stat-chip")

    def get_coin_button(self):
        return self.page.get_by_role("button", name="Open leaderboard")

    def get_streak_button(self):
        return self.page.get_by_role("button", name="Open streak")

    def click_coin_button(self):
        self.get_coin_button().click()

    def click_streak_button(self):
        self.get_streak_button().click()

    # ---------- cards ----------

    def get_cards(self):
        return self.page.locator(".an-card")

    def get_card(self, title):
        return self.page.locator(".an-card").filter(has_text=title)

    def get_card_titles(self):
        return self.page.locator(".an-card-title-text")

    def get_effort_tracker_card(self):
        return self.get_card("Daily Effort Tracker")

    def get_ability_tracker_card(self):
        return self.get_card("Ability Tracker")

    # ---------- effort tracker ----------

    def get_effort_gauge(self):
        return self.page.locator(".an-gauge")

    def get_effort_quote(self):
        return self.page.locator(".an-effort-quote")

    def get_slider_dots(self):
        return self.page.locator(".an-dot-btn")

    def get_active_slider_dot(self):
        return self.page.locator(".an-dot-active")

    def click_slider_dot(self, index):
        self.get_slider_dots().nth(index).click()

    def get_donut_legend_items(self):
        return self.page.locator(".an-donut-legend-item")

    def get_donut_legend_labels(self):
        return self.page.locator(".an-donut-legend-label")

    def get_donut_legend_values(self):
        return self.page.locator(".an-donut-legend-val")

    # ---------- ability tracker ----------

    def get_subjects(self):
        return self.page.locator(".an-subject-col")

    def subject_count(self, timeout=10000):
        """The ability tracker's subjects arrive after the card shell renders,
        so give them a moment before counting. Returns 0 if none show up."""
        try:
            self.get_subjects().first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_subjects().count()

    def get_subject(self, index):
        return self.get_subjects().nth(index)

    def get_subject_name(self, index):
        return self.get_subject(index).locator(".an-subject-name")

    def get_subject_percentage(self, index):
        return self.get_subject(index).locator(".an-subject-pct")

    def click_subject(self, index):
        self.get_subject(index).click()

    # ---------- more buttons ----------

    def get_more_buttons(self):
        return self.page.locator(".an-more-btn")

    def get_effort_more_button(self):
        return self.get_effort_tracker_card().locator(".an-more-btn")

    def get_ability_more_button(self):
        return self.get_ability_tracker_card().locator(".an-more-btn")

    def click_effort_more(self):
        self.get_effort_more_button().click()

    def click_ability_more(self):
        self.get_ability_more_button().click()

    # ---------- info sheet ----------

    def get_info_buttons(self):
        return self.page.get_by_role("button", name="How analytics works")

    def click_info_button(self, index=0):
        self.get_info_buttons().nth(index).click()

    def get_info_sheet(self):
        return self.page.locator(".ais-overlay")

    def get_info_sheet_title(self):
        return self.page.locator(".ais-title")

    def get_info_sections(self):
        return self.page.locator(".ais-section")

    def get_info_section_titles(self):
        return self.page.locator(".ais-section-title")
