class LoginPage:
    def __init__(self,page):
        self.page = page
        
    def enter_mobile(self, mobile_number):
        self.page.locator("input").fill(mobile_number)


    def click_continue(self):
        self.page.get_by_role("button", name="Continue").click()


    def login(self, mobile_number):
        self.enter_mobile(mobile_number)
        self.click_continue()

    def get_continue_button(self):
        return self.page.get_by_role("button", name="Continue")