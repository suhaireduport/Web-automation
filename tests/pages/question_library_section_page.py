import re

BASE_URL = "https://eduport-react.pages.dev"


class SectionPage:
    """The chapter list of a Question Library section.

    My Notes, Bookmarks and Mistake Book are the same screen served with a
    different qlType: subject tabs over a list of chapters, or an empty state
    when the account holds nothing in that section. Each section subclasses
    this with its own URL.
    """

    URL = f"{BASE_URL}/home/questionLibrary/contents"

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def get_page(self):
        return self.page.locator(".qlx-page")

    def get_header(self):
        return self.page.locator(".qlx-header")

    def get_title(self):
        return self.page.locator(".qlx-title-text")

    def wait_for_loaded(self):
        """Either the chapter list or the empty state shows up once loaded."""
        self.page.locator(".qlx-list, .qlx-no-data").first.wait_for()

    def get_back_button(self):
        return self.page.locator(".qlx-icon-btn[aria-label='Back']")

    def click_back(self):
        self.get_back_button().click()

    def get_search_button(self):
        return self.page.locator(".qlx-icon-btn[aria-label='Search']")

    def click_search(self):
        self.get_search_button().click()

    # ---------- empty state ----------

    def get_empty_state(self):
        return self.page.locator(".qlx-no-data")

    def get_empty_message(self):
        return self.page.locator(".qlx-no-data-msg")

    def has_questions(self):
        return self.get_empty_state().count() == 0

    # ---------- subject tabs ----------

    def get_tabs(self):
        return self.page.locator(".qlx-tab")

    def get_tab(self, subject):
        """Tabs read "Chemistry (1)", so match the name at the start."""
        return self.get_tabs().filter(has_text=re.compile("^" + re.escape(subject)))

    def get_active_tab(self):
        return self.page.locator(".qlx-tab-active")

    def get_tab_names(self):
        """The subject names alone, without the count they carry."""
        return [
            re.sub(r"\s*\(\d+\)\s*$", "", text).strip()
            for text in self.get_tabs().all_inner_texts()
        ]

    def click_tab(self, index):
        self.get_tabs().nth(index).click()

    def open_subject(self, subject):
        self.get_tab(subject).click()
        self.page.locator(".qlx-card").first.wait_for()

    def get_tab_count(self, index):
        """The number in brackets on a tab, which counts chapters, not
        questions: a subject with one chapter holding four bookmarks reads
        "Chemistry (1)"."""
        return int(re.search(r"\((\d+)\)", self.get_tabs().nth(index).inner_text()).group(1))

    # ---------- chapters ----------

    def get_chapters(self):
        return self.page.locator(".qlx-card")

    def get_chapter(self, index):
        return self.get_chapters().nth(index)

    def chapter_count(self, timeout=10000):
        """count() does not auto-wait, and switching tabs re-fetches the list."""
        try:
            self.get_chapters().first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_chapters().count()

    def get_chapter_numbers(self):
        return self.page.locator(".qlx-num")

    def get_chapter_titles(self):
        return self.page.locator(".qlx-title")

    def get_chapter_title_texts(self):
        return [text.strip() for text in self.get_chapter_titles().all_inner_texts()]

    def get_chapter_by_title(self, title):
        """Chapter titles here are numbered - "1. Some Basic Concepts of
        Chemistry" - where the rest of the app gives the same chapter without
        its number, so the title is matched as part of the card, not as all
        of it."""
        return self.get_chapters().filter(has_text=title.strip())

    def find_chapter(self, title):
        """Position of that chapter in the list, or None."""
        wanted = title.strip()
        for index, listed in enumerate(self.get_chapter_title_texts()):
            if wanted in listed:
                return index
        return None

    def get_chapter_question_count(self, index):
        """How many of the section's questions this chapter holds."""
        return self.get_chapter(index).locator(".qlx-question-count")

    def chapter_question_total(self):
        """Every chapter of the subject on screen added up."""
        return sum(
            int(self.get_chapter_question_count(index).inner_text().strip())
            for index in range(self.chapter_count())
        )

    def get_chapter_mastery(self, index):
        return self.get_chapter(index).locator(".qlx-mastery")

    def open_chapter(self, index):
        self.get_chapter(index).click()

    # ---------- chapter search ----------
    # Search leaves the section behind: it opens the subject's own chapter
    # search, which counts every question of a chapter rather than only the
    # ones the section holds.

    def get_search_input(self):
        return self.page.locator(".qlcs-input")

    def wait_for_search_loaded(self):
        """The search screen fetches the subject's chapters for itself, and
        starts out with nothing on it while it does."""
        self.page.locator(".qlcs-card, .qlcs-no-result").first.wait_for()

    def search(self, text):
        self.get_search_input().fill(text)

    def get_search_results(self):
        return self.page.locator(".qlcs-card")

    def get_search_result_titles(self):
        return self.page.locator(".qlcs-title")

    def get_search_clear_button(self):
        return self.page.locator(".qlcs-clear-btn")

    def clear_search(self):
        self.get_search_clear_button().click()

    def get_no_search_result(self):
        return self.page.locator(".qlcs-no-result")

    def get_no_search_result_title(self):
        return self.page.locator(".qlcs-no-result-title")


class SectionQuestionsPage:
    """The questions one chapter holds in a section.

    Reached from a chapter card. The cards carry whatever the section is about:
    the note saved against the question, its bookmark control, and in the
    Mistake Book a control that drops it from the book.
    """

    URL_PATTERN = re.compile(
        r"https://eduport-react\.pages\.dev/home/questionLibrary/subject/\d+/.+/chapter/\d+/.+"
    )

    def __init__(self, page):
        self.page = page

    def get_page(self):
        return self.page.locator(".qq-page")

    def get_title(self):
        return self.page.locator(".qq-page-title")

    def wait_for_loaded(self):
        self.get_questions().first.wait_for()

    def get_back_button(self):
        return self.page.locator(".qq-icon-btn[aria-label='Back']")

    def click_back(self):
        self.get_back_button().click()

    # ---------- search ----------

    def get_search_button(self):
        return self.page.locator(".qq-icon-btn[aria-label='Search']")

    def click_search(self):
        self.get_search_button().click()

    def get_search_input(self):
        return self.page.locator(".qqs-input")

    def search(self, text):
        self.get_search_input().fill(text)

    def get_search_clear_button(self):
        return self.page.locator(".qq-icon-btn[aria-label='Clear search']")

    def get_no_search_result(self):
        return self.page.get_by_text("No Matching Search Result")

    # ---------- topic filter sheet ----------

    def get_filter_button(self):
        return self.page.locator(".qq-filter-btn")

    def click_filter(self):
        self.get_filter_button().click()

    def get_filter_sheet(self):
        return self.page.locator(".qq-sheet")

    def get_filter_overlay(self):
        return self.page.locator(".qq-sheet-overlay")

    def get_filter_title(self):
        return self.page.locator(".qq-sheet-title")

    def get_filter_options(self):
        return self.page.locator(".qq-topic-row")

    def get_filter_option_titles(self):
        return self.page.locator(".qq-topic-title")

    def get_filter_option_names(self):
        return [text.strip() for text in self.get_filter_option_titles().all_inner_texts()]

    def get_filter_apply_button(self):
        return self.page.locator(".qq-sheet-apply")

    def get_filter_clear_button(self):
        return self.page.locator(".qq-sheet-clear")

    def close_filter(self):
        """Escape does not dismiss this sheet, so use its own button."""
        self.page.locator(".qq-sheet-close").click()

    # ---------- answer state tabs ----------
    # Only the plain chapter view carries these; a section opens the same
    # screen with its own filter already applied and no tab bar.

    def get_state_tabs(self):
        return self.page.locator(".qq-tab")

    def get_active_state_tab(self):
        return self.page.locator(".qq-tab-active")

    # ---------- questions ----------

    def get_questions(self):
        return self.page.locator(".qq-card")

    def get_question(self, index):
        return self.get_questions().nth(index)

    def question_count(self, timeout=10000):
        try:
            self.get_questions().first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_questions().count()

    def get_question_numbers(self):
        return self.page.locator(".qq-num")

    def get_question_text(self, index):
        return self.get_question(index).locator(".qq-html").first

    def get_question_texts(self):
        return [normalise(text) for text in self.get_questions().all_inner_texts()]

    def find_question(self, text):
        """Index of the card whose question reads like text, or None.

        Questions are rendered as HTML, so they come back peppered with
        non breaking spaces and line breaks that the practice screen and the
        library render differently; both sides are flattened before matching."""
        wanted = normalise(text)
        for index, listed in enumerate(self.get_question_texts()):
            if wanted and wanted in listed:
                return index
        return None

    def get_note_previews(self):
        return self.page.locator(".qq-note-preview")

    def get_note_preview(self, index):
        return self.get_question(index).locator(".qq-note-preview")

    def get_note_text(self, index):
        return self.get_question(index).locator(".qq-note-text")

    def get_bookmark_buttons(self):
        return self.page.locator(".qq-bookmark-btn")

    def get_bookmark_button(self, index):
        return self.get_question(index).locator(".qq-bookmark-btn")

    def is_bookmarked(self, index):
        return self.get_bookmark_button(index).get_attribute("aria-label") == "Remove bookmark"

    def remove_bookmark(self, index):
        self.get_bookmark_button(index).click()

    def get_remove_buttons(self):
        return self.page.locator(".qq-remove-btn")

    def get_remove_button(self, index):
        return self.get_question(index).locator(".qq-remove-btn")

    def open_question(self, index):
        self.get_question(index).click()

    def get_practice_button(self):
        return self.page.locator(".qq-practice")

    def click_practice(self):
        self.get_practice_button().click()


class SectionQuestionPage:
    """A single question opened from a section: options, note, bookmark, the
    solution and the recent attempts, plus the answer state filter and the
    report sheet."""

    # The filter rows, spelled the way the sheet spells them - the apostrophe in
    # "I don't know" is a typographic one.
    FILTERS = ["All", "Correct", "Wrong", "I don’t know", "Bookmark"]

    def __init__(self, page):
        self.page = page

    def get_page(self):
        return self.page.locator(".qlr-page")

    def wait_for_loaded(self):
        self.get_options().first.wait_for()

    def get_close_button(self):
        return self.page.locator(".qlr-icon-btn[aria-label='Close']")

    def click_close(self):
        self.get_close_button().click()

    # ---------- counter ----------

    def get_counter(self):
        return self.page.locator(".qlr-counter")

    def get_current_number(self):
        return int(self.page.locator(".qlr-counter-cur").inner_text().strip())

    def get_total_number(self):
        return int(self.page.locator(".qlr-counter-tot").inner_text().strip())

    # ---------- question ----------

    def get_question(self):
        return self.page.locator(".qlr-question")

    def get_question_text(self):
        return normalise(self.get_question().inner_text())

    def get_choose_label(self):
        return self.page.locator(".qlr-choose")

    def get_options(self):
        return self.page.locator(".qlr-option")

    def get_option(self, index):
        return self.get_options().nth(index)

    def get_option_numbers(self):
        return self.page.locator(".qlr-opt-num")

    def get_option_texts(self):
        return self.page.locator(".qlr-opt-text")

    def get_option_text_values(self):
        return [text.strip() for text in self.get_option_texts().all_inner_texts()]

    def select_option(self, index):
        self.get_option(index).click()

    def is_option_selected(self, index):
        return "qlr-opt-selected" in self.get_option(index).get_attribute("class")

    # ---------- recent attempts ----------

    def get_recent_attempts_label(self):
        return self.page.locator(".qlr-recent-label")

    def get_attempts(self):
        return self.page.locator(".qlr-attempt")

    def get_wrong_attempts(self):
        return self.page.locator(".qlr-attempt-bad")

    # ---------- note ----------

    def get_note_button(self):
        return self.page.locator(".qlr-pen-fab")

    def click_note(self):
        self.get_note_button().click()

    def get_note_editor(self):
        return self.page.locator("div.tiptap")

    def get_note_save_button(self):
        return self.page.locator(".nes-save")

    def get_note_close_button(self):
        return self.page.locator(".nes-close")

    # ---------- bookmark ----------

    def get_bookmark_button(self):
        return self.page.locator(".qlr-bookmark")

    def is_bookmarked(self):
        return self.get_bookmark_button().get_attribute("aria-label") == "Remove bookmark"

    def click_bookmark(self):
        self.get_bookmark_button().click()

    # ---------- solution ----------

    def get_view_solution_button(self):
        return self.page.locator(".qlr-view-solution")

    def is_solution_available(self):
        return "qlr-view-solution-on" in self.get_view_solution_button().get_attribute("class")

    def click_view_solution(self):
        self.get_view_solution_button().click()

    # ---------- answer state filter ----------

    def get_filter_button(self):
        return self.page.locator(".qlr-icon-btn[aria-label='Filter questions']")

    def click_filter(self):
        self.get_filter_button().click()

    def get_filter_sheet(self):
        return self.page.locator(".qlf-sheet")

    def get_filter_overlay(self):
        return self.page.locator(".qlf-overlay")

    def get_filter_rows(self):
        return self.page.locator(".qlf-cat-row")

    def get_filter_row(self, name):
        return self.get_filter_rows().filter(has_text=re.compile("^" + re.escape(name)))

    def get_filter_names(self):
        """Rows read "Correct (0)", so drop the count."""
        return [
            re.sub(r"\s*\(\d+\)\s*$", "", text).strip()
            for text in self.get_filter_rows().all_inner_texts()
        ]

    def get_filter_count(self, name):
        return int(re.search(r"\((\d+)\)", self.get_filter_row(name).inner_text()).group(1))

    def get_active_filter(self):
        return self.page.locator(".qlf-cat-on")

    def select_filter(self, name):
        self.get_filter_row(name).click()

    def get_question_cells(self):
        return self.page.locator(".qlf-cell")

    def close_filter(self):
        self.page.locator(".qlf-close").click()

    # ---------- report ----------

    def get_report_button(self):
        return self.page.locator(".qlr-icon-report")

    def click_report(self):
        self.get_report_button().click()

    def get_report_sheet(self):
        return self.page.locator(".ri-sheet")

    def get_report_overlay(self):
        return self.page.locator(".ri-overlay")

    def get_report_send_button(self):
        return self.page.get_by_role("button", name="Send Report")


def searchable_snippet(text, limit=4):
    """A chunk of the question that is safe to type into search.

    Search comes back empty for text with characters outside ASCII - one
    typographic apostrophe or maths glyph is enough - so the snippet is drawn
    from the longest run of plain words the question offers, keeping the words
    contiguous so a substring match still holds."""
    runs, run = [], []
    for word in normalise(text).split():
        if word.isascii():
            run.append(word)
        elif run:
            runs.append(run)
            run = []
    if run:
        runs.append(run)
    if not runs:
        return None
    words = max(runs, key=len)[:limit]
    words[-1] = words[-1].rstrip(".,;:?!")
    return " ".join(words)


def normalise(text):
    """Flatten rendered question HTML to one comparable line.

    The same question comes back with different line breaks and non breaking
    spaces depending on the screen it is rendered on, so neither side of a
    comparison can be used raw."""
    return " ".join(text.replace("\xa0", " ").split())


def read_section_count(context, section):
    """The count a Question Library card shows, read on a page of its own.

    Used to take a before reading without disturbing the screen a test already
    has open - a practice question, say, which cannot be navigated away from
    and come back to."""
    from pages.question_library_page import QuestionLibraryPage

    page = context.new_page()
    try:
        page.goto(QuestionLibraryPage.URL, wait_until="domcontentloaded")
        library = QuestionLibraryPage(page)
        library.wait_for_loaded()
        return int(library.get_card_count(section).inner_text().strip())
    finally:
        page.close()
