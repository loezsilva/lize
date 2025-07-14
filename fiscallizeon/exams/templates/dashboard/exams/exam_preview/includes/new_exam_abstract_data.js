{% load static %}
{% load get_exam_question %}
{% load remove_line_break %}
{% load increment %}
{% load exams_tags %}
{% load questions_tags %}
{% load exam_question_tags %}

{% with exam=object %}
    {% with exam|get_exam_abstract_subjects as subjects %}
        
        examTeacherSubjects: [
            {% for subject in subjects %}

                {% with exam|get_exam_abstract_discursive_questions_subject:subject as exam_questions %}
                
                    {
                        id:"{{subject.id}}",
                        subject: {
                            id: "{{subject.id}}",
                            name: "{{subject.name}}",
                        },
                        questions: [
                        
                            {% for exam_question in exam_questions %}
                                {% if not exam_question.question.is_essay %}
                                    {
                                        id: "{{exam_question.question.pk}}",
                                        index: {{forloop.counter}},
                                        {% if not exam_question.question.number_is_hidden %}
                                            number_print: {{exam_question.question|number_print_question:exam}},
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
                                        examQuestionShortCode : "{{exam_question.short_code|default:""}}",
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