import gzip
import json
from decimal import Decimal

from celery import states

from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.celery import app
from fiscallizeon.omr.models import OMRUpload, OMRStudents, OMRError, OMRCategory
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.answers.models import TextualAnswer
from fiscallizeon.questions.models import Question
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.exams.json_utils import convert_json_to_textual_exam_questions_list, get_exam_base_json

def create_textual_answers(answer, omr_category):
    questions_count = 0

    application_student = ApplicationStudent.objects.using('default').filter(pk=answer['instance']).first()

    if not application_student:
        raise Exception(f'Aluno/prova não encontrado (id {answer["instance"]})')

    exam = application_student.application.exam
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
        grade = None
        grades_dict = {'A': 0, 'B': 0.5, 'C': 0.75, 'D': 1}

        checked_option = answer.get(f'q{index}', None)
        if len(checked_option) != 1:
            continue
        
        try:
            exam_question = ExamQuestion.objects.get(pk=question['pk'])
            grade_proportion = Decimal(round(grades_dict[checked_option], 6))
            grade = grade_proportion * exam_question.weight
        except Exception as e:
            print(e)
            continue

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


@app.task(bind=True)
def handle_answers(self, args):
    upload_id, gziped_answers = args
    answers = json.loads(gzip.decompress(gziped_answers).decode('utf-8'))
    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)
    
    for i, answer in enumerate(answers, 1):
        try:
            application_student = ApplicationStudent.objects.get(pk=answer['instance'])
            omr_category = OMRCategory.objects.get(
                sequential=answer.get('category', 0)
            )

            TextualAnswer.objects.filter(student_application=application_student).delete()

            omr_student = OMRStudents.objects.filter(
                upload=omr_upload,
                application_student=application_student
            ).first()

            if not omr_student:
                omr_student = OMRStudents.objects.create(
                    upload=omr_upload,
                    application_student=application_student
                )

            if answer.get('b1', '') == 'E':
                application_student.missed = True
                application_student.save()
                omr_student.checked = True
                omr_student.checked_by = omr_upload.user
                omr_student.save()
                continue
            elif answer.get('b1', '') == 'H':
                application_student.feedback_after_clean = 'Prova zerada por comando de anulação na folha de respostas'
                application_student.save()
                omr_student.checked = True
                omr_student.checked_by = omr_upload.user
                omr_student.save()
                continue

            if omr_category.sequential in [OMRCategory.ELIT]:
                discursive_questions_count = create_textual_answers(answer, omr_category)

            omr_student.successful_questions_count = discursive_questions_count
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
                omr_student.scan_image = UploadedFile(
                    file=open(file_url, 'rb')
                )
                omr_student.save()
                
        except Exception as e:
            omr_upload.append_processing_log(f'Erro no cadastro de alternativas: {e}')
        
        self.update_state(state=states.STARTED, meta={'done': i, 'total': omr_upload.total_pages})

    self.update_state(state=states.SUCCESS, meta={'done': omr_upload.total_pages, 'total': omr_upload.total_pages})
    return upload_id