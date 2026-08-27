class ProfileMenuPage:
    """The popup behind the avatar in the home header.

    Five of its items are routes; Help centre and Customer care open an overlay
    on top of the page instead, and Sign Out asks for confirmation first.
    """

    def __init__(self, page):
        self.page = page

    # ---------- menu ----------

    def get_menu(self):
        return self.page.locator(".hp-profile-popup")

    def is_open(self):
        return self.get_menu().count() > 0

    def get_items(self):
        return self.page.locator(".hp-profile-item")

    def get_item_names(self):
        return [name.strip() for name in self.get_items().all_inner_texts()]

    def get_item(self, name):
        return self.get_menu().get_by_role("button", name=name, exact=True)

    def click_item(self, name):
        self.get_item(name).click()

    # ---------- signed in user ----------

    def get_user(self):
        return self.page.locator(".hp-profile-user")

    def get_user_avatar(self):
        return self.page.locator(".hp-profile-user-avatar")

    def get_user_name(self):
        return self.page.locator(".hp-profile-user-name")

    def get_student_id(self):
        return self.page.locator(".hp-profile-student-id")

    # ---------- help centre overlay ----------

    def get_help_centre_overlay(self):
        return self.page.locator(".hc-overlay")

    def get_help_centre_panel(self):
        return self.page.locator(".hc-panel")

    def get_help_centre_frame(self):
        return self.page.locator(".hc-iframe")

    def get_help_centre_close_button(self):
        return self.page.locator(".hc-close")

    def close_help_centre(self):
        self.get_help_centre_close_button().click()

    # ---------- customer care sheet ----------

    def get_customer_care_overlay(self):
        return self.page.locator(".cu-overlay")

    def get_customer_care_sheet(self):
        return self.page.locator(".cu-sheet")

    def get_customer_care_title(self):
        return self.page.locator(".cu-title")

    def get_customer_care_options(self):
        return self.page.locator(".cu-option")

    def close_customer_care(self):
        """The sheet carries no close button, so dismiss it on the backdrop."""
        box = self.get_customer_care_sheet().bounding_box()
        self.page.mouse.click(box["x"] + box["width"] / 2, max(box["y"] - 40, 10))

    # ---------- sign out ----------

    def get_sign_out_item(self):
        return self.page.locator(".hp-profile-item-logout")

    def click_sign_out(self):
        self.get_sign_out_item().click()

    def get_sign_out_dialog(self):
        return self.page.locator(".hp-signout-dialog")

    def get_sign_out_overlay(self):
        return self.page.locator(".hp-signout-overlay")

    def get_sign_out_title(self):
        return self.page.locator(".hp-signout-title")

    def get_sign_out_subtitle(self):
        return self.page.locator(".hp-signout-subtitle")

    def get_sign_out_confirm_button(self):
        return self.page.locator(".hp-signout-yes")

    def get_sign_out_cancel_button(self):
        return self.page.locator(".hp-signout-no")

    def confirm_sign_out(self):
        self.get_sign_out_confirm_button().click()

    def cancel_sign_out(self):
        self.get_sign_out_cancel_button().click()
