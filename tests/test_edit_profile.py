"""Edit Details, and what the home page shows afterwards.

Saving writes to a real account, and this one is the login the rest of the
suite signs in as, so every test that changes something puts it back.
"""
import random
import re
import string

import pytest
from playwright.sync_api import expect

from pages.edit_profile_page import EditProfilePage
from pages.home_page import HomePage
from pages.profile_menu_page import ProfileMenuPage

MOBILE = "9876543210"

HOME_URL = "https://eduport-react.pages.dev/"
EDIT_PROFILE_URL = EditProfilePage.URL


def random_name():
    """Test plus a random suffix, so no two edits write the same name."""
    return "Test " + "".join(random.choices(string.ascii_uppercase, k=6))


def session_value(page, key):
    """The app mirrors the account into localStorage, so assertions can read the
    real values instead of repeating them as literals."""
    return page.evaluate("key => localStorage.getItem(key)", key)


def displayed_name(home_page):
    """The name home is greeting the user by.

    Used instead of localStorage wherever a test needs the saved name: saving a
    profile leaves localStorage holding the previous value until the next full
    load, so it is not trustworthy mid run."""
    return home_page.get_greeting().inner_text().replace("Hello,", "").strip()


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(MOBILE)


@pytest.fixture
def home_page(page):
    page.goto(HOME_URL)

    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()
    return home_page


@pytest.fixture
def current_profile(home_page):
    """What home shows before anything is edited.

    Captured through its own fixture so it is read while home is still the page
    on screen, whatever order the fixtures of a test are listed in."""
    return {
        "name": displayed_name(home_page),
        "course": home_page.get_course_button().inner_text().strip(),
    }


@pytest.fixture
def edit_page(home_page, current_profile):
    """Opened the way a user reaches it, through the profile menu.

    The form is filled in from the profile a moment after the page renders, and
    that arrives late enough to overwrite anything typed first, so wait for the
    saved name to land before handing the page over."""
    home_page.open_profile_menu()
    ProfileMenuPage(home_page.page).click_item("Edit details")

    edit_page = EditProfilePage(home_page.page)
    expect(edit_page.get_page()).to_be_visible()
    expect(edit_page.get_full_name_input()).not_to_have_value("")
    return edit_page


@pytest.fixture
def restore_profile(home_page, current_profile):
    """Put the name and course back, so the account the rest of the suite signs
    in as ends the run exactly as it started.

    Restored unconditionally rather than only when something looks changed:
    after a save the page still reports the old values, so nothing on screen can
    be trusted to decide whether a restore is needed."""
    page = home_page.page
    original_name = current_profile["name"]
    original_course = current_profile["course"]

    yield

    page.goto(EDIT_PROFILE_URL)
    edit_page = EditProfilePage(page)
    expect(edit_page.get_full_name_input()).not_to_have_value("")
    edit_page.enter_full_name(original_name)
    edit_page.select_course(original_course)
    edit_page.click_save()
    page.wait_for_url(HOME_URL, timeout=30000)
    page.reload()


# ---------------------------------------------------------------------------
# Scenario:   Edit Details opens from the profile menu
# Pre:        signed in, on the home page
# Steps:      open the profile menu, click Edit details
# Expected:   /profile/edit with its heading, form and Save button
# ---------------------------------------------------------------------------

def test_edit_details_page_opens_from_the_profile_menu(page, edit_page):
    expect(page).to_have_url(EDIT_PROFILE_URL)
    expect(edit_page.get_title()).to_have_text("Edit Details")
    expect(edit_page.get_form()).to_be_visible()
    expect(edit_page.get_save_button()).to_be_enabled()


# ---------------------------------------------------------------------------
# Scenario:   the form arrives holding the saved profile
# Pre:        the edit page is open
# Steps:      read the fields
# Expected:   name and course match the session, not a hard coded string
# ---------------------------------------------------------------------------

def test_edit_details_is_prefilled_with_the_current_profile(current_profile, edit_page):
    expect(edit_page.get_full_name_input()).to_have_value(current_profile["name"])

    assert edit_page.get_current_course() == current_profile["course"]


def test_edit_details_shows_the_account_badges(page, edit_page):
    """Phone and student id never change, so localStorage is safe to read."""
    expect(edit_page.get_badges()).to_have_count(2)
    expect(edit_page.get_phone_badge()).to_contain_text(session_value(page, "phone_no"))
    expect(edit_page.get_student_id_badge()).to_have_text(
        session_value(page, "unique_student_id")
    )


# ---------------------------------------------------------------------------
# Scenario:   the date of birth is fixed once the account has one
# Pre:        the edit page is open
# Steps:      inspect the Date of Birth field
# Expected:   it holds the saved date, is marked locked and cannot be typed in
# ---------------------------------------------------------------------------

def test_date_of_birth_cannot_be_edited(edit_page):
    date_of_birth = edit_page.get_date_of_birth_input()

    expect(date_of_birth).to_be_visible()
    expect(date_of_birth).to_be_disabled()
    expect(date_of_birth).to_have_class(re.compile("edp-input-locked"))

    assert date_of_birth.input_value()


# ---------------------------------------------------------------------------
# Scenario:   changing the name reaches the home page
# Pre:        the edit page is open
# Steps:      type a new name, Save, reload home
# Expected:   the greeting shows the new name
#
# The reload is needed rather than incidental: saving returns to home still
# showing the previous name. See the xfail below, which is the same check
# without it.
# ---------------------------------------------------------------------------

def test_changing_the_name_updates_the_home_greeting(page, edit_page, restore_profile):
    new_name = random_name()

    edit_page.enter_full_name(new_name)
    edit_page.click_save()
    page.wait_for_url(HOME_URL, timeout=30000)
    page.reload()

    expect(HomePage(page).get_greeting()).to_have_text(f"Hello, {new_name}")


# ---------------------------------------------------------------------------
# Scenario:   the greeting keeps up with a save on its own
# Pre:        the edit page is open
# Steps:      type a new name, Save
# Expected:   the greeting home returns to shows the name just saved
#
# Known defect: the profile is stored correctly, but home is not refreshed with
# it. The greeting, the profile menu and localStorage all keep the previous
# name until the next full load. Left as xfail so the suite stays green and
# this reports XPASS the moment the app starts refreshing.
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason="Saving a name does not refresh home; the old name shows until reload",
)
def test_home_greeting_updates_without_a_reload(page, edit_page, restore_profile):
    new_name = random_name()

    edit_page.enter_full_name(new_name)
    edit_page.click_save()
    page.wait_for_url(HOME_URL, timeout=30000)

    expect(HomePage(page).get_greeting()).to_have_text(f"Hello, {new_name}")


# ---------------------------------------------------------------------------
# Scenario:   a changed name sticks
# Pre:        the edit page is open
# Steps:      save a new name, reopen Edit Details
# Expected:   the form comes back holding the new name
# ---------------------------------------------------------------------------

def test_changed_name_is_kept_in_the_edit_form(page, edit_page, restore_profile):
    new_name = random_name()

    edit_page.enter_full_name(new_name)
    edit_page.click_save()
    page.wait_for_url(HOME_URL, timeout=30000)

    page.goto(EDIT_PROFILE_URL)

    expect(edit_page.get_full_name_input()).to_have_value(new_name)


# ---------------------------------------------------------------------------
# Scenario:   a changed name reaches the profile menu
# Pre:        the edit page is open
# Steps:      save a new name, open the profile menu on home
# Expected:   the menu names the user by the new name
# ---------------------------------------------------------------------------

def test_changed_name_shows_in_the_profile_menu(page, edit_page, restore_profile):
    new_name = random_name()

    edit_page.enter_full_name(new_name)
    edit_page.click_save()
    page.wait_for_url(HOME_URL, timeout=30000)
    page.reload()

    home_page = HomePage(page)
    home_page.get_subjects().first.wait_for()
    home_page.open_profile_menu()

    expect(ProfileMenuPage(page).get_user_name()).to_have_text(new_name)


# ---------------------------------------------------------------------------
# Scenario:   changing the course reaches the home page
# Pre:        the edit page is open
# Steps:      pick a different course, Save
# Expected:   back on home, the course badge shows the newly chosen course
# ---------------------------------------------------------------------------

def test_changing_the_course_updates_the_home_course_badge(page, edit_page, restore_profile):
    previous_course = edit_page.get_current_course()
    new_course = edit_page.select_other_option("Course")
    assert new_course != previous_course

    edit_page.click_save()
    page.wait_for_url(HOME_URL, timeout=30000)

    home_page = HomePage(page)

    expect(home_page.get_course_button()).to_have_text(new_course)


# ---------------------------------------------------------------------------
# Scenario:   name and course change together
# Pre:        the edit page is open
# Steps:      set both, Save
# Expected:   home shows both new values at once
# ---------------------------------------------------------------------------

def test_changing_name_and_course_together_shows_both_on_home(page, edit_page, restore_profile):
    new_name = random_name()
    new_course = edit_page.select_other_option("Course")
    edit_page.enter_full_name(new_name)

    edit_page.click_save()
    page.wait_for_url(HOME_URL, timeout=30000)

    home_page = HomePage(page)

    expect(home_page.get_greeting()).to_have_text(f"Hello, {new_name}")
    expect(home_page.get_course_button()).to_have_text(new_course)


# ---------------------------------------------------------------------------
# Scenario:   saving without touching anything changes nothing
# Pre:        the edit page is open
# Steps:      Save straight away
# Expected:   home still shows the same name and course
# ---------------------------------------------------------------------------

def test_saving_without_changes_leaves_the_profile_alone(page, edit_page):
    name = edit_page.get_full_name()
    course = edit_page.get_current_course()

    edit_page.click_save()
    page.wait_for_url(HOME_URL, timeout=30000)

    home_page = HomePage(page)

    expect(home_page.get_greeting()).to_have_text(f"Hello, {name}")
    expect(home_page.get_course_button()).to_have_text(course)


# ---------------------------------------------------------------------------
# Scenario:   leaving without saving keeps the profile
# Pre:        the edit page is open
# Steps:      type a new name, go back instead of saving
# Expected:   home still greets the user by the name saved before
# ---------------------------------------------------------------------------

def test_leaving_without_saving_discards_the_change(page, edit_page):
    saved_name = edit_page.get_full_name()
    edit_page.enter_full_name(random_name())

    edit_page.click_back()
    page.wait_for_url(HOME_URL, timeout=30000)
    page.reload()

    expect(HomePage(page).get_greeting()).to_have_text(f"Hello, {saved_name}")
