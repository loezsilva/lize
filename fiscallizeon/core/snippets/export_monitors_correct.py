import csv
import datetime
from pytz import timezone
from fiscallizeon.answers.models import FileAnswer, TextualAnswer
from fiscallizeon.exams.models import ExamQuestion

date = datetime.datetime(2022, 8, 30, 00, 00, 00, tzinfo=timezone('America/Recife'))
date_end = datetime.datetime(2022, 10, 2, 00, 00, 00, tzinfo=timezone('America/Recife'))

fa = FileAnswer.objects.filter(
  updated_at__gte=date,
  updated_at__lte=date_end, 
  who_corrected__isnull=False, 
  student_application__student__client__name__icontains="ph",

).only("question", "who_corrected", "student_application", "updated_at").distinct()

ta = TextualAnswer.objects.filter(
  updated_at__gte=date, 
  updated_at__lte=date_end,  
  who_corrected__isnull=False, 
  student_application__student__client__name__icontains="ph"
).only("question", "who_corrected", "student_application", "updated_at").distinct()

totals = fa.union(ta).order_by("updated_at")

print("totals", totals.count())

def number_print_question(question, exam):
  all_exam_questions = ExamQuestion.objects.filter(
    exam=exam, question__number_is_hidden=False
  ).availables().order_by(
        'exam_teacher_subject__order', 'order'
  ).values("pk")
  active_exam_question = ExamQuestion.objects.filter(
    question=question,
    exam=exam
  ).availables().first().pk
  
  for index, exam_question in enumerate(all_exam_questions, 1):
    if active_exam_question == exam_question["pk"]:
      if exam.is_english_spanish and index >= 6:
        return index - 5 + exam.start_number - 1
      return index + exam.start_number - 1

with open('tmp/ph-redacao.csv', 'w') as csvfile:
  fieldnames = ['monitor', 'iniciou', 'email', 'data', 'hora', 'aluno', 'caderno', 'disciplina', 'questão']
  writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
  writer.writeheader()
  count = 1
  for total in totals:
    result = {
      'monitor':total.who_corrected.name,
      'iniciou': "sim" if total.student_application.start_time else "não",
      'email':total.who_corrected.email,
      'data':total.updated_at.date(),
      'hora':total.updated_at.time(),
      'aluno':total.student_application.student.name,
      'caderno':total.student_application.application.exam.name,
      'disciplina': total.question.subject.name,
      'questão': total.student_application.application.exam.number_print_question(total.question)
    }
    writer.writerow(result)
    print(count, "-----")
    count = count + 1
