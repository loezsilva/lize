{% load static %}
{% load shuffle %}
{% load remove_line_break %}
{% load increment %}
{% load get_answer_file_link %}
{% load get_exam_question %}
{% load questions_tags %}

{% with exam=object %}
    {% if randomization %}
        examTeacherSubjects: [
            {% for exam_teacher_subject in exam_teacher_subjects %}
                {   
                    name: "{{exam_teacher_subject.grade.name}}",
                    grade: {
                        id: "{{exam_teacher_subject.grade.id}}",
                        name: "{{exam_teacher_subject.grade.name}}",
                    },
                    subject: {
                        id: "{{exam_teacher_subject.subject.id}}",
                        name: "{{exam_teacher_subject.subject.name}}",
                    },
                    questions: [
                        {% for exam_question in exam_teacher_subject.exam_questions %}
                            {
                                id: "{{exam_question.question.pk}}",
                                index: {{forloop.counter}},                           
                                number_print: "{{ exam_question.order }}",
                                print_only_enunciation:{{exam_question.question.print_only_enunciation|lower}},
                                quantity_lines:{{exam_question.question.quantity_lines|lower}},
                                draft_rows_number:{{exam_question.question.draft_rows_number|default:0}},
                                supportContentQuestion: "{{ question.support_content_question|default:''|escapejs }}",
                                supportContentPosition: "{{ question.support_content_position|lower }}",
                                text_question_format:{{exam_question.question.text_question_format|lower}},
                                break_enunciation:{{exam_question.question.break_enunciation|lower}},
                                break_alternatives:{{exam_question.question.break_alternatives|lower}},
                                force_one_column:{{exam_question.question.force_one_column|lower}},
                                updated_at: "{{ exam_question.question.updated_at|date:'c' }}",
                                level: "{{ exam_question.question.get_level_display }}",
                                weight: "{{ exam_question.weight }}",
                                board: "{{ exam_question.question.board|default:'' }}",
                                enunciation: "{{exam_question.question.enunciation_escaped|remove_line_break|safe}}",
                                category: "{{exam_question.question.get_category_display}}",
                                answerId: "{{exam_question.question.answer_id}}",
                                annuled: {{exam_question.annuled|default:False|lower}},
                                {% if exam_question.question.get_category_display == 'Discursiva' or exam_question.question.get_category_display == 'Objetiva' %}
                                    answerContent: "{{exam_question.question.answer_content|default:''|escapejs|remove_line_break}}",
                                {% else  %}
                                    answerContent: "{{exam_question.question.answer_id|get_answer_file_link|default:''|escapejs|remove_line_break}}",
                                {% endif %}
                                file: "",
                                fileMessage: "",
                                canBeUpdated: {{exam_question.question|check_can_be_updated:user|lower}},
                                grade: "{{exam_question.question.grade}}",
                                subject: "{{exam_question.question.subject.name}}",
                                force_break_page:{{exam_question.question.force_break_page|lower}},
                                subjectID: "{{exam_question.question.subject.id}}",
                                knowledgeArea: "{{exam_question.question.subject.knowledge_area.name}}",
                                answerTeacherFeedback: "{{exam_question.question.answer_teacher_feedback|default:''|escapejs|remove_line_break}}",
                                teacherFeedback: "{{exam_question.question.feedback_escaped|default:''|default_if_none:''|remove_line_break|safe}}",
                                commentedAwnser: "{{exam_question.question.commented_awnser_escaped|default:''|default_if_none:''|remove_line_break|safe}}",
                                hasFeedback:{{exam_question.question.has_feedback|lower}},
                                saving: false,
                                timing: {{exam_question.question.answer.duration.total_seconds|stringformat:'.f'|default:0}},
                                alternatives:[
                                    {% for alternative in exam_question.alternatives %}
                                    {
                                        id: "{{alternative.pk}}",
                                        text: "{{alternative.text_escaped|remove_line_break|safe}}",
                                        index: {{alternative.index}},
                                    },
                                    {% endfor %}
                                ],
                                correctAlternatives:[
                                    {% for alternative in exam_question.question.correct_alternatives.all %}
                                        "{{alternative.pk}}",
                                    {% endfor %}
                                ],
                                base_texts: [
                                    {% for base_text in exam_question.question.base_texts.all %}
                                        {
                                            id: "{{base_text.id}}",
                                            title: "{{base_text.title}}",
                                            text: "{{base_text.text_escaped|remove_line_break|safe}}",
                                        },
                                    {% endfor %}
                                ],
                                baseTextRelations: [],
                            },
                        {% endfor %}
                    ]
                },
            {% endfor %}
        ],
        knowledgeAreas: [],
    {% else %}
        {% regroup questions by subject.knowledge_area as knowledge_areas %}
        knowledgeAreas: [
            {% for knowledge_area in knowledge_areas %}
                {   
                    name: "{{knowledge_area.grouper.name}}",
                    {% regroup knowledge_area.list by subject as subjects %}
                    subjects: [
                        {% for subject in subjects %}
                            {
                                id: "{{subject.grouper.id}}",
                                name: "{{subject.grouper.name}}",
                                questions: [
                                    {% for question in subject.list %}
                                        {
                                            id: "{{question.pk}}",
                                            index: {{forloop.counter}},
                                            number: {{ iterator|increment}},
                                            {% if not question.number_is_hidden %}
                                                {% if application_randomization_version %}
                                                    number_print: {{question|randomized_application_number_print_question:application_randomization_version}},
                                                {% else %}
                                                    number_print: {{question|number_print_question:exam}},
                                                {% endif %}
                                            {% else %}
                                                number_print: '',
                                            {% endif %}
                                            print_only_enunciation:{{question.print_only_enunciation|lower}},
                                            level: "{{ question.get_level_display }}",
                                            quantity_lines:{{question.quantity_lines|lower}},
                                            draft_rows_number:{{question.draft_rows_number|default:0}},
                                            supportContentQuestion: "{{ question.support_content_question|default:''|escapejs }}",
                                            supportContentPosition: "{{ question.support_content_position|lower }}",
                                            text_question_format:{{question.text_question_format}},
                                            break_enunciation:{{question.break_enunciation|lower}},
                                            break_alternatives: {{question.break_alternatives|lower}},
                                            force_choices_with_statement:{{question.force_choices_with_statement|lower}},
                                            force_break_page:{{question.force_break_page|lower}},
                                            force_one_column:{{question.force_one_column|lower}},
                                            updated_at: "{{ question.updated_at|date:'c' }}",
                                            enunciation: "{{question.enunciation_escaped|remove_line_break|safe}}",
                                            category: "{{question.get_category_display}}",
                                            answerId: "{{question.answer_id}}",
                                            {% if question.get_category_display == 'Discursiva' or question.get_category_display == 'Objetiva' %}
                                                answerContent: "{{question.answer_content|default:''|escapejs|remove_line_break}}",
                                            {% else  %}
                                                answerContent: "{{question.answer_id|get_answer_file_link|default:''|escapejs|remove_line_break}}",
                                            {% endif %}
                                            file: "",
                                            fileMessage: "",
                                            canBeUpdated: {{question|check_can_be_updated:user|lower}},
                                            grade: "{{question.grade}}",
                                            subject: "{{question.subject.name}}",
                                            subjectID: "{{question.subject.id}}",
                                            knowledgeArea: "{{question.subject.knowledge_area.name}}",
                                            answerTeacherFeedback: "{{question.answer_teacher_feedback|default:''|escapejs|remove_line_break}}",
                                            teacherFeedback: "{{question.feedback_escaped|default:''|default_if_none:''|remove_line_break|safe}}",
                                            commentedAwnser: "{{question.commented_awnser_escaped|default:''|default_if_none:''|remove_line_break|safe}}",
                                            hasFeedback:{{question.has_feedback|lower}},
                                            textQuestionFormat: {{exam_question.question.text_question_format|default:0}},
                                            examTeacherSubject: "{{question|get_exam_teacher_subject:exam}}",
                                            {% with question|get_exam_question:exam as exam_question %}
                                                examQuestion: "{{exam_question.id|default:""}}",
                                                examQuestionShortCode : "{{exam_question.short_code|default:""}}",
                                                weight: "{{exam_question.weight}}",
                                                annuled: {% if exam_question.last_status_v2.status == 6 or exam_question.last_status_v2.annuled_give_score %}true{% else %}false{% endif %},
                                            {% endwith %}
                                            board: "{{ question.board|default:'' }}",

                                            saving: false,
                                            timing: {{question.answer.duration.total_seconds|stringformat:'.f'|default:0}},
                                            alternatives:[
                                                {% if question.randomized_alternatives %}
                                                    {% for alternative in question.randomized_alternatives.all %}
                                                    {
                                                        id: "{{alternative.pk}}",
                                                        text: "{{alternative.text_escaped|remove_line_break|safe}}",
                                                        index: {{alternative.index}},
                                                    },
                                                    {% endfor %}
                                                {% else %}
                                                    {% for alternative in question.alternatives.all %}
                                                    {
                                                        id: "{{alternative.pk}}",
                                                        text: "{{alternative.text_escaped|remove_line_break|safe}}",
                                                        index: {{alternative.index}},
                                                    },
                                                    {% endfor %}
                                                {% endif %}
                                                
                                            ],
                                            abilities:[
                                                {% for ability in question.abilities.all %}
                                                {
                                                    code: "{{ability.code}}",
                                                    text: "{{ability.text|remove_line_break|safe}}",
                                                },
                                                {% endfor %}
                                            ],
                                            correctAlternatives:[
                                                {% for alternative in question.correct_alternatives.all %}
                                                    "{{alternative.pk}}",
                                                {% endfor %}
                                            ],
                                            base_texts: [
                                                {% for base_text in question.base_texts.all %}
                                                    {
                                                        id: "{{base_text.id}}",
                                                        title: "{{base_text.title}}",
                                                        text: "{{base_text.text_escaped|remove_line_break|safe}}",
                                                    },
                                                {% endfor %}
                                            ],
                                            baseTextRelations: [],
                                        },
                                    {% endfor %}
                                ]
                            },
                        {% endfor %}
                    ]
                },
            {% endfor %}
        ],
    {% endif %}
{% endwith %}