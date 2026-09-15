"""The Profile page behind the home avatar.

The home avatar used to drop a small menu; it now opens a full Profile page at
/profile. The hero across the top is the account - name, number, join date,
leaderboard rank and coins - and it is drawn from two calls: profile for the
identity and profile/analysis for the row of stat tiles under it. Below that
sit a study reminder, a settings grid and a help grid, then Sign Out.

Edit Details is unchanged and lives at /profile/edit; it is covered in
test_edit_profile.py. What is checked here is the Profile page itself: that it
shows what its calls carry, that its cards do what they say, and that Sign Out
asks first.

The identity on the hero is not drawn from the profile call - the page never
makes one. It comes from the home call the page makes on load, which is where
the avatar, the join date and the mentor behind Call My Mentor come from too,
so that payload is what those are held against.

Three of the cards raise a sheet instead of routing: My Account is a small
editable form, Help Center is a hosted form in an iframe, and WhatsApp and
Contact Us both open the same contact sheet.

This account is the one the rest of the suite signs in as, and the context it
is signed in on is shared, so everything here that changes something puts it
back: the name saved through My Account, the study reminder switch, and the
session that Sign Out clears.
"""
import random
import re
import string
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import expect

from conftest import STUDENT_MOBILE
from pages.edit_profile_page import EditProfilePage
from pages.home_page import HomePage
from pages.profile_page import ProfilePage
from pages.leaderboard_page import call_api, read_balance


HOME_URL = "https://eduport-react.pages.dev/"
PROFILE_URL = ProfilePage.URL
EDIT_PROFILE_URL = "https://eduport-react.pages.dev/profile/edit"
SUBSCRIPTIONS_URL = "https://eduport-react.pages.dev/subscriptions"
PREFERENCES_URL = "https://eduport-react.pages.dev/preferences"

ANALYSIS_API = "**/api/v3/profile/analysis"
HOME_API = "**/api/v3/home"
PROFILE_UPDATE_API = "**/api/v3/profile/update"
TERMS_URL = "https://eduport-react.pages.dev/terms"
LOGIN_URL = "https://eduport-react.pages.dev/login"

# What the page draws in place of a number it has not been given yet, and what
# it falls back to when the call it wanted never arrives.
PENDING = "\u2026"
MISSING = "--"


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(STUDENT_MOBILE)


@pytest.fixture
def home_page(page):
    home = HomePage(page)
    home.get_subjects().first.wait_for()
    return home


@pytest.fixture
def profile_page(page, home_page):
    """Opened the way a user reaches it: tap the avatar in the home header."""
    home_page.open_profile_menu()
    profile = ProfilePage(page)
    expect(page).to_have_url(PROFILE_URL)
    profile.wait_for_loaded()
    return profile


def open_profile_with(page, api):
    """Load the Profile page and hand back the payload behind one of its
    calls."""
    with page.expect_response(api) as answer:
        page.goto(PROFILE_URL, wait_until="domcontentloaded")
    assert answer.value.status == 200, f"{api} answered {answer.value.status}"
    profile = ProfilePage(page)
    profile.wait_for_loaded()
    return profile, answer.value.json()


def digits(text):
    return re.sub(r"\D", "", text)


# ---------------------------------------------------------------------------
# 1. The avatar opens the Profile page
# ---------------------------------------------------------------------------

def test_the_home_avatar_opens_the_profile_page(page, home_page):
    home_page.open_profile_menu()

    expect(page).to_have_url(PROFILE_URL)
    profile = ProfilePage(page)
    expect(profile.get_title()).to_have_text("Profile")


def test_profile_page_shows_its_sections(profile_page):
    expect(profile_page.get_name()).to_be_visible()
    expect(profile_page.get_phone()).to_be_visible()
    expect(profile_page.get_stats()).to_have_count(4)
    assert profile_page.get_section_titles() == ["Settings", "Help & Support"]


# ---------------------------------------------------------------------------
# 2. The hero against the profile call  (API + UI)
# ---------------------------------------------------------------------------

def test_the_hero_matches_the_profile_api(page, profile_page):
    """Name, number, course and the My Account student id are what the profile
    call carries, not values written down here.

    The Profile page draws the identity from what was cached at sign in and does
    not call profile itself, so the call is made directly and held against the
    hero on screen."""
    student = call_api(page, "/profile")["student"]

    expect(profile_page.get_name()).to_have_text(student["name"])
    assert digits(profile_page.get_phone().inner_text()) == digits(student["phone"])
    expect(profile_page.get_course_name()).to_have_text(student["course_name"])
    expect(profile_page.get_my_account_sub()).to_have_text(student["unique_student_id"])


def test_the_coins_match_the_coins_api(page, profile_page):
    """The coin pill on the hero is the same balance the coins call answers."""
    assert profile_page.get_coins() == read_balance(page)


# ---------------------------------------------------------------------------
# 3. The stat tiles against the analysis call  (API + UI)
# ---------------------------------------------------------------------------

def test_the_stat_tiles_match_the_analysis_api(page):
    """The four tiles under the hero are drawn from profile/analysis: the time
    spent, the streak, the task tally and the leaderboard rank."""
    profile, analysis = open_profile_with(page, ANALYSIS_API)

    assert profile.get_stat_labels() == [
        "Time Spent Today",
        "Current Streak",
        "Task Completed",
        "Latest Exam Results",
    ]

    assert digits(profile.get_stat_value("Current Streak")) == str(
        analysis["current_streak"]
    )
    assert profile.get_stat_value("Task Completed") == (
        f"{analysis['completed_tasks']}/{analysis['total_tasks']}"
    )
    # Time spent is drawn in minutes.
    assert digits(profile.get_stat_value("Time Spent Today")) == str(
        analysis["time_spend"]
    )


def test_the_leaderboard_rank_matches_the_analysis_api(page):
    """The rank on the hero is the leaderboard rank the analysis call reports."""
    profile, analysis = open_profile_with(page, ANALYSIS_API)

    expect(profile.get_rank_label()).to_have_text("Leaderboard")
    assert digits(profile.get_rank_number().inner_text()) == str(
        analysis["leader_board_rank"]
    )


# ---------------------------------------------------------------------------
# 4. Persistence
# ---------------------------------------------------------------------------

def test_the_profile_reads_the_same_after_a_reload(page, profile_page):
    name = profile_page.get_name().inner_text()
    phone = profile_page.get_phone().inner_text()

    page.reload(wait_until="domcontentloaded")
    profile_page.wait_for_loaded()

    expect(profile_page.get_name()).to_have_text(name)
    expect(profile_page.get_phone()).to_have_text(phone)
    assert call_api(page, "/profile")["student"]["name"] == name


# ---------------------------------------------------------------------------
# 5. Navigation
# ---------------------------------------------------------------------------

def test_the_avatar_pencil_opens_edit_details(page, profile_page):
    profile_page.open_edit_details()

    expect(page).to_have_url(EDIT_PROFILE_URL)


def test_my_courses_opens_subscriptions(page, profile_page):
    profile_page.click_card("My Courses")

    expect(page).to_have_url(SUBSCRIPTIONS_URL)


def test_preferences_opens_the_preferences_page(page, profile_page):
    profile_page.click_card("Preferences")

    expect(page).to_have_url(PREFERENCES_URL)


def test_the_course_button_names_the_current_course(page, profile_page):
    """The course button in the app bar carries the account's course, the same
    the profile call holds."""
    student = call_api(page, "/profile")["student"]

    expect(profile_page.get_course_name()).to_have_text(student["course_name"])


# ---------------------------------------------------------------------------
# 6. Sign out asks first
# ---------------------------------------------------------------------------

def test_sign_out_asks_for_confirmation(profile_page):
    profile_page.click_sign_out()

    expect(profile_page.get_sign_out_dialog()).to_be_visible()
    expect(profile_page.get_sign_out_title()).to_have_text("Sign Out!")
    expect(profile_page.get_sign_out_confirm()).to_be_visible()
    expect(profile_page.get_sign_out_cancel()).to_be_visible()


def test_declining_sign_out_keeps_the_user_on_the_profile(page, profile_page):
    profile_page.click_sign_out()
    expect(profile_page.get_sign_out_dialog()).to_be_visible()

    profile_page.cancel_sign_out()

    expect(profile_page.get_sign_out_dialog()).to_have_count(0)
    expect(page).to_have_url(PROFILE_URL)


# ---------------------------------------------------------------------------
# Fixtures that put back what a test changes
#
# The account is the suite's own login and the context it is signed in on is
# shared between tests, so anything written here is written back.
# ---------------------------------------------------------------------------

@pytest.fixture
def restore_account_name(page):
    """Hand back the saved name, and put it back afterwards.

    Put back through Edit Details rather than through the sheet that changed it:
    the sheet fills its box from the copy of the account kept in the browser,
    which is not always the name the account actually holds, and it will not
    send a save unless the box is left holding something other than what it was
    opened with. Edit Details fills itself from the profile call, so writing the
    original name there is always a change it will send."""
    original = call_api(page, "/profile")["student"]["name"]

    yield original

    page.goto(EDIT_PROFILE_URL, wait_until="domcontentloaded")
    edit_page = EditProfilePage(page)
    expect(edit_page.get_full_name_input()).not_to_have_value("")
    edit_page.enter_full_name(original)
    with page.expect_response(PROFILE_UPDATE_API) as answer:
        edit_page.click_save()
    assert answer.value.status == 200, f"restoring the name answered {answer.value.status}"

    # Save takes the app back to the screen Edit was opened from, which is the
    # Profile page. That is waited on rather than navigated to: driving the page
    # anywhere while it is already going somewhere interrupts both.
    page.wait_for_url(PROFILE_URL)
    ProfilePage(page).wait_for_loaded()
    assert call_api(page, "/profile")["student"]["name"] == original


@pytest.fixture
def restore_reminder(profile_page):
    """The reminder switch is remembered between loads, so put it back."""
    was_on = profile_page.is_reminder_on()

    yield was_on

    profile_page.page.goto(PROFILE_URL, wait_until="domcontentloaded")
    profile_page.wait_for_loaded()
    profile_page.set_reminder(was_on)


@pytest.fixture
def restore_session(page):
    """Sign Out empties the session out of the shared context, so put it back.

    Signing out is a browser side clear - no call is made and the token is not
    retired - so writing back what was there signs the context in again."""
    saved = page.evaluate("() => JSON.stringify(Object.entries(localStorage))")

    yield

    page.evaluate(
        """raw => {
            localStorage.clear();
            for (const [key, value] of JSON.parse(raw)) localStorage.setItem(key, value);
        }""",
        saved,
    )


def joined_from(doj):
    """"Joined on February 2026" out of the date of joining the call carries."""
    return "Joined on " + datetime.strptime(doj, "%Y-%m-%d").strftime("%B %Y")


# ---------------------------------------------------------------------------
# 7. The hero against the home call  (API + UI)
#
# The profile call is checked above because it is the account of record. These
# hold the hero against the call the page actually makes, which is the only
# place the avatar and the join date come from.
# ---------------------------------------------------------------------------

def test_the_hero_matches_the_home_api(page):
    """Name, number, course and avatar are what the home call handed the page."""
    profile, home = open_profile_with(page, HOME_API)
    user = home["user"]

    expect(profile.get_name()).to_have_text(user["name"])
    assert digits(profile.get_phone().inner_text()) == digits(user["phone"])
    expect(profile.get_course_name()).to_have_text(user["course_name"].strip())
    expect(profile.get_avatar_image()).to_have_attribute("src", user["avatar"])


def test_the_join_date_matches_the_home_api(page):
    """The line under the number is the date of joining, drawn as month and
    year."""
    profile, home = open_profile_with(page, HOME_API)

    expect(profile.get_joined()).to_have_text(joined_from(home["user"]["doj"]))


# ---------------------------------------------------------------------------
# 8. The last stat tile
#
# Covered apart from the other three: it is the one that has something to say
# when there is nothing to report.
# ---------------------------------------------------------------------------

def test_the_latest_exam_results_tile_reports_the_rank_or_says_there_is_none(page):
    profile, analysis = open_profile_with(page, ANALYSIS_API)
    tile = profile.get_stat_value("Latest Exam Results")

    if analysis["rank"] is None:
        assert tile == "No Ranks", f"no rank was reported but the tile read {tile!r}"
    else:
        assert digits(tile) == str(analysis["rank"])


# ---------------------------------------------------------------------------
# 9. The study reminder
# ---------------------------------------------------------------------------

def test_the_study_reminder_offers_a_switch(profile_page):
    expect(profile_page.get_reminder_title()).to_have_text("Study Reminder")
    expect(profile_page.get_reminder_hint()).not_to_be_empty()
    expect(profile_page.get_reminder_switch()).to_be_visible()


def test_the_study_reminder_switch_turns_over(profile_page, restore_reminder):
    was_on = restore_reminder

    profile_page.toggle_reminder()

    expect(profile_page.get_reminder_switch()).to_have_attribute(
        "aria-checked", str(not was_on).lower()
    )


def test_the_study_reminder_setting_is_remembered(page, profile_page, restore_reminder):
    """Nothing is sent for it - it is kept in the browser - so a reload is what
    proves it was kept at all."""
    was_on = restore_reminder
    profile_page.toggle_reminder()

    page.reload(wait_until="domcontentloaded")
    profile_page.wait_for_loaded()

    assert profile_page.is_reminder_on() is (not was_on)


# ---------------------------------------------------------------------------
# 10. The cards the page offers
# ---------------------------------------------------------------------------

def test_the_page_offers_its_settings_and_help_cards(profile_page):
    assert profile_page.get_card_titles() == [
        "My Account",
        "My Courses",
        "Preferences",
        "Refer a Friend",
        "Help Center",
        "WhatsApp",
        "Contact Us",
        "Call My Mentor",
    ]


# ---------------------------------------------------------------------------
# 11. My Account
#
# The one card that does not route anywhere: it raises a sheet holding a short
# editable form over the page.
# ---------------------------------------------------------------------------

def test_my_account_opens_a_sheet_holding_the_account(page):
    """Name and gender are what the home call carries, not values written down
    here."""
    profile, home = open_profile_with(page, HOME_API)
    user = home["user"]

    profile.open_my_account()

    expect(profile.get_account_title()).to_have_text("My Account")
    expect(profile.get_account_name_input()).to_have_value(user["name"])
    assert profile.get_account_gender_names() == ["Female", "Male"]
    assert profile.get_selected_gender() == user["gender"]
    # Whatever the sheet is showing is what it offers to save, so the hero and
    # the form have to be naming the same person.
    expect(profile.get_name()).to_have_text(profile.get_account_name())


def test_my_account_will_not_let_the_date_of_birth_be_edited(profile_page):
    """Three boxes, all locked - the same rule Edit Details keeps."""
    profile_page.open_my_account()

    selects = profile_page.get_account_dob_selects()
    expect(selects).to_have_count(3)
    for index in range(3):
        expect(selects.nth(index)).to_be_disabled()


def test_my_account_save_stays_down_until_something_is_changed(profile_page):
    profile_page.open_my_account()
    assert profile_page.account_save_is_armed() is False

    profile_page.enter_account_name(profile_page.get_account_name() + " X")

    assert profile_page.account_save_is_armed() is True


def test_my_account_refuses_to_save_an_empty_name(page, profile_page):
    """Nothing is sent and the sheet stays up, so the account cannot be left
    nameless."""
    profile_page.open_my_account()
    profile_page.enter_account_name("")

    sent = []
    page.on("request", lambda request: sent.append(request.url))
    profile_page.save_account()
    page.wait_for_timeout(3000)

    assert [url for url in sent if "profile/update" in url] == []
    expect(profile_page.get_account_sheet()).to_be_visible()


def test_my_account_saves_a_new_name(page, profile_page, restore_account_name):
    """Saved through the sheet, then read back off the account rather than off
    the screen the save left behind."""
    new_name = "Test " + "".join(random.choices(string.ascii_uppercase, k=6))
    profile_page.open_my_account()
    profile_page.enter_account_name(new_name)

    with page.expect_response(PROFILE_UPDATE_API) as answer:
        profile_page.save_account()

    assert answer.value.status == 200, f"profile/update answered {answer.value.status}"
    expect(profile_page.get_account_overlay()).to_have_count(0)
    assert call_api(page, "/profile")["student"]["name"] == new_name


def test_leaving_my_account_without_saving_keeps_the_name(page, profile_page):
    saved_name = call_api(page, "/profile")["student"]["name"]
    profile_page.open_my_account()
    profile_page.enter_account_name("Test Discarded")

    profile_page.exit_account_without_saving()

    expect(profile_page.get_account_overlay()).to_have_count(0)
    assert call_api(page, "/profile")["student"]["name"] == saved_name


def test_tapping_outside_my_account_closes_it(profile_page):
    profile_page.open_my_account()

    profile_page.close_account_from_outside()

    expect(profile_page.get_account_overlay()).to_have_count(0)


# ---------------------------------------------------------------------------
# 12. Help & Support
# ---------------------------------------------------------------------------

def test_help_center_opens_a_form_that_already_knows_the_account(page):
    """The form is hosted elsewhere and is handed the account in its address,
    so what it was handed is held against the home call."""
    profile, home = open_profile_with(page, HOME_API)
    user = home["user"]

    profile.open_help_center()

    expect(profile.get_help_iframe()).to_be_visible()
    handed = parse_qs(urlparse(profile.get_help_iframe().get_attribute("src")).query)
    assert handed["name"][0] == user["name"]
    assert handed["phone"][0] == user["phone"]
    assert handed["unique_student_id"][0] == user["unique_student_id"]
    assert handed["current_choosed_course"][0].strip() == user["course_name"].strip()


def test_help_center_closes_again(profile_page):
    profile_page.open_help_center()

    profile_page.close_help_center()

    expect(profile_page.get_help_overlay()).to_have_count(0)


@pytest.mark.parametrize("card", ["Contact Us", "WhatsApp"])
def test_both_contact_cards_open_the_same_contact_sheet(profile_page, card):
    profile_page.open_contact_sheet(card)

    expect(profile_page.get_contact_title()).to_have_text("Contact Us")
    assert profile_page.get_contact_option_labels() == ["Whatsapp", "Contact Us"]


def test_call_my_mentor_dials_the_mentor_the_home_api_names(page):
    """It dials rather than navigating, so the number it asked for is what is
    checked, against the mentor on the account."""
    profile, home = open_profile_with(page, HOME_API)
    mentor_number = digits(home["user"]["mentor"]["number"])

    with page.expect_request(lambda request: request.url.startswith("tel:")) as dialled:
        profile.click_card("Call My Mentor")

    assert digits(dialled.value.url) == mentor_number


# ---------------------------------------------------------------------------
# 13. Getting back out
# ---------------------------------------------------------------------------

def test_back_returns_to_the_page_the_profile_was_opened_from(page, home_page):
    home_page.open_profile_menu()
    profile = ProfilePage(page)
    profile.wait_for_loaded()

    profile.click_back()

    expect(page).to_have_url(HOME_URL)


def test_the_footer_opens_the_terms(page, profile_page):
    expect(profile_page.get_footer_build()).not_to_be_empty()

    profile_page.click_footer_links()

    expect(page).to_have_url(TERMS_URL)


# ---------------------------------------------------------------------------
# 14. Sign out, gone through
#
# Covered apart from the two above, which only open the dialog: this is the one
# test that actually signs out, and it puts the session back afterwards.
# ---------------------------------------------------------------------------

def test_tapping_outside_the_sign_out_dialog_dismisses_it(page, profile_page):
    profile_page.click_sign_out()
    expect(profile_page.get_sign_out_dialog()).to_be_visible()

    profile_page.dismiss_sign_out_outside()

    expect(profile_page.get_sign_out_dialog()).to_have_count(0)
    expect(page).to_have_url(PROFILE_URL)


def test_the_sign_out_dialog_says_what_it_is_about_to_do(profile_page):
    profile_page.click_sign_out()

    expect(profile_page.get_sign_out_body()).to_have_text(
        "Are you sure you want to sign out?"
    )
    expect(profile_page.get_sign_out_cancel()).to_have_text("No")
    expect(profile_page.get_sign_out_confirm()).to_have_text("Yes")


def test_signing_out_returns_to_login_and_shuts_the_profile(page, profile_page, restore_session):
    profile_page.click_sign_out()
    expect(profile_page.get_sign_out_dialog()).to_be_visible()

    profile_page.confirm_sign_out()

    expect(page).to_have_url(LOGIN_URL)
    assert page.evaluate("() => localStorage.getItem('eduport_auth_token')") is None

    # And the page it came from is shut behind it rather than merely left.
    page.goto(PROFILE_URL, wait_until="domcontentloaded")
    expect(page).to_have_url(LOGIN_URL)


# ---------------------------------------------------------------------------
# 15. Loading, and what is left when a call does not arrive
#
# The identity is mirrored into the browser at sign in, so the hero and the
# cards stand whatever happens to the calls; it is the tiles and the rank that
# have nothing to draw.
# ---------------------------------------------------------------------------

def test_the_tiles_show_a_placeholder_while_the_analysis_call_is_out(page):
    """Hold the analysis call open so the loading state cannot be missed."""
    held = []
    page.route(ANALYSIS_API, lambda route: held.append(route))

    page.goto(PROFILE_URL, wait_until="commit")

    profile = ProfilePage(page)
    profile.wait_for_loaded()
    expect(profile.get_stats()).to_have_count(4)
    assert profile.get_stat_labels() == [
        "Time Spent Today",
        "Current Streak",
        "Task Completed",
        "Latest Exam Results",
    ]
    for label in profile.get_stat_labels():
        assert profile.get_stat_value(label) == PENDING, (
            f"{label} was drawn before the call answered"
        )
    expect(profile.get_rank_number()).to_have_text(PENDING)


def test_the_profile_still_stands_when_the_analysis_call_fails(page):
    """A 500 costs the page its tiles and its rank, and nothing else."""
    page.route(
        ANALYSIS_API,
        lambda route: route.fulfill(status=500, json={"message": "server error"}),
    )

    page.goto(PROFILE_URL, wait_until="domcontentloaded")

    profile = ProfilePage(page)
    profile.wait_for_loaded()
    expect(profile.get_title()).to_have_text("Profile")
    expect(profile.get_name()).not_to_be_empty()
    expect(profile.get_rank_number()).to_have_text(MISSING)
    expect(profile.get_stats()).to_have_count(4)
    for label in profile.get_stat_labels():
        assert profile.get_stat_value(label), f"{label} was left blank"
    expect(profile.get_sign_out_button()).to_be_visible()


def test_the_profile_still_stands_when_the_home_call_fails(page):
    """The join date is the only thing on the hero that has nowhere else to come
    from, so it is the one that goes."""
    page.route(HOME_API, lambda route: route.abort())

    page.goto(PROFILE_URL, wait_until="domcontentloaded")

    profile = ProfilePage(page)
    profile.wait_for_loaded()
    expect(profile.get_title()).to_have_text("Profile")
    expect(profile.get_name()).not_to_be_empty()
    expect(profile.get_phone()).not_to_be_empty()
    expect(profile.get_joined()).to_have_text(f"Joined on {MISSING}")
    expect(profile.get_my_account_sub()).not_to_be_empty()
    expect(profile.get_sign_out_button()).to_be_visible()
