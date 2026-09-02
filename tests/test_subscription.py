"""Subscriptions, reached from the profile menu.

The screen is served by one call and renders nothing of its own, so every card
is read back against that payload rather than against an account written down
here - which subscriptions a login holds changes as courses are sold.

test_profile_menu.py already checks that the menu entry routes here, so that is
not repeated; these start from the screen itself.
"""
import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.profile_menu_page import ProfileMenuPage
from pages.subscription_page import SubscriptionPage

MOBILE = "9876543210"

SUBSCRIPTIONS_URL = SubscriptionPage.URL
SUBSCRIPTIONS_API = "**/api/v3/subscriptions"

# The badge each status in the payload is drawn as.
STATUS_LABELS = {"ACTIVE": "Active", "EXPIRED": "Expired"}

# "2027-05-31" is drawn as "Expires on 31 May 2027".
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


def open_subscriptions_with_payload(page):
    """Open the screen and hand back the payload it was built from."""
    with page.expect_response(SUBSCRIPTIONS_API) as answer:
        page.goto(SUBSCRIPTIONS_URL, wait_until="domcontentloaded")
    assert answer.value.status == 200, f"subscriptions answered {answer.value.status}"

    subscriptions = SubscriptionPage(page)
    subscriptions.wait_for_loaded()
    subscriptions.card_count()
    return subscriptions, answer.value.json()["subscriptions"]


# ---------------------------------------------------------------------------
# Reaching the screen
# ---------------------------------------------------------------------------

def test_subscriptions_open_from_the_profile_menu(page):
    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()
    home_page.open_profile_menu()

    menu = ProfileMenuPage(page)
    expect(menu.get_menu()).to_be_visible()
    menu.click_item("Subscriptions")

    subscriptions = SubscriptionPage(page)

    expect(page).to_have_url(SUBSCRIPTIONS_URL)
    expect(subscriptions.get_page()).to_be_visible()
    expect(subscriptions.get_title()).to_have_text("Subscription")
    expect(subscriptions.get_back_button()).to_be_enabled()


# ---------------------------------------------------------------------------
# API verification
# ---------------------------------------------------------------------------

def test_subscription_cards_match_the_subscriptions_api(page):
    subscriptions, served = open_subscriptions_with_payload(page)

    expect(subscriptions.get_cards()).to_have_count(len(served))
    if not served:
        return

    # The card leads with the course and names the plan under it, which is the
    # other way round from the payload.
    courses = [text.strip() for text in subscriptions.get_courses().all_inner_texts()]
    plans = [text.strip() for text in subscriptions.get_plans().all_inner_texts()]

    assert courses == [one["course"].strip() for one in served]
    assert plans == [one["title"].strip() for one in served]


def test_subscription_status_badges_match_the_subscriptions_api(page):
    subscriptions, served = open_subscriptions_with_payload(page)
    if not served:
        pytest.skip("This account holds no subscription")

    shown = [text.strip() for text in subscriptions.get_badges().all_inner_texts()]
    expected = [
        STATUS_LABELS.get(one["status"], one["status"].title()) for one in served
    ]

    assert shown == expected


def test_subscription_expiry_dates_match_the_subscriptions_api(page):
    subscriptions, served = open_subscriptions_with_payload(page)
    if not served:
        pytest.skip("This account holds no subscription")

    shown = [text.strip() for text in subscriptions.get_expiries().all_inner_texts()]
    assert len(shown) == len(served)

    for text, one in zip(shown, served):
        year, month, day = one["expiry"].split("-")

        assert year in text, f"{text!r} does not carry the year {year}"
        assert str(int(day)) in text, f"{text!r} does not carry the day {day}"
        assert MONTHS[int(month) - 1][:3] in text, (
            f"{text!r} does not carry the month {MONTHS[int(month) - 1]}"
        )
