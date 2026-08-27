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