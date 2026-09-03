import re


class ChapterPage:
    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    URL = "https://eduport-react.pages.dev/home/subject"

    def open(self, url):
        self.page.goto(url)
        self.wait_for_chapters_loaded()

    def open_by_id(self, subject_id, subject_name="subject"):
        """Deep link straight to a subject's chapters, skipping Home.

        Only the id selects the subject: the trailing slug is display-only and
        is echoed into the header as-is, so pass the real name if the header
        matters to your assertion."""
        self.open(f"{self.URL}/{subject_id}/{subject_name}")

    def get_subject_id(self):
        match = re.search(r"/home/subject/(\d+)/", self.page.url)
        return match.group(1) if match else None

    def wait_for_chapters_loaded(self):
        """Chapters are fetched per subject, so the first card is the signal
        that the page has finished loading."""
        self.page.locator(".ch-item").first.wait_for()

    def get_shell(self):
        return self.page.locator(".ch-shell")

    def get_title(self):
        return self.page.locator(".ch-title")

    def get_back_button(self):
        return self.page.locator(".ch-back")

    def click_back(self):
        self.get_back_button().click()

    # ---------- chapter list ----------

    def get_chapters(self):
        return self.page.locator(".ch-item")

    def chapter_count(self, timeout=10000):
        """count() does not auto-wait, so give the list a chance to render
        before treating it as empty."""
        try:
            self.get_chapters().first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_chapters().count()

    def get_chapter(self, index):
        return self.get_chapters().nth(index)

    def get_chapter_number(self, index):
        return self.get_chapter(index).locator(".ch-item-num")

    def get_chapter_title(self, index):
        return self.get_chapter(index).locator(".ch-item-title")

    def get_chapter_titles(self):
        return self.page.locator(".ch-item-title")

    def get_chapter_numbers(self):
        return self.page.locator(".ch-item-num")

    def click_chapter(self, index):
        self.get_chapter(index).click()

    # ---------- progress ----------

    def get_progress_bar(self, index):
        return self.get_chapter(index).locator(".ch-item-progress-bar")

    def get_progress_fill(self, index):
        return self.get_chapter(index).locator(".ch-item-progress-fill")

    def get_progress_width(self, index):
        return self.get_progress_fill(index).evaluate("el => el.style.width")

    def get_completed_text(self, index):
        return self.get_chapter(index).locator(".ch-item-completed")

    def get_completed_texts(self):
        return self.page.locator(".ch-item-completed")

    def get_progress_percent(self, index):
        return float(self.get_progress_width(index).rstrip("%"))

    def get_completed_counts(self, index):
        """The "3/22 Completed" line as (completed, total)."""
        match = re.search(r"(\d+)\s*/\s*(\d+)", self.get_completed_text(index).inner_text())
        return int(match.group(1)), int(match.group(2))

    def get_subject_totals(self):
        """What the subject adds up to, as (completed, total).

        A subject publishes no figure of its own anywhere in the app. This page
        is the subject, so its progress is only ever the sum of the chapters
        listed on it."""
        counts = [self.get_completed_counts(i) for i in range(self.chapter_count())]
        return sum(done for done, _ in counts), sum(total for _, total in counts)

    def get_subject_percent(self):
        done, total = self.get_subject_totals()
        return done / total * 100 if total else 0.0

    # ---------- locked / unlocked ----------

    def get_locked_chapters(self):
        return self.page.locator(".ch-item-locked")

    def get_unlocked_chapters(self):
        return self.page.locator(".ch-item:not(.ch-item-locked)")

    def get_lock_icons(self):
        return self.page.locator(".ch-item-lock")

    def is_chapter_locked(self, index):
        classes = self.get_chapter(index).get_attribute("class") or ""
        return "ch-item-locked" in classes
