from pages.question_library_section_page import (
    BASE_URL,
    SectionPage,
    SectionQuestionsPage,
    SectionQuestionPage,
)


class MistakeBookPage(SectionPage):
    """Mistake Book: the subject tabs and chapter list of the questions that
    were answered wrong, reached from the Question Library card."""

    URL = f"{BASE_URL}/home/questionLibrary/contents/mistakebook"

    def has_mistakes(self):
        return self.has_questions()

    def get_chapter_mistake_count(self, index):
        return self.get_chapter_question_count(index)


class MistakeQuestionsPage(SectionQuestionsPage):
    """The mistaken questions of one chapter.

    These cards carry one control the other sections do not: a Remove from
    Mistake Book button beside the bookmark.
    """


class MistakeQuestionPage(SectionQuestionPage):
    """A single question opened from the Mistake Book.

    Recent attempts is what marks it as a mistake: a wrong attempt is shown as
    a bad dot, which is inherited as get_wrong_attempts().
    """
