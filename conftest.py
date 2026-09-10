import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

BASE_URL = "https://eduport-react.pages.dev"
LOGIN_URL = f"{BASE_URL}/login"
OTP_URL = f"{BASE_URL}/otp"
HOME_URL = f"{BASE_URL}/"
DEFAULT_OTP = "4305"

# The registered students the suite signs in as.
#
# STUDENT_MOBILE is the default: every test module signs in as this one unless
# it has a reason not to.
#
# SECOND_STUDENT_MOBILE exists because a few things cannot be shared. An exam
# attempt cannot be made twice, an answered practice question leaves the pool
# for good, and asking for a real OTP leaves a live code on the number that
# blocks the next sign-in. Six modules hold one of those against the second
# account so they are not spending what the rest of the suite reads, and each
# says why where it picks the account: test_coins_connections.py (needs both
# at once), test_otp.py (real OTP sends), test_live_exam.py (spends an exam
# attempt), test_ql_bookmark.py, test_ql_mistake_book.py and
# test_practice_questions.py (spend practice questions). Nothing else should
# use it.
#
# Numbers belonging to a single test - a throwaway for a fresh signup, an
# account in a particular subscription state, a string being fed to the login
# box to check what it accepts - stay in the test that needs them.
STUDENT_MOBILE = "9876543210"
SECOND_STUDENT_MOBILE = "8893963137"

# Headless by default because it is much faster. Run with HEADED=1 to watch.
HEADLESS = os.getenv("HEADED", "").lower() not in ("1", "true", "yes")

# Spoken audio fed to the fake microphone so voice recordings transcribe to real
# words instead of the default beep.
VOICE_SAMPLE = Path(__file__).parent / "tests" / "data" / "voice_question.wav"

# The question library onboarding covers the home page a couple of seconds
# after it renders and swallows every click underneath, so it has to be closed
# before a test can do anything. It is shown once per account and remembers
# being closed, which is what SPLASH_SEEN_KEY holds.
SPLASH_SEEN_KEY = "eduport_ql_onboarding_seen"
SPLASH_TIMEOUT = 5000


@pytest.fixture(scope="session")
def browser():
    """One browser for the whole run instead of one per test."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=HEADLESS,
            # Feed a synthetic mic so voice recording works without hardware
            # and without a permission prompt.
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
            ]
            + (
                [f"--use-file-for-fake-audio-capture={VOICE_SAMPLE}"]
                if VOICE_SAMPLE.exists()
                else []
            ),
        )
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """A logged out page sitting on the login screen.

    Test modules that need a signed in user shadow this fixture with their own
    that calls login_as()."""
    context = browser.new_context(permissions=["microphone"])
    page = context.new_page()
    page.goto(LOGIN_URL)
    yield page
    context.close()


@pytest.fixture(scope="session")
def _auth_states():
    return {}


@pytest.fixture(scope="session")
def _contexts():
    """One browser context per account, kept open for the whole run.

    Reusing the context keeps the HTTP cache warm; a fresh context per test
    re-downloads the ~5MB app bundle every time, which dominated the runtime."""
    contexts = {}
    yield contexts
    for context in contexts.values():
        context.close()


def _dismiss_intro_splash(page):
    """Close the intro splash if this page gets one.

    Optional by design: an account that has already dismissed it carries the
    flag, so the usual case costs nothing and nothing here waits on a splash
    that is never coming."""
    if page.evaluate("key => localStorage.getItem(key)", SPLASH_SEEN_KEY):
        return

    splash = page.locator(".qlob-overlay")
    try:
        splash.wait_for(timeout=SPLASH_TIMEOUT)
    except Exception:
        return

    page.locator(".qlob-close").click()
    splash.wait_for(state="detached")


# The login screen carries a country selector and a button that now reads
# "Send OTP"; the phone box is its only text field.
#
# Sending a code is refused while one is still live for that number ("A valid
# OTP already exists"), which leaves the app on the login screen instead of
# moving to /otp. A code left by an earlier test clears in well under a minute,
# so the send is retried rather than treated as a failure.
SEND_OTP_ATTEMPTS = 4
SEND_OTP_RETRY_MS = 20000


def _sign_in(page, mobile, otp):
    """Take a fresh page from the login screen through to home, signed in."""
    for attempt in range(SEND_OTP_ATTEMPTS):
        page.goto(LOGIN_URL)
        page.locator(".dl-phone-input").fill(mobile)
        page.get_by_role("button", name="Send OTP").click()
        try:
            page.wait_for_url(OTP_URL, timeout=8000)
            break
        except Exception:
            if attempt == SEND_OTP_ATTEMPTS - 1:
                raise AssertionError(
                    f"Send OTP would not go through for {mobile}: a code is "
                    "still live for it"
                )
            page.wait_for_timeout(SEND_OTP_RETRY_MS)

    # The code is four boxes that take keystrokes rather than a value set on
    # them, and the form submits itself the moment the fourth digit lands -
    # there is no button to press.
    page.locator(".otp-box").first.wait_for()
    page.locator(".otp-box").first.click()
    page.keyboard.type(otp)
    page.wait_for_url(HOME_URL)


def _signed_in_page(browser, auth_states, contexts, mobile, otp):
    """Open a page already signed in as the given mobile number.

    The OTP is requested once per number per session and the resulting session
    is replayed into every later context. That keeps the suite fast and avoids
    the "A valid OTP already exists. Please verify or wait." lockout that back
    to back logins on the same number trigger."""
    if mobile not in auth_states:
        context = browser.new_context(permissions=["microphone"])
        page = context.new_page()
        _sign_in(page, mobile, otp)
        page.wait_for_timeout(3000)
        auth_states[mobile] = context.storage_state()
        context.close()

    if mobile not in contexts:
        contexts[mobile] = browser.new_context(
            storage_state=auth_states[mobile],
            permissions=["microphone"],
        )

    page = contexts[mobile].new_page()
    # "load" waits for every banner, video and analytics script on the home
    # page, which costs far more than the page needs to be usable.
    page.goto(HOME_URL, wait_until="domcontentloaded")
    _dismiss_intro_splash(page)
    return page


@pytest.fixture
def login_as(browser, _auth_states, _contexts):
    """Return a page already signed in as the given mobile number."""
    pages = []

    def _login(mobile, otp=DEFAULT_OTP):
        page = _signed_in_page(browser, _auth_states, _contexts, mobile, otp)
        pages.append(page)
        return page

    yield _login

    for page in pages:
        page.close()


@pytest.fixture(scope="session")
def login_session(browser, _auth_states, _contexts):
    """login_as for a page that has to outlive a single test.

    Starting an exam consumes it permanently - the backend answers a second
    exam-start with 406 - so the live exam tests share one attempt for the whole
    run rather than burning an exam per test."""
    pages = []

    def _login(mobile, otp=DEFAULT_OTP):
        page = _signed_in_page(browser, _auth_states, _contexts, mobile, otp)
        pages.append(page)
        return page

    yield _login

    for page in pages:
        page.close()
