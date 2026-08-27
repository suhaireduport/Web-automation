import re

from pages.home_page import HomePage
from pages.question_library_section_page import BASE_URL, normalise


class AddTopicsPage:
    """Add topics: the subject, chapter and topic picker a practice starts from.

    Reached from the Practice button on Home. Chapters arrive collapsed, so a
    topic can only be picked once its chapter has been opened.
    """

    URL = f"{BASE_URL}/home/homePractice/addtopic/problemBased"

    def __init__(self, page):
        self.page = page

    def get_page(self):
        return self.page.locator(".atp-page")

    def get_title(self):
        return self.page.locator(".atp-title")

    def wait_for_loaded(self):
        self.get_chapters().first.wait_for()

    def get_back_button(self):
        return self.page.locator(".atp-back")

    def get_search_input(self):
        return self.page.locator(".atp-search-input")

    # ---------- subjects ----------

    def get_tabs(self):
        return self.page.locator(".atp-tab")

    def get_active_tab(self):
        return self.page.locator(".atp-tab-active")

    def get_subject_names(self):
        """Tabs read "Chemistry (4)", where the number counts chapters."""
        return [
            re.sub(r"\s*\(\d+\)\s*$", "", text).strip()
            for text in self.get_tabs().all_inner_texts()
        ]

    def get_active_subject(self):
        return re.sub(r"\s*\(\d+\)\s*$", "", self.get_active_tab().inner_text()).strip()

    def click_tab(self, index):
        self.get_tabs().nth(index).click()

    # ---------- chapters ----------

    def get_chapters(self):
        return self.page.locator(".atp-chapter")

    def get_chapter(self, index):
        return self.get_chapters().nth(index)

    def chapter_count(self, timeout=10000):
        try:
            self.get_chapters().first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_chapters().count()

    def get_chapter_title(self, index):
        return self.get_chapter(index).locator(".atp-chapter-title")

    def is_chapter_open(self, index):
        return "atp-chapter-open" in (self.get_chapter(index).get_attribute("class") or "")

    def open_chapter(self, index):
        if not self.is_chapter_open(index):
            self.get_chapter(index).locator(".atp-chapter-head").click()
            self.get_chapter(index).locator(".atp-topic").first.wait_for()

    # ---------- topics ----------

    def get_topics(self, chapter_index=None):
        if chapter_index is None:
            return self.page.locator(".atp-topic")
        return self.get_chapter(chapter_index).locator(".atp-topic")

    def get_topic(self, chapter_index, topic_index):
        return self.get_topics(chapter_index).nth(topic_index)

    def get_topic_title(self, chapter_index, topic_index):
        return self.get_topic(chapter_index, topic_index).locator(".atp-topic-title")

    def get_topic_count(self, chapter_index, topic_index):
        return self.get_topic(chapter_index, topic_index).locator(".atp-topic-count")

    def get_remaining_questions(self, chapter_index, topic_index):
        """Topics read "2/5 Questions": answered, then how many the topic has."""
        answered, total = re.search(
            r"(\d+)\s*/\s*(\d+)",
            self.get_topic_count(chapter_index, topic_index).inner_text(),
        ).groups()
        return int(total) - int(answered)

    def is_topic_selected(self, chapter_index, topic_index):
        classes = self.get_topic(chapter_index, topic_index).get_attribute("class") or ""
        return "atp-topic-checked" in classes

    def select_topic(self, chapter_index, topic_index):
        self.get_topic(chapter_index, topic_index).click()

    def select_practicable_topic(self):
        """Pick the first topic that still has questions left to practise.

        A topic whose questions have all been answered cannot be practised, and
        which topics those are changes as the account is used, so the topic is
        found rather than fixed. Returns the chapter and topic titles chosen so
        a test can look for them again in the Question Library."""
        for chapter_index in range(self.chapter_count()):
            self.open_chapter(chapter_index)
            for topic_index in range(self.get_topics(chapter_index).count()):
                if self.get_remaining_questions(chapter_index, topic_index) < 1:
                    continue
                chapter = self.get_chapter_title(chapter_index).inner_text().strip()
                # Topics are numbered here and nowhere else, so the number is
                # dropped rather than carried into a comparison later on.
                topic = re.sub(
                    r"^\d+\.\s*",
                    "",
                    self.get_topic_title(chapter_index, topic_index).inner_text().strip(),
                )
                self.select_topic(chapter_index, topic_index)
                return chapter, topic
        return None, None

    # ---------- footer ----------

    def get_footer(self):
        return self.page.locator(".atp-footer")

    def get_selection_label(self):
        return self.page.locator(".atp-cta-label")

    def get_continue_button(self):
        return self.page.locator(".atp-cta-continue")

    def click_continue(self):
        self.get_continue_button().click()


class PracticeConfigPage:
    """The practice setup: the topics picked, the mode and how many questions."""

    URL_PATTERN = re.compile(
        r"https://eduport-react\.pages\.dev/home/homePractice/addtopic/problemBased/practice.*"
    )

    def __init__(self, page):
        self.page = page

    def get_page(self):
        return self.page.locator(".cp-page")

    def get_title(self):
        return self.page.locator(".cp-title")

    def wait_for_loaded(self):
        self.get_start_button().wait_for()

    def get_topic_summary(self):
        return self.page.locator(".cp-topic-summary")

    def get_edit_topic_button(self):
        return self.page.locator(".cp-edit-topic")

    # ---------- mode ----------

    def get_modes(self):
        return self.page.locator(".cp-mode")

    def get_mode(self, name):
        return self.get_modes().filter(has_text=re.compile("^\\s*" + re.escape(name)))

    def get_selected_mode(self):
        return self.page.locator(".cp-mode-on")

    def select_mode(self, name):
        self.get_mode(name).click()

    # ---------- number of questions ----------

    def get_counts(self):
        return self.page.locator(".cp-count")

    def get_count(self, number):
        pattern = re.compile(r"^\s*" + str(number) + r"\s*$")
        return self.get_counts().filter(has_text=pattern)

    def get_selected_count(self):
        return self.page.locator(".cp-count-on")

    def get_count_values(self):
        return [int(text.strip()) for text in self.get_counts().all_inner_texts()]

    def select_count(self, number):
        self.get_count(number).click()

    def select_smallest_count(self):
        """The shortest practice on offer.

        How many questions can be asked for depends on how many the topic has
        left, so a fixed number is not always one of the choices."""
        smallest = min(self.get_count_values())
        self.select_count(smallest)
        return smallest

    # ---------- start ----------

    def get_start_button(self):
        return self.page.locator(".cp-cta")

    def start(self):
        self.get_start_button().click()


class PracticeQuestionPage:
    """A quick practice: the rules screen, the questions and the result.

    The same primary button submits an answer and then moves on, so it is read
    by what the screen is showing rather than by a second locator.
    """

    URL_PATTERN = re.compile(
        r"https://eduport-react\.pages\.dev/home/homePractice/addtopic/problemBased/"
        r"practice/quickPractice/\d+.*"
    )

    def __init__(self, page):
        self.page = page

    # ---------- rules screen ----------

    def get_title(self):
        return self.page.locator(".tq-title")

    def get_subtitle(self):
        return self.page.locator(".tq-subtitle")

    def get_question_total(self):
        return self.page.locator(".tq-count-num")

    def get_scoring(self):
        return self.page.locator(".tq-score-box")

    def get_take_test_button(self):
        return self.page.locator(".tq-take-btn")

    def take_test(self):
        self.get_take_test_button().click()
        self.wait_for_question()

    # ---------- question ----------

    def wait_for_question(self, timeout=30000):
        self.get_options().first.wait_for(timeout=timeout)

    def wait_for_next_question(self, timeout=30000):
        """The next question is up once its answer is asked for again: the
        options of the one just marked are still on screen until then."""
        self.page.wait_for_function(
            "() => document.querySelector('.tq-btn-primary')"
            "?.textContent.trim() === 'Submit'",
            timeout=timeout,
        )

    def question_total(self):
        """One dot on the strip per question in the set."""
        return self.get_strip_dots().count()

    def get_back_button(self):
        return self.page.locator(".tq-back")

    def get_question(self):
        return self.page.locator(".tq-question")

    def get_question_text(self):
        return normalise(self.get_question().inner_text())

    def get_choose_label(self):
        return self.page.locator(".tq-choose")

    def get_options(self):
        return self.page.locator(".tq-option")

    def get_option(self, index):
        return self.get_options().nth(index)

    def get_option_letters(self):
        return self.page.locator(".tq-opt-letter")

    def get_option_texts(self):
        return self.page.locator(".tq-opt-text")

    def get_option_text_values(self):
        return [text.strip() for text in self.get_option_texts().all_inner_texts()]

    def select_option(self, index):
        self.get_option(index).click()

    def is_option_selected(self, index):
        return "tq-opt-selected" in (self.get_option(index).get_attribute("class") or "")

    # ---------- palette ----------

    def get_palette_button(self):
        return self.page.locator(".tq-icon-btn[aria-label='Question palette']")

    def get_strip_dots(self):
        return self.page.locator(".tq-strip-dot")

    def get_strip_dot(self, index):
        return self.get_strip_dots().nth(index)

    def get_strip_dot_class(self, index):
        return self.get_strip_dot(index).get_attribute("class") or ""

    # ---------- bookmark and note ----------

    def get_bookmark_button(self):
        return self.page.locator(".tq-bookmark")

    def is_bookmarked(self):
        return self.get_bookmark_button().get_attribute("aria-label") == "Remove bookmark"

    def click_bookmark(self):
        self.get_bookmark_button().click()

    def get_note_button(self):
        return self.page.locator(".tq-note-fab")

    def get_report_button(self):
        return self.page.locator(".tq-icon-btn[aria-label='Report issue']")

    # ---------- answering ----------

    def get_dont_know_button(self):
        return self.page.locator(".tq-btn-outline")

    def get_primary_button(self):
        return self.page.locator(".tq-btn-primary")

    def submit(self):
        """Answer the question and wait for the marking to come back."""
        self.get_primary_button().click()
        self.page.locator(".tq-opt-correct").first.wait_for()

    def next_question(self):
        self.get_primary_button().click()

    def get_correct_options(self):
        return self.page.locator(".tq-opt-correct")

    def get_wrong_options(self):
        return self.page.locator(".tq-opt-wrong")

    def answered_wrong(self):
        """The answer given was marked wrong, not merely a wrong option shown:
        only the option that was picked is given the wrong marking."""
        return self.get_wrong_options().count() > 0

    def get_explanation_button(self):
        return self.page.locator(".tq-btn-outline")

    # ---------- result ----------

    def wait_for_result(self, timeout=30000):
        self.get_result_title().wait_for(timeout=timeout)

    def get_result_title(self):
        return self.page.locator(".tq-result-title")

    def get_result_message(self):
        return self.page.locator(".tq-result-message")

    def get_result_stats(self):
        return self.page.locator(".tq-result-stats")

    def get_result_stat(self, label):
        pattern = re.compile(re.escape(label) + r"\s*$")
        return self.page.locator(".tq-result-stat").filter(has_text=pattern)

    def get_result_coins(self):
        return self.page.locator(".tq-result-coins")

    def get_close_button(self):
        return self.page.locator(".tq-collect-btn")

    def close_result(self):
        self.get_close_button().click()


def open_practice_from_home(page):
    """Home -> Practice: the Add topics screen a quick practice starts from."""
    home_page = HomePage(page)
    # Home is handed over on domcontentloaded, so wait for it to render before
    # reaching for a resource button near the bottom of it.
    home_page.get_subjects().first.wait_for()
    home_page.get_practice().scroll_into_view_if_needed()
    home_page.get_practice().click()
    page.wait_for_url(AddTopicsPage.URL)

    add_topics = AddTopicsPage(page)
    add_topics.wait_for_loaded()
    return add_topics


def start_quick_practice(page, questions=1):
    """Subject -> topic -> topic quiz, all the way to the first question.

    Hands back the question page and what was practised, so a test can find the
    same question again in the Question Library. questions is what to ask the
    setup screen for; it is offered only as many as the topic has left, so a
    topic with fewer keeps its own default.

    Returns (None, None) when no topic on the account has a question left to
    practise, which is a test data problem rather than a failure."""
    add_topics = open_practice_from_home(page)
    subject = add_topics.get_active_subject()
    chapter, topic = add_topics.select_practicable_topic()
    if topic is None:
        return None, None
    add_topics.click_continue()

    config = PracticeConfigPage(page)
    config.wait_for_loaded()
    if config.get_count(questions).count():
        config.select_count(questions)
    else:
        config.select_smallest_count()
    config.start()

    practice = PracticeQuestionPage(page)
    practice.get_take_test_button().wait_for(timeout=30000)
    practice.take_test()
    return practice, {"subject": subject, "chapter": chapter, "topic": topic}
