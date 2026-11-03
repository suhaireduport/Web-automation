import re
from decimal import Decimal, InvalidOperation
from html import unescape

from playwright.sync_api import Error as PlaywrightError

from pages.home_page import HomePage
from pages.leaderboard_page import read_balance, read_coin_log
from pages.question_library_section_page import BASE_URL, normalise


class AddTopicsPage:
    """Add topics: the subject, chapter and topic picker a practice starts from.

    Reached from the Practice button on Home. Chapters arrive collapsed, so a
    topic can only be picked once its chapter has been opened.
    """

    URL = f"{BASE_URL}/home/homePractice/addtopic/problemBased"

    # The same screen is also reached from a Question Library subject, through
    # the Practice Now button of its study recommendations, which roots the
    # route at the chapter being recommended instead of at Home.
    SUBJECT_URL_PATTERN = re.compile(
        r"https://eduport-react\.pages\.dev/home/questionLibrary/subject/\d+/.+"
        r"/chapter/\d+/.+/addtopic$"
    )

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

    def get_open_chapter_title(self):
        """The title of the chapter the picker opens already unfolded."""
        return self.page.locator(".atp-chapter-open .atp-chapter-title")

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

    def get_practicable_topics(self, chapter_index=None):
        """A topic whose questions have all been answered is served disabled."""
        if chapter_index is None:
            return self.page.locator(".atp-topic:not([disabled])")
        return self.get_chapter(chapter_index).locator(".atp-topic:not([disabled])")

    def get_topic_title(self, chapter_index, topic_index):
        return self.get_topic(chapter_index, topic_index).locator(".atp-topic-title")

    def get_first_practicable_topic_title(self):
        return self.get_practicable_topics().first.locator(".atp-topic-title")

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

    def select_practicable_topic(self, minimum=1, skip=()):
        """Pick the first topic that still has questions left to practise.

        A topic whose questions have all been answered cannot be practised, and
        which topics those are changes as the account is used, so the topic is
        found rather than fixed. Returns the chapter and topic titles chosen so
        a test can look for them again in the Question Library.

        minimum is how many questions the topic has to have left: a set of more
        than one is only offered by a topic that can fill it. skip holds the
        (chapter, topic) positions already tried, for a caller looking for a
        topic that offers something the ones before it did not."""
        for chapter_index in range(self.chapter_count()):
            self.open_chapter(chapter_index)
            for topic_index in range(self.get_topics(chapter_index).count()):
                if (chapter_index, topic_index) in skip:
                    continue
                if self.get_remaining_questions(chapter_index, topic_index) < minimum:
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
                return chapter, topic, (chapter_index, topic_index)
        return None, None, None

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

    def get_mode_labels(self):
        return self.page.locator(".cp-mode-label")

    def get_mode_names(self):
        return [text.strip() for text in self.get_mode_labels().all_inner_texts()]

    def get_selected_mode_name(self):
        return self.get_selected_mode().locator(".cp-mode-label").inner_text().strip()

    # ---------- selected topics sheet ----------
    # What the summary opens: the subject and chapter the practice was built
    # from, and the topics picked under them. It has no close button - a test
    # that needs the screen back navigates to it again.

    def open_topic_summary(self):
        self.get_topic_summary().click()
        self.get_topic_sheet().wait_for()

    def get_topic_sheet(self):
        return self.page.locator(".cp-sheet")

    def get_topic_sheet_title(self):
        return self.page.locator(".cp-sheet-title")

    def get_sheet_subject(self):
        return self.page.locator(".cp-sheet-chapter-subject")

    def get_sheet_chapter(self):
        return self.page.locator(".cp-sheet-chapter-title")

    def get_sheet_topics(self):
        return self.page.locator(".cp-sheet-topic-text")

    def get_sheet_topic_names(self):
        """Topics are numbered here and not on the quiz that follows, so the
        number is dropped rather than carried into a comparison."""
        return [
            re.sub(r"^\d+\.\s*", "", text).strip()
            for text in self.get_sheet_topics().all_inner_texts()
        ]

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

    # A set names its mode in its own route: quick practice goes straight to
    # its questions, problem based stops at an instruction screen first.
    URL_PATTERN = re.compile(
        r"https://eduport-react\.pages\.dev/home/homePractice/addtopic/problemBased/"
        r"practice/(quickPractice|instruction)/\d+.*"
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
        """A question is up once it offers a way of answering it - options for
        one kind, a box to type into for the other."""
        self.get_answer_controls().first.wait_for(timeout=timeout)

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

    def get_coin_chip(self):
        """The running balance in the quiz header. It is the student's whole
        balance, not a tally of the quiz being taken."""
        return self.page.locator(".tq-coin-chip")

    def get_question(self):
        return self.page.locator(".tq-question")

    def get_question_images(self):
        """A question can be a picture rather than words."""
        return self.get_question().locator("img")

    def get_question_text(self):
        return normalise(self.get_question().inner_text())

    def get_choose_label(self):
        return self.page.locator(".tq-choose")

    def get_options(self):
        return self.page.locator(".tq-option")

    def get_option(self, index):
        return self.get_options().nth(index)

    def get_option_images(self, index):
        return self.get_option(index).locator("img")

    def get_option_letters(self):
        return self.page.locator(".tq-opt-letter")

    def get_option_texts(self):
        return self.page.locator(".tq-opt-text")

    def get_option_text_values(self):
        return [text.strip() for text in self.get_option_texts().all_inner_texts()]

    # An option carrying maths is typeset rather than written out, so its text
    # on screen is nothing like the markup it was served as. What is the same
    # on both sides is the source: the typesetter keeps it in an annotation
    # beside what it drew, so each formula is swapped back for its source
    # before the option is read.
    OPTION_SOURCE = """
        option => {
            const text = option.querySelector('.tq-opt-text') || option;
            const copy = text.cloneNode(true);
            copy.querySelectorAll('.katex').forEach(formula => {
                const source = formula.querySelector(
                    'annotation[encoding="application/x-tex"]');
                formula.replaceWith(document.createTextNode(
                    source ? source.textContent : formula.textContent));
            });
            return copy.textContent;
        }
    """

    def get_option_sources(self):
        """Every option of the question on screen, as close to the markup it
        was served as the screen can give back."""
        return self.get_options().evaluate_all(
            f"options => options.map({self.OPTION_SOURCE})"
        )

    def get_question_source(self):
        """The question on screen, read back the same way as an option is."""
        return self.get_question().evaluate(self.OPTION_SOURCE)

    def select_option(self, index):
        self.get_option(index).click()

    def is_option_selected(self, index):
        return "tq-opt-selected" in (self.get_option(index).get_attribute("class") or "")

    # ---------- typed answers ----------
    #
    # A question with no options is answered by typing a number into a box
    # instead, and either kind can turn up in any set. The box only takes what
    # its input_type allows - a whole number, or a decimal to two places - and
    # the answer is right when it reads the same as one of right_answers.

    def get_answer_controls(self):
        """Whatever the question on screen offers as a way of answering it:
        options to choose from, or a box to type into."""
        return self.page.locator(".tq-option, .tq-numeric-input input")

    def get_type_answer_label(self):
        return self.page.locator(".tq-type-answer")

    def get_numeric_input(self):
        return self.page.locator(".tq-numeric-input input")

    def is_numeric_question(self):
        return self.get_numeric_input().count() > 0

    def type_answer(self, value):
        self.get_numeric_input().fill(str(value))

    def get_numeric_marked_correct(self):
        return self.page.locator(".tq-numeric-input input.tq-input-correct")

    def get_numeric_marked_wrong(self):
        return self.page.locator(".tq-numeric-input input.tq-input-wrong")

    def get_numeric_mark(self):
        """The tick or cross drawn beside the box once it has been marked."""
        return self.page.locator(".tq-numeric-mark")

    def get_correct_answer_label(self):
        return self.page.locator(".tq-correct-answer-label")

    def get_correct_answer_box(self):
        """The right answer to a typed question, shown once it is out of reach:
        under a box marked wrong, and in the explanation."""
        return self.page.locator(".tq-correct-answer-box")

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

    def wait_for_bookmark_state(self, bookmarked, timeout=15000):
        """Hold until the control shows the state asked for.

        The button flips as soon as it is pressed, so its own look proves
        nothing; this waits for the label the screen settles on once the call
        behind it has come back."""
        label = "Remove bookmark" if bookmarked else "Add bookmark"
        self.page.locator(f".tq-bookmark[aria-label='{label}']").wait_for(
            timeout=timeout
        )

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
        self.wait_for_marking()

    def give_an_answer(self):
        """Answer the question on screen without minding whether it is right:
        the first option, or a 0 typed into the box."""
        if self.is_numeric_question():
            self.type_answer(0)
        else:
            self.select_option(0)
        self.submit()

    def get_marking(self):
        """What a question is drawn with once it has been marked: the right
        option picked out, or the tick or cross beside a typed answer."""
        return self.page.locator(".tq-opt-correct, .tq-numeric-mark")

    def wait_for_marking(self):
        self.get_marking().first.wait_for()

    def next_question(self):
        self.get_primary_button().click()

    def get_correct_options(self):
        return self.page.locator(".tq-opt-correct")

    def get_wrong_options(self):
        return self.page.locator(".tq-opt-wrong")

    def answered_wrong(self):
        """The answer given was marked wrong, not merely a wrong option shown:
        only the option that was picked is given the wrong marking, and a
        typed answer is marked on the box it was typed into."""
        return (
            self.get_wrong_options().count() + self.get_numeric_marked_wrong().count()
        ) > 0

    def get_explanation_button(self):
        return self.page.locator(".tq-btn-outline")

    def get_explanation_body(self):
        return self.page.locator(".tq-exp-body")

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

    def get_result_coins_block(self):
        return self.page.locator(".tq-result-coins-block")

    def get_result_coins_sign(self):
        """The "+" drawn beside the figure. Only a quiz that paid something
        carries one: a quiz that cost the student is drawn with the minus in
        the figure itself."""
        return self.page.locator(".tq-result-coins-sign")

    def award_is_marked_negative(self):
        """Whether the result screen is styled as a loss."""
        classes = self.get_result_coins_block().get_attribute("class") or ""
        return "tq-coins-negative" in classes

    def get_awarded_coins(self):
        """What the result screen says the quiz paid, as a signed number."""
        return int(re.search(r"-?\d+", self.get_result_coins().inner_text()).group())

    def get_result_stat_values(self):
        """The result tallies as {"Correct": 2, "I don't know": 0, "Wrong": 1}.

        A stat is drawn "2/3" over its label: how many of the questions fell
        into that bucket, over how many were asked. The figure and the total
        are separate elements, so the stat is read whole and parsed."""
        stats = self.page.locator(".tq-result-stat")
        values = {}
        for index in range(stats.count()):
            text = stats.nth(index).inner_text()
            count = re.search(r"(\d+)\s*/\s*(\d+)", text)
            label = re.sub(r"^[\d/\s]+", "", text).strip()
            values[label] = int(count.group(1))
        return values

    def get_result_stat_total(self):
        """How many questions the result screen is counting over."""
        text = self.page.locator(".tq-result-stat").first.inner_text()
        return int(re.search(r"\d+\s*/\s*(\d+)", text).group(1))

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


def start_quick_practice(page, questions=1, minimum=1, mode=None, take_test=True):
    """Subject -> topic -> topic quiz, all the way to the first question.

    Hands back the question page and what was practised, so a test can find the
    same question again in the Question Library. questions is what to ask the
    setup screen for; it is offered only as many as the topic has left, so a
    topic with fewer keeps its own default. minimum is how many questions the
    topic picked has to have left.

    take_test says whether to go on from the rules screen to the first
    question; left False, the rules screen is what comes back.

    mode names which of the two practices to take. Left out, whichever the
    setup screen has already selected is taken, which is what every caller did
    before the two were told apart. Named and not offered by the topic that was
    picked, (None, None) comes back with the mode said in the reason.

    Returns (None, None) when no topic on the account has a question left to
    practise, which is a test data problem rather than a failure."""
    tried = set()
    offered = {}

    while True:
        # Back to home each time round: after a topic has been turned down for
        # not offering the mode, the browser is sitting on that topic's setup
        # screen and Practice is only reachable from home.
        page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
        add_topics = open_practice_from_home(page)
        subject = add_topics.get_active_subject()
        chapter, topic, where = add_topics.select_practicable_topic(
            minimum=minimum, skip=tried
        )
        if topic is None:
            if offered:
                # There were topics to practise; none of them would give this
                # mode, which is a different thing from having nothing left.
                return None, {
                    "reason": f"No topic offers {mode!r}. Tried "
                    + ", ".join(f"{name!r} ({modes})" for name, modes in offered.items())
                }
            return None, None

        add_topics.click_continue()
        config = PracticeConfigPage(page)
        config.wait_for_loaded()

        if mode is None or mode in config.get_mode_names():
            break

        # This topic will not give the mode that was asked for, so try the next
        # one rather than standing down on the first that says no.
        tried.add(where)
        offered[topic] = config.get_mode_names()
        if len(tried) >= MODE_SEARCH_TOPICS:
            return None, {
                "reason": f"No topic offers {mode!r} in the first "
                f"{len(tried)} looked at: "
                + ", ".join(f"{name!r} ({modes})" for name, modes in offered.items())
            }

    if mode is not None:
        config.select_mode(mode)

    taking = config.get_selected_mode_name()
    if config.get_count(questions).count():
        config.select_count(questions)
    else:
        config.select_smallest_count()
    config.start()

    practice = PracticeQuestionPage(page)
    practice.get_take_test_button().wait_for(timeout=30000)
    if take_test:
        practice.take_test()
    return practice, {
        "subject": subject,
        "chapter": chapter,
        "topic": topic,
        "mode": taking,
    }


# ---------------------------------------------------------------------------
# Driving a practice for its coins
#
# A quick practice is what the app pays coins for, and it pays on completion
# rather than per answer: the submit that carries completed=true answers with
# what the whole set came to. To check what an answer is worth, then, a
# practice has to be driven deliberately - every question right, or every
# question wrong, or every question passed on - and the figure that comes back
# read against the rule the app publishes.
#
# Which option is the right one is not on the screen until an answer has been
# given, so it is taken from the payload the questions were served in. Getting
# one wrong brings on a similar question to try again, so the key covers those
# alternatives too and questions are answered until the result appears rather
# than a fixed number of times.
# ---------------------------------------------------------------------------

# The setup screen offers up to two modes and they are two different quizzes,
# not one quiz with a label: each is served and submitted through its own pair
# of calls, and each names itself on its own result screen. Which of the two a
# topic offers is the topic's business - some offer both, some only Quick
# practice - so a test that means one of them has to ask for it by name and
# stand down when it is not on offer.
PROBLEM_BASED = "Problem based"
QUICK_PRACTICE = "Quick practice"
MODES = (PROBLEM_BASED, QUICK_PRACTICE)

# mode -> (where its questions come from, where its answers go)
QUIZ_APIS = {
    PROBLEM_BASED: ("practice-quiz/problem-quiz", "practice-quiz/submit/problem-quiz"),
    QUICK_PRACTICE: (
        "practice-quiz/non-adaptive-quiz",
        "practice-quiz/submit/non-adaptive-quiz",
    ),
}

# What the result screen calls itself, per mode. The rules screen a set opens
# on names it the same way.
RESULT_TITLES = {PROBLEM_BASED: "Problem Practice", QUICK_PRACTICE: "Quick Practice"}

# How a mode is spelled in a coin log tag, which reads
# <where the set was started>_<this>_quiz_completed. A set that is marked in one
# mode is logged under that mode's tag and not the other's.
COIN_LOG_MODES = {PROBLEM_BASED: "problem", QUICK_PRACTICE: "non_adaptive"}

# The call that opens a set, whichever mode it is in.
CREATE_API = "practice-quiz/create"

# How many topics to walk before giving up on finding one that offers a
# particular mode. Which modes a topic offers is the topic's business, so the
# first practicable one often is not the one wanted.
MODE_SEARCH_TOPICS = 6

# Kept for the callers that predate the modes being told apart.
PROBLEM_QUIZ_API = QUIZ_APIS[PROBLEM_BASED][0]
SUBMIT_API = QUIZ_APIS[PROBLEM_BASED][1]

# Every questions call and every submit call, so a driver can pick a set up
# without being told which mode it is in.
QUESTION_APIS = tuple(apis[0] for apis in QUIZ_APIS.values())
SUBMIT_APIS = tuple(apis[1] for apis in QUIZ_APIS.values())

CORRECT = "correct"
WRONG = "wrong"
DONT_KNOW = "idk"

# How a question asks to be answered, by its input_type: 1 is options, and the
# typed ones are named by the inputmode their box is drawn with.
OPTIONS_INPUT = 1
TYPED_INPUTS = {2: "numeric", 3: "decimal"}

# A wrong answer can bring on a retry, so the number of questions a set ends up
# asking is not the number it was started with. This only bounds the loop.
MAX_QUESTIONS = 30


def signature(text):
    """What is left of an option once everything that survives neither the
    markup nor the typesetting is dropped.

    Enough to tell the options of one question apart and to recognise the same
    option again on screen, and nothing more: tags, spacing, punctuation and
    the delimiters maths is wrapped in all go, while the digits, letters and
    signs that carry the meaning stay. The minus of a typeset formula is not
    the hyphen of the source, so the two are made one."""
    text = unescape(re.sub(r"<[^>]+>", " ", text or "")).replace("\u2212", "-")
    return re.sub(r"[^0-9A-Za-z\-+=<>^_]", "", text)


def right_answers(question):
    """The answers a typed question accepts, as the screen compares them: the
    served right_answers split on commas."""
    return [
        answer.strip()
        for answer in str(question.get("right_answers", "")).split(",")
        if answer.strip()
    ]


def answer_key(payload):
    """{the options of a question: which of them are right}, by position, and
    {a typed question: the answers it accepts}.

    Keyed on the options rather than on the question, because the options are
    what can be read back off the screen, and they tell the two halves of an
    adaptive pair apart just as well. A typed question has no options to key
    on, so it is keyed on its own text instead - a string, where an options
    key is a tuple, so the two never meet."""
    key = {}

    def add(question):
        if question.get("options"):
            options = tuple(
                signature(option["value"]) for option in question["options"]
            )
            right = str(question.get("right_answers", ""))
            key[options] = [int(n) - 1 for n in re.findall(r"\d+", right)]
        else:
            key[signature(question["question_description"])] = right_answers(question)
        for alternative in question.get("alternatives") or []:
            add(alternative)

    for question in payload.get("questions", []):
        add(question)
    return key


def choose_option(practice, key, how):
    """Which option to click for the question on screen.

    Returns None when the key does not carry this question, which leaves it to
    the caller to decide whether that is a problem."""
    options = tuple(signature(source) for source in practice.get_option_sources())
    right = key.get(options)
    if right is None:
        return None
    if how == CORRECT:
        return right[0]
    return next(index for index in range(len(options)) if index not in right)


def choose_typed_answer(practice, key, how):
    """What to type for the question on screen, or None when the key does not
    carry it.

    A wrong answer is a whole number one past the right one, which both kinds
    of box will take whether the right answer is whole or not."""
    right = key.get(signature(practice.get_question_source()))
    if not right:
        return None
    if how == CORRECT:
        return right[0]
    try:
        wrong = int(Decimal(right[0]).to_integral_value()) + 1
    except InvalidOperation:
        wrong = 0
    while str(wrong) in right:
        wrong += 1
    return str(wrong)


def answer_question(practice, key, how):
    """Answer the question on screen `how`, by whatever it asks for - an option
    or a typed number - and wait for the marking.

    Hands back what was given: the index of the option picked, the text typed,
    or None for I don't know."""
    if how == DONT_KNOW:
        practice.get_dont_know_button().click()
        practice.wait_for_marking()
        return None

    typed = practice.is_numeric_question()
    given = (choose_typed_answer if typed else choose_option)(practice, key, how)
    assert given is not None, (
        "the quiz asked a question that was not in the payload it was served "
        "in, so there is no way to answer it on purpose"
    )
    if typed:
        practice.type_answer(given)
    else:
        practice.select_option(given)
    practice.submit()
    return given


def take_practice_quiz(page, how=CORRECT, questions=1, attempts=2, mode=None):
    """Start a quick practice, answer every question the same way, and go on
    to the result screen.

    how is CORRECT, WRONG or DONT_KNOW. Hands back what the app was asked and
    what it answered with - the questions served, every submit it made and the
    completion it finished on - so a test can hold the coins it paid against
    the rule it publishes. Returns None when the account has no question left
    to practise, which is a test data problem rather than a failure.

    A set that is part way through cannot be picked up from the beginning, so
    a screen that will not come up in time is met by starting a fresh set
    rather than by carrying on with a half driven one. Only that is retried: a
    set marked in a way it was not answered is a finding, and is left to
    fail."""
    for attempt in range(attempts):
        try:
            return _drive_practice_quiz(page, how, questions, mode)
        except PlaywrightError as slow:
            if attempt == attempts - 1:
                raise
            print(f"the practice would not come up ({slow}); starting another")
            page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")


def _drive_practice_quiz(page, how, questions, mode=None):
    served = []
    submitted = []

    # Listened for on both modes' calls rather than one mode's. Which mode a
    # set ends up in is the topic's business unless it was asked for by name,
    # and a driver watching the wrong pair collects nothing, ends up with an
    # empty answer key, and fails as though the app had served a question it
    # never asked for.
    def collect(response):
        if any(api in response.url for api in SUBMIT_APIS):
            submitted.append(
                {
                    "sent": response.request.post_data_json,
                    "answered": response.json(),
                }
            )
        elif any(api in response.url for api in QUESTION_APIS):
            served.append(response.json())

    page.on("response", collect)
    try:
        practice, practised = start_quick_practice(
            page, questions=questions, mode=mode
        )
        if practice is None:
            # Nothing left to practise anywhere is None; a topic that will not
            # offer the mode that was asked for says so, so a caller can stand
            # down with the reason rather than with a bare nothing.
            return practised if practised and "reason" in practised else None

        key = {}
        for payload in served:
            key.update(answer_key(payload))

        asked = 0
        for _ in range(MAX_QUESTIONS):
            practice.wait_for_question()
            asked += 1

            answer_question(practice, key, how)

            practice.next_question()
            try:
                practice.wait_for_next_question(timeout=8000)
            except Exception:
                break

        practice.wait_for_result()
    finally:
        page.remove_listener("response", collect)

    finish = next(
        (call for call in reversed(submitted) if "coin" in call["answered"]), None
    )
    assert finish is not None, (
        "the practice reached its result screen without a submit that finished "
        f"the set: {submitted}"
    )
    return {
        "practice": practice,
        "practised": practised,
        "asked": asked,
        "served": served,
        "submitted": submitted,
        # The submit that finished the set, and what it was answered with. It
        # is the only one carrying a coin figure: the ones before it are
        # answered "Question Submitted Successfully" and nothing more.
        "completion": finish["answered"],
        "completion_request": finish["sent"],
    }


def attend_quiz(page, how, mode, questions=1):
    """Take one practice in `mode` answering every question `how`, and gather in
    one go everything an attend check needs: the balance either side of it, what
    the result screen said, what the completion call answered, and the coin log
    it left behind.

    Driven once and read by many tests. Every question a practice asks is used
    up for good, so taking a fresh one per assertion would empty the account
    inside a single run.

    Hands back None when nothing is left to practise anywhere, and a dict
    carrying only a reason when the topics on offer will not give this mode."""
    before = read_balance(page)
    taken = take_practice_quiz(page, how=how, questions=questions, mode=mode)
    if taken is None or "reason" in taken:
        return taken

    practice = taken["practice"]
    taken.update(
        before=before,
        result_title=practice.get_result_title().inner_text().strip(),
        on_result=practice.get_awarded_coins(),
        marked_negative=practice.award_is_marked_negative(),
        stats=practice.get_result_stat_values(),
    )
    practice.close_result()
    taken.update(after=read_balance(page), log=read_coin_log(page, "log-today"))
    return taken
