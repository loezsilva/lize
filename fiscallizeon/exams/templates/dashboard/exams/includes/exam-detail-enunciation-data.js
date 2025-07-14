{% load remove_line_break %}
{% load exam_question_tags %}
{% load call_method %}
examQuestions: [
    {% for exam_question in exam_questions %}
        {
            "id": "{{ exam_question.pk }}",
            "question_number": "{% call_method exam 'number_print_question' exam_question.question %}",
            "enunciation": "{{ exam_question.question.get_enunciation_str|remove_line_break|truncatechars:300 }}",
            "category": "{{ exam_question.question.get_category_display }}",
            "correctAnswers": "{{ exam_question.correct_answers|default:0|default_if_none:0 }}",
            "incorrectAnswers": "{{ exam_question.incorrect_answers|default:0|default_if_none:0 }}",
            "partialAnswers": "{{ exam_question.partial_answers|default:0|default_if_none:0 }}",
            "correctedAnswers": "{{ exam_question.corrected_answers|default:0|default_if_none:0 }}",
            "totalAnswers": "{{ exam_question.answers|default:0|default_if_none:0 }}",
            "awaitCorrection": "{{exam_question|get_await_correction_count:application_students}}"
        },
    {% endfor %}
],
selectedQuestion: {},
feedbackSaved: false,
feedbackError: false,
hideEnunciation: true,
loadingAnswers: false,
schoolClass: "{{ school_class_pk }}",