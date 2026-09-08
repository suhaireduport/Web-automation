import re


class ProfilePage:
    """The Profile page behind the home avatar.

    The avatar in the home header no longer drops a popup menu; it opens this
    full page at /profile. The hero across the top carries the account - name,
    number, join date, leaderboard rank and coin balance - drawn from the
    profile call, over a row of stat tiles drawn from a profile analysis call.
    Below the hero sit a study reminder, a grid of settings cards and a grid of
    help cards, then Sign Out.

    Edit Details is unchanged and is reached from here through the pencil on the
    avatar (get_avatar_edit), which routes to /profile/edit.
    """

    URL = "https://eduport-react.pages.dev/profile"

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def get_page(self):
        return self.page.locator(".pp-page")

    def get_title(self):
        return self.page.locator(".pp-title")

    def wait_for_loaded(self, timeout=30000):
        self.page.locator(".pp-hero").wait_for(timeout=timeout)

    def get_back_button(self):
        return self.page.locator(".pp-back")

    def click_back(self):
        self.get_back_button().click()

    def get_course_button(self):
        return self.page.locator(".pp-course")

    def get_course_name(self):
        return self.page.locator(".pp-course-name")

    # ---------- hero ----------

    def get_avatar(self):
        return self.page.locator(".pp-avatar")

    def get_avatar_edit(self):
        return self.page.locator(".pp-avatar-edit")

    def open_edit_details(self):
        self.get_avatar_edit().click()

    def get_share_button(self):
        return self.page.locator(".pp-share")

    def get_name(self):
        return self.page.locator(".pp-name")

    def get_phone(self):
        return self.page.locator(".pp-phone")

    def get_joined(self):
        return self.page.locator(".pp-joined")

    def get_rank_number(self):
        return self.page.locator(".pp-rank-num")

    def get_rank_label(self):
        return self.page.locator(".pp-rank-label")

    def get_coin_pill(self):
        return self.page.locator(".pp-coin-pill")

    def get_coins(self):
        return int(re.sub(r"\D", "", self.get_coin_pill().inner_text()) or "0")

    # ---------- stat tiles ----------

    def get_stats(self):
        return self.page.locator(".pp-stat")

    def get_stat(self, label):
        pattern = re.compile(r"^\s*" + re.escape(label) + r"\s*$")
        return self.get_stats().filter(
            has=self.page.locator(".pp-stat-label").filter(has_text=pattern)
        )

    def get_stat_value(self, label):
        return self.get_stat(label).locator(".pp-stat-value").inner_text().strip()

    def get_stat_labels(self):
        return [t.strip() for t in self.page.locator(".pp-stat-label").all_inner_texts()]

    # ---------- study reminder ----------

    def get_reminder(self):
        return self.page.locator(".pp-reminder")

    def get_reminder_switch(self):
        return self.page.locator(".pp-switch")

    # ---------- settings / help grids ----------

    def get_section_titles(self):
        return [t.strip() for t in self.page.locator(".pp-section").all_inner_texts()]

    def get_cards(self):
        return self.page.locator(".pp-card")

    def get_card(self, title):
        pattern = re.compile(r"^\s*" + re.escape(title) + r"\s*$")
        return self.get_cards().filter(
            has=self.page.locator(".pp-card-title").filter(has_text=pattern)
        )

    def get_card_titles(self):
        return [t.strip() for t in self.page.locator(".pp-card-title").all_inner_texts()]

    def click_card(self, title):
        self.get_card(title).click()

    def get_my_account_card(self):
        return self.get_card("My Account")

    def get_my_account_sub(self):
        """The student id shown under My Account."""
        return self.get_my_account_card().locator(".pp-card-sub")

    # ---------- sign out ----------

    def get_sign_out_button(self):
        return self.page.locator(".pp-signout")

    def click_sign_out(self):
        self.get_sign_out_button().click()

    def get_sign_out_dialog(self):
        return self.page.locator(".pp-signout-dialog")

    def get_sign_out_overlay(self):
        return self.page.locator(".pp-signout-overlay")

    def get_sign_out_title(self):
        return self.page.locator(".pp-signout-dialog-title")

    def get_sign_out_confirm(self):
        return self.page.locator(".pp-signout-yes")

    def get_sign_out_cancel(self):
        return self.page.locator(".pp-signout-no")

    def confirm_sign_out(self):
        self.get_sign_out_confirm().click()

    def cancel_sign_out(self):
        self.get_sign_out_cancel().click()

    # ---------- footer ----------

    def get_footer_links(self):
        return self.page.locator(".pp-footer-links")
