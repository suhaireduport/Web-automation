"""The live class player, and the Live Classes list it is opened from.

A live class plays on one screen reached by two routes:

    /home/liveClasses/live/:liveId/:title   a class tapped on Live Classes
    /tasks/live/:liveId/:title              Watch Now on a Daily Tasks live card

The list hands the player everything it already knows about the class in the
query string - stream_link, youtube_id, chat_id, note, live_status and
disable_chat - and the player asks youtube/live for the class by id as well,
which is where the description beside the title comes from. A route carrying
none of that, a class linked by id alone, makes the player look the class up in
the two syllabus/lives lists first. It is only on that path that a premium class
is refused with Content Is Locked and an id the lists do not carry is answered
with Content unavailable.

Which player is drawn follows what the class is served with: a stream link is
played in the page's own video element through hls.js, a class with only a
YouTube id through an embed, and both are wrapped in Plyr.

The chat beside it is a Firestore conversation. Reading it writes nothing;
sending is the one thing on the screen that would.
"""
import re
from urllib.parse import quote, unquote, urlencode, urlparse

from pages.leaderboard_page import call_api
from pages.question_library_section_page import BASE_URL, normalise

UPCOMING = "upcoming"
STREAMED = "streamed"

# The player's own call for a class. Matched on the path rather than as a glob,
# because the question mark in front of the id is part of what is matched.
LIVE_DETAIL_PATH = "/youtube/live?live_id="

# What a tap on Send with nothing typed is answered with. A student on the chat
# blacklist is told so before the box is looked at, and the standing is read
# from Firestore rather than from anything a test can set, so either answer is
# the app refusing to send.
EMPTY_MESSAGE_TOAST = "Oops it's empty message"
BLOCKED_TOAST = "You are blocked and cannot send messages"

# The YouTube ids the player treats as no id at all.
NOT_A_YOUTUBE_ID = {"", ".", "none", "test"}


# ---------------------------------------------------------------------------
# The classes, read without going through the screen
# ---------------------------------------------------------------------------


def live_classes(page, which=STREAMED):
    """Every class on one tab, as syllabus/lives answers it: the day groups run
    together into one list, in the order the tab draws them. A class listed on
    more than one day comes back once per day."""
    body = call_api(page, f"/syllabus/lives?live={which}")
    return [live for day in body["results"] for live in day["live_class"]]


def live_detail(page, live_id):
    """What youtube/live says about one class."""
    return call_api(page, f"{LIVE_DETAIL_PATH}{live_id}").get("live") or {}


def is_premium(live):
    """A private class the student is not subscribed to. The list answers a tap
    on one with the Premium sheet instead of the player."""
    private = (live.get("youtube_type") or "").lower() == "private"
    return private and not live.get("subscription_status")


def youtube_id_of(live):
    """The YouTube id the player would use, or "" where it would use none."""
    value = (live.get("youtube_id") or "").strip()
    return "" if value.lower() in NOT_A_YOUTUBE_ID else value


def opens_from_list(live, tab=STREAMED):
    """Whether tapping the class on that tab routes to the player.

    Mirrors the list: a premium class raises a sheet, an upcoming Zoom or public
    YouTube class raises a join dialog, and a class with nothing to play does
    nothing at all."""
    if is_premium(live):
        return False
    if tab == UPCOMING and (
        (live.get("live_class_type") or "").lower() == "zoom"
        or (live.get("youtube_type") or "").lower() == "public"
    ):
        return False
    has_youtube_id = bool(live.get("youtube_id")) and live["youtube_id"] != "test"
    return bool(live.get("stream_link")) or has_youtube_id


def route_query(live):
    """The query string the list builds for a class, as a dict."""
    query = {"disable_chat": "false" if live.get("chat_id") else "true"}
    if live.get("stream_link"):
        query["stream_link"] = live["stream_link"]
    if live.get("youtube_id") and live["youtube_id"] != "test":
        query["youtube_id"] = live["youtube_id"]
    if live.get("note"):
        query["note"] = live["note"]
    if live.get("chat_id"):
        query["chat_id"] = live["chat_id"]
    if live.get("live_class_type"):
        query["live_class_type"] = live["live_class_type"]
    if live.get("live_status"):
        query["live_status"] = live["live_status"]
    return query


def is_zoom(live):
    """A class held on Zoom. The player never asks youtube/live about one."""
    return (live.get("live_class_type") or "").lower() == "zoom"


def player_route(live, query=None, prefix="/home/liveClasses/live"):
    """Where a class is played.

    Left without a query, the route is the one the list builds. An empty query
    links the class by id alone, which is the path a shared link takes."""
    if query is None:
        query = route_query(live)
    path = f"{BASE_URL}{prefix}/{live['id']}/{quote(live['title'], safe='')}"
    return f"{path}?{urlencode(query)}" if query else path


def tasks_route(live):
    """The route Watch Now on a Daily Tasks live card builds: chat left on, and
    the YouTube id where the class has a usable one."""
    query = {"disable_chat": "false"}
    if youtube_id_of(live):
        query["youtube_id"] = live["youtube_id"]
    return player_route(live, query, prefix="/tasks/live")


def route_parts(url):
    """The class id and title a player route names."""
    parts = urlparse(url).path.rstrip("/").split("/")
    return int(parts[-2]), unquote(parts[-1])


# ---------------------------------------------------------------------------
# Live Classes
# ---------------------------------------------------------------------------


class LiveClassesPage:
    """Live Classes, behind the Lives shortcut on Home.

    Upcoming and Streamed are two tabs over one list of cards grouped by month;
    ?tab=streamed picks the second. A card is badged Premium or Free, and only
    a card the student may watch routes anywhere.
    """

    URL = f"{BASE_URL}/lives"

    def __init__(self, page):
        self.page = page

    def open(self, tab=UPCOMING):
        url = self.URL if tab == UPCOMING else f"{self.URL}?tab={tab}"
        self.page.goto(url, wait_until="domcontentloaded")
        self.wait_for_loaded()

    def wait_for_loaded(self, timeout=30000):
        """Settled means the tab has drawn its cards or said it has none."""
        self.page.locator(".lc-card, .lc-empty").first.wait_for(timeout=timeout)

    def get_title(self):
        return self.page.locator(".lc-title")

    def get_tabs(self):
        return self.page.locator(".lc-tab")

    def get_active_tab(self):
        return self.page.locator(".lc-tab-active")

    # ---------- cards ----------

    def get_cards(self):
        return self.page.locator(".lc-card")

    def get_card(self, live):
        """The card of one class, by its title. A class listed on more than one
        day has a card on each, and any of them opens the same class."""
        title = re.compile(r"^\s*" + re.escape(normalise(live["title"])) + r"\s*$")
        return self.get_cards().filter(
            has=self.page.locator(".lc-card-title").filter(has_text=title)
        ).first

    def open_class(self, live):
        self.get_card(live).click()

    # ---------- the Premium sheet a premium card raises ----------

    def get_premium_overlay(self):
        return self.page.locator(".pls-overlay")

    def get_premium_sheet(self):
        return self.page.locator(".pls-sheet")

    def get_premium_title(self):
        return self.page.locator(".pls-title")

    def close_premium_sheet(self):
        self.page.locator(".pls-close").click()


# ---------------------------------------------------------------------------
# The player
# ---------------------------------------------------------------------------


class LivePlayerPage:
    URL_PATTERN = re.compile(
        r"https://eduport-react\.pages\.dev/home/liveClasses/live/\d+/[^/?]+(\?.*)?$"
    )
    TASKS_URL_PATTERN = re.compile(
        r"https://eduport-react\.pages\.dev/tasks/live/\d+/[^/?]+(\?.*)?$"
    )

    def __init__(self, page):
        self.page = page

    def open(self, url):
        self.page.goto(url, wait_until="domcontentloaded")
        self.wait_for_loaded()

    def wait_for_loaded(self, timeout=30000):
        """Settled means the class has been looked up and one of the three
        answers is on screen: the player, Content Is Locked or Content
        unavailable."""
        self.page.locator(".lp-body, .clp-page, .cua-page").first.wait_for(timeout=timeout)

    def get_page(self):
        return self.page.locator(".lp-page")

    def get_back_button(self):
        return self.page.locator(".lp-back")

    def click_back(self):
        self.get_back_button().click()

    def get_toast(self):
        """react-hot-toast renders every message into this one container, which
        is always in the DOM, so assert on its text rather than its presence."""
        return self.page.locator("[data-rht-toaster]")

    # ---------- the video ----------

    def get_video_column(self):
        return self.page.locator(".lp-video-col")

    def get_player(self):
        return self.page.locator(".lp-video-col .plyr")

    def get_stream_video(self):
        """The page's own video element, which a stream link is played in."""
        return self.page.locator(".lp-video-col video.hp-video")

    def get_youtube_embed(self):
        return self.page.locator(".lp-video-col iframe")

    def get_video_unavailable(self):
        return self.page.locator(".lp-video-empty")

    def get_play_control(self):
        return self.page.locator(".lp-video-col .plyr__controls button[data-plyr='play']")

    def get_control_names(self):
        """Every Plyr control on the bar, by the name Plyr gives it."""
        self.get_play_control().wait_for(state="attached")
        names = self.page.locator(
            ".lp-video-col .plyr__controls button[data-plyr]"
        ).evaluate_all("buttons => buttons.map(b => b.getAttribute('data-plyr'))")
        return set(names)

    def get_current_time(self):
        return self.get_stream_video().evaluate("video => video.currentTime")

    def is_paused(self):
        return self.get_stream_video().evaluate("video => video.paused")

    def wait_until_playing(self, timeout=30000):
        self.page.wait_for_function(
            "() => { const v = document.querySelector('.lp-video-col video.hp-video');"
            " return v && !v.paused && v.currentTime > 0.5; }",
            timeout=timeout,
        )

    CONTROLS_SHOWN = (
        "() => { const p = document.querySelector('.lp-video-col .plyr');"
        " return p && !p.classList.contains('plyr--hide-controls'); }"
    )

    def show_controls(self, nudge=0):
        """Bring Plyr's bar back. It hides itself a couple of seconds into
        playback, and hovering a spot the pointer already occupies fires no
        event, so the pointer is moved and nudged on repeat calls."""
        box = self.get_player().bounding_box()
        self.page.mouse.move(
            box["x"] + box["width"] / 2, box["y"] + box["height"] / 2 + nudge
        )
        self.page.wait_for_function(self.CONTROLS_SHOWN, timeout=8000)

    def pause(self, attempts=3):
        """Pause through Plyr's own button, confirmed on the video element.

        The bar can be hidden again between being shown and taking the click,
        so the click is retried rather than trusted."""
        for attempt in range(attempts):
            if self.is_paused():
                return
            try:
                self.show_controls(nudge=attempt * 6)
                self.get_play_control().click(timeout=6000)
                self.page.wait_for_function(
                    "() => document.querySelector('.lp-video-col video.hp-video').paused",
                    timeout=5000,
                )
            except Exception:
                continue
        if not self.is_paused():
            raise AssertionError("the stream would not pause")

    # ---------- the chat ----------

    def get_chat(self):
        return self.page.locator(".lp-chat")

    def get_disabled_chat(self):
        """What stands in for the chat on a class that has none: the title and
        the help and notes buttons, with no conversation."""
        return self.page.locator(".lp-chat-disabled")

    def get_chat_title(self):
        """The class title, followed by " | <description>" where youtube/live
        gives the class one."""
        return self.page.locator(".lp-chat-title")

    def get_chat_meta(self):
        return self.page.locator(".lp-chat-meta")

    def get_chat_count(self):
        """The number beside Live Chat, drawn "(3)"."""
        return int(re.search(r"\d+", self.page.locator(".lp-chat-count").inner_text()).group())

    def get_chat_rows(self):
        return self.page.locator(".lp-chat-row")

    def get_chat_notice(self):
        """The line the list holds instead of messages: still loading, not
        loaded, or no chat for this session."""
        return self.page.locator(".lp-chat-empty")

    def wait_for_chat_loaded(self, timeout=30000):
        """The conversation arrives from Firestore after the panel is drawn,
        and the panel says Loading messages until it has."""
        self.get_chat().wait_for(timeout=timeout)
        self.page.wait_for_function(
            "() => ![...document.querySelectorAll('.lp-chat-empty')]"
            ".some(line => line.textContent.includes('Loading'))",
            timeout=timeout,
        )

    def get_chat_input_bar(self):
        """Only offered while the class is live."""
        return self.page.locator(".lp-chat-inputbar")

    def get_chat_input(self):
        return self.page.locator(".lp-chat-input")

    def get_send_button(self):
        return self.page.locator(".lp-chat-send")

    def tap_send(self):
        self.get_send_button().click()

    # ---------- help and notes ----------

    def get_help_button(self):
        """Labelled Help center beside a chat and Report issue where the chat
        is switched off; it opens the same form either way."""
        return self.page.locator(".lp-report-btn")

    def open_help(self):
        self.get_help_button().click()
        self.get_help_panel().wait_for()

    def get_help_overlay(self):
        return self.page.locator(".hc-overlay")

    def get_help_panel(self):
        return self.page.locator(".hc-panel")

    def get_help_iframe(self):
        return self.page.locator(".hc-iframe")

    def close_help(self):
        self.page.locator(".hc-close").click()

    def get_notes_button(self):
        """Only drawn for a class that carries a note."""
        return self.page.locator(".lp-notes-btn")

    # ---------- a class linked by id that cannot be played ----------

    def get_locked_page(self):
        return self.page.locator(".clp-page")

    def get_locked_header_title(self):
        return self.page.locator(".clp-header-title")

    def get_locked_title(self):
        return self.page.locator(".clp-title")

    def get_locked_contact_button(self):
        return self.page.locator(".clp-contact")

    def get_locked_back_button(self):
        return self.page.locator(".clp-back")

    def get_unavailable_page(self):
        return self.page.locator(".cua-page")

    def get_unavailable_header_title(self):
        return self.page.locator(".cua-header-title")

    def get_unavailable_title(self):
        return self.page.locator(".cua-title")

    def get_unavailable_back_button(self):
        return self.page.locator(".cua-back")

    def get_contact_sheet(self):
        return self.page.locator(".cu-sheet")

    def get_contact_title(self):
        return self.page.locator(".cu-title")
