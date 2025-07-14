#remover respostas duplicadas
from fiscallizeon.answers.models import FileAnswer, TextualAnswer, OptionAnswer

pk_exams = [
    "ab0b1d84-c647-43a4-87c0-2471c75c562e",
    "cd8d1007-9b7f-47fe-a2b8-cec325609f3a"
]

answers = (
    TextualAnswer.objects.filter(
        student_application__application__exam__in=pk_exams,
    )
    .order_by("-created_at")
    .distinct()
)

#para discursivas
pks_delete_answers = []
for a in answers:
    if a.pk in pks_delete_answers:
        continue
    textual_answer = TextualAnswer.objects.filter(
        question=a.question,
        student_application=a.student_application
    ).exclude(pk=a.pk)
    file_answer = FileAnswer.objects.filter(
        question=a.question,
        student_application=a.student_application
    ).exclude(pk=a.pk)
    if textual_answer :
        print("textual", a.student_application.student.name, a.created_at, textual_answer.first().created_at)
        pks_delete_answers.extend(list(textual_answer.values_list("pk", flat=True)))
        textual_answer.delete()
    if file_answer:
        print("file", a.student_application.student.name, a.created_at, file_answer.first().created_at)
        pks_delete_answers.extend(list(file_answer.values_list("pk", flat=True)))
        file_answer.delete()



from fiscallizeon.answers.models import FileAnswer, TextualAnswer, OptionAnswer
pks_delete_answers = []

pk_exams = [
    "ab0b1d84-c647-43a4-87c0-2471c75c562e",
    "cd8d1007-9b7f-47fe-a2b8-cec325609f3a",
]

answers = (
    OptionAnswer.objects.filter(
        student_application__application__exam_id__in=pk_exams,
        status=OptionAnswer.ACTIVE,
    )
    .order_by("-created_at")
    .distinct()
)

for a in answers:
    if a.pk in pks_delete_answers:
        continue
    same_option_answer = OptionAnswer.objects.filter(
        question_option__question=a.question_option.question,
        student_application=a.student_application,
        status=OptionAnswer.ACTIVE
    ).exclude(
        pk=a.pk
    )
    if same_option_answer:
        pks_delete_answers.extend(same_option_answer.values_list("pk", flat=True))
        print("objetiva", a.student_application.student.name, a.created_at, same_option_answer.first().created_at)
        same_option_answer.update(status=OptionAnswer.INACTIVE)



# detectar questões alteradas após fechamento do caderno
from fiscallizeon.exams.models import Exam, ExamQuestion
from fiscallizeon.applications.models import Application
from django.db.models import Subquery, OuterRef, DateField, Prefetch

exams = Exam.objects.filter(
    status=Exam.CLOSED,
    coordinations__unity__client="16d02aad-91cf-49a5-b8e4-a05cafc5952e",
    created_at__date__gte="2024-05-01"
).distinct()

from fiscallizeon.questions.models import Question
for exam in exams:
    application = Application.objects.filter(exam=exam).order_by('date').first()
    application_date = application.date.strftime('%d-%m-%Y') if application else "-"
    date_exam_closed = exam.history.filter(status=Exam.CLOSED).order_by('history_date').first().history_date
    history_exam = exam.history.filter(history_date__lt=date_exam_closed).order_by('history_date').last()
    questions = Question.objects.filter(examquestion__exam=exam, updated_at__gt=date_exam_closed).distinct()
    questions_count = questions.count()
    if questions_count:
        list_questions = []
        for question in questions:
            for change in question.changes():
                if "enunciado" in change['fields'].lower() and change['history_user'] and change['history_date'] > date_exam_closed:
                    exam_questions = ExamQuestion.objects.filter(question=question).order_by('created_at')
                    if exam_questions.count() > 1:
                        try:
                            print(f'{exam.name}, {application_date}, {exam.number_print_question(question)}, {str(question.pk)}, {change["history_user"]}')
                        except:
                            pass
                        # for index, exam_question in enumerate(exam_questions):
                        #     if index == 0:
                        #         continue
                        #     exam_question.question = exam_question.question.duplicate_question(exam_question.exam_teacher_subject.teacher_subject.teacher.user)
                        #     exam_question.save(skip_hooks=True)
                    break




