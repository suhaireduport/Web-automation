"""Resources: the folders on the home row, and what opening one gives.

The row of resource buttons under Subjects on home is the entry. Each button is
a folder the course carries, and the home call answers the row: id, title and
resource_type per folder. Opening one routes to
/home/resources/<id>/<title>/<type> and the screen there is drawn from one call
of its own, resources/child-resources?resource_id=<id>.

That call answers in one of two shapes, and which one says what kind of folder
it is:

  resource_type 1  filed under the course's subjects. One entry per subject -
                   subject_id, syllabus_title and the sections beneath it - and
                   the screen carries a subject strip above the section tabs.
  resource_type 2  a flat set of sections, answered as the sections
                   themselves, with no subject strip on the screen.

Under either, a section holds contents, and a content is a file or a video. A
file opens in a browser tab of its own; a video routes on to a player screen
whose path carries the folder, the section and the content it is showing.

Nothing here writes a folder, subject or title down. Which resources a course
carries changes with the course, and the course on this account changes on its
own, so every folder is taken from the home call at run time and a test stands
down naming what it found when the course has nothing of the kind it needs.

What is deliberately not here: the resource row on home - that it is drawn from
the home call, and what the three fixed shortcuts beside it are - stays in
test_home.py. What is here is the folders themselves.
"""
import re

import pytest
from playwright.sync_api import expect

from conftest import STUDENT_MOBILE
from pages.home_page import HomePage
from pages.question_library_section_page import normalise
from pages.resources_page import (
    CHILD_RESOURCES_API,
    OPENS_FILE,
    OPENS_LOCKED,
    OPENS_VIDEO,
    PLAIN_FOLDER,
    ResourceSearchPage,
    ResourceVideoPage,
    ResourcesPage,
    SUBJECT_FOLDER,
    child_resources,
    contents_in,
    is_filed_under_subjects,
    opens_as,
    resource_folders,
    route_to,
    search_matches,
    search_route,
    searchable_items,
    sections_in,
    subjects_in,
    videos_in,
)

@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(STUDENT_MOBILE)


@pytest.fixture
def folders(page):
    """The folders the course carries. Nothing to test without at least one."""
    carried = resource_folders(page)
    if not carried:
        pytest.skip("This course carries no resources at all")
    return carried


def a_folder_with_content(page, folders, kind=None):
    """The first folder that has something in it, of a given kind if asked.

    Hands back the folder and what its own call answered, or a string saying
    what was looked at when nothing suitable turned up."""
    looked_at = []
    for folder in folders:
        if kind is not None and folder["resource_type"] != kind:
            continue
        body = child_resources(page, folder)
        if any(contents_in(section) for section in sections_in(body)):
            return folder, body
        looked_at.append(folder["title"].strip())

    named = {SUBJECT_FOLDER: "filed under subjects", PLAIN_FOLDER: "of sections"}
    what = f" {named[kind]}" if kind in named else ""
    return (
        f"No folder{what} on this course holds anything: "
        f"{looked_at or 'the course carries none of that kind'}"
    )


@pytest.fixture
def filled_folder(page, folders):
    """A folder with items in it, whichever kind the course happens to fill."""
    found = a_folder_with_content(page, folders)
    if isinstance(found, str):
        pytest.skip(found)
    return found


@pytest.fixture
def subject_folder(page, folders):
    found = a_folder_with_content(page, folders, kind=SUBJECT_FOLDER)
    if isinstance(found, str):
        pytest.skip(found)
    return found


@pytest.fixture
def plain_folder(page, folders):
    found = a_folder_with_content(page, folders, kind=PLAIN_FOLDER)
    if isinstance(found, str):
        pytest.skip(found)
    return found


@pytest.fixture
def video_content(page, folders):
    """A folder holding a video, the section it sits in and the video itself."""
    for folder in folders:
        body = child_resources(page, folder)
        found = videos_in(body)
        if found:
            subject, section, content = found[0]
            return folder, body, subject, section, content
    pytest.skip(
        "No folder on this course holds a video: "
        f"{[f['title'].strip() for f in folders]}"
    )


def open_folder(page, folder):
    resources = ResourcesPage(page)
    resources.open(folder)
    return resources


# ---------------------------------------------------------------------------
# 1. Opening a folder
# ---------------------------------------------------------------------------

def test_a_folder_opens_from_the_home_row_on_its_own_route(page, folders):
    """Tapping a folder lands on the route built from what the home call said
    it was: its id, its title and how it is arranged."""
    home = HomePage(page)
    home.get_subjects().first.wait_for(timeout=30000)
    folder = folders[0]

    home.get_resources().filter(has_text=normalise(folder["title"])).first.click()

    expect(page).to_have_url(route_to(folder))
    ResourcesPage(page).wait_for_loaded()


def test_the_folder_names_itself_in_its_header(page, filled_folder):
    folder, _ = filled_folder
    resources = open_folder(page, folder)

    expect(resources.get_page()).to_be_visible()
    expect(resources.get_title()).to_have_text(normalise(folder["title"]))
    expect(resources.get_back_button()).to_be_visible()


def test_a_folder_the_course_has_filled_nothing_into_says_so(page, folders):
    """An empty folder draws a line saying there is nothing rather than an
    empty grid of tiles."""
    empty = None
    for folder in folders:
        body = child_resources(page, folder)
        if not any(contents_in(section) for section in sections_in(body)):
            empty = folder
            break
    if empty is None:
        pytest.skip("Every folder on this course holds something")

    resources = open_folder(page, empty)

    assert resources.is_empty()
    expect(resources.get_empty_label()).not_to_be_empty()
    expect(resources.get_tiles()).to_have_count(0)


def test_going_back_leaves_the_folder(page, filled_folder):
    folder, _ = filled_folder
    resources = open_folder(page, folder)

    resources.click_back()

    expect(page).not_to_have_url(route_to(folder))


# ---------------------------------------------------------------------------
# 2. The folder against its own call  (API + UI)
# ---------------------------------------------------------------------------

def test_the_folder_is_drawn_from_the_call_it_makes_on_opening(page, filled_folder):
    """The screen is not taken on trust: the call is listened for as the folder
    opens and the tabs and tiles are held against what it answered."""
    folder, _ = filled_folder
    resources = ResourcesPage(page)

    with page.expect_response(CHILD_RESOURCES_API) as answer:
        page.goto(route_to(folder), wait_until="domcontentloaded")
    assert answer.value.status == 200
    body = answer.value.json()
    resources.wait_for_loaded()

    assert str(folder["id"]) in answer.value.url, (
        f"the folder asked for {answer.value.url}, which is not {folder['id']}"
    )

    # A section the call answers with no contents is not drawn as a tab at all,
    # so the tabs are held against the sections that have something in them.
    displayed = [section for section in sections_in(body) if contents_in(section)]
    assert displayed, (
        f"{folder['title'].strip()!r} answered no section with anything in it"
    )
    assert resources.get_section_names() == [
        normalise(section["title"]) for section in displayed
    ]
    assert resources.get_active_section_name() == normalise(displayed[0]["title"])

def test_the_tiles_are_the_contents_the_call_answered_for_the_open_section(
    page, filled_folder
):
    """One tile per content, titled as the call titled it and in its order."""
    folder, body = filled_folder
    resources = open_folder(page, folder)

    section = next(s for s in sections_in(body) if contents_in(s))
    if normalise(section["title"]) != resources.get_active_section_name():
        resources.click_section(normalise(section["title"]))

    expected = [normalise(content["title"]) for content in contents_in(section)]
    expect(resources.get_tiles()).to_have_count(len(expected))
    assert resources.get_tile_titles() == expected


def test_every_tile_carries_an_icon(page, filled_folder):
    """The icon is what tells a file from a video at a glance, so every tile
    has one."""
    folder, _ = filled_folder
    resources = open_folder(page, folder)

    expect(resources.get_tile_icons()).to_have_count(resources.get_tiles().count())


def test_moving_between_sections_swaps_the_tiles_for_that_sections_contents(
    page, filled_folder
):
    """Each tab is its own set of items, and the call said which."""
    folder, body = filled_folder
    filled = [s for s in sections_in(body) if contents_in(s)]
    if len(filled) < 2:
        pytest.skip(f"{folder['title'].strip()!r} has only one section with anything in it")

    resources = open_folder(page, folder)
    for section in filled[:2]:
        resources.click_section(normalise(section["title"]))
        assert resources.get_active_section_name() == normalise(section["title"])
        assert resources.get_tile_titles() == [
            normalise(content["title"]) for content in contents_in(section)
        ]


# ---------------------------------------------------------------------------
# 3. Resources filed under a subject
# ---------------------------------------------------------------------------

def test_a_subject_folder_offers_the_subjects_the_call_files_it_under(
    page, subject_folder
):
    """The strip above the tabs is the course's subjects, as the folder's own
    call names them, with one of them picked to start."""
    folder, body = subject_folder
    assert is_filed_under_subjects(body), (
        f"{folder['title'].strip()!r} is a subject folder but did not answer in "
        f"that shape"
    )

    resources = open_folder(page, folder)
    named = subjects_in(body)

    assert resources.get_subject_names() == named
    assert resources.get_active_subject_name() == named[0]


def test_a_subject_folders_items_are_the_ones_filed_under_the_chosen_subject(
    page, subject_folder
):
    """The tiles belong to the subject on show and to the section under it, and
    the call says which those are."""
    folder, body = subject_folder
    resources = open_folder(page, folder)

    for index, subject in enumerate(subjects_in(body)):
        sections = sections_in(body, index)
        if not any(contents_in(section) for section in sections):
            continue

        resources.click_subject(subject)
        assert resources.get_active_subject_name() == subject
        assert resources.get_section_names() == [
            normalise(section["title"]) for section in sections
        ]

        section = next(s for s in sections if contents_in(s))
        resources.click_section(normalise(section["title"]))
        assert resources.get_tile_titles() == [
            normalise(content["title"]) for content in contents_in(section)
        ]
        return

    pytest.skip(f"No subject in {folder['title'].strip()!r} has anything filed under it")


def test_a_subject_folder_keeps_its_subjects_apart(page, subject_folder):
    """Choosing a subject shows that subject's items and not the one before's,
    where the two differ."""
    folder, body = subject_folder
    named = subjects_in(body)
    if len(named) < 2:
        pytest.skip(f"{folder['title'].strip()!r} is filed under one subject only")

    resources = open_folder(page, folder)
    resources.click_subject(named[0])
    first = resources.get_tile_titles()

    resources.click_subject(named[1])
    second = resources.get_tile_titles()

    expected_first = [
        normalise(c["title"]) for s in sections_in(body, 0) for c in contents_in(s)
    ]
    expected_second = [
        normalise(c["title"]) for s in sections_in(body, 1) for c in contents_in(s)
    ]
    if expected_first == expected_second:
        pytest.skip(f"{named[0]!r} and {named[1]!r} hold the same items")

    assert first != second, "the tiles did not change with the subject"
    assert set(second) <= set(expected_second), (
        f"{named[1]!r} is showing items that are not filed under it"
    )


# ---------------------------------------------------------------------------
# 4. Resources not filed under a subject
# ---------------------------------------------------------------------------

def test_a_plain_folder_has_no_subject_strip(page, plain_folder):
    """A folder of sections is not filed under anything, so the screen offers
    the sections alone."""
    folder, body = plain_folder
    assert not is_filed_under_subjects(body)
    assert subjects_in(body) == []

    resources = open_folder(page, folder)

    # Only a section with something in it is drawn as a tab.
    displayed = [section for section in sections_in(body) if contents_in(section)]
    expect(resources.get_subjects()).to_have_count(0)
    expect(resources.get_sections()).to_have_count(len(displayed))


def test_a_plain_folders_items_are_the_contents_of_its_sections(page, plain_folder):
    """Its tiles come from the section on show, the same as a subject folder's
    do, only without a subject in the way."""
    folder, body = plain_folder
    resources = open_folder(page, folder)

    section = next(s for s in sections_in(body) if contents_in(s))
    resources.click_section(normalise(section["title"]))

    assert resources.get_tile_titles() == [
        normalise(content["title"]) for content in contents_in(section)
    ]


def test_a_file_opens_in_a_tab_of_its_own_and_leaves_the_folder_alone(
    page, plain_folder
):
    """A file is handed to the browser rather than drawn in the app, so the
    folder is still there behind it."""
    folder, body = plain_folder
    section = next(
        (
            s
            for s in sections_in(body)
            if any(not c.get("stream_link") and c.get("file") for c in contents_in(s))
        ),
        None,
    )
    if section is None:
        pytest.skip(f"{folder['title'].strip()!r} holds no file to open")

    resources = open_folder(page, folder)
    resources.click_section(normalise(section["title"]))
    document = next(c for c in contents_in(section) if c.get("file"))

    opened_before = len(page.context.pages)
    with page.context.expect_page() as opened:
        resources.open_tile(normalise(document["title"]))

    assert len(page.context.pages) == opened_before + 1
    expect(page).to_have_url(route_to(folder))
    opened.value.close()


# ---------------------------------------------------------------------------
# 5. A resource that is a video
# ---------------------------------------------------------------------------

def test_a_video_opens_on_the_player_route_for_that_content(page, video_content):
    """The path carries the whole way to it, ending on the id the call gave the
    video."""
    folder, body, subject, section, content = video_content
    resources = open_folder(page, folder)
    if is_filed_under_subjects(body):
        resources.click_subject(subjects_in(body)[subject])
    resources.click_section(normalise(section["title"]))

    resources.open_tile(normalise(content["title"]))

    video = ResourceVideoPage(page)
    video.wait_for_loaded()
    expect(page).to_have_url(ResourceVideoPage.URL_PATTERN)
    assert video.get_content_id() == content["id"]


def test_the_video_screen_names_the_video_the_call_named(page, video_content):
    folder, body, subject, section, content = video_content
    resources = open_folder(page, folder)
    if is_filed_under_subjects(body):
        resources.click_subject(subjects_in(body)[subject])
    resources.click_section(normalise(section["title"]))
    resources.open_tile(normalise(content["title"]))

    video = ResourceVideoPage(page)
    video.wait_for_loaded()

    expect(video.get_title()).to_have_text(normalise(content["title"]))


def test_the_video_screen_puts_up_a_player_and_its_controls(page, video_content):
    """The picture itself is an embed and cannot be read into from outside, so
    what is checked is that the player is there and the screen around it is
    ready to drive it."""
    folder, body, subject, section, content = video_content
    resources = open_folder(page, folder)
    if is_filed_under_subjects(body):
        resources.click_subject(subjects_in(body)[subject])
    resources.click_section(normalise(section["title"]))
    resources.open_tile(normalise(content["title"]))

    video = ResourceVideoPage(page)
    video.wait_for_loaded()

    expect(video.get_player()).to_be_attached()
    expect(video.get_progress()).to_be_visible()
    expect(video.get_time()).not_to_be_empty()
    assert video.get_controls().count() >= 1
    expect(video.get_back_button()).to_be_visible()


def test_the_video_clock_starts_at_nothing_and_is_a_clock(page, video_content):
    """The time reads as a clock before anything has played. What the video is
    worth in seconds is in the call; the screen writes it minutes and seconds,
    so the two are not the same string and only the shape is checked here."""
    folder, body, subject, section, content = video_content
    resources = open_folder(page, folder)
    if is_filed_under_subjects(body):
        resources.click_subject(subjects_in(body)[subject])
    resources.click_section(normalise(section["title"]))
    resources.open_tile(normalise(content["title"]))

    video = ResourceVideoPage(page)
    video.wait_for_loaded()

    import re as _re

    assert _re.match(r"^\d+:\d{2}\s*/\s*\d+:\d{2}$", video.get_time_text()), (
        f"the clock reads {video.get_time_text()!r}"
    )
    assert content["duration"] > 0, (
        f"{content['title']!r} is offered as a video the call says lasts "
        f"{content['duration']} seconds"
    )


def test_leaving_the_video_returns_to_the_folder_it_came_from(page, video_content):
    folder, body, subject, section, content = video_content
    resources = open_folder(page, folder)
    if is_filed_under_subjects(body):
        resources.click_subject(subjects_in(body)[subject])
    resources.click_section(normalise(section["title"]))
    resources.open_tile(normalise(content["title"]))

    video = ResourceVideoPage(page)
    video.wait_for_loaded()
    video.click_back()

    expect(page).to_have_url(route_to(folder))


def test_a_video_the_player_cannot_load_still_gives_the_screen_around_it(
    page, video_content
):
    """The embed is fed from somewhere else entirely, so it can fail on its own.
    With it blocked the screen still comes up, names the video and offers the
    way back, rather than going blank."""
    folder, body, subject, section, content = video_content
    resources = open_folder(page, folder)
    if is_filed_under_subjects(body):
        resources.click_subject(subjects_in(body)[subject])
    resources.click_section(normalise(section["title"]))

    page.route("**/*.m3u8*", lambda route: route.abort())
    page.route("**/youtube.com/**", lambda route: route.abort())
    try:
        resources.open_tile(normalise(content["title"]))
        video = ResourceVideoPage(page)
        video.wait_for_loaded()

        expect(video.get_title()).to_have_text(normalise(content["title"]))
        expect(video.get_back_button()).to_be_visible()
    finally:
        page.unroute("**/*.m3u8*")
        page.unroute("**/youtube.com/**")


# ---------------------------------------------------------------------------
# 6. Searching a folder  (API + UI)
#
# Search is a screen of its own behind the Search button in a folder's header.
# It asks the server nothing: it lists every item the folder's child-resources
# call answered, across all of its sections and subjects, and narrows that list
# in the browser as the box is typed into. So the results are held against the
# call the folder made as it opened, and every word searched for is taken from
# the folder's own titles.
# ---------------------------------------------------------------------------

def open_search_from_folder(page, folder):
    """The search as a student reaches it: the folder opened, then the Search
    button in its header.

    Hands back the search screen and what the folder's call answered. The call
    is listened for on the way into the folder, because the search lists that
    answer rather than asking again."""
    with page.expect_response(CHILD_RESOURCES_API) as answer:
        page.goto(route_to(folder), wait_until="domcontentloaded")
    assert answer.value.status == 200, f"child-resources answered {answer.value.status}"
    resources = ResourcesPage(page)
    resources.wait_for_loaded()
    resources.open_search()
    return ResourceSearchPage(page), answer.value.json()


def shown_title(content):
    """How a result is titled: the item's own title, or Untitled where it has
    none."""
    return normalise(content.get("title") or "Untitled")


def a_narrowing_word(items):
    """A word to search with, taken from the folder's own titles.

    One that keeps some items and drops others is preferred, so the list is
    seen to narrow; a folder whose titles all share their words gets one that
    keeps everything. Letters only, so its case can be turned over."""
    words = []
    for _, content in items:
        for word in re.findall(r"[A-Za-z]{3,}", content.get("title") or ""):
            if word not in words:
                words.append(word)
    for word in words:
        if 0 < len(search_matches(items, word)) < len(items):
            return word
    return words[0] if words else (items[0][1].get("title") or "").strip()


def a_word_nothing_matches(items):
    """Letters no title in the folder holds."""
    word = "zqxjv"
    while search_matches(items, word):
        word += "q"
    return word


def test_the_search_button_opens_the_folders_search_on_its_own_route(page, filled_folder):
    folder, _ = filled_folder
    resources = open_folder(page, folder)
    expect(resources.get_search_button()).to_be_visible()

    resources.open_search()

    expect(page).to_have_url(search_route(folder))
    search = ResourceSearchPage(page)
    expect(search.get_input()).to_have_attribute("placeholder", "Search here")
    expect(search.get_input()).to_be_focused()
    expect(search.get_input()).to_have_value("")
    expect(search.get_clear_button()).to_have_count(0)
    expect(search.get_back_button()).to_be_visible()


def test_an_empty_search_lists_every_item_in_the_folder(page, folders, filled_folder):
    """Before anything is typed the search offers the whole folder in one list:
    every item of every section, and of every subject in a folder filed under
    them, in the order the folder's call answered it, each with an icon.

    Checked on the filled folder and, where the course carries one, on a filled
    folder of the other kind as well, since the two are walked differently."""
    first, _ = filled_folder
    other_kind = SUBJECT_FOLDER if first["resource_type"] == PLAIN_FOLDER else PLAIN_FOLDER
    other = a_folder_with_content(page, folders, kind=other_kind)
    to_check = [first] + ([] if isinstance(other, str) else [other[0]])

    for folder in to_check:
        search, body = open_search_from_folder(page, folder)
        expected = [shown_title(content) for _, content in searchable_items(body)]

        expect(search.get_results()).to_have_count(len(expected))
        assert search.get_result_titles() == expected, folder["title"].strip()
        expect(search.get_result_icons()).to_have_count(len(expected))
        expect(search.get_matches()).to_have_count(0)


def test_a_search_keeps_only_the_items_whose_titles_hold_it(page, filled_folder):
    folder, _ = filled_folder
    search, body = open_search_from_folder(page, folder)
    items = searchable_items(body)
    word = a_narrowing_word(items)
    expected = [shown_title(content) for _, content in search_matches(items, word)]

    search.search(word)

    expect(search.get_matches()).to_have_count(len(expected))
    assert search.get_result_titles() == expected
    for title in search.get_result_titles():
        assert word.lower() in title.lower(), f"{title!r} does not hold {word!r}"


def test_the_search_pays_no_attention_to_case(page, filled_folder):
    """The word is typed with its case turned over from how the titles write
    it, and the same items are kept."""
    folder, _ = filled_folder
    search, body = open_search_from_folder(page, folder)
    items = searchable_items(body)
    word = a_narrowing_word(items)
    expected = [shown_title(content) for _, content in search_matches(items, word)]

    search.search(word.swapcase())

    expect(search.get_matches()).to_have_count(len(expected))
    assert search.get_result_titles() == expected


def test_each_result_marks_the_first_place_its_title_matched(page, filled_folder):
    """What is picked out is the title's own text, in the title's own case,
    wherever the search first appears in it."""
    folder, _ = filled_folder
    search, body = open_search_from_folder(page, folder)
    items = searchable_items(body)
    word = a_narrowing_word(items)
    kept = search_matches(items, word)

    search.search(word.swapcase())

    expect(search.get_matches()).to_have_count(len(kept))
    expected = []
    for _, content in kept:
        title = content["title"]
        start = title.lower().index(word.lower())
        expected.append(title[start:start + len(word)])
    assert search.get_match_texts() == expected


def test_a_search_that_matches_nothing_says_so(page, filled_folder):
    folder, _ = filled_folder
    search, body = open_search_from_folder(page, folder)

    search.search(a_word_nothing_matches(searchable_items(body)))

    expect(search.get_empty_state()).to_be_visible()
    expect(search.get_empty_title()).to_have_text("No Matching Search Result")
    expect(search.get_empty_subtitle()).to_have_text("Please try again with another keyword")
    expect(search.get_results()).to_have_count(0)


def test_clearing_the_search_brings_every_item_back(page, filled_folder):
    folder, _ = filled_folder
    search, body = open_search_from_folder(page, folder)
    items = searchable_items(body)
    search.search(a_narrowing_word(items))
    expect(search.get_clear_button()).to_be_visible()

    search.clear()

    expect(search.get_input()).to_have_value("")
    expect(search.get_clear_button()).to_have_count(0)
    expect(search.get_matches()).to_have_count(0)
    expected = [shown_title(content) for _, content in items]
    expect(search.get_results()).to_have_count(len(expected))
    assert search.get_result_titles() == expected


def test_going_back_from_search_returns_to_the_folder(page, filled_folder):
    folder, _ = filled_folder
    resources = open_folder(page, folder)
    resources.open_search()

    ResourceSearchPage(page).click_back()

    expect(page).to_have_url(route_to(folder))
    resources.wait_for_loaded()
    expect(resources.get_title()).to_have_text(normalise(folder["title"]))


def test_a_result_opens_the_way_the_folder_call_says_it_should(page, folders, filled_folder):
    """A result is opened by what its item is, and the folder's call is what
    says that: a video routes on to the player, a file opens in a tab of its
    own and leaves the search where it was, and an item in a premium section the
    student's batch does not cover raises the Premium sheet instead.

    One result of each of those the course carries is searched for by its own
    title and opened."""
    picked = {}
    for folder in folders:
        body = child_resources(page, folder)
        for section, content in searchable_items(body):
            outcome = opens_as(body, section, content)
            if outcome in (OPENS_LOCKED, OPENS_VIDEO, OPENS_FILE) and (content.get("title") or "").strip():
                picked.setdefault(outcome, (folder, section, content))
        if len(picked) == 3:
            break
    assert picked, "nothing in this course's folders is a video, a file or locked"

    for outcome, (folder, section, content) in picked.items():
        search, body = open_search_from_folder(page, folder)
        title = content["title"].strip()
        kept = search_matches(searchable_items(body), title)
        index = next(
            position
            for position, (kept_section, kept_content) in enumerate(kept)
            if kept_content["id"] == content["id"] and kept_section["id"] == section["id"]
        )
        search.search(title)
        expect(search.get_matches()).to_have_count(len(kept))

        if outcome == OPENS_VIDEO:
            search.open_result(index)
            video = ResourceVideoPage(page)
            video.wait_for_loaded()
            expect(page).to_have_url(ResourceVideoPage.URL_PATTERN)
            assert video.get_content_id() == content["id"]
            expect(video.get_title()).to_have_text(normalise(content["title"]))
            video.click_back()
            expect(page).to_have_url(search_route(folder))
        elif outcome == OPENS_FILE:
            with page.context.expect_page() as opened:
                search.open_result(index)
            expect(page).to_have_url(search_route(folder))
            opened.value.close()
        else:
            search.open_result(index)
            expect(search.get_lock_sheet()).to_be_visible()
            expect(search.get_lock_title()).to_have_text("Premium")
            expect(page).to_have_url(search_route(folder))
