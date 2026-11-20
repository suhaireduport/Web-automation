"""The Help Center: FAQs, raising a ticket, and following a ticket's replies.

It opens two ways and draws the same thing in both:

- from the Profile page's Help Center card, as a modal dialog (dialog.hc-dialog)
  over the page, closed with the X, Escape or a click on the backdrop;
- by URL at /help-center or /help-center/tickets/<id> (/help-desk is an alias),
  as a full page (main.hc-page); closing it there goes to home.

Either way the content is one .hc-app with a header (Back, the view's title,
Close) and a stack of views. Only the top view is shown; the ones under it stay
mounted but hidden, which is why every locator here goes through
get_view() - the hidden views carry the same classes.

The Help Center has its own backend, separate from the main API: HC_API_BASE.
Every call carries the app's sign-in token and the student's EPS id, so
hc_call() can read the same answers from inside the page that the screen is
drawn from.
"""
import json
import re

from playwright.sync_api import expect

HC_API_BASE = "https://helpcenter-test-amber.vercel.app/api/app"
HC_HOST = "helpcenter-test-amber.vercel.app"

AUTH_TOKEN_KEY = "eduport_auth_token"
STUDENT_ID_KEY = "unique_student_id"

# The header title of each view.
TITLES = {
    "home": "Help Center",
    "raise": "Raise a ticket",
    "tickets": "My tickets",
    "faqs": "FAQs",
    "faq": "FAQ",
    "ticket": "Ticket details",
}

# Statuses after which a ticket takes no more replies.
FINISHED_STATUSES = {
    "resolved",
    "cannot_be_solved",
    "cancelled",
    "closed",
    "suggestion",
    "merged",
}

# The status chip's colour class, keyed on the ticket's status.
def status_kind(status):
    if status in ("awaiting_reply", "awaiting_student"):
        return "waiting"
    if status == "resolved":
        return "resolved"
    if status in ("open", "in_progress"):
        return "open"
    return "finished"


def hc_api(path):
    """A predicate matching one Help Center endpoint, with or without a query
    string. It takes a request or response (expect_request, expect_response)
    or a bare URL (page.route hands its matcher the URL string)."""
    pattern = re.compile(re.escape(HC_HOST) + r"/api/app/" + re.escape(path) + r"(\?|$)")
    return lambda r: bool(pattern.search(r if isinstance(r, str) else r.url))


def hc_call(page, path, body=None):
    """Ask the Help Center backend from inside the page, with the student's own
    credentials, and return (status, json)."""
    return page.evaluate(
        """async ([base, tokenKey, idKey, path, body]) => {
            const headers = {
                Authorization: 'Token ' + localStorage.getItem(tokenKey),
                'X-EPS-ID': localStorage.getItem(idKey),
                Accept: 'application/json',
            };
            const init = {headers};
            if (body !== null) {
                init.method = 'POST';
                headers['Content-Type'] = 'application/json';
                init.body = JSON.stringify(body);
            }
            const r = await fetch(base + path, init);
            const text = await r.text();
            let data = null;
            try { data = JSON.parse(text); } catch (e) { data = text; }
            return [r.status, data];
        }""",
        [HC_API_BASE + "/", AUTH_TOKEN_KEY, STUDENT_ID_KEY, path.lstrip("/"), body],
    )


def hc_get(page, path):
    status, data = hc_call(page, path)
    assert status == 200, f"Help Center {path} answered {status}: {data}"
    return data


def patch_response(page, path, change):
    """Serve one Help Center endpoint with its real answer, changed by change().

    For states the backend cannot be put into on demand, such as a ticket
    waiting on the student, or a finished ticket with no rating. Nothing is sent anywhere it
    would not have gone; only what the screen is told is altered."""

    def handle(route):
        # The calls carry an Authorization header, so the browser asks first
        # with a CORS preflight; that one passes through untouched.
        if route.request.method == "OPTIONS":
            route.continue_()
            return
        response = route.fetch()
        data = response.json()
        change(data)
        route.fulfill(response=response, body=json.dumps(data))

    page.route(hc_api(path), handle)


class HelpCenterPage:
    def __init__(self, page):
        self.page = page

    # ---------- shell ----------

    def get_dialog(self):
        return self.page.locator("dialog.hc-dialog")

    def get_full_page(self):
        return self.page.locator("main.hc-page")

    def get_app(self):
        return self.page.locator(".hc-app")

    def get_header(self):
        return self.get_app().locator(".hc-header")

    def get_title(self):
        return self.get_header().locator("h1")

    def get_back(self):
        return self.get_header().get_by_role("button", name="Back")

    def get_close(self):
        return self.get_header().get_by_role("button", name="Close Help Center")

    def go_back(self):
        self.get_back().click()

    def close(self):
        self.get_close().click()

    def get_view(self, kind=None):
        """The view on top. Hidden views stay mounted with the same classes."""
        selector = f".hc-view-{kind}" if kind else ".hc-view"
        return self.get_app().locator(f"{selector}:not([hidden])")

    def wait_for_view(self, kind, timeout=30000):
        expect(self.get_view(kind)).to_be_visible(timeout=timeout)
        expect(self.get_title()).to_have_text(TITLES[kind])

    def wait_for_home(self, timeout=30000):
        self.wait_for_view("home", timeout)
        self.get_view("home").locator(".hc-section-heading").first.wait_for(timeout=timeout)

    # ---------- home ----------

    def get_hero(self):
        return self.get_view().locator(".hc-hero")

    def get_hero_raise(self):
        return self.get_hero().get_by_role("button", name="Raise a ticket")

    def get_home_sections(self):
        return self.get_view("home").locator(".hc-section-heading h2")

    def get_featured_faqs(self):
        return self.get_view("home").locator(".hc-featured-faqs .hc-faq-row")

    def get_see_all_faqs(self):
        return self.get_view("home").get_by_role("button", name="See all")

    def get_view_all_tickets(self):
        return self.get_view("home").get_by_role("button", name="View all")

    def get_home_tickets(self):
        return self.get_view("home").locator(".hc-ticket-card")

    def open_raise(self):
        self.get_hero_raise().click()
        self.wait_for_view("raise")

    def open_all_faqs(self):
        self.get_see_all_faqs().click()
        self.wait_for_view("faqs")

    def open_all_tickets(self):
        self.get_view_all_tickets().click()
        self.wait_for_view("tickets")

    # ---------- ticket cards (home and My tickets) ----------

    @staticmethod
    def card_number(card):
        return card.locator(".hc-ticket-number")

    @staticmethod
    def card_status(card):
        return card.locator(".hc-status")

    @staticmethod
    def card_title(card):
        return card.locator("strong")

    @staticmethod
    def card_category(card):
        return card.locator(".hc-ticket-meta span")

    def get_ticket_card(self, ticket_no):
        return self.get_view().locator(".hc-ticket-card").filter(
            has=self.page.locator(".hc-ticket-number", has_text=re.compile(rf"^{re.escape(ticket_no)}$"))
        )

    # ---------- FAQs ----------

    def get_search(self):
        return self.get_view("faqs").get_by_role("searchbox", name="Search FAQs")

    def search(self, text):
        self.get_search().fill(text)

    def get_search_cancel(self):
        return self.get_view("faqs").get_by_role("button", name="Clear search")

    def get_search_back(self):
        return self.get_view("faqs").get_by_role("button", name="Back to FAQs")

    def get_topic_tabs(self):
        return self.get_view("faqs").locator(".hc-tabs .hc-tab")

    def get_topic_tab(self, name):
        return self.get_view("faqs").locator(".hc-tabs").get_by_role("button", name=name, exact=True)

    def get_faq_rows(self):
        return self.get_view("faqs").locator(".hc-faq-row")

    def get_faq_questions(self):
        """The question on each row, without the topic shown under it in
        search results."""
        return [
            t.strip()
            for t in self.get_faq_rows().evaluate_all(
                "els => els.map(e => e.querySelector(':scope > span > span').textContent)"
            )
        ]

    def get_faq_topics_shown(self):
        return [t.strip() for t in self.get_faq_rows().locator(".hc-faq-topic").all_inner_texts()]

    def get_faq_loading(self):
        return self.get_view("faqs").locator(".hc-loading")

    def get_faq_empty(self):
        return self.get_view("faqs").locator(".hc-empty")

    def open_faq_row(self, question):
        self.get_view().locator(".hc-faq-row").filter(has_text=question).first.click()
        self.wait_for_view("faq")
        self.get_faq_detail().wait_for()

    # ---------- one FAQ ----------

    def get_faq_detail(self):
        return self.get_view("faq").locator(".hc-faq-detail")

    def get_faq_question(self):
        return self.get_faq_detail().locator("h2")

    def get_faq_meta(self):
        return self.get_faq_detail().locator("p.hc-faq-meta").first

    def get_faq_answer(self):
        return self.get_faq_detail().locator(".hc-faq-answer")

    def get_helpful(self):
        return self.get_faq_detail().locator(".hc-feedback-actions").get_by_role("button", name="Helpful")

    def get_not_resolved(self):
        return self.get_faq_detail().locator(".hc-feedback-actions").get_by_role("button", name="Not resolved")

    def get_feedback_thanks(self):
        return self.get_faq_detail().get_by_role("status").filter(has_text="Thanks for your feedback.")

    def get_still_need_help(self):
        return self.get_faq_detail().locator(".hc-faq-cta")

    # ---------- raise a ticket ----------

    def get_categories(self):
        return self.get_view("raise").locator(".hc-category")

    def get_category_labels(self):
        """Each option's own label, without its help text."""
        return [
            t.strip()
            for t in self.get_categories().evaluate_all(
                "els => els.map(e => e.querySelector('span').firstChild.textContent)"
            )
        ]

    def choose_category(self, label):
        self.get_categories().filter(
            has=self.page.locator("span", has_text=re.compile(rf"^{re.escape(label)}"))
        ).first.click()

    def get_continue(self):
        return self.get_view("raise").get_by_role("button", name="Continue")

    def continue_(self):
        self.get_continue().click()

    def get_issue_path(self):
        return [t.strip() for t in self.get_view("raise").locator(".hc-issue-path li").all_inner_texts()]

    def get_change(self):
        return self.get_view("raise").locator(".hc-selected-category").get_by_role("button", name="Change")

    def get_description(self):
        return self.get_view("raise").locator("#hc-description")

    def get_description_counter(self):
        return self.get_view("raise").locator(".hc-field-hint small").last

    def get_file_input(self, scope=None):
        return (scope or self.get_view()).locator("input.hc-file-input")

    def attach(self, name, mime_type, data, scope=None):
        self.get_file_input(scope).set_input_files(
            {"name": name, "mimeType": mime_type, "buffer": data}
        )

    def get_attachment_picker(self, scope=None):
        return (scope or self.get_view()).locator(".hc-attachment-picker")

    def get_attachment_preview(self, scope=None):
        return (scope or self.get_view()).locator(".hc-attachment-preview")

    def get_attachment_error(self, scope=None):
        return (scope or self.get_view()).locator(".hc-attachment-field .hc-field-error")

    def get_submit(self):
        return self.get_view("raise").get_by_role("button", name=re.compile(r"Submit ticket|Sending ticket"))

    def get_raise_error(self):
        return self.get_view("raise").locator(".hc-raise-content > .hc-error")

    def get_success(self):
        return self.get_view("raise").locator(".hc-success")

    def get_success_summary(self):
        """The Ticket ID / Issue / Status list, as {label: value}."""
        rows = self.get_success().locator(".hc-summary > div")
        return {
            row.locator("dt").inner_text().strip(): row.locator("dd").inner_text().strip()
            for row in rows.all()
        }

    # ---------- My tickets ----------

    def get_filter(self, name):
        return self.get_view("tickets").locator(".hc-filter-tabs").get_by_role(
            "button", name=re.compile(rf"^{name}\b")
        )

    def get_list_tickets(self):
        return self.get_view("tickets").locator(".hc-ticket-card")

    def get_list_numbers(self):
        return [t.strip() for t in self.get_list_tickets().locator(".hc-ticket-number").all_inner_texts()]

    def get_load_more(self):
        return self.get_view("tickets").get_by_role("button", name=re.compile("Load more tickets|Loading"))

    # ---------- one ticket ----------

    def get_ticket_detail(self):
        return self.get_view("ticket").locator(".hc-ticket-detail")

    def wait_for_ticket(self, timeout=30000):
        self.wait_for_view("ticket", timeout)
        self.get_ticket_detail().wait_for(timeout=timeout)

    def get_ticket_created(self):
        return self.get_ticket_detail().locator(".hc-ticket-created")

    def get_ticket_heading(self):
        return self.get_ticket_created().locator(".hc-ticket-top strong")

    def get_ticket_status(self):
        return self.get_ticket_created().locator(".hc-status")

    def get_ticket_category(self):
        return self.get_ticket_created().locator(".hc-category-tag")

    def get_ticket_title(self):
        return self.get_ticket_created().locator("p")

    def get_messages(self):
        return self.get_ticket_detail().locator(".hc-message-row")

    def get_student_messages(self):
        return self.get_ticket_detail().locator(".hc-message-row.hc-message-student")

    def get_support_messages(self):
        return self.get_ticket_detail().locator(".hc-message-row:not(.hc-message-student)")

    def get_screenshots(self):
        return self.get_ticket_detail().locator(".hc-image-attachment")

    def get_resolved_footer(self):
        return self.get_ticket_detail().locator("footer.hc-resolved")

    def get_reply_notice(self):
        return self.get_ticket_detail().locator("footer.hc-reply-notice")

    def get_composer(self):
        return self.get_ticket_detail().locator("form.hc-composer")

    def get_reply_box(self):
        return self.get_composer().get_by_role("textbox", name="Reply to support")

    def get_send_reply(self):
        return self.get_composer().get_by_role("button", name="Send reply")

    def get_rate_support(self):
        return self.get_ticket_detail().get_by_role("button", name="Rate support")

    # ---------- support rating sheet ----------

    def get_rating_sheet(self):
        return self.page.locator("dialog.hc-rating-dialog")

    def get_rating_close(self):
        return self.get_rating_sheet().get_by_role("button", name="Close support rating")

    def get_rating_button(self, label):
        return self.get_rating_sheet().get_by_role("button", name=label, exact=True)

    def dismiss_rating_if_open(self, wait=1500):
        """The sheet opens by itself on a finished, unrated ticket; tests that
        are not about it close it."""
        try:
            self.get_rating_sheet().wait_for(timeout=wait)
        except Exception:
            return
        self.get_rating_close().click()
        expect(self.get_rating_sheet()).to_have_count(0)

    # ---------- image viewer ----------

    def get_image_viewer(self):
        return self.page.locator("dialog.hc-image-viewer")

    def get_viewer_title(self):
        return self.get_image_viewer().locator(".hc-image-viewer-header h2")

    def get_viewer_image(self):
        return self.get_image_viewer().locator("img.hc-image-viewer-image")

    def get_viewer_close(self):
        return self.get_image_viewer().get_by_role("button", name="Close image preview")

    def get_zoom_level(self):
        return self.get_image_viewer().get_by_label("Zoom level")

    def get_zoom_in(self):
        return self.get_image_viewer().get_by_role("button", name="Zoom in")

    def get_zoom_out(self):
        return self.get_image_viewer().get_by_role("button", name="Zoom out")

    def get_fit_image(self):
        return self.get_image_viewer().get_by_role("button", name="Fit image")

    def get_original_size(self):
        return self.get_image_viewer().get_by_role("button", name="Original size")

    def zoom_percent(self):
        text = self.get_zoom_level().inner_text().strip()
        assert text.endswith("%"), f"zoom level reads {text!r}"
        return int(text[:-1])

    def wait_for_image_loaded(self, timeout=30000):
        self.page.wait_for_function(
            "() => { const img = document.querySelector('dialog.hc-image-viewer img.hc-image-viewer-image');"
            " return img && img.complete && img.naturalWidth > 0; }",
            timeout=timeout,
        )
        expect(self.get_zoom_level()).to_have_text(re.compile(r"^\d+%$"))
