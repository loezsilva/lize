from django.utils import timezone
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from mixer.backend.django import mixer
from django.db.models import Q

from fiscallizeon.exams.models import Exam, ExamTeacherSubject, TeacherSubject, ExamQuestion, StatusQuestion
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.accounts.models import User
from fiscallizeon.questions.models import Question, QuestionOption
from fiscallizeon.students.models import Student
from fiscallizeon.subjects.models import Grade, Subject
from fiscallizeon.answers.models import OptionAnswer

class Command(BaseCommand):
    help = 'Adiciona hora de término appication students não finaizados. Por padrão, utiliza-se a hora final da aplicação'


    def add_arguments(self, parser):
        parser.add_argument('--create_answers', default=True, type=bool)
        parser.add_argument('--all_answers_is_correct', default=False, type=bool)
        parser.add_argument('--username', default='fiscallize_geral', type=str)
        
    def handle(self, *args, **kwargs):
        
        with transaction.atomic():
            
            user = User.objects.get(username=kwargs['username'])
            coordinations = user.get_coordinations()
            client = user.get_clients().first()
            
            exam = mixer.blend(Exam, status=Exam.READY_PRINT, category=Exam.EXAM, random_alternatives=False, random_questions=False, is_abstract=False, is_english_spanish=False)
            exam.coordinations.set(coordinations)
            
            teacher = mixer.blend(Inspector)
            teacher_subject = mixer.blend(TeacherSubject, teacher=teacher, subject=Subject.objects.filter(client__isnull=True).order_by('?').first())
            exam_teacher_subject = mixer.blend(ExamTeacherSubject, grade=Grade.objects.filter(level__in=[1,2,3,4,5,6,7,8,9]).order_by('?').first(), exam=exam, teacher_subject=teacher_subject)
            
            for i in range(10):
                exam_question = mixer.blend(ExamQuestion, order=i, exam=exam, is_abstract=False, question=Question.objects.filter(coordinations__in=coordinations, is_public=False, category=Question.CHOICE, alternatives__is_correct=True, alternatives__isnull=False).order_by('?').first(), exam_teacher_subject=exam_teacher_subject)
                StatusQuestion.objects.create(
                    exam_question=exam_question,
                    status=StatusQuestion.APPROVED
                )
                
            classes = SchoolClass.objects.filter(coordination__unity__client=client, id_erp__isnull=False, school_year=timezone.now().year)
            students = Student.objects.filter(pk__in=classes.values_list('students', flat=True)).distinct()

            application = mixer.blend(Application, exam=exam, date=timezone.now().date(), start=(timezone.now() - timedelta(hours=2)).time(), end=(timezone.now() - timedelta(hours=1)).time())
            application.school_classes.set(classes)
            application.students.set(students)
            
            if kwargs['create_answers']:
                
                exam_questions = exam.examquestion_set.all().availables().distinct()
                
                applications_student = application.applicationstudent_set.all().distinct()
                
                for application_student in applications_student:
                    for exam_question in exam_questions:
                        mixer.blend(
                            OptionAnswer, 
                            student_application=application_student, 
                            question_option=QuestionOption.objects.filter(
                                Q(question=exam_question.question),
                                Q(is_correct=True) if kwargs['all_answers_is_correct'] else Q()
                            ).order_by('?').first()
                        )