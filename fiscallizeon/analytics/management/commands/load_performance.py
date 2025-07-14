import csv
import progressbar

from datetime import datetime
from django.core.management.base import BaseCommand

from django.db.models import Q, Count

from fiscallizeon.questions.models import Question
from fiscallizeon.inspectors.models import TeacherSubject
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.analytics.models import ApplicationStudentLevelQuestion
from fiscallizeon.applications.models import Application, ApplicationStudent

class Command(BaseCommand):
    help = 'Command para carregar performance de aplicações que ainda não foram importadas'

    # def add_arguments(self, parser):
    #     parser.add_argument('client_id', nargs=1, type=str)

    def handle(self, *args, **kwargs):
        application_students = ApplicationStudent.objects.filter(
            start_time__isnull=False, 
            # end_time__isnull=False, 
            application__exam__isnull=False,
            # application__exam__coordinations__unity__client__pk="86ba20fe-3822-4f72-ab9a-01720bf93662"
        ).order_by('application__date', 'application__start').distinct()

        application_student_level_question = ApplicationStudentLevelQuestion.objects.all().order_by('application_student__application__date', '-application_student__application__start').last()
        
        if application_student_level_question:
            application_students = application_students.filter(
                Q(
                    Q(application__date__gt=application_student_level_question.application_student.application.date) |
                    Q(
                        Q(application__date=application_student_level_question.application_student.application.date) &
                        Q(application__start__gte=application_student_level_question.application_student.application.start)
                    )
                )  
            ).distinct()

        application_students_count = int(application_students.count())

        print("###", application_students_count)

        bar = progressbar.ProgressBar(maxval=application_students_count, \
            widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
        
        bar.start()     

        for index, application_student in enumerate(application_students):       
            try:
                for teacher_subject in application_student.application.exam.teacher_subjects.all():
                    question_levels = list(ExamQuestion.objects.filter(
                            exam_teacher_subject__teacher_subject=teacher_subject,
                            exam=application_student.application.exam
                        ).values_list('question__level', flat=True)
                    )
                
                    for question_level in question_levels:
                        if not ApplicationStudentLevelQuestion.objects.filter(
                            application_student=application_student,
                            teacher_subject=teacher_subject,
                            level=question_level
                        ).exists():
                            performance = ApplicationStudent.objects.filter(
                                    pk=application_student.pk
                                ).get_average_grade(
                                    level=question_level, 
                                    teacher_subject=teacher_subject
                                )

                            ApplicationStudentLevelQuestion.objects.create(
                                application_student=application_student,
                                teacher_subject=teacher_subject,
                                level=question_level,
                                performance=performance
                            )

            except Exception as e:
                print(f'Erro - {index} - {application_student.pk} - {e}')
                    
            bar.update(index+1)

        bar.finish()
