import re


class SignupPage:
    """The new-user wizard a brand new number lands on after verifying its OTP.

    It is three steps on one route (/new-user), each a ``.nu-step`` that
    replaces the one before it:

      1. Enter Your Details - full name and a gender pill. Save & Continue
         stays disabled until both are given.
      2. Choose Your Class  - a searchable list of classes; tapping one expands
         it to its courses, and Confirm Class stays disabled until a course is
         picked. The list is drawn from courses_list and premium_courses.
      3. Choose Avatar      - a carousel of stock avatars and avatar packs. Skip
         completes the signup with the default avatar; the account is created by
         a single POST to profile/update.

    The old single /signup form - date of birth, an avatar grid and Board /
    Class / Course dropdowns - is gone, and with it the ``.sp-*`` markup.
    """

    URL = "https://eduport-react.pages.dev/new-user"

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def get_step(self):
        return self.page.locator(".nu-step")

    def get_title(self):
        """The heading of whichever step is showing."""
        return self.page.locator(".nu-title")

    def wait_for_loaded(self, timeout=30000):
        self.get_step().wait_for(timeout=timeout)

    # ---------- step 1: details ----------

    def get_name_input(self):
        return self.page.locator(".nu-name-input")

    def enter_name(self, name):
        self.get_name_input().fill(name)

    def get_gender_pills(self):
        return self.page.locator(".nu-gender-pill")

    def get_selected_gender_pills(self):
        return self.page.locator(".nu-gender-pill--selected")

    def choose_gender(self, label):
        """Pick a gender. Matched exactly because "Female" carries "male" as a
        substring, so a loose match would hit both pills."""
        self.page.get_by_role("button", name=label, exact=True).click()

    def get_selected_gender(self):
        """The label of the chosen pill, or None while none is chosen."""
        pill = self.page.locator(".nu-gender-pill--selected")
        if not pill.count():
            return None
        return pill.locator(".nu-gender-label").inner_text().strip()

    def get_details_cta(self):
        """Save & Continue, at the foot of step one."""
        return self.page.locator(".nu-cta-bar button")

    def details_cta_enabled(self):
        return not self.get_details_cta().is_disabled()

    def submit_details(self):
        self.get_details_cta().click()

    # ---------- step 2: class and course ----------

    def get_class_search(self):
        return self.page.locator(".nu-search input")

    def search_class(self, text):
        self.get_class_search().fill(text)

    def get_class_rows(self):
        return self.page.locator(".nu-class-row")

    def get_class_names(self):
        return [name.strip() for name in self.page.locator(".nu-class-name").all_inner_texts()]

    def get_class_tile(self, name):
        """Exact match on the class name, so "Class 1" does not also hit
        "Class 10"."""
        pattern = re.compile(r"^\s*" + re.escape(name) + r"\s*$")
        return self.get_class_rows().filter(
            has=self.page.locator(".nu-class-name").filter(has_text=pattern)
        )

    def expand_class(self, name):
        """Open a class to reveal its courses."""
        self.get_class_tile(name).first.click()

    def get_course_tiles(self):
        """The course buttons revealed under an expanded class."""
        return self.page.locator(".nu-course-tile")

    def get_course_names(self):
        return [name.strip() for name in self.get_course_tiles().all_inner_texts()]

    def choose_course(self, title):
        pattern = re.compile(r"^\s*" + re.escape(title) + r"\s*$")
        self.get_course_tiles().filter(has_text=pattern).first.click()

    def get_selected_course(self):
        tile = self.page.locator(".nu-course-tile--selected")
        if not tile.count():
            return None
        return tile.inner_text().strip()

    def get_confirm_class_button(self):
        return self.page.locator(".nu-class-foot button")

    def confirm_class_enabled(self):
        return not self.get_confirm_class_button().is_disabled()

    def confirm_class(self):
        self.get_confirm_class_button().click()

    def get_class_back_button(self):
        return self.page.locator(".nu-class-head button")

    # ---------- step 3: avatar ----------

    def get_avatar_carousel(self):
        return self.page.locator(".nu-carousel")

    def get_avatar_items(self):
        return self.page.locator(".nu-carousel-item")

    def get_avatar_names(self):
        return [name.strip() for name in self.page.locator(".nu-carousel-name").all_inner_texts()]

    def get_active_avatar_name(self):
        return self.page.locator(".nu-carousel-item--active .nu-carousel-name").inner_text().strip()

    def choose_avatar(self, name):
        pattern = re.compile(r"^\s*" + re.escape(name) + r"\s*$")
        self.get_avatar_items().filter(has_text=pattern).first.click()

    def get_avatar_packs(self):
        return self.page.locator(".nu-pack-tile")

    def get_set_profile_button(self):
        return self.page.locator(".nu-avatar-cta")

    def set_profile(self):
        self.get_set_profile_button().click()

    def get_skip_button(self):
        return self.page.get_by_text("Skip", exact=True)

    def skip(self):
        self.get_skip_button().click()
