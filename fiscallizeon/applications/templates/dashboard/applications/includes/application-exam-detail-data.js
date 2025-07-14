{% load remove_line_break %}
{% load l10n %}
{% load get_answer_file_link %}

questions: [
    {% for question in questions %}
        {
            "pk": "{{ question.pk }}",
            "answer": "{{ question.answer|default_if_none:'' }}",
            "is_correct": {{ question.is_correct|yesno:"true,false"|default_if_none:"''" }},
            "total_answers": {{ question.total_answers|default_if_none:"''" }},
            "duration": "{{ question.duration|default_if_none:'' }}",
            "category": "{{ question.get_category_display }}",
            "question_weight": "{{ question.question_weight|unlocalize }}",
            "textual_answer": "{{ question.textual_answer_content|default_if_none:''|remove_line_break|escapejs }}",
            "file_answer": "{{ question.file_answer|default_if_none:''|get_answer_file_link|safe }}",
            "teacher_feedback": "{{ question.teacher_feedback|default_if_none:''|escapejs }}",
            "teacher_grade": "{{ question.teacher_grade|default_if_none:''|unlocalize }}",
        },
    {% endfor %}
],
selectedQuestion: {},