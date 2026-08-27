class SubtopicPage:
    """The player screen a subtopic opens into.

    A subtopic is a sequence of items shown in the header strip: a video on its
    own ("video only"), or a video followed by a checkpoint quiz, sometimes
    introduced by a pretest screen."""

    def __init__(self, page):
        self.page = page

    # ---------- page ----------

    def open(self, url):
        self.page.goto(url)
        self.wait_for_player_loaded()

    def wait_for_player_loaded(self, timeout=30000):
        """The <video> element attaches before its metadata arrives, so wait for
        a real duration too - otherwise duration reads back as NaN."""
        self.page.locator("video.pl-video").wait_for(timeout=timeout)
        self.page.wait_for_function(
            "() => { const v = document.querySelector('video.pl-video');"
            " return v && Number.isFinite(v.duration) && v.duration > 0; }",
            timeout=timeout,
        )

    def get_page(self):
        return self.page.locator(".pl-page")

    def get_back_button(self):
        return self.page.locator(".pl-back")

    def click_back(self):
        self.get_back_button().click()

    def get_report_issue_button(self):
        return self.page.get_by_role("button", name="Report issue")

    # ---------- header strip ----------

    def get_strip(self):
        return self.page.locator(".pl-strip")

    def get_strip_items(self):
        return self.page.locator(".pl-strip-item")

    def get_strip_circles(self):
        return self.page.locator(".pl-strip-circle")

    def get_video_strip_items(self):
        return self.page.locator(".pl-strip-video")

    def get_quiz_strip_items(self):
        return self.page.locator(".pl-strip-quiz")

    def get_done_strip_items(self):
        return self.page.locator(".pl-strip-done")

    def get_current_strip_item(self):
        return self.page.locator(".pl-strip-current-ring")

    def is_video_only(self):
        """A video-only subtopic has exactly one item and no quiz in the strip."""
        return self.get_strip_items().count() == 1 and self.get_quiz_strip_items().count() == 0

    # ---------- video ----------

    def get_video(self):
        return self.page.locator("video.pl-video")

    def get_video_title(self):
        return self.page.locator(".pl-video-title")

    def get_player_container(self):
        return self.page.locator(".pl-player-container")

    def get_play_button(self):
        return self.page.locator(".plyr__control[data-plyr='play']").first

    def get_seek_slider(self):
        return self.page.locator("input[data-plyr='seek']")

    def get_volume_slider(self):
        return self.page.locator("input[data-plyr='volume']")

    def get_settings_button(self):
        return self.page.locator("button[data-plyr='settings']").first

    def get_fullscreen_button(self):
        return self.page.locator("button[data-plyr='fullscreen']")

    def get_duration(self):
        return self.get_video().evaluate("video => video.duration")

    # ---------- plyr controls ----------
    # Plyr hides its control bar a couple of seconds into playback, so anything
    # that clicks a control has to bring the bar back first.

    def get_plyr(self):
        return self.page.locator(".plyr").first

    CONTROLS_SHOWN = (
        "() => { const p = document.querySelector('.plyr');"
        " return p && !p.classList.contains('plyr--hide-controls'); }"
    )

    def show_controls(self, nudge=0):
        """Bring the control bar back and wait for it.

        The pointer is physically moved rather than hovered: hovering a spot it
        already occupies fires no event, so Plyr would leave the bar hidden.
        The nudge shifts the target slightly so repeat calls still move it."""
        box = self.get_plyr().bounding_box()
        self.page.mouse.move(
            box["x"] + box["width"] / 2,
            box["y"] + box["height"] / 2 + nudge,
        )
        self.page.wait_for_function(self.CONTROLS_SHOWN, timeout=8000)

    def click_control(self, locator):
        """Plyr hides the bar again on its own timer, so a control click can be
        overtaken between showing the bar and landing the click."""
        for attempt in range(3):
            try:
                self.show_controls(nudge=attempt * 6)
                locator.click(timeout=6000)
                return
            except Exception:
                continue
        raise AssertionError("a player control would not take a click")

    def get_overlaid_play_button(self):
        return self.page.locator(".plyr__control--overlaid")

    def get_current_time_display(self):
        return self.page.locator(".plyr__time--current")

    def get_mute_button(self):
        return self.page.locator("button[data-plyr='mute']")

    def get_settings_menu(self):
        return self.page.locator(".plyr__menu__container")

    def get_settings_submenu_buttons(self):
        """The Quality and Speed rows of the settings menu."""
        return self.page.locator("button[data-plyr='settings'].plyr__control--forward")

    def get_quality_options(self):
        return self.page.locator("button[data-plyr='quality']")

    def get_speed_options(self):
        return self.page.locator("button[data-plyr='speed']")

    # ---------- playback state ----------

    def get_playback_state(self):
        """Everything the <video> knows about itself, read in one hop."""
        return self.get_video().evaluate(
            "video => ({currentTime: video.currentTime, duration: video.duration,"
            " paused: video.paused, muted: video.muted, volume: video.volume,"
            " playbackRate: video.playbackRate})"
        )

    def get_current_time(self):
        return self.get_video().evaluate("video => video.currentTime")

    def is_paused(self):
        return self.get_video().evaluate("video => video.paused")

    def is_muted(self):
        return self.get_video().evaluate("video => video.muted")

    def get_volume(self):
        return self.get_video().evaluate("video => video.volume")

    def get_playback_rate(self):
        return self.get_video().evaluate("video => video.playbackRate")

    def wait_until_playing(self, timeout=15000):
        self.page.wait_for_function(
            "() => { const v = document.querySelector('video.pl-video');"
            " return v && !v.paused && v.currentTime > 0; }",
            timeout=timeout,
        )

    def wait_for_time_past(self, seconds, timeout=20000):
        self.page.wait_for_function(
            "target => { const v = document.querySelector('video.pl-video');"
            " return v && v.currentTime > target; }",
            arg=seconds,
            timeout=timeout,
        )

    # ---------- play / pause ----------

    def click_play_toggle(self):
        self.click_control(self.get_play_button())

    def pause(self):
        self._toggle_until_paused(True)

    def play(self):
        self._toggle_until_paused(False)

    def _toggle_until_paused(self, paused):
        """A video that is still buffering reports itself paused for a moment
        and then plays on, so the state is confirmed after settling rather than
        trusted the instant it reads right."""
        condition = "v.paused" if paused else "!v.paused"
        for _ in range(3):
            if self.is_paused() != paused:
                self.click_play_toggle()
            try:
                self.page.wait_for_function(
                    "() => { const v = document.querySelector('video.pl-video');"
                    f" return v && {condition}; }}",
                    timeout=5000,
                )
            except Exception:
                continue
            self.page.wait_for_timeout(500)
            if self.is_paused() == paused:
                return
        raise AssertionError(
            f"the video would not stay {'paused' if paused else 'playing'}"
        )

    # ---------- volume and mute ----------

    def set_volume(self, level):
        """Drive the slider rather than the media element, so the player keeps
        its own state in step."""
        self.show_controls()
        self.get_volume_slider().fill(str(level))
        self.page.wait_for_timeout(400)

    def click_mute(self):
        self.click_control(self.get_mute_button())
        self.page.wait_for_timeout(400)

    # ---------- settings, quality and speed ----------

    def open_settings(self):
        if self.get_settings_button().get_attribute("aria-expanded") != "true":
            self.click_control(self.get_settings_button())
            self.page.wait_for_timeout(500)

    def close_settings(self):
        if self.get_settings_button().get_attribute("aria-expanded") == "true":
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(300)

    def get_menu_back_buttons(self):
        return self.page.locator("button.plyr__control--back")

    def return_to_main_menu(self):
        """Reopening the settings lands back in whichever submenu was open last,
        so step out of it before looking for a row on the main pane."""
        back_buttons = self.get_menu_back_buttons()
        for index in range(back_buttons.count()):
            if back_buttons.nth(index).is_visible():
                back_buttons.nth(index).click()
                self.page.wait_for_timeout(300)
                return

    def open_submenu(self, name):
        """name is Quality or Speed.

        The settings menu can be sitting on any pane, and closing it does not
        always reset that, so this works back to a known state rather than
        assuming the row is on screen."""
        row = self.get_settings_submenu_buttons().filter(has_text=name)
        for _ in range(3):
            self.open_settings()
            if not row.is_visible():
                self.return_to_main_menu()
            if row.is_visible():
                row.click()
                self.page.wait_for_timeout(500)
                return
            self.close_settings()
        raise AssertionError(f"the {name} menu would not open")

    def click_menu_option(self, kind, value):
        """kind is quality or speed; wait for the option to be on screen rather
        than clicking into a pane that is still sliding in."""
        option = self.page.locator(f"button[data-plyr='{kind}'][value='{value}']")
        option.wait_for(state="visible", timeout=8000)
        option.click()

    def get_submenu_value(self, name):
        """What the settings menu reports as the current Quality or Speed."""
        self.open_settings()
        row = self.get_settings_submenu_buttons().filter(has_text=name)
        return row.inner_text().replace(name, "").strip()

    def get_quality_labels(self):
        self.open_submenu("Quality")
        return [text.strip() for text in self.get_quality_options().all_inner_texts()]

    def get_speed_labels(self):
        self.open_submenu("Speed")
        return [text.strip() for text in self.get_speed_options().all_inner_texts()]

    def select_quality(self, value):
        """value is the option's value attribute: 0 for Auto, else 720, 480 ..."""
        self.open_submenu("Quality")
        self.click_menu_option("quality", value)
        self.page.wait_for_timeout(1500)

    def select_speed(self, value):
        """value is the option's value attribute: 1 for Normal, 1.5, 2 ..."""
        self.open_submenu("Speed")
        self.click_menu_option("speed", value)
        self.page.wait_for_timeout(800)

    # ---------- fullscreen ----------

    def click_fullscreen(self):
        self.click_control(self.get_fullscreen_button())
        self.page.wait_for_timeout(1200)

    def is_fullscreen(self):
        return self.page.evaluate("() => document.fullscreenElement !== null")

    def seek_to(self, seconds):
        self.get_video().evaluate(
            "(video, t) => { video.currentTime = t; video.play(); }", seconds
        )

    def seek_to_end(self):
        """Jump to the last seconds so the video finishes without waiting it out."""
        self.seek_to(max(self.get_duration() - 3, 0))

    def get_replay_overlay(self):
        return self.page.locator(".pl-replay-overlay")

    def get_replay_label(self):
        return self.page.locator(".pl-replay-label")

    # ---------- actions ----------

    def get_action_buttons(self):
        return self.page.locator(".pl-action-btn")

    def get_notes_link(self):
        return self.page.locator("a.pl-action-btn")

    def get_rate_now_button(self):
        """Labelled "Rate Now" until the lesson is rated, then the rating itself
        ("Good"), so match the icon rather than the text."""
        return self.page.locator(".pl-action-btn:has(.pl-action-rate)")

    def get_rating_panel(self):
        return self.page.locator(".pl-rating-panel")

    def get_rating_options(self):
        return self.page.locator(".pl-rating-options .pl-rating-opt-label")

    def get_continue_button(self):
        return self.page.locator(".pl-proceed-btn")

    def click_continue(self):
        self.get_continue_button().click()

    # ---------- pretest ----------

    def get_pretest_intro(self):
        return self.page.locator(".pl-pretest-intro")

    def get_pretest_title(self):
        return self.page.locator(".pl-pretest-title")

    def get_pretest_points(self):
        return self.page.locator(".pl-pretest-point")

    def get_pretest_button(self):
        return self.page.locator(".pl-pretest-btn")

    def click_pretest_button(self):
        self.get_pretest_button().click()

    # ---------- checkpoint quiz ----------

    def get_quiz_card(self):
        return self.page.locator(".pl-quiz-card")

    def get_quiz_question(self):
        return self.page.locator(".pl-quiz-question")

    def get_quiz_options(self):
        return self.page.locator(".pl-quiz-option")

    def get_quiz_option(self, index):
        return self.get_quiz_options().nth(index)

    def get_quiz_option_letters(self):
        return self.page.locator(".pl-quiz-letter")

    def select_quiz_option(self, index):
        self.get_quiz_option(index).click()

    def get_quiz_solution(self):
        return self.page.locator(".pl-quiz-solution")

    def get_quiz_solution_title(self):
        return self.page.locator(".pl-quiz-solution-title")

    def get_quiz_bookmark(self):
        return self.page.locator(".pl-quiz-bookmark")

    def get_question_palette(self):
        return self.page.locator(".pl-palette-sheet")

    def get_palette_cells(self):
        return self.page.locator(".pl-palette-grid > *")

    # ---------- completion ----------

    def get_complete_overlay(self):
        return self.page.locator(".pl-complete-overlay")

    def get_complete_title(self):
        return self.page.locator(".pl-complete-title")

    def get_complete_next_button(self):
        return self.page.locator(".pl-complete-next")


class MiniPlayer:
    """The floating tile that keeps the last opened video reachable from any
    page once you leave the player."""

    def __init__(self, page):
        self.page = page

    def get_tile(self):
        return self.page.locator(".mp-tile")

    def is_visible(self):
        return self.get_tile().count() > 0

    def get_title(self):
        return self.page.locator(".mp-title")

    def get_type(self):
        return self.page.locator(".mp-type")

    def get_play_icon(self):
        return self.page.locator(".mp-play")

    def get_close_button(self):
        return self.page.get_by_role("button", name="Close mini player")

    def click(self):
        self.get_tile().click()

    def close(self):
        self.get_close_button().click()

    def get_back_to_video_button(self):
        return self.page.get_by_role("button", name="Back to video")
