import os
import requests
import shutil

from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Q, OuterRef, Subquery, Value, Count
from django.db.models.functions import Coalesce
from django.conf import settings

from fiscallizeon.omr.models import OMRCategory, OMRStudents
from fiscallizeon.applications.models import RandomizationVersion, ApplicationStudent
from fiscallizeon.answers.models import OptionAnswer, FileAnswer, TextualAnswer
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.omr.functions.main import process_file
from fiscallizeon.exams.json_utils import convert_json_to_choice_exam_questions_list, get_exam_base_json


class Command(BaseCommand):
    help = 'Resolve problema de alunos duplicados em aplicações do META'

    def read_sheet(self, file_path, exam, category):
        omr_marker_path = os.path.join(settings.BASE_DIR, 'fiscallizeon', 'core', 'static', 'omr_marker.jpg')
        json_obj = category.get_exam_json(exam)
        return process_file(file_path, json_obj, omr_marker_path)

    def create_option_answers(self, answer):
        questions_count = 0
        application_student = answer['instance']

        OptionAnswer.objects.filter(student_application=application_student).delete()
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
                raise Exception(f'Versão de randomização não encontrada ({randomization_version})')
        else:
            exam_json = get_exam_base_json(exam)

        
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
                option_index = 'ABCDE'.index(checked_option) if len(checked_option) == 1 else -1
                db_exam_question = ExamQuestion.objects.get(pk=question['pk'])

                if option_index < 0:
                    continue

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

        return questions_count


    def read_sheets_directory_fiscallize(self, wrong_application_student, correct_application_student):
        omr_category = OMRCategory.objects.get(sequential=OMRCategory.FISCALLIZE)
        wrong_omr_student = OMRStudents.objects.filter(application_student=wrong_application_student).first()

        answer_filename = f'/code/tmp/meta-student-answer.jpg'
        with requests.get(wrong_omr_student.scan_image.url, stream=True) as r:
            with open(answer_filename, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

        answer = self.read_sheet(answer_filename, wrong_application_student.application.exam, omr_category)
        answer['instance'] = correct_application_student
        answer['randomization_version'] = wrong_application_student.read_randomization_version

        correct_application_student.read_randomization_version = wrong_application_student.read_randomization_version
        correct_application_student.is_omr = True
        correct_application_student.save()

        omr_student = OMRStudents.objects.filter(
            upload=wrong_omr_student.upload,
            application_student=correct_application_student
        ).first()

        if not omr_student:
            omr_student = OMRStudents.objects.create(
                upload=wrong_omr_student.upload,
                application_student=correct_application_student,
                successful_questions_count=0,
                scan_image=UploadedFile(
                    file=open(answer_filename, 'rb')
                ),
            )

        questions_count = self.create_option_answers(answer)
        omr_student.successful_questions_count = questions_count
        omr_student.save()

    def handle(self, *args, **kwargs):        
        apps= ApplicationStudent.objects.filter(
            Q(student__client__name__icontains="meta"),
            Q(application__date__gte="2023-05-01"),
            Q(
                Q(option_answers__isnull=False) |
                Q(textual_answers__isnull=False) |
                Q(file_answers__isnull=False)
            )
        ).exclude(
            read_randomization_version=0    
        ).annotate(
            count=Coalesce(
                Subquery(
                    ApplicationStudent.objects.filter(
                        Q(
                            Q(student=OuterRef('student')) |
                            Q(student__enrollment_number=OuterRef('student__enrollment_number'))
                        ),
                        Q(application=OuterRef('application'))
                    ).values(
                        'application', 'student'
                    ).annotate(
                        count_sub=Count('pk')
                    ).values('count_sub')[:1]
                ), Value(1)
            )
        ).filter(
            count__gt=1
        ).distinct()

        for app in apps:
            nota_errada = ApplicationStudent.objects.filter(pk=app.pk).get_annotation_count_answers(
                only_total_grade=True,
                exclude_annuleds=True
            ).first().total_grade
            wrong_application = app
            correct_application = ApplicationStudent.objects.filter(
                Q(
                    Q(student=app.student) |
                    Q(student__enrollment_number=app.student.enrollment_number)
                ),
                Q(application=app.application)
            ).exclude(pk=app.pk).first()

            self.read_sheets_directory_fiscallize(wrong_application, correct_application)

            nota_certa = ApplicationStudent.objects.filter(pk=correct_application.pk).get_annotation_count_answers(
                only_total_grade=True,
                exclude_annuleds=True
            ).first().total_grade
            print(f'ERRADA --- {app.student.name}, {app.application.exam.name}, {nota_errada}')
            print(f'CERTA  --- {correct_application.student.name}, {correct_application.application.exam.name}, {nota_certa}')

            if nota_errada >= nota_certa:
                OptionAnswer.objects.filter(student_application=correct_application).delete()
                FileAnswer.objects.filter(student_application=correct_application).delete()
                TextualAnswer.objects.filter(student_application=correct_application).delete()
                correct_application.is_omr=False
                correct_application.save()
            else:
                OptionAnswer.objects.filter(student_application=wrong_application).delete()
                FileAnswer.objects.filter(student_application=wrong_application).delete()
                TextualAnswer.objects.filter(student_application=wrong_application).delete()
                wrong_application.is_omr=False
                wrong_application.save()
            print("-----")