import re

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

# How many places the podium takes off the top of a board before the list
# starts. A board with this many students or fewer is drawn as a plain list.
PODIUM_PLACES = 3

# The board draws only the top of the list it is served: the first
# VISIBLE_PLACES students, and then - when the signed in student ranks below
# that - their own row pinned underneath, numbered with their real rank.
VISIBLE_PLACES = 20


def board_rows(served):
    """The served rows the board draws, in the order it draws them, each as
    (the rank it prints, the row)."""
    drawn = [(place + 1, row) for place, row in enumerate(served[:VISIBLE_PLACES])]
    mine = next(
        (place for place, row in enumerate(served) if row["is_current_user"]), None
    )
    if mine is not None and mine >= VISIBLE_PLACES:
        drawn.append((mine + 1, served[mine]))
    return drawn


def podium_name(student):
    """What a podium tile prints for a student: the name up to its first
    space, where the list prints the whole of it."""
    return student.strip().split(" ")[0]


class LeaderboardPage:
    """The coin leaderboard, reached from the coin chip in any app header.

    Four tabs over one screen. Each tab is drawn from two calls: a rank list
    and a coin log. The rank list is the screen itself; the log is what the
    "My log" sheet shows when the signed in student taps their own row, and
    only their own row is tappable.

    A tab whose rank list comes back empty draws an invitation to start
    earning in place of the list, which is the same set of coin rules the
    Info button opens as a sheet.
    """

    URL = "https://eduport-react.pages.dev/home/leader_board"

    # Tab label -> (rank list path, coin log path). Both hang off
    # /api/v3/analytics/leaderboard/.
    TABS = {
        "Today": ("today", "log-today"),
        "This Week": ("week", "log-week"),
        "This Month": ("monthly", "log-month"),
        "All Time": ("overall", "log"),
    }

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def open(self):
        self.page.goto(self.URL)
        self.wait_for_loaded()

    def wait_for_loaded(self, timeout=30000):
        """The tab strip renders with the screen; the list or the banner under
        it arrives with the call, so settling means one of those two is up."""
        self.get_tabs().first.wait_for(timeout=timeout)
        self.page.wait_for_function(
            "() => document.querySelector('.lb-row, .lb-banner, .lb-empty')"
            " !== null",
            timeout=timeout,
        )

    def get_page(self):
        return self.page.locator(".lb-page")

    def get_title(self):
        return self.page.locator(".lb-title")

    def get_back_button(self):
        return self.page.locator(".lb-back")

    def click_back(self):
        self.get_back_button().click()

    # ---------- tabs ----------

    def get_tabs(self):
        return self.page.locator(".lb-tab")

    def get_tab(self, name):
        pattern = re.compile(r"^\s*" + re.escape(name) + r"\s*$")
        return self.get_tabs().filter(has_text=pattern)

    def get_tab_names(self):
        return [name.strip() for name in self.get_tabs().all_inner_texts()]

    def get_active_tab(self):
        return self.page.locator(".lb-tab-active")

    def get_active_tab_name(self):
        return self.get_active_tab().inner_text().strip()

    def click_tab(self, name):
        self.get_tab(name).click()
        self.wait_for_loaded()

    # ---------- rank list ----------

    def get_list(self):
        return self.page.locator(".lb-list")

    # A board is drawn in two parts. The top three are podium tiles above the
    # list, laid out 2, 1, 3 for the picture, and the list underneath starts at
    # rank four. A board with three students or fewer has no podium and is a
    # plain list. DOM order is therefore not rank order, so everything here
    # finds a podium tile by the place it carries rather than by where it sits,
    # and every reading below comes back in rank order with the two parts run
    # together - one board, however it happens to be drawn.

    def get_podium(self):
        return self.page.locator(".lb-podium")

    def has_podium(self):
        return self.get_podium().count() > 0

    def get_podium_tiles(self):
        return self.page.locator(".lb-rank-tile")

    def get_podium_tile(self, place):
        """The tile in a given place, counting from one."""
        return self.page.locator(f".lb-rank-tile.lb-rank-{place}")

    def get_list_rows(self):
        return self.page.locator(".lb-row")

    def get_rows(self):
        """Every entry on the board, podium tiles and list rows alike.

        For counting and waiting. Reach for get_row() rather than nth() on
        this: the podium is not held in rank order."""
        return self.page.locator(".lb-rank-tile, .lb-row")

    def row_count(self, timeout=10000):
        """count() does not auto-wait, and an empty tab never grows a row, so
        the absence of one is an answer rather than something to wait out."""
        try:
            self.get_rows().first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_rows().count()

    def get_row(self, index):
        """The entry in the given place on the board, counting from the top."""
        if self.has_podium():
            if index < PODIUM_PLACES:
                return self.get_podium_tile(index + 1)
            return self.get_list_rows().nth(index - PODIUM_PLACES)
        return self.get_list_rows().nth(index)

    def get_row_rank(self, index):
        return self.get_row(index).locator(".lb-rank-badge, .lb-row-rank")

    def get_row_name(self, index):
        return self.get_row(index).locator(".lb-name, .lb-row-name")

    def get_row_coins(self, index):
        return self.get_row(index).locator(".lb-coins, .lb-row-coins")

    def is_podium_place(self, index):
        """Whether the entry in this place is drawn as a podium tile rather
        than as a list row. The two are not drawn alike, so a caller reading
        one has to know which it has."""
        return self.has_podium() and index < PODIUM_PLACES

    def get_row_avatar(self, index):
        """The picture on an entry. A podium tile carries a fallback div of the
        same class beside the image, so the image is asked for by tag."""
        return self.get_row(index).locator("img.lb-avatar, img.lb-row-avatar")

    def _board_texts(self, on_a_tile, on_a_row):
        """One reading per entry, in rank order, off the podium and the list
        together."""
        readings = []
        if self.has_podium():
            for place in range(1, PODIUM_PLACES + 1):
                tile = self.get_podium_tile(place)
                if tile.count():
                    readings.append(tile.locator(on_a_tile).inner_text().strip())
        readings += [
            text.strip() for text in self.page.locator(on_a_row).all_inner_texts()
        ]
        return readings

    def get_ranks(self):
        """Ranks are drawn zero padded ("01") in the list and bare on the
        podium, and read back as numbers either way."""
        return [int(text) for text in self._board_texts(".lb-rank-badge", ".lb-row-rank")]

    def get_names(self):
        return self._board_texts(".lb-name", ".lb-row-name")

    def get_coins(self):
        """The coin figure of every entry. It can be negative, so the sign is
        kept rather than the digits alone."""
        return [
            int(re.search(r"-?\d+", text).group())
            for text in self._board_texts(".lb-coins", ".lb-row-coins")
        ]

    # ---------- the signed in student's row ----------

    def get_current_row(self):
        """The signed in student's own entry, wherever it is drawn. On the
        podium it is the tile wearing the YOU tag; in the list it is the row
        marked current."""
        return self.page.locator(
            ".lb-rank-tile:has(.lb-rank-you-tag), .lb-row-current"
        )

    def has_current_row(self):
        return self.get_current_row().count() > 0

    def current_row_index(self):
        """Where the signed in student sits on the board, or None when this tab
        does not carry them."""
        offset = 0
        if self.has_podium():
            for place in range(1, PODIUM_PLACES + 1):
                tile = self.get_podium_tile(place)
                if tile.count() and tile.locator(".lb-rank-you-tag").count():
                    return place - 1
            offset = PODIUM_PLACES

        rows = self.get_list_rows()
        for index in range(rows.count()):
            classes = rows.nth(index).get_attribute("class") or ""
            if "lb-row-current" in classes:
                return offset + index
        return None

    def get_clickable_rows(self):
        """Only the student's own entry is offered as something to tap."""
        return self.page.locator(".lb-row-clickable, .lb-rank-tile-clickable")

    def is_row_clickable(self, index):
        classes = self.get_row(index).get_attribute("class") or ""
        return "lb-row-clickable" in classes or "lb-rank-tile-clickable" in classes

    def get_you_tag(self):
        return self.page.locator(".lb-you-tag, .lb-rank-you-tag")

    # ---------- rank movement ----------

    def get_row_delta(self, index):
        """Which way the row has moved since the list was last worked out:
        "up", "down" or "equal". A tab that publishes no movement has no
        marker at all, which reads back as None - and neither does a podium
        tile, which is not drawn with one."""
        row = self.get_row(index)
        if row.locator(".lb-delta-up, .lb-delta-text-up").count():
            return "up"
        if row.locator(".lb-delta-down, .lb-delta-text-down").count():
            return "down"
        if row.locator(".lb-delta-equal, .lb-delta-text-equal").count():
            return "equal"
        return None

    def get_row_delta_text(self, index):
        """The number beside the arrow ("+1"). Only a row that has moved
        carries one."""
        return self.get_row(index).locator(".lb-delta-text")

    # ---------- empty tab ----------

    def get_empty_banner(self):
        return self.page.locator(".lb-banner")

    def is_empty(self):
        return self.get_rows().count() == 0

    def get_inline_rules_panel(self):
        """The coin rules an empty tab shows in place of a list."""
        return self.page.locator(".lb-info-panel")

    # ---------- app rating prompt ----------
    #
    # "How's your experience so far?" is raised by this screen itself, a moment
    # after the list renders, whenever the signed in student ranks in the top
    # tenth of the tab - and only until it has been closed once on this browser.
    # Its backdrop covers the whole screen and takes every tap.

    # How long a visit is given to raise the prompt. It mounts a few
    # milliseconds after the list, so this is headroom, not an expected wait.
    RATING_PROMPT_TIMEOUT = 2000

    def get_rating_overlay(self):
        return self.page.locator(".arp-overlay")

    def get_rating_close_button(self):
        return self.get_rating_overlay().locator("button.arp-close")

    def dismiss_rating_prompt(self, timeout=RATING_PROMPT_TIMEOUT):
        """Close the rating prompt if this visit raises one.

        Waited for briefly rather than checked for once, since a check made the
        moment the list is up can land just before it mounts. Closed with its
        own button, the way a student would. Returns whether it was there."""
        try:
            self.get_rating_overlay().wait_for(state="visible", timeout=timeout)
        except PlaywrightTimeoutError:
            return False
        self.get_rating_close_button().click()
        self.get_rating_overlay().wait_for(state="detached")
        return True

    # ---------- how to get coins ----------

    def get_info_button(self):
        return self.page.locator(".lb-info")

    def open_info(self):
        self.get_info_button().click()
        self.get_info_sheet().wait_for()

    def get_info_sheet(self):
        return self.page.locator(".gc-sheet")

    def get_info_title(self):
        return self.page.locator(".gc-title")

    def get_info_hints(self):
        return self.page.locator(".gc-hint-list li")

    def get_info_hint_texts(self):
        return [text.strip() for text in self.get_info_hints().all_inner_texts()]

    def get_rule_sections(self):
        return self.page.locator(".gc-section")

    def get_rule_section_titles(self):
        return [
            title.strip()
            for title in self.page.locator(".gc-section-title").all_inner_texts()
        ]

    def get_rule_rows(self):
        return self.page.locator(".gc-row")

    def get_rules(self):
        """The published coin rules as {what it is for: how many coins}.

        The points are drawn "+10", "0", "-1"; they read back as numbers so a
        test can compare them with what an action actually pays."""
        rules = {}
        rows = self.get_rule_rows()
        for index in range(rows.count()):
            row = rows.nth(index)
            points = row.locator(".gc-row-points").inner_text().strip()
            text = row.locator(".gc-row-text").inner_text().strip()
            rules[text] = int(points.replace("+", ""))
        return rules

    # ---------- my log ----------

    def open_my_log(self):
        """Tap the signed in student's own row, which is the only one that
        opens anything.

        The sheet renders before what it holds arrives, so it is not settled
        until it is showing either entries or the line saying there are
        none."""
        self.get_current_row().first.click()
        self.get_log_sheet().wait_for()
        self.page.wait_for_function(
            "() => document.querySelector('.mls-tile, .mls-no-coins-title') !== null",
            timeout=30000,
        )

    def get_log_sheet(self):
        return self.page.locator(".mls-sheet")

    def get_log_title(self):
        return self.page.locator(".mls-title")

    def get_log_close_button(self):
        return self.page.locator(".mls-close")

    def close_my_log(self):
        self.get_log_close_button().click()
        self.get_log_sheet().wait_for(state="detached")

    def get_log_groups(self):
        """Entries are grouped by the day they were earned."""
        return self.page.locator(".mls-group")

    def get_log_group_labels(self):
        return [
            label.strip()
            for label in self.page.locator(".mls-group-label").all_inner_texts()
        ]

    def get_log_tiles(self):
        return self.page.locator(".mls-tile")

    def get_log_body(self):
        """The part of the sheet that scrolls, and whose scrolling asks for
        more of the log."""
        return self.page.locator(".mls-body")

    def load_log(self, count, timeout=15000):
        """Scroll the sheet until it holds `count` entries, or stops growing.

        The sheet is handed the log a page at a time, 30 entries to a page,
        and only asks for the next page once it is scrolled to near its
        bottom. Stops short rather than failing when no more arrive, so the
        caller's count is what reports the shortfall."""
        while self.get_log_tiles().count() < count:
            shown = self.get_log_tiles().count()
            self.get_log_body().evaluate("body => body.scrollTop = body.scrollHeight")
            try:
                self.page.wait_for_function(
                    "shown => document.querySelectorAll('.mls-tile').length > shown",
                    arg=shown,
                    timeout=timeout,
                )
            except PlaywrightTimeoutError:
                return

    def log_tile_count(self, timeout=10000):
        try:
            self.get_log_tiles().first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_log_tiles().count()

    def get_log_titles(self):
        return [
            title.strip()
            for title in self.page.locator(".mls-tile-title").all_inner_texts()
        ]

    def get_log_scores(self):
        """What each entry paid. Losing entries are drawn with their sign."""
        return [
            int(re.search(r"-?\d+", text).group())
            for text in self.page.locator(".mls-tile-score-num").all_inner_texts()
        ]

    def get_log_empty_title(self):
        """Shown instead of the grid when nothing has been earned in the
        period the tab covers."""
        return self.page.locator(".mls-no-coins-title")


# ---------------------------------------------------------------------------
# Reading the same calls the screen reads
#
# The balance moves while a test is part way through something it cannot
# navigate away from - a quiz that is being taken, say - so it is asked for
# from inside the page, with the token the app itself signed in with, rather
# than by reloading a screen that shows it. This is the call the header chip
# is drawn from and nothing else; every assertion about what it means is left
# to the tests.
# ---------------------------------------------------------------------------

API_BASE = "https://dev.eduport.co.in/api/v3"

# The coins call, as a route pattern for expect_response on a screen that
# carries the chip. The rank lists and the coin logs are read through call_api
# instead: all four rank lists go out when the screen opens and a tab's log
# goes out the first time it is shown, so by the time a test has something to
# compare, the calls it would have listened for have already been and gone.
COINS_API = "**/api/v3/analytics/leaderboard/coins"

AUTH_TOKEN_KEY = "eduport_auth_token"


def call_api(page, path):
    """GET one of the app's own calls, as the student the page is signed in
    as."""
    return page.evaluate(
        """async ([base, key, path]) => {
            const response = await fetch(base + path, {
                headers: {Authorization: 'Token ' + localStorage.getItem(key)},
            });
            if (!response.ok) throw new Error(path + ' answered ' + response.status);
            return await response.json();
        }""",
        [API_BASE, AUTH_TOKEN_KEY, path],
    )


def post_api(page, path, body):
    """POST one of the app's own calls, as the student the page is signed in
    as, and hand back the status and whatever came with it.

    Used to send a request the app has already sent a second time, which is
    what a retried request or a double tap would do."""
    return page.evaluate(
        """async ([base, key, path, body]) => {
            const response = await fetch(base + path, {
                method: 'POST',
                headers: {
                    Authorization: 'Token ' + localStorage.getItem(key),
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(body),
            });
            let answered = null;
            try { answered = await response.json(); } catch (error) {}
            return {status: response.status, answered};
        }""",
        [API_BASE, AUTH_TOKEN_KEY, path, body],
    )


def read_balance(page):
    """The coin balance the header chip is drawn from."""
    return call_api(page, "/analytics/leaderboard/coins")["coins"]


def read_coin_log(page, log="log-today"):
    """Every coin event of the period, following the pages it comes in."""
    events = []
    number = 1
    while True:
        body = call_api(page, f"/analytics/leaderboard/{log}?p={number}")
        events.extend(body["event_log"])
        pagination = body.get("pagination") or {}
        if not pagination.get("next"):
            return events
        number += 1


def read_balance_elsewhere(context):
    """The balance, read on a page of its own.

    Used to take a before reading without disturbing the screen a test already
    has open."""
    page = context.new_page()
    try:
        page.goto(LeaderboardPage.URL, wait_until="domcontentloaded")
        LeaderboardPage(page).wait_for_loaded()
        return read_balance(page)
    finally:
        page.close()
