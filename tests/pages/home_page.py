import re


class HomePage:
    def __init__(self,page):
        self.page = page

    def get_greeting(self):
        """Reads "Hello, <full name>"."""
        return self.page.locator(".hp-greeting")

    def get_home_button(self):
        return self.page.get_by_role("button", name="Go to Home")

    def get_search_button(self):
        return self.page.get_by_role("button", name="Search")

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