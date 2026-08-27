class TopicPage:
    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def open(self, url):
        self.page.goto(url)
        self.wait_for_topics_loaded()

    def wait_for_topics_loaded(self):
        """Topics are fetched per chapter, so the first row is the signal that
        the page has finished loading."""
        self.page.locator(".tp-topic").first.wait_for()

    def get_page(self):
        return self.page.locator(".tp-page")

    def get_title(self):
        return self.page.locator(".tp-title")

    def get_subject_icon(self):
        return self.page.locator(".tp-subject-icon")

    def get_back_button(self):
        return self.page.locator(".tp-back")

    def click_back(self):
        self.get_back_button().click()

    # ---------- progress ----------

    def get_progress_bar(self):
        return self.page.locator(".tp-progress-bar")

    def get_progress_fill(self):
        return self.page.locator(".tp-progress-fill")

    def get_progress_width(self):
        return self.get_progress_fill().evaluate("el => el.style.width")

    def get_lessons_completed(self):
        return self.page.locator(".tp-progress-label")

    # ---------- topics ----------

    def get_topics(self):
        return self.page.locator(".tp-topic")

    def topic_count(self, timeout=10000):
        """count() does not auto-wait, so give the list a chance to render."""
        try:
            self.get_topics().first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_topics().count()

    def get_topic(self, index):
        return self.get_topics().nth(index)

    def get_topic_header(self, index):
        return self.get_topic(index).locator(".tp-topic-header")

    def get_topic_number(self, index):
        return self.get_topic(index).locator(".tp-topic-num")

    def get_topic_title(self, index):
        return self.get_topic(index).locator(".tp-topic-title")

    def get_topic_numbers(self):
        return self.page.locator(".tp-topic-num")

    def get_topic_titles(self):
        return self.page.locator(".tp-topic-title")

    # ---------- expand / collapse ----------

    def toggle_topic(self, index):
        """Topics are independent, not an accordion: opening one does not
        close the others, and clicking an open one collapses it."""
        self.get_topic_header(index).click()

    def get_topic_content(self, index):
        return self.get_topic(index).locator(".tp-topic-content")

    def get_expanded_topics(self):
        return self.page.locator(".tp-topic-content")

    def is_topic_expanded(self, index):
        return self.get_topic_content(index).count() > 0

    def get_expanded_topic_index(self):
        """The app auto-expands the topic the user should continue from, which
        is not necessarily the first one. Returns None if nothing is open."""
        for i in range(self.get_topics().count()):
            if self.is_topic_expanded(i):
                return i
        return None

    def get_collapsed_topic_index(self):
        """Index of any topic that is currently closed."""
        for i in range(self.get_topics().count()):
            if not self.is_topic_expanded(i):
                return i
        return None

    # ---------- subtopics ----------

    def get_subtopics(self, index=None):
        if index is None:
            return self.page.locator(".tp-subtopic")
        return self.get_topic(index).locator(".tp-subtopic")

    def get_subtopic(self, topic_index, subtopic_index=0):
        return self.get_subtopics(topic_index).nth(subtopic_index)

    def get_subtopic_title(self, topic_index, subtopic_index=0):
        return self.get_subtopic(topic_index, subtopic_index).locator(".tp-subtopic-title")

    def get_subtopic_duration(self, topic_index, subtopic_index=0):
        return self.get_subtopic(topic_index, subtopic_index).locator(".tp-subtopic-duration")

    def get_progress_rings(self):
        return self.page.locator(".tp-progress-ring-wrap")

    def click_subtopic(self, topic_index, subtopic_index=0):
        self.get_subtopic(topic_index, subtopic_index).click()

    # ---------- subtopic types ----------

    def expand_all_topics(self):
        for i in range(self.get_topics().count()):
            if not self.is_topic_expanded(i):
                self.toggle_topic(i)
        self.page.wait_for_timeout(1000)

    def get_all_subtopics(self):
        return self.page.locator(".tp-subtopic")

    def get_subtopic_dots(self, flat_index):
        """Decorative indicator only. It is NOT an item count: subtopics showing
        three dots still report has_quiz=false from the syllabus API."""
        return self.get_all_subtopics().nth(flat_index).locator(".tp-dot")

    def find_video_only_subtopic(self):
        """Flat index of the first subtopic, which is a plain video unless the
        player strip says otherwise."""
        return 0 if self.get_all_subtopics().count() else None

    def open_subtopic_at(self, flat_index):
        self.get_all_subtopics().nth(flat_index).click()

    # ---------- continue ----------

    def get_start_here_button(self):
        return self.page.locator(".tp-continue-btn")

    def click_start_here(self):
        self.get_start_here_button().click()
