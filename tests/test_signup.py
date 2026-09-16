"""New user signup, driven from the phone-number screen the way the app is used.

A number the backend has never seen verifies its OTP onto the /new-user
wizard; a known one goes straight to home (that branch is covered in
test_otp.py and not repeated here). The wizard is three steps on one route -
details, class and course, avatar - and the account is created by a single
POST to profile/update when Skip is tapped on the avatar step. Only the
happy-path test carries it through to that point, so only it leaves an account
behind.

The old single /signup form - date of birth, an avatar grid and Board / Class /
Course dropdowns - is gone, so nothing here opens /signup.
"""
import random
import re
import string

import pytest
from playwright.sync_api import expect

from pages.login_page import LoginPage
from pages.otp_page import OtpPage
from pages.home_page import HomePage
from pages.signup_page import PersonalisingPage, SignupPage
from pages.leaderboard_page import call_api

OTP = "4305"

OTP_URL = OtpPage.URL
NEW_USER_URL = SignupPage.URL
HOME_URL = "https://eduport-react.pages.dev/"

PROFILE_UPDATE_API = "**/api/v3/profile/update"

# A class the dev catalogue keeps, used where a test needs to expand a class and
# pick a course. It is checked against the catalogue rather than assumed, so a
# test skips cleanly if the class is ever dropped or left without courses.
PREFERRED_CLASS = "Class 10"


def throwaway_number():
    """A fresh number, so a signup does not collide with an account the rest of
    the suite signs in as, and so a pending OTP from an earlier test does not
    refuse a new code."""
    return str(random.randint(6100000000, 6999999999))


def random_name():
    """Test plus a random suffix, so every signup is identifiable and no two
    runs enter the same name."""
    return "Test " + "".join(random.choices(string.ascii_uppercase, k=6))


def form_field(post_data, name):
    """Pull one field out of the multipart body profile/update is posted as."""
    if not post_data:
        return None
    match = re.search(
        r'name="' + re.escape(name) + r'"\r?\n\r?\n(.*?)\r?\n--', post_data, re.S
    )
    return match.group(1).strip() if match else None


def catalogue(page):
    """The class -> course tree the class step is drawn from: the free classes
    from courses_list and any premium ones alongside them."""
    classes = call_api(page, "/courses_list")["classes"]
    premium = call_api(page, "/premium_courses")["premium_courses"]
    return classes, premium


def pick_class_with_courses(page, preferred=PREFERRED_CLASS):
    """A class carrying at least one course, and its first course. Prefers the
    named class but falls back to the first that qualifies."""
    classes, _ = catalogue(page)
    by_title = {c["title"].strip(): c for c in classes}
    chosen = by_title.get(preferred)
    if not chosen or not chosen["courses"]:
        chosen = next((c for c in classes if c["courses"]), None)
    if chosen is None:
        pytest.skip("The catalogue has no class with a course to choose")
    course = chosen["courses"][0]
    return chosen["title"].strip(), course["title"].strip(), course["id"]


@pytest.fixture
def signup_page(page):
    """A new number sitting on step one of the wizard.

    On the rare chance the random number already belongs to a user the app goes
    to home instead, and the test skips rather than pretending to sign up."""
    LoginPage(page).login(throwaway_number())
    page.wait_for_url(OTP_URL, timeout=30000)
    OtpPage(page).enter_otp(OTP)
    page.wait_for_url(re.compile(r"/(new-user)?$"), timeout=30000)

    if page.url != NEW_USER_URL:
        pytest.skip("That number already belongs to a user, so no signup was asked for")

    signup = SignupPage(page)
    signup.wait_for_loaded()
    return signup


# ---------------------------------------------------------------------------
# Which branch a number takes
# ---------------------------------------------------------------------------

def test_a_new_number_lands_on_the_new_user_wizard(page, signup_page):
    """The wizard opens on its first step, Enter Your Details."""
    expect(page).to_have_url(NEW_USER_URL)
    expect(signup_page.get_title()).to_have_text("Enter Your Details")


# ---------------------------------------------------------------------------
# Step 1: the details
# ---------------------------------------------------------------------------

def test_step_one_asks_for_a_name_and_a_gender(signup_page):
    expect(signup_page.get_name_input()).to_be_visible()
    expect(signup_page.get_gender_pills()).to_have_count(2)
    labels = {text.strip() for text in signup_page.get_gender_pills().all_inner_texts()}
    assert {"Female", "Male"}.issubset(labels), labels
    expect(signup_page.get_details_cta()).to_have_text("Save & Continue")


def test_step_one_starts_empty_and_locked(signup_page):
    expect(signup_page.get_name_input()).to_have_value("")
    assert signup_page.get_selected_gender() is None
    assert not signup_page.details_cta_enabled()


def test_save_and_continue_stays_locked_until_both_are_given(signup_page):
    """Name alone or gender alone is not enough; both together unlock it."""
    signup_page.enter_name("Someone")
    assert not signup_page.details_cta_enabled(), "a name with no gender should not unlock"

    signup_page.enter_name("")
    signup_page.choose_gender("Female")
    assert not signup_page.details_cta_enabled(), "a gender with no name should not unlock"

    signup_page.enter_name("Someone")
    assert signup_page.details_cta_enabled()


def test_gender_is_a_single_choice(signup_page):
    signup_page.choose_gender("Female")
    assert signup_page.get_selected_gender() == "Female"

    signup_page.choose_gender("Male")
    assert signup_page.get_selected_gender() == "Male"
    expect(signup_page.get_selected_gender_pills()).to_have_count(1)


# ---------------------------------------------------------------------------
# Step 2: class and course  (API + UI)
# ---------------------------------------------------------------------------

def reach_class_step(signup_page):
    signup_page.enter_name(random_name())
    signup_page.choose_gender("Female")
    signup_page.submit_details()
    # The class list is drawn from courses_list, so wait for the rows to arrive
    # rather than only for the step's Confirm button.
    signup_page.get_class_rows().first.wait_for(timeout=30000)


def test_the_class_list_matches_the_courses_api(page, signup_page):
    """Every class the catalogue serves is offered, and nothing else is."""
    reach_class_step(signup_page)

    classes, premium = catalogue(page)
    expected = {c["title"].strip() for c in classes} | {
        c["title"].strip() for c in premium if isinstance(c, dict) and c.get("title")
    }

    shown = set(signup_page.get_class_names())
    assert shown == expected, {"only in UI": shown - expected, "only in API": expected - shown}


def test_a_class_expands_to_the_courses_the_api_lists_for_it(page, signup_page):
    """Tapping a class reveals exactly the courses the catalogue files under
    it."""
    reach_class_step(signup_page)
    class_title, _, _ = pick_class_with_courses(page)

    classes, _ = catalogue(page)
    listed = [
        c["title"].strip()
        for c in next(c for c in classes if c["title"].strip() == class_title)["courses"]
    ]

    signup_page.expand_class(class_title)
    expect(signup_page.get_course_tiles()).to_have_count(len(listed))
    assert signup_page.get_course_names() == listed


def test_confirm_class_is_locked_until_a_course_is_chosen(page, signup_page):
    reach_class_step(signup_page)
    class_title, course_title, _ = pick_class_with_courses(page)

    assert not signup_page.confirm_class_enabled(), "nothing chosen yet"

    signup_page.expand_class(class_title)
    assert not signup_page.confirm_class_enabled(), "a class opened but no course picked"

    signup_page.choose_course(course_title)
    assert signup_page.get_selected_course() == course_title
    assert signup_page.confirm_class_enabled()


def test_the_class_search_narrows_the_list(signup_page):
    reach_class_step(signup_page)
    everything = signup_page.get_class_rows().count()

    signup_page.search_class(PREFERRED_CLASS)
    signup_page.page.wait_for_timeout(800)
    narrowed = signup_page.get_class_names()

    assert 0 < len(narrowed) < everything, narrowed
    assert PREFERRED_CLASS in narrowed


# ---------------------------------------------------------------------------
# Step 3: the avatar
# ---------------------------------------------------------------------------

def reach_avatar_step(page, signup_page):
    reach_class_step(signup_page)
    class_title, course_title, course_id = pick_class_with_courses(page)
    signup_page.expand_class(class_title)
    signup_page.choose_course(course_title)
    signup_page.confirm_class()
    signup_page.get_set_profile_button().wait_for(timeout=30000)
    return course_title, course_id


def test_step_three_offers_avatars_and_the_two_actions(page, signup_page):
    reach_avatar_step(page, signup_page)

    expect(signup_page.get_title()).to_have_text("Choose Avatar")
    assert len(signup_page.get_avatar_names()) > 0
    expect(signup_page.get_set_profile_button()).to_be_visible()
    expect(signup_page.get_skip_button()).to_be_visible()


@pytest.mark.xfail(
    reason="Set Profile on the avatar step is a no-op: it fires no request and "
    "does not move off the wizard. Skip is the only working completion.",
    strict=False,
)
def test_set_profile_completes_the_signup(page, signup_page):
    """Set Profile is meant to finish signup with the chosen avatar. It does
    nothing at all today, so this documents the defect rather than asserting a
    behaviour that works."""
    reach_avatar_step(page, signup_page)

    with page.expect_response(PROFILE_UPDATE_API, timeout=8000):
        signup_page.set_profile()


# ---------------------------------------------------------------------------
# The whole flow  (API + UI)
# ---------------------------------------------------------------------------

def test_completing_signup_creates_the_account_with_the_entered_details(page, signup_page):
    """Skip finishes signup with the default avatar: profile/update is posted
    with the details as entered, and home then greets the new student by name
    and shows the course they picked.

    This is the one test that carries the wizard to completion, so it is the
    one that leaves an account behind."""
    name = random_name()
    signup_page.enter_name(name)
    signup_page.choose_gender("Male")
    signup_page.submit_details()
    signup_page.get_confirm_class_button().wait_for(timeout=30000)

    class_title, course_title, course_id = pick_class_with_courses(page)
    signup_page.expand_class(class_title)
    signup_page.choose_course(course_title)
    signup_page.confirm_class()
    signup_page.get_set_profile_button().wait_for(timeout=30000)

    # The account is created here. Hold the call so its payload and answer can
    # be checked against what was entered.
    with page.expect_response(PROFILE_UPDATE_API) as answer:
        signup_page.skip()
    response = answer.value
    assert response.status == 200, f"profile/update answered {response.status}"

    sent = response.request.post_data
    assert form_field(sent, "name") == name
    assert form_field(sent, "gender") == "Male"
    assert form_field(sent, "course_id") == str(course_id)

    body = response.json()
    assert body["name"] == name
    assert body["gender"] == "Male"

    # The wizard does not move off /new-user on its own; a load of home is what
    # shows the finished account.
    page.goto(HOME_URL, wait_until="domcontentloaded")
    home = HomePage(page)
    expect(home.get_greeting()).to_have_text(f"Hello, {name}", timeout=30000)
    expect(home.get_course_button()).to_have_text(course_title)
    expect(home.get_subjects().first).to_be_visible()


# ---------------------------------------------------------------------------
# Step 4: the summary, and the personalising screen it hands over to
# ---------------------------------------------------------------------------

def reach_summary_step(page, signup_page):
    """Carry the wizard through to the summary that saving the avatar lands on.

    Skip is what creates the account, so this leaves one behind, the same as
    the completion test above. Hands back the name and the course it was made
    with."""
    name = random_name()
    signup_page.enter_name(name)
    signup_page.choose_gender("Male")
    signup_page.submit_details()
    signup_page.get_confirm_class_button().wait_for(timeout=30000)

    class_title, course_title, _ = pick_class_with_courses(page)
    signup_page.expand_class(class_title)
    signup_page.choose_course(course_title)
    signup_page.confirm_class()
    signup_page.get_set_profile_button().wait_for(timeout=30000)

    with page.expect_response(PROFILE_UPDATE_API) as answer:
        signup_page.skip()
    assert answer.value.status == 200, f"profile/update answered {answer.value.status}"

    signup_page.wait_for_summary()
    return name, course_title


def test_start_learning_hands_the_new_account_over_to_home(page, signup_page):
    """Saving the avatar does not leave the wizard: it creates the account and
    moves on to a summary of it, and Start learning is what leaves. That goes
    to the personalising screen, which carries nothing to press and replaces
    itself with home a couple of seconds later, showing the account just made.
    """
    name, course_title = reach_summary_step(page, signup_page)

    # The step it is reached from: the account as the wizard has just made it.
    expect(page).to_have_url(NEW_USER_URL)
    expect(signup_page.get_summary_name()).to_have_text(name)
    expect(signup_page.get_summary_course_label()).to_have_text("Course")
    expect(signup_page.get_summary_course()).to_have_text(course_title)
    expect(signup_page.get_summary_avatar()).to_be_visible()
    expect(signup_page.get_start_learning_button()).to_be_enabled()

    signup_page.start_learning()

    page.wait_for_url(PersonalisingPage.URL, timeout=15000)
    personalising = PersonalisingPage(page)
    personalising.get_page().wait_for(timeout=5000)
    # Read in one hop: the screen is only up for about two seconds, so a
    # reading per element can end up taken after it has gone.
    showing = personalising.read()

    assert showing["page"], showing
    assert showing["text"] == PersonalisingPage.TEXT, showing
    assert showing["icon"] and showing["bar"] and showing["fill"], showing

    # Nothing is pressed here: the screen hands over on its own.
    page.wait_for_url(HOME_URL, timeout=30000)
    home = HomePage(page)
    expect(home.get_greeting()).to_have_text(f"Hello, {name}", timeout=30000)
    expect(home.get_course_button()).to_have_text(course_title)

    # It replaces itself rather than stacking, so there is no going back to it.
    page.go_back()
    expect(page).not_to_have_url(PersonalisingPage.URL)
