"""The coin leaderboard: four periods over one screen.

Each tab is drawn from two calls of its own, both under
/api/v3/analytics/leaderboard/:

  Today       today      log-today
  This Week   week       log-week
  This Month  monthly    log-month
  All Time    overall    log

The first is the rank list the screen shows. The second is the coin ledger
behind it - every event that paid or cost the signed in student over that
period - and it is what the "My log" sheet holds when they tap their own row.
Only their own row opens anything.

The four rank lists are all asked for when the screen opens; the log of a tab
is asked for when that tab is opened. A tab whose rank list comes back empty
draws an invitation to start earning in place of a list.

When it is worked out, in the app's own words on the How to get coins sheet:
"Weekly, monthly, and all-time leaderboards update every day at 4 AM." So the
rank a board shows is a daily rebuild rather than a live reading, and nothing
here expects a board to move because coins were just earned. What is checked
instead is that each board and its own ledger agree, and that the screen shows
what its call answered - which holds whenever the call was last worked out.
Coins earned during a run are checked against the balance and the Today board
in test_coins.py, where the reading is live.
"""
import pytest
from playwright.sync_api import expect

from pages.leaderboard_page import LeaderboardPage, call_api, read_balance, read_coin_log

MOBILE = "8893963137"

TABS = list(LeaderboardPage.TABS)


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture
def leaderboard(page):
    page.goto(LeaderboardPage.URL, wait_until="domcontentloaded")
    board = LeaderboardPage(page)
    board.wait_for_loaded()
    return board


def rank_list(page, tab):
    """The rank list the given tab is drawn from."""
    period, _ = LeaderboardPage.TABS[tab]
    return call_api(page, f"/analytics/leaderboard/{period}")["leaderboard"]


def open_tab(page, leaderboard, tab):
    """Show a tab and hand back the rows it was drawn from.

    The list is asked for again rather than read off the payload the screen
    opened with, so what is compared is the answer that was current when the
    screen was read."""
    leaderboard.click_tab(tab)
    return rank_list(page, tab)


def arrow_for(delta):
    """Which way the marker on a row should point for a rank movement."""
    if delta > 0:
        return "up"
    if delta < 0:
        return "down"
    return "equal"


# ---------------------------------------------------------------------------
# 1. The tabs
# ---------------------------------------------------------------------------

def test_the_leaderboard_offers_the_four_periods(page, leaderboard):
    expect(page).to_have_url(LeaderboardPage.URL)
    expect(leaderboard.get_title()).to_have_text("Leaderboard")
    assert leaderboard.get_tab_names() == TABS


def test_today_is_the_tab_it_opens_on(leaderboard):
    expect(leaderboard.get_active_tab()).to_have_count(1)
    assert leaderboard.get_active_tab_name() == "Today"


@pytest.mark.parametrize("tab", TABS)
def test_a_tab_becomes_the_active_one_when_it_is_opened(leaderboard, tab):
    leaderboard.click_tab(tab)

    expect(leaderboard.get_active_tab()).to_have_count(1)
    assert leaderboard.get_active_tab_name() == tab


# ---------------------------------------------------------------------------
# 2. The rank list against the call it is drawn from
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tab", TABS)
def test_the_rank_list_matches_the_leaderboard_api(page, leaderboard, tab):
    """One row per student the call answered with, in the order it answered
    them, each showing that student's name and that student's coins."""
    served = open_tab(page, leaderboard, tab)

    expect(leaderboard.get_rows()).to_have_count(len(served))
    if not served:
        return

    assert leaderboard.get_names() == [row["student"].strip() for row in served]
    assert leaderboard.get_coins() == [row["coins"] for row in served]


@pytest.mark.parametrize("tab", TABS)
def test_the_ranks_run_from_one_down_the_order_the_api_returns(
    page, leaderboard, tab
):
    """Rank is position in the answer rather than anything sent with it: the
    call returns the board already in order and the screen numbers it 1, 2,
    3 down the page."""
    served = open_tab(page, leaderboard, tab)
    if not served:
        pytest.skip(f"{tab} has nobody on it")

    assert leaderboard.get_ranks() == list(range(1, len(served) + 1))

    coins = [row["coins"] for row in served]
    assert coins == sorted(coins, reverse=True), (
        f"{tab} was not returned best first: {coins}"
    )


@pytest.mark.parametrize("tab", TABS)
def test_the_signed_in_student_is_the_row_the_api_flags(page, leaderboard, tab):
    """is_current_user picks out one row, and that row is the one carrying the
    YOU tag and the only one that opens anything."""
    served = open_tab(page, leaderboard, tab)
    mine = [index for index, row in enumerate(served) if row["is_current_user"]]

    expect(leaderboard.get_you_tag()).to_have_count(len(mine))
    if not mine:
        assert leaderboard.current_row_index() is None
        return

    assert len(mine) == 1, f"{tab} flagged {len(mine)} rows as the current student"
    index = mine[0]

    assert leaderboard.current_row_index() == index
    expect(leaderboard.get_row_name(index)).to_have_text(served[index]["student"].strip())
    assert leaderboard.get_coins()[index] == served[index]["coins"]
    assert leaderboard.get_ranks()[index] == index + 1


@pytest.mark.parametrize("tab", TABS)
def test_the_rank_arrow_follows_the_movement_the_api_reports(page, leaderboard, tab):
    """rank_delta is drawn as an arrow: up when the row has climbed, down when
    it has slipped, and a flat marker when it has not moved."""
    served = open_tab(page, leaderboard, tab)
    if not served:
        pytest.skip(f"{tab} has nobody on it")

    shown = [leaderboard.get_row_delta(index) for index in range(len(served))]
    expected = [arrow_for(row["rank_delta"]) for row in served]

    assert shown == expected, [row["rank_delta"] for row in served]

    for index, row in enumerate(served):
        if row["rank_delta"]:
            expect(leaderboard.get_row_delta_text(index)).to_have_text(
                f"{row['rank_delta']:+d}"
            )


# ---------------------------------------------------------------------------
# 3. The empty tab
# ---------------------------------------------------------------------------

def test_an_empty_tab_offers_the_coin_rules_instead_of_a_list(page, leaderboard):
    """A period nobody has earned in has no list to show, so the screen puts
    up the invitation to start earning and the rules for doing it."""
    empty = None
    for tab in TABS:
        if not open_tab(page, leaderboard, tab):
            empty = tab
            break
    if empty is None:
        pytest.skip("Every period on this account has somebody on it")

    print("empty tab:", empty)
    expect(leaderboard.get_rows()).to_have_count(0)
    expect(leaderboard.get_empty_banner()).to_be_visible()
    expect(leaderboard.get_inline_rules_panel()).to_be_visible()


# ---------------------------------------------------------------------------
# 4. My log, the ledger behind the row
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tab", TABS)
def test_my_log_matches_the_coin_log_api(page, leaderboard, tab):
    """The sheet behind the student's own row is the coin log of that tab's
    period: one tile per event, titled and scored as the call answered."""
    served = open_tab(page, leaderboard, tab)
    if not any(row["is_current_user"] for row in served):
        pytest.skip(f"This student is not on {tab}, so their row cannot be opened")

    _, log = LeaderboardPage.TABS[tab]
    events = read_coin_log(page, log)

    leaderboard.open_my_log()
    expect(leaderboard.get_log_title()).to_have_text("My log")

    if not events:
        expect(leaderboard.get_log_tiles()).to_have_count(0)
        expect(leaderboard.get_log_empty_title()).to_be_visible()
        return

    expect(leaderboard.get_log_tiles()).to_have_count(len(events))
    assert leaderboard.get_log_titles() == [
        event["data"]["title"].strip() for event in events
    ]
    assert leaderboard.get_log_scores() == [event["score"] for event in events]


@pytest.mark.parametrize("tab", TABS)
def test_a_board_is_worth_what_its_own_log_adds_up_to(page, leaderboard, tab):
    """The figure against the student on a board is the sum of the events in
    that board's own ledger. The two are served by different calls, so this is
    the one place they are held against each other."""
    served = open_tab(page, leaderboard, tab)
    mine = next((row for row in served if row["is_current_user"]), None)

    _, log = LeaderboardPage.TABS[tab]
    events = read_coin_log(page, log)
    ledger = sum(event["score"] for event in events)

    if mine is None:
        assert ledger == 0, (
            f"{tab} has no row for this student but its log adds up to {ledger}"
        )
        return

    assert mine["coins"] == ledger, [(e["tag"], e["score"]) for e in events]
    assert leaderboard.get_coins()[leaderboard.current_row_index()] == ledger


def test_only_the_students_own_row_opens_the_log(page, leaderboard):
    """Every row is drawn the same way, but only the student's own is offered
    as something to tap."""
    served = open_tab(page, leaderboard, "All Time")
    if len(served) < 2:
        pytest.skip("All Time carries only this student, so there is no other row")

    clickable = page.locator(".lb-row-clickable")
    expect(clickable).to_have_count(sum(1 for row in served if row["is_current_user"]))

    for index, row in enumerate(served):
        classes = leaderboard.get_row(index).get_attribute("class") or ""
        assert ("lb-row-clickable" in classes) is bool(row["is_current_user"]), (
            f"row {index + 1} ({row['student']})"
        )


def test_the_log_sheet_closes(leaderboard):
    leaderboard.click_tab("All Time")
    if not leaderboard.has_current_row():
        pytest.skip("This student is not on All Time, so their row cannot be opened")

    leaderboard.open_my_log()
    expect(leaderboard.get_log_sheet()).to_be_visible()

    leaderboard.close_my_log()

    expect(leaderboard.get_log_sheet()).to_have_count(0)


# ---------------------------------------------------------------------------
# 5. What the leaderboard says about itself
#
# The rates it publishes are what the quiz tests hold the app to, and the
# refresh policy is why nothing here expects a board to move on the spot.
# ---------------------------------------------------------------------------

def test_the_leaderboard_publishes_how_coins_are_earned(leaderboard):
    leaderboard.open_info()

    expect(leaderboard.get_info_title()).to_have_text("How to get coins?")
    assert leaderboard.get_rule_section_titles() == ["Exams", "Quizzes", "Daily Tasks"]

    rules = leaderboard.get_rules()
    assert rules == {
        "For attending an exam": 10,
        "For re attempting an exam": 0,
        "For each correct answer": 4,
        "For an incorrect answer": -1,
        "For reattending a quiz": 0,
        "For completing a study task from your daily tasks": 10,
    }


def test_the_leaderboard_says_when_each_board_is_worked_out(leaderboard):
    """The refresh policy is published on the same sheet as the rates. It is
    read back rather than assumed, because it is the reason a board is not
    expected to move the moment coins are earned."""
    leaderboard.open_info()
    hints = leaderboard.get_info_hint_texts()

    schedule = [hint for hint in hints if "update" in hint.lower()]
    assert schedule, hints
    print("refresh policy:", schedule)

    resets = [hint for hint in hints if "reset" in hint.lower()]
    assert resets, hints
    for hint in resets:
        print("reset:", hint)


def test_today_is_the_one_board_that_reads_live(page, leaderboard):
    """Today is worked out from the balance as it stands rather than on the
    nightly rebuild: the student's row on Today is the coins call, to the
    coin.

    The longer boards are left alone here on purpose - what they carry is
    whatever the last rebuild left, which this test has no way to know."""
    served = open_tab(page, leaderboard, "Today")
    balance = read_balance(page)
    mine = next((row for row in served if row["is_current_user"]), None)

    if mine is None:
        assert balance == 0, f"nothing on Today, but the balance is {balance}"
        return

    assert mine["coins"] == balance
    assert leaderboard.get_coins()[leaderboard.current_row_index()] == balance
