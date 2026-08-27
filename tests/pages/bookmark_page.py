from pages.question_library_section_page import (
    BASE_URL,
    SectionPage,
    SectionQuestionsPage,
    SectionQuestionPage,
)


class BookmarkPage(SectionPage):
    """Bookmarks: the subject tabs and chapter list of the bookmarked
    questions, reached from the Question Library card.

    The card on the landing screen says Bookmarks; the screen itself and the
    question filters say Bookmark.
    """

    URL = f"{BASE_URL}/home/questionLibrary/contents/bookmark"

    def has_bookmarks(self):
        return self.has_questions()

    def get_chapter_bookmark_count(self, index):
        return self.get_chapter_question_count(index)


class BookmarkQuestionsPage(SectionQuestionsPage):
    """The bookmarked questions of one chapter.

    Every card carries the bookmark control, which here always starts on:
    turning it off is what removes the question from the section.
    """


class BookmarkQuestionPage(SectionQuestionPage):
    """A single bookmarked question."""
