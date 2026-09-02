import re
import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.analytics_page import AnalyticsPage

MOBILE = "8893963137"
OTP = "430582"

OTP_URL = "https://eduport-react.pages.dev/otp"
HOME_URL = "https://eduport-react.pages.dev/"
ANALYTICS_URL = "https://eduport-react.pages.dev/analytics"
EFFORT_TRACKER_URL = "https://eduport-react.pages.dev/analysis/effort-tracker"
ABILITY_TRACKER_URL = "https://eduport-react.pages.dev/analysis/ability-tracker"
LEADERBOARD_URL = "https://eduport-react.pages.dev/home/leader_board"
STREAK_URL = "https://eduport-react.pages.dev/home/streak"


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture
def analytics_page(page):

    home_page = HomePage(page)
    home_page.get_analysis_button().click()
    page.wait_for_url(ANALYTICS_URL)

    analytics = AnalyticsPage(page)
    analytics.wait_for_analytics_loaded()
    return analytics


def test_analytics_page_opens(page, analytics_page):
    expect(page).to_have_url(ANALYTICS_URL)
    expect(analytics_page.get_page_title()).to_have_text("Analysis")


def test_header_stat_chips_visible(analytics_page):
    expect(analytics_page.get_stat_chips()).to_have_count(2)
    expect(analytics_page.get_coin_button()).to_be_visible()
    expect(analytics_page.get_streak_button()).to_be_visible()


def test_tracker_cards_visible(analytics_page):
    expect(analytics_page.get_cards()).to_have_count(2)
    expect(analytics_page.get_effort_tracker_card()).to_be_visible()
    expect(analytics_page.get_ability_tracker_card()).to_be_visible()


def test_card_titles(analytics_page):
    expect(analytics_page.get_card_titles()).to_have_text(
        ["Daily Effort Tracker", "Ability Tracker"]
    )


def test_effort_gauge_and_quote_visible(analytics_page):
    expect(analytics_page.get_effort_gauge()).to_be_visible()
    expect(analytics_page.get_effort_quote()).not_to_be_empty()


def test_effort_slider_has_two_slides(analytics_page):
    expect(analytics_page.get_slider_dots()).to_have_count(2)
    expect(analytics_page.get_active_slider_dot()).to_have_count(1)


def test_switch_effort_slider_to_time_breakdown(analytics_page):
    expect(analytics_page.get_slider_dots().nth(0)).to_have_class(
        re.compile("an-dot-active")
    )

    analytics_page.click_slider_dot(1)

    expect(analytics_page.get_slider_dots().nth(1)).to_have_class(
        re.compile("an-dot-active")
    )
    expect(analytics_page.get_slider_dots().nth(0)).to_have_class(
        re.compile("an-dot-inactive")
    )


def test_time_breakdown_categories(analytics_page):
    analytics_page.click_slider_dot(1)

    expect(analytics_page.get_donut_legend_items()).to_have_count(3)
    expect(analytics_page.get_donut_legend_labels()).to_have_text(
        ["Study", "Practice", "Exams"]
    )


def test_info_button_opens_sheet(analytics_page):
    analytics_page.click_info_button(0)

    expect(analytics_page.get_info_sheet()).to_be_visible()
    expect(analytics_page.get_info_sheet_title()).to_have_text("How analytics works?")


def test_info_sheet_sections(analytics_page):
    analytics_page.click_info_button(0)

    expect(analytics_page.get_info_sections()).to_have_count(3)
    expect(analytics_page.get_info_section_titles()).to_have_text(
        ["Effort Tracker", "Ability Tracker", "Syllabus Tracker"]
    )


def test_effort_more_opens_effort_tracker(page, analytics_page):
    analytics_page.click_effort_more()

    expect(page).to_have_url(EFFORT_TRACKER_URL)


def test_ability_more_opens_ability_tracker(page, analytics_page):
    analytics_page.click_ability_more()

    expect(page).to_have_url(ABILITY_TRACKER_URL)


def test_subjects_listed(analytics_page):
    count = analytics_page.subject_count()

    if count == 0:
        pytest.skip("No subjects for this user")

    print("Subject count:", count)

    for i in range(count):
        expect(analytics_page.get_subject_name(i)).not_to_be_empty()
        print(analytics_page.get_subject_name(i).inner_text().strip())


def test_subject_percentages_shown(analytics_page):
    count = analytics_page.subject_count()

    if count == 0:
        pytest.skip("No subjects for this user")

    for i in range(count):
        expect(analytics_page.get_subject_percentage(i)).to_have_text(
            re.compile(r"^\d+%$")
        )


def test_subject_opens_ability_tracker(page, analytics_page):
    if analytics_page.subject_count() == 0:
        pytest.skip("No subjects for this user")

    analytics_page.click_subject(0)

    expect(page).to_have_url(
        re.compile(
            r"https://eduport-react\.pages\.dev/analysis/ability-tracker\?subject=\d+"
        )
    )


def test_coin_button_opens_leaderboard(page, analytics_page):
    analytics_page.click_coin_button()

    expect(page).to_have_url(LEADERBOARD_URL)


def test_streak_button_opens_streak(page, analytics_page):
    analytics_page.click_streak_button()

    expect(page).to_have_url(STREAK_URL)


# ---------------------------------------------------------------------------
# API verification
#
# The subject list under the tracker cards is drawn from the ability call, so
# the names and the percentages can be read back against it.
# ---------------------------------------------------------------------------

ABILITY_API = "**/api/v3/analytics/ability/list"


def test_analytics_subjects_match_the_ability_api(page):
    with page.expect_response(ABILITY_API) as answer:
        page.goto(ANALYTICS_URL, wait_until="domcontentloaded")
    assert answer.value.status == 200, f"ability answered {answer.value.status}"
    subjects = answer.value.json()["subjects"]

    analytics = AnalyticsPage(page)
    analytics.wait_for_analytics_loaded()

    if not subjects:
        pytest.skip("No subjects for this user")

    expected = [
        (subject["title"].strip(), f"{subject['ability_index']}%")
        for subject in subjects
    ]
    shown = [
        (
            analytics.get_subject_name(index).inner_text().strip(),
            analytics.get_subject_percentage(index).inner_text().strip(),
        )
        for index in range(analytics.subject_count())
    ]

    assert shown == expected
