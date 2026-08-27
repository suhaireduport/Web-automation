class DoubtChatPage:
    """The AI Doubt Clearance chat at /ai/doubt-clearance.

    Reached from the Adapt AI floating button on Home. Messages can be plain
    text, a text plus an attached image, or a voice recording."""

    URL = "https://eduport-react.pages.dev/ai/doubt-clearance"

    def __init__(self, page):
        self.page = page

    # ---------- opening ----------

    def open(self):
        self.page.goto(self.URL)
        self.wait_for_chat_loaded()

    def get_ai_button(self):
        return self.page.locator("button.hp-ai-fab")

    def open_from_home(self):
        """The Adapt AI button opens this chat directly. It used to show a
        chooser with an Ai Virtual Teacher card first; that step is gone."""
        self.get_ai_button().wait_for()
        self.get_ai_button().click()
        self.wait_for_chat_loaded()

    def wait_for_chat_loaded(self):
        self.page.locator(".aid-input").wait_for()

    def get_page(self):
        return self.page.locator(".aid-page")

    # ---------- header ----------

    def get_header(self):
        return self.page.locator(".aid-header")

    def get_header_title(self):
        return self.page.locator(".aid-header-title")

    def get_beta_badge(self):
        return self.page.locator(".aid-header-beta")

    def get_header_buttons(self):
        return self.page.locator(".aid-header-btn")

    def get_back_button(self):
        return self.get_header_buttons().nth(0)

    def click_back(self):
        self.get_back_button().click()

    def get_menu_button(self):
        return self.get_header_buttons().nth(1)

    def toggle_menu(self):
        self.get_menu_button().click()

    # ---------- landing content ----------

    def get_greeting(self):
        return self.page.locator(".aid-greeting")

    def get_suggestion_chips(self):
        return self.page.locator(".aid-chip")

    def click_suggestion_chip(self, index=0):
        self.get_suggestion_chips().nth(index).click()

    def get_disclaimer(self):
        return self.page.locator(".aid-disclaimer")

    # ---------- conversation sidebar ----------

    def get_sidebar(self):
        return self.page.locator(".aid-sidebar")

    def get_sidebar_toggle(self):
        """The conversation list is collapsed until the header menu is used.
        This is the second header button; the first one is Back."""
        return self.get_menu_button()

    def open_sidebar(self):
        if not self.get_new_chat_button().is_visible():
            self.get_sidebar_toggle().click()
            self.get_new_chat_button().wait_for()

    def get_sidebar_overlay(self):
        return self.page.locator(".aid-sidebar-overlay")

    def close_sidebar(self):
        """The header menu button is unmounted while the sidebar is open, so the
        panel closes by tapping the overlay beside it rather than by toggling."""
        box = self.get_sidebar_overlay().bounding_box()
        self.page.mouse.click(box["x"] + box["width"] - 20, box["y"] + box["height"] / 2)

    def is_sidebar_open(self):
        classes = self.get_sidebar().get_attribute("class") or ""
        return "aid-sidebar-open" in classes

    def get_sidebar_search(self):
        return self.page.locator(".aid-sidebar-search-input")

    def get_new_chat_button(self):
        return self.page.locator(".aid-sidebar-new")

    def start_new_chat(self):
        self.get_new_chat_button().click()

    def get_sidebar_items(self):
        return self.page.locator(".aid-sidebar-item-wrap")

    def get_sidebar_item(self, index):
        return self.get_sidebar_items().nth(index)

    def get_sidebar_item_titles(self):
        return self.page.locator(".aid-sidebar-item-title")

    def get_sidebar_item_title(self, index):
        return self.get_sidebar_item(index).locator(".aid-sidebar-item-title")

    def get_sidebar_months(self):
        return self.page.locator(".aid-sidebar-month")

    def open_conversation(self, index):
        self.get_sidebar_item(index).locator(".aid-sidebar-item").click()

    # ---------- searching conversations ----------

    def search_conversations(self, text):
        self.get_sidebar_search().fill(text)

    def clear_conversation_search(self):
        self.get_sidebar_search().fill("")

    # ---------- per conversation menu ----------

    def get_item_menu_buttons(self):
        return self.page.locator(".aid-sidebar-item-menu")

    def open_item_menu(self, index):
        self.get_item_menu_buttons().nth(index).click()

    def get_context_menu(self):
        return self.page.locator(".aid-ctx-menu")

    def get_context_menu_items(self):
        return self.page.locator(".aid-ctx-item")

    def get_rename_option(self):
        return self.get_context_menu_items().filter(has_text="Rename")

    def get_delete_option(self):
        return self.page.locator(".aid-ctx-delete")

    # ---------- renaming a conversation ----------

    def get_rename_modal(self):
        return self.page.locator(".aid-rename-modal")

    def get_rename_input(self):
        return self.page.locator(".aid-rename-input")

    def get_rename_save_button(self):
        return self.page.locator(".aid-rename-save")

    def get_rename_cancel_button(self):
        return self.page.locator(".aid-rename-cancel")

    def open_rename_dialog(self, index):
        self.open_item_menu(index)
        self.get_rename_option().click()
        self.get_rename_modal().wait_for()

    def rename_conversation(self, index, new_title):
        self.open_rename_dialog(index)
        self.get_rename_input().fill(new_title)
        self.get_rename_save_button().click()

    def cancel_rename(self):
        self.get_rename_cancel_button().click()

    def get_sidebar_empty_message(self):
        return self.page.locator(".aid-sidebar-empty")

    # ---------- input bar ----------

    def get_input(self):
        return self.page.locator(".aid-input")

    def get_placeholder(self):
        return self.page.locator(".aid-placeholder")

    def get_input_buttons(self):
        return self.page.locator(".aid-input-btn")

    def get_attach_button(self):
        return self.get_input_buttons().first

    def get_mic_button(self):
        return self.get_input_buttons().last

    def type_message(self, text):
        self.get_input().fill(text)

    def send_message(self, text):
        self.type_message(text)
        self.get_input().press("Enter")

    # ---------- messages ----------

    def get_chat_list(self):
        return self.page.locator(".aid-chat-list")

    def get_messages(self):
        return self.page.locator(".aid-msg")

    def get_user_messages(self):
        return self.page.locator(".aid-msg-user")

    def get_ai_messages(self):
        return self.page.locator(".aid-msg-ai")

    def get_last_ai_message(self):
        return self.get_ai_messages().last

    def get_message_texts(self):
        return self.page.locator(".aid-msg-text")

    def get_ai_message_bodies(self):
        return self.page.locator(".aid-msg-md")

    def get_message_images(self):
        return self.page.locator(".aid-msg-img")

    def get_thinking_indicator(self):
        return self.page.locator(".aid-thinking")

    def wait_for_reply(self, timeout=90000):
        """The reply is streamed, so wait for a bubble and for the thinking dots
        to disappear."""
        self.get_ai_messages().first.wait_for(timeout=timeout)
        self.page.wait_for_function(
            "() => document.querySelectorAll('.aid-thinking').length === 0",
            timeout=timeout,
        )

    # ---------- reply feedback ----------

    def get_feedback_row(self):
        return self.page.locator(".aid-feedback")

    def get_like_button(self):
        # exact=True matters: role-name matching is substring based, so "Like"
        # would also match the "Dislike" button.
        return self.page.get_by_role("button", name="Like", exact=True)

    def get_dislike_button(self):
        return self.page.get_by_role("button", name="Dislike", exact=True)

    # ---------- image attachment ----------

    def click_attach(self):
        self.get_attach_button().click()

    def get_attach_sheet(self):
        return self.page.locator(".aid-attach-sheet")

    def get_attach_title(self):
        return self.page.locator(".aid-attach-title")

    def get_attach_options(self):
        return self.page.locator(".aid-attach-option")

    def get_file_input(self):
        return self.page.locator("input[type=file]")

    def attach_image(self, file_path):
        """The file input is hidden, so set it directly rather than clicking
        through the OS picker."""
        self.click_attach()
        self.get_attach_sheet().wait_for()
        self.get_file_input().set_input_files(file_path)
        self.get_image_preview().wait_for()

    def get_image_preview(self):
        return self.page.locator(".aid-img-preview")

    def get_image_uploading(self):
        return self.page.locator(".aid-img-uploading")

    def get_remove_image_button(self):
        return self.page.locator(".aid-img-remove")

    def remove_attached_image(self):
        self.get_remove_image_button().click()

    # ---------- voice recording ----------

    def start_recording(self):
        self.get_mic_button().click()

    def is_recording(self):
        return self.get_recording_time().count() > 0

    def get_recording_time(self):
        return self.page.locator(".aid-rec-time")

    def get_recording_wave(self):
        return self.page.locator(".aid-rec-wave")

    def get_recording_bars(self):
        return self.page.locator(".aid-rec-bar")

    def get_stop_recording_button(self):
        return self.page.locator(".aid-rec-stop")

    def get_delete_recording_button(self):
        return self.page.locator(".aid-rec-delete")

    def stop_recording(self):
        self.get_stop_recording_button().click()

    def wait_for_transcript(self, timeout=60000):
        """Stopping a recording transcribes the speech into the text input.
        It is not sent automatically: the transcript still has to be submitted."""
        self.page.wait_for_function(
            "() => { const input = document.querySelector('.aid-input');"
            " return input && input.value.trim().length > 0; }",
            timeout=timeout,
        )

    def get_transcript(self):
        return self.get_input().input_value().strip()

    def delete_recording(self):
        self.get_delete_recording_button().click()
