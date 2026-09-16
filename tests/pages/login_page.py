import re


class LoginPage:
    """The login screen: a country selector, a phone box and Send OTP.

    The number is entered against a chosen country code (India by default). The
    button reads "Send OTP" and stays disabled until the box holds a full ten
    digit number; the box itself only ever keeps digits, so anything else typed
    into it is dropped rather than rejected with a message.
    """

    URL = "https://eduport-react.pages.dev/login"

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def get_page(self):
        return self.page.locator(".dl-page")

    def get_logo(self):
        return self.page.locator(".dl-logo")

    def wait_for_loaded(self, timeout=30000):
        self.get_mobile_input().wait_for(timeout=timeout)

    # ---------- phone ----------

    def get_mobile_input(self):
        return self.page.locator(".dl-phone-input")

    def enter_mobile(self, mobile_number):
        self.get_mobile_input().fill(mobile_number)

    def type_mobile(self, mobile_number):
        """Enter the number a keystroke at a time.

        The box caps itself at ten digits per keystroke, and a single fill of a
        longer string is rejected whole rather than truncated, so a test about
        the cap has to type."""
        box = self.get_mobile_input()
        box.click()
        box.press("Control+A")
        box.press("Backspace")
        self.page.keyboard.type(mobile_number)

    def get_mobile_value(self):
        return self.get_mobile_input().input_value()

    def get_clear_button(self):
        """Shown once the box holds something, to empty it in one tap."""
        return self.page.get_by_role("button", name="Clear")

    def clear_mobile(self):
        self.get_clear_button().click()

    # ---------- send otp ----------

    def get_continue_button(self):
        """Kept under its old name so callers read the same; the label is now
        "Send OTP"."""
        return self.page.locator(".dl-primary-btn")

    def get_send_otp_button(self):
        return self.page.locator(".dl-primary-btn")

    def click_continue(self):
        self.get_send_otp_button().click()

    def login(self, mobile_number):
        self.enter_mobile(mobile_number)
        self.click_continue()

    def get_send_spinner(self):
        """The button gives up its label for a spinner while the send is out."""
        return self.page.locator(".dl-primary-btn .dl-spinner")

    def press_enter(self):
        """Enter in the phone box sends the code, the same as the button."""
        self.get_mobile_input().press("Enter")

    # ---------- country selector ----------

    def get_country_button(self):
        return self.page.locator(".dl-country-btn")

    def get_country_code(self):
        return self.page.locator(".dl-country-code").inner_text().strip()

    def get_country_flag(self):
        return self.page.locator(".dl-country-flag").inner_text().strip()

    def open_country_menu(self):
        self.get_country_button().click()
        self.get_country_menu().wait_for()

    def get_country_menu(self):
        return self.page.locator(".dl-country-menu")

    def get_country_search(self):
        return self.page.locator(".dl-country-search")

    def get_country_items(self):
        return self.page.locator(".dl-country-item")

    def get_active_country_item(self):
        """The country the box is currently set to, marked in the open menu."""
        return self.page.locator(".dl-country-item--active")

    def get_country_item_codes(self):
        """The dial code on every country row the open menu is listing."""
        return self.page.locator(".dl-country-item-code")

    def get_country_empty_message(self):
        """Shown in place of the list when the search matches no country."""
        return self.page.locator(".dl-country-empty")

    def close_country_menu(self):
        """Tap away from the menu. It closes on a press outside itself rather
        than on a button of its own."""
        self.page.locator(".dl-hero").click()
        self.get_country_menu().wait_for(state="hidden")

    def search_country(self, text):
        self.get_country_search().fill(text)

    def select_country(self, name):
        """Pick a country by name from the open menu and return its dial code."""
        self.open_country_menu()
        self.search_country(name)
        item = self.get_country_items().filter(
            has=self.page.locator(".dl-country-item-name").filter(
                has_text=re.compile(r"^\s*" + re.escape(name) + r"\s*$")
            )
        ).first
        code = item.locator(".dl-country-item-code").inner_text().strip()
        item.click()
        return code

    # ---------- help ----------

    def get_help_button(self):
        return self.page.locator(".dl-help-btn")

    def click_help(self):
        self.get_help_button().click()

    def get_contact_sheet(self):
        return self.page.locator(".cu-overlay")

    def get_contact_sheet_title(self):
        return self.page.locator(".cu-title")

    def get_contact_options(self):
        """One row per channel the contact call offers, in the order served."""
        return self.page.locator(".cu-option")

    def get_contact_option_labels(self):
        return [text.strip() for text in self.page.locator(".cu-option-label").all_inner_texts()]

    def close_contact_sheet_with_escape(self):
        self.page.keyboard.press("Escape")

    def close_contact_sheet_with_backdrop(self):
        """The sheet sits on an overlay that dismisses it; the sheet itself
        swallows the press, so the corner of the overlay is what is tapped."""
        self.get_contact_sheet().click(position={"x": 5, "y": 5})

    # ---------- terms ----------

    def get_terms_link(self):
        return self.page.locator(".dl-terms a")

    # ---------- feedback ----------

    def get_toast(self, text):
        """Send failures surface as a toast rather than inline text."""
        return self.page.get_by_text(text)
