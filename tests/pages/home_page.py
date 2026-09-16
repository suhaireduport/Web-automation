import re


class HomePage:
    def __init__(self,page):
        self.page = page

    def get_greeting(self):
        """Reads "Hello, <full name>"."""
        return self.page.locator(".hp-greeting")

    def get_home_button(self):
        return self.page.get_by_role("button", name="Go to Home")

    def wait_for_loaded(self, timeout=30000):
        """Settled means home has drawn what the course holds: its subject
        cards, or the line saying it holds none."""
        self.page.locator(".hp-subject-card, .hp-empty").first.wait_for(timeout=timeout)

    def get_search_button(self):
        return self.page.get_by_role("button", name="Search")

    def open_search(self):
        """The header box raises the search sheet; it does not route anywhere."""
        self.page.get_by_role("button", name="Open search").click()

    def get_course_button(self):
        return self.page.locator(".hp-course-badge")

    def get_profile_button(self):
        return self.page.locator(".hp-profile-wrap")

    def open_profile_menu(self):
        self.get_profile_button().click()

    def get_exams_button(self):
        return self.page.get_by_role("button", name="Exams")

    def get_daily_tasks_button(self):
        return self.page.get_by_role("button", name="Daily Tasks")


    def get_analysis_button(self):
        return self.page.get_by_role("button", name="Analysis")

    def get_subjects(self):
        return self.page.locator(".hp-subject-card")

    def get_subject_names(self):
        return [name.strip() for name in self.get_subjects().all_inner_texts()]

    def get_subject_progress_bar(self, index):
        """The chapter list's progress bar, looked for on a home subject card."""
        return self.get_subjects().nth(index).locator(".ch-item-progress-bar")

    def get_subject_progress_ring(self, index):
        """The topic list's progress ring, looked for on a home subject card."""
        return self.get_subjects().nth(index).locator(".tp-progress-ring-wrap")

    def get_subject_by_name(self, subject_name):
        """Exact match. A substring match would make "One Shot" also hit
        "JEE One Shot" and blow up on strict mode."""
        pattern = re.compile(r"^\s*" + re.escape(subject_name) + r"\s*$")
        return self.get_subjects().filter(has_text=pattern)

    def click_subject(self, subject_name):
        self.get_subject_by_name(subject_name).click()

    def open_subject(self, subject):
        """subject may be an index (int) or an exact subject name (str)."""
        if isinstance(subject, int):
            self.get_subjects().nth(subject).click()
        else:
            self.get_subject_by_name(subject).click()

    def get_resources(self):
        return self.page.locator(".hp-resource-card")

    def get_resource_titles(self):
        return self.page.locator(".hp-resource-title")

    def get_lives(self):
        return self.page.get_by_role("button", name="Lives")


    def get_practice(self):
        return self.page.get_by_role("button", name="Practice")


    def get_question_library(self):
        return self.page.get_by_role("button", name="Question Library")

    def get_coin_button(self):
        return self.page.get_by_role("button", name="Open leaderboard")


    def get_streak_button(self):
        return self.page.get_by_role("button", name="Open streak")


    def get_ai_chat(self):
        return self.page.locator("button.hp-ai-fab")

    def get_mini_player(self):
        return self.page.get_by_role("button", name="Resume video")

    def get_close_mini_player(self):
        return self.page.get_by_role("button", name="Close mini player")

    def get_back_to_video(self):
        return self.page.get_by_role("button", name="Back to video")

    def get_contact_us_card(self):
        return self.page.locator(".hp-unlock-card")

    # Not being subscribed is answered two ways, and which one is on screen
    # depends on whether the account ever held a course: one that never did is
    # offered the Contact Us card above, one whose course has run out is
    # offered this tile and its Renew now button instead.

    def get_expiry_tile(self):
        return self.page.locator(".hp-expiry-tile")

    def get_expiry_text(self):
        return self.page.locator(".hp-expiry-text")

    def get_renew_button(self):
        return self.page.locator(".hp-expiry-renew")

    # ---------- what the page draws while it waits, and when it cannot ----------

    def get_loading_spinner(self):
        return self.page.locator(".hp-loading .hp-spinner")

    def get_error_message(self):
        return self.page.locator(".hp-error")

    def get_retry_button(self):
        return self.page.locator(".hp-retry-btn")

    def get_empty_subjects_message(self):
        return self.page.locator(".hp-empty")

    def get_stat_values(self):
        """The two chips read left to right: coins, then streak. Each shows a
        dash until the call behind it answers."""
        return self.page.locator(".hp-stat-val")

    # ---------- banners ----------
    #
    # The strip under the header is drawn from the banners the home call
    # carries, in the order the payload gives them. A banner that carries a
    # link does not open it outright: it asks first.

    def get_banner_strip(self):
        return self.page.locator(".hp-banner-wrap")

    def get_banner_card(self):
        return self.page.get_by_role("button", name="Open banner")

    def get_banner_image(self):
        return self.page.locator(".hp-banner-img")

    def get_banner_dots(self):
        return self.page.locator(".hp-banner-dots button")

    def get_active_banner_dot(self):
        return self.page.locator(".hp-banner-dot-active")

    def show_banner(self, index):
        """Pick a banner off the dots rather than waiting out the rotation."""
        self.get_banner_dots().nth(index).click()

    def banner_state(self):
        """Which banner is showing and which dot says so, read together.

        The strip moves on by itself every few seconds, so the two are taken in
        one go: read apart, the rotation can land between them."""
        return self.page.evaluate(
            """() => {
                const dots = [...document.querySelectorAll('.hp-banner-dots button')];
                const image = document.querySelector('.hp-banner-img');
                return {
                    dot: dots.findIndex(d => d.classList.contains('hp-banner-dot-active')),
                    image: image ? image.getAttribute('src') : null,
                };
            }"""
        )

    def get_open_link_dialog(self):
        return self.page.locator(".hp-open-link-dialog")

    def get_open_link_title(self):
        return self.page.locator(".hp-open-link-title")

    def get_open_link_yes(self):
        return self.page.locator(".hp-open-link-yes")

    def get_open_link_no(self):
        return self.page.locator(".hp-open-link-no")

    # ---------- subscription ----------

    def get_unlock_button(self):
        """The one action on the Contact Us card offered to an account that has
        never held a course."""
        return self.page.locator(".hp-unlock-btn")

    def get_contact_sheet(self):
        return self.page.locator(".cu-overlay")

    def get_contact_sheet_title(self):
        return self.page.locator(".cu-title")

    # ---------- the question library intro ----------
    #
    # Shown once per account a couple of seconds after home renders, and
    # remembered as seen once it is closed.

    SPLASH_SEEN_KEY = "eduport_ql_onboarding_seen"

    def get_intro_splash(self):
        return self.page.locator(".qlob-overlay")

    def get_intro_title(self):
        return self.page.locator(".qlob-title")

    def get_intro_number(self):
        return self.page.locator(".qlob-number")

    def get_intro_next(self):
        return self.page.get_by_role("button", name="Next")

    def get_intro_close(self):
        return self.page.get_by_role("button", name="Close onboarding")

    def intro_was_seen(self):
        return self.page.evaluate(
            "key => localStorage.getItem(key)", self.SPLASH_SEEN_KEY
        ) == "true"

    def set_intro_seen(self, seen):
        if seen:
            self.page.evaluate(
                "key => localStorage.setItem(key, 'true')", self.SPLASH_SEEN_KEY
            )
        else:
            self.page.evaluate(
                "key => localStorage.removeItem(key)", self.SPLASH_SEEN_KEY
            )

    # ---------- the birthday card ----------
    #
    # Raised over home for an account the home call says has not confirmed its
    # date of birth.

    def get_birthday_card(self):
        return self.page.locator(".hp-bday-card")

    def get_birthday_title(self):
        return self.page.locator(".hp-bday-title")

    def get_birthday_dob(self):
        return self.page.locator(".hp-bday-dob")

    def get_birthday_confirm(self):
        return self.page.locator(".hp-bday-confirm-link")

    def get_birthday_change(self):
        return self.page.locator(".hp-bday-change")

    # ---------- section navigation ----------
    #
    # The four sections are offered twice over: a sidebar on a desktop width
    # and a bar along the bottom on a phone, only one of which is on screen.

    def get_sidebar(self):
        return self.page.locator(".hp-sidebar")

    def get_sidebar_item(self, label):
        return self.page.locator(".hp-nav-item").filter(has_text=label)

    def get_bottom_nav(self):
        return self.page.locator(".hp-bottom-nav")

    def get_bottom_nav_item(self, label):
        return self.page.locator(".hp-bnav-item").filter(has_text=label)

    def get_active_nav_item(self):
        """The section the sidebar is marking as the one being viewed."""
        return self.page.locator(".hp-nav-item.hp-nav-active")

    def get_active_bottom_nav_item(self):
        return self.page.locator(".hp-bnav-item.hp-bnav-active")
