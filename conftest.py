import base64
import html
import os
import re
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

try:
    from pytest_html import extras as html_extras
except ImportError:  # pytest-html not installed, or switched off with -p no:html
    html_extras = None

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
STUDENT_MOBILE = "9037929697"
SECOND_STUDENT_MOBILE = "9037929697"

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


# The Page Objects live under tests/, which pytest only puts on sys.path once it
# starts collecting test modules - after this file has been imported - so they
# are imported where they are used rather than at the top.


def _dismiss_intro_splash(page):
    """Close the intro splash if this page gets one.

    Optional by design: an account that has already dismissed it carries the
    flag, so the usual case costs nothing and nothing here waits on a splash
    that is never coming."""
    from pages.home_page import HomePage

    if page.evaluate("key => localStorage.getItem(key)", SPLASH_SEEN_KEY):
        return

    home_page = HomePage(page)
    splash = home_page.get_intro_splash()
    try:
        splash.wait_for(timeout=SPLASH_TIMEOUT)
    except Exception:
        return

    home_page.get_intro_close().click()
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
    from pages.login_page import LoginPage
    from pages.otp_page import OtpPage

    login_page = LoginPage(page)
    for attempt in range(SEND_OTP_ATTEMPTS):
        page.goto(LOGIN_URL)
        login_page.enter_mobile(mobile)
        login_page.get_send_otp_button().click()
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
    OtpPage(page).enter_otp(otp)
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


# ---------------------------------------------------------------------------
# HTML report extras (pytest-html; pytest.ini switches the report on).
#
# Every failed test gets a screenshot of the page it was driving and a one-line
# Failure Explanation column. Both are added to the report only: nothing here
# changes how a test runs or whether it passes, and Allure is left alone.
# ---------------------------------------------------------------------------

SCREENSHOT_TIMEOUT = 5000
EXPLANATION_LIMIT = 300


def _page_for_screenshot(item):
    """The page the failing test was driving.

    The first Playwright page among the test's fixtures. Tests that reach the
    page through something else (a session fixture, a dict of results) fall
    back to the newest page still open in the shared browser."""
    values = list(getattr(item, "funcargs", {}).values())
    for value in values:
        if isinstance(value, Page) and not value.is_closed():
            return value
    for value in values:
        if isinstance(value, Browser):
            open_pages = [
                page
                for context in value.contexts
                for page in context.pages
                if not page.is_closed()
            ]
            if open_pages:
                return open_pages[-1]
    return None


def _short(text):
    text = " ".join(text.split())
    return text if len(text) <= EXPLANATION_LIMIT else text[:EXPLANATION_LIMIT] + "…"


def _explain_failure(excinfo, when):
    """A plain-language reason for a failure, read off the exception."""
    error = excinfo.value
    kind = type(error).__name__
    message = str(error).strip()
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    first = lines[0] if lines else kind

    waiting = re.search(r"waiting for (.+)", message)
    target = waiting.group(1).strip() if waiting else None
    actual = re.search(r"Actual value: (.+)", message)

    if when == "setup":
        if "Send OTP would not go through" in message:
            return (
                "Setup failed at login: the OTP could not be sent because a "
                "code is still live for this number (OTP lockout). Usually "
                "passes on a re-run a minute later."
            )
        return _short(
            f"The test never started: a fixture (login, browser or test data) "
            f"failed during setup with {kind}: {first}"
        )

    if kind == "TimeoutError":
        reason = f"Timed out: {first}"
        if target:
            reason += f" Waiting for {target}."
        return _short(
            reason + " The element was missing, hidden or renamed, or the page "
            "or API was too slow."
        )

    if isinstance(error, AssertionError) and re.match(
        r"(Locator|Page) expected", first
    ):
        reason = f"UI check failed: {first}."
        if actual:
            reason += f" Actual: {actual.group(1).strip()}."
        if target:
            reason += f" Element: {target}."
        return _short(reason)

    if isinstance(error, AssertionError):
        return _short(
            "Assertion failed: what the app showed or returned did not match "
            f"what the test expected. {first}"
        )

    if "has been closed" in message or "net::ERR" in message:
        return _short(f"The browser page closed or a navigation failed: {first}")

    if isinstance(error, (KeyError, IndexError, TypeError, AttributeError, ValueError)):
        return _short(
            f"The test code hit a {kind} ({first}): the page or API returned "
            "data in a shape the test did not expect."
        )

    return _short(f"{kind}: {first}")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if not report.failed or report.when not in ("setup", "call") or not call.excinfo:
        return

    report.failure_explanation = _explain_failure(call.excinfo, report.when)

    if html_extras is None:
        return
    page = _page_for_screenshot(item)
    if page is None:
        return
    try:
        png = page.screenshot(timeout=SCREENSHOT_TIMEOUT)
    except Exception as error:
        print(f"no failure screenshot for {item.nodeid}: {error}")
        return
    report.extras = getattr(report, "extras", []) + [
        html_extras.png(base64.b64encode(png).decode(), "Screenshot on failure")
    ]


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_header(cells):
    cells.append('<th class="explanation">Failure Explanation</th>')


@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_row(report, cells):
    explanation = getattr(report, "failure_explanation", "")
    cells.append(f'<td class="col-explanation">{html.escape(explanation)}</td>')
