"""Course Switch.

The account works inside one course at a time, and the badge in the app bar is
where that is changed. It is offered on five pages - Home, Exams, Daily Tasks,
Analytics and Profile - and opens the same modal on all five: a short premium
list, and behind View All the whole catalogue, searchable, with the class
holding the current course left open and that course marked.

Choosing one posts course/update with the course id and nothing else; the
backend answers "Syllabus set successfully." and the page refetches whatever it
was showing. Everything the account sees is scoped to the selection - the
subjects and resources on home, the exams, the daily tasks, the ability
tracker's subjects, the course on the profile - so the switch is checked by
what the page carries afterwards, not only by the badge.

Nothing here writes a course name down. Which courses exist on the account
changes with the dev data, so the pair to switch between is taken from
courses_list at run time and a test skips if the account is left with only one.

The account is put back on the course it was found on after every test, in the
same way test_edit_profile.py puts back a name it changed: the rest of the
suite reads this account's subjects, chapters and exams, and all of those are
course-scoped.
"""

import re

import pytest
from playwright.sync_api import expect

from conftest import HOME_URL, STUDENT_MOBILE
from pages.analytics_page import AnalyticsPage
from pages.course_switch_page import (
    COURSE_UPDATE_API,
    COURSES_LIST_API,
    CourseSwitchModal,
    PREMIUM_COURSES_API,
    course_catalogue,
    courses_by_class,
    selected_course,
    set_course,
)
from pages.daily_tasks_page import DailyTasksPage
from pages.exam_page import ExamPage
from pages.home_page import HomePage
from pages.leaderboard_page import call_api
from pages.profile_page import ProfilePage

# The five pages that offer the switcher, keyed by the tail of their route.
PAGES = ["home", "exams", "daily-tasks", "analytics", "profile"]

# What the backend says when the switch takes.
SWITCHED_MESSAGE = "Syllabus set successfully."

# An id no course has, for asking the endpoint what it does with one. The modal
# never offers such a thing, so this is the only way to reach that answer.
MISSING_COURSE_ID = 999999999


@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(STUDENT_MOBILE)


# ---------------------------------------------------------------------------
# Landing on each of the five pages, and reading what it shows for the course
# ---------------------------------------------------------------------------


# The five, as the route to reach each and the object that speaks for it.
ROUTES = {
    "home": HOME_URL,
    "exams": ExamPage.URL,
    "daily-tasks": DailyTasksPage.URL,
    "analytics": AnalyticsPage.URL,
    "profile": ProfilePage.URL,
}

POMS = {
    "home": HomePage,
    "exams": ExamPage,
    "daily-tasks": DailyTasksPage,
    "analytics": AnalyticsPage,
    "profile": ProfilePage,
}

# What each page puts on screen once its own content has arrived. Waited for
# twice over: on the way in, and again after a switch, which reloads the route
# it was made on and draws the page from scratch.
READY = {
    "home": lambda pom: pom.get_subjects().first.wait_for(timeout=30000),
    "exams": lambda pom: pom.wait_for_exams_loaded(),
    "daily-tasks": lambda pom: pom.wait_for_tasks_loaded(),
    "analytics": lambda pom: pom.wait_for_analytics_loaded(),
    "profile": lambda pom: pom.wait_for_loaded(),
}


def wait_ready(pom, name):
    READY[name](pom)


def open_page(page, name):
    """Land on one of the five, loaded far enough that its course-scoped
    content is on screen, and hand back that page's object."""
    page.goto(ROUTES[name], wait_until="domcontentloaded")
    pom = POMS[name](page)
    wait_ready(pom, name)
    return pom


def wait_for_settled(page, quiet=2000, timeout=30000):
    """Wait until the route stops reloading itself.

    A switch reloads the page it was made on, and on some routes it does so more
    than once. A request sent between two of those reloads is dropped by the
    browser rather than answered, so anything read from the page waits for the
    reloading to stop first."""
    navigations = []

    def note(frame):
        if frame == page.main_frame:
            navigations.append(frame.url)

    page.on("framenavigated", note)
    try:
        waited = 0
        while waited < timeout:
            seen = len(navigations)
            page.wait_for_timeout(quiet)
            waited += quiet
            if len(navigations) == seen:
                return
    finally:
        page.remove_listener("framenavigated", note)


def account_course(page):
    """The course the account is in, as the backend has it.

    Asked for rather than read out of the app's own storage: that copy is only
    rewritten when a page that fetches the course renders, so between a switch
    and the next such render it lags behind.

    Trimmed, because titles come back padded on the wire and every screen
    renders them trimmed."""
    return call_api(page, "/profile")["student"]["course_name"].strip()


def course_badge(pom):
    """The control the switcher opens from. Profile carries its own; the other
    four share the badge in the home header."""
    return pom.get_course_button()


def course_label(pom):
    """The course the page says it is working in."""
    if isinstance(pom, ProfilePage):
        return pom.get_course_name().inner_text().strip()
    return pom.get_course_button().inner_text().strip()


def page_content(pom, name):
    """What the page is showing that belongs to the selected course.

    Course-scoped in every case: home is built from the course's subjects and
    resources, the exam tabs from its exams, the day from its tasks, the ability
    tracker from its subjects, and the profile names the course itself."""
    if name == "home":
        return {
            "subjects": pom.get_subject_names(),
            "resources": [t.strip() for t in pom.get_resource_titles().all_inner_texts()],
        }

    if name == "exams":
        pom.click_past_tab()
        return {
            "tabs": {tab: pom.get_tab_count_value(tab) for tab in ("Current", "Upcoming", "Past")},
            "past": [t.strip() for t in pom.get_exam_titles().all_inner_texts()],
        }

    if name == "daily-tasks":
        # Task cards land a moment after the date strip they hang under, and
        # count() does not wait, so give them that moment before counting.
        pom.page.wait_for_timeout(2000)
        return {
            "groups": [t.strip() for t in pom.get_task_group_titles().all_inner_texts()],
            "cards": pom.get_task_cards().count(),
        }

    if name == "analytics":
        return {
            "subjects": [
                pom.get_subject_name(index).inner_text().strip()
                for index in range(pom.subject_count())
            ]
        }

    return {
        "course": pom.get_course_name().inner_text().strip(),
        "api_course": account_course(pom.page),
    }


# ---------------------------------------------------------------------------
# Opening the switcher and choosing out of it
# ---------------------------------------------------------------------------


def open_switcher(pom):
    course_badge(pom).click()
    modal = CourseSwitchModal(pom.page)
    modal.wait_for_open()
    return modal


def switch_from(pom, page_name, course_name):
    """Switch course from whichever page pom is on, and hand the page back once
    it has come up again on the new course.

    The badge is what is waited on rather than the modal closing: choosing a
    course reloads the route it was made on, and the badge survives that while
    the modal does not. What the backend answered is not read here - the reload
    takes the bodies belonging to the page it replaced with it - so a test that
    needs the answer watches the call go past for itself."""
    modal = open_switcher(pom)
    modal.open_all_courses()

    with pom.page.expect_response(COURSE_UPDATE_API) as answer:
        modal.choose(course_name)
    assert answer.value.status == 200, (
        f"the switch to {course_name!r} answered {answer.value.status}"
    )

    expect(course_badge(pom)).to_have_text(course_name, timeout=30000)
    wait_for_settled(pom.page)
    wait_ready(pom, page_name)


def other_courses(page, current_name):
    """Courses the account could switch to, the ones sharing a class with the
    current course first.

    Same class first because those are the courses a student actually moves
    between, and because the modal already has that class open."""
    classes = courses_by_class(page)
    same_class = next(
        (titles for titles in classes.values() if current_name in titles), []
    )
    nearby = [title for title in same_class if title != current_name]
    rest = [
        title
        for titles in classes.values()
        for title in titles
        if title != current_name and title not in nearby
    ]
    return nearby + rest


@pytest.fixture
def catalogue(page):
    return course_catalogue(page)


@pytest.fixture
def target_course(page):
    """The course each test switches to."""
    current = account_course(page)
    options = other_courses(page, current)
    if not options:
        pytest.skip(f"The account is on {current!r} and the catalogue offers nothing else")
    return options[0]


# The course the account was found on, captured the first time a test needs it
# so that a test which fails halfway through a switch cannot make the next one
# restore to the wrong course.
_ORIGINAL = {}


@pytest.fixture(autouse=True)
def restore_course(page):
    """Put the account back on the course it started the run on.

    Sent unconditionally rather than only when the course looks changed: a
    switch that half happened leaves nothing on screen worth trusting, and the
    rest of the suite reads this account's subjects, chapters and exams, which
    are all scoped to the selection."""
    if "course" not in _ORIGINAL:
        # Read once home has rendered, so the app has had the chance to write
        # the course it is in rather than leaving the last one behind.
        HomePage(page).get_subjects().first.wait_for(timeout=30000)
        _ORIGINAL["course"] = selected_course(page)

    yield

    original = _ORIGINAL["course"]

    # A switch reloads the page it was made on, and a request sent into that
    # reload is dropped by the browser rather than answered, so the restore is
    # given a couple of goes.
    answered = None
    for attempt in range(3):
        try:
            answered = set_course(page, original["id"])
            break
        except Exception:
            if attempt == 2:
                raise
            page.wait_for_timeout(3000)

    assert answered["status"] == 200, (
        f"could not put the account back on {original['name']!r}: "
        f"course/update answered {answered['status']}"
    )


# ---------------------------------------------------------------------------
# 1. The switcher is offered, and looks right, on all five pages
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("page_name", PAGES)
def test_the_switcher_is_offered_on_every_page_that_carries_it(page, page_name):
    """The badge is on screen, carries the course the account is in, and opens
    the switcher."""
    pom = open_page(page, page_name)

    expect(course_badge(pom)).to_be_visible()
    assert course_label(pom) == account_course(page)

    modal = open_switcher(pom)
    expect(modal.get_modal()).to_be_visible()
    expect(modal.get_close_button().first).to_be_visible()


@pytest.mark.parametrize("page_name", PAGES)
def test_the_switcher_closes_again_without_changing_the_course(page, page_name):
    """Backing out leaves the account where it was."""
    pom = open_page(page, page_name)
    before = account_course(page)

    modal = open_switcher(pom)
    modal.close()

    assert not modal.is_open()
    assert account_course(page) == before
    assert course_label(pom) == before


def test_the_switcher_also_closes_on_the_backdrop(page):
    modal = open_switcher(open_page(page, "home"))
    modal.click_outside()
    modal.wait_for_closed()
    assert not modal.is_open()


# ---------------------------------------------------------------------------
# 2. The courses it offers  (API + UI)
# ---------------------------------------------------------------------------


def test_it_opens_on_the_premium_courses_the_api_lists(page):
    """The panel the badge opens is premium_courses, name for name."""
    home = open_page(page, "home")

    with page.expect_response(PREMIUM_COURSES_API) as answer:
        modal = open_switcher(home)
    assert answer.value.status == 200

    listed = [c["title"].strip() for c in answer.value.json()["premium_courses"]]

    expect(modal.get_premium_title()).to_have_text("Premium Courses")
    expect(modal.get_view_all_button()).to_be_visible()
    assert modal.get_premium_course_names() == listed


def test_view_all_lists_every_class_the_catalogue_carries(page):
    """Behind View All is courses_list, class for class and in its order."""
    modal = open_switcher(open_page(page, "home"))

    with page.expect_response(COURSES_LIST_API) as answer:
        modal.open_all_courses()
    assert answer.value.status == 200

    listed = [grade["title"].strip() for grade in answer.value.json()["classes"]]

    expect(modal.get_all_title()).to_have_text("All Courses")
    assert modal.get_class_names() == listed


def test_the_class_holding_the_current_course_is_the_one_left_open(page):
    """One class is open when the list appears, and it is the account's own."""
    modal = open_switcher(open_page(page, "home"))
    modal.open_all_courses()

    expect(modal.get_open_classes()).to_have_count(1)
    assert account_course(page) in modal.get_course_names()


def test_the_current_course_is_the_one_marked_in_the_list(page):
    """Exactly one course is marked, and it is the one the badge names."""
    modal = open_switcher(open_page(page, "home"))
    modal.open_all_courses()

    expect(modal.get_current_course()).to_have_count(1)
    assert modal.get_current_course_name() == account_course(page)


def test_an_opened_class_shows_exactly_the_courses_filed_under_it(page):
    """A class opens on its header and offers what courses_list files there."""
    modal = open_switcher(open_page(page, "home"))
    modal.open_all_courses()

    current = account_course(page)
    classes = courses_by_class(page)
    shut = next(
        (name for name, titles in classes.items() if titles and current not in titles),
        None,
    )
    if shut is None:
        pytest.skip("Every class in the catalogue is the account's own or empty")

    assert modal.get_courses(shut).count() == 0, f"{shut} was already open"

    modal.toggle_class(shut)
    assert modal.get_course_names(shut) == classes[shut]

    modal.toggle_class(shut)
    expect(modal.get_courses(shut)).to_have_count(0)


def test_search_narrows_the_list_to_what_matches(page, target_course):
    modal = open_switcher(open_page(page, "home"))
    modal.open_all_courses()

    modal.search(target_course)
    expect(modal.get_course(target_course)).to_have_count(1)
    assert modal.get_course_names() == [target_course]


def test_search_says_so_when_nothing_matches(page):
    modal = open_switcher(open_page(page, "home"))
    modal.open_all_courses()

    modal.search("no course is called this")
    expect(modal.get_class_groups()).to_have_count(0)
    expect(modal.get_body()).to_have_text("No courses found")


def test_the_same_catalogue_is_offered_whichever_page_it_is_opened_from(page):
    """The switcher is one modal, not five, so the list does not depend on where
    it was opened."""
    from_home = open_switcher(open_page(page, "home"))
    from_home.open_all_courses()
    home_classes = from_home.get_class_names()

    from_profile = open_switcher(open_page(page, "profile"))
    from_profile.open_all_courses()

    assert from_profile.get_class_names() == home_classes
    assert from_profile.get_current_course_name() == from_home.get_current_course_name()


# ---------------------------------------------------------------------------
# 3. Switching, from each page, against what that page then shows
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("page_name", PAGES)
def test_switching_course_redraws_the_page_for_the_course_chosen(
    page, page_name, target_course
):
    """The badge follows the choice and the page's own content follows with it,
    with nothing of the previous course left behind.

    Read on the page the switch was made from and nowhere else: choosing a
    course reloads that route, so bringing the new course's content up is part
    of the switch rather than something the next navigation does."""
    pom = open_page(page, page_name)
    before_name = course_label(pom)
    before = page_content(pom, page_name)

    switch_from(pom, page_name, target_course)

    expect(course_badge(pom)).to_have_text(target_course)
    assert course_label(pom) == target_course
    assert selected_course(page)["name"] == target_course

    after = page_content(pom, page_name)
    if after == before:
        # Two things look like this: the courses really do carry the same thing
        # on this page, or the switch left the previous course's content up.
        # Loading the page again tells them apart, because a fresh load can only
        # be showing the course the account is now in.
        assert page_content(open_page(page, page_name), page_name) == after, (
            f"{page_name} went on showing {before_name!r}'s content after the "
            f"switch to {target_course!r}, and only picked the new course up "
            f"when it was loaded again"
        )
        pytest.skip(
            f"{before_name!r} and {target_course!r} show the same thing on "
            f"{page_name}, so there is nothing here to tell apart"
        )


@pytest.mark.parametrize("page_name", PAGES)
def test_switching_course_leaves_the_page_where_it_was(page, page_name):
    """The switch happens where it was made. The route is reloaded, but it is
    the same route - the account is not bounced back to home, which would lose
    whatever they were looking at."""
    pom = open_page(page, page_name)
    where = page.url
    current = account_course(page)
    options = other_courses(page, current)
    if not options:
        pytest.skip(f"The account is on {current!r} and the catalogue offers nothing else")

    switch_from(pom, page_name, options[0])

    assert page.url == where


def test_switching_back_returns_the_page_to_the_first_courses_content(
    page, target_course
):
    """The other direction works too, and puts back exactly what was there."""
    home = open_page(page, "home")
    original = course_label(home)
    before = page_content(home, "home")

    switch_from(home, "home", target_course)
    expect(home.get_course_button()).to_have_text(target_course)

    switch_from(home, "home", original)
    expect(home.get_course_button()).to_have_text(original)
    assert page_content(home, "home") == before


def test_switching_through_several_courses_ends_on_the_last_one_chosen(page):
    """Three courses in a row, each one taking over from the one before."""
    home = open_page(page, "home")
    current = course_label(home)
    options = other_courses(page, account_course(page))
    if len(options) < 2:
        pytest.skip(f"The account is on {current!r} with fewer than two others to visit")

    for course in options[:2] + [current]:
        switch_from(home, "home", course)
        expect(home.get_course_button()).to_have_text(course)
        assert selected_course(page)["name"] == course

    assert course_label(home) == current


def test_choosing_the_course_already_selected_leaves_everything_as_it_was(page):
    """Picking the marked course is allowed, and is a switch to where the
    account already is: the modal closes and nothing on the page moves."""
    home = open_page(page, "home")
    before = page_content(home, "home")
    current = course_label(home)

    modal = open_switcher(home)
    modal.open_all_courses()
    with page.expect_response(COURSE_UPDATE_API) as answer:
        modal.click_current_course()
    expect(home.get_course_button()).to_have_text(current, timeout=30000)
    wait_for_settled(page)
    wait_ready(home, "home")

    assert answer.value.status == 200
    assert course_label(home) == current
    assert selected_course(page)["name"] == current
    assert page_content(home, "home") == before


def test_a_premium_course_the_account_does_not_own_switches_like_any_other(page):
    """The premium panel is a list of courses the account has not bought, and
    choosing one out of it switches straight into it - there is no purchase or
    paywall in the way. Written to what the app does today, so it will fail if
    a gate is ever put in front of it."""
    home = open_page(page, "home")
    modal = open_switcher(home)

    offered = modal.get_premium_course_names()
    if not offered:
        pytest.skip("The account is offered no premium course to try this on")
    premium = offered[0]

    with page.expect_response(COURSE_UPDATE_API) as answer:
        modal.click_premium_course(premium)
    expect(home.get_course_button()).to_have_text(premium, timeout=30000)
    wait_for_settled(page)
    wait_ready(home, "home")

    assert answer.value.status == 200
    assert selected_course(page)["name"] == premium


# ---------------------------------------------------------------------------
# 4. The switch call itself  (API + UI)
# ---------------------------------------------------------------------------


def test_the_switch_posts_the_id_of_the_course_that_was_chosen(
    page, catalogue, target_course
):
    """course/update carries the chosen course's id from the catalogue, and
    answers that the syllabus was set.

    Read off a copy of the exchange taken as it passes rather than off the
    response afterwards: the switch reloads the page, and the browser lets go of
    the bodies belonging to the page it replaced. The call still goes to the
    backend and the app is still handed the backend's own answer."""
    home = open_page(page, "home")
    exchange = {}

    def relay(route):
        answered = route.fetch()
        exchange["posted"] = route.request.post_data
        exchange["status"] = answered.status
        exchange["body"] = answered.json()
        route.fulfill(response=answered)

    page.route(COURSE_UPDATE_API, relay)
    try:
        switch_from(home, "home", target_course)
    finally:
        page.unroute(COURSE_UPDATE_API)

    assert exchange["status"] == 200
    assert exchange["body"]["message"] == SWITCHED_MESSAGE

    sent = re.search(r'name="course"\s+([^\s-]+)', exchange["posted"])
    assert sent, f"the switch posted no course field: {exchange['posted']!r}"
    assert sent.group(1) == str(catalogue[target_course]), (
        f"the switch to {target_course!r} carried {sent.group(1)} rather than "
        f"its catalogue id {catalogue[target_course]}"
    )


def test_the_course_on_screen_after_a_switch_is_the_one_the_api_reports(
    page, target_course
):
    """The badge is not taken on trust: the profile call is asked what course
    the account is in, and the two have to agree."""
    home = open_page(page, "home")
    switch_from(home, "home", target_course)

    expect(home.get_course_button()).to_have_text(target_course)
    assert account_course(page) == target_course


def test_the_home_payload_after_a_switch_belongs_to_the_new_course(
    page, target_course
):
    """Home is rebuilt from a fresh home call, and what that call carries is
    what the page shows - the new course's name and its subjects."""
    home = open_page(page, "home")

    modal = open_switcher(home)
    modal.open_all_courses()
    with page.expect_response("**/api/v3/home") as answer:
        modal.choose(target_course)
    expect(home.get_course_button()).to_have_text(target_course, timeout=30000)
    wait_for_settled(page)
    wait_ready(home, "home")

    body = answer.value.json()
    assert body["user"]["course_name"].strip() == target_course
    assert home.get_subject_names() == [s["title"].strip() for s in body["subjects"]]


def test_every_page_reports_the_new_course_after_a_single_switch(page, target_course):
    """One switch, made once on home, and then all five pages asked. The
    selection belongs to the account, not to the page it was made on."""
    switch_from(open_page(page, "home"), "home", target_course)

    for page_name in PAGES:
        pom = open_page(page, page_name)
        assert course_label(pom) == target_course, f"{page_name} still names another course"


def test_the_backend_refuses_a_course_that_does_not_exist(page):
    """The modal only ever offers real courses, so this is asked of the endpoint
    directly: an id no course has is turned down and the account is left where
    it was."""
    before = account_course(page)

    answered = set_course(page, MISSING_COURSE_ID)

    assert answered["status"] == 404
    assert "does not exist" in answered["answered"]["message"]
    assert account_course(page) == before


def test_the_backend_refuses_a_switch_with_no_course_at_all(page):
    """The other half of the same guard: nothing sent, nothing changed."""
    before = account_course(page)

    answered = set_course(page, "")

    assert answered["status"] == 400
    assert "Missing course ID" in answered["answered"]["message"]
    assert account_course(page) == before


# ---------------------------------------------------------------------------
# 5. The selection sticks
# ---------------------------------------------------------------------------


def test_the_chosen_course_survives_a_reload(page, target_course):
    home = open_page(page, "home")
    switch_from(home, "home", target_course)

    page.reload(wait_until="domcontentloaded")
    wait_ready(home, "home")

    assert course_label(home) == target_course
    assert selected_course(page)["name"] == target_course


def test_the_chosen_course_survives_a_fresh_session_on_the_same_account(
    browser, page, target_course
):
    """Opened again from scratch - a new context carrying only the sign in - the
    account is still in the course it was moved to, so the choice is held by the
    backend and not just by this tab."""
    switch_from(open_page(page, "home"), "home", target_course)

    reopened = browser.new_context(storage_state=page.context.storage_state())
    try:
        fresh = reopened.new_page()
        fresh.goto(HOME_URL, wait_until="domcontentloaded")
        home = HomePage(fresh)
        home.get_subjects().first.wait_for(timeout=30000)

        expect(home.get_course_button()).to_have_text(target_course)
        assert account_course(fresh) == target_course
    finally:
        reopened.close()


# ---------------------------------------------------------------------------
# 6. When the switch cannot be made
# ---------------------------------------------------------------------------


def test_a_switch_that_never_reaches_the_backend_leaves_the_course_alone(
    page, target_course
):
    """Network gone. The course is unchanged and the page still shows the
    course's own content, rather than half of the one that was asked for."""
    home = open_page(page, "home")
    before_name = course_label(home)
    before = page_content(home, "home")

    page.route(COURSE_UPDATE_API, lambda route: route.abort())
    modal = open_switcher(home)
    modal.open_all_courses()
    modal.choose(target_course)
    page.wait_for_timeout(4000)
    page.unroute(COURSE_UPDATE_API)

    assert course_label(home) == before_name
    assert account_course(page) == before_name
    assert page_content(home, "home") == before


def test_a_switch_the_backend_rejects_leaves_the_course_alone(page, target_course):
    """Same again with the call answered rather than dropped: a 500 must not
    move the account."""
    home = open_page(page, "home")
    before_name = course_label(home)

    page.route(
        COURSE_UPDATE_API,
        lambda route: route.fulfill(status=500, json={"message": "server error"}),
    )
    modal = open_switcher(home)
    modal.open_all_courses()
    modal.choose(target_course)
    page.wait_for_timeout(4000)
    page.unroute(COURSE_UPDATE_API)

    assert course_label(home) == before_name
    assert account_course(page) == before_name


def test_the_switcher_stays_open_after_a_failed_switch_so_it_can_be_tried_again(
    page, target_course
):
    """The modal is not dismissed by a failure, which is what makes a retry
    possible: the same course is chosen a second time with the network back and
    the switch goes through.

    Staying open is all the account is told, though. Nothing names the failure -
    no message, no toast - so a switch that silently did nothing looks the same
    as one that was never tapped."""
    home = open_page(page, "home")
    before_name = course_label(home)

    page.route(COURSE_UPDATE_API, lambda route: route.abort())
    modal = open_switcher(home)
    modal.open_all_courses()
    modal.choose(target_course)
    page.wait_for_timeout(4000)

    assert modal.is_open(), "the switcher closed on a failed switch, with nothing switched"
    assert course_label(home) == before_name

    page.unroute(COURSE_UPDATE_API)
    with page.expect_response(COURSE_UPDATE_API) as answer:
        modal.choose(target_course)
    expect(home.get_course_button()).to_have_text(target_course, timeout=30000)
    wait_for_settled(page)
    wait_ready(home, "home")

    assert answer.value.status == 200
