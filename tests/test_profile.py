"""The Profile page behind the home avatar.

The home avatar used to drop a small menu; it now opens a full Profile page at
/profile. The hero across the top is the account - name, number, join date,
leaderboard rank and coins - and it is drawn from two calls: profile for the
identity and profile/analysis for the row of stat tiles under it. Below that
sit a study reminder, a settings grid and a help grid, then Sign Out.

Edit Details is unchanged and lives at /profile/edit; it is covered in
test_edit_profile.py. What is checked here is the Profile page itself: that it
shows what the two calls carry, that its cards go where they say, and that Sign
Out asks first.

This account is the one the rest of the suite signs in as, so nothing here
changes it - Sign Out is opened and dismissed rather than gone through.
"""
import re

import pytest
from playwright.sync_api import expect

from conftest import STUDENT_MOBILE
from pages.home_page import HomePage
from pages.profile_page import ProfilePage
from pages.leaderboard_page import call_api, read_balance


HOME_URL = "https://eduport-react.pages.dev/"
PROFILE_URL = ProfilePage.URL
EDIT_PROFILE_URL = "https://eduport-react.pages.dev/profile/edit"
SUBSCRIPTIONS_URL = "https://eduport-react.pages.dev/subscriptions"
PREFERENCES_URL = "https://eduport-react.pages.dev/preferences"

ANALYSIS_API = "**/api/v3/profile/analysis"


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(STUDENT_MOBILE)


@pytest.fixture
def home_page(page):
    home = HomePage(page)
    home.get_subjects().first.wait_for()
    return home


@pytest.fixture
def profile_page(page, home_page):
    """Opened the way a user reaches it: tap the avatar in the home header."""
    home_page.open_profile_menu()
    profile = ProfilePage(page)
    expect(page).to_have_url(PROFILE_URL)
    profile.wait_for_loaded()
    return profile


def open_profile_with(page, api):
    """Load the Profile page and hand back the payload behind one of its
    calls."""
    with page.expect_response(api) as answer:
        page.goto(PROFILE_URL, wait_until="domcontentloaded")
    assert answer.value.status == 200, f"{api} answered {answer.value.status}"
    profile = ProfilePage(page)
    profile.wait_for_loaded()
    return profile, answer.value.json()


def digits(text):
    return re.sub(r"\D", "", text)


# ---------------------------------------------------------------------------
# 1. The avatar opens the Profile page
# ---------------------------------------------------------------------------

def test_the_home_avatar_opens_the_profile_page(page, home_page):
    home_page.open_profile_menu()

    expect(page).to_have_url(PROFILE_URL)
    profile = ProfilePage(page)
    expect(profile.get_title()).to_have_text("Profile")


def test_profile_page_shows_its_sections(profile_page):
    expect(profile_page.get_name()).to_be_visible()
    expect(profile_page.get_phone()).to_be_visible()
    expect(profile_page.get_stats()).to_have_count(4)
    assert profile_page.get_section_titles() == ["Settings", "Help & Support"]


# ---------------------------------------------------------------------------
# 2. The hero against the profile call  (API + UI)
# ---------------------------------------------------------------------------

def test_the_hero_matches_the_profile_api(page, profile_page):
    """Name, number, course and the My Account student id are what the profile
    call carries, not values written down here.

    The Profile page draws the identity from what was cached at sign in and does
    not call profile itself, so the call is made directly and held against the
    hero on screen."""
    student = call_api(page, "/profile")["student"]

    expect(profile_page.get_name()).to_have_text(student["name"])
    assert digits(profile_page.get_phone().inner_text()) == digits(student["phone"])
    expect(profile_page.get_course_name()).to_have_text(student["course_name"])
    expect(profile_page.get_my_account_sub()).to_have_text(student["unique_student_id"])


def test_the_coins_match_the_coins_api(page, profile_page):
    """The coin pill on the hero is the same balance the coins call answers."""
    assert profile_page.get_coins() == read_balance(page)


# ---------------------------------------------------------------------------
# 3. The stat tiles against the analysis call  (API + UI)
# ---------------------------------------------------------------------------

def test_the_stat_tiles_match_the_analysis_api(page):
    """The four tiles under the hero are drawn from profile/analysis: the time
    spent, the streak, the task tally and the leaderboard rank."""
    profile, analysis = open_profile_with(page, ANALYSIS_API)

    assert profile.get_stat_labels() == [
        "Time Spent Today",
        "Current Streak",
        "Task Completed",
        "Latest Exam Results",
    ]

    assert digits(profile.get_stat_value("Current Streak")) == str(
        analysis["current_streak"]
    )
    assert profile.get_stat_value("Task Completed") == (
        f"{analysis['completed_tasks']}/{analysis['total_tasks']}"
    )
    # Time spent is drawn in minutes.
    assert digits(profile.get_stat_value("Time Spent Today")) == str(
        analysis["time_spend"]
    )


def test_the_leaderboard_rank_matches_the_analysis_api(page):
    """The rank on the hero is the leaderboard rank the analysis call reports."""
    profile, analysis = open_profile_with(page, ANALYSIS_API)

    expect(profile.get_rank_label()).to_have_text("Leaderboard")
    assert digits(profile.get_rank_number().inner_text()) == str(
        analysis["leader_board_rank"]
    )


# ---------------------------------------------------------------------------
# 4. Persistence
# ---------------------------------------------------------------------------

def test_the_profile_reads_the_same_after_a_reload(page, profile_page):
    name = profile_page.get_name().inner_text()
    phone = profile_page.get_phone().inner_text()

    page.reload(wait_until="domcontentloaded")
    profile_page.wait_for_loaded()

    expect(profile_page.get_name()).to_have_text(name)
    expect(profile_page.get_phone()).to_have_text(phone)
    assert call_api(page, "/profile")["student"]["name"] == name


# ---------------------------------------------------------------------------
# 5. Navigation
# ---------------------------------------------------------------------------

def test_the_avatar_pencil_opens_edit_details(page, profile_page):
    profile_page.open_edit_details()

    expect(page).to_have_url(EDIT_PROFILE_URL)


def test_my_courses_opens_subscriptions(page, profile_page):
    profile_page.click_card("My Courses")

    expect(page).to_have_url(SUBSCRIPTIONS_URL)


def test_preferences_opens_the_preferences_page(page, profile_page):
    profile_page.click_card("Preferences")

    expect(page).to_have_url(PREFERENCES_URL)


def test_the_course_button_names_the_current_course(page, profile_page):
    """The course button in the app bar carries the account's course, the same
    the profile call holds."""
    student = call_api(page, "/profile")["student"]

    expect(profile_page.get_course_name()).to_have_text(student["course_name"])


# ---------------------------------------------------------------------------
# 6. Sign out asks first
# ---------------------------------------------------------------------------

def test_sign_out_asks_for_confirmation(profile_page):
    profile_page.click_sign_out()

    expect(profile_page.get_sign_out_dialog()).to_be_visible()
    expect(profile_page.get_sign_out_title()).to_have_text("Sign Out!")
    expect(profile_page.get_sign_out_confirm()).to_be_visible()
    expect(profile_page.get_sign_out_cancel()).to_be_visible()


def test_declining_sign_out_keeps_the_user_on_the_profile(page, profile_page):
    profile_page.click_sign_out()
    expect(profile_page.get_sign_out_dialog()).to_be_visible()

    profile_page.cancel_sign_out()

    expect(profile_page.get_sign_out_dialog()).to_have_count(0)
    expect(page).to_have_url(PROFILE_URL)
