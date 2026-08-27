"""Profile menu navigation.

Every scenario opens the menu from the home header, follows one item, checks
where it landed and comes back, so the cases stay independent of each other.

Not every item is a route: Help centre and Customer care open an overlay on top
of the page, and Sign Out asks for confirmation before it does anything.
"""
import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.login_page import LoginPage
from pages.otp_page import OtpPage
from pages.profile_menu_page import ProfileMenuPage

MOBILE = "9876543210"
OTP = "430582"

LOGIN_URL = "https://eduport-react.pages.dev/login"
OTP_URL = "https://eduport-react.pages.dev/otp"
HOME_URL = "https://eduport-react.pages.dev/"
EDIT_DETAILS_URL = "https://eduport-react.pages.dev/profile/edit"
EXAM_RESULTS_URL = "https://eduport-react.pages.dev/profile/exam-results"
SUBSCRIPTIONS_URL = "https://eduport-react.pages.dev/subscriptions"
PREFERENCES_URL = "https://eduport-react.pages.dev/preferences"
TERMS_URL = "https://eduport-react.pages.dev/terms"

MENU_ITEMS = [
    "Edit details",
    "Exam Result",
    "Subscriptions",
    "Preferences",
    "Help centre",
    "Terms & Conditions",
    "Customer care",
    "Sign Out",
]


def session_value(page, key):
    """The app keeps the signed in user in localStorage, so assertions can read
    the real values instead of repeating them as literals."""
    return page.evaluate("key => localStorage.getItem(key)", key)


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture
def home_page(page):
    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()
    return home_page


@pytest.fixture
def profile_menu(home_page):
    home_page.open_profile_menu()

    menu = ProfileMenuPage(home_page.page)
    expect(menu.get_menu()).to_be_visible()
    return menu


def return_to_home(page, home_page):
    """Back out of wherever the item led and reopen the menu, the way a user
    working through the list would."""
    page.go_back()
    expect(page).to_have_url(HOME_URL)

    home_page.open_profile_menu()
    expect(ProfileMenuPage(page).get_menu()).to_be_visible()


# ---------------------------------------------------------------------------
# The menu itself
#
# Scenario:   the profile menu opens from the home header
# Pre:        signed in and sitting on the home page
# Steps:      click the avatar
# Expected:   the menu appears with all nine entries
# ---------------------------------------------------------------------------

def test_profile_menu_opens_from_the_home_page(profile_menu):
    expect(profile_menu.get_menu()).to_be_visible()
    expect(profile_menu.get_user()).to_be_visible()


def test_profile_menu_shows_the_expected_items(profile_menu):
    expect(profile_menu.get_items()).to_have_count(len(MENU_ITEMS))

    for name in MENU_ITEMS:
        expect(profile_menu.get_item(name)).to_be_visible()

    assert profile_menu.get_item_names() == MENU_ITEMS


# ---------------------------------------------------------------------------
# Scenario:   the menu identifies the signed in user
# Pre:        signed in
# Steps:      open the menu
# Expected:   name and student id match the session, not a hard coded string
# ---------------------------------------------------------------------------

def test_profile_menu_shows_the_signed_in_user(page, profile_menu):
    expect(profile_menu.get_user_avatar()).to_be_visible()
    expect(profile_menu.get_user_name()).to_have_text(session_value(page, "user_name"))
    expect(profile_menu.get_student_id()).to_have_text(
        session_value(page, "unique_student_id")
    )


# ---------------------------------------------------------------------------
# Scenario:   Edit details opens the edit details page
# Pre:        the profile menu is open
# Steps:      click Edit details, then go back
# Expected:   /profile/edit with its heading, and home again afterwards
# ---------------------------------------------------------------------------

def test_edit_details_opens_the_edit_details_page(page, home_page, profile_menu):
    profile_menu.click_item("Edit details")

    expect(page).to_have_url(EDIT_DETAILS_URL)
    expect(page.get_by_role("heading", name="Edit Details")).to_be_visible()

    return_to_home(page, home_page)


# ---------------------------------------------------------------------------
# Scenario:   Exam Result opens the exam results page
# Pre:        the profile menu is open
# Steps:      click Exam Result, then go back
# Expected:   /profile/exam-results with its heading, and home again afterwards
# ---------------------------------------------------------------------------

def test_exam_result_opens_the_exam_results_page(page, home_page, profile_menu):
    profile_menu.click_item("Exam Result")

    expect(page).to_have_url(EXAM_RESULTS_URL)
    expect(page.get_by_role("heading", name="Exam Results")).to_be_visible()

    return_to_home(page, home_page)


# ---------------------------------------------------------------------------
# Scenario:   Subscriptions opens the subscriptions page
# Pre:        the profile menu is open
# Steps:      click Subscriptions, then go back
# Expected:   /subscriptions with its heading, and home again afterwards
# ---------------------------------------------------------------------------

def test_subscriptions_opens_the_subscriptions_page(page, home_page, profile_menu):
    profile_menu.click_item("Subscriptions")

    expect(page).to_have_url(SUBSCRIPTIONS_URL)
    expect(page.get_by_role("heading", name="Subscription", exact=True)).to_be_visible()

    return_to_home(page, home_page)


# ---------------------------------------------------------------------------
# Scenario:   Preferences opens the preferences page
# Pre:        the profile menu is open
# Steps:      click Preferences, then go back
# Expected:   /preferences with its heading, and home again afterwards
# ---------------------------------------------------------------------------

def test_preferences_opens_the_preferences_page(page, home_page, profile_menu):
    profile_menu.click_item("Preferences")

    expect(page).to_have_url(PREFERENCES_URL)
    expect(page.get_by_role("heading", name="Preferences")).to_be_visible()

    return_to_home(page, home_page)


# ---------------------------------------------------------------------------
# Scenario:   Help centre opens the help centre
# Pre:        the profile menu is open
# Steps:      click Help centre, then close it
# Expected:   the help panel and its frame appear over the home page, and
#             closing it leaves the user back on home
# ---------------------------------------------------------------------------

def test_help_centre_opens_the_help_centre(page, profile_menu):
    profile_menu.click_item("Help centre")

    expect(profile_menu.get_help_centre_overlay()).to_be_visible()
    expect(profile_menu.get_help_centre_panel()).to_be_visible()
    expect(profile_menu.get_help_centre_frame()).to_be_attached()
    expect(page).to_have_url(HOME_URL)

    profile_menu.close_help_centre()

    expect(profile_menu.get_help_centre_overlay()).to_have_count(0)


# ---------------------------------------------------------------------------
# Scenario:   Terms & Conditions opens the terms page
# Pre:        the profile menu is open
# Steps:      click Terms & Conditions, then go back
# Expected:   /terms with its heading, and home again afterwards
# ---------------------------------------------------------------------------

def test_terms_and_conditions_opens_the_terms_page(page, home_page, profile_menu):
    profile_menu.click_item("Terms & Conditions")

    expect(page).to_have_url(TERMS_URL)
    # The page repeats the title as a section heading further down, so pin the h1.
    expect(
        page.get_by_role("heading", name="Terms & Conditions", level=1)
    ).to_be_visible()

    return_to_home(page, home_page)


# ---------------------------------------------------------------------------
# Scenario:   Customer care opens the contact sheet
# Pre:        the profile menu is open
# Steps:      click Customer care, then dismiss the sheet
# Expected:   a Contact Us sheet over the home page, gone once dismissed
# ---------------------------------------------------------------------------

def test_customer_care_opens_the_contact_sheet(page, profile_menu):
    profile_menu.click_item("Customer care")

    expect(profile_menu.get_customer_care_sheet()).to_be_visible()
    expect(profile_menu.get_customer_care_title()).to_have_text("Contact Us")
    expect(profile_menu.get_customer_care_options().first).to_be_visible()
    expect(page).to_have_url(HOME_URL)

    profile_menu.close_customer_care()

    expect(profile_menu.get_customer_care_overlay()).to_have_count(0)


# ---------------------------------------------------------------------------
# Scenario:   Sign Out asks before signing out
# Pre:        the profile menu is open
# Steps:      click Sign Out
# Expected:   a confirmation dialog with No and Yes
# ---------------------------------------------------------------------------

def test_sign_out_asks_for_confirmation(profile_menu):
    profile_menu.click_sign_out()

    expect(profile_menu.get_sign_out_dialog()).to_be_visible()
    expect(profile_menu.get_sign_out_title()).to_have_text("Sign Out!")
    expect(profile_menu.get_sign_out_subtitle()).to_have_text(
        "Are you sure you want to sign out?"
    )
    expect(profile_menu.get_sign_out_cancel_button()).to_be_visible()
    expect(profile_menu.get_sign_out_confirm_button()).to_be_visible()


# ---------------------------------------------------------------------------
# Scenario:   declining the confirmation keeps the session
# Pre:        the sign out dialog is open
# Steps:      click No
# Expected:   the dialog closes and the user is still signed in on home
# ---------------------------------------------------------------------------

def test_declining_sign_out_keeps_the_user_signed_in(page, profile_menu):
    profile_menu.click_sign_out()
    expect(profile_menu.get_sign_out_dialog()).to_be_visible()

    profile_menu.cancel_sign_out()

    expect(profile_menu.get_sign_out_dialog()).to_have_count(0)
    expect(page).to_have_url(HOME_URL)
    expect(HomePage(page).get_profile_button()).to_be_visible()
    assert session_value(page, "eduport_auth_token")


# ---------------------------------------------------------------------------
# Scenario:   signing out returns to the phone number screen
# Pre:        signed in through the login screen in a context of its own
# Steps:      open the menu, Sign Out, confirm with Yes, then ask for home
# Expected:   redirected to /login, the session is cleared and home is no
#             longer reachable without signing in again
# ---------------------------------------------------------------------------

@pytest.fixture
def signed_out_page(browser):
    """Signing out empties the session, and every other test in the run shares
    one context per account, so this scenario gets a context to itself."""
    context = browser.new_context()
    page = context.new_page()
    page.goto(LOGIN_URL)
    yield page
    context.close()


def test_sign_out_returns_to_the_login_screen(signed_out_page):
    LoginPage(signed_out_page).login(MOBILE)
    signed_out_page.wait_for_url(OTP_URL)
    OtpPage(signed_out_page).enter_otp(OTP)
    signed_out_page.wait_for_url(HOME_URL)

    home_page = HomePage(signed_out_page)
    home_page.get_subjects().first.wait_for()
    home_page.open_profile_menu()

    menu = ProfileMenuPage(signed_out_page)
    menu.click_sign_out()
    expect(menu.get_sign_out_dialog()).to_be_visible()

    menu.confirm_sign_out()

    expect(signed_out_page).to_have_url(LOGIN_URL)
    expect(LoginPage(signed_out_page).get_continue_button()).to_be_visible()
    assert session_value(signed_out_page, "eduport_auth_token") is None

    # The authenticated home page is no longer reachable.
    signed_out_page.goto(HOME_URL)

    expect(signed_out_page).to_have_url(LOGIN_URL)
    expect(HomePage(signed_out_page).get_profile_button()).to_have_count(0)
