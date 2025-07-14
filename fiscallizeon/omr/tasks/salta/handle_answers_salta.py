import os

from celery import states

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.celery import app
from fiscallizeon.omr.functions.main import process_file
from fiscallizeon.omr.utils import download_spaces_image
from fiscallizeon.omr.models import OMRUpload, OMRCategory, OMRError, OMRStudents
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.answers.models import OptionAnswer
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.exams.json_utils import convert_json_to_choice_exam_questions_list, get_exam_base_json

def create_option_answers(answer):
    questions_count = 0
    application_student = answer['instance']

    OptionAnswer.objects.filter(student_application=application_student).delete()
    application_student.duplicated_answers.set([])
    application_student.is_omr = True
    application_student.save()

    exam = application_student.application.exam
    exam_json = get_exam_base_json(exam)

    if exam.is_abstract:
        exam_questions = ExamQuestion.objects.filter(
            exam=exam
        ).order_by('order')

        if exam.has_foreign_languages:
            questions = list(exam.get_foreign_exam_questions().values_list('pk', flat=True))
            if answer.get('Language', 'E') in ['E', 'EH', '']:
                foreign_language_remove = questions[len(questions)//2:]
            elif answer.get('Language', 'E') == 'H':
                foreign_language_remove = questions[:len(questions)//2]

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
                application_student.language = ApplicationStudent.ENGLISH
            elif answer.get('Language', 'E') == 'H':
                _subject = filter(lambda x: x['pk'] == str(foreign_subjects[0].pk), exam_json['exam_teacher_subjects'])
                subject_index = exam_json['exam_teacher_subjects'].index(next(_subject))
                application_student.language = ApplicationStudent.SPANISH

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
            print(f"Erro na criação de option answer: {e}")
            print(f"Checked option: {checked_option}")
            continue

    return application_student, questions_count

@app.task(bind=True)
def handle_answers_salta(self, args):
    upload_id, uploads_data = args

    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)
    omr_category = OMRCategory.objects.get(sequential=9)

    for i, sheet in enumerate(uploads_data, 1):
        tmp_file = download_spaces_image(sheet['path'])

        application_student = ApplicationStudent.objects.filter(
            pk=sheet["instance"]
        ).order_by('created_at').first()

        omr_student = OMRStudents.objects.filter(
            upload=omr_upload,
            application_student=application_student
        ).first()

        if not omr_student:
            omr_student = OMRStudents.objects.create(
                upload=omr_upload,
                application_student=application_student,
                successful_questions_count=0,
                scan_image=UploadedFile(
                    file=open(tmp_file, 'rb')
                ),
            )

        try:
            omr_marker_path = omr_category.get_omr_marker_path()
            json_obj = omr_category.template
            answer = process_file(tmp_file, json_obj, omr_marker_path)
            answer['instance'] = application_student
        except:
            #Se for associado manualmente, remove o erro e mantém o omr_student sem respostas
            if omr_error_id := sheet.get('omr_error_id', None):
                omr_error = OMRError.objects.get(pk=omr_error_id)
                omr_error.is_solved = True
                omr_error.save()
                continue

            OMRError.objects.create(
                upload=omr_upload,
                omr_category=omr_category,
                error_image=UploadedFile(
                    file=open(tmp_file, 'rb')
                ),
                category=OMRError.MARKERS_NOT_FOUND,
                page_number=sheet['page_number'],
            )
            continue

        if settings.DEBUG:
            print(f'Answer | ApplicationStudent {sheet["instance"]}:')
            print(answer)

        application_student, questions_count = create_option_answers(answer)

        omr_student.successful_questions_count = questions_count
        omr_student.save()

        if omr_error_id := sheet.get('omr_error_id', None):
            omr_error = OMRError.objects.get(pk=omr_error_id)
            omr_error.is_solved = True
            omr_error.save()
        
        os.remove(tmp_file)
        self.update_state(state=states.STARTED, meta={'done': i, 'total': omr_upload.total_pages})

    self.update_state(state=states.SUCCESS, meta={'done': omr_upload.total_pages, 'total': omr_upload.total_pages})

    omr_upload.status = OMRUpload.FINISHED
    omr_upload.save()

    return upload_id