class OtpPage:
    def __init__(self,page):
        self.page = page

    def enter_otp(self, otp):
        for i in range(len(otp)):
            self.page.locator("input").nth(i).fill(otp[i])

    def get_continue_button(self):
            return self.page.get_by_role("button", name="Continue")    

    def get_invalid_otp_message(self):
        return self.page.get_by_text("Invalid OTP. Please try again.")

    def get_resend_otp_sms(self):
        return self.page.get_by_role("button", name="Resend via SMS")    

    def get_resend_otp_whatsapp(self):
            return self.page.get_by_role("button", name="Resend via WhatsApp")   

    def click_resend_otp_sms(self):
        self.get_resend_otp_sms().click()

    def click_resend_otp_whatsapp(self):
        self.get_resend_otp_whatsapp().click()

    def get_resend_otp_sms_popup(self):
            return self.page.get_by_text("OTP resent via SMS") 

    def get_resend_otp_whatsapp_popup(self):
                return self.page.get_by_text("OTP sent via WhatsApp") 
    