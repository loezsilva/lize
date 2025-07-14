import csv

from django.db.models.aggregates import Avg
from fiscallizeon.classes.models import SchoolClass
import progressbar

from datetime import datetime
from django.core.management.base import BaseCommand

from django.db.models import Q, Count

from fiscallizeon.questions.models import Question
from fiscallizeon.inspectors.models import TeacherSubject
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.analytics.models import ApplicationStudentLevelQuestion, ClassSubjectApplicationLevel
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.clients.models import Client

from django.utils import timezone


class Command(BaseCommand):
    help = 'Command para carregar performance de aplicações que ainda não foram importadas de uma escola específica e por turma e nível de questão.'

    # def add_arguments(self, parser):
    #     parser.add_argument('date_application', nargs=1, type=str)

    def handle(self, *args, **kwargs):
        clients = Client.objects.filter(
            has_dashboard=True
        )

        for index, client in enumerate(clients):

            applications = Application.objects.using('readonly').filter(
                exam__isnull=False,
                exam__coordinations__unity__client=client,
                category=Application.PRESENTIAL,
                date__year=timezone.now().year,
                date__lte=timezone.now().date(),
                applicationstudent__is_omr=True            
            ).order_by('date').distinct()

            applications.count()

            application_level_question = set(list(ClassSubjectApplicationLevel.objects.using('readonly').filter(
                application__exam__coordinations__unity__client=client,
                application__category=Application.PRESENTIAL,
                application__date__year=timezone.now().year,
            ).distinct("application__pk").values_list("application__pk", flat=True)))

            print("application_level_question: ", len(application_level_question))

            if application_level_question:
                applications = applications.using('readonly').exclude(
                    Q(
                        pk__in=application_level_question
                    )  
                ).distinct()
            
            bar_applications = progressbar.ProgressBar(
            maxval=applications.count(), 
            widgets=[
                    progressbar.Bar('=', '[', ']'), 
                    ' ', 
                    progressbar.Percentage()
                ]
            )
            
            print(f'\nProcessando {applications.count()} aplicações do cliente: {client.name}')
            bar_applications.start() 

            print("application_count", applications.count())

            for index_application, application in enumerate(applications):
                teacher_subjects = application.exam.teacher_subjects.all().distinct()
                try:
                    school_classes = SchoolClass.objects.using('readonly').filter(
                        students__applicationstudent__application=application,
                        class_type=SchoolClass.REGULAR,
                        school_year=timezone.now().year
                    ).distinct()

                    print("techaer_subject_count", teacher_subjects.count())

                    for teacher_subject in teacher_subjects:
                        question_levels = set(list(ExamQuestion.objects.using('readonly').filter(
                                exam_teacher_subject__teacher_subject=teacher_subject,
                                exam=application.exam
                            ).values_list('question__level', flat=True)
                        ))   

                        print("question_levels: ", question_levels)

                        for level in question_levels:
                            for classe in school_classes:
                                students = application.applicationstudent_set.using('readonly').all().filter(
                                    student__classes=classe,
                                    is_omr=True
                                ).distinct()
                                
                                if students:
                                    performance, created = ClassSubjectApplicationLevel.objects.using('default').get_or_create(
                                        application=application,
                                        teacher_subject=teacher_subject,
                                        level=level,
                                        school_class=classe,
                                        students_quantity=students.count(),
                                        defaults={
                                            "performance": students.get_average_grade(
                                                level=level, 
                                                teacher_subject=teacher_subject
                                            )
                                        }
                                    )
                    print("-----------------------------------------------------")
                except Exception as e:
                    print(f'Erro - {index_application} - {application.pk} - {e}')
                
                bar_applications.update(index_application+1)

            bar_applications.finish()