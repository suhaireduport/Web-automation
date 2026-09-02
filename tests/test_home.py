import re
import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage

MOBILE = "8893963137"


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


def test_home_page(page):


    home_page = HomePage(page)

    home_button = home_page.get_home_button()
    
    expect(home_button).to_be_visible()

def test_search_page(page):


    home_page = HomePage(page)

    search_button = home_page.get_search_button()
    
    expect(search_button).to_be_visible()


def test_course_switch_page(page):


    home_page = HomePage(page)

    course_button = home_page.get_course_button()
    page.wait_for_timeout(2000)
    
    expect(course_button).to_be_visible()

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

def test_resource_open(login_as):
    page = login_as("9876543210")

    home_page = HomePage(page)

    page.wait_for_timeout(3000)

    resources = home_page.get_resources()

    resource = resources.nth(4)
    resource.click()

    page.wait_for_timeout(2000)

    expect(page).to_have_url(re.compile(r"https://eduport-react\.pages\.dev/home/resources/.*"))

def test_resource_count(page):

    home_page = HomePage(page)

    page.wait_for_timeout(3000)

    resources = home_page.get_resources()

    print("Resource count:", resources.count())
    resource_titles = home_page.get_resource_titles()
    all_titles = [
        resource_titles.nth(i).inner_text().strip()
        for i in range(resource_titles.count())
    ]

    actual_resources = [
        title for title in all_titles
        if title not in ["Lives", "Practice", "Question Library"]
    ]

    print("Actual resource count:", len(actual_resources))
    print("Resources:", actual_resources)

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
    page = login_as("5555555551")

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


def test_home_greeting_and_course_match_the_home_api(page):
    user = reload_home(page, HOME_API)["user"]

    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()

    expect(home_page.get_greeting()).to_have_text(f"Hello, {user['name']}")
    expect(home_page.get_course_button()).to_have_text(user["course_name"])


def test_contact_us_card_follows_the_subscription_status_from_the_api(page):
    """The card is the app's own answer to subscription_status, so the payload
    decides which way this goes rather than the account being written down."""
    body = reload_home(page, HOME_API)

    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()

    if body["subscription_status"]:
        expect(home_page.get_contact_us_card()).to_be_hidden()
    else:
        expect(home_page.get_contact_us_card()).to_be_visible()


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
