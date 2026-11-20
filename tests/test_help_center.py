"""The Help Center behind the Profile page's Help Center card.

It replaced the hosted form that used to sit in an iframe. It is now part of
the app: a dialog over Profile (or a page at /help-center) with FAQs, a search
over them, a way to raise a ticket with a screenshot or video, the student's
tickets, and each ticket's conversation with support - replies when support
asks a question, a viewer for attached screenshots, and a rating once a ticket
is finished.

Everything it shows comes from its own backend (HC_API_BASE in
pages/help_center_page.py), not the main API, and the tests hold the screen
against those same calls, read with the student's own credentials.

Writes, and what they leave behind:

- test_raising_a_ticket_end_to_end raises a real ticket on every run. Its
  description starts "Automation test ticket" so support can tell them apart.
- The FAQ feedback tests set this student's verdict on one FAQ.
- test_replying_to_a_support_question and test_rating_support_is_saved each
  use up a state only support can create: a ticket waiting on the student, and
  a finished ticket that has not been rated. They run when the account has
  one and skip with the reason when it does not.

A ticket waiting on the student cannot be made on demand from here, so the
tests for how the reply box is drawn serve one of the student's real open
tickets with only that changed (patch_response). Nothing is sent that would
not otherwise be.

The web app is the online app only (its calls always say app=online), so there
is nothing residential to test here.
"""
import re
import time

import pytest
from playwright.sync_api import expect

from conftest import BASE_URL, HOME_URL, STUDENT_MOBILE
from pages.help_center_page import (
    FINISHED_STATUSES,
    HelpCenterPage,
    hc_api,
    hc_get,
    patch_response,
    status_kind,
)
from pages.profile_page import ProfilePage

PROFILE_URL = ProfilePage.URL
HELP_CENTER_URL = f"{BASE_URL}/help-center"

# What the screen says, word for word.
HERO_HEADING = "Something not working?"
NO_TICKETS = "No tickets yet"
RESOLVED_NOTICE = "Issue {} has been marked as resolved by our support team."
FINISHED_NOTICE = "This ticket is finished. If you need more help, raise a new ticket."
WAITING_NOTICE = "The reply box opens when your agent asks a question."
NOT_WHAT_IT_CLAIMS = "The attachment does not match its PNG, JPG, MP4, WebM or MOV format."
RATING_HEADING = "How was our support?"

# The attachment checks, in the order the form makes them.
WRONG_TYPE = "Choose a PNG/JPG image or an MP4, WebM or MOV video."
EMPTY_FILE = "This file is empty. Choose another attachment."
TOO_BIG = "Choose an attachment under 5 MB."
SIZE_LIMIT = 5_000_000

# A minimal MP4 header: an ftyp box naming isom. Enough for the form's own
# check that a .mp4 really is one; it is never played.
MP4_HEADER = (
    (24).to_bytes(4, "big") + b"ftyp" + b"isom" + (512).to_bytes(4, "big") + b"isom" + b"mp41"
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def page(login_as):
    """Signed in once per session and replayed, instead of logging in per test."""
    return login_as(STUDENT_MOBILE)


@pytest.fixture
def help_center(page):
    """Opened the way a student reaches it: the Help Center card on Profile."""
    page.goto(PROFILE_URL, wait_until="domcontentloaded")
    profile = ProfilePage(page)
    profile.wait_for_loaded()
    profile.click_card("Help Center")
    hc = HelpCenterPage(page)
    expect(hc.get_dialog()).to_be_visible()
    hc.wait_for_home()
    return hc


def open_help_center_with(page, path):
    """Open the Help Center from Profile and hand back the payload of one of
    the calls it makes on the way."""
    page.goto(PROFILE_URL, wait_until="domcontentloaded")
    profile = ProfilePage(page)
    profile.wait_for_loaded()
    with page.expect_response(hc_api(path), timeout=30000) as answer:
        profile.click_card("Help Center")
    assert answer.value.status == 200, f"{path} answered {answer.value.status}"
    hc = HelpCenterPage(page)
    hc.wait_for_home()
    return hc, answer.value.json()


def open_ticket(page, ticket_id):
    """Open one ticket straight from its link, the way a notification would."""
    page.goto(f"{HELP_CENTER_URL}/tickets/{ticket_id}", wait_until="domcontentloaded")
    hc = HelpCenterPage(page)
    hc.wait_for_ticket()
    return hc


def all_tickets(page, filter_="all"):
    """Every ticket of the student's under one filter, following the cursor."""
    tickets, cursor = [], None
    while True:
        query = f"tickets?filter={filter_}&limit=20" + (f"&cursor={cursor}" if cursor else "")
        body = hc_get(page, query)
        tickets += body["tickets"]
        cursor = body.get("next_cursor")
        if not cursor:
            return tickets


def ticket_details(page, ticket_id):
    body = hc_get(page, f"ticket?id={ticket_id}")
    return body["ticket"], body.get("history", [])


def find_ticket(page, wanted, reason):
    """The first of the student's tickets whose details satisfy wanted(ticket,
    history), or a skip naming what was missing."""
    for listed in all_tickets(page):
        ticket, history = ticket_details(page, listed["id"])
        if wanted(ticket, history):
            return ticket, history
    pytest.skip(f"No ticket on this account {reason}.")


def conversation(history):
    """The messages a ticket's conversation shows; status changes are not
    drawn."""
    return [m for m in history if m.get("type") != "status"]


def has_support_reply(history):
    return any(m.get("type") == "support_reply" for m in history)


def has_attachment(history):
    return any(m.get("attachments") for m in history)


def png(page, width=120, height=80):
    return page.screenshot(clip={"x": 0, "y": 0, "width": width, "height": height})


def go_to_describe(hc, form):
    """From the category step to the description, through the first category
    that has subcategories. Returns the labels chosen."""
    category = next(c for c in form["categories"] if c["subcategories"])
    sub = category["subcategories"][0]
    hc.choose_category(category["label"])
    hc.continue_()
    hc.choose_category(sub["label"])
    hc.continue_()
    expect(hc.get_description()).to_be_visible()
    return category, sub


def raise_form(page):
    """Open Raise a ticket and hand back the form it was drawn from."""
    hc, _ = open_help_center_with(page, "home")
    with page.expect_response(hc_api("form")) as answer:
        hc.open_raise()
    form = answer.value.json()
    hc.get_categories().first.wait_for()
    return hc, form


# ---------------------------------------------------------------------------
# 1. Opening and closing
# ---------------------------------------------------------------------------

def test_the_help_center_card_opens_the_help_center(help_center):
    expect(help_center.get_dialog()).to_have_attribute("aria-label", "Help Center")
    expect(help_center.get_title()).to_have_text("Help Center")
    expect(help_center.get_back()).to_have_count(0)


def test_close_shuts_the_help_center(help_center, page):
    help_center.close()

    expect(help_center.get_dialog()).to_have_count(0)
    expect(page).to_have_url(PROFILE_URL)


def test_escape_shuts_the_help_center(help_center, page):
    page.keyboard.press("Escape")

    expect(help_center.get_dialog()).to_have_count(0)


def test_a_click_outside_shuts_the_help_center(help_center, page):
    # The dialog fills the screen behind its panel, so its own top-left corner
    # is backdrop rather than panel.
    help_center.get_dialog().click(position={"x": 2, "y": 2})

    expect(help_center.get_dialog()).to_have_count(0)


def test_the_help_center_link_opens_it_as_a_page(page):
    page.goto(HELP_CENTER_URL, wait_until="domcontentloaded")
    hc = HelpCenterPage(page)

    expect(hc.get_full_page()).to_be_visible()
    hc.wait_for_home()

    hc.close()
    expect(page).to_have_url(HOME_URL)


def test_a_ticket_link_opens_that_ticket_over_the_help_center(page):
    listed = hc_get(page, "tickets?filter=all&limit=20")["tickets"]
    if not listed:
        pytest.skip("This account has no tickets to link to.")
    ticket = listed[0]

    hc = open_ticket(page, ticket["id"])

    expect(hc.get_ticket_heading()).to_have_text(f"Ticket {ticket['ticket_no']} created")
    hc.dismiss_rating_if_open()
    hc.go_back()
    hc.wait_for_home()


# ---------------------------------------------------------------------------
# 2. Home
# ---------------------------------------------------------------------------

def test_home_offers_to_raise_a_ticket(help_center):
    hero = help_center.get_hero()

    expect(hero.locator("h2")).to_have_text(HERO_HEADING)
    expect(hero).to_contain_text("Raise a ticket and our team")
    expect(help_center.get_hero_raise()).to_be_enabled()
    expect(help_center.get_home_sections()).to_have_text(["FAQs", "Your recent tickets"])


def test_home_shows_the_top_three_faqs(page):
    hc, home = open_help_center_with(page, "home")
    top = [faq["question"] for faq in home["top_faqs"]][:3]

    if top:
        expect(hc.get_featured_faqs()).to_have_text(top)
    else:
        expect(hc.get_view("home").locator(".hc-featured-faqs")).to_have_text(
            "Have a question? Our support team can help."
        )


def test_home_shows_the_three_latest_tickets(page):
    hc, home = open_help_center_with(page, "home")
    recent = home["recent_tickets"][:3]

    if not recent:
        expect(hc.get_view("home").locator(".hc-empty h3")).to_have_text(NO_TICKETS)
        return

    cards = hc.get_home_tickets()
    expect(cards).to_have_count(len(recent))
    for card, ticket in zip(cards.all(), recent):
        expect(hc.card_number(card)).to_have_text(ticket["ticket_no"])
        expect(hc.card_status(card)).to_have_text(ticket["status_label"])
        expect(hc.card_title(card)).to_have_text(ticket["title"] or ticket["category"])
        expect(hc.card_category(card).first).to_have_text(ticket["category"])


def test_see_all_opens_the_faqs_and_back_returns_home(help_center):
    help_center.open_all_faqs()

    expect(help_center.get_back()).to_be_visible()
    help_center.go_back()
    help_center.wait_for_home()


def test_view_all_opens_my_tickets(help_center):
    help_center.open_all_tickets()

    expect(help_center.get_filter("All")).to_have_attribute("aria-pressed", "true")


def test_a_recent_ticket_opens_its_conversation(page):
    hc, home = open_help_center_with(page, "home")
    if not home["recent_tickets"]:
        pytest.skip("This account has no tickets.")
    ticket = home["recent_tickets"][0]

    hc.get_ticket_card(ticket["ticket_no"]).click()

    hc.wait_for_ticket()
    expect(hc.get_ticket_heading()).to_have_text(f"Ticket {ticket['ticket_no']} created")


# ---------------------------------------------------------------------------
# 3. FAQs and search
# ---------------------------------------------------------------------------

@pytest.fixture
def faqs(page):
    """The FAQ browser, and the FAQ list it was drawn from."""
    hc, _ = open_help_center_with(page, "home")
    with page.expect_response(hc_api("faqs")) as answer:
        hc.open_all_faqs()
    body = answer.value.json()
    if body["popular"]:
        hc.get_faq_rows().first.wait_for()
    return hc, body


def test_faqs_open_on_the_popular_questions(faqs):
    hc, body = faqs

    expect(hc.get_topic_tab("Popular")).to_have_attribute("aria-pressed", "true")
    assert hc.get_faq_questions() == [faq["question"] for faq in body["popular"]]


def test_the_topic_tabs_are_the_faq_topics(faqs):
    hc, body = faqs

    expect(hc.get_topic_tabs()).to_have_text(["Popular"] + [t["name"] for t in body["topics"]])


def test_a_topic_tab_shows_that_topics_questions(faqs):
    hc, body = faqs
    topic = next((t for t in body["topics"] if t["faqs"]), None)
    if topic is None:
        pytest.skip("No FAQ topic has questions.")

    hc.get_topic_tab(topic["name"]).click()

    expect(hc.get_topic_tab(topic["name"])).to_have_attribute("aria-pressed", "true")
    expect(hc.get_topic_tab("Popular")).to_have_attribute("aria-pressed", "false")
    expect(hc.get_faq_rows()).to_have_count(len(topic["faqs"]))
    assert hc.get_faq_questions() == [faq["question"] for faq in topic["faqs"]]


def test_search_lists_the_matching_questions_with_their_topics(faqs, page):
    hc, _ = faqs

    with page.expect_response(hc_api("faq-search")) as answer:
        hc.search("payment")
    results = answer.value.json()["results"]
    if not results:
        pytest.skip('No FAQ matches "payment" any more.')

    expect(hc.get_faq_rows()).to_have_count(len(results))
    assert hc.get_faq_questions() == [r["question"] for r in results]
    assert hc.get_faq_topics_shown() == [r["topic"] for r in results if r["topic"]]
    # Searching swaps the topic tabs for a way back.
    expect(hc.get_topic_tabs()).to_have_count(0)
    expect(hc.get_search_back()).to_be_visible()


def test_a_search_with_no_match_says_so_and_offers_a_ticket(faqs, page):
    hc, _ = faqs
    query = "zzqxvplk"

    with page.expect_response(hc_api("faq-search")) as answer:
        hc.search(query)
    assert answer.value.json()["no_results"] is True

    empty = hc.get_faq_empty()
    expect(empty.locator("h2")).to_have_text(f"No results for “{query}”")
    expect(hc.get_hero_raise()).to_be_visible()

    hc.get_hero_raise().click()
    hc.wait_for_view("raise")


def test_cancel_clears_the_search_and_brings_back_the_topics(faqs):
    hc, body = faqs
    hc.search("payment")
    expect(hc.get_search_cancel()).to_be_visible()

    hc.get_search_cancel().click()

    expect(hc.get_search()).to_have_value("")
    expect(hc.get_topic_tab("Popular")).to_have_attribute("aria-pressed", "true")
    expect(hc.get_faq_rows()).to_have_count(len(body["popular"]))


# ---------------------------------------------------------------------------
# 4. One FAQ and its feedback
# ---------------------------------------------------------------------------

@pytest.fixture
def faq(faqs, page):
    """One FAQ opened from the list, and its own answer."""
    hc, body = faqs
    if not body["popular"]:
        pytest.skip("There are no FAQs.")
    question = body["popular"][0]["question"]
    with page.expect_response(hc_api("faq")) as answer:
        hc.open_faq_row(question)
    return hc, answer.value.json()["faq"]


def test_an_faq_shows_its_answer(faq):
    hc, data = faq

    expect(hc.get_faq_question()).to_have_text(data["question"])
    meta = hc.get_faq_meta().inner_text()
    assert meta.startswith(data["topic"]), meta
    assert meta.endswith(f"{data['helpful_count']} found this helpful"), meta

    answer = hc.get_faq_answer()
    for block in data["answer"]:
        if block["type"] == "steps":
            for item in block["items"]:
                expect(answer.locator("ol.hc-faq-steps")).to_contain_text(item)
        else:
            expect(answer).to_contain_text(block["text"])
    expect(hc.get_faq_detail().locator(".hc-faq-feedback h3")).to_have_text("Was this helpful?")


def test_marking_an_faq_helpful_is_saved(faq, page):
    hc, _ = faq

    with page.expect_request(hc_api("faq-feedback")) as sent:
        with page.expect_response(hc_api("faq-feedback")) as answer:
            hc.get_helpful().click()
    assert sent.value.post_data_json["verdict"] == "helpful"
    reply = answer.value.json()
    assert reply["saved"] is True, reply

    expect(hc.get_helpful()).to_have_attribute("aria-pressed", "true")
    expect(hc.get_not_resolved()).to_have_attribute("aria-pressed", "false")
    expect(hc.get_feedback_thanks()).to_be_visible()
    expect(hc.get_faq_meta()).to_contain_text(f"{reply['helpful_count']} found this helpful")


def test_not_resolved_offers_to_raise_a_ticket(faq, page):
    hc, _ = faq

    with page.expect_request(hc_api("faq-feedback")) as sent:
        hc.get_not_resolved().click()
    assert sent.value.post_data_json["verdict"] == "not_resolved"

    expect(hc.get_not_resolved()).to_have_attribute("aria-pressed", "true")
    cta = hc.get_still_need_help()
    expect(cta.locator("h3")).to_have_text("Still need help?")

    cta.get_by_role("button", name="Raise a ticket").click()
    hc.wait_for_view("raise")


# ---------------------------------------------------------------------------
# 5. Raise a ticket: choosing the issue
# ---------------------------------------------------------------------------

def test_raise_lists_the_issue_categories(page):
    hc, form = raise_form(page)

    assert hc.get_category_labels() == [c["label"] for c in form["categories"]]
    expect(hc.get_continue()).to_be_disabled()


def test_a_category_with_subcategories_asks_for_one(page):
    hc, form = raise_form(page)
    category = next(c for c in form["categories"] if c["subcategories"])

    hc.choose_category(category["label"])
    expect(hc.get_continue()).to_be_enabled()
    hc.continue_()

    assert hc.get_category_labels() == [s["label"] for s in category["subcategories"]]
    expect(hc.get_continue()).to_be_disabled()

    # Back steps out to the categories with the choice still made.
    hc.go_back()
    assert hc.get_category_labels() == [c["label"] for c in form["categories"]]
    expect(hc.get_categories().filter(has_text=category["label"]).first).to_have_class(
        re.compile(r"\bis-selected\b")
    )


def test_a_category_without_subcategories_goes_straight_to_the_form(page):
    hc, form = raise_form(page)
    category = next(
        (c for c in form["categories"] if not c["subcategories"] and not c["requires_subcategory"]),
        None,
    )
    if category is None:
        pytest.skip("Every category has subcategories.")

    hc.choose_category(category["label"])
    hc.continue_()

    expect(hc.get_description()).to_be_visible()
    assert hc.get_issue_path() == [category["label"]]


def test_the_form_shows_the_chosen_issue_and_change_goes_back(page):
    hc, form = raise_form(page)
    category, sub = go_to_describe(hc, form)

    assert hc.get_issue_path() == [category["label"], sub["label"]]

    hc.get_change().click()
    expect(hc.get_categories().first).to_be_visible()
    expect(hc.get_description()).to_have_count(0)


# ---------------------------------------------------------------------------
# 6. Raise a ticket: the form
# ---------------------------------------------------------------------------

@pytest.fixture
def ticket_form(page):
    """The ticket form, reached through a category and subcategory."""
    hc, form = raise_form(page)
    go_to_describe(hc, form)
    return hc, form


def test_the_description_counts_and_stops_at_its_limit(ticket_form):
    hc, form = ticket_form
    limit = min(500, form["description_max_length"])

    expect(hc.get_description_counter()).to_have_text(f"0/{limit}")
    hc.get_description().fill("hello")
    expect(hc.get_description_counter()).to_have_text(f"5/{limit}")

    hc.get_description().fill("x" * (limit + 100))
    expect(hc.get_description()).to_have_value("x" * limit)
    expect(hc.get_description_counter()).to_have_text(f"{limit}/{limit}")


def test_submit_waits_for_a_description_and_an_attachment(ticket_form, page):
    hc, _ = ticket_form
    submit = hc.get_submit()
    expect(submit).to_be_disabled()

    hc.get_description().fill("Something broke")
    expect(submit).to_be_disabled()

    hc.get_description().fill("")
    hc.attach("shot.png", "image/png", png(page))
    expect(submit).to_be_disabled()

    hc.get_description().fill("Something broke")
    expect(submit).to_be_enabled()

    # Spaces alone are not a description.
    hc.get_description().fill("   ")
    expect(submit).to_be_disabled()


def test_the_attachment_is_marked_required(ticket_form):
    hc, _ = ticket_form

    picker = hc.get_attachment_picker()
    expect(picker).to_contain_text("Add an image or video *")
    expect(picker).to_contain_text("Required · PNG, JPG, MP4, WebM or MOV · under 5 MB")


def test_an_image_shows_a_preview_that_can_be_removed(ticket_form, page):
    hc, _ = ticket_form

    hc.attach("my-screen.png", "image/png", png(page))

    preview = hc.get_attachment_preview()
    expect(preview.get_by_role("img", name="Screenshot preview")).to_be_visible()
    expect(preview).to_contain_text("my-screen.png")
    expect(hc.get_attachment_picker()).to_have_count(0)

    preview.get_by_role("button", name="Remove screenshot").click()
    expect(preview).to_have_count(0)
    expect(hc.get_attachment_picker()).to_be_visible()


def test_a_jpeg_is_accepted(ticket_form, page):
    hc, _ = ticket_form

    hc.attach("photo.jpg", "image/jpeg", page.screenshot(type="jpeg"))

    expect(hc.get_attachment_preview()).to_contain_text("photo.jpg")
    expect(hc.get_attachment_error()).to_have_count(0)


def test_a_video_shows_a_video_preview(ticket_form):
    hc, _ = ticket_form

    hc.attach("screen-recording.mp4", "video/mp4", MP4_HEADER)

    preview = hc.get_attachment_preview()
    expect(preview.locator("video[aria-label='Video preview']")).to_be_attached()
    expect(preview).to_contain_text("screen-recording.mp4")
    preview.get_by_role("button", name="Remove video").click()
    expect(preview).to_have_count(0)


@pytest.mark.parametrize(
    "name, mime_type, data, message",
    [
        ("notes.txt", "text/plain", b"plain text", WRONG_TYPE),
        ("animation.gif", "image/gif", b"GIF89a....", WRONG_TYPE),
        ("document.pdf", "application/pdf", b"%PDF-1.4", WRONG_TYPE),
        ("empty.png", "image/png", b"", EMPTY_FILE),
        ("huge.png", "image/png", b"\x89PNG\r\n\x1a\n" + b"\0" * SIZE_LIMIT, TOO_BIG),
    ],
    ids=["text", "gif", "pdf", "empty", "5mb"],
)
def test_an_attachment_the_form_cannot_take_is_refused(ticket_form, name, mime_type, data, message):
    hc, _ = ticket_form

    hc.attach(name, mime_type, data)

    expect(hc.get_attachment_error()).to_have_text(message)
    expect(hc.get_attachment_preview()).to_have_count(0)
    expect(hc.get_attachment_picker()).to_be_visible()


def test_a_file_that_is_not_what_its_name_says_is_refused_before_upload(ticket_form, page):
    hc, _ = ticket_form
    uploads = []
    page.on("request", lambda r: hc_api("upload-url")(r) and uploads.append(r))

    hc.get_description().fill("Automation check - this ticket must not be sent")
    hc.attach("pretend.png", "image/png", b"this is not a picture at all" * 4)
    hc.get_submit().click()

    expect(hc.get_raise_error()).to_contain_text(NOT_WHAT_IT_CLAIMS)
    expect(hc.get_success()).to_have_count(0)
    # Nothing was asked of the backend for a file that failed its own check,
    # and the draft is still there to fix.
    assert uploads == []
    expect(hc.get_description()).to_have_value("Automation check - this ticket must not be sent")


# ---------------------------------------------------------------------------
# 7. Raise a ticket: sending it
# ---------------------------------------------------------------------------

def test_raising_a_ticket_end_to_end(page):
    """Fill the form, send it, and follow the new ticket everywhere it should
    now appear. This raises a real ticket."""
    before = hc_get(page, "tickets?filter=all&limit=20")["counts"]["all"]
    hc, form = raise_form(page)
    category, sub = go_to_describe(hc, form)
    description = f"Automation test ticket {time.strftime('%Y-%m-%d %H:%M:%S')} - please ignore"

    hc.get_description().fill(description)
    hc.attach("automation-screen.png", "image/png", png(page, 320, 200))
    with page.expect_request(lambda r: hc_api("tickets")(r) and r.method == "POST") as sent:
        with page.expect_response(
            lambda r: hc_api("tickets")(r) and r.request.method == "POST", timeout=60000
        ) as answer:
            hc.get_submit().click()

    body = sent.value.post_data_json
    assert body["category_id"] == category["id"]
    assert body["subcategory_id"] == sub["id"]
    assert body["description"] == description
    assert body["attachment_path"], "the ticket went out without its attachment"
    assert answer.value.status in (200, 201), answer.value.status
    created = answer.value.json()
    assert created.get("test_ticket") is not True, "the backend only checked the ticket, it did not save it"
    ticket = created["ticket"]

    # The confirmation.
    expect(hc.get_success().locator("h2")).to_have_text("Ticket raised")
    summary = hc.get_success_summary()
    assert summary["Ticket ID"] == ticket["ticket_no"]
    # The issue is the ticket's own category when the backend sends one back,
    # otherwise the path that was picked.
    assert summary["Issue"] in (
        f"{category['label']} / {sub['label']}",
        f"{category['label']} > {sub['label']}",
    ), summary["Issue"]
    assert summary["Status"] == ticket["status_label"]

    # The ticket itself: what was sent, and the screenshot with it.
    hc.get_success().get_by_role("button", name="View ticket").click()
    hc.wait_for_ticket()
    expect(hc.get_ticket_heading()).to_have_text(f"Ticket {ticket['ticket_no']} created")
    expect(hc.get_ticket_category()).to_have_text(f"{category['label']} > {sub['label']}")
    expect(hc.get_ticket_title()).to_have_text(description)
    student = hc.get_student_messages()
    expect(student.first).to_contain_text("You")
    expect(student.first).to_contain_text(description)
    expect(hc.get_screenshots()).to_have_count(1)

    # Home lists it first, and My tickets counts it.
    hc.go_back()
    hc.get_success().get_by_role("button", name="Back to Help Center").click()
    hc.wait_for_home()
    expect(hc.card_number(hc.get_home_tickets().first)).to_have_text(ticket["ticket_no"])
    hc.open_all_tickets()
    expect(hc.get_filter("All")).to_have_text(f"All ({before + 1})")


# ---------------------------------------------------------------------------
# 8. My tickets
# ---------------------------------------------------------------------------

@pytest.fixture
def my_tickets(page):
    hc, _ = open_help_center_with(page, "home")
    with page.expect_response(hc_api("tickets")) as answer:
        hc.open_all_tickets()
    body = answer.value.json()
    if body["tickets"]:
        hc.get_list_tickets().first.wait_for()
    return hc, body


def test_the_filters_carry_the_ticket_counts(my_tickets):
    hc, body = my_tickets
    counts = body["counts"]

    expect(hc.get_filter("All")).to_have_text(f"All ({counts['all']})")
    expect(hc.get_filter("Open")).to_have_text(f"Open ({counts['open']})")
    expect(hc.get_filter("Resolved")).to_have_text(f"Resolved ({counts['resolved']})")
    assert counts["all"] == counts["open"] + counts["resolved"]


@pytest.mark.parametrize("filter_, label", [("all", "All"), ("open", "Open"), ("resolved", "Resolved")])
def test_a_filter_lists_only_its_tickets(my_tickets, page, filter_, label):
    hc, _ = my_tickets

    with page.expect_response(lambda r: hc_api("tickets")(r) and f"filter={filter_}" in r.url) as answer:
        if filter_ == "all":
            hc.get_filter("Open").click()
        hc.get_filter(label).click()
    expected = answer.value.json()["tickets"]

    expect(hc.get_filter(label)).to_have_attribute("aria-pressed", "true")
    expect(hc.get_list_tickets()).to_have_count(len(expected))
    assert hc.get_list_numbers() == [t["ticket_no"] for t in expected]
    if filter_ != "all":
        assert {t["group"] for t in expected} <= {filter_}


def test_each_ticket_card_shows_its_number_status_title_and_issue(my_tickets):
    hc, body = my_tickets
    if not body["tickets"]:
        expect(hc.get_view("tickets").locator(".hc-ticket-empty h2")).to_have_text(NO_TICKETS)
        return

    for card, ticket in zip(hc.get_list_tickets().all(), body["tickets"]):
        expect(hc.card_number(card)).to_have_text(ticket["ticket_no"])
        expect(hc.card_status(card)).to_have_text(ticket["status_label"])
        expect(hc.card_status(card)).to_have_class(
            re.compile(rf"\bhc-status-{status_kind(ticket['status'])}\b")
        )
        expect(hc.card_title(card)).to_have_text(ticket["title"] or ticket["category"])
        expect(hc.card_category(card).first).to_have_text(ticket["category"])


def test_load_more_brings_the_next_page(my_tickets, page):
    hc, body = my_tickets
    if not body.get("next_cursor"):
        pytest.skip(f"All {body['counts']['all']} tickets fit on the first page.")

    with page.expect_response(lambda r: hc_api("tickets")(r) and "cursor=" in r.url) as answer:
        hc.get_load_more().click()
    more = answer.value.json()["tickets"]

    expect(hc.get_list_tickets()).to_have_count(len(body["tickets"]) + len(more))


# ---------------------------------------------------------------------------
# 9. A ticket's conversation
# ---------------------------------------------------------------------------

def test_a_ticket_shows_its_details_and_conversation(page):
    ticket, history = find_ticket(
        page,
        lambda t, h: has_support_reply(h),
        "that support has replied to",
    )
    hc = open_ticket(page, ticket["id"])
    hc.dismiss_rating_if_open()

    expect(hc.get_ticket_heading()).to_have_text(f"Ticket {ticket['ticket_no']} created")
    expect(hc.get_ticket_status()).to_have_text(ticket["status_label"])
    expect(hc.get_ticket_category()).to_have_text(ticket["category"])
    expect(hc.get_ticket_title()).to_have_text(ticket["title"])

    # Each message is one bubble for its words and one more per attachment;
    # status changes are not drawn.
    messages = conversation(history)
    bubbles = sum(
        (1 if (m.get("text") or m.get("answers") or m.get("faq") or not m.get("attachments")) else 0)
        + len(m.get("attachments") or [])
        for m in messages
    )
    expect(hc.get_messages()).to_have_count(bubbles)

    from_student = [m for m in messages if m["type"] in ("student_message", "student_reply")]
    expect(hc.get_student_messages().first.locator(".hc-message-author")).to_have_text("You")
    support = [m for m in messages if m not in from_student]
    for message in support:
        if message.get("text"):
            expect(hc.get_support_messages().filter(has_text=message["text"]).first).to_be_visible()
    if support:
        expect(hc.get_support_messages().first.locator(".hc-message-author")).to_have_text(
            support[0].get("author") or "Eduport Support"
        )


def test_a_resolved_ticket_says_so_and_takes_no_reply(page):
    ticket, _ = find_ticket(page, lambda t, h: t["status"] == "resolved", "that is resolved")
    hc = open_ticket(page, ticket["id"])
    hc.dismiss_rating_if_open()

    expect(hc.get_resolved_footer()).to_have_text(RESOLVED_NOTICE.format(ticket["ticket_no"]))
    expect(hc.get_composer()).to_have_count(0)


def test_a_finished_ticket_points_to_a_new_one(page):
    ticket, _ = find_ticket(
        page,
        lambda t, h: t["status"] in FINISHED_STATUSES and t["status"] != "resolved",
        "that is closed, cancelled or otherwise finished without being resolved",
    )
    hc = open_ticket(page, ticket["id"])
    hc.dismiss_rating_if_open()

    expect(hc.get_reply_notice()).to_have_text(FINISHED_NOTICE)
    expect(hc.get_composer()).to_have_count(0)


def test_an_open_ticket_keeps_the_reply_box_closed_until_support_asks(page):
    ticket, _ = find_ticket(
        page,
        lambda t, h: t["status"] not in FINISHED_STATUSES and not t["question_waiting"],
        "that is open with no question from support",
    )
    hc = open_ticket(page, ticket["id"])

    expect(hc.get_reply_notice()).to_have_text(WAITING_NOTICE)
    expect(hc.get_composer()).to_have_count(0)


def waiting_on_student(ticket_data, with_attachment):
    ticket_data["ticket"].update(
        can_reply=True,
        question_waiting=True,
        can_reply_with_attachment=with_attachment,
    )


def open_ticket_as_waiting(page, with_attachment):
    """One of the student's open tickets, drawn as if support had just asked a
    question on it."""
    ticket, _ = find_ticket(
        page,
        lambda t, h: t["status"] not in FINISHED_STATUSES,
        "that is still open",
    )
    patch_response(page, "ticket", lambda data: waiting_on_student(data, with_attachment))
    return open_ticket(page, ticket["id"])


def test_a_question_from_support_opens_the_reply_box(page):
    hc = open_ticket_as_waiting(page, with_attachment=True)

    expect(hc.get_composer()).to_be_visible()
    expect(hc.get_reply_box()).to_have_attribute("maxlength", "500")
    expect(hc.get_send_reply()).to_be_disabled()
    hc.get_reply_box().fill("Here is more detail")
    expect(hc.get_send_reply()).to_be_enabled()
    hc.get_reply_box().fill("   ")
    expect(hc.get_send_reply()).to_be_disabled()


def test_the_reply_box_offers_an_upload_when_support_allows_one(page):
    hc = open_ticket_as_waiting(page, with_attachment=True)
    composer = hc.get_composer()

    picker = hc.get_attachment_picker(composer)
    expect(picker).to_contain_text("Add an image or video")
    expect(picker).to_contain_text("Optional")

    hc.attach("reply.png", "image/png", png(page), scope=composer)
    expect(hc.get_attachment_preview(composer)).to_contain_text("reply.png")
    # A screenshot on its own is a reply.
    expect(hc.get_send_reply()).to_be_enabled()


def test_the_reply_box_hides_uploads_when_support_does_not_allow_them(page):
    """Support decides per ticket whether a reply may carry a screenshot
    (can_reply_with_attachment); without that, the reply is text only."""
    hc = open_ticket_as_waiting(page, with_attachment=False)
    composer = hc.get_composer()

    expect(composer).to_be_visible()
    expect(hc.get_attachment_picker(composer)).to_have_count(0)
    expect(hc.get_file_input(composer)).to_have_count(0)


def test_replying_to_a_support_question(page):
    """Answers the question support is waiting on. Uses that state up: it
    runs only while support has a question open on one of this account's
    tickets."""
    ticket, history = find_ticket(
        page,
        lambda t, h: t["can_reply"] and t["question_waiting"] and t["status"] not in FINISHED_STATUSES,
        "with a question from support waiting on the student",
    )
    hc = open_ticket(page, ticket["id"])
    text = f"Automation reply {time.strftime('%H:%M:%S')}"
    before = hc.get_student_messages().count()

    hc.get_reply_box().fill(text)
    if ticket["can_reply_with_attachment"]:
        hc.attach("reply.png", "image/png", png(page), scope=hc.get_composer())
    with page.expect_request(hc_api("reply")) as sent:
        with page.expect_response(hc_api("reply"), timeout=60000) as answer:
            hc.get_send_reply().click()

    body = sent.value.post_data_json
    assert body["ticket_id"] == ticket["id"]
    assert body["text"] == text
    assert bool(body.get("attachment_path")) == ticket["can_reply_with_attachment"]
    assert answer.value.status == 200, answer.value.status

    expect(hc.get_student_messages().filter(has_text=text)).to_have_count(1)
    expect(hc.get_student_messages()).to_have_count(
        before + 1 + (1 if ticket["can_reply_with_attachment"] else 0)
    )


# ---------------------------------------------------------------------------
# 10. Viewing an attached screenshot
# ---------------------------------------------------------------------------

@pytest.fixture
def image_viewer(page):
    ticket, _ = find_ticket(
        page,
        lambda t, h: any(
            not (a.get("content_type") or "").startswith("video/")
            for m in h
            for a in (m.get("attachments") or [])
        ),
        "with a screenshot attached",
    )
    hc = open_ticket(page, ticket["id"])
    hc.dismiss_rating_if_open()
    shot = hc.get_screenshots().first
    name = shot.get_attribute("aria-label").removeprefix("View image: ")
    expect(shot).to_contain_text("View screenshot")
    shot.click()
    expect(hc.get_image_viewer()).to_be_visible()
    hc.wait_for_image_loaded()
    return hc, name


def test_a_screenshot_opens_in_the_image_viewer(image_viewer):
    hc, name = image_viewer

    expect(hc.get_viewer_title()).to_have_text(name)
    expect(hc.get_viewer_image()).to_have_attribute("alt", name)
    expect(hc.get_image_viewer()).to_contain_text("Zoom in to read details. Drag or scroll to move around.")
    expect(hc.get_fit_image()).to_have_attribute("aria-pressed", "true")


def test_the_image_viewer_zooms_in_and_out(image_viewer):
    hc, _ = image_viewer
    fit = hc.zoom_percent()

    hc.get_zoom_in().click()
    zoomed = hc.zoom_percent()
    assert abs(zoomed - fit * 1.25) <= 1, (fit, zoomed)
    expect(hc.get_fit_image()).to_have_attribute("aria-pressed", "false")

    hc.get_zoom_out().click()
    assert abs(hc.zoom_percent() - fit) <= 1


def test_the_image_viewer_switches_between_fit_and_original_size(image_viewer):
    hc, _ = image_viewer
    fit = hc.zoom_percent()

    hc.get_original_size().click()
    expect(hc.get_zoom_level()).to_have_text("100%")
    expect(hc.get_original_size()).to_have_attribute("aria-pressed", "true")

    hc.get_fit_image().click()
    expect(hc.get_zoom_level()).to_have_text(f"{fit}%")
    expect(hc.get_fit_image()).to_have_attribute("aria-pressed", "true")


def test_the_image_viewer_closes_with_its_button(image_viewer):
    hc, _ = image_viewer

    hc.get_viewer_close().click()

    expect(hc.get_image_viewer()).to_have_count(0)
    expect(hc.get_ticket_detail()).to_be_visible()


def test_the_image_viewer_closes_with_escape(image_viewer, page):
    hc, _ = image_viewer

    page.keyboard.press("Escape")

    expect(hc.get_image_viewer()).to_have_count(0)
    # Escape shuts the viewer only, not the Help Center under it.
    expect(hc.get_ticket_detail()).to_be_visible()


# ---------------------------------------------------------------------------
# 11. Rating support on a finished ticket
# ---------------------------------------------------------------------------

def rateable(ticket, history):
    return (
        ticket["can_rate"]
        and ticket["status"] in FINISHED_STATUSES
        and ticket["status"] not in ("cancelled", "merged")
        and has_support_reply(history)
    )


def test_a_finished_ticket_asks_for_a_rating(page):
    """The sheet opens by itself on a finished ticket that support answered and
    the student has not rated. Drawn from a rated ticket with its rating taken
    off, so the real unrated ones are left for the test that rates."""
    ticket, _ = find_ticket(page, rateable, "that is finished, answered by support and rateable")
    patch_response(page, "ticket", lambda data: data["ticket"].update(my_rating=None))
    hc = open_ticket(page, ticket["id"])

    sheet = hc.get_rating_sheet()
    expect(sheet).to_be_visible()
    expect(sheet.locator("h2")).to_have_text(RATING_HEADING)
    expect(sheet).to_contain_text("Closing this ticket. If the issue comes back, raise a new one.")
    expect(hc.get_rating_button("Not Helpful")).to_be_enabled()
    expect(hc.get_rating_button("Helpful")).to_be_enabled()


def test_the_rating_sheet_can_be_put_off_and_reopened(page):
    ticket, _ = find_ticket(page, rateable, "that is finished, answered by support and rateable")
    patch_response(page, "ticket", lambda data: data["ticket"].update(my_rating=None))
    hc = open_ticket(page, ticket["id"])
    expect(hc.get_rating_sheet()).to_be_visible()

    hc.get_rating_close().click()
    expect(hc.get_rating_sheet()).to_have_count(0)

    hc.get_rate_support().click()
    expect(hc.get_rating_sheet()).to_be_visible()


def test_a_rated_ticket_does_not_ask_again(page):
    ticket, _ = find_ticket(
        page,
        lambda t, h: rateable(t, h) and t["my_rating"],
        "that has already been rated",
    )
    hc = open_ticket(page, ticket["id"])

    page.wait_for_timeout(1500)
    expect(hc.get_rating_sheet()).to_have_count(0)
    expect(hc.get_rate_support()).to_have_count(0)


def test_a_ticket_that_cannot_be_rated_never_asks(page):
    ticket, _ = find_ticket(
        page,
        lambda t, h: t["status"] in FINISHED_STATUSES and not t["can_rate"],
        "that is finished but not open to rating",
    )
    hc = open_ticket(page, ticket["id"])

    page.wait_for_timeout(1500)
    expect(hc.get_rating_sheet()).to_have_count(0)
    expect(hc.get_rate_support()).to_have_count(0)


def test_an_open_ticket_never_asks_for_a_rating(page):
    ticket, _ = find_ticket(
        page,
        lambda t, h: t["status"] not in FINISHED_STATUSES,
        "that is still open",
    )
    hc = open_ticket(page, ticket["id"])

    page.wait_for_timeout(1500)
    expect(hc.get_rating_sheet()).to_have_count(0)
    expect(hc.get_rate_support()).to_have_count(0)


def test_rating_support_is_saved(page):
    """Rates a real finished ticket. A rating cannot be changed afterwards, so
    this runs only while the account has an unrated one."""
    ticket, _ = find_ticket(
        page,
        lambda t, h: rateable(t, h) and not t["my_rating"],
        "that is finished and still unrated",
    )
    hc = open_ticket(page, ticket["id"])
    expect(hc.get_rating_sheet()).to_be_visible()

    with page.expect_request(hc_api("rate")) as sent:
        with page.expect_response(hc_api("rate")) as answer:
            hc.get_rating_button("Helpful").click()

    assert sent.value.post_data_json == {"ticket_id": ticket["id"], "rating": "up"}
    assert answer.value.status == 200, answer.value.status
    expect(hc.get_rating_sheet()).to_have_count(0)
    expect(hc.get_rate_support()).to_have_count(0)

    saved, _ = ticket_details(page, ticket["id"])
    assert saved["my_rating"] == "up"
