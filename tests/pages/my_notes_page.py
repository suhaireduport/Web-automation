from pages.question_library_section_page import (
    BASE_URL,
    SectionPage,
    SectionQuestionsPage,
    SectionQuestionPage,
)


class MyNotesPage(SectionPage):
    """My Notes: the subject tabs and chapter list reached from Question
    Library.

    The screen is the one every Question Library section uses, so only the URL
    and the wording of its counts belong here.
    """

    URL = f"{BASE_URL}/home/questionLibrary/contents/note"

    def has_notes(self):
        return self.has_questions()

    def get_chapter_note_count(self, index):
        return self.get_chapter_question_count(index)


class NoteQuestionsPage(SectionQuestionsPage):
    """The questions of one chapter, each shown with a preview of its note."""


class NoteQuestionPage(SectionQuestionPage):
    """A single question opened from My Notes."""
