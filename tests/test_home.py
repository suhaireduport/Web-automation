import datetime
import re
from urllib.parse import unquote, unquote_plus

import pytest
from playwright.sync_api import expect

from conftest import STUDENT_MOBILE
from pages.home_page import HomePage
from pages.search_page import SEARCH_API, SearchPage, strip_number

# A non-premium account: the Contact Us card is only offered to one, so it
# cannot be checked on either of the students the rest of the suite signs in as.
NON_PREMIUM_MOBILE = "5555555551"


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(STUDENT_MOBILE)


def test_home_page(page):


    home_page = HomePage(page)

    home_button = home_page.get_home_button()
    
    expect(home_button).to_be_visible()

def test_search_page(page):


    home_page = HomePage(page)

    search_button = home_page.get_search_button()
    
    expect(search_button).to_be_visible()


# The course badge in the header used to be checked here for nothing but being
# visible. It is the entry to the course switcher, and everything it does -
# including being on screen on this page - is now in test_course_switch.py.

def test_profile_button(page):


    home_page = HomePage(page)

    profile_button = home_page.get_profile_button()
    page.wait_for_timeout(8000)
    
    expect(profile_button).to_be_visible()


def test_exams(page):


    home_page = HomePage(page)
    

    exams_button = home_page.get_exams_button()

    expect(exams_button).to_be_visible()
    home_page.get_exams_button().click()
    page.wait_for_timeout(2000)
    expect(page).to_have_url("https://eduport-react.pages.dev/exams")

def test_daily_tasks(page):

    home_page = HomePage(page)

    daily_tasks_button = home_page.get_daily_tasks_button()

    expect(daily_tasks_button).to_be_visible()

    home_page.get_daily_tasks_button().click()

    page.wait_for_timeout(2000)

    expect(page).to_have_url("https://eduport-react.pages.dev/daily-tasks")


def test_analysis(page):

    home_page = HomePage(page)

    analysis_button = home_page.get_analysis_button()

    expect(analysis_button).to_be_visible()

    home_page.get_analysis_button().click()

    page.wait_for_timeout(2000)

    expect(page).to_have_url("https://eduport-react.pages.dev/analytics")


def test_subject_count(page):

    home_page = HomePage(page)

    subjects = home_page.get_subjects()
    page.wait_for_timeout(3000)
    subjects = home_page.get_subjects()

    print("Subject count:", subjects.count())

    for i in range(subjects.count()):
        print(subjects.nth(i).inner_text())



def test_subject_open(page):

    home_page = HomePage(page)

    page.wait_for_timeout(3000)
    subjects = home_page.get_subjects()
    subject = subjects.nth(0)
    subject.click()
    page.wait_for_timeout(2000)
    expect(page).to_have_url(re.compile(r"https://eduport-react\.pages\.dev/home/subject/.*"))

# Opening a resource used to be checked here by tapping the fifth button in the
# row and looking at the route, and counting them by printing the titles without
# asserting anything. Both are in test_resources.py now, against the folder each
# button opens and the call that draws it.

def test_lives_open(page):

    home_page = HomePage(page)

    lives = home_page.get_lives()
    expect(lives).to_be_visible()

    lives.click()

    expect(page).to_have_url("https://eduport-react.pages.dev/lives")

def test_practice_open(page):

    home_page = HomePage(page)

    practice = home_page.get_practice()
    expect(practice).to_be_visible()

    practice.click()
    expect(page).to_have_url("https://eduport-react.pages.dev/home/homePractice/addtopic/problemBased")

def test_question_library_open(page):

    home_page = HomePage(page)

    question_library = home_page.get_question_library()
    expect(question_library).to_be_visible()

    question_library.click()
    expect(page).to_have_url("https://eduport-react.pages.dev/home/questionLibrary")

def test_coin_button(page):

    home_page = HomePage(page)

    coin_button = home_page.get_coin_button()
    expect(coin_button).to_be_visible()

    coin_button.click()

    page.wait_for_timeout(2000)

    expect(page).to_have_url("https://eduport-react.pages.dev/home/leader_board")


def test_streak_button(page):

    home_page = HomePage(page)

    streak_button = home_page.get_streak_button()
    expect(streak_button).to_be_visible()

    streak_button.click()

    page.wait_for_timeout(2000)

    expect(page).to_have_url("https://eduport-react.pages.dev/home/streak")

def test_ai_chat(page):

    home_page = HomePage(page)

    ai_button = home_page.get_ai_chat()
    expect(ai_button).to_be_visible()

    ai_button.click()

    # The button used to open a chooser sheet; it now opens the chat directly.
    expect(page).to_have_url("https://eduport-react.pages.dev/ai/doubt-clearance")

def test_mini_player_visibilty(page):

    home_page = HomePage(page)

    mini_player = home_page.get_mini_player()
    expect(mini_player).to_be_visible()
  

def test_mini_player_click(page):

    home_page = HomePage(page)

    mini_player = home_page.get_mini_player()

    expect(mini_player).to_be_visible()

    mini_player.click()
    page.wait_for_timeout(2000)
    back_to_video = home_page.get_back_to_video()

    expect(back_to_video).to_be_visible()

def test_mini_player_close(page):

    home_page = HomePage(page)

    mini_player = home_page.get_mini_player()

    close_button = home_page.get_close_mini_player()
    expect(mini_player).to_be_visible()

    close_button.click()
    page.wait_for_timeout(2000)
    expect(mini_player).to_be_hidden()

def test_contact_us_card_for_non_premium_user(login_as):
    page = login_as(NON_PREMIUM_MOBILE)

    home_page = HomePage(page)

    contact_us_card = home_page.get_contact_us_card()

    expect(contact_us_card).to_be_visible()


def test_no_contact_us_card_for_premium_user(page):

    home_page = HomePage(page)

    contact_us_card = home_page.get_contact_us_card()

    expect(contact_us_card).to_be_hidden()

# ---------------------------------------------------------------------------
# API verification
#
# Home is served by one call, so what the screen renders can be read back
# against the payload it was built from instead of against literals written
# down here. Each test reloads home inside expect_response, because the answer
# has to be listened for before the navigation that asks for it.
# ---------------------------------------------------------------------------

HOME_URL = "https://eduport-react.pages.dev/"

HOME_API = "**/api/v3/home"
COINS_API = "**/api/v3/analytics/leaderboard/coins"
STREAK_API = "**/api/v3/analytics/streak/now"

# The three shortcuts the app adds to the resource row itself. They are not in
# the payload, so they are set aside before the two lists are compared.
FIXED_RESOURCES = ["Lives", "Practice", "Question Library"]


def reload_home(page, api):
    """Reload home and hand back the payload the screen was built from."""
    with page.expect_response(api) as answer:
        page.goto(HOME_URL, wait_until="domcontentloaded")
    assert answer.value.status == 200, f"{api} answered {answer.value.status}"
    return answer.value.json()


def digits(text):
    """The number a chip shows, without whatever it is decorated with."""
    return re.sub(r"\D", "", text)


def test_home_subjects_match_the_home_api(page):
    body = reload_home(page, HOME_API)

    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()

    # Titles come back padded on the wire, and the card renders them trimmed.
    expected = [subject["title"].strip() for subject in body["subjects"]]
    shown = [text.strip() for text in home_page.get_subjects().all_inner_texts()]

    expect(home_page.get_subjects()).to_have_count(len(expected))
    assert shown == expected


def test_home_resources_match_the_home_api(page):
    body = reload_home(page, HOME_API)

    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()

    expected = [resource["title"].strip() for resource in body["resources"]]
    titles = [t.strip() for t in home_page.get_resource_titles().all_inner_texts()]
    shown = [title for title in titles if title not in FIXED_RESOURCES]

    assert shown == expected
    for shortcut in FIXED_RESOURCES:
        assert shortcut in titles, f"the row lost its {shortcut} shortcut"


def test_home_greeting_and_course_match_the_home_api(page):
    user = reload_home(page, HOME_API)["user"]

    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()

    expect(home_page.get_greeting()).to_have_text(f"Hello, {user['name']}")
    expect(home_page.get_course_button()).to_have_text(user["course_name"])


def has_expired(expiry_date):
    """Whether a payload's expiry_date is already behind us."""
    return datetime.date.fromisoformat(expiry_date) < datetime.date.today()


def test_contact_us_card_follows_the_subscription_status_from_the_api(page):
    """What the screen offers an unsubscribed account is the app's own answer to
    the payload, so what is served decides this rather than the account being
    written down.

    There are two of those answers and expiry_date picks between them: an
    account carrying no expiry has never held a course and is offered the
    Contact Us card, while one whose course has run out is offered the expiry
    tile and its Renew now button in its place."""
    body = reload_home(page, HOME_API)

    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()

    expiry = body.get("expiry_date")

    if not expiry:
        expect(home_page.get_contact_us_card()).to_be_visible()
        expect(home_page.get_expiry_tile()).to_be_hidden()
    elif not body["subscription_status"] or has_expired(expiry):
        expect(home_page.get_expiry_tile()).to_be_visible()
        expect(home_page.get_renew_button()).to_be_enabled()
        expect(home_page.get_contact_us_card()).to_be_hidden()
    else:
        expect(home_page.get_contact_us_card()).to_be_hidden()
        expect(home_page.get_expiry_tile()).to_be_hidden()


def test_coin_chip_matches_the_coins_api(page):
    coins = reload_home(page, COINS_API)["coins"]

    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()

    assert digits(home_page.get_coin_button().inner_text()) == str(coins)


def test_streak_chip_matches_the_streak_api(page):
    streak = reload_home(page, STREAK_API)["current_streak"]

    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()

    assert digits(home_page.get_streak_button().inner_text()) == str(streak)


EXAMS_URL = "https://eduport-react.pages.dev/exams"
DAILY_TASKS_URL = "https://eduport-react.pages.dev/daily-tasks"
SIGNUP_URL = "https://eduport-react.pages.dev/signup"

PROFILE_UPDATE_API = "**/api/v3/profile/update"

# The payment team's number behind Renew now, and the app's own terms page,
# used as the link on the banner the dialog is checked against.
PAYMENT_TEAM_NUMBER = "919778645015"

# A banner is only as big as the image inside it - the card is sized by its
# contents and nothing else - so a banner whose image is missing or will not
# load is nothing a person can tap. What the course is carrying changes from
# day to day, so the banner the dialog is checked against is given a picture
# that is certain to draw: a single dot, which the card sizes itself around.
BANNER_IMAGE = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAA"
    "DUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
TERMS_URL = "https://eduport-react.pages.dev/terms"


@pytest.fixture
def home_page(page):
    home = HomePage(page)
    home.wait_for_loaded()
    return home


def serve_home_with(page, change):
    """Serve home its own payload with one thing about it changed.

    Home draws what it is given, and most of what it can draw depends on the
    state of the account behind it - a course about to run out, a birthday not
    yet confirmed, a course with nothing in it. None of those can be arranged
    on a live account without changing it, so the account's own payload is
    taken as it passes and the one field in question is set on the way
    through."""

    def handler(route):
        response = route.fetch()
        body = response.json()
        change(body)
        route.fulfill(response=response, json=body)

    page.route(HOME_API, handler)


def open_home(page):
    home = HomePage(page)
    page.goto(HOME_URL, wait_until="domcontentloaded")
    home.wait_for_loaded()
    return home


# ---------------------------------------------------------------------------
# Search  (API + UI)
#
# The search box in the header raises a sheet rather than opening a page. One
# call answers it, made as it opens and with nothing in the query: the course
# comes back whole and the typing is sifted in the browser.
# ---------------------------------------------------------------------------

def open_search(page, home_page):
    """Open the sheet and hand back the payload it was built from.

    The call answers with the whole course - every subject, chapter, topic,
    subtopic and folder item at once - so it is given longer than the usual
    wait."""
    with page.expect_response(SEARCH_API, timeout=60000) as answer:
        home_page.open_search()
    assert answer.value.status == 200, f"search answered {answer.value.status}"
    sheet = SearchPage(page)
    sheet.wait_for_loaded()
    return sheet, answer.value.json()


def pick_query(body, kind):
    """Something the course actually carries to search for, and enough of its
    title to search with."""
    for item in body.get(kind) or []:
        title = strip_number(item["title"])
        if len(title) >= 4:
            return item, title[:4]
    return None, None


def test_the_search_button_opens_and_closes_the_search(page, home_page):
    """The sheet opens over home rather than taking its place - the address does
    not move - and every way out of it leaves home where it was."""
    sheet, _ = open_search(page, home_page)

    expect(sheet.get_sheet()).to_be_visible()
    assert sheet.focused_is_the_box(), "the box was not ready to be typed into"
    expect(page).to_have_url(HOME_URL)

    sheet.close()
    expect(page).to_have_url(HOME_URL)
    expect(home_page.get_subjects().first).to_be_visible()

    home_page.open_search()
    sheet.wait_for_loaded()
    sheet.close_with_escape()

    home_page.open_search()
    sheet.wait_for_loaded()
    sheet.close_with_backdrop()

    expect(home_page.get_subjects().first).to_be_visible()


def test_search_lists_the_subjects_and_resources_the_search_api_returns(page, home_page):
    """With nothing typed the sheet is a way in rather than a search: the
    course's subjects, then Lives and the folders, all of them off the call."""
    sheet, body = open_search(page, home_page)

    expected = [strip_number(subject["title"]) for subject in body.get("subjects") or []]
    # Lives is the app's own, added at the head of the folders.
    expected += ["Lives"] + [
        resource["title"].strip() for resource in body.get("resources") or []
    ]

    assert sheet.get_tile_titles() == expected
    assert "Browse Resources" in sheet.get_section_titles()


def test_typing_narrows_the_results_and_marks_what_matched(page, home_page):
    """What is typed keeps only the titles holding it, and marks the run of
    letters it matched on so it can be seen why each result is there."""
    sheet, body = open_search(page, home_page)
    chapter, query = pick_query(body, "chapters")
    if not chapter:
        pytest.skip("the course carries no chapter to search for")

    sheet.search(query)

    expect(sheet.get_results().first).to_be_visible()
    shown = sheet.get_result_titles()
    assert strip_number(chapter["title"]) in shown
    for title in shown:
        assert query.lower() in title.lower(), f"{title!r} does not hold {query!r}"

    marked = sheet.get_marked_text()
    assert marked, "nothing was marked as the match"
    assert all(mark.lower() == query.lower() for mark in marked)

    sheet.search("zzzzzzzz")
    expect(sheet.get_results()).to_have_count(0)
    expect(sheet.get_empty_message()).to_have_text("No matching results")


def test_a_search_result_opens_the_item_and_shuts_the_search(page, home_page):
    """A result is a way to the thing itself: it routes to the chapter it names
    and closes the sheet behind it."""
    sheet, body = open_search(page, home_page)
    chapter, query = pick_query(body, "chapters")
    if not chapter:
        pytest.skip("the course carries no chapter to search for")

    sheet.search(query)
    row = sheet.get_results_tagged("Chapter").first
    expect(row).to_be_visible()
    opened = sheet.get_result_title(row).inner_text().strip()
    wanted = next(
        entry
        for entry in body["chapters"]
        if strip_number(entry["title"]) == opened
    )

    row.click()

    expect(page).to_have_url(
        re.compile(
            r"^https://eduport-react\.pages\.dev"
            rf"/home/subject/{wanted['subject_id']}/.+/topics/{wanted['id']}$"
        )
    )
    assert not sheet.is_open()


def test_the_search_filters_keep_one_kind_of_result(page, home_page):
    """The chips above the results are what the results are made of: choosing
    one leaves only that kind on screen."""
    sheet, body = open_search(page, home_page)
    topic, query = pick_query(body, "topics")
    if not topic:
        pytest.skip("the course carries no topic to search for")

    sheet.search(query)
    assert sheet.get_active_filter() == "All"
    assert sheet.get_filter_labels()[:4] == ["All", "Chapters", "Topics", "Subtopics"]

    sheet.filter_by("Topics")

    assert sheet.get_active_filter() == "Topics"
    expect(sheet.get_results().first).to_be_visible()
    assert set(sheet.get_result_tags()) == {"Topic"}

    sheet.filter_by("Subtopics")
    assert set(sheet.get_result_tags()) in ({"Subtopic"}, set())


def test_a_premium_search_result_is_refused_without_a_subscription(page, home_page):
    """A premium item is listed for everyone and opened by the subscribed. An
    account the call reports as unsubscribed is turned away instead of routed.

    The call's own answer is served back with the standing it reports changed,
    because which items are premium and who is subscribed both belong to the
    account rather than to the screen."""
    premium = {}

    def handler(route):
        response = route.fetch()
        body = response.json()
        body["subscription_status"] = False
        for folder in body.get("resources") or []:
            for child in folder.get("children") or []:
                child["is_resource_premium"] = True
                premium.setdefault("title", strip_number(child["title"]))
        route.fulfill(response=response, json=body)

    page.route(SEARCH_API, handler)
    with page.expect_response(SEARCH_API, timeout=60000):
        home_page.open_search()
    sheet = SearchPage(page)
    sheet.wait_for_loaded()

    if not premium:
        pytest.skip("no folder on this course holds an item to lock")

    sheet.search(premium["title"][:6])
    row = sheet.get_resource_results().first
    expect(row).to_be_visible()

    row.click()

    expect(sheet.get_no_access_message()).to_be_visible()
    expect(page).to_have_url(HOME_URL)
    assert sheet.is_open(), "the sheet was closed on a result it would not open"


def test_recent_searches_are_remembered_reused_and_removable(page, home_page):
    """What has been searched for comes back the next time the sheet is opened,
    ready to be used again or thrown away."""
    sheet = SearchPage(page)
    sheet.clear_stored_recents()
    _, body = open_search(page, home_page)
    chapter, query = pick_query(body, "chapters")
    if not chapter:
        pytest.skip("the course carries no chapter to search for")

    sheet.search(query)
    expect(sheet.get_results().first).to_be_visible()
    sheet.close()

    assert sheet.read_stored_recents() == [query]

    home_page.open_search()
    sheet.wait_for_loaded()
    assert sheet.get_recent_texts() == [query]

    sheet.reuse_recent(query)
    assert sheet.get_input_value() == query

    sheet.clear()
    sheet.remove_recent(query)

    expect(sheet.get_recent_pills()).to_have_count(0)
    assert sheet.read_stored_recents() == []


# ---------------------------------------------------------------------------
# Banners  (API + UI)
# ---------------------------------------------------------------------------

def popup_url(page, popup):
    """The address a popup was opened on.

    A window opened by the page starts blank and is given its address a moment
    later, so it is read back rather than taken straight away."""
    for _ in range(20):
        if popup.url and popup.url != "about:blank":
            break
        page.wait_for_timeout(250)
    return popup.url


def sorted_banners(body):
    return sorted(body.get("banners") or [], key=lambda banner: banner.get("order") or 0)


def test_the_banners_match_the_home_api(page):
    """The strip is the banners the payload carries and nothing else: one dot
    for each, and whichever is showing is one of them."""
    body = reload_home(page, HOME_API)
    banners = sorted_banners(body)
    if not banners:
        pytest.skip("the course carries no banners")

    home_page = HomePage(page)
    home_page.wait_for_loaded()

    expect(home_page.get_banner_strip()).to_be_visible()
    images = [banner["image"] for banner in banners]

    if len(banners) == 1:
        expect(home_page.get_banner_dots()).to_have_count(0)
        if images[0]:
            expect(home_page.get_banner_image()).to_have_attribute("src", images[0])
        return

    expect(home_page.get_banner_dots()).to_have_count(len(banners))
    assert [
        dot.get_attribute("aria-label") for dot in home_page.get_banner_dots().all()
    ] == [f"Banner {index + 1}" for index in range(len(banners))]

    # The strip moves on by itself every few seconds, so which banner is showing
    # is read in the same breath as the dot that says so rather than asserted
    # against over time.
    home_page.show_banner(1)
    showing = home_page.banner_state()
    assert showing["dot"] == 1
    assert showing["image"] == banners[1].get("image")


def test_a_banner_asks_before_leaving_the_app(page):
    """A banner that carries a link does not simply follow it: it says the app
    is about to be left and waits to be told to go on."""
    body = reload_home(page, HOME_API)
    existing = sorted_banners(body)
    link = next(
        (
            banner["link"].strip()
            for banner in existing
            if (banner.get("link") or "").strip()
        ),
        TERMS_URL,
    )

    def one_linked_banner(payload):
        """Serve a single banner that carries a link and will draw.

        One rather than the several a course can hold, because the strip moves
        on by itself every few seconds and a tap would otherwise land on
        whichever banner had arrived by then. The link is the one the course
        already carries where it carries one, and a page of the app's own
        rather than somewhere invented where it does not."""
        first = existing[0] if existing else {"id": 1, "order": 1}
        payload["banners"] = [{**first, "image": BANNER_IMAGE, "link": link}]

    serve_home_with(page, one_linked_banner)

    home_page = open_home(page)
    expect(home_page.get_banner_image()).to_be_visible()
    home_page.get_banner_card().click()

    expect(home_page.get_open_link_dialog()).to_be_visible()
    expect(home_page.get_open_link_title()).to_have_text("Open link?")

    home_page.get_open_link_no().click()
    expect(home_page.get_open_link_dialog()).to_have_count(0)
    expect(page).to_have_url(HOME_URL)

    home_page.get_banner_card().click()
    expect(home_page.get_open_link_dialog()).to_be_visible()
    with page.expect_popup() as opened:
        home_page.get_open_link_yes().click()

    assert popup_url(page, opened.value).startswith(link.split("?")[0])
    opened.value.close()
    expect(home_page.get_open_link_dialog()).to_have_count(0)


# ---------------------------------------------------------------------------
# What home draws while it waits, and when it cannot  (API + UI)
# ---------------------------------------------------------------------------

def test_home_shows_a_spinner_while_its_data_is_out(page):
    """Hold the call open so the state it leaves the page in cannot be missed."""
    held = []
    page.route(HOME_API, lambda route: held.append(route))

    page.goto(HOME_URL, wait_until="commit")

    home_page = HomePage(page)
    expect(home_page.get_loading_spinner()).to_be_visible()
    expect(home_page.get_subjects()).to_have_count(0)
    expect(home_page.get_error_message()).to_have_count(0)
    assert len(held) == 1


def test_the_chips_show_a_placeholder_while_their_calls_are_out(page):
    """The coins and the streak are two calls of their own, and home does not
    wait on them: it draws a dash where each number will go and gets on with the
    rest of the page."""
    held = []
    page.route(COINS_API, lambda route: held.append(route))
    page.route(STREAK_API, lambda route: held.append(route))

    home_page = open_home(page)

    assert [value.strip() for value in home_page.get_stat_values().all_inner_texts()] == [
        "-",
        "-",
    ]
    expect(home_page.get_subjects().first).to_be_visible()
    expect(home_page.get_greeting()).to_be_visible()


def test_home_says_so_when_its_data_will_not_load_and_retry_fetches_again(page):
    """A home call that will not answer costs the whole page, so it is the one
    failure that is told rather than absorbed - and Retry is a real way back
    rather than a dead button."""
    page.route(
        HOME_API,
        lambda route: route.fulfill(status=500, json={"message": "server error"}),
    )

    page.goto(HOME_URL, wait_until="domcontentloaded")

    home_page = HomePage(page)
    # The call is tried again twice over before the page gives up on it.
    expect(home_page.get_error_message()).to_contain_text(
        "Something went wrong loading your data.", timeout=30000
    )
    expect(home_page.get_retry_button()).to_have_text("Retry")

    page.unroute(HOME_API)
    with page.expect_response(HOME_API) as answer:
        home_page.get_retry_button().click()
    assert answer.value.status == 200

    home_page.wait_for_loaded()
    expect(home_page.get_error_message()).to_have_count(0)
    expect(home_page.get_greeting()).to_be_visible()


def test_home_says_so_when_the_course_has_no_subjects(page):
    """A course with nothing filed under it leaves the grid saying so rather
    than leaving it blank."""
    serve_home_with(page, lambda body: body.update(subjects=[]))

    page.goto(HOME_URL, wait_until="domcontentloaded")

    home_page = HomePage(page)
    expect(home_page.get_empty_subjects_message()).to_have_text("No subjects available")
    expect(home_page.get_subjects()).to_have_count(0)
    # The rest of the page is unaffected by the course being empty.
    expect(home_page.get_resource_titles().first).to_be_visible()


# ---------------------------------------------------------------------------
# Opening a subject  (API + UI)
# ---------------------------------------------------------------------------

def test_opening_a_subject_carries_that_subjects_id_and_title(page):
    """The route a card opens is the subject it was drawn from: the id the
    payload gave it, and the title as it was served."""
    body = reload_home(page, HOME_API)
    home_page = HomePage(page)
    home_page.wait_for_loaded()
    subject = body["subjects"][0]

    home_page.get_subjects().first.click()

    expect(page).to_have_url(
        re.compile(
            r"^https://eduport-react\.pages\.dev"
            rf"/home/subject/{subject['id']}/"
        )
    )
    carried = unquote(page.url).split(f"/home/subject/{subject['id']}/", 1)[1]
    assert carried == subject["title"]


# ---------------------------------------------------------------------------
# A course running out  (API + UI)
#
# The tile is not a fixed warning: the date the payload carries decides both
# whether it is drawn at all and what it says.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "days, expected",
    [
        (-1, "Your course has expired,"),
        (0, "Your course will expire today,"),
        (1, "Your course expires tomorrow,"),
        (3, "Your course expires in 3 days,"),
        (30, None),
    ],
    ids=["expired", "today", "tomorrow", "three-days", "well-in-hand"],
)
def test_the_expiry_tile_wording_follows_the_days_left(page, days, expected):
    expiry = datetime.date.today() + datetime.timedelta(days=days)
    serve_home_with(
        page,
        lambda body: body.update(
            expiry_date=expiry.isoformat(), subscription_status=True
        ),
    )

    home_page = open_home(page)

    if expected is None:
        # A course with time left on it is not something to be told about.
        expect(home_page.get_expiry_tile()).to_have_count(0)
        return

    expect(home_page.get_expiry_tile()).to_be_visible()
    expect(home_page.get_expiry_text()).to_contain_text(expected)
    expect(home_page.get_renew_button()).to_have_text("Renew now")


def test_renew_now_opens_the_renewal_message(page):
    """Renew hands the account over to the payment team with everything they
    need to find it already written out."""
    body = reload_home(page, HOME_API)
    course = body["user"]["course_name"]
    expiry = datetime.date.today() - datetime.timedelta(days=1)
    serve_home_with(
        page,
        lambda payload: payload.update(
            expiry_date=expiry.isoformat(), subscription_status=True
        ),
    )

    home_page = open_home(page)
    expect(home_page.get_renew_button()).to_be_visible()

    with page.expect_popup() as opened:
        home_page.get_renew_button().click()
    opened_url = popup_url(page, opened.value)
    opened.value.close()

    # wa.me hands the browser straight on to WhatsApp's own send page, so the
    # address that settles is that one rather than the short link the app asked
    # for. What matters is who it is addressed to and what it already says.
    asked = unquote_plus(opened_url)
    assert "whatsapp" in opened_url
    assert PAYMENT_TEAM_NUMBER in asked
    assert "renew subscription" in asked.lower()
    assert course.strip() in asked


def test_the_unlock_cards_contact_button_opens_the_contact_sheet(login_as):
    """The card offered to an account that has never held a course has one
    thing on it to do, and it raises the same contact sheet Help does."""
    page = login_as(NON_PREMIUM_MOBILE)
    home_page = HomePage(page)
    home_page.wait_for_loaded()

    expect(home_page.get_unlock_button()).to_have_text("Contact Us")
    home_page.get_unlock_button().click()

    expect(home_page.get_contact_sheet()).to_be_visible()
    expect(home_page.get_contact_sheet_title()).to_have_text("Contact Us")


# ---------------------------------------------------------------------------
# The question library intro
# ---------------------------------------------------------------------------

def test_the_question_library_intro_is_shown_once(page):
    """The intro is shown to an account that has not seen it, a couple of
    seconds after home settles, and having been closed it is not shown again."""
    home_page = HomePage(page)
    home_page.set_intro_seen(False)

    page.goto(HOME_URL, wait_until="domcontentloaded")
    home_page.wait_for_loaded()

    expect(home_page.get_intro_splash()).to_be_visible(timeout=15000)
    expect(home_page.get_intro_number()).to_have_text("01")
    expect(home_page.get_intro_title()).to_have_text("Question Library")

    home_page.get_intro_next().click()
    expect(home_page.get_intro_number()).to_have_text("02")

    home_page.get_intro_close().click()
    expect(home_page.get_intro_splash()).to_have_count(0)
    assert home_page.intro_was_seen()

    page.reload(wait_until="domcontentloaded")
    home_page.wait_for_loaded()
    page.wait_for_timeout(4000)
    expect(home_page.get_intro_splash()).to_have_count(0)


# ---------------------------------------------------------------------------
# Confirming a birthday  (API + UI)
# ---------------------------------------------------------------------------

def posted_field(body, name):
    """One field out of a form the app posted."""
    found = re.search(rf'name="{name}"\r?\n\r?\n(.*?)\r?\n--', body, re.S)
    return found.group(1) if found else None


def formatted_birthday(dob):
    """"09-September-2008" out of the date of birth the call carries."""
    return datetime.datetime.strptime(dob.split("T")[0], "%Y-%m-%d").strftime(
        "%d-%B-%Y"
    )


def test_the_birthday_card_confirms_the_date_of_birth(page):
    """An account the call says has not confirmed its date of birth is asked to,
    over home, and confirming writes it back and puts the card away.

    The save is answered in the browser rather than let through: this is the
    account the rest of the suite signs in as, and a confirmation is a write to
    it. What was posted is what is checked."""
    body = reload_home(page, HOME_API)
    dob = (body.get("user") or {}).get("dob")
    if not dob:
        pytest.skip("the account carries no date of birth to confirm")

    def not_yet_confirmed(payload):
        payload["user"]["update_birthday"] = False

    serve_home_with(page, not_yet_confirmed)
    # The card waits its turn behind the question library intro, so the account
    # is taken as one that has already seen that.
    HomePage(page).set_intro_seen(True)

    home_page = open_home(page)

    expect(home_page.get_birthday_card()).to_be_visible()
    expect(home_page.get_birthday_title()).to_have_text("Confirm your Birthday")
    expect(home_page.get_birthday_dob()).to_have_text(formatted_birthday(dob))

    posted = {}

    def confirm(route):
        posted["body"] = route.request.post_data
        route.fulfill(status=200, json={"message": "Profile updated successfully"})

    page.route(PROFILE_UPDATE_API, confirm)
    home_page.get_birthday_confirm().click()

    expect(home_page.get_birthday_card()).to_have_count(0)
    assert posted_field(posted["body"], "update_birthday") == "true"
    assert posted_field(posted["body"], "dob") == dob.split("T")[0]


# ---------------------------------------------------------------------------
# The four sections
# ---------------------------------------------------------------------------

def test_the_nav_marks_the_section_being_viewed(page, home_page):
    """The nav says where the user is, not only where they can go, and it says
    it again on the way back."""
    expect(home_page.get_active_nav_item()).to_have_text("Home")

    home_page.get_sidebar_item("Exams").click()

    expect(page).to_have_url(EXAMS_URL)
    expect(home_page.get_active_nav_item()).to_have_text("Exams")

    home_page.get_sidebar_item("Home").click()

    expect(page).to_have_url(HOME_URL)
    expect(home_page.get_active_nav_item()).to_have_text("Home")


def test_the_bottom_nav_replaces_the_sidebar_on_a_phone(page):
    """On a phone the sections move off the side of the page and onto a bar
    along the bottom, which is the only way between them at that width."""
    page.set_viewport_size({"width": 390, "height": 844})

    home_page = open_home(page)

    expect(home_page.get_sidebar()).to_be_hidden()
    expect(home_page.get_bottom_nav()).to_be_visible()
    expect(home_page.get_active_bottom_nav_item()).to_have_text("Home")

    home_page.get_bottom_nav_item("Daily Tasks").click()

    expect(page).to_have_url(DAILY_TASKS_URL)
    expect(home_page.get_active_bottom_nav_item()).to_have_text("Daily Tasks")


# ---------------------------------------------------------------------------
# An account that has not finished signing up  (API + UI)
# ---------------------------------------------------------------------------

def test_an_incomplete_profile_is_sent_back_to_signup(page):
    """Home is for accounts that are finished. One the call says is not is
    handed back to the wizard rather than shown a half filled page."""
    serve_home_with(page, lambda body: body.update(is_profile_completed=False))

    page.goto(HOME_URL, wait_until="domcontentloaded")

    expect(page).to_have_url(SIGNUP_URL)
