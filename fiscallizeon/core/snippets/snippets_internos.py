from django.db.models import Q

from fiscallizeon.clients.models import Client, Unity
from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import Grade

clients = Client.objects.all()

for c in clients:
    students = Student.objects.filter(client=c, user__is_active=True)
    fund1 = students.filter(classes__school_year=2024, classes__grade__level=Grade.ELEMENTARY_SCHOOL).distinct().count()	
    fund2 = students.filter(classes__school_year=2024, classes__grade__level=Grade.ELEMENTARY_SCHOOL_2).distinct().count()	
    medio = students.filter(classes__school_year=2024, classes__grade__level=Grade.HIGHT_SCHOOL).distinct().count()	
    semturma = students.filter(classes__isnull=True).count()
    unities = Unity.objects.filter(client=c).distinct().count()
    print(f'{c.name}, {unities}, {fund1}, {fund2}, {medio}, {semturma}')4




from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.answers.models import OptionAnswer


apps = ApplicationStudent.objects.filter(
    application="4f34c7b6-8e9b-435c-85a0-b33cd113f222"
)

for app in apps:
    count_ing = OptionAnswer.objects.filter(
        student_application=app, 
        status=OptionAnswer.ACTIVE,
        question_option__question__subject__name__icontains="ingl"
    ).count()
    if count_ing > 0:
        app.foreign_language = ApplicationStudent.ENGLISH
        app.save()
        continue
    count_esp = OptionAnswer.objects.filter(
        student_application=app, 
        status=OptionAnswer.ACTIVE,
        question_option__question__subject__name__icontains="espanh"
    ).count()
    if count_esp > 0:
        app.foreign_language = ApplicationStudent.SPANISH
        app.save()
    


    print(f'{app.student.name}, {app.student.enrollment_number}, {app.student.get_last_class()}, {app.student.get_last_class().coordination.unity.name}, {count_ing}, {count_esp}')


    GERAR PLANILHA DE PENDÊNCIAS

from django.db.models import Q
from fiscallizeon.exams.models import Exam, StatusQuestion
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.questions.models import Question
from fiscallizeon.answers.models import OptionAnswer, FileAnswer, TextualAnswer

from fiscallizeon.clients.models import Unity

unities = Unity.objects.filter(
   client__name__icontains="decis",
)

for unity in unities:
    # print(unity)
    inspectors = Inspector.objects.filter(
        user__is_active=True,
        teachersubject__classes__coordination__unity=unity,
        name__icontains="adilson"
    ).distinct()
    for inspector in inspectors:
        print(unity, inspector)
        teacher_subjects = inspector.teachersubject_set.filter(
            classes__school_year=2025
        ).distinct()
        for teacher_subject in teacher_subjects:
            # print(unity, inspector, teacher_subject)
            classes = SchoolClass.objects.filter(
                school_year=2025,
                teachersubject=teacher_subject,
                coordination__unity=unity,
            ).distinct()
            subject = teacher_subject.subject
            print(classes)
            for school_class in classes:
                # print(unity, inspector, teacher_subject, school_class)
                selected_exams = Exam.objects.filter(
                    # created_at__year=2025,
                    # teaching_stage__name="P2",
                    # application__school_classes=school_class,
                    # examteachersubject__teacher_subject__subject=subject,
                    name="P2_Química Unificada_M3_SAS_2025"
                ).distinct()
                for exam in selected_exams:
                    # print(unity, inspector, teacher_subject, school_class, exam)
                    count_choice_questions = (
                        exam.examquestion_set.all()
                        .availables(exclude_annuleds=True)
                        .filter(question__category=Question.CHOICE)
                        .count()
                    )
                    # print("count_choice_questions", count_choice_questions)
                    count_discursive_questions = (
                        exam.examquestion_set.all()
                        .availables(exclude_annuleds=True)
                        .filter(question__category__in=[Question.TEXTUAL, Question.FILE]) 
                        .count()
                    )
                    application_students = ApplicationStudent.objects.filter(
                        student__classes=school_class,
                        application__exam=exam,
                        missed=False
                    ).distinct()
                    count_students = application_students.count()
                    # print("count_students", count_students)
                    # through_model = ApplicationStudent._meta.get_field(
                    #     'empty_questions'
                    # ).remote_field.through
                    # count_blank_choice_answers = through_model.objects.filter(
                    #     applicationstudent__in=application_students
                    # ).count()
                    total_pendences_choice = count_students * count_choice_questions
                    total_pendence_discursive = count_students * count_discursive_questions
                    questions_annuleds  = Question.objects.filter(
                        examquestion__exam=exam,
                        examquestion__statusquestion__active=True,
                        examquestion__statusquestion__status=StatusQuestion.ANNULLED,
                    ).distinct()
                    total_choice_answers = (
                        OptionAnswer.objects.filter(
                            status=OptionAnswer.ACTIVE,
                            student_application__missed=False,
                            student_application__application__exam=exam,
                            student_application__student__classes=school_class,
                        )
                        .exclude(question_option__question__in=questions_annuleds)
                        .distinct()
                        .count()
                    )
                    # print("total_choice_answers", total_choice_answers)
                    total_discursive_answers = FileAnswer.objects.filter(
                        Q(student_application__application__exam=exam),
                        Q(student_application__missed=False),
                        Q(student_application__student__classes=school_class),
                        Q(
                            Q(teacher_grade__isnull=False) |
                            Q(empty=True)
                        ),
                    ).exclude(
                        exam_question__question__in=questions_annuleds
                    ).count() + TextualAnswer.objects.filter(
                        Q(student_application__application__exam=exam),
                        Q(student_application__missed=False),
                        Q(student_application__student__classes=school_class),
                        Q(
                            Q(teacher_grade__isnull=False) |
                            Q(empty=True)
                        ),
                    ).exclude(
                        exam_question__question__in=questions_annuleds
                    ).count()
                    total_pendence_choice = (
                        total_pendences_choice
                        - total_choice_answers
                        # - count_blank_choice_answers
                    )
                    total_pendence_discursive = (
                        total_pendence_discursive - total_discursive_answers
                    )
                    if total_pendence_choice != 0 or total_pendence_discursive != 0:
                        print(
                            f'{unity.name},{inspector.name},{exam.name},{school_class.name},{total_pendence_choice},{total_pendence_discursive}'
                        )