import re

from pages.question_library_section_page import (
    SectionQuestionsPage,
    SectionQuestionPage,
)


class SubjectPage:
    """A subject of the Question Library.

    Reached from the subject list under the four section cards. It lists the
    chapters of that subject the account has attempted questions in, each with
    how many questions it holds, how those questions were answered and the
    mastery reached, over a footer that raises the study recommendations.
    """

    URL_PATTERN = re.compile(
        r"https://eduport-react\.pages\.dev/home/questionLibrary/subject/\d+/[^/]+$"
    )

    # The breakdown a chapter card carries. Bookmark is not an answer state:
    # a bookmarked question is also correct, wrong or unknown, so it is counted
    # in two of these rows at once.
    STATUSES = ["Correct", "Wrong", "I don’t know", "Bookmark"]
    ANSWER_STATES = ["Correct", "Wrong", "I don’t know"]

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def get_page(self):
        return self.page.locator(".qlc-page")

    def get_header(self):
        return self.page.locator(".qlc-header")

    def get_title(self):
        return self.page.locator(".qlc-page-title")

    def wait_for_loaded(self):
        """The chapter cards arrive with the page, so one of them is the signal
        that the screen is ready rather than just routed to."""
        self.get_chapters().first.wait_for()

    def get_back_button(self):
        return self.page.locator(".qlc-icon-btn[aria-label='Back']")

    def click_back(self):
        self.get_back_button().click()

    def get_search_button(self):
        return self.page.locator(".qlc-icon-btn[aria-label='Search']")

    def click_search(self):
        self.get_search_button().click()

    # ---------- chapters ----------

    def get_chapters(self):
        return self.page.locator(".qlc-card")

    def get_chapter(self, index):
        return self.get_chapters().nth(index)

    def chapter_count(self, timeout=10000):
        """count() does not auto-wait, and the chapters arrive with the page."""
        try:
            self.get_chapters().first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_chapters().count()

    def get_chapter_numbers(self):
        return self.page.locator(".qlc-num")

    def get_chapter_titles(self):
        return self.page.locator(".qlc-title")

    def get_chapter_title(self, index):
        return self.get_chapter(index).locator(".qlc-title")

    def get_chapter_title_text(self, index):
        """The chapter name without the number the card prints in front of it,
        which is where the rest of the app gives the same chapter unnumbered."""
        return re.sub(
            r"^\s*\d+\s*\.\s*", "", self.get_chapter_title(index).inner_text()
        ).strip()

    def get_chapter_question_count(self, index):
        """How many attempted questions of the subject this chapter holds."""
        return self.get_chapter(index).locator(".qlc-question-count")

    def get_chapter_question_total(self, index):
        return int(self.get_chapter_question_count(index).inner_text().strip())

    def question_total(self):
        """Every chapter of the subject added up."""
        return sum(
            self.get_chapter_question_total(index)
            for index in range(self.chapter_count())
        )

    def open_chapter(self, index):
        self.get_chapter(index).click()

    # ---------- answer state breakdown ----------

    def get_statuses(self, index):
        return self.get_chapter(index).locator(".qlc-status")

    def get_status_labels(self, index):
        return self.get_chapter(index).locator(".qlc-status-label")

    def get_status_names(self, index):
        """Labels read "Correct (7)", so drop the count."""
        return [
            re.sub(r"\s*\(\d+\)\s*$", "", text).strip()
            for text in self.get_status_labels(index).all_inner_texts()
        ]

    def get_status_label(self, index, name):
        return self.get_status_labels(index).filter(
            has_text=re.compile(r"^\s*" + re.escape(name) + r"\s*\(")
        )

    def get_status_count(self, index, name):
        return int(
            re.search(r"\((\d+)\)", self.get_status_label(index, name).inner_text()).group(1)
        )

    def get_status_dots(self, index):
        return self.get_chapter(index).locator(".qlc-status-dot")

    # ---------- mastery ----------

    def get_mastery(self, index):
        return self.get_chapter(index).locator(".qlc-mastery")

    def get_mastery_value(self, index):
        return self.get_chapter(index).locator(".qlc-mastery-value")

    # ---------- study recommendations ----------

    def get_footer(self):
        return self.page.locator(".qlc-footer")

    def get_recommendations_button(self):
        return self.page.locator(".qlc-recommend")

    def click_recommendations(self):
        self.get_recommendations_button().click()


class SubjectSearchPage:
    """The chapter search a subject opens.

    The same screen the Question Library sections reach through their own
    search button, so it counts every question of a chapter rather than only
    the ones already attempted.
    """

    URL_PATTERN = re.compile(
        r"https://eduport-react\.pages\.dev/home/questionLibrary/subject/\d+/[^/]+/search$"
    )

    def __init__(self, page):
        self.page = page

    def get_page(self):
        return self.page.locator(".qlcs-page")

    def wait_for_loaded(self):
        """The screen fetches the subject's chapters for itself, and starts out
        with nothing on it while it does."""
        self.page.locator(".qlcs-card, .qlcs-no-result").first.wait_for()

    def get_back_button(self):
        return self.page.locator(".qlcs-icon-btn[aria-label='Back']")

    def get_search_input(self):
        return self.page.locator(".qlcs-input")

    def search(self, text):
        self.get_search_input().fill(text)

    def get_results(self):
        return self.page.locator(".qlcs-card")

    def get_result_titles(self):
        return self.page.locator(".qlcs-title")

    def get_result_title_texts(self):
        return [text.strip() for text in self.get_result_titles().all_inner_texts()]

    def get_no_result(self):
        return self.page.locator(".qlcs-no-result")

    def get_no_result_title(self):
        return self.page.locator(".qlcs-no-result-title")


class StudyRecommendationsSheet:
    """The sheet the Study Recommendations button raises.

    One card per chapter whose mastery is low, each naming how many of its
    subtopics are behind, the study rate reached, and a button that carries the
    student straight into a practice on that chapter.
    """

    def __init__(self, page):
        self.page = page

    def get_overlay(self):
        return self.page.locator(".srs-overlay")

    def get_sheet(self):
        return self.page.locator(".srs-sheet")

    def wait_for_loaded(self):
        self.get_cards().first.wait_for()

    def get_title(self):
        return self.page.locator(".srs-title")

    def get_subtitle(self):
        return self.page.locator(".srs-subtitle")

    # ---------- cards ----------

    def get_cards(self):
        return self.page.locator(".srs-card")

    def get_card(self, index):
        return self.get_cards().nth(index)

    def card_count(self, timeout=10000):
        try:
            self.get_cards().first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_cards().count()

    def get_card_number(self, index):
        return self.get_card(index).locator(".srs-card-num")

    def get_card_title(self, index):
        return self.get_card(index).locator(".srs-card-title")

    def get_card_title_text(self, index):
        return self.get_card_title(index).inner_text().strip()

    # ---------- subtopics and study rate ----------

    def get_status_pill(self, index):
        return self.get_card(index).locator(".srs-status-pill")

    def get_subtopic_count(self, index):
        """The pill reads "17 Subtopics are in Poor 4%"."""
        return int(re.search(r"(\d+)", self.get_status_pill(index).inner_text()).group(1))

    def get_study_rate(self, index):
        """The rate the pill ends on, which the sheet colours by how bad it is:
        "Poor 4%"."""
        return self.get_card(index).locator(".srs-status-strong")

    def get_study_rate_text(self, index):
        return self.get_study_rate(index).inner_text().strip()

    # ---------- practice ----------

    def get_practice_buttons(self):
        return self.page.locator(".srs-practice")

    def get_practice_button(self, index):
        return self.get_card(index).locator(".srs-practice")

    def click_practice(self, index=0):
        self.get_practice_button(index).click()


class SubjectQuestionsPage(SectionQuestionsPage):
    """The attempted questions of one chapter of a subject.

    The same screen the sections open, but reached without a section filter, so
    it carries the answer state tabs a section hides.
    """

    # The tabs, in the order the screen shows them, and the class each one
    # carries. The tab text is matched by class rather than by name because the
    # apostrophe in "I don't know" is a typographic one.
    TABS = ["All", "Correct", "Wrong", "I don’t know", "Bookmark"]
    TAB_CLASSES = {
        "All": "qq-tab-all",
        "Correct": "qq-tab-correct",
        "Wrong": "qq-tab-wrong",
        "I don’t know": "qq-tab-idk",
        "Bookmark": "qq-tab-bookmark",
    }

    def get_tabs_bar(self):
        return self.page.locator(".qq-tabs-bar")

    def get_tab(self, name):
        return self.page.locator(f".qq-tab.{self.TAB_CLASSES[name]}")

    def get_tab_names(self):
        """Tabs read "Correct (7)", so drop the count."""
        return [
            re.sub(r"\s*\(\s*\d+\s*\)\s*$", "", text).strip()
            for text in self.get_state_tabs().all_inner_texts()
        ]

    def get_tab_count(self, name):
        return int(re.search(r"\(\s*(\d+)\s*\)", self.get_tab(name).inner_text()).group(1))

    def get_active_tab_name(self):
        return re.sub(
            r"\s*\(\s*\d+\s*\)\s*$", "", self.get_active_state_tab().inner_text()
        ).strip()

    def open_tab(self, name):
        """The list is re-fetched, and a tab that matches nothing swaps it for
        the empty state, so either of those is the signal it has come back."""
        self.get_tab(name).click()
        self.page.locator(".qq-card, .qq-empty").first.wait_for()

    def get_empty_state(self):
        return self.page.locator(".qq-empty")


class SubjectQuestionPage(SectionQuestionPage):
    """A single question opened from a subject chapter."""

    URL_PATTERN = re.compile(
        r"https://eduport-react\.pages\.dev/home/questionLibrary/subject/\d+/.+/chapter/\d+/.+/question/\d+.*"
    )
