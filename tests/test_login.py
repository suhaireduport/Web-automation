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

from conftest import STUDENT_MOBILE
from pages.home_page import HomePage
from pages.login_page import LoginPage
from pages.otp_page import OtpPage

LOGIN_URL = LoginPage.URL
OTP_URL = "https://eduport-react.pages.dev/otp"
TERMS_URL = "https://eduport-react.pages.dev/terms"
HOME_URL = "https://eduport-react.pages.dev/"
EXAMS_URL = "https://eduport-react.pages.dev/exams"

GET_OTP_API = "**/api/v3/otp/get-4-digit"
CONTACT_API = "**/api/v3/onboarding/contact"

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


# ---------------------------------------------------------------------------
# 6. Where the screen sends people who should not be on it
# ---------------------------------------------------------------------------

def test_a_signed_in_visitor_is_sent_to_home(login_as):
    """The screen is for guests: a session already in the browser is carried
    past it rather than asked to sign in again."""
    page = login_as(STUDENT_MOBILE)

    page.goto(LOGIN_URL, wait_until="domcontentloaded")

    expect(page).to_have_url(HOME_URL)
    HomePage(page).wait_for_loaded()


@pytest.mark.parametrize("route", [HOME_URL, EXAMS_URL], ids=["home", "exams"])
def test_a_logged_out_visitor_is_sent_to_login(page, route):
    """Everything behind the sign in is shut to a browser holding no session,
    including a link followed straight to an inner page."""
    page.goto(route, wait_until="domcontentloaded")

    expect(page).to_have_url(LOGIN_URL)
    expect(LoginPage(page).get_mobile_input()).to_be_visible()


# ---------------------------------------------------------------------------
# 7. A send the backend will not take  (API + UI)
# ---------------------------------------------------------------------------

def test_a_refused_send_keeps_the_user_on_login_and_says_so(page, login_page):
    """A send the backend turns down leaves the screen where it is, says so, and
    gives the button back so it can be tried again.

    The failure is served rather than provoked: the refusals this screen meets
    are the backend's own state - a code already live for the number, a number
    it will not take - and none of them can be arranged from here to order. What
    is being checked is what the screen does with a refusal, and that is the
    same whichever one it is. Note that whatever the backend says is not what is
    shown: the screen has one line for every failure."""
    page.route(
        GET_OTP_API,
        lambda route: route.fulfill(
            status=400, json={"message": "A valid OTP already exists. Please verify or wait."}
        ),
    )

    with page.expect_response(GET_OTP_API) as answer:
        login_page.login(throwaway_number())
    assert answer.value.status == 400

    expect(login_page.get_toast("Failed to send OTP. Please try again.")).to_be_visible()
    expect(page).to_have_url(LOGIN_URL)
    expect(login_page.get_send_otp_button()).to_be_enabled()
    expect(login_page.get_send_spinner()).to_have_count(0)


def test_send_otp_is_locked_while_the_request_is_out(page, login_page):
    """Hold the send open so the state it puts the button in cannot be missed:
    the label gives way to a spinner and the button cannot be pressed again, so
    one tap cannot become two requests."""
    held = []
    page.route(GET_OTP_API, lambda route: held.append(route))

    login_page.enter_mobile(TEN_DIGITS)
    login_page.click_continue()

    expect(login_page.get_send_spinner()).to_be_visible()
    expect(login_page.get_send_otp_button()).to_be_disabled()
    expect(page).to_have_url(LOGIN_URL)
    assert len(held) == 1


# ---------------------------------------------------------------------------
# 8. The country decides the number  (API + UI)
#
# A number is not ten digits everywhere. Each country carries its own length,
# and the box and the button both follow the country chosen rather than the
# ten digits India happens to want.
#
# These do not spend a real code. What is being checked is what the screen
# makes of the country - what it keeps, when it unlocks, and what it posts -
# so the send is answered in the browser and no message is sent to a number
# nobody owns.
# ---------------------------------------------------------------------------

# Australia's numbers are nine digits, where India's are ten.
NINE_DIGIT_COUNTRY = "Australia"
NINE_DIGIT_CODE = "+61"


def serve_otp_sent(page):
    """Answer the send in the browser, the way the backend answers a good one."""
    posted = {}

    def handler(route):
        posted["body"] = route.request.post_data
        route.fulfill(status=200, json={"message": "OTP sent successfully."})

    page.route(GET_OTP_API, handler)
    return posted


def test_the_number_length_follows_the_country_chosen(login_page):
    """Nine digits is a whole number for Australia: the box stops there and the
    button unlocks there, where under India it would still be waiting."""
    assert login_page.select_country(NINE_DIGIT_COUNTRY) == NINE_DIGIT_CODE

    login_page.type_mobile(TEN_DIGITS)
    assert login_page.get_mobile_value() == TEN_DIGITS[:9]
    expect(login_page.get_send_otp_button()).to_be_enabled()

    login_page.enter_mobile(TEN_DIGITS[:8])
    expect(login_page.get_send_otp_button()).to_be_disabled()


def test_the_dial_code_posted_is_the_country_chosen(page, login_page):
    """What goes to the backend is the number under the country on screen, not
    the one it opened on."""
    posted = serve_otp_sent(page)
    login_page.select_country(NINE_DIGIT_COUNTRY)
    number = TEN_DIGITS[:9]

    with page.expect_response(GET_OTP_API):
        login_page.login(number)

    assert (NINE_DIGIT_CODE + number) in posted["body"].replace(" ", "")
    assert "+91" not in posted["body"]


def test_enter_sends_the_code_from_the_phone_box(page, login_page):
    """A whole number is sent by pressing Enter in the box, and a part of one is
    not sent at all."""
    posted = serve_otp_sent(page)

    login_page.enter_mobile(TOO_SHORT)
    login_page.press_enter()
    page.wait_for_timeout(1000)
    assert posted == {}
    expect(page).to_have_url(LOGIN_URL)

    login_page.enter_mobile(TEN_DIGITS)
    with page.expect_response(GET_OTP_API):
        login_page.press_enter()

    assert TEN_DIGITS in posted["body"].replace(" ", "")
    page.wait_for_url(OTP_URL, timeout=30000)


# ---------------------------------------------------------------------------
# 9. Finding a country
# ---------------------------------------------------------------------------

def test_the_country_search_matches_dial_codes_and_says_when_nothing_does(login_page):
    """The search is not only by name: a dial code typed into it finds the
    country that carries it, and a query that is neither leaves the list saying
    so rather than empty."""
    login_page.open_country_menu()

    login_page.search_country(NINE_DIGIT_CODE)
    expect(login_page.get_country_items().first).to_be_visible()
    codes = [
        item.strip()
        for item in login_page.get_country_item_codes().all_inner_texts()
    ]
    assert codes and all(NINE_DIGIT_CODE in code for code in codes)

    login_page.search_country("zzzzzz")
    expect(login_page.get_country_items()).to_have_count(0)
    expect(login_page.get_country_empty_message()).to_have_text("No countries found")


def test_the_country_menu_closes_on_an_outside_tap(login_page):
    """Tapping away shuts the menu and leaves the country as it was."""
    login_page.open_country_menu()
    expect(login_page.get_active_country_item()).to_have_count(1)

    login_page.close_country_menu()

    expect(login_page.get_country_menu()).to_have_count(0)
    assert login_page.get_country_code() == "+91"


# ---------------------------------------------------------------------------
# 10. Help  (API + UI)
# ---------------------------------------------------------------------------

def test_the_contact_sheet_offers_the_channels_the_api_returns_and_closes(page, login_page):
    """The sheet is not a fixed pair of buttons: the contact call decides which
    channels the help desk is offering, and only the ones it marks visible are
    drawn."""
    with page.expect_response(CONTACT_API) as answer:
        login_page.click_help()
    assert answer.value.status == 200
    desk = answer.value.json()["help_desk"]

    expected = []
    if desk.get("whatsapp", {}).get("visibility"):
        expected.append("Whatsapp")
    if desk.get("phone_number", {}).get("visibility"):
        expected.append("Contact Us")

    expect(login_page.get_contact_sheet()).to_be_visible()
    expect(login_page.get_contact_options()).to_have_count(len(expected))
    assert login_page.get_contact_option_labels() == expected

    login_page.close_contact_sheet_with_escape()
    expect(login_page.get_contact_sheet()).to_have_count(0)

    login_page.click_help()
    expect(login_page.get_contact_sheet()).to_be_visible()
    login_page.close_contact_sheet_with_backdrop()
    expect(login_page.get_contact_sheet()).to_have_count(0)
