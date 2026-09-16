import re

# Search is answered by one call, made once when the sheet opens and with an
# empty query: everything the course holds comes back at once and the typing is
# sifted in the browser. Nothing is asked of the server as the query changes.
SEARCH_API = "**/api/v3/courses/search/**"

# Titles arrive numbered - "1. Kinematics", "2.1 Vectors" - and the sheet drops
# the number before drawing a subject or a chapter, topic or subtopic result.
# Resource titles are drawn as they come.
NUMBER_PREFIX = re.compile(r"^\s*\d+(\.\d+)*\.?\s*")


def strip_number(title):
    return NUMBER_PREFIX.sub("", title or "").strip()


class SearchPage:
    """The search sheet, raised over whatever page it was opened from.

    It is a sheet rather than a route: the address does not change while it is
    open and closing it leaves the page underneath where it was.

    With nothing typed it offers what has been searched for before and a list
    to browse - the course's subjects, then Lives and the resource folders.
    Typing swaps all of that for results, which are the chapters, topics,
    subtopics and resource items whose titles hold what was typed, each tagged
    with what it is and with the matched run of letters marked. A strip of chips
    narrows the results to one kind.

    Opening a result routes to it and shuts the sheet behind it.
    """

    def __init__(self, page):
        self.page = page

    # ---------- the sheet ----------

    def get_sheet(self):
        return self.page.locator(".sm-card")

    def get_overlay(self):
        return self.page.locator(".sm-overlay")

    def wait_for_loaded(self, timeout=30000):
        """Settled means the call has answered and the sheet has drawn what it
        offers with nothing typed."""
        self.page.locator(".sm-tile, .sm-empty").first.wait_for(timeout=timeout)

    def is_open(self):
        return self.get_sheet().count() > 0

    # ---------- the box ----------

    def get_input(self):
        return self.page.locator(".sm-input")

    def get_input_value(self):
        return self.get_input().input_value()

    def search(self, text):
        self.get_input().fill(text)

    def get_clear_button(self):
        return self.page.get_by_role("button", name="Clear search")

    def clear(self):
        self.get_clear_button().click()

    def focused_is_the_box(self):
        return self.page.evaluate(
            "() => document.activeElement === document.querySelector('.sm-input')"
        )

    # ---------- closing ----------

    def get_close_button(self):
        return self.page.get_by_role("button", name="Close search")

    def close(self):
        self.get_close_button().click()
        self.get_sheet().wait_for(state="detached")

    def close_with_escape(self):
        self.page.keyboard.press("Escape")
        self.get_sheet().wait_for(state="detached")

    def close_with_backdrop(self):
        """The sheet swallows the press, so the overlay is tapped at its edge."""
        self.get_overlay().click(position={"x": 5, "y": 5})
        self.get_sheet().wait_for(state="detached")

    # ---------- what it offers with nothing typed ----------

    def get_section_titles(self):
        return [t.strip() for t in self.page.locator(".sm-section-title").all_inner_texts()]

    def get_tiles(self):
        """The browse list: the subjects first, then Lives and the folders."""
        return self.page.locator(".sm-tile")

    def get_tile_titles(self):
        return [t.strip() for t in self.page.locator(".sm-tile-title").all_inner_texts()]

    def open_tile(self, title):
        self.get_tiles().filter(
            has=self.page.locator(".sm-tile-title").filter(
                has_text=re.compile(r"^\s*" + re.escape(title) + r"\s*$")
            )
        ).first.click()

    # ---------- what has been searched for before ----------

    RECENTS_KEY = "eduport_recent_searches"

    def get_recent_pills(self):
        return self.page.locator(".sm-recent-pill")

    def get_recent_texts(self):
        return [t.strip() for t in self.page.locator(".sm-recent-text").all_inner_texts()]

    def reuse_recent(self, text):
        self.page.get_by_role("button", name=f"Search {text}").click()

    def remove_recent(self, text):
        self.page.get_by_label(f"Remove {text} from recent searches").click()

    def get_more_recents_button(self):
        return self.page.locator(".sm-recent-more")

    def read_stored_recents(self):
        return self.page.evaluate(
            "key => JSON.parse(localStorage.getItem(key) || '[]')", self.RECENTS_KEY
        )

    def clear_stored_recents(self):
        self.page.evaluate("key => localStorage.removeItem(key)", self.RECENTS_KEY)

    def write_stored_recents(self, entries):
        self.page.evaluate(
            "([key, entries]) => localStorage.setItem(key, JSON.stringify(entries))",
            [self.RECENTS_KEY, entries],
        )

    # ---------- results ----------

    def get_results(self):
        return self.page.locator(".sm-result")

    def get_result_titles(self):
        return [t.strip() for t in self.page.locator(".sm-result-title").all_inner_texts()]

    def get_result_title(self, result):
        """The title inside one result row."""
        return result.locator(".sm-result-title")

    def get_result_tags(self):
        """What each tagged result is - Chapter, Topic or Subtopic. Items out of
        a resource folder are drawn with an icon instead of a tag."""
        return [t.strip() for t in self.page.locator(".sm-result-tag").all_inner_texts()]

    def get_results_tagged(self, tag):
        return self.get_results().filter(
            has=self.page.locator(".sm-result-tag").filter(
                has_text=re.compile(r"^\s*" + re.escape(tag) + r"\s*$")
            )
        )

    def get_marked_text(self):
        """The runs of letters the sheet marked as the match."""
        return [t.strip() for t in self.page.locator(".sm-result mark").all_inner_texts()]

    def get_resource_results(self):
        """The results that are items out of a resource folder: those are drawn
        with an icon instead of a tag."""
        return self.get_results().filter(has=self.page.locator(".sm-result-icon"))

    def get_no_access_message(self):
        """Raised over home when a locked result is tapped."""
        return self.page.get_by_text("You don't have access to this content")

    def get_empty_message(self):
        return self.page.locator(".sm-empty")

    def open_result(self, index=0):
        self.get_results().nth(index).click()

    # ---------- filters ----------

    def get_filter_chips(self):
        return self.page.locator(".sm-filter-chip")

    def get_filter_labels(self):
        return [t.strip() for t in self.get_filter_chips().all_inner_texts()]

    def get_active_filter(self):
        return self.page.locator(".sm-filter-chip-active").inner_text().strip()

    def filter_by(self, label):
        self.get_filter_chips().filter(
            has_text=re.compile(r"^\s*" + re.escape(label) + r"\s*$")
        ).first.click()
