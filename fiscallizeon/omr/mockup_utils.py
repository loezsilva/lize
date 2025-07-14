import os
import uuid
import itertools
from datetime import datetime

from django.conf import settings
from django.template.loader import render_to_string
from django.db.models import Case, When, F
from django.utils import translation

from fiscallizeon.questions.models import Question
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.accounts.models import User
from fiscallizeon.clients.models import ExamPrintConfig
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.exams.json_utils import get_exam_base_json, convert_json_to_exam_questions_list, \
    convert_json_to_questions_list, convert_json_to_choice_exam_questions_list



def print_mockup_answer_sheet(application, remote_directory, sheet_model=None, application_randomization_version=None):
    print(f"Printing mockup answer sheet for application {application.pk}")
    template_name = 'omr/mockups/answer_sheet_lize.html'
    if sheet_model == 'enem':
        template_name = 'omr/mockups/answer_sheet_enem.html'
    elif sheet_model == 'hybrid':
        template_name = 'omr/mockups/answer_sheet_hybrid.html'
    elif sheet_model == 'sum':
        template_name = 'omr/mockups/answer_sheet_sum.html'
    elif sheet_model == 'subjects':
        template_name = 'omr/mockups/answer_sheet_subjects.html'
    elif sheet_model == 'reduced':
        template_name = 'omr/mockups/answer_sheet_reduced_model.html'

    exam = application.exam
    client = application.students.all().first().client

    exam_questions = ExamQuestion.objects.filter(
        exam=exam,
        question__number_is_hidden=False,
        question__category__in=[Question.CHOICE, Question.SUM_QUESTION],
    ).availables().order_by(
        'exam_teacher_subject__order', 'order'
    ).using('default')

    if sheet_model == 'subjects':
        if application.exam.is_abstract:
            exam_questions = exam_questions.annotate(
                subject=F('question__subject__name')
            ).order_by('order')
        else:
            exam_questions = exam_questions.annotate(
                subject=F('exam_teacher_subject__teacher_subject__subject__name')
            )

    elif exam.has_foreign_languages:
        if exam.is_abstract:
            questions = exam.get_foreign_exam_questions()
            last_foreign_language_questions = questions[questions.count()//2:]
        elif foreign_subjects := exam.get_foreign_exam_teacher_subjects():
            last_foreign_language_questions = foreign_subjects[1].examquestion_set.using('default').availables()

        exam_questions = exam_questions.exclude(
            pk__in=last_foreign_language_questions.values('pk')
        )

    if application_randomization_version: #TODO: testar novo manager aqui
        exam_questions_json = convert_json_to_exam_questions_list(application_randomization_version.exam_json)
        randomized_exam_question_pks = [q['pk'] for q in exam_questions_json]
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(randomized_exam_question_pks)])
        exam_questions = exam_questions.filter(pk__in=randomized_exam_question_pks).order_by(preserved)

    context = {
        'object': application,
        'client': client,
        'exam_questions': exam_questions,
        'application_randomization_version': application_randomization_version,
    }

    html_content = render_to_string(template_name, context)

    tmp_filename = f'tmp/{uuid.uuid4()}.html'
    with open(tmp_filename, 'w') as file:
        file.write(html_content)

    remote_filename = f'mockup_answer_sheet_{application.pk}.html'
    if application_randomization_version:
        remote_filename = f'mockup_answer_sheet_{application.pk}_v{application_randomization_version.sequential}.html'

    fs = PrivateMediaStorage()
    saved_file_path = fs.save(
        os.path.join(remote_directory, remote_filename),
        open(tmp_filename, 'rb')
    )

    os.remove(tmp_filename)
    return saved_file_path


def print_mockup_discursive_sheet(application, remote_directory, print_params={}, application_randomization_version=None):
    print(f"Printing mockup discursive answer sheet for application {application.pk}")
    template_name = 'omr/export_discursive_answer_sheet.html'

    try:
        auto_correct_discursives = application.exam.coordinations.all().first().unity.client.has_discursive_auto_correction
    except:
        auto_correct_discursives = True

    context = {
        'qr_code_text': "###QR_CONTENT###",
        'application': application,
        'exam': application.exam,
        'split_subjects': 1 if print_params.get('split_subjects', False) else '',
        'iterator': itertools.count(),
        'questions_categories': [Question.TEXTUAL, Question.FILE],
        'user': User.objects.first(),
        'application_randomization_version': application_randomization_version,
        'auto_correct_discursives': auto_correct_discursives,
        'object': {
            'student': {
                'name': '#NomeDoAluno',
            },
        }
    }
    
    html_content = render_to_string(template_name, context)

    tmp_filename = f'tmp/{uuid.uuid4()}.html'
    with open(tmp_filename, 'w') as file:
        file.write(html_content)

    remote_filename = f'mockup_discursive_sheet_{application.pk}.html'
    if application_randomization_version:
        remote_filename = f'mockup_discursive_sheet_{application.pk}_v{application_randomization_version.sequential}.html'

    fs = PrivateMediaStorage()
    saved_file_path = fs.save(
        os.path.join(remote_directory, remote_filename),
        open(tmp_filename, 'rb')
    )

    os.remove(tmp_filename)
    return saved_file_path


def print_mockup_essay_sheet(application, remote_directory, is_draft=False, application_randomization_version=None):
    print(f"Printing mockup essay answer sheet for application {application.pk}")
    template_name = 'omr/mockups/answer_sheet_essay.html'
    client = application.students.all().first().client

    exam_question = ExamQuestion.objects.filter(
        exam=application.exam,
        question__is_essay=True
    ).availables(application.exam).first()

    context = {
        'object': application,
        'client': client,
        'exam_question': exam_question,
        'is_draft': is_draft,
        'application_randomization_version': application_randomization_version,
    }

    html_content = render_to_string(template_name, context)

    tmp_filename = f'tmp/{uuid.uuid4()}.html'
    with open(tmp_filename, 'w') as file:
        file.write(html_content)

    remote_filename = f'mockup_essay_answer_sheet_{application.pk}.html'
    if is_draft:
        remote_filename = f'essay_draft_answer_sheet_{application.pk}.html'

    fs = PrivateMediaStorage()
    saved_file_path = fs.save(
        os.path.join(remote_directory, remote_filename),
        open(tmp_filename, 'rb')
    )

    os.remove(tmp_filename)
    return saved_file_path


def print_mockup_exam(application, remote_directory, print_params={}, application_randomization_version=None):
    print(f"Printing mockup exam for application {application.pk}")
    template_name = 'dashboard/exams/exam_print.html'

    economy_mode = int(print_params.get('economy_mode', 0))
        
    questions = application.exam.questions.using('default').all().order_by(
        'examquestion__exam_teacher_subject__order', 'examquestion__order'
    ).distinct()

    context = {}
    context['base_url'] = settings.BASE_URL
    context['object'] = application.exam
    context['user'] = User.objects.first()
    context['two_columns'] = 1 if economy_mode else int(print_params.get('two_columns', 0))
    context['separate_subjects'] = int(print_params.get('separate_subjects', 0))
    context['line_textual'] = int(print_params.get('line_textual', 1))
    context['line_spacing'] = int(print_params.get('line_spacing', 0))
    context['font_family'] = int(print_params.get('font_family', 0))
    context['print_correct_answers'] = False
    context['header_full'] = int(print_params.get('header_full', 0))
    context['break_all_questions'] = int(print_params.get('break_all_questions', 0))
        
    font_size =print_params.get('font_size', 0)
    keys_list_sizes = [item[0] for item in ExamPrintConfig.FONT_SIZES]

    exam_creation_date = application.exam.created_at.date()
    date_creation_new_font_size_standard = datetime(2024, 7, 7, 7, 0, 0).date()
    
    #adicionado excessão para o decisão, remover após fim de ano letivo 2024
    # if str(application.students.all().first().client.pk) == 'a2b1158b-367a-40a4-8413-9897057c8aa2':
    #     if not int(font_size) in keys_list_sizes:
    #         context['font_size'] = int(font_size)
    #     elif exam_creation_date > date_creation_new_font_size_standard:
    #         context['font_size'] = int(ExamPrintConfig.get_new_default_font_value(int(font_size)))
    #     else:
    #         context['font_size'] = int(ExamPrintConfig.get_font_size(int(font_size)))
    # else:
    if not int(font_size) in keys_list_sizes:
        context['font_size'] = int(font_size)
    elif exam_creation_date > date_creation_new_font_size_standard:
        context['font_size'] = int(ExamPrintConfig.get_new_default_font_value(int(font_size)))
    else:
        context['font_size'] = int(ExamPrintConfig.get_font_size(int(font_size)))

    context['hide_dialog'] = True
    context['hide_discipline_name'] = int(print_params.get('hide_discipline_name', 0))
    context['hide_knowledge_area_name'] = int(print_params.get('hide_knowledge_area_name', 0))
    context['hide_questions_referencies'] = int(print_params.get('hide_questions_referencies', 0))
    context['print_images_with_grayscale'] = int(print_params.get('print_images_with_grayscale', 0))
    context['hyphenate_text'] = int(print_params.get('hyphenate_text', 0))
    context['discursive_line_height'] = float(print_params.get('discursive_line_height', 1))
    context["number_print_iterator"] = itertools.count(start=1)
    context['show_question_score'] = int(print_params.get('show_question_score', 0))
    context['show_question_board'] = int(print_params.get('show_question_board', 0))

    context['economy_mode'] = economy_mode
    context['force_choices_with_statement'] = int(print_params.get('force_choices_with_statement', 0))
    context['hide_numbering'] = int(print_params.get('hide_numbering', 0))  
    context['break_enunciation'] = 1 if economy_mode else int(print_params.get('break_enunciation', 0))
    context['discursive_question_space_type'] = int(print_params.get('discursive_question_space_type', 0))
    context['break_alternatives'] = 1 if economy_mode else int(print_params.get('break_alternatives', 0))

    context['uppercase_letters'] = print_params.get('uppercase_letters', 0)
    context['text_question_format'] = print_params.get('text_question_format', 1)
    context['show_footer'] = print_params.get('show_footer', 0)
    
    margin_top = float(print_params.get('margin_top', 0.6))
    margin_bottom = float(print_params.get('margin_bottom', 0.6))
    margin_right = float(print_params.get('margin_right', 0.0))
    margin_left = float(print_params.get('margin_left', 0.0))  
    context['margin_right'] = _normalize_margins(margin_right, "right_or_left")
    context['margin_left'] =  _normalize_margins(margin_left, "right_or_left")
    context['margin_bottom'] = _normalize_margins(margin_bottom, "bottom_or_top")
    context['margin_top'] =  _normalize_margins(margin_top,"bottom_or_top")
    
    for question in questions:
        question.in_last_questions = str(question in list(questions)[-4:]).lower()

    questions = questions.availables(application.exam)

    ordered_questions = None
    if application_randomization_version:
        questions_json = convert_json_to_questions_list(application_randomization_version.exam_json)
        randomized_exam_question_pks = [q['pk'] for q in questions_json]
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(randomized_exam_question_pks)])
        ordered_questions = questions.filter(pk__in=randomized_exam_question_pks).order_by(preserved)
        
        for i, ordered_question in enumerate(ordered_questions):
            if not questions_json[i]['alternatives']:
                continue

            preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(questions_json[i]['alternatives'])])
            alternatives = ordered_question.alternatives.all().order_by(preserved)
            ordered_question.randomized_alternatives = alternatives

    context['questions'] = ordered_questions or questions
    context['total_questions'] = questions.count()
    context['iterator'] = itertools.count()
    context['application_randomization_version'] = application_randomization_version

    context['application_student'] = {
        'student': {
            'name': '#NomeDoAluno',
            'enrollment_number': '#Matricula',
        },
        'get_last_class_student': {
            'grade': '#Serie',
            'name': '#Turma',
            'unity': '#Unidade'
        }
    }

    if header_id := print_params.get('header', None):
        context["exam_header"] = application.exam.get_personalized_header(header_id, remove_student_data=False)
        if application_randomization_version:
            student_name = f'#NomeDoAluno - V{application_randomization_version.version_number}'
            context["exam_header"].content = context["exam_header"].content.replace('#NomeDoAluno', student_name)
    
    try:
        language = int(print_params.get('language', ExamPrintConfig.PORTUGUESE))
        if language == ExamPrintConfig.ENGLISH:
            translation.activate('en')
        elif language == ExamPrintConfig.SPANISH:
            translation.activate('es')
        else:
            translation.activate('pt_BR')
    except Exception as e:
        print(f'Erro ao setar language: {e}')

    html_content = render_to_string(template_name, context)
    translation.activate('pt_BR')

    tmp_filename = f'tmp/{uuid.uuid4()}.html'
    with open(tmp_filename, 'w') as file:
        file.write(html_content)

    remote_filename = f'mockup_exam_{application.pk}.html'
    if application_randomization_version:
        remote_filename = f'mockup_exam_{application.pk}_v{application_randomization_version.sequential}.html'

    fs = PrivateMediaStorage()
    saved_file_path = fs.save(
        os.path.join(remote_directory, remote_filename),
        open(tmp_filename, 'rb')
    )

    os.remove(tmp_filename)
    return saved_file_path


def _normalize_margins(margin, margin_type):
    reference_margin = 0.6

    if margin_type == "right_or_left":
        new_margin = margin - reference_margin
    else: 
        new_margin = margin
    return  max(new_margin, 0)