"""The login screen: entering a number and asking for a code.

The screen is a country selector, a phone box and a Send OTP button. The button
is disabled until the box holds a full ten digit number, and the box keeps only
digits, so validation is a matter of what makes the button live rather than of
error messages.

Send OTP posts to otp/get-4-digit and, on success, moves to the OTP screen. A
number that already has a code waiting is refused by the backend and surfaces as
a toast, which is why the happy-path send is driven with a throwaway number
rather than a shared account - a shared one may still be holding a code from an
earlier test.
"""
import random

import pytest
from playwright.sync_api import expect

from pages.login_page import LoginPage
from pages.otp_page import OtpPage

LOGIN_URL = LoginPage.URL
OTP_URL = "https://eduport-react.pages.dev/otp"
TERMS_URL = "https://eduport-react.pages.dev/terms"

GET_OTP_API = "**/api/v3/otp/get-4-digit"

# Strings fed to the phone box to see what it accepts. None of them signs in,
# so they are deliberately not the suite's student number: what the box makes
# of ten digits must not change when that account is swapped for another.
TEN_DIGITS = "9876543210"
TOO_SHORT = "98765"
OVERLONG = TEN_DIGITS + "1234"
LETTERS = "qwertyuiop"
LETTERS_AND_DIGITS = "qw1234iop"


def throwaway_number():
    """A fresh number that will not be holding a code from an earlier test."""
    return str(random.randint(6100000000, 6999999999))


@pytest.fixture
def login_page(page):
    login = LoginPage(page)
    login.wait_for_loaded()
    return login


# ---------------------------------------------------------------------------
# 1. The screen
# ---------------------------------------------------------------------------

def test_login_screen_shows_its_elements(login_page):
    expect(login_page.get_page()).to_be_visible()
    expect(login_page.get_mobile_input()).to_be_visible()
    expect(login_page.get_mobile_input()).to_have_attribute("placeholder", "Enter Mobile Number")
    expect(login_page.get_send_otp_button()).to_have_text("Send OTP")
    expect(login_page.get_country_button()).to_be_visible()
    expect(login_page.get_help_button()).to_be_visible()


def test_india_is_the_default_country_code(login_page):
    assert login_page.get_country_code() == "+91"


def test_terms_link_points_at_the_terms_page(login_page):
    expect(login_page.get_terms_link()).to_have_attribute("href", "/terms")


# ---------------------------------------------------------------------------
# 2. Phone number validation
# ---------------------------------------------------------------------------

def test_send_otp_is_disabled_to_start_with(login_page):
    expect(login_page.get_send_otp_button()).to_be_disabled()


def test_send_otp_stays_disabled_below_ten_digits(login_page):
    login_page.enter_mobile(TOO_SHORT)
    expect(login_page.get_send_otp_button()).to_be_disabled()


def test_send_otp_enables_at_ten_digits(login_page):
    login_page.enter_mobile(TEN_DIGITS)
    expect(login_page.get_send_otp_button()).to_be_enabled()


def test_the_box_keeps_only_digits(login_page):
    login_page.enter_mobile(LETTERS)
    assert login_page.get_mobile_value() == ""
    expect(login_page.get_send_otp_button()).to_be_disabled()


def test_letters_mixed_with_digits_are_dropped(login_page):
    login_page.enter_mobile(LETTERS_AND_DIGITS)
    assert login_page.get_mobile_value() == "1234"
    expect(login_page.get_send_otp_button()).to_be_disabled()


def test_the_number_is_capped_at_ten_digits(login_page):
    login_page.type_mobile(OVERLONG)
    assert login_page.get_mobile_value() == TEN_DIGITS
    expect(login_page.get_send_otp_button()).to_be_enabled()


def test_clear_empties_the_box(login_page):
    login_page.enter_mobile(TEN_DIGITS)
    login_page.clear_mobile()

    assert login_page.get_mobile_value() == ""
    expect(login_page.get_send_otp_button()).to_be_disabled()


# ---------------------------------------------------------------------------
# 3. Country selector
# ---------------------------------------------------------------------------

def test_country_menu_lists_and_searches_countries(login_page):
    login_page.open_country_menu()
    expect(login_page.get_country_menu()).to_be_visible()

    login_page.search_country("United States")
    expect(login_page.get_country_items().first).to_be_visible()
    assert login_page.get_country_items().count() >= 1


def test_choosing_a_country_changes_the_dial_code(login_page):
    code = login_page.select_country("United States")

    assert code == "+1"
    assert login_page.get_country_code() == "+1"


# ---------------------------------------------------------------------------
# 4. Help
# ---------------------------------------------------------------------------

def test_help_opens_the_contact_sheet(login_page):
    login_page.click_help()

    expect(login_page.get_contact_sheet()).to_be_visible()
    expect(login_page.get_contact_sheet_title()).to_have_text("Contact Us")


# ---------------------------------------------------------------------------
# 5. Send OTP flow  (API + UI)
# ---------------------------------------------------------------------------

def test_sending_a_code_moves_to_the_otp_screen_and_calls_the_api(page, login_page):
    """A fresh number is accepted, the app posts get-4-digit, and the OTP
    screen comes up carrying that same number."""
    mobile = throwaway_number()

    with page.expect_response(GET_OTP_API) as answer:
        login_page.login(mobile)
    assert answer.value.status == 200, answer.value.json()
    assert answer.value.json()["message"] == "OTP sent successfully."

    # What was posted is the chosen code and the number entered.
    posted = answer.value.request.post_data
    assert "+91" + mobile in posted.replace(" ", "")

    page.wait_for_url(OTP_URL, timeout=30000)
    expect(OtpPage(page).get_phone_badge()).to_contain_text(mobile)
