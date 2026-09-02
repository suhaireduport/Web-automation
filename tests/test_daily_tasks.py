import re
import pytest
from playwright.sync_api import expect

from pages.home_page import HomePage
from pages.daily_tasks_page import DailyTasksPage

MOBILE = "8893963137"
OTP = "430582"

OTP_URL = "https://eduport-react.pages.dev/otp"
HOME_URL = "https://eduport-react.pages.dev/"
DAILY_TASKS_URL = "https://eduport-react.pages.dev/daily-tasks"
PENDING_TASKS_URL = "https://eduport-react.pages.dev/tasks/pendingTask"
LEADERBOARD_URL = "https://eduport-react.pages.dev/home/leader_board"
STREAK_URL = "https://eduport-react.pages.dev/home/streak"


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture
def daily_tasks_page(page):

    home_page = HomePage(page)
    home_page.get_daily_tasks_button().click()
    page.wait_for_url(DAILY_TASKS_URL)

    daily_tasks = DailyTasksPage(page)
    daily_tasks.wait_for_tasks_loaded()
    return daily_tasks


def test_daily_tasks_page_opens(page, daily_tasks_page):
    expect(page).to_have_url(DAILY_TASKS_URL)
    expect(daily_tasks_page.get_page_title()).to_have_text("Daily Tasks")


def test_header_stat_chips_visible(daily_tasks_page):
    expect(daily_tasks_page.get_stat_chips()).to_have_count(2)
    expect(daily_tasks_page.get_coin_button()).to_be_visible()
    expect(daily_tasks_page.get_streak_button()).to_be_visible()


def test_calendar_visible(daily_tasks_page):
    expect(daily_tasks_page.get_calendar()).to_be_visible()
    expect(daily_tasks_page.get_date_strip()).to_be_visible()
    expect(daily_tasks_page.get_month_year()).to_have_text(
        re.compile(r"^[A-Za-z]+ \d{4}$")
    )


def test_date_strip_has_dates(daily_tasks_page):
    dates = daily_tasks_page.get_date_cells()

    expect(dates.first).to_be_visible()
    assert dates.count() > 0

    print("Date cell count:", dates.count())


def test_one_date_selected_by_default(daily_tasks_page):
    expect(daily_tasks_page.get_selected_date()).to_have_count(1)
    expect(daily_tasks_page.get_selected_date()).to_be_visible()


def test_date_cell_shows_day_name_and_number(daily_tasks_page):
    expect(daily_tasks_page.get_day_name(0)).to_have_text(
        re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)$")
    )
    expect(daily_tasks_page.get_day_number(0)).to_have_text(re.compile(r"^\d{1,2}$"))


def test_select_a_different_date(daily_tasks_page):
    selected_day = daily_tasks_page.get_selected_date().locator(".dt-day-num")
    expect(selected_day).not_to_have_text(
        daily_tasks_page.get_day_number(0).inner_text()
    )

    daily_tasks_page.click_date(0)

    expect(daily_tasks_page.get_selected_date()).to_have_count(1)
    expect(daily_tasks_page.get_date_cell(0)).to_have_class(
        re.compile("dt-date-selected")
    )


def test_calendar_nav_arrows_visible(daily_tasks_page):
    expect(daily_tasks_page.get_nav_arrows()).to_have_count(2)
    expect(daily_tasks_page.get_previous_arrow()).to_be_enabled()
    expect(daily_tasks_page.get_next_arrow()).to_be_enabled()


def test_previous_arrow_changes_dates(daily_tasks_page):
    before = daily_tasks_page.get_day_numbers().all_inner_texts()

    daily_tasks_page.click_previous_arrow()

    expect(daily_tasks_page.get_day_numbers().first).not_to_have_text(before[0])
    print("before:", before[:5], "after:",
          daily_tasks_page.get_day_numbers().all_inner_texts()[:5])


def test_pending_tasks_badge_opens_pending_page(page, daily_tasks_page):
    if not daily_tasks_page.has_pending_tasks():
        pytest.skip("No pending tasks for this user")

    daily_tasks_page.click_pending_tasks()

    expect(page).to_have_url(PENDING_TASKS_URL)


def test_task_groups_have_titles(daily_tasks_page):
    group_count = daily_tasks_page.task_group_count()

    if group_count == 0:
        pytest.skip("No tasks on the selected date")

    print("Task group count:", group_count)

    titles = daily_tasks_page.get_task_group_titles()
    for i in range(titles.count()):
        expect(titles.nth(i)).not_to_be_empty()
        print("Group:", titles.nth(i).inner_text().strip())


def test_live_card_details(daily_tasks_page):
    if daily_tasks_page.live_card_count() == 0:
        pytest.skip("No live classes on the selected date")

    expect(daily_tasks_page.get_live_badge(0)).to_contain_text("Live")
    expect(daily_tasks_page.get_live_subject(0)).not_to_be_empty()
    expect(daily_tasks_page.get_live_title(0)).not_to_be_empty()

    # Not clicked on purpose: it joins a live class.
    expect(daily_tasks_page.get_watch_now_button(0)).to_be_enabled()


def test_fab_opens_add_task_modal(daily_tasks_page):
    daily_tasks_page.click_fab()

    expect(daily_tasks_page.get_add_task_modal()).to_be_visible()
    expect(daily_tasks_page.get_add_task_title()).to_have_text("Add Tasks")


def test_add_task_options(daily_tasks_page):
    daily_tasks_page.click_fab()

    expect(daily_tasks_page.get_add_task_cards()).to_have_count(3)
    expect(daily_tasks_page.get_catch_up_card()).to_contain_text("Catch Up")
    expect(daily_tasks_page.get_practice_card()).to_contain_text("Practice")
    expect(daily_tasks_page.get_self_learn_card()).to_contain_text("Self Learn")


def test_close_add_task_modal(daily_tasks_page):
    daily_tasks_page.click_fab()
    expect(daily_tasks_page.get_add_task_modal()).to_be_visible()

    daily_tasks_page.close_add_task_modal()

    expect(daily_tasks_page.get_add_task_modal()).to_be_hidden()
    expect(daily_tasks_page.get_add_task_overlay()).to_be_hidden()


def test_coin_button_opens_leaderboard(page, daily_tasks_page):
    daily_tasks_page.click_coin_button()

    expect(page).to_have_url(LEADERBOARD_URL)


def test_streak_button_opens_streak(page, daily_tasks_page):
    daily_tasks_page.click_streak_button()

    expect(page).to_have_url(STREAK_URL)


# ---------------------------------------------------------------------------
# API verification
#
# The calendar strip is wider than the window the API answers for, so the dates
# it returns are checked as a subset of what the strip offers rather than as an
# equal list.
# ---------------------------------------------------------------------------

DAILY_TASKS_API = "**/api/v3/dailytasks/list"

# The task buckets a day is served with. A bucket holding nothing is not drawn.
TASK_KEYS = [
    "study_tasks",
    "practice_tasks",
    "revision_tasks",
    "exam_tasks",
    "selflearn_tasks",
    "catchup_tasks",
]


def open_daily_tasks_with_payload(page):
    with page.expect_response(DAILY_TASKS_API) as answer:
        page.goto(DAILY_TASKS_URL, wait_until="domcontentloaded")
    assert answer.value.status == 200, f"dailytasks answered {answer.value.status}"

    daily_tasks = DailyTasksPage(page)
    daily_tasks.wait_for_tasks_loaded()
    return daily_tasks, answer.value.json()["results"]


def day_of(date_text):
    """"2026-08-25" -> 25"""
    return int(date_text.split("-")[2])


def test_calendar_dates_cover_what_the_daily_tasks_api_returns(page):
    daily_tasks, results = open_daily_tasks_with_payload(page)

    if not results:
        pytest.skip("The API returned no days for this account")

    shown = {int(text) for text in daily_tasks.get_day_numbers().all_inner_texts()}
    served = {day_of(entry["date"]) for entry in results}

    assert served <= shown, f"{sorted(served - shown)} are not on the strip"


def test_pending_date_badges_match_the_daily_tasks_api(page):
    daily_tasks, results = open_daily_tasks_with_payload(page)

    shown = {int(text) for text in daily_tasks.get_day_numbers().all_inner_texts()}
    pending = [
        entry
        for entry in results
        if entry["pending_status"] and day_of(entry["date"]) in shown
    ]

    expect(daily_tasks.get_pending_date_badges()).to_have_count(len(pending))


def test_task_groups_match_the_daily_tasks_api_for_the_selected_date(page):
    daily_tasks, results = open_daily_tasks_with_payload(page)

    selected = int(
        daily_tasks.get_selected_date().locator(".dt-day-num").inner_text().strip()
    )
    entry = next((e for e in results if day_of(e["date"]) == selected), None)
    if entry is None:
        pytest.skip("The selected date is outside the range the API answered for")

    expected = sum(1 for key in TASK_KEYS if entry[key])

    assert daily_tasks.task_group_count() == expected
