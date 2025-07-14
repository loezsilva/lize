{% load static %}
{% load shuffle %}
{% load remove_line_break %}
{% load increment %}
{% load get_answer_file_link %}
{% load get_exam_question %}
{% load exams_tags %}

{% with exam=object.application.exam %}
{% regroup questions by subject.knowledge_area as knowledge_areas %}
knowledgeAreas: [
    {% for knowledge_area in knowledge_areas %}
    {   
        name: "{{knowledge_area.grouper.name|default:"Sem area do conhecimento"}}",
        {% regroup knowledge_area.list by subject as subjects %}
        subjects:[
            {% for subject in subjects %}
                {
                    id: "{{subject.grouper.id}}",
                    name: "{{subject.grouper.name|default:"Sem disciplina"}}",
                    foreignLanguageIndex: {{subject.grouper.id|get_foreign_language_index:exam|default_if_none:'null'}},
                    questions: [
                        {% for question in subject.list|shuffle:exam.random_questions %}
                            {
                                id: "{{question.pk}}",
                                number: {{iterator|increment}},
                                {% if not question.number_is_hidden %}
                                    {% if exam.random_questions %}
                                        number_print: {{number_print_iterator|increment}},
                                    {% else %}
                                        number_print: {{question|number_print_question:exam}},
                                    {% endif %}
                                {% else %}
                                    number_print: null,
                                {% endif %}
                                print_only_enunciation: {{question.print_only_enunciation|default:False|lower}},
                                updated_at: "{{ question.updated_at|date:'c' }}",
                                enunciation: "{{question.enunciation_escaped|remove_line_break|safe}}",
                                category: "{{question.get_category_display}}",
                                answerId: "{{question.answer_id|default:''}}",
                                sumQuestionOptionsChecked: [
                                    {% for sum_question_option_id in question.sum_question_options_checked|default_if_none:"" %}
                                        "{{ sum_question_option_id }}"{% if not forloop.last %}, {% endif %}
                                    {% endfor %}
                                ],
                                values: {{question.values|default:0}},
                                selectedIndexes: [],
                                answerTime: 
                                {% if question.answer_time %}
                                    new Date("{{question.answer_time|date:'Y-m-d H:i:s'}}"),
                                {% else %}
                                    "",
                                {% endif %}
                                {% if question.get_category_display == 'Discursiva' or question.get_category_display == 'Objetiva' %}
                                    answerContent: "{{question.answer_content|default:''|escapejs|remove_line_break}}",
                                {% else  %}
                                    answerContent: "{{question.answer_id|get_answer_file_link|default:''|escapejs|remove_line_break}}",
                                {% endif %}
                                file: "",
                                fileMessage: "",
                                error: false,
                                saving: false,
                                subjectID: "{{question.subject.id}}",
                                timing: {{question.answer.duration.total_seconds|stringformat:'.f'|default:0}},
                                examTeacherSubjectID: "{{question|get_exam_teacher_subject:object.application.exam}}",
                                send_on_qrcode: {{question.send_on_qrcode|lower|default:'false'}},
                                alternatives:[
                                    {% for alternative in question.alternatives.all|shuffle:exam.random_alternatives %}
                                    {
                                        id: "{{alternative.pk}}",
                                        text: "{{alternative.text_escaped|remove_line_break|safe}}",
                                        scratched: false
                                    },
                                    {% endfor %}
                                ],
                                base_texts: [
                                    {% for base_text in question.base_texts.all %}
                                        {
                                            id: "{{base_text.id}}",
                                            title: "{{base_text.title}}",
                                            text: "{{base_text.text_escaped|remove_line_break|safe}}"

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
needChooseLanguage: {{need_choose_language|lower|default:'false'}},
selectedLanguage: {{object.foreign_language|default_if_none:'null'}},
fontSize: "font-2x",
isLoading: true,
openingFileInput: false,
contrast: false,
configOpened: false,
leaveEventPending: {% if object.pending_leave_event %}
{
    "pk":"{{object.pending_leave_event.pk}}",
    "get_event_type_display": "{{object.pending_leave_event.get_event_type_display}}",
    "created_at": "{{object.pending_leave_event.created_at|date:'c'}}",
    "start": "{{object.pending_leave_event.start}}",
}
{% else %}
null
{% endif %}
{% endwith %}