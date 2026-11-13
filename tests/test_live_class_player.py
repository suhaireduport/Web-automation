"""The live class player.

Reached by tapping a class on Live Classes, by Watch Now on a Daily Tasks live
card, and by a link naming the class by id. What the player shows is checked
against the calls it is built from - syllabus/lives for the class, youtube/live
for its description and stream - rather than against classes written down here,
because which classes exist and how each is served changes with the dev data.
The class a test works on is picked at run time by the same rules the list
applies to a tap, and a test that needs a kind of class the account does not
carry stands down saying so.

Everything here only reads. The one thing on the screen that writes is sending
a chat message, and no test sends one: the chat is only ever asked to send an
empty box, which the app turns down before it reaches Firestore.
"""
import datetime
import re
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import expect

from conftest import HOME_URL, STUDENT_MOBILE
from pages.daily_tasks_page import DailyTasksPage
from pages.leaderboard_page import call_api
from pages.live_class_player_page import (
    BLOCKED_TOAST,
    EMPTY_MESSAGE_TOAST,
    LIVE_DETAIL_PATH,
    STREAMED,
    LiveClassesPage,
    LivePlayerPage,
    is_premium,
    is_zoom,
    live_classes,
    live_detail,
    opens_from_list,
    player_route,
    route_parts,
    route_query,
    tasks_route,
)
from pages.question_library_section_page import normalise

# An id neither syllabus/lives list carries.
UNKNOWN_LIVE_ID = 999999999

LIVE_CLASSES = "Live Classes"


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(STUDENT_MOBILE)


def digits(text):
    return re.sub(r"\D", "", text or "")


def query_of(url):
    return {key: values[0] for key, values in parse_qs(urlparse(url).query).items()}


# ---------------------------------------------------------------------------
# The classes a test works on
# ---------------------------------------------------------------------------


@pytest.fixture
def streamed(page):
    classes = live_classes(page, STREAMED)
    if not classes:
        pytest.skip("This account has no streamed live classes")
    return classes


@pytest.fixture
def free_class(streamed):
    """A streamed class a tap on the list plays.

    One with a stream link is preferred: that is played in the page's own video
    element, which is the player whose playback can be read."""
    openable = [live for live in streamed if opens_from_list(live, STREAMED)]
    if not openable:
        pytest.skip("Every streamed class on this account is premium or has nothing to play")
    return next((live for live in openable if live.get("stream_link")), openable[0])


@pytest.fixture
def youtube_live_class(streamed):
    """A streamed class a tap plays that is not held on Zoom: the player asks
    youtube/live about every class but a Zoom one."""
    openable = [
        live for live in streamed if opens_from_list(live, STREAMED) and not is_zoom(live)
    ]
    if not openable:
        pytest.skip("Every streamed class a tap plays on this account is a Zoom class")
    return next((live for live in openable if live.get("stream_link")), openable[0])


@pytest.fixture
def premium_class(streamed):
    locked = next((live for live in streamed if is_premium(live)), None)
    if locked is None:
        pytest.skip("No streamed class on this account is premium")
    return locked


@pytest.fixture
def live_list(page):
    lives = LiveClassesPage(page)
    lives.open(STREAMED)
    return lives


@pytest.fixture
def player(page, live_list, free_class):
    """Opened the way a student opens it: the class tapped on Streamed."""
    live_list.open_class(free_class)
    player = LivePlayerPage(page)
    player.wait_for_loaded()
    return player


def open_route(page, url):
    player = LivePlayerPage(page)
    player.open(url)
    return player


# ---------------------------------------------------------------------------
# 1. Getting there from the list
# ---------------------------------------------------------------------------


def test_tapping_a_free_class_opens_its_player(page, player, free_class):
    expect(page).to_have_url(LivePlayerPage.URL_PATTERN)
    assert route_parts(page.url) == (free_class["id"], free_class["title"])

    expect(player.get_video_column()).to_be_visible()
    expect(player.get_chat_title()).to_contain_text(normalise(free_class["title"]))


def test_the_route_carries_what_the_list_knows_about_the_class(page, player, free_class):
    """The list passes the class on in the query string, so the player can start
    before its own call is back. What it passes is what syllabus/lives served."""
    assert query_of(page.url) == route_query(free_class)


def test_opening_the_player_asks_youtube_live_for_that_class(
    page, live_list, youtube_live_class
):
    with page.expect_response(lambda response: LIVE_DETAIL_PATH in response.url) as answer:
        live_list.open_class(youtube_live_class)

    assert answer.value.status == 200, f"youtube/live answered {answer.value.status}"
    assert f"{LIVE_DETAIL_PATH}{youtube_live_class['id']}" in answer.value.url


def test_a_premium_class_raises_the_premium_sheet_instead(page, live_list, premium_class):
    live_list.open_class(premium_class)

    expect(live_list.get_premium_sheet()).to_be_visible()
    expect(live_list.get_premium_title()).to_have_text("Premium")
    expect(page).to_have_url(re.compile(r"/lives\?tab=streamed$"))

    live_list.close_premium_sheet()
    expect(live_list.get_premium_overlay()).to_have_count(0)


def test_back_returns_to_the_tab_the_class_was_opened_from(page, player, live_list):
    player.click_back()

    expect(page).to_have_url(re.compile(r"/lives\?tab=streamed$"))
    expect(live_list.get_active_tab()).to_have_text("Streamed")


# ---------------------------------------------------------------------------
# 2. The video
# ---------------------------------------------------------------------------


def needs_stream(live):
    if not live.get("stream_link"):
        pytest.skip("No free streamed class on this account has a stream link")


def test_a_class_with_a_stream_link_plays_it_in_the_page(player, free_class):
    needs_stream(free_class)

    expect(player.get_stream_video()).to_be_visible()
    expect(player.get_player()).to_be_visible()
    expect(player.get_video_unavailable()).to_have_count(0)

    player.wait_until_playing()


def test_the_player_offers_its_controls(player):
    expect(player.get_player()).to_be_visible()

    names = player.get_control_names()
    for control in ("play", "mute", "settings", "pip", "fullscreen"):
        assert control in names, f"the player has no {control} control: {sorted(names)}"


def test_pausing_the_stream_holds_it(page, player, free_class):
    needs_stream(free_class)
    player.wait_until_playing()

    player.pause()
    held = player.get_current_time()
    page.wait_for_timeout(2000)

    assert player.is_paused() is True
    assert player.get_current_time() == pytest.approx(held, abs=0.3)


# ---------------------------------------------------------------------------
# 3. The chat
# ---------------------------------------------------------------------------


def test_the_chat_is_titled_with_the_class_and_its_description(page, player, free_class):
    """The title is the class's own; the description after it comes from
    youtube/live, and a class that has none is titled alone."""
    description = normalise(live_detail(page, free_class["id"]).get("description") or "")
    title = normalise(free_class["title"])
    expected = f"{title} | {description}" if description else title

    expect(player.get_chat_title()).to_have_text(expected)


def test_the_chat_counts_the_messages_it_lists(player, free_class):
    if not free_class.get("chat_id"):
        pytest.skip("The free class on this account has no chat")

    player.wait_for_chat_loaded()

    expect(player.get_chat_meta()).to_contain_text("Live Chat")
    assert player.get_chat_count() == player.get_chat_rows().count()


def test_a_class_still_live_offers_the_chat_box(player, free_class):
    if not free_class.get("chat_id") or free_class.get("live_status") != "started":
        pytest.skip("The free class on this account is not live with a chat")

    expect(player.get_chat_input_bar()).to_be_visible()
    expect(player.get_chat_input()).to_have_attribute("placeholder", "Type here...")
    expect(player.get_send_button()).to_be_visible()


def test_a_class_that_has_ended_offers_no_chat_box(page, streamed):
    """The box is offered only while the class is live, and live_status in the
    route is what the player goes by first. A free class that has ended is used
    where the account has one; otherwise a free class is opened on its own
    route with the status it would carry once it had ended."""
    with_chat = [live for live in streamed if opens_from_list(live) and live.get("chat_id")]
    if not with_chat:
        pytest.skip("No free streamed class on this account has a chat")
    live = next((one for one in with_chat if one.get("live_status") == "ended"), with_chat[0])

    player = open_route(page, player_route(live, {**route_query(live), "live_status": "ended"}))

    expect(player.get_chat()).to_be_visible()
    expect(player.get_chat_meta()).to_contain_text("Live Chat")
    expect(player.get_chat_input_bar()).to_have_count(0)


def test_sending_an_empty_message_is_turned_down(player, free_class):
    """Nothing typed and Send tapped: the app refuses with a toast and the
    conversation is left as it was. Nothing is ever typed here, so nothing can
    be sent to the real chat."""
    if not free_class.get("chat_id") or free_class.get("live_status") != "started":
        pytest.skip("The free class on this account is not live with a chat")
    player.wait_for_chat_loaded()
    before = player.get_chat_count()
    expect(player.get_chat_input()).to_have_value("")

    player.tap_send()

    expect(player.get_toast()).to_contain_text(
        re.compile(f"{re.escape(EMPTY_MESSAGE_TOAST)}|{re.escape(BLOCKED_TOAST)}")
    )
    assert player.get_chat_count() == before


def test_a_class_without_a_chat_gets_the_title_and_help_only(page, streamed):
    """The list switches the chat off for a class that has no chat id, and the
    panel is swapped for the title and the help button."""
    chatless = next(
        (live for live in streamed if opens_from_list(live) and not live.get("chat_id")),
        None,
    )
    if chatless is None:
        pytest.skip("Every free streamed class on this account has a chat")

    player = open_route(page, player_route(chatless))

    expect(player.get_disabled_chat()).to_be_visible()
    expect(player.get_chat_title()).to_have_text(normalise(chatless["title"]))
    expect(player.get_help_button()).to_have_attribute("aria-label", "Report issue")
    expect(player.get_chat_meta()).to_have_count(0)
    expect(player.get_chat_input_bar()).to_have_count(0)


# ---------------------------------------------------------------------------
# 4. Help and notes
# ---------------------------------------------------------------------------


def test_help_opens_the_help_center_form_for_the_student(page, player):
    """The form is hosted elsewhere and is handed the student in its address,
    so what it was handed is held against the home call."""
    user = call_api(page, "/home")["user"]

    player.open_help()

    expect(player.get_help_iframe()).to_be_visible()
    handed = query_of(player.get_help_iframe().get_attribute("src"))
    assert handed["unique_student_id"] == user["unique_student_id"]
    assert digits(handed["phone"]).endswith(digits(user["phone"])[-10:])
    assert handed["platform"] == "web"


def test_help_closes_again(player):
    player.open_help()

    player.close_help()

    expect(player.get_help_overlay()).to_have_count(0)
    expect(player.get_video_column()).to_be_visible()


def test_notes_asks_for_the_class_notes_in_a_new_tab(page, streamed):
    """Notes hands the note to window.open rather than following a link, so
    that call is what is read: the note the class carries, in a tab of its own.
    A free class with a note is used where the account has one."""
    with_notes = [live for live in streamed if live.get("note")]
    if not with_notes:
        pytest.skip("No streamed class on this account carries notes")
    live = next((one for one in with_notes if opens_from_list(one)), with_notes[0])

    player = open_route(page, player_route(live))
    expect(player.get_notes_button()).to_have_text("Notes")

    page.evaluate(
        "() => { window.__opened = [];"
        " window.open = (...args) => { window.__opened.push(args); return null; }; }"
    )
    player.get_notes_button().click()

    assert page.evaluate("() => window.__opened") == [
        [live["note"], "_blank", "noopener,noreferrer"]
    ]


# ---------------------------------------------------------------------------
# 5. A class linked by id alone
# ---------------------------------------------------------------------------


def test_a_free_class_linked_by_id_still_plays(page, free_class):
    """With nothing in the query the player looks the class up in the lists
    itself, and a class the student may watch is played as usual."""
    player = open_route(page, player_route(free_class, query={}))

    expect(player.get_video_column()).to_be_visible()
    expect(player.get_locked_page()).to_have_count(0)
    expect(player.get_chat_title()).to_contain_text(normalise(free_class["title"]))


def test_a_premium_class_linked_by_id_is_locked(page, premium_class):
    player = open_route(page, player_route(premium_class, query={}))

    expect(player.get_locked_page()).to_be_visible()
    expect(player.get_locked_header_title()).to_have_text(LIVE_CLASSES)
    expect(player.get_locked_title()).to_have_text("Content Is Locked")
    expect(player.get_video_column()).to_have_count(0)


def test_the_locked_page_offers_to_contact_us(page, premium_class):
    player = open_route(page, player_route(premium_class, query={}))

    player.get_locked_contact_button().click()

    expect(player.get_contact_sheet()).to_be_visible()
    expect(player.get_contact_title()).to_have_text("Contact Us")


def test_back_from_the_locked_page_goes_home(page, premium_class):
    player = open_route(page, player_route(premium_class, query={}))

    player.get_locked_back_button().click()

    expect(page).to_have_url(HOME_URL)


def test_an_id_no_list_carries_is_content_unavailable(page):
    player = open_route(page, player_route({"id": UNKNOWN_LIVE_ID, "title": "Nothing"}, query={}))

    expect(player.get_unavailable_page()).to_be_visible()
    expect(player.get_unavailable_header_title()).to_have_text(LIVE_CLASSES)
    expect(player.get_unavailable_title()).to_have_text("Content unavailable")

    player.get_unavailable_back_button().click()
    expect(page).to_have_url(HOME_URL)


# ---------------------------------------------------------------------------
# 6. From Daily Tasks
# ---------------------------------------------------------------------------


def test_the_daily_tasks_live_route_plays_the_class(page, free_class):
    """Watch Now passes on only the id, the title and the YouTube id, and the
    player fills in the rest from youtube/live."""
    player = open_route(page, tasks_route(free_class))

    expect(page).to_have_url(LivePlayerPage.TASKS_URL_PATTERN)
    expect(player.get_player()).to_be_visible(timeout=30000)
    expect(player.get_chat_title()).to_contain_text(normalise(free_class["title"]))


def test_watch_now_on_a_daily_tasks_live_card_opens_the_player(page):
    today = datetime.date.today().isoformat()
    body = call_api(page, "/dailytasks/list")
    day = next((entry for entry in body["results"] if entry["date"] == today), {})
    lives = [task["youtube_live"] for task in day.get("study_tasks", []) if task.get("youtube_live")]
    if not lives:
        pytest.skip("No YouTube live class is on today's Daily Tasks")
    live = lives[0]

    page.goto(DailyTasksPage.URL, wait_until="domcontentloaded")
    tasks = DailyTasksPage(page)
    tasks.wait_for_tasks_loaded()
    tasks.click_watch_now_on(normalise(live["title"]))

    expect(page).to_have_url(re.compile(rf"/tasks/live/{live['id']}/"))
    player = LivePlayerPage(page)
    player.wait_for_loaded()
    expect(player.get_video_column()).to_be_visible()
