from django.core.management.base import BaseCommand

from fiscallizeon.clients.models import Client, ExamPrintConfig
from mixer.backend.django import mixer
from ...models import Exam
from fiscallizeon.exams.models import ExamTeacherSubject
from fiscallizeon.applications.models import ApplicationStudent, Application
from fiscallizeon.answers.models import OptionAnswer, TextualAnswer, FileAnswer
from fiscallizeon.questions.models import Question
from fiscallizeon.students.models import Student
from django.utils import timezone
import datetime


class Command(BaseCommand):
    help = 'Adiciona configuração de impressão de caderno a todos os cadernos'

    def add_arguments(self, parser):
        parser.add_argument('--examteachersubject', required=True)
        parser.add_argument('--quantity', default=20, required=False)
        parser.add_argument('--create_application', default=False, required=False)
        parser.add_argument('--date', default=timezone.now().strftime("%Y-%m-%d"), required=False)
        parser.add_argument('--start', default=(timezone.now() - datetime.timedelta(hours=5)).strftime("%H:%M:%S"), required=False)
        parser.add_argument('--end', default=timezone.now().strftime("%H:%M:%S"), required=False)
        
    def handle(self, *args, **kwargs):
        exam_teacher_subject = ExamTeacherSubject.objects.get(pk=kwargs['examteachersubject'])
        user = exam_teacher_subject.teacher_subject.teacher.user
        client = user.get_clients().first()
        
        exam = exam_teacher_subject.exam
        exam_questions = exam.examquestion_set.availables()
        application = exam.application_set.all().last()
        
        if not application or kwargs['create_application']:
            application = mixer.blend(
                Application, 
                exam=exam,
                date=kwargs['date'],
                start=kwargs['start'],
                end=kwargs['end'],
                category=Application.MONITORIN_EXAM,
                automatic_creation=False,
                leveling_test=False,
                is_presential_sync=False,
                student_stats_permission_date=timezone.now().strftime("%Y-%m-%d"),
            )
            
            for student in application.students.set(Student.objects.filter(client=client).order_by('?')[:kwargs['quantity']]):
                mixer.blend(
                    ApplicationStudent, 
                    student=student, 
                    application=application, 
                    is_omr=False
                )
        
        if application.applicationstudent_set.exists():
            applications_student = application.applicationstudent_set.all()
            for application_student in applications_student:
                for exam_question in exam_questions:
                    if exam_question.question.category == Question.CHOICE:
                        alternative = exam_question.question.alternatives.all().order_by('?').first()
                        if alternative:
                            mixer.blend(OptionAnswer, question_option=alternative, student_application=application_student)
                    elif not application_student.textual_answers.exists() and exam_question.question.category == Question.TEXTUAL:
                        mixer.blend(TextualAnswer, question=exam_question.question, student_application=application_student)
                    elif not application_student.file_answers.exists() and exam_question.question.category == Question.FILE:
                        mixer.blend(FileAnswer, question=exam_question.question, student_application=application_student)