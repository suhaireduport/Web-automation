import re


class StreakPage:
    """The streak screen behind the streak chip in the app header.

    One call, analytics/streak/now, answers {max_streak, current_streak,
    is_today} and the whole screen is drawn from it: the heading, the run of
    days across the middle and the line underneath.
    """

    URL = "https://eduport-react.pages.dev/home/streak"

    def __init__(self, page):
        self.page = page

    def open(self):
        self.page.goto(self.URL)
        self.wait_for_loaded()

    def wait_for_loaded(self, timeout=30000):
        self.get_days().first.wait_for(timeout=timeout)

    def get_page(self):
        return self.page.locator(".sk-page")

    def get_title_lines(self):
        return self.page.locator(".sk-title-line")

    def get_title(self):
        return " ".join(
            line.strip() for line in self.get_title_lines().all_inner_texts()
        )

    def get_message_lines(self):
        return self.page.locator(".sk-message-line")

    def get_message(self):
        return " ".join(
            line.strip() for line in self.get_message_lines().all_inner_texts()
        )

    def get_streak_from_message(self):
        """The run the line underneath reads out: "You are on a 3-day streak."
        """
        return int(re.search(r"(\d+)\s*-\s*day streak", self.get_message()).group(1))

    # ---------- the run of days ----------

    def get_days(self):
        return self.page.locator(".sk-day")

    def get_day_labels(self):
        return [label.strip() for label in self.page.locator(".sk-day-label").all_inner_texts()]

    def get_lit_days(self):
        """The days marked as studied."""
        return self.page.locator(".sk-day-on")

    def get_day_numbers(self):
        return self.page.locator(".sk-day-num")

    # ---------- footer ----------

    def get_back_button(self):
        return self.page.locator(".sk-back")

    def click_back(self):
        self.get_back_button().click()
