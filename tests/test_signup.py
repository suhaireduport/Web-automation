"""New user signup, entered the way the app is actually used: from the phone
number screen.

The number decides the branch. An unknown one verifies its OTP and lands on the
signup form; a known one goes straight to the home page. Nothing here opens
/signup directly.
"""
import random
import re
import string

import pytest
from playwright.sync_api import expect

from pages.login_page import LoginPage
from pages.otp_page import OtpPage
from pages.home_page import HomePage
from pages.signup_page import SignupPage

OTP = "430582"

OTP_URL = "https://eduport-react.pages.dev/otp"
HOME_URL = "https://eduport-react.pages.dev/"
SIGNUP_URL = "https://eduport-react.pages.dev/signup"
AFTER_OTP_URL_PATTERN = re.compile(
    r"https://eduport-react\.pages\.dev/(signup)?$"
)

# Reserved for signups, so a run does not collide with the accounts the rest of
# the suite signs in as.
MOBILE_RANGE = (5000000000, 5000055555)

# An account that already exists, for the other side of the branch.
EXISTING_MOBILE = "9037929697"

DATE_OF_BIRTH = "2005-05-15"


def random_mobile():
    return str(random.randint(*MOBILE_RANGE))


def random_name():
    """Test plus a random suffix, so every signup is identifiable and no two
    runs enter the same name."""
    return "Test " + "".join(random.choices(string.ascii_uppercase, k=6))


def verify_otp(page, mobile):
    """The project's own login and OTP flow, no shortcut."""
    LoginPage(page).login(mobile)
    page.wait_for_url(OTP_URL)

    OtpPage(page).enter_otp(OTP)
    page.wait_for_url(AFTER_OTP_URL_PATTERN, timeout=30000)


@pytest.fixture
def signup_page(page):
    """A new number taken through login and OTP as far as the signup form."""
    mobile = random_mobile()
    verify_otp(page, mobile)

    if page.url != SIGNUP_URL:
        pytest.skip(f"{mobile} already belongs to a user, so no signup was asked for")

    signup = SignupPage(page)
    expect(signup.get_page()).to_be_visible()
    return signup


# ---------------------------------------------------------------------------
# Which branch the number takes
# ---------------------------------------------------------------------------

def test_a_new_number_is_taken_to_the_signup_page(page, signup_page):
    expect(page).to_have_url(SIGNUP_URL)
    expect(signup_page.get_form()).to_be_visible()


def test_an_existing_number_goes_straight_to_home(page):
    verify_otp(page, EXISTING_MOBILE)

    expect(page).to_have_url(HOME_URL)
    expect(SignupPage(page).get_page()).to_have_count(0)
    expect(HomePage(page).get_greeting()).to_contain_text("Hello,")


# ---------------------------------------------------------------------------
# The signup form
# ---------------------------------------------------------------------------

def test_signup_form_asks_for_the_expected_details(signup_page):
    for label in ["Full name", "Date of Birth", "Gender", "Board", "Class", "Course"]:
        expect(signup_page.get_field(label)).to_have_count(1)

    expect(signup_page.get_full_name_input()).to_be_visible()
    expect(signup_page.get_date_of_birth_input()).to_be_visible()
    expect(signup_page.get_continue_button()).to_be_visible()


def test_signup_form_offers_courses_to_choose_from(signup_page):
    expect(signup_page.get_course_select()).to_be_visible()

    assert len(signup_page.get_course_options()) > 0


def test_signup_form_starts_empty(signup_page):
    expect(signup_page.get_full_name_input()).to_have_value("")


# ---------------------------------------------------------------------------
# The whole flow
# ---------------------------------------------------------------------------

def test_new_user_signup_lands_on_home_with_the_entered_name_and_course(page, signup_page):
    name = random_name()

    signup_page.enter_full_name(name)
    signup_page.enter_date_of_birth(DATE_OF_BIRTH)
    signup_page.select_first_option("Gender")

    # Board narrows Class, and Class narrows Course, so each list is only read
    # once the one before it has been answered.
    signup_page.select_first_option("Board")
    page.wait_for_timeout(1500)
    signup_page.select_first_option("Class")
    page.wait_for_timeout(1500)
    course = signup_page.select_first_option("Course")
    page.wait_for_timeout(4000)

    signup_page.click_continue()
    page.wait_for_url(HOME_URL, timeout=30000)

    home_page = HomePage(page)
    page.wait_for_timeout(2000)


    expect(home_page.get_greeting()).to_have_text(f"Hello, {name}")
    expect(home_page.get_course_button()).to_have_text(course)
    expect(home_page.get_subjects().first).to_be_visible()
