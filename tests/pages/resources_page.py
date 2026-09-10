import re
from urllib.parse import quote

from pages.leaderboard_page import call_api
from pages.question_library_section_page import BASE_URL, normalise

# The folder's own call. Everything a folder shows comes from it, keyed on the
# folder the home call named.
CHILD_RESOURCES_API = "**/api/v3/resources/child-resources**"

# A folder's resource_type says how it is arranged, and the two arrangements
# are different screens answered in different shapes:
#
#   1  filed under the course's subjects. The call answers one entry per
#      subject - subject_id, syllabus_title and the sections under it - and the
#      screen carries a subject strip above the section tabs.
#   2  a flat set of sections. The call answers the sections themselves, and
#      the screen has no subject strip.
SUBJECT_FOLDER = 1
PLAIN_FOLDER = 2


class ResourcesPage:
    """A resource folder, opened from the resource row on home.

    The header names the folder, a strip of tabs picks the section, and the
    section's items are drawn as tiles. A folder the course has filled nothing
    into shows an empty state in place of the tabs and tiles.

    Tapping a tile does one of two things, decided by what the item is: a file
    opens in a browser tab of its own and leaves this screen where it was, and
    a video routes on to ResourceVideoPage.
    """

    URL_PATTERN = re.compile(
        r"https://eduport-react\.pages\.dev/home/resources/\d+/[^/]+/\d+$"
    )

    def __init__(self, page):
        self.page = page

    def open(self, folder):
        """Go straight to a folder, as the home row would."""
        self.page.goto(route_to(folder), wait_until="domcontentloaded")
        self.wait_for_loaded()

    def wait_for_loaded(self, timeout=30000):
        """Settled means the folder has drawn what it has: its tiles, or the
        line saying it holds nothing."""
        self.page.locator(".rs-tile, .rs-empty-state").first.wait_for(timeout=timeout)

    # ---------- header ----------

    def get_page(self):
        return self.page.locator(".rs-page")

    def get_title(self):
        return self.page.locator(".rs-header-title")

    def get_back_button(self):
        return self.page.locator(".rs-header .rs-icon-btn").first

    def click_back(self):
        self.get_back_button().click()

    # ---------- nothing to show ----------

    def get_empty_state(self):
        return self.page.locator(".rs-empty-state")

    def get_empty_label(self):
        return self.page.locator(".rs-empty-label")

    def is_empty(self):
        return self.get_empty_state().count() > 0

    # ---------- subjects, on a folder filed under them ----------

    def get_subjects(self):
        return self.page.locator(".rs-subject")

    def get_subject_names(self):
        return [normalise(name) for name in self.get_subjects().all_inner_texts()]

    def get_active_subject(self):
        return self.page.locator(".rs-subject-active")

    def get_active_subject_name(self):
        return normalise(self.get_active_subject().inner_text())

    def click_subject(self, name):
        self.get_subjects().filter(has_text=name).first.click()
        self.wait_for_loaded()

    # ---------- sections ----------
    # A plain folder draws them as .rs-tab and a subject folder as .rs-utab.
    # Both are the same thing to a caller: which set of items is on show.

    def get_sections(self):
        return self.page.locator(".rs-tab, .rs-utab")

    def get_section_names(self):
        return [normalise(name) for name in self.get_sections().all_inner_texts()]

    def get_active_section(self):
        return self.page.locator(".rs-tab-active, .rs-utab-active")

    def get_active_section_name(self):
        return normalise(self.get_active_section().inner_text())

    def click_section(self, name):
        self.get_sections().filter(has_text=name).first.click()
        self.wait_for_loaded()

    # ---------- the items themselves ----------

    def get_tiles(self):
        return self.page.locator(".rs-tile")

    def get_tile(self, index):
        return self.get_tiles().nth(index)

    def get_tile_titles(self):
        return [
            normalise(title)
            for title in self.page.locator(".rs-tile-title").all_inner_texts()
        ]

    def get_tile_by_title(self, title):
        return self.get_tiles().filter(has_text=re.compile(re.escape(title))).first

    def open_tile(self, title):
        self.get_tile_by_title(title).click()

    def get_tile_icons(self):
        return self.page.locator(".rs-tile-icon")


class ResourceVideoPage:
    """A video held in a resource folder, opened from its tile.

    The route carries the whole path to it - the folder, the section and the
    content - and the player itself is an embed, so what can be read from
    outside it is the title, the controls and the clock rather than the picture.
    """

    URL_PATTERN = re.compile(
        r"https://eduport-react\.pages\.dev/home/resources/\d+/[^/]+/\d+/video/"
    )

    def __init__(self, page):
        self.page = page

    def wait_for_loaded(self, timeout=30000):
        self.page.locator(".rv-page").wait_for(timeout=timeout)
        self.get_title().wait_for(timeout=timeout)

    def get_page(self):
        return self.page.locator(".rv-page")

    def get_title(self):
        return self.page.locator(".rv-title")

    def get_back_button(self):
        return self.page.locator(".rv-header .rv-icon-btn").first

    def click_back(self):
        self.get_back_button().click()

    def get_report_button(self):
        return self.page.get_by_role("button", name="Report Issue")

    # ---------- the player ----------

    def get_player(self):
        return self.page.locator(".rv-yt-iframe")

    def get_player_wrap(self):
        return self.page.locator(".rv-yt-wrap")

    def get_controls(self):
        return self.page.locator(".rv-ctrl-btn")

    def get_progress(self):
        return self.page.locator(".rv-progress")

    def get_time(self):
        return self.page.locator(".rv-time")

    def get_time_text(self):
        return normalise(self.get_time().inner_text())

    def get_content_id(self):
        """The content the route ends on, which is the id the call gave it."""
        return int(self.page.url.rstrip("/").split("/")[-1])


# ---------------------------------------------------------------------------
# The folders and what they hold, read without going through the screen
# ---------------------------------------------------------------------------


def resource_folders(page):
    """The resource folders the course carries, as the home call answers them.

    The resource row on home is drawn from this, and each entry carries the id,
    the title and the resource_type the folder's own route is built from."""
    return call_api(page, "/home")["resources"]


def route_to(folder):
    """Where a folder lives: its id, its title and how it is arranged.

    The title goes into the path, so it is escaped the way the browser reports
    it back - a folder called "Study Materials" sits at Study%20Materials - and
    a route built here can be held against page.url as it stands."""
    return (
        f"{BASE_URL}/home/resources/{folder['id']}/"
        f"{quote(folder['title'].strip(), safe='')}/{folder['resource_type']}"
    )


def child_resources(page, folder):
    """What one folder holds."""
    return call_api(page, f"/resources/child-resources?resource_id={folder['id']}")


def subjects_in(body):
    """The subjects a folder is filed under, in the order it answers them.

    Empty for a folder that is not filed under subjects at all."""
    return [
        normalise(entry["syllabus_title"])
        for entry in body["results"]
        if entry.get("syllabus_title") is not None
    ]


def is_filed_under_subjects(body):
    """Whether the answer came back in the shape a subject folder uses."""
    return bool(body["results"]) and "resources" in body["results"][0]


def sections_in(body, subject=0):
    """The sections on offer, whichever shape the folder came back in.

    subject picks which subject's sections to read on a folder filed under
    them, and is ignored on one that is not."""
    results = body["results"]
    if not results:
        return []
    if is_filed_under_subjects(body):
        return results[subject]["resources"]
    return results


def contents_in(section):
    return section.get("contents") or []


def is_video(content):
    """A video carries somewhere to play it from; a file carries a file."""
    return bool(content.get("stream_link")) or content.get("content_type") == "video_content"


def videos_in(body):
    """Every video in a folder, with the section it sits in.

    Walked over every subject rather than only the one on show, because which
    subject holds a video is the course's business."""
    found = []
    results = body["results"]
    subjects = range(len(results)) if is_filed_under_subjects(body) else [0]
    for subject in subjects:
        for section in sections_in(body, subject):
            for content in contents_in(section):
                if is_video(content):
                    found.append((subject, section, content))
    return found
