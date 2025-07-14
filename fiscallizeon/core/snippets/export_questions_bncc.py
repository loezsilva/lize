import csv
from django.utils import timezone
from django.db.models import Q
from fiscallizeon.exams.models import Exam, ExamQuestion
from fiscallizeon.core.templatetags.increment import number_print_question
date_first_day_of_year = timezone.datetime(year=timezone.now().year, month=1, day=1)
exams = Exam.objects.filter(
    Q(application__isnull=False),
    Q(
        Q(application__applicationstudent__start_time__isnull=False) |
        Q(application__applicationstudent__is_omr=True)
    ),
    Q(application__date__gte=date_first_day_of_year.date()),
    Q(application__date__lte=timezone.localtime(timezone.now()).date()),
    Q(coordinations__unity__client__name__icontains="CEI")
).distinct()
with open('exams_2.csv', 'w', encoding='UTF8', newline='') as f:
    header = ["Exame", "Questão", "Disciplina", "Tipo", "Conteúdo"]
    writer = csv.writer(f)
    writer.writerow(header)
    for exam in exams:
        questions = all_exam_questions = ExamQuestion.objects.filter(
            exam=exam, 
            question__number_is_hidden=False
        ).availables().order_by('exam_teacher_subject__order', 'order')
        for index_question, exam_question in enumerate(questions):
            question = exam_question.question
            topics = question.topics.all()
            abilities = question.abilities.all()
            competences = question.competences.all()
            subject_name = question.subject.name if question.subject else ''
            exam_name = exam.name
            number_question = exam.number_print_question(question)
            for topic in topics:
                writer.writerow([exam_name, number_question, subject_name, "Assunto", topic.name])
            for abilitie in abilities:
                code = f'({abilitie.code}) ' if abilitie.code else ''
                result_abilities = f'{code}{abilitie.text}'
                writer.writerow([exam_name, number_question, subject_name, "Habilidade", result_abilities])
            for competence in competences:
                code = f'({competence.code}) ' if competence.code else ''
                result_competences = f'{code}{competence.text}'
                writer.writerow([exam_name, number_question, subject_name, "Competência", result_competences])