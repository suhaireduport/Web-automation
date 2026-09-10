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

    def get_course_button(self):
        """The course switcher in the app bar, the same badge home carries."""
        return self.page.locator(".hp-course-badge")

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

    # ---------- syllabus tracker ----------
    #
    # The ability and syllabus cards are only built once they are scrolled
    # near, so the syllabus card is not in the page at all on a screen that has
    # not been scrolled. Everything here scrolls first.
    #
    # The subject strip is drawn with the same .an-subject-col the ability card
    # uses, so anything read subject wise off the syllabus card has to be asked
    # for through the card rather than off the page.

    def scroll_to_bottom(self):
        """Bring the foot of the screen into view so the lazy cards build.

        The analysis screen scrolls inside the app's main pane rather than the
        window, so scrolling the window does nothing."""
        self.page.evaluate(
            """() => {
                const pane = document.querySelector('.hp-main');
                if (pane) pane.scrollTop = pane.scrollHeight;
            }"""
        )
        self.get_syllabus_tracker_card().wait_for()

    def get_syllabus_tracker_card(self):
        return self.get_card("Syllabus Tracker")

    def get_syllabus_more_button(self):
        return self.page.locator(".an-more-btn-red")

    def click_syllabus_more(self):
        self.get_syllabus_more_button().click()

    def get_syllabus_course(self):
        return self.page.locator(".an-syllabus-course")

    def get_syllabus_count(self):
        return self.page.locator(".an-syllabus-count")

    def get_syllabus_percentage(self):
        return self.page.locator(".an-ring-text")

    def get_card_subjects(self, title):
        """The subject strip on one card. Both cards draw theirs with the same
        class, so which card is being read has to be said."""
        return self.get_card(title).locator(".an-subject-col")

    def card_subject_count(self, title, timeout=15000):
        """The subjects on one card, once its strip has been filled in.

        The strip is drawn from a call of its own and arrives after the card
        shell does, so it is waited for rather than counted straight away.
        Returns 0 if none turn up."""
        try:
            self.get_card_subjects(title).first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_card_subjects(title).count()

    def get_card_subject_names(self, title):
        return [
            name.strip()
            for name in self.get_card(title).locator(".an-subject-name").all_inner_texts()
        ]

    def get_card_subject_values(self, title):
        return [
            value.strip()
            for value in self.get_card(title).locator(".an-subject-pct").all_inner_texts()
        ]

    def click_card_subject(self, title, index):
        self.get_card_subjects(title).nth(index).click()
