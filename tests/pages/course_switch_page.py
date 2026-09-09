import re

from pages.leaderboard_page import API_BASE, AUTH_TOKEN_KEY, call_api

# The switcher's own calls, as route patterns for expect_response.
#
# The badge opens on a short list of premium courses (premium_courses), and
# View All swaps in the whole catalogue (courses_list). Choosing one posts
# course/update, which is the switch itself; everything the page was showing is
# then refetched for the newly selected course.
COURSE_UPDATE_API = "**/api/v3/course/update"
PREMIUM_COURSES_API = "**/api/v3/premium_courses"
COURSES_LIST_API = "**/api/v3/courses_list"

# Where the app keeps the selected course between renders.
COURSE_ID_KEY = "course_id"
COURSE_NAME_KEY = "course_name"


class CourseSwitchModal:
    """The course switcher, opened from the course badge in the app bar.

    It opens on a "Premium Courses" panel - a short list drawn from
    premium_courses with a View All beneath it - and View All replaces that with
    "All Courses": a search box over every class in the catalogue, collapsed to
    their headers except for the class the current course belongs to, which is
    left open with the current course marked.

    The same modal is reached from Home, Exams, Daily Tasks and Analytics
    (.hp-course-badge) and from Profile (.pp-course), so one object serves all
    five pages.

    Choosing a course reloads the route it was chosen on - twice over on some
    of them - so the modal and everything around it are thrown away rather than
    updated. Anything read after a switch has to wait for the page to come back
    first, and the response body of the switch itself does not survive that.
    """

    def __init__(self, page):
        self.page = page

    # ---------- the modal itself ----------

    def get_overlay(self):
        return self.page.locator(".csm-overlay")

    def get_modal(self):
        return self.page.locator(".csm-modal")

    def is_open(self):
        return self.get_modal().count() > 0

    def wait_for_open(self, timeout=15000):
        self.get_modal().wait_for(timeout=timeout)

    def wait_for_closed(self, timeout=15000):
        self.get_modal().wait_for(state="detached", timeout=timeout)

    def get_close_button(self):
        return self.page.locator(".csm-close")

    def close(self):
        self.get_close_button().click()
        self.wait_for_closed()

    def click_outside(self):
        """Tap the backdrop, which is the other way the modal is dismissed."""
        self.get_overlay().click(position={"x": 5, "y": 5})

    # ---------- the premium panel it opens on ----------

    def get_premium_title(self):
        return self.page.locator(".csm-title-premium")

    def get_premium_courses(self):
        return self.page.locator(".csm-course-item-premium")

    def get_premium_course_names(self):
        return [name.strip() for name in self.get_premium_courses().all_inner_texts()]

    def click_premium_course(self, name):
        self.get_premium_courses().filter(has_text=name).first.click()

    def get_view_all_button(self):
        return self.page.locator(".csm-view-all-btn")

    def open_all_courses(self):
        self.get_view_all_button().click()
        self.get_all_title().wait_for()

    # ---------- the whole catalogue behind View All ----------

    def get_all_title(self):
        return self.page.locator(".csm-title-all")

    def get_search_input(self):
        return self.page.locator(".csm-search-input")

    def search(self, text):
        self.get_search_input().fill(text)

    def get_body(self):
        return self.page.locator(".csm-body-all")

    def get_class_groups(self):
        return self.page.locator(".csm-class-group")

    def get_class_group(self, name):
        return self.get_class_groups().filter(
            has=self.page.locator(".csm-class-header-label").filter(
                has_text=re.compile(r"^\s*" + re.escape(name) + r"\b")
            )
        )

    def get_class_headers(self):
        return self.page.locator(".csm-class-header-label")

    def get_class_names(self):
        """Just the class names; a premium class carries a badge alongside."""
        return [
            text.strip().split("\n")[0]
            for text in self.get_class_headers().all_inner_texts()
        ]

    def toggle_class(self, name):
        self.get_class_group(name).locator(".csm-class-header").click()

    def get_open_classes(self):
        return self.page.locator(".csm-chevron-open")

    def get_courses(self, class_name=None):
        """The course buttons on show. Only an opened class contributes any."""
        if class_name is None:
            return self.page.locator(".csm-course-item-all")
        return self.get_class_group(class_name).locator(".csm-course-item-all")

    def get_course_names(self, class_name=None):
        return [
            text.strip().split("\n")[0]
            for text in self.get_courses(class_name).all_inner_texts()
        ]

    def get_course(self, name):
        """By exact name. A course the account does not own carries a Premium
        chip inside the same button, so that is allowed to follow the name."""
        return self.get_courses().filter(
            has_text=re.compile(r"^\s*" + re.escape(name) + r"\s*(Premium\s*)?$")
        )

    def get_current_course(self):
        return self.page.locator(".csm-course-item-current")

    def get_current_course_name(self):
        return self.get_current_course().inner_text().strip().split("\n")[0]

    def choose(self, name):
        """Pick a course out of the whole catalogue.

        Searched for rather than scrolled to: only the current course's own
        class is left open, so anything else has to be found first."""
        self.search(name)
        course = self.get_course(name).first
        course.wait_for()
        course.click()

    def click_current_course(self):
        self.get_current_course().click()


# ---------------------------------------------------------------------------
# The catalogue and the selected course, read without going through the modal
# ---------------------------------------------------------------------------


def course_catalogue(page):
    """Every course the switcher can offer, as {title: id}.

    Read from courses_list, which is the call View All is built from, so the
    ids here are the ones the switcher posts."""
    return {
        course["title"].strip(): course["id"]
        for grade in call_api(page, "/courses_list")["classes"]
        for course in grade["courses"]
    }


def courses_by_class(page):
    """The same catalogue kept in its classes, as {class title: [course, ...]}."""
    return {
        grade["title"].strip(): [c["title"].strip() for c in grade["courses"]]
        for grade in call_api(page, "/courses_list")["classes"]
    }


def selected_course(page):
    """The course the app is working in, as the app itself holds it.

    Its own copy, not the backend's: it is rewritten when a page that fetches
    the course renders, so between a switch and the next such render it names
    the course before. Good for checking that a switch was taken down, and no
    good as an answer to which course the account is in - ask the profile call
    for that."""
    held = page.evaluate(
        "([id, name]) => ({id: localStorage.getItem(id), name: localStorage.getItem(name)})",
        [COURSE_ID_KEY, COURSE_NAME_KEY],
    )
    # Titles come back padded on the wire and every screen renders them
    # trimmed, so they are trimmed here too and nothing has to remember which
    # side of the app a name came from.
    return {"id": held["id"], "name": (held["name"] or "").strip()}


def set_course(page, course_id):
    """Send the switch the app sends, without the modal.

    The same multipart POST the switcher makes, replayed to put an account back
    the way it was found and to ask the endpoint about ids the modal never
    offers. It answers {"message": ...} either way, so the status is what says
    whether the switch took."""
    return page.evaluate(
        """async ([base, key, path, course]) => {
            const form = new FormData();
            form.append('course', String(course));
            const response = await fetch(base + path, {
                method: 'POST',
                headers: {Authorization: 'Token ' + localStorage.getItem(key)},
                body: form,
            });
            let answered = null;
            try { answered = await response.json(); } catch (error) {}
            return {status: response.status, answered};
        }""",
        [API_BASE, AUTH_TOKEN_KEY, "/course/update", course_id],
    )
