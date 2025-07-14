import csv

from django.db.models.aggregates import Avg
from fiscallizeon.classes.models import SchoolClass
import progressbar
from django.utils import timezone

from datetime import datetime
from django.core.management.base import BaseCommand

from django.db.models import Q, Count

from fiscallizeon.questions.models import Question
from fiscallizeon.inspectors.models import TeacherSubject
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.analytics.models import ApplicationStudentLevelQuestion, ClassSubjectApplicationLevel
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.clients.models import Client

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
                Q(exam__isnull=False),
                Q(date__year=2022),
                Q(date__lte=timezone.now().date()),
                Q(exam__coordinations__unity__client=client),
                Q(
                    Q(                    
                        Q(category=Application.MONITORIN_EXAM) |
                        Q(applicationstudent__start_time__isnull=False)
                    ) | 
                    Q(
                        Q(category=Application.HOMEWORK),
                        Q(
                            Q(applicationstudent__option_answers__isnull=False) |
                            Q(applicationstudent__textual_answers__isnull=False) |
                            Q(applicationstudent__file_answers__isnull=False)
                        )
                    )
                )     
            ).exclude(
                category=Application.PRESENTIAL
            ).order_by('date').distinct()

            application_level_question = set(list(ClassSubjectApplicationLevel.objects.using('readonly').filter(
                application__exam__coordinations__unity__client=client
            ).distinct("application__pk").values_list("application__pk", flat=True)))

            if application_level_question:
                applications = applications.using('readonly').exclude(
                    pk__in=application_level_question
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


            for index_application, application in enumerate(applications):
                teacher_subjects = application.exam.teacher_subjects.all()
                try:
                    school_classes = SchoolClass.objects.using('readonly').filter(
                        students__applicationstudent__application=application,
                        class_type=SchoolClass.REGULAR,
                        school_year=timezone.now().year
                    ).distinct()

                    for teacher_subject in teacher_subjects:
                        question_levels = set(list(ExamQuestion.objects.using('readonly').filter(
                                exam_teacher_subject__teacher_subject=teacher_subject,
                                exam=application.exam
                            ).values_list('question__level', flat=True)
                        ))

                        for level in question_levels:

                            for classe in school_classes:
                                
                                students = application.applicationstudent_set.using('readonly').all().filter(
                                    Q(student__classes=classe),
                                    Q(
                                        Q(
                                            Q(application__category=Application.MONITORIN_EXAM),
                                            Q(start_time__isnull=False), 
                                            Q(end_time__isnull=False)
                                        ) |
                                        Q(
                                            Q(application__category=Application.HOMEWORK),
                                            Q(
                                                Q(optionanswer__isnull=False) |
                                                Q(textualanswer__isnull=False) |
                                                Q(fileanswer__isnull=False)
                                            )
                                        )
                                    )
                                ).distinct()
                                
                                if students:
                                    performance, created = ClassSubjectApplicationLevel.objects.get_or_create(
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
                except Exception as e:
                    print(f'Erro - {index_application} - {application.pk} - {e}')
                
                bar_applications.update(index_application+1)

            bar_applications.finish()