import re


class SignupPage:
    """The profile form a brand new number lands on after verifying its OTP.

    Board, Class and Course refresh each other, so they have to be chosen in
    that order and their options re-read after every choice.
    """

    URL = "https://eduport-react.pages.dev/signup"

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def get_page(self):
        return self.page.locator(".sp-page")

    def get_form(self):
        return self.page.locator(".sp-form")

    def get_fields(self):
        return self.page.locator(".sp-field")

    def get_labels(self):
        return self.page.locator(".sp-label")

    def get_field(self, label):
        """Exact label match, so "Class" does not also hit "Class 11 Science"."""
        pattern = re.compile(r"^\s*" + re.escape(label) + r"\s*$")
        return self.get_fields().filter(
            has=self.page.locator(".sp-label").filter(has_text=pattern)
        )

    # ---------- avatar ----------

    def get_avatars(self):
        return self.page.locator(".sp-avatar-option")

    def get_current_avatar(self):
        return self.page.locator(".sp-current-avatar")

    def choose_avatar(self, index):
        self.get_avatars().nth(index).click()

    # ---------- text fields ----------

    def get_full_name_input(self):
        return self.page.get_by_placeholder("Enter full name")

    def enter_full_name(self, name):
        self.get_full_name_input().fill(name)

    def get_date_of_birth_input(self):
        return self.page.locator("input[type='date']")

    def enter_date_of_birth(self, date_of_birth):
        self.get_date_of_birth_input().fill(date_of_birth)

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

    def select_option(self, label, option_text):
        """Options carry stray whitespace, so match on the trimmed text."""
        options = self.get_options(label)
        for index in range(options.count()):
            option = options.nth(index)
            if option.inner_text().strip() == option_text:
                self.get_select(label).select_option(option.get_attribute("value"))
                return option_text
        raise AssertionError(f"{label} has no option {option_text!r}")

    def select_first_option(self, label):
        """Pick the first real choice and hand back exactly what was selected,
        so the caller can assert against it later."""
        options = self.get_options(label)
        for index in range(options.count()):
            option = options.nth(index)
            text = option.inner_text().strip()
            value = option.get_attribute("value")
            if text and value:
                self.get_select(label).select_option(value)
                return text
        raise AssertionError(f"{label} has no selectable option")

    def get_selected_option(self, label):
        select = self.get_select(label)
        value = select.input_value()
        return select.locator(f"option[value='{value}']").inner_text().strip()

    # ---------- gender / board / class / course ----------

    def get_gender_select(self):
        return self.get_select("Gender")

    def get_board_select(self):
        return self.get_select("Board")

    def get_class_select(self):
        return self.get_select("Class")

    def get_course_select(self):
        return self.get_select("Course")

    def get_course_options(self):
        return self.get_option_texts("Course")

    def select_course(self, course_name):
        return self.select_option("Course", course_name)

    # ---------- submit ----------

    def get_continue_button(self):
        return self.page.locator(".sp-cta")

    def click_continue(self):
        self.get_continue_button().click()
