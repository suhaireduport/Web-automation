import re


class EditProfilePage:
    """Edit Details, reached from the profile menu.

    Laid out like the signup form but prefilled from the account, with the date
    of birth locked. Saving posts the profile and drops the user back on home.
    """

    URL = "https://eduport-react.pages.dev/profile/edit"

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def get_page(self):
        return self.page.locator(".edp-shell")

    def get_title(self):
        return self.page.locator(".edp-title")

    def get_form(self):
        return self.page.locator(".edp-form")

    def get_back_button(self):
        return self.page.locator(".edp-back")

    def click_back(self):
        self.get_back_button().click()

    def get_save_button(self):
        return self.page.locator(".edp-save-btn")

    def click_save(self):
        self.get_save_button().scroll_into_view_if_needed()
        self.get_save_button().click()

    # ---------- account badges ----------

    def get_badges(self):
        return self.page.locator(".edp-badge")

    def get_phone_badge(self):
        return self.get_badges().nth(0)

    def get_student_id_badge(self):
        return self.get_badges().nth(1)

    # ---------- avatar ----------

    def get_avatars(self):
        return self.page.locator(".edp-avatar-option")

    def get_current_avatar(self):
        return self.page.locator(".edp-current-avatar")

    def choose_avatar(self, index):
        self.get_avatars().nth(index).click()

    # ---------- fields ----------

    def get_fields(self):
        return self.page.locator(".edp-field")

    def get_field(self, label):
        """Exact label match, so "Class" does not also hit "Class 11 Science"."""
        pattern = re.compile(r"^\s*" + re.escape(label) + r"\s*$")
        return self.get_fields().filter(
            has=self.page.locator(".edp-label").filter(has_text=pattern)
        )

    def scroll_to_field(self, label):
        """The form runs past the fold, so bring a field into view before using
        it. Selects in particular sit below the visible area on a short window."""
        self.get_field(label).scroll_into_view_if_needed()

    def get_full_name_input(self):
        return self.get_field("Full name").locator("input")

    def get_full_name(self):
        return self.get_full_name_input().input_value()

    def enter_full_name(self, name):
        self.scroll_to_field("Full name")
        self.get_full_name_input().fill(name)

    def get_date_of_birth_input(self):
        return self.get_field("Date of Birth").locator("input")

    # ---------- dropdowns ----------

    def get_select(self, label):
        return self.get_field(label).locator("select")

    def get_options(self, label):
        return self.get_select(label).locator("option")

    def get_option_texts(self, label):
        return [
            text.strip()
            for text in self.get_options(label).all_inner_texts()
            if text.strip()
        ]

    def get_selected_option(self, label):
        select = self.get_select(label)
        value = select.input_value()
        return select.locator(f"option[value='{value}']").inner_text().strip()

    def select_option(self, label, option_text):
        """Options carry stray whitespace, so match on the trimmed text."""
        self.scroll_to_field(label)
        options = self.get_options(label)
        for index in range(options.count()):
            option = options.nth(index)
            if option.inner_text().strip() == option_text:
                self.get_select(label).select_option(option.get_attribute("value"))
                return option_text
        raise AssertionError(f"{label} has no option {option_text!r}")

    def select_other_option(self, label):
        """Move to any choice other than the current one and return it."""
        self.scroll_to_field(label)
        select = self.get_select(label)
        current = select.input_value()
        options = self.get_options(label)
        for index in range(options.count()):
            option = options.nth(index)
            value = option.get_attribute("value")
            text = option.inner_text().strip()
            if value and value != current and text:
                select.select_option(value)
                return text
        raise AssertionError(f"{label} has no alternative to choose")

    # ---------- named dropdowns ----------

    def get_gender_select(self):
        return self.get_select("Gender")

    def get_board_select(self):
        return self.get_select("Board")

    def get_class_select(self):
        return self.get_select("Class")

    def get_course_select(self):
        return self.get_select("Course")

    def get_current_course(self):
        return self.get_selected_option("Course")

    def get_course_options(self):
        return self.get_option_texts("Course")

    def select_course(self, course_name):
        return self.select_option("Course", course_name)
