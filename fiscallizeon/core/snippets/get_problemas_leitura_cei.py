import csv

from django.db.models import Count

from fiscallizeon.exams.models import Exam
from fiscallizeon.questions.models import Question
from fiscallizeon.applications.models import ApplicationStudent

exams = Exam.objects.filter(
    coordinations__unity__client='60c76b23-e58e-44de-997f-821f3b26993d', 
    coordinations__high_school=True, 
    application__date__gte='2022-05-25'
).distinct()


with open('problemas.csv', 'a') as arquivo:
    arquivo_writer = csv.writer(arquivo, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    for exam in exams:
        total_choice_questions = exam.questions.availables(exam).filter(category=Question.CHOICE).count()
        application_students = ApplicationStudent.objects.annotate(
            objetivas=Count('option_answers', distinct=True),
        ).filter(
            application__exam=exam,
            is_omr=True,
            objetivas__lt=total_choice_questions
        )
        for application_student in application_students:
            student_url = f'https://app.lizeedu.com.br/provas/{exam.pk}?turma=all#{application_student.pk}'
            arquivo_writer.writerow([exam.name, application_student.student.name, application_student.objetivas, total_choice_questions, student_url])