from fiscallizeon.exams.models import ExamQuestion, Exam
from fiscallizeon.answers.models import OptionAnswer
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.questions.models import QuestionOption

from django.db.models import Q

#### Adiciona repostas às questões que foram anuladas e não possuem respostas

exam_question = ExamQuestion.objects.get(pk='2e3c612c-133d-49a4-af1d-ca5bb0b9e5c6')

application_students = ApplicationStudent.objects.filter(    
    Q(
        Q(start_time__isnull=False) |
        Q(is_omr=True)
    ),
    application__exam=exam_question.exam,
)

option_answer = OptionAnswer.objects.filter(        
    question_option__question=exam_question.question,
    status=OptionAnswer.ACTIVE
).distinct()


for application_student in application_students:
    option_answer = OptionAnswer.objects.filter(
        student_application=application_student,
        question_option__question=exam_question.question,
        status=OptionAnswer.ACTIVE
    )

    if not option_answer:
        option_answer = OptionAnswer.objects.create(
            student_application=application_student,
            question_option=exam_question.question.alternatives.first(),            
            status=OptionAnswer.ACTIVE,
        )
        print(f"Criada resposta para aluno {application_student.student}")
    else:
        print(f'Aluno {application_student.student} já respondeu questão')



### Move respostas objetivas de uma prova para outra (duplicada/copia)


old_exam = Exam.objects.get(pk='16f90519-4cdb-432c-b80c-f5d6e7f357cd')
new_exam = Exam.objects.get(pk='16055b3a-e575-479f-aeec-98c05f277a61')
application_students = ApplicationStudent.objects.filter(application__exam=new_exam)

for application_student in application_students:
    for question in old_exam.questions.all():
        answers = OptionAnswer.objects.filter(
            student_application=application_student,
            question_option__question=question
        )

        for answer in answers:
            new_question_option = new_exam.questions.filter(source_question=question).first().alternatives.filter(
                text=answer.question_option.text
            ).first()
            answer.question_option = new_question_option
            answer.save()