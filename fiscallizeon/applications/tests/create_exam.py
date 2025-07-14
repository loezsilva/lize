from django.utils import timezone

from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.exams.models import Exam, ExamTeacherSubject, ExamQuestion
from fiscallizeon.inspectors.models import TeacherSubject
from fiscallizeon.questions.models import Question
from fiscallizeon.clients.models import SchoolCoordination
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.students.models import Student

coordination = SchoolCoordination.objects.get(pk='5b632224-4598-424c-9095-14b91b8d3e7b')

teacher_subject1 = TeacherSubject.objects.get(pk='12a78f64-7801-4580-a266-428ea8e6fba6') #Geografia
teacher_subject2 = TeacherSubject.objects.get(pk='47cfede1-a6a9-4572-9501-08b2bb10577e') #Matemática

exam, _ = Exam.objects.get_or_create(
    name='Exame de Teste de randomização',
    random_alternatives=True,
    random_questions=True,
)

exam.coordinations.add(coordination)

exam_teacher_subject1, _ = ExamTeacherSubject.objects.get_or_create(
    teacher_subject=teacher_subject1,
    exam=exam,
    order=0,
    quantity=4,
)
exam_teacher_subject2, _ = ExamTeacherSubject.objects.get_or_create(
    teacher_subject=teacher_subject2,
    exam=exam,
    order=1,
    quantity=4,
)

exam_question1 = ExamQuestion.objects.get_or_create(
    question=Question.objects.get(pk='7cac3abb-51ae-4bd2-a7c7-e492a6058280'),
    exam=exam,
    exam_teacher_subject=exam_teacher_subject1,
    order=0
)
exam_question2 = ExamQuestion.objects.get_or_create(
    question=Question.objects.get(pk='7596d678-4390-4dd4-b8e0-2dd38dbff7bb'),
    exam=exam,
    exam_teacher_subject=exam_teacher_subject1,
    order=1
)
exam_question3 = ExamQuestion.objects.get_or_create(
    question=Question.objects.get(pk='6ad43c7e-f459-40c6-9397-22d2737b24ef'),
    exam=exam,
    exam_teacher_subject=exam_teacher_subject1,
    order=2
)
exam_question4 = ExamQuestion.objects.get_or_create(
    question=Question.objects.get(pk='33f2df75-6b25-4fa4-b337-4c1f2e42d45d'),
    exam=exam,
    exam_teacher_subject=exam_teacher_subject1,
    order=3
)
exam_question5 = ExamQuestion.objects.get_or_create(
    question=Question.objects.get(pk='cde6aa1d-7a83-4b98-834f-9a9e64f9ad31'),
    exam=exam,
    exam_teacher_subject=exam_teacher_subject2,
    order=0
)
exam_question6 = ExamQuestion.objects.get_or_create(
    question=Question.objects.get(pk='4c9e2b85-7819-4b53-9cb2-844e5c808407'),
    exam=exam,
    exam_teacher_subject=exam_teacher_subject2,
    order=1
)
exam_question7 = ExamQuestion.objects.get_or_create(
    question=Question.objects.get(pk='71f4c7ff-5d0d-4efa-9844-8e06c81a710e'),
    exam=exam,
    exam_teacher_subject=exam_teacher_subject2,
    order=2
)
exam_question8 = ExamQuestion.objects.get_or_create(
    question=Question.objects.get(pk='268686ed-a818-423b-bba3-e9c541e58219'),
    exam=exam,
    exam_teacher_subject=exam_teacher_subject2,
    order=3
)

exam.teacher_subjects.set([teacher_subject1, teacher_subject2])

application, _ = Application.objects.get_or_create(
    date='2023-04-30',
    start='00:00:00',
    end='23:59:59',
    exam=exam,
    category=Application.PRESENTIAL
)

school_class = SchoolClass.objects.get(pk='f6436442-71d6-46b6-ad41-d9b58d7bff5c')
application.school_classes.set([school_class])

application_student_1, _ = ApplicationStudent.objects.get_or_create(
    application=application,
    student=school_class.students.get(pk='64d44758-16fa-473a-87e9-a206f73b92f5'),
)

application_student_2, _ = ApplicationStudent.objects.get_or_create(
    application=application,
    student=school_class.students.get(pk='fdf055b6-853c-416f-bf32-3061de174bc8'),
)

application_student_3, _ = ApplicationStudent.objects.get_or_create(
    application=application,
    student=school_class.students.get(pk='ba5939ac-d29e-4425-b020-ff3909c6105f'),
)