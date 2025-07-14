import gzip
import json
from decimal import Decimal

from sentry_sdk import capture_message
from celery import states

from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.celery import app
from fiscallizeon.omr.models import OMRUpload, OMRStudents, OMRError, OMRCategory
from fiscallizeon.applications.models import ApplicationStudent, RandomizationVersion
from fiscallizeon.answers.models import OptionAnswer, TextualAnswer, SumAnswer
from fiscallizeon.questions.models import Question
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.exams.json_utils import convert_json_to_choice_exam_questions_list, convert_json_to_textual_exam_questions_list, \
    get_exam_base_json, convert_json_to_sum_exam_questions_list

def create_option_answers(answer):
    questions_count = 0
    application_student = ApplicationStudent.objects.using('default').filter(pk=answer['instance']).first()

    if not application_student:
        raise Exception(f'Aluno/prova não encontrado (id {answer["instance"]})')

    OptionAnswer.objects.filter(student_application=application_student).delete()
    application_student.duplicated_answers.set([])
    application_student.is_omr = True
    application_student.save()

    exam = application_student.application.exam

    if randomization_version := answer.get('randomization_version', None):
        try:
            exam_json = RandomizationVersion.objects.using('default').filter(
                application_student=application_student,
                version_number=int(randomization_version)
            ).first().exam_json
            application_student.read_randomization_version = int(randomization_version)
            application_student.save()
        except:
            capture_message(f'Versão de randomização não encontrada ({randomization_version})')
            raise Exception(f'Versão de randomização não encontrada ({randomization_version})')
    else:
        exam_json = get_exam_base_json(exam)

    if exam.is_abstract:
        exam_questions = ExamQuestion.objects.filter(
            exam=exam
        ).order_by('order')

        if exam.has_foreign_languages:
            questions = list(exam.get_foreign_exam_questions().values_list('pk', flat=True))
            if answer.get('Language', 'E') in ['E', 'EH', '']:
                foreign_language_remove = questions[len(questions)//2:]
                application_student.foreign_language = ApplicationStudent.ENGLISH
            elif answer.get('Language', 'E') == 'H':
                foreign_language_remove = questions[:len(questions)//2]
                application_student.foreign_language = ApplicationStudent.SPANISH

            application_student.save()
            exam_questions = exam_questions.exclude(pk__in=foreign_language_remove)

        questions = []
        for exam_question in exam_questions:
            questions.append({
                "pk": exam_question.pk,
                "alternatives": [
                    str(alternative.pk) for alternative in exam_question.question.alternatives.all()
                ]
            })
    else:
        if foreign_subjects := exam.get_foreign_exam_teacher_subjects():
            if answer.get('Language', 'E') in ['E', 'EH', '']:
                _subject = filter(lambda x: x['pk'] == str(foreign_subjects[1].pk), exam_json['exam_teacher_subjects'])
                subject_index = exam_json['exam_teacher_subjects'].index(next(_subject))
                application_student.foreign_language = ApplicationStudent.ENGLISH
            elif answer.get('Language', 'E') == 'H':
                _subject = filter(lambda x: x['pk'] == str(foreign_subjects[0].pk), exam_json['exam_teacher_subjects'])
                subject_index = exam_json['exam_teacher_subjects'].index(next(_subject))
                application_student.foreign_language = ApplicationStudent.SPANISH

            del exam_json['exam_teacher_subjects'][subject_index]
            application_student.save()

        questions = convert_json_to_choice_exam_questions_list(exam_json)

    for index, question in enumerate(questions, 1):
        checked_option = answer.get(f'q{index}', None)
        if not checked_option:
            continue

        try:
            db_exam_question = ExamQuestion.objects.get(pk=question['pk'])
            if len(checked_option) > 1:
                application_student.duplicated_answers.add(db_exam_question.question)
                continue
            
            elif len(checked_option) == 1:
                option_index = 'ABCDE'.index(checked_option)
                alternative_pk = question['alternatives'][option_index]
                question_option = db_exam_question.question.alternatives.get(pk=alternative_pk)

                if question_option:
                    questions_count += 1
                    OptionAnswer.objects.create(
                        question_option=question_option,
                        student_application=application_student
                    )

        except Exception as e:
            print("ERRO:", e)
            continue

    return application_student, questions_count

def create_textual_answers(answer, omr_category):
    questions_count = 0

    application_student = ApplicationStudent.objects.using('default').filter(pk=answer['instance']).first()

    if not application_student:
        raise Exception(f'Aluno/prova não encontrado (id {answer["instance"]})')

    exam = application_student.application.exam

    TextualAnswer.objects.filter(student_application=application_student).delete()
    if not application_student.is_omr:
        application_student.is_omr = True
        application_student.save()

    if randomization_version := answer.get('randomization_version', None):
        try:
            exam_json = RandomizationVersion.objects.using('default').filter(
                application_student=application_student,
                version_number=int(randomization_version)
            ).first().exam_json
            application_student.read_randomization_version = int(randomization_version)
            application_student.save()
        except:
            raise Exception(f'Versão de randomização não encontrada ({randomization_version})')
    else:
        exam_json = get_exam_base_json(exam)

    if exam.is_abstract:
        exam_questions = ExamQuestion.objects.filter(
            exam=exam,
            question__category=Question.TEXTUAL
        ).order_by('order')

        questions = []
        for exam_question in exam_questions:
            questions.append({
                "pk": exam_question.pk,
            })
    else:
        questions = convert_json_to_textual_exam_questions_list(exam_json)

    for index, question in enumerate(questions, 1):
        checked_option = answer.get(f'd{index}', None)
        try:
            option_index = 'ABCDEFGHIJ'.index(checked_option)
        except ValueError:
            return None
        
        try:
            exam_question = ExamQuestion.objects.get(pk=question['pk'])
        except:
            continue

        if not omr_category.discursive_grade_setps:
            continue

        step_value = Decimal(round(1/(omr_category.discursive_grade_setps-1), 6))
        grade = option_index * step_value * exam_question.weight

        if grade != None:
            TextualAnswer.objects.update_or_create(
                question=exam_question.question,
                student_application=application_student,
                defaults={
                    "teacher_grade": grade,
                    "content": "Gerado automaticamente (leitura de nota realizada via cartão resposta do professor)",
                }
            )
            questions_count += 1

    return questions_count

def create_sum_answers(answer, omr_category):
    questions_count = 0
    application_student = ApplicationStudent.objects.using('default').filter(pk=answer['instance']).first()

    if not application_student:
        raise Exception(f'Aluno/prova não encontrado (id {answer["instance"]})')
    
    exam = application_student.application.exam
    SumAnswer.objects.filter(student_application=application_student).delete()

    if not application_student.is_omr:
        application_student.is_omr = True
        application_student.save()

    if randomization_version := answer.get('randomization_version', None):
        try:
            exam_json = RandomizationVersion.objects.using('default').filter(
                application_student=application_student,
                version_number=int(randomization_version)
            ).first().exam_json
            application_student.read_randomization_version = int(randomization_version)
            application_student.save()
        except:
            raise Exception(f'Versão de randomização não encontrada ({randomization_version})')
    else:
        exam_json = get_exam_base_json(exam)

    if exam.is_abstract:
        exam_questions = ExamQuestion.objects.filter(
            exam=exam,
            question__category=Question.TEXTUAL
        ).order_by('order')

        questions = []
        for exam_question in exam_questions:
            questions.append({
                "pk": exam_question.pk,
            })
    else:
        questions = convert_json_to_sum_exam_questions_list(exam_json)

    for index, question in enumerate(questions, 1):
        answer_sum = answer.get(f'Sum{index}', None)

        if len(answer_sum) != 2:
            continue

        try:
            exam_question = ExamQuestion.objects.get(pk=question['pk'])
        except:
            continue

        sum_answer = SumAnswer.objects.create(
            value=answer_sum,
            question=exam_question.question,
            student_application=application_student,
            empty=answer_sum == '00'
        )

        options_created = sum_answer.create_sum_option_answers()
        questions_count += int(options_created)
        sum_answer.grade = sum_answer.get_grade_proportion()
        sum_answer.save()

    return questions_count


@app.task(bind=True)
def handle_answers(self, args):
    if not args:
        return

    upload_id, answer = args
    
    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)

    try:
        application_student, questions_count = create_option_answers(answer)

        omr_category = OMRCategory.objects.filter(
            sequential=answer.get('category', 0)
        ).first()

        if omr_category.sequential in [OMRCategory.HYBRID_025]:
            discursive_questions_count = create_textual_answers(answer, omr_category)

            if questions_count and discursive_questions_count:
                questions_count += discursive_questions_count
            else:
                questions_count = questions_count or discursive_questions_count

        elif omr_category.sequential in [OMRCategory.SUM_1]:
            sum_questions_count = create_sum_answers(answer, omr_category)

            if questions_count and sum_questions_count:
                questions_count += sum_questions_count
            else:
                questions_count = questions_count or sum_questions_count

        omr_student = OMRStudents.objects.filter(
            upload=omr_upload,
            application_student=application_student
        ).first()

        if not omr_student:
            omr_student = OMRStudents.objects.create(
                upload=omr_upload,
                application_student=application_student
            )

        omr_student.successful_questions_count = questions_count
        omr_student.save()

        if omr_error_id := answer.get('omr_error_id', None):
            omr_error = OMRError.objects.get(pk=omr_error_id)
            omr_student.scan_image = omr_error.error_image
            omr_student.save()
            omr_error.is_solved = True
            omr_error.save()
            if omr_upload.error_pages_count:
                omr_upload.error_pages_count -= 1
                omr_upload.save()

        elif file_url := answer.get('file_url', None):
            omr_student.scan_image = file_url
            omr_student.save()
            
    except Exception as e:
        omr_upload.append_processing_log(f'Erro no cadastro de alternativas: {e}')

    return upload_id