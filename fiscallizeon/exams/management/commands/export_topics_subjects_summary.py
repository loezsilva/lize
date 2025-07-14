from django.core.management.base import BaseCommand

from fiscallizeon.students.models import Student

from fiscallizeon.subjects.models import Topic

from statistics import fmean

from fiscallizeon.classes.models import SchoolClass, Grade

import csv

from django.utils import timezone

from fiscallizeon.applications.models import ApplicationStudent


class Command(BaseCommand):
    help = 'Mistura alternativas das questões discursivas de uma prova'

    def add_arguments(self, parser):
        parser.add_argument('--year', default=timezone.now().year - 1)
        parser.add_argument('--client', default='60c76b23-e58e-44de-997f-821f3b26993d')

    def handle(self, *args, **kwargs):
        
        year = kwargs['year']
        client_id = kwargs['client']
        students = Student.objects.filter(classes__school_year=year, classes__grade__level__in=[Grade.ELEMENTARY_SCHOOL, Grade.ELEMENTARY_SCHOOL_2], applicationstudent__isnull=False, applicationstudent__application__date__year=year, client=client_id).distinct()
        topics = Topic.objects.filter(questions__exams__in=students.values('applicationstudent__application__exam')).order_by('subject__name').distinct()

        header = ["Assunto"]
        
        with open('ensino_fundamental.csv', 'w') as csvfile:

            for student in students:
                
                classe = student.classes.filter(school_year=year).first()
                
                header.append(f"{student.enrollment_number}{'-'+ classe.grade.name if classe else ''}")
                
            
            writer = csv.writer(csvfile, delimiter=',')
            
            writer.writerow(header)

            for topic in topics:
                
                row = [f"{topic.subject.name} - {topic.name}"]
                
                for student in students:
                    
                    applications_students = ApplicationStudent.objects.filter(
                        application__date__year=year, student=student,
                        application__exam__questions__topics=topic
                    ).distinct()
                    
                    if not applications_students:
                        row.append(0)
                        continue
                    
                    topic_performances = []
                    
                    for application_student in applications_students:
                        
                        if performance := application_student.get_performance(bncc_pk=topic.pk):
                        
                            topic_performances.append(performance) if performance else 0
                    
                    row.append(str("%.1f" % fmean(topic_performances) if len(topic_performances) else 0))

                writer.writerow(row)