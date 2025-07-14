{% load static %}
{% load get_exam_question %}
{% load remove_line_break %}
{% load increment %}
{% load exams_tags %}
{% load questions_tags %}
{% load exam_question_tags %}

{% with exam=object %}
    {% with exam|get_exam_teacher_subjects as exam_teacher_subjects %}
        examTeacherSubjects: [
            {% for exam_teacher_subject in exam_teacher_subjects %}
                {% with exam_teacher_subject|get_exam_questions_availables:questions_categories|sort_exam_questions_by_randomization_version:application_randomization_version as exam_questions %}
                    {
                        id: "{{exam_teacher_subject.id}}",
                        subject: {
                            id: "{{exam_teacher_subject.teacher_subject.subject.id}}",
                            name: "{{exam_teacher_subject.teacher_subject.subject.name}}",
                        },
                        questions: [
                            {% for exam_question in exam_questions %}
                                {% if not exam_question.question.is_essay %}
                                    {
                                        id: "{{exam_question.question.pk}}",
                                        index: {{forloop.counter}},
                                        {% if not exam_question.question.number_is_hidden %}
                                            {% if application_randomization_version %}
                                                number_print: {{exam_question.question|randomized_application_number_print_question:application_randomization_version}},
                                            {% else %}
                                                number_print: {{exam_question.question|number_print_question:exam}},
                                            {% endif %}
                                        {% else %}
                                            number_print: '',
                                        {% endif %}
                                    {% with exam_question.question.quantity_lines|default:5 as lines %}
                                        {% if lines > 30 %}
                                            quantity_lines: 30,
                                        {% elif lines < 3 %}
                                            quantity_lines: 3,
                                        {% else %}
                                            quantity_lines: {{lines}},
                                        {% endif %}
                                    {% endwith %}
                                    text_question_format:{{exam_question.question.text_question_format|lower}},
                                    enunciation: "{{exam_question.question.enunciation_escaped|remove_line_break|safe}}",
                                    category: "{{exam_question.question.get_category_display}}",
                                    subject: "{{exam_question.question.subject.name}}",
                                    subjectID: "{{exam_question.question.subject.id}}",
                                    textQuestionFormat: {{exam_question.question.text_question_format|default:0|lower}},
                                    examQuestionShortCode : "{{exam_question.short_code|default:""}}",
                                    supportContentQuestion: "{{exam_question.question.support_content_question_escaped|remove_line_break|safe}}",
                                    supportContentPosition: "{{ exam_question.question.support_content_position }}",

                                    },
                                {% endif %}
                            {% endfor %}
                        ]
                    },
                {% endwith %}
            {% endfor %}
        ],
    {% endwith %}
{% endwith %}