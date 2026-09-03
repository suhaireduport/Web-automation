"""What else the coin ledger is wired to, and what it turns out not to be.

Looked for by following the calls the app makes and the paths its bundle
carries, rather than by guessing at names:

  Exams          exams/exam-start pays into the same ledger. An exam that has
                 been attempted leaves an exam_attended event in the coin log,
                 worth the rate the leaderboard publishes. Attempting one is
                 one way only - the backend answers a second exam-start with
                 406 - so the rate is checked against an attempt the account
                 already carries rather than by spending an exam on it.
  Streaks        analytics/streak/now, its own call and its own screen. It is
                 not a coin figure, but it is set by the same activity: a day
                 with something in the coin log is a day the streak counts.
  Profile        the name and the picture on a leaderboard row are the
                 student's, and profile is where those come from.
  Practice/Quiz  where the coins come from. Covered in
                 test_daily_task_coins.py.
  Progress       a topic's checkpoint quiz pays into the ledger too, as
                 checkpoint_quiz_completed. What watching does to progress is
                 covered in test_progress.py; what the quiz pays follows the
                 same quiz rates and is checked here only as far as the ledger
                 shows it.

  Notifications  no call and no screen. The bundle carries no notifications
                 path at all, so there is nothing to check.
  Rewards        no rewards call either. The reward data the app does keep is
                 the coin log, and that is checked in test_leaderboard.py.
  Question       reached through the same practice quizzes and carries no coin
  Library        figure of its own, so it adds nothing here.
"""
import pytest
from playwright.sync_api import expect

from pages.leaderboard_page import LeaderboardPage, call_api, read_coin_log
from pages.streak_page import StreakPage

# The account carrying an exam attempt, and the one earning coins as this
# suite runs. They are different accounts because an exam attempt cannot be
# made twice and the one that has made one is not the one with questions left
# to practise.
EXAMS_MOBILE = "8893963137"
EARNING_MOBILE = "9876543210"

STREAK_API = "**/api/v3/analytics/streak/now"

# The tags the coin ledger uses, as seen on the accounts under test. Anything
# outside this set is something new to look at rather than a failure.
KNOWN_TAGS = {
    "exam_attended",
    "practice_problem_quiz_completed",
    "checkpoint_quiz_completed",
}


@pytest.fixture
def exams_page(login_as):
    return login_as(EXAMS_MOBILE)


@pytest.fixture
def earning_page(login_as):
    return login_as(EARNING_MOBILE)


def open_leaderboard(page):
    page.goto(LeaderboardPage.URL, wait_until="domcontentloaded")
    leaderboard = LeaderboardPage(page)
    leaderboard.wait_for_loaded()
    return leaderboard


# ---------------------------------------------------------------------------
# 1. Exams
# ---------------------------------------------------------------------------

def test_an_attempted_exam_pays_the_rate_the_leaderboard_publishes(exams_page):
    """Attending an exam is worth what the How to get coins sheet says it is.

    Read off an attempt the account already carries: an exam can only be
    started once, so this checks the rate the app applied rather than spending
    an exam to make it apply again."""
    leaderboard = open_leaderboard(exams_page)
    leaderboard.open_info()
    published = leaderboard.get_rules()["For attending an exam"]

    events = read_coin_log(exams_page, "log")
    attended = [event for event in events if event["tag"] == "exam_attended"]
    if not attended:
        pytest.skip("This account has never attempted an exam")

    print("exam events:", [(e["created"], e["score"]) for e in attended])
    for event in attended:
        assert event["score"] == published, event


def test_an_exam_award_is_on_the_board_and_in_the_log_sheet(exams_page):
    """The exam coins are part of what the student is ranked on, and the sheet
    behind their row shows the award itself."""
    leaderboard = open_leaderboard(exams_page)
    leaderboard.click_tab("All Time")

    served = call_api(exams_page, "/analytics/leaderboard/overall")["leaderboard"]
    mine = next((row for row in served if row["is_current_user"]), None)
    if mine is None:
        pytest.skip("This student is not on the All Time board")

    events = read_coin_log(exams_page, "log")
    attended = [event for event in events if event["tag"] == "exam_attended"]
    if not attended:
        pytest.skip("This account has never attempted an exam")

    assert mine["coins"] == sum(event["score"] for event in events)

    leaderboard.open_my_log()
    titles = leaderboard.get_log_titles()
    for event in attended:
        assert event["data"]["title"].strip() in titles, titles


def test_every_coin_event_is_one_of_the_kinds_the_app_pays_for(exams_page):
    """The ledger only ever carries events the app has a published rate for:
    an exam attended, a practice quiz completed, or a topic's checkpoint quiz
    completed."""
    open_leaderboard(exams_page)
    events = read_coin_log(exams_page, "log")
    if not events:
        pytest.skip("This account has earned nothing at all")

    tags = {event["tag"] for event in events}
    assert tags <= KNOWN_TAGS, f"the ledger carries something new: {tags - KNOWN_TAGS}"

    for event in events:
        assert event["data"]["title"].strip(), event
        assert isinstance(event["score"], int), event


# ---------------------------------------------------------------------------
# 2. Streaks
# ---------------------------------------------------------------------------

def open_streak_with_payload(page):
    """The streak screen together with the call it is drawn from."""
    with page.expect_response(STREAK_API) as answer:
        page.goto(StreakPage.URL, wait_until="domcontentloaded")
    assert answer.value.status == 200, f"streak answered {answer.value.status}"

    streak = StreakPage(page)
    streak.wait_for_loaded()
    return streak, answer.value.json()


@pytest.mark.parametrize("account", [EXAMS_MOBILE, EARNING_MOBILE])
def test_the_streak_screen_matches_the_streak_api(login_as, account):
    """The run the screen reads out is current_streak, and the days it lights
    up are that same run."""
    page = login_as(account)
    streak, served = open_streak_with_payload(page)

    assert streak.get_streak_from_message() == served["current_streak"]
    expect(streak.get_lit_days()).to_have_count(
        min(served["current_streak"], streak.get_days().count())
    )

    if served["current_streak"]:
        assert str(served["current_streak"]) in streak.get_title()
    else:
        assert "Start a Streak" in streak.get_title()


@pytest.mark.parametrize("account", [EXAMS_MOBILE, EARNING_MOBILE])
def test_a_streak_never_runs_past_the_best_one(login_as, account):
    """max_streak is the best run there has been, so the run going on now
    cannot be longer than it."""
    page = login_as(account)
    _, served = open_streak_with_payload(page)

    assert 0 <= served["current_streak"] <= served["max_streak"], served


def test_a_day_that_earned_coins_is_a_day_the_streak_counts(earning_page):
    """The streak and the coin log are two records of the same activity: an
    account with something in today's coin log has today counted."""
    open_leaderboard(earning_page)
    today = read_coin_log(earning_page, "log-today")

    streak, served = open_streak_with_payload(earning_page)
    print("today's events:", len(today), "| streak:", served)

    if not today:
        pytest.skip("This account has earned nothing today")

    assert served["is_today"] is True, (
        f"{len(today)} coin events today, but the streak does not count today"
    )
    assert served["current_streak"] >= 1
    expect(streak.get_lit_days()).not_to_have_count(0)


# ---------------------------------------------------------------------------
# 3. Profile
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("account", [EXAMS_MOBILE, EARNING_MOBILE])
def test_the_leaderboard_row_is_the_student_the_profile_call_describes(
    login_as, account
):
    """The name and the picture on the student's own row come from their
    profile, so the row on screen is checked against the profile call rather
    than against anything written down here."""
    page = login_as(account)
    leaderboard = open_leaderboard(page)
    leaderboard.click_tab("All Time")

    served = call_api(page, "/analytics/leaderboard/overall")["leaderboard"]
    mine = next((row for row in served if row["is_current_user"]), None)
    if mine is None:
        pytest.skip("This student is not on the All Time board")

    student = call_api(page, "/profile")["student"]

    assert mine["student"].strip() == student["name"].strip()
    assert mine["avatar"] == student["avatar"]

    index = leaderboard.current_row_index()
    expect(leaderboard.get_row_name(index)).to_have_text(student["name"].strip())
    expect(leaderboard.get_row(index).locator("img.lb-row-avatar")).to_have_attribute(
        "src", student["avatar"]
    )
