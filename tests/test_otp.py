"""The OTP screen: verifying a code.

The code is four boxes that take keystrokes, and the form submits itself the
moment the fourth digit lands - there is no button to press and the visible
"Verify & Continue" stays disabled throughout. So an incomplete code is simply
one that has not submitted yet, and a complete code is a submission.

Verifying posts to otp/verify. A valid code moves on - to home for an account
whose profile is complete, to the new-user details form for a number the
backend has never seen. A wrong code is answered 400, clears the boxes and
raises a toast.

Each test starts from a fresh throwaway number so that get-4-digit is not
refused by a code left waiting from an earlier test, except where an existing
account is needed to prove the signed-in destination.
"""
import random

import pytest
from playwright.sync_api import expect

from conftest import SECOND_STUDENT_MOBILE
from pages.login_page import LoginPage
from pages.otp_page import OtpPage
from pages.signup_page import SignupPage

OTP = "4305"

LOGIN_URL = LoginPage.URL
OTP_URL = OtpPage.URL
HOME_URL = "https://eduport-react.pages.dev/"
NEW_USER_URL = "https://eduport-react.pages.dev/new-user"

VERIFY_API = "**/api/v3/otp/verify"

# An existing account whose profile is complete, so a valid code lands on home.
#
# The second student rather than the main one because this file asks for real
# codes: a send leaves a live OTP on the number, and conftest signs the rest of
# the suite in on the main student, where that would meet "A valid OTP already
# exists. Please verify or wait."
EXISTING_MOBILE = SECOND_STUDENT_MOBILE


def throwaway_number():
    return str(random.randint(6100000000, 6999999999))


def start_otp(page, mobile):
    """Drive login for a number and hand back the OTP screen it lands on."""
    login = LoginPage(page)
    login.wait_for_loaded()
    login.login(mobile)
    page.wait_for_url(OTP_URL, timeout=30000)

    otp_page = OtpPage(page)
    otp_page.wait_for_loaded()
    return otp_page


@pytest.fixture
def otp_new_number(page):
    """The OTP screen for a fresh number - safe to get wrong and to leave."""
    return start_otp(page, throwaway_number())


# ---------------------------------------------------------------------------
# 1. The screen
# ---------------------------------------------------------------------------

def test_otp_screen_shows_four_boxes_and_the_number(otp_new_number):
    expect(otp_new_number.get_title()).to_have_text("OTP Verifications")
    assert otp_new_number.box_count() == 4
    expect(otp_new_number.get_phone_badge()).to_be_visible()


def test_the_number_the_code_went_to_is_shown(page):
    mobile = throwaway_number()
    otp_page = start_otp(page, mobile)

    expect(otp_page.get_phone_badge()).to_contain_text(mobile)
    expect(otp_page.get_phone_badge()).to_contain_text("+91")


# ---------------------------------------------------------------------------
# 2. Input behaviour
# ---------------------------------------------------------------------------

def test_typing_walks_the_focus_along_the_boxes(otp_new_number):
    otp_new_number.get_boxes().first.click()
    otp_new_number.type_digit("1")
    assert otp_new_number.focused_box_index() == 1

    otp_new_number.type_digit("2")
    assert otp_new_number.focused_box_index() == 2
    assert otp_new_number.get_box_values()[:2] == ["1", "2"]


def test_backspace_deletes_the_last_digit(otp_new_number):
    otp_new_number.get_boxes().first.click()
    otp_new_number.type_digit("1")
    otp_new_number.type_digit("2")
    otp_new_number.press_backspace()

    # Backspace clears one box and steps focus back, rather than wiping the
    # whole code.
    assert otp_new_number.get_box_values() == ["1", "", "", ""]
    assert otp_new_number.focused_box_index() == 1


def test_an_incomplete_code_does_not_submit(page, otp_new_number):
    """Three digits is not a submission: the app makes no verify call and the
    screen stays put."""
    verified = []
    page.on("response", lambda r: verified.append(r) if "otp/verify" in r.url else None)

    otp_new_number.get_boxes().first.click()
    otp_new_number.type_digit("1")
    otp_new_number.type_digit("2")
    otp_new_number.type_digit("3")
    page.wait_for_timeout(1500)

    assert verified == []
    expect(page).to_have_url(OTP_URL)


def test_the_verify_button_stays_disabled(otp_new_number):
    """The visible button never becomes the way to submit; a complete code
    posts on its own."""
    expect(otp_new_number.get_verify_button()).to_be_disabled()

    otp_new_number.get_boxes().first.click()
    otp_new_number.type_digit("1")
    otp_new_number.type_digit("2")
    otp_new_number.type_digit("3")
    expect(otp_new_number.get_verify_button()).to_be_disabled()


# ---------------------------------------------------------------------------
# 3. Invalid code  (API + UI)
# ---------------------------------------------------------------------------

def test_a_wrong_code_is_rejected_and_clears_the_boxes(page, otp_new_number):
    with page.expect_response(VERIFY_API) as answer:
        otp_new_number.enter_otp("1357")
    assert answer.value.status == 400
    assert "Invalid OTP" in answer.value.json()["message"]

    expect(otp_new_number.get_invalid_otp_message()).to_be_visible()
    expect(page).to_have_url(OTP_URL)
    assert otp_new_number.get_box_values() == ["", "", "", ""]


def test_a_valid_code_after_a_wrong_one_still_gets_through(page):
    """A wrong code does not lock the screen: the boxes clear and the right
    code, typed next, verifies."""
    otp_page = start_otp(page, throwaway_number())

    otp_page.enter_otp("1357")
    expect(otp_page.get_invalid_otp_message()).to_be_visible()
    otp_page.get_boxes().first.wait_for()

    with page.expect_response(VERIFY_API) as answer:
        otp_page.enter_otp(OTP)
    assert answer.value.status == 200

    # A brand new number verifies onto the new-user form.
    page.wait_for_url(NEW_USER_URL, timeout=30000)


# ---------------------------------------------------------------------------
# 4. Valid code and where it lands  (API + UI)
# ---------------------------------------------------------------------------

def test_a_new_number_verifies_onto_the_new_user_form(page):
    """A number the backend has never seen is verified with a token that says
    the profile is not complete, and the app opens the new-user details form."""
    otp_page = start_otp(page, throwaway_number())

    with page.expect_response(VERIFY_API) as answer:
        otp_page.enter_otp(OTP)
    body = answer.value.json()
    assert answer.value.status == 200
    assert body["token"]
    assert body["is_profile_completed"] is False

    page.wait_for_url(NEW_USER_URL, timeout=30000)
    expect(SignupPage(page).get_title()).to_be_visible()


def test_an_existing_account_verifies_onto_home(page):
    """An account whose profile is complete verifies straight onto home."""
    otp_page = start_otp(page, EXISTING_MOBILE)

    with page.expect_response(VERIFY_API) as answer:
        otp_page.enter_otp(OTP)
    body = answer.value.json()
    assert answer.value.status == 200
    assert body["is_profile_completed"] is True

    page.wait_for_url(HOME_URL, timeout=30000)


# ---------------------------------------------------------------------------
# 5. Resend
# ---------------------------------------------------------------------------

def test_resend_is_locked_behind_a_countdown(otp_new_number):
    """Resend is not offered straight away: a countdown runs and no Resend
    button is on screen while it does."""
    assert otp_new_number.resend_seconds_left() > 0
    expect(otp_new_number.get_resend_button()).to_have_count(0)


def test_resend_appears_once_the_countdown_ends(otp_new_number):
    """After the countdown a single Resend OTP button appears - the old split
    of SMS and WhatsApp is gone."""
    assert otp_new_number.resend_available(timeout=45000)
    expect(otp_new_number.get_resend_button()).to_be_visible()
    expect(otp_new_number.get_resend_button()).to_have_text("Resend OTP")


def test_resend_asks_for_a_fresh_code(page, otp_new_number):
    """Tapping Resend posts otp/resend for the same number and restarts the
    countdown, which locks the button away again."""
    assert otp_new_number.resend_available(timeout=45000)

    with page.expect_response("**/api/v3/otp/resend") as answer:
        otp_new_number.click_resend()
    assert answer.value.status == 200

    page.wait_for_timeout(1000)
    assert otp_new_number.resend_seconds_left() > 0
    expect(otp_new_number.get_resend_button()).to_have_count(0)
