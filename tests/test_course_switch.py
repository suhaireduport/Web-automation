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
from datetime import datetime

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
    premium_courses,
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

# The call each page is built from. A page showing the right course name while
# being built from the previous course's payload is the thing these are here to
# catch, so every page is checked against its own call and not against the badge.
HOME_API = "**/api/v3/home"
EXAMS_API = "**/api/v3/exams/all"
TASKS_API = "**/api/v3/dailytasks/list"
ABILITY_API = "**/api/v3/analytics/ability/list"

# The four lists a day's tasks are split into in the daily tasks payload.
TASK_KINDS = ("study_tasks", "practice_tasks", "revision_tasks", "exam_tasks")


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
# Holding each page against the course it is supposed to be showing
#
# A page can put the newly chosen course in its header while it is still built
# from the previous course's payload, so a badge that reads correctly proves
# nothing on its own. Each page below is opened with its own call listened for,
# the payload is shown to belong to the chosen course, and only then is the
# screen held against that payload.
#
# What makes a payload the course's own, page by page:
#   home         user.course_name is the course
#   exams        every exam is filed under the course by name
#   daily tasks  every exam a task points at is one of the course's own exams
#   analytics    every subject the ability tracker scores is one of the
#                course's subjects
#   profile      course_id is the id the switch posted
#
# Each returns a fingerprint of what it was served, so one course's can be held
# against another's.
# ---------------------------------------------------------------------------


def course_ref(catalogue, title):
    """A course as the switcher deals in it: the title that shows on screen and
    the id the switch posts."""
    assert title in catalogue, f"{title!r} is not a course the catalogue offers"
    return {"title": title, "id": catalogue[title]}


def verify_home(page, course):
    with page.expect_response(HOME_API) as answer:
        page.goto(HOME_URL, wait_until="domcontentloaded")
    assert answer.value.status == 200
    body = answer.value.json()

    served = body["user"]["course_name"].strip()
    assert served == course["title"], (
        f"home was built from {served!r} after the switch to {course['title']!r}"
    )

    home = HomePage(page)
    wait_ready(home, "home")
    assert home.get_subject_names() == [s["title"].strip() for s in body["subjects"]]
    assert course_label(home) == course["title"]

    return {
        "subject_ids": {s["id"] for s in body["subjects"]},
        "resources": [r["title"].strip() for r in body["resources"]],
        "subscription_status": body["subscription_status"],
    }


def verify_exams(page, course):
    with page.expect_response(EXAMS_API) as answer:
        page.goto(ExamPage.URL, wait_until="domcontentloaded")
    assert answer.value.status == 200
    listed = answer.value.json()["exams"]

    filed_under = {(exam.get("subject") or "").strip() for exam in listed}
    assert filed_under <= {course["title"]}, (
        f"exams/all came back carrying exams filed under "
        f"{sorted(filed_under - {course['title']})} after the switch to "
        f"{course['title']!r}"
    )

    exams = ExamPage(page)
    wait_ready(exams, "exams")
    counted = sum(exams.get_tab_count_value(tab) for tab in ("Current", "Upcoming", "Past"))
    assert counted == len(listed), (
        f"the tabs count {counted} exams and exams/all served {len(listed)}"
    )
    assert course_label(exams) == course["title"]

    return {"exam_ids": {exam["id"] for exam in listed}}


def selected_day(tasks):
    """The date the tasks list is showing, spelled the way the payload spells
    it. The strip carries the day number and the header the month and year."""
    day = re.search(r"\d+", tasks.get_selected_date().inner_text()).group()
    month_year = tasks.get_month_year().inner_text().strip()
    return datetime.strptime(f"{day} {month_year}", "%d %B %Y").strftime("%Y-%m-%d")


def verify_daily_tasks(page, course, course_exam_ids):
    with page.expect_response(TASKS_API) as answer:
        page.goto(DailyTasksPage.URL, wait_until="domcontentloaded")
    assert answer.value.status == 200
    body = answer.value.json()

    pointed_at = {
        task["exam_id"] for day in body["results"] for task in day["exam_tasks"]
    }
    assert pointed_at <= course_exam_ids, (
        f"the tasks point at exams {sorted(pointed_at - course_exam_ids)}, which "
        f"are not among {course['title']!r}'s own"
    )

    tasks = DailyTasksPage(page)
    wait_ready(tasks, "daily-tasks")
    # Task cards land a moment after the strip they hang under, and count()
    # does not wait, so give them that moment.
    page.wait_for_timeout(2000)

    showing = selected_day(tasks)
    listed = next((day for day in body["results"] if day["date"] == showing), None)
    expected = 0 if listed is None else sum(len(listed[kind]) for kind in TASK_KINDS)
    assert tasks.get_task_cards().count() == expected, (
        f"the payload puts {expected} tasks on {showing} and the page shows "
        f"{tasks.get_task_cards().count()}"
    )
    assert course_label(tasks) == course["title"]

    return {
        "days": {day["date"]: sum(len(day[k]) for k in TASK_KINDS) for day in body["results"]},
        "exams_pointed_at": pointed_at,
        "is_premium": body["is_premium"],
    }


def verify_analytics(page, course, course_subject_ids):
    with page.expect_response(ABILITY_API) as answer:
        page.goto(AnalyticsPage.URL, wait_until="domcontentloaded")
    assert answer.value.status == 200
    scored = answer.value.json()["subjects"]

    ids = {subject["id"] for subject in scored}
    assert ids <= course_subject_ids, (
        f"the ability tracker scores subjects {sorted(ids - course_subject_ids)}, "
        f"which are not {course['title']!r}'s"
    )

    analytics = AnalyticsPage(page)
    wait_ready(analytics, "analytics")
    shown = [
        analytics.get_subject_name(index).inner_text().strip()
        for index in range(analytics.subject_count())
    ]
    assert shown == [subject["title"].strip() for subject in scored]
    assert course_label(analytics) == course["title"]

    return {"subject_ids": ids}


def verify_profile(page, course):
    """The profile page does not call profile; it is drawn from the home call it
    makes on load, so that is the payload it is held against. The profile call
    is then asked separately for the course id, which is the one thing that
    names the course beyond doubt."""
    with page.expect_response(HOME_API) as answer:
        page.goto(ProfilePage.URL, wait_until="domcontentloaded")
    assert answer.value.json()["user"]["course_name"].strip() == course["title"]

    profile = ProfilePage(page)
    wait_ready(profile, "profile")
    assert course_label(profile) == course["title"]

    student = call_api(page, "/profile")["student"]
    assert student["course_id"] == course["id"], (
        f"the account is on course {student['course_id']} and "
        f"{course['title']!r} is {course['id']}"
    )
    assert student["course_name"].strip() == course["title"]

    return {"course_id": student["course_id"]}


def verify_all_pages_on(page, course):
    """Walk all five pages and hold each against `course`, payload first and
    then screen against payload.

    Walked in this order because two of the checks are built out of an earlier
    one: the day's tasks are held against the course's own exams, and the
    ability tracker against the course's own subjects."""
    facts = {}
    facts["home"] = verify_home(page, course)
    facts["exams"] = verify_exams(page, course)
    facts["daily-tasks"] = verify_daily_tasks(page, course, facts["exams"]["exam_ids"])
    facts["analytics"] = verify_analytics(page, course, facts["home"]["subject_ids"])
    facts["profile"] = verify_profile(page, course)
    return facts


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


# ---------------------------------------------------------------------------
# 4b. Every page against the course that was chosen  (API + UI)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("origin", PAGES)
def test_every_page_serves_the_new_courses_data_after_a_switch_from(
    page, origin, catalogue, target_course
):
    """Switch on one page, then walk all five and hold each against the course
    that was chosen - the page's own call first, and the screen against that
    call afterwards.

    Made from a different page each time round because the page the switch is
    made on is the one that reloads itself. The other four pick the course up
    whenever they are next opened, and that is the half where a page can come
    back wearing the new course while being built from the old one's data."""
    chosen = course_ref(catalogue, target_course)

    switch_from(open_page(page, origin), origin, chosen["title"])

    verify_all_pages_on(page, chosen)


def test_no_page_is_left_serving_the_previous_courses_data(
    page, catalogue, target_course
):
    """Every page's payload taken twice, once in each course, and held apart.

    The test above rules stale data out from one side: a payload has to belong
    to the course now chosen. This one says it from the other side - what the
    pages served for the first course is not what they serve for the second.

    Home and profile have to differ, because each of them names the course it
    was built for. The other three are allowed to coincide: two courses can
    genuinely carry the same exams or the same empty week, and their payloads
    have already been shown to be the new course's own."""
    before = course_ref(catalogue, account_course(page))
    after = course_ref(catalogue, target_course)

    was = verify_all_pages_on(page, before)
    switch_from(open_page(page, "home"), "home", after["title"])
    now = verify_all_pages_on(page, after)

    assert was["home"] != now["home"], "home served both courses the same thing"
    assert was["profile"] != now["profile"], "profile served both courses the same thing"
    assert now["profile"]["course_id"] == after["id"]


# ---------------------------------------------------------------------------
# 4c. What the endpoint refuses
# ---------------------------------------------------------------------------


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

    # Not just the badge: home is asked what it is built from, so a screen that
    # quietly moved on while the switch was refused would be caught.
    with page.expect_response(HOME_API) as served:
        page.goto(HOME_URL, wait_until="domcontentloaded")
    assert served.value.json()["user"]["course_name"].strip() == before_name


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


# ---------------------------------------------------------------------------
# 7. Premium courses
#
# premium_courses is the list the switcher opens on and the same list it draws
# its Premium chips from, so it is what a chip has to be held against. Being
# premium also shows in the data: an account sitting in a premium course is
# served subscription_status true and its day's tasks come back flagged.
# ---------------------------------------------------------------------------

# How many ordinary courses to check for a chip they should not have. The
# catalogue runs to hundreds and they are all the same check.
ORDINARY_SAMPLE = 8


@pytest.fixture
def premium(page):
    """The premium courses the catalogue names, as {title: id}."""
    return premium_courses(page)


def premium_standing(page):
    """What the backend says about the account's standing in the course it is
    currently in."""
    return {
        "subscription_status": call_api(page, "/home")["subscription_status"],
        "is_premium": call_api(page, "/dailytasks/list")["is_premium"],
    }


def test_every_premium_course_is_badged_premium_in_the_full_list(page, premium):
    """The chip is not decoration - a course wears it when premium_courses
    names it."""
    if not premium:
        pytest.skip("The catalogue names no premium course")

    modal = open_switcher(open_page(page, "home"))
    modal.open_all_courses()

    for title in premium:
        modal.search(title)
        assert modal.is_badged_premium(title), (
            f"the premium call names {title!r} and its row carries no Premium chip"
        )


def test_a_course_the_premium_call_does_not_name_is_not_badged_premium(
    page, premium, catalogue
):
    """And the other way round, so a chip on everything would not pass."""
    ordinary = [title for title in catalogue if title not in premium]
    if not ordinary:
        pytest.skip("Every course in the catalogue is premium")

    modal = open_switcher(open_page(page, "home"))
    modal.open_all_courses()

    for title in ordinary[:ORDINARY_SAMPLE]:
        modal.search(title)
        assert not modal.is_badged_premium(title), (
            f"the premium call does not name {title!r} and its row wears a "
            f"Premium chip anyway"
        )


def test_a_class_is_badged_premium_exactly_when_it_holds_a_premium_course(
    page, premium
):
    """The badge on a class header follows the courses filed under it, for
    every class in the list and not just the ones that carry it."""
    modal = open_switcher(open_page(page, "home"))
    modal.open_all_courses()

    for class_name, titles in courses_by_class(page).items():
        holds_premium = any(title in premium for title in titles)
        assert modal.is_class_badged_premium(class_name) == holds_premium, (
            f"{class_name!r} "
            f"{'holds a premium course and is not badged' if holds_premium else 'holds none and is badged'}"
        )


def test_switching_between_two_premium_courses_carries_every_page_over(
    page, catalogue, premium
):
    """Premium to premium, which is the move a paying account actually makes.

    Both courses are premium, so what changes is the course's own content
    rather than the account's standing: every page comes back built from the
    second course, and the subscription is still on at the end of it."""
    if len(premium) < 2:
        pytest.skip(
            f"The catalogue names {len(premium)} premium course(s) and this needs two"
        )

    first, second = (course_ref(catalogue, title) for title in list(premium)[:2])

    home = open_page(page, "home")
    if course_label(home) != first["title"]:
        switch_from(home, "home", first["title"])
    was = verify_all_pages_on(page, first)

    switch_from(open_page(page, "home"), "home", second["title"])
    now = verify_all_pages_on(page, second)

    assert now["profile"]["course_id"] == second["id"]
    assert was["home"] != now["home"], "both premium courses served the same home"
    assert was["home"]["subscription_status"] is True
    assert now["home"]["subscription_status"] is True
    assert now["daily-tasks"]["is_premium"] is True


def test_a_premium_course_and_an_ordinary_one_are_served_different_standing(
    page, catalogue, premium
):
    """Being premium reaches the data and not only the chip: the same account
    is subscribed in a premium course and is not in an ordinary one."""
    if not premium:
        pytest.skip("The catalogue names no premium course")
    ordinary = [title for title in catalogue if title not in premium]
    if not ordinary:
        pytest.skip("Every course in the catalogue is premium")

    home = open_page(page, "home")

    switch_from(home, "home", list(premium)[0])
    assert premium_standing(page) == {"subscription_status": True, "is_premium": True}

    switch_from(open_page(page, "home"), "home", ordinary[0])
    assert premium_standing(page) == {"subscription_status": False, "is_premium": False}
