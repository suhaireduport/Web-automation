BASE_URL = "https://eduport-react.pages.dev"


class SubscriptionPage:
    """The subscriptions the account holds, reached from the profile menu.

    One card per subscription: the course it belongs to over the plan itself,
    with the expiry date and a status badge under a divider.
    """

    URL = f"{BASE_URL}/subscriptions"

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def get_page(self):
        return self.page.locator(".sub-page")

    def get_title(self):
        return self.page.locator(".sub-title")

    def get_back_button(self):
        return self.page.locator(".sub-back")

    def click_back(self):
        self.get_back_button().click()

    def wait_for_loaded(self):
        """The heading renders with the shell; the cards arrive with the answer."""
        self.get_title().wait_for()

    # ---------- cards ----------

    def get_cards(self):
        return self.page.locator(".sub-card")

    def card_count(self, timeout=10000):
        """count() does not auto-wait, and the cards arrive after the shell."""
        try:
            self.get_cards().first.wait_for(timeout=timeout)
        except Exception:
            return 0
        return self.get_cards().count()

    def get_card(self, index):
        return self.get_cards().nth(index)

    def get_courses(self):
        return self.page.locator(".sub-course")

    def get_course(self, index):
        return self.get_courses().nth(index)

    def get_plans(self):
        return self.page.locator(".sub-class")

    def get_plan(self, index):
        return self.get_plans().nth(index)

    def get_expiries(self):
        return self.page.locator(".sub-expiry")

    def get_expiry(self, index):
        return self.get_expiries().nth(index)

    def get_badges(self):
        return self.page.locator(".sub-badge")

    def get_badge(self, index):
        return self.get_badges().nth(index)
