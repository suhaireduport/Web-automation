from pages.login_page import LoginPage
from pages.otp_page import OtpPage
import random
from playwright.sync_api import expect


def test_valid_otp_existing_user(page):
    login_page = LoginPage(page)
    login_page.login("9037929697")
    page.wait_for_url("https://eduport-react.pages.dev/otp")    

    otp_page = OtpPage(page)
    otp_page.enter_otp("430582")
    print(page.url)
    expect(page).to_have_url("https://eduport-react.pages.dev/")

def test_valid_otp_new_user(page):
    login_page = LoginPage(page)
    login_page.login(str(random.randint(6000000000,7000000000)))
    page.wait_for_url("https://eduport-react.pages.dev/otp")

    otp_page = OtpPage(page)
    otp_page.enter_otp("430582")
    print(page.url)
    expect(page).not_to_have_url("https://eduport-react.pages.dev/signup")

def test_incomplete_otp(page):
    login_page = LoginPage(page)
    login_page.login("8893962137")
    page.wait_for_url("https://eduport-react.pages.dev/otp")    

    otp_page = OtpPage(page)
    continue_button = otp_page.get_continue_button()

    otp_page.enter_otp("43582")
    expect(continue_button).to_be_disabled()


def test_invalid_otp(page):
    login_page = LoginPage(page)
    login_page.login("8893463137")

    page.wait_for_url("https://eduport-react.pages.dev/otp")

    otp_page = OtpPage(page)
    otp_page.enter_otp("123456")
    invalid_message = otp_page.get_invalid_otp_message()
    expect(invalid_message).to_be_visible()

def test_valid_otp_after_invalid_otp(page):
    login_page = LoginPage(page)
    login_page.login("7736140338")

    page.wait_for_url("https://eduport-react.pages.dev/otp")

    otp_page = OtpPage(page)
    otp_page.enter_otp("123456")

    page.wait_for_timeout(1000)
    otp_page.enter_otp("430582")
    expect(page).to_have_url("https://eduport-react.pages.dev/")

def test_empty_otp(page):
    login_page = LoginPage(page)
    login_page.login("8893963137")

    page.wait_for_url("https://eduport-react.pages.dev/otp")

    otp_page = OtpPage(page)
    continue_button = otp_page.get_continue_button()

    expect(continue_button).to_be_disabled()


def test_invalid_otp_format(page):
    login_page = LoginPage(page)
    login_page.login("8893963137")

    page.wait_for_url("https://eduport-react.pages.dev/otp")

    otp_page = OtpPage(page)
    otp_page.enter_otp("abc123")

    continue_button = otp_page.get_continue_button()

    expect(continue_button).to_be_disabled()


def test_resend_otp_options(page):
    login_page = LoginPage(page)
    login_page.login("8893963137")

    page.wait_for_url("https://eduport-react.pages.dev/otp")

    otp_page = OtpPage(page)


    resend_sms = otp_page.get_resend_otp_sms()
    resend_whatsapp = otp_page.get_resend_otp_whatsapp()

    expect(resend_sms).to_be_enabled(timeout=35000)
    expect(resend_whatsapp).to_be_enabled(timeout=35000)

def test_resend_via_sms_click(page):
    login_page = LoginPage(page)
    login_page.login(str(random.randint(1000000000,2000000000)))

    page.wait_for_url("https://eduport-react.pages.dev/otp")

    otp_page = OtpPage(page)

    resend_sms = otp_page.get_resend_otp_sms()
    resend_whatsapp = otp_page.get_resend_otp_whatsapp()

    expect(resend_sms).to_be_enabled(timeout=35000)
    expect(resend_whatsapp).to_be_enabled(timeout=35000)
    otp_page.click_resend_otp_sms()
    sms_popup = otp_page.get_resend_otp_sms_popup()
    page.wait_for_timeout(2000)
    expect(sms_popup).to_be_visible()

def test_resend_via_whatsapp_click(page):
    login_page = LoginPage(page)
    login_page.login(str(random.randint(1000000000,2000000000)))

    page.wait_for_url("https://eduport-react.pages.dev/otp")

    otp_page = OtpPage(page)

    resend_sms = otp_page.get_resend_otp_sms()
    resend_whatsapp = otp_page.get_resend_otp_whatsapp()

    expect(resend_sms).to_be_enabled(timeout=35000)
    expect(resend_whatsapp).to_be_enabled(timeout=35000)
    otp_page.click_resend_otp_whatsapp()
    whatsapp_popup = otp_page.get_resend_otp_whatsapp_popup()
    page.wait_for_timeout(2000)
    expect(whatsapp_popup).to_be_visible()