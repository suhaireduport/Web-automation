"""The coin balance: what it is, where it is shown and what moves it.

What the balance turns out to be, read off the running app rather than
assumed:

  the chip     every screen with a header draws the same figure, and every one
               of them draws it from GET analytics/leaderboard/coins, which
               answers {"coins": n}.
  today only   that figure is what has been earned today, not a running total.
               It matches the signed in student's entry on the Today
               leaderboard and the sum of the Today coin log, and it parts
               company with the week, month and all time figures as soon as the
               account has earned anything on an earlier day.
  when it pays a quick practice pays nothing for being started and nothing for
               an answer being given. The submit that carries completed=true is
               answered with what the whole set came to, and that is the moment
               the balance moves.

Coins are earned here by completing a quick practice, because that is the one
action in the app that pays and can be repeated: an exam pays for being
attended but each one can only be attempted once, so the exam rate is left to
the rules the app publishes (test_leaderboard.py) rather than being spent to
prove it.

What a quiz pays for each kind of answer is in test_daily_task_coins.py; this
file is only about the balance those payments land in.
"""
import re
import pytest

from pages.home_page import HomePage
from pages.daily_tasks_page import DailyTasksPage
from pages.analytics_page import AnalyticsPage
from pages.leaderboard_page import (
    COINS_API,
    LeaderboardPage,
    call_api,
    read_balance,
    read_coin_log,
)
from pages.practice_page import CORRECT, take_practice_quiz

MOBILE = "9876543210"

HOME_URL = "https://eduport-react.pages.dev/"

NOTHING_TO_PRACTISE = "No topic on this account has a question left to practise"


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


def digits(text):
    """The number a chip shows, without whatever it is decorated with."""
    return int(re.sub(r"\D", "", text))


def open_with_balance(page, url, wait_for):
    """Open a screen and hand back the balance the call behind it answered.

    The answer has to be listened for before the navigation that asks for it,
    so the two go together."""
    with page.expect_response(COINS_API) as answer:
        page.goto(url, wait_until="domcontentloaded")
    assert answer.value.status == 200, f"coins answered {answer.value.status}"
    wait_for()
    return answer.value.json()["coins"]


# ---------------------------------------------------------------------------
# 1. The balance, and the chips drawn from it
#
# Home's chip is checked in test_home.py. What is checked here is that the
# other screens carrying one draw the same figure from the same call, and that
# it is the figure the leaderboard and the coin log agree on.
# ---------------------------------------------------------------------------

def test_the_daily_tasks_chip_matches_the_coins_api(page):
    daily_tasks = DailyTasksPage(page)
    coins = open_with_balance(
        page, DailyTasksPage.URL, daily_tasks.wait_for_tasks_loaded
    )

    assert digits(daily_tasks.get_coin_button().inner_text()) == coins


def test_the_analytics_chip_matches_the_coins_api(page):
    analytics = AnalyticsPage(page)
    coins = open_with_balance(
        page, AnalyticsPage.URL, analytics.wait_for_analytics_loaded
    )

    assert digits(analytics.get_coin_button().inner_text()) == coins


def test_every_screen_shows_the_one_balance(page):
    """Home, Daily Tasks and Analytics all carry a coin chip. They are three
    renders of one number, so they are held to being equal to each other as
    well as to the call."""
    home = HomePage(page)
    coins = open_with_balance(page, HOME_URL, home.get_subjects().first.wait_for)

    daily_tasks = DailyTasksPage(page)
    on_tasks = open_with_balance(
        page, DailyTasksPage.URL, daily_tasks.wait_for_tasks_loaded
    )
    analytics = AnalyticsPage(page)
    on_analytics = open_with_balance(
        page, AnalyticsPage.URL, analytics.wait_for_analytics_loaded
    )

    shown = {
        "home": coins,
        "daily tasks": digits(daily_tasks.get_coin_button().inner_text()),
        "analytics": digits(analytics.get_coin_button().inner_text()),
    }
    assert on_tasks == coins and on_analytics == coins, shown
    assert len(set(shown.values())) == 1, shown


def test_the_balance_survives_a_reload(page):
    """Nothing about the balance is held on the page: it is asked for again on
    every load and comes back the same."""
    daily_tasks = DailyTasksPage(page)
    before = open_with_balance(
        page, DailyTasksPage.URL, daily_tasks.wait_for_tasks_loaded
    )
    shown_before = digits(daily_tasks.get_coin_button().inner_text())

    with page.expect_response(COINS_API) as answer:
        page.reload()
    daily_tasks.wait_for_tasks_loaded()

    assert answer.value.json()["coins"] == before
    assert digits(daily_tasks.get_coin_button().inner_text()) == shown_before


# ---------------------------------------------------------------------------
# 2. What the balance is a total of
# ---------------------------------------------------------------------------

def open_leaderboard(page):
    """The leaderboard, which carries no chip of its own and so asks for no
    balance. The balance is asked for separately once it is open."""
    page.goto(LeaderboardPage.URL, wait_until="domcontentloaded")
    leaderboard = LeaderboardPage(page)
    leaderboard.wait_for_loaded()
    return leaderboard, read_balance(page)


def test_the_balance_is_what_the_leaderboard_carries_for_today(page):
    """The chip and the Today leaderboard are the same figure: the student's
    own row on Today reads what the coins call answers.

    An account that has earned nothing today is on neither, which is the same
    statement and is asserted as such."""
    leaderboard, coins = open_leaderboard(page)

    today = call_api(page, "/analytics/leaderboard/today")["leaderboard"]
    mine = next((row for row in today if row["is_current_user"]), None)

    if mine is None:
        assert coins == 0, f"nothing on Today, but the chip shows {coins}"
        assert leaderboard.current_row_index() is None
        return

    assert mine["coins"] == coins
    index = leaderboard.current_row_index()
    assert index is not None, "the API put this student on Today, the screen did not"
    assert leaderboard.get_coins()[index] == coins


def test_the_balance_is_the_sum_of_todays_coin_log(page):
    """Every coin the balance holds is accounted for by an entry in the Today
    log, and the log holds nothing the balance does not."""
    _, coins = open_leaderboard(page)

    events = read_coin_log(page, "log-today")

    assert sum(event["score"] for event in events) == coins, [
        (event["tag"], event["score"]) for event in events
    ]


def test_the_balance_is_todays_earnings_and_not_a_running_total(page):
    """The chip is today's coins, so an account that earned on an earlier day
    carries more on the longer boards than the chip shows.

    Nothing is asserted about which way they differ when they do not: an
    account whose only earnings are today's has every board agreeing with the
    chip, and that is not a failure."""
    _, coins = open_leaderboard(page)

    def mine(period):
        rows = call_api(page, f"/analytics/leaderboard/{period}")["leaderboard"]
        row = next((row for row in rows if row["is_current_user"]), None)
        return row["coins"] if row else 0

    everything = sum(event["score"] for event in read_coin_log(page, "log"))
    today = sum(event["score"] for event in read_coin_log(page, "log-today"))
    earned_earlier = everything - today

    overall = mine("overall")
    print("chip:", coins, "week:", mine("week"), "month:", mine("monthly"),
          "all time:", overall, "| earned before today:", earned_earlier)

    assert overall == coins + earned_earlier
    if earned_earlier:
        assert overall != coins, (
            "this account earned on an earlier day, so the all time figure "
            "cannot be the same number as today's chip"
        )


# ---------------------------------------------------------------------------
# 3. The balance after an action
#
# Earning is done once for the whole run and read back by several tests,
# because every quiz taken uses up questions the account cannot get back.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def _earning_state():
    return {}


@pytest.fixture(scope="session")
def earning(login_session, _earning_state):
    """Complete one quick practice, and record what it did to the balance.

    The balance is read from inside the page rather than by opening a screen
    that shows it, because the before reading is taken with a quiz already on
    screen that cannot be navigated away from and back to."""
    if "reason" in _earning_state:
        pytest.skip(_earning_state["reason"])
    if "paid" in _earning_state:
        return _earning_state

    page = login_session(MOBILE)
    page.goto(HOME_URL, wait_until="domcontentloaded")

    before = read_balance(page)
    taken = take_practice_quiz(page, how=CORRECT, questions=1)
    if taken is None:
        _earning_state["reason"] = NOTHING_TO_PRACTISE
        pytest.skip(NOTHING_TO_PRACTISE)

    practice = taken["practice"]
    _earning_state.update(
        before=before,
        paid=taken["completion"]["coin"],
        completion=taken["completion"],
        shown_on_result=practice.get_awarded_coins(),
        after=read_balance(page),
        log=read_coin_log(page, "log-today"),
        practised=taken["practised"],
    )
    practice.close_result()
    return _earning_state


def test_the_balance_moves_by_exactly_what_the_quiz_paid(earning):
    """Before plus what the app said it paid is after: no rounding of its own
    and nothing else slipped in."""
    assert earning["after"] == earning["before"] + earning["paid"], earning["completion"]


def test_the_result_screen_shows_what_the_api_paid(earning):
    """The coins on the result screen are the coin figure the submit was
    answered with."""
    assert earning["shown_on_result"] == earning["paid"]


def test_the_chip_shows_the_new_balance_after_earning(page, earning):
    """A screen opened after the quiz draws the balance the quiz left behind,
    which is also the point the reading survives a fresh load."""
    daily_tasks = DailyTasksPage(page)
    coins = open_with_balance(
        page, DailyTasksPage.URL, daily_tasks.wait_for_tasks_loaded
    )

    assert coins >= earning["after"], (
        "the balance went backwards after the quiz was paid for"
    )
    assert digits(daily_tasks.get_coin_button().inner_text()) == coins


def test_what_the_quiz_paid_is_written_into_todays_log(earning):
    """The award is one entry in the Today log, not a figure kept only in the
    total."""
    scores = [event["score"] for event in earning["log"]]

    assert sum(scores) == earning["after"], earning["log"]
    assert earning["paid"] in scores, (
        f"nothing in today's log paid {earning['paid']}: {scores}"
    )
