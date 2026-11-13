import re


class OtpPage:
    """The OTP screen: four boxes that verify themselves.

    The code is four single-digit boxes rather than one field, and they take
    real keystrokes - focus walks to the next box on a digit and back on a
    backspace. There is no button to press: the form posts the moment the
    fourth digit lands, so a full code is a submission. The visible
    "Verify & Continue" is a status button and stays disabled throughout.

    Resend is time gated. A countdown runs first ("Resend in (0:27s)"); only
    once it reaches zero does a single "Resend OTP" button appear. That button
    sends nothing itself: it raises a "Resend OTP via" sheet offering SMS or
    WhatsApp, and the code goes out when one of the two is chosen.
    """

    URL = "https://eduport-react.pages.dev/otp"

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def get_title(self):
        return self.page.locator(".otp-title")

    def get_subtitle(self):
        return self.page.locator(".otp-subtitle")

    def wait_for_loaded(self, timeout=30000):
        self.get_boxes().first.wait_for(timeout=timeout)

    def get_phone_badge(self):
        """Reads back the number the code was sent to, e.g. "+91 6350039849"."""
        return self.page.locator(".otp-phone-badge")

    def click_phone_badge(self):
        """The badge is a button: it goes back to the login screen so the
        number can be corrected, carrying the number with it."""
        self.get_phone_badge().click()

    # ---------- the code ----------

    def get_boxes(self):
        return self.page.locator(".otp-box")

    def box_count(self):
        return self.get_boxes().count()

    def get_box_values(self):
        return self.get_boxes().evaluate_all("boxes => boxes.map(b => b.value)")

    def enter_otp(self, otp):
        """Type the code the way a person does: focus the first box and let each
        keystroke fall into whichever box has focus.

        Filling the boxes directly does not drive the component - the value is
        set but the app never sees the change - so the keyboard is used."""
        self.get_boxes().first.wait_for()
        self.get_boxes().first.click()
        self.page.keyboard.type(otp)

    def type_digit(self, digit):
        self.page.keyboard.type(digit)

    def get_inputs_row(self):
        """The row of boxes. Paste is handled here rather than on a box, so a
        code pasted anywhere in the row fills all four."""
        return self.page.locator(".otp-inputs")

    def paste_otp(self, text):
        """Paste a code the way a person does off an SMS.

        The clipboard is not driven through the browser's own paste - that
        needs permissions the run does not have - so the paste event is raised
        on the row with the text on it, which is what the screen listens for."""
        self.get_boxes().first.wait_for()
        self.get_inputs_row().evaluate(
            """(row, text) => {
                const data = new DataTransfer();
                data.setData('text', text);
                row.dispatchEvent(new ClipboardEvent('paste', {
                    clipboardData: data,
                    bubbles: true,
                    cancelable: true,
                }));
            }""",
            text,
        )

    def press_backspace(self):
        self.page.keyboard.press("Backspace")

    def focused_box_index(self):
        """Which box currently has focus, or -1 when none does."""
        return self.page.evaluate(
            "() => [...document.querySelectorAll('.otp-box')]"
            ".indexOf(document.activeElement)"
        )

    # ---------- help ----------

    def get_help_button(self):
        """The same Help button the login screen carries, in the same corner."""
        return self.page.locator(".dl-help-btn")

    def click_help(self):
        self.get_help_button().click()

    def get_contact_sheet(self):
        return self.page.locator(".cu-overlay")

    # ---------- status button ----------

    def get_verify_button(self):
        return self.page.locator(".dl-primary-btn")

    def get_continue_button(self):
        """Kept under its old name for callers; the label is now
        "Verify & Continue" and it is never the thing that submits."""
        return self.get_verify_button()

    # ---------- resend ----------

    def get_resend_row(self):
        return self.page.locator(".otp-resend")

    def get_resend_timer(self):
        """The countdown, drawn "(0:27s)" while resend is still locked."""
        return self.page.locator(".otp-resend b")

    def resend_seconds_left(self):
        """Seconds still on the countdown, or 0 once it has run out."""
        timer = self.get_resend_timer()
        if not timer.count():
            return 0
        match = re.search(r"(\d+):(\d+)", timer.inner_text())
        if not match:
            return 0
        return int(match.group(1)) * 60 + int(match.group(2))

    def get_resend_button(self):
        return self.page.locator(".otp-resend-btn")

    def resend_available(self, timeout=40000):
        """Wait out the countdown and report whether Resend OTP has appeared."""
        try:
            self.get_resend_button().wait_for(timeout=timeout)
        except Exception:
            return False
        return True

    def click_resend(self):
        self.get_resend_button().click()

    def get_resend_sheet(self):
        return self.page.locator(".ors-sheet")

    def get_resend_sheet_title(self):
        return self.page.locator(".ors-title")

    def get_resend_option(self, channel):
        """channel is "SMS" or "WhatsApp", as the sheet names them."""
        return self.page.locator(".ors-option").filter(has_text=f"Get OTP via {channel}")

    def choose_resend_channel(self, channel):
        self.get_resend_option(channel).click()

    # ---------- feedback ----------

    def get_invalid_otp_message(self):
        """A wrong code clears the boxes and raises a toast rather than showing
        inline text; the wording is unchanged."""
        return self.page.get_by_text("Invalid OTP. Please try again.")
