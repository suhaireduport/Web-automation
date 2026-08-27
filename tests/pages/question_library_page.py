import re


class QuestionLibraryPage:
    """The Question Library landing screen.

    Four section cards over a list of subjects, with an Info button in the
    header that opens a "How it works?" dialog.
    """

    URL = "https://eduport-react.pages.dev/home/questionLibrary"

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def get_page(self):
        return self.page.locator(".ql-page")

    def get_header(self):
        return self.page.locator(".ql-header")

    def get_title(self):
        return self.page.locator(".ql-title")

    def wait_for_loaded(self):
        """The counts arrive with the page, so a card is the signal that the
        screen is ready rather than just routed to."""
        self.get_cards().first.wait_for()

    # ---------- header ----------

    def get_back_button(self):
        return self.page.locator(".ql-icon-btn[aria-label='Back']")

    def click_back(self):
        self.get_back_button().click()

    def get_info_button(self):
        return self.page.locator(".ql-icon-btn[aria-label='Info']")

    def click_info(self):
        self.get_info_button().click()

    # ---------- section cards ----------

    def get_cards(self):
        return self.page.locator(".ql-card")

    def get_card(self, title):
        """Exact title match, so "Bookmarks" does not also hit a longer name."""
        pattern = re.compile(r"^\s*" + re.escape(title) + r"\s*$")
        return self.get_cards().filter(
            has=self.page.locator(".ql-card-title").filter(has_text=pattern)
        )

    def get_card_titles(self):
        return self.page.locator(".ql-card-title")

    def get_card_title_texts(self):
        return [text.strip() for text in self.get_card_titles().all_inner_texts()]

    def get_card_count(self, title):
        return self.get_card(title).locator(".ql-card-count")

    def get_card_icon(self, title):
        return self.get_card(title).locator(".ql-card-icon")

    def open_card(self, title):
        self.get_card(title).click()

    # ---------- subjects ----------

    def get_subjects_section_title(self):
        return self.page.locator(".ql-section-title")

    def get_subject_cards(self):
        return self.page.locator(".ql-subject-card")

    def get_subject_names(self):
        return self.page.locator(".ql-subject-name")

    def get_subject_counts(self):
        return self.page.locator(".ql-subject-count")

    def subject_count(self, timeout=10000):
        """count() does not auto-wait, and the subjects arrive with the page."""
        try:
            self.get_subject_cards().first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_subject_cards().count()

    # ---------- how it works dialog ----------

    def get_info_dialog(self):
        return self.page.locator(".qlh-overlay")

    def get_info_sheet(self):
        return self.page.locator(".qlh-sheet")

    def get_info_title(self):
        return self.page.locator(".qlh-title")

    def get_info_close_button(self):
        return self.page.locator(".qlh-close")

    def close_info(self):
        self.get_info_close_button().click()

    def get_info_cards(self):
        return self.page.locator(".qlh-card")

    def get_info_card_titles(self):
        return self.page.locator(".qlh-card-title")

    def get_info_card_title_texts(self):
        return [text.strip() for text in self.get_info_card_titles().all_inner_texts()]

    def get_info_card_descriptions(self):
        return self.page.locator(".qlh-card-desc")

    def get_info_card(self, title):
        pattern = re.compile(r"^\s*" + re.escape(title) + r"\s*$")
        return self.get_info_cards().filter(
            has=self.page.locator(".qlh-card-title").filter(has_text=pattern)
        )
