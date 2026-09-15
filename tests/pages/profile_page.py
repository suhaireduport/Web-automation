import re


class ProfilePage:
    """The Profile page behind the home avatar.

    The avatar in the home header no longer drops a popup menu; it opens this
    full page at /profile. The hero across the top carries the account - name,
    number, avatar, join date, leaderboard rank and coin balance - drawn from
    the home call the page makes on load, over a row of stat tiles drawn from a
    profile analysis call. Below the hero sit a study reminder, a grid of
    settings cards and a grid of help cards, then Sign Out and a footer.

    Three of the cards open a sheet over the page rather than routing anywhere:
    My Account is a small editable form (name, gender, a locked date of birth),
    Help Center is a hosted form in an iframe, and WhatsApp and Contact Us both
    open the same contact sheet. Call My Mentor dials rather than navigating.

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

    def wait_for_account_ready(self, timeout=30000):
        """Wait for the home call behind the page to answer.

        The hero is drawn from the copy of the account kept in the browser, so
        it is up well before that call is in. The join date is the one line on
        it with no cached source, so it reading as anything but a dash is the
        signal that the call has landed - which the My Account sheet needs,
        because the course it posts when saving comes from that payload and is
        zero until then."""
        self.page.wait_for_function(
            "() => { const line = document.querySelector('.pp-joined');"
            " return line && !line.textContent.includes('--'); }",
            timeout=timeout,
        )

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

    def get_avatar_image(self):
        return self.get_avatar().locator("img")

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

    def get_reminder_title(self):
        return self.page.locator(".pp-reminder-title")

    def get_reminder_hint(self):
        return self.page.locator(".pp-reminder-input")

    def get_reminder_switch(self):
        return self.page.locator(".pp-switch")

    def is_reminder_on(self):
        return self.get_reminder_switch().get_attribute("aria-checked") == "true"

    def toggle_reminder(self):
        self.get_reminder_switch().click()

    def set_reminder(self, on):
        """Put the switch in a given position, whichever it is in now.

        Used to put the setting back: the switch is remembered between loads,
        so a test that turns it on has to turn it off again."""
        if self.is_reminder_on() != on:
            self.toggle_reminder()

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

    def get_sign_out_body(self):
        return self.page.locator(".pp-signout-dialog-body")

    def dismiss_sign_out_outside(self):
        """Tap the backdrop rather than No. The dialog sits in the middle of the
        overlay, so the click is aimed at a corner of it."""
        self.get_sign_out_overlay().click(position={"x": 5, "y": 5})

    def confirm_sign_out(self):
        self.get_sign_out_confirm().click()

    def cancel_sign_out(self):
        self.get_sign_out_cancel().click()

    # ---------- footer ----------

    def get_footer_links(self):
        return self.page.locator(".pp-footer-links")

    def click_footer_links(self):
        self.get_footer_links().click()

    def get_footer_build(self):
        return self.page.locator(".pp-footer-dev")

    # ---------- My Account sheet ----------
    #
    # The My Account card does not route anywhere; it raises a sheet over the
    # page holding a short form. Name and gender can be changed and saved
    # through profile/update; the date of birth is shown but locked.

    def open_my_account(self):
        """Open the sheet and wait for it to be worth typing into.

        The form is filled in from the account a moment after the sheet is up,
        late enough to overwrite anything typed first - the same wait Edit
        Details needs."""
        self.wait_for_account_ready()
        self.click_card("My Account")
        self.get_account_sheet().wait_for()
        self.page.wait_for_function(
            "() => { const box = document.querySelector('.ma-input');"
            " return box && box.value !== ''; }"
        )

    def get_account_overlay(self):
        return self.page.locator(".ma-overlay")

    def get_account_sheet(self):
        return self.page.locator(".ma-sheet")

    def get_account_title(self):
        return self.page.locator(".ma-title")

    def get_account_name_input(self):
        return self.page.locator(".ma-input")

    def get_account_name(self):
        return self.get_account_name_input().input_value()

    def enter_account_name(self, name):
        self.get_account_name_input().fill(name)

    def get_account_genders(self):
        return self.page.locator(".ma-gender")

    def get_account_gender_names(self):
        return [t.strip() for t in self.get_account_genders().all_inner_texts()]

    def get_selected_gender(self):
        return self.page.locator(".ma-gender--selected").inner_text().strip()

    def get_account_dob_fields(self):
        return self.page.locator(".ma-dob")

    def get_account_dob_selects(self):
        return self.page.locator(".ma-dob-native")

    def get_account_save(self):
        return self.page.locator(".ma-save")

    def account_save_is_armed(self):
        """Save only lights up once something on the form has been changed."""
        return "ma-save--active" in (self.get_account_save().get_attribute("class") or "")

    def save_account(self):
        self.get_account_save().click()

    def get_account_exit(self):
        return self.page.locator(".ma-exit")

    def exit_account_without_saving(self):
        self.get_account_exit().click()

    def close_account_from_outside(self):
        self.get_account_overlay().click(position={"x": 5, "y": 5})

    # ---------- Help Center sheet ----------

    def open_help_center(self):
        self.click_card("Help Center")
        self.get_help_panel().wait_for()

    def get_help_overlay(self):
        return self.page.locator(".hc-overlay")

    def get_help_panel(self):
        return self.page.locator(".hc-panel")

    def get_help_iframe(self):
        return self.page.locator(".hc-iframe")

    def get_help_close(self):
        return self.page.locator(".hc-close")

    def close_help_center(self):
        self.get_help_close().click()

    # ---------- Contact sheet ----------
    #
    # Reached from either of two cards: WhatsApp and Contact Us both raise it.

    def open_contact_sheet(self, card="Contact Us"):
        self.click_card(card)
        self.get_contact_sheet().wait_for()
        # The options arrive with the sheet animating in, and reading their text
        # does not wait, so settle on the first one being up.
        self.get_contact_options().first.wait_for()

    def get_contact_overlay(self):
        return self.page.locator(".cu-overlay")

    def get_contact_sheet(self):
        return self.page.locator(".cu-sheet")

    def get_contact_title(self):
        return self.page.locator(".cu-title")

    def get_contact_options(self):
        return self.page.locator(".cu-option")

    def get_contact_option_labels(self):
        return [t.strip() for t in self.page.locator(".cu-option-label").all_inner_texts()]
