from pages.login_page import LoginPage
from playwright.sync_api import expect

def test_valid_login(page):
    login_page = LoginPage(page)
    login_page.login("9876543200")
    #page.wait_for_url("https://eduport-react.pages.dev/otp")
    #assert page.url == "https://eduport-react.pages.dev/otp"
    expect(page).to_have_url("https://eduport-react.pages.dev/otp")

def test_continue_button_disabled_for_less_than_10_digits(page):
    login_page = LoginPage(page)
    continue_button = login_page.get_continue_button()

    login_page.enter_mobile("98543210")
    expect(continue_button).to_be_disabled()

def test_continue_button_enabled_for_10_digits(page):
    login_page = LoginPage(page)
    continue_button = login_page.get_continue_button()

    login_page.enter_mobile("9876543210")
    
    expect(continue_button).to_be_enabled()
#     assert continue_button.is_enabled()


def test_empty_mobile(page):
    login_page = LoginPage(page)
    continue_button = login_page.get_continue_button()
#     assert continue_button.is_disabled()
    expect(continue_button).to_be_disabled()



def test_text_only(page):
    login_page = LoginPage(page)
    continue_button = login_page.get_continue_button()

    login_page.enter_mobile("qwertyuiop")

    expect(continue_button).to_be_disabled()
#     assert continue_button.is_disabled()


def test_text_and_number(page):
    login_page = LoginPage(page)
    continue_button = login_page.get_continue_button()

    login_page.enter_mobile("qw1234iop")
    expect(continue_button).to_be_disabled()
#     assert continue_button.is_disabled()


