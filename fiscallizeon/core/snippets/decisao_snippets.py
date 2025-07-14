from fiscallizeon.applications.models import ApplicationStudent
from django.db.models import Subquery, OuterRef, Value, Q, Case, When, F
from django.db.models.functions import Substr
from fiscallizeon.classes.models import SchoolClass

applications_student = ApplicationStudent.objects.filter(
    Q(
        student__client='a2b1158b-367a-40a4-8413-9897057c8aa2',
        application__date__year=2023,
        application__exam__name__icontains="P1"
    )
).annotate(
    last_classe_name=Subquery(
        SchoolClass.objects.filter(pk__in=OuterRef('student__classes'), school_year=2023).order_by('-created_at').distinct().values('coordination__pk')[:1]
    ),
    exam_grade_name=Case(
        When(Q(application__exam__name__icontains="_M1"), then=Value("M1")),
        When(Q(application__exam__name__icontains="_M2"), then=Value("M2")),
        When(Q(application__exam__name__icontains="_M3"), then=Value("M3")),
        When(Q(application__exam__name__icontains="_F1"), then=Value("F1")),
        When(Q(application__exam__name__icontains="_F2"), then=Value("F2")),
        When(Q(application__exam__name__icontains="_F3"), then=Value("F3")),
        When(Q(application__exam__name__icontains="_F4"), then=Value("F4")),
        When(Q(application__exam__name__icontains="_F5"), then=Value("F5")),
        When(Q(application__exam__name__icontains="_F6"), then=Value("F6")),
        When(Q(application__exam__name__icontains="_F7"), then=Value("F7")),
        When(Q(application__exam__name__icontains="_F8"), then=Value("F8")),
        When(Q(application__exam__name__icontains="_F9"), then=Value("F9")),
        ),
    classe_first_letter=Substr('last_classe_name', 1, 2)
).exclude(
    Q(classe_first_letter=F('exam_grade_name'))
)

from django.db.models import Count
from fiscallizeon.applications.models import ApplicationStudent
from django.db.models import Subquery, OuterRef, Value, Q, Case, When, F
from django.db.models.functions import Coalesce
from fiscallizeon.subjects.models import Subject

application_students = ApplicationStudent.objects.filter(
    application__date__year=2023,
    application__exam__name__icontains="P1",
    student__client='a2b1158b-367a-40a4-8413-9897057c8aa2',
).annotate(
    last_subject=Subquery(
        Subject.objects.filter(
            pk__in=OuterRef('application__exam__teacher_subjects__subject')
        ).values('pk')[:1]
    )
).annotate(
    count=Coalesce(Subquery(
        ApplicationStudent.objects.filter(
            student=OuterRef('student'),
            application__date__year=2023,
            application__exam__name__icontains="P1",
            application__exam__teacher_subjects__subject__pk=OuterRef('last_subject')
        ).annotate(
            count_sub=Count('pk', distinct=True)
        ).values('count_sub')[:1]
    ), Value(1))
).filter(
    count__gt=1
)




applications_student = ApplicationStudent.objects.filter(
    Q(
        student__client='a2b1158b-367a-40a4-8413-9897057c8aa2',
        application__date__year=2023,
        application__exam__name__icontains="P1"
    )
).annotate(
    coordination_pk=Subquery(
        SchoolClass.objects.filter(pk__in=OuterRef('student__classes'), school_year=2023).order_by('-created_at').distinct().values('coordination__pk')[:1]
    )
).exclude(
    coordination_pk__in=F('application__exam__coordinations')
).distinct()

from fiscallizeon.students.models import Student

students = Student.objects.filter(
    client='a2b1158b-367a-40a4-8413-9897057c8aa2'
).annotate(
    count_sas=Subquery(
        ApplicationStudent.objects.filter(
            Q(
                Q(application__date__year=2023) &
                Q(student=OuterRef('pk')) &
                Q(application__exam__name__icontains="P1") &
                Q(application__exam__name__icontains="SAS")
            )
        ).annotate(
            count=Count('pk')
        ).values('count')[:1]
    ),
    count_anglo=Subquery(
        ApplicationStudent.objects.filter(
            Q(
                Q(application__date__year=2023) &
                Q(student=OuterRef('pk')) &
                Q(application__exam__name__icontains="P1") &
                Q(
                    Q(application__exam__name__icontains="ANGLO") |
                    Q(application__exam__name__icontains="OXFORD")
                )
            )
        ).annotate(
            count=Count('pk')
        ).values('count')[:1]
    )
).filter(
    count_sas__gt=0,
    count_anglo__gt=0
).distinct()

for student in students:
    applications = ApplicationStudent.objects.filter(
            Q(
                Q(student=student) &
                Q(application__date__year=2023) &
                Q(application__exam__name__icontains="P1")
            )
    ).exclude(
        Q(
            Q(application__exam__name__icontains="P1")
        )
    )
    sas = applications.filter(
        Q(
            application__exam__name__icontains="SAS"
        )
    )
    anglo = applications.filter(
        Q(
            Q(application__exam__name__icontains="ANGLO") |
            Q(application__exam__name__icontains="OXFORD")
        )
    )
    if sas.count() > anglo.count():
        for app in anglo:
            print(app.pk, ',', student.name, ',', app.application.exam.name)
    if anglo.count() > sas.count():
        for app in sas:
            print(app.pk, ',', student.name, ',', app.application.exam.name)

applications_student = ApplicationStudent.objects.filter(
    Q(
        student__client='a2b1158b-367a-40a4-8413-9897057c8aa2',
        application__date__year=2023,
        application__exam__name__icontains="P1",
        application__exam__name__icontains="SAS"
    )
).annotate(
    count_
).exclude(
    coordination_pk__in=F('application__exam__coordinations')
).distinct()

applications_student.count()


from fiscallizeon.omr.models import OMRStudents, OMRDiscursiveScan, OMRDiscursiveError

application_students_with_error=[
    "6126be1f-9c99-46e8-a244-9041772ee487","feff5e05-1404-45f9-b2cd-4f9ad07e8621","e34243b8-a0f2-47d1-8824-e9e73d6ce64e","9878301c-61df-40d1-9394-76a459acd8ff","cc029e29-e942-4aa3-be23-7f7f7b1e2514","cd9b1557-43f5-4d22-8b0d-5b0b5800a398","804f161f-9a3f-456c-b129-d1b01bbc9449","83aa8aa0-e212-4ef3-9ec9-839d7e84e3b9","a12d2dbf-341a-4e02-b64c-c3a74e758ba8","4c39d31f-8fba-4022-954a-9f474e8a30ca","258d4860-c531-48aa-9a2f-1f2e6f1866bb","a5dd4959-a34e-427f-ac46-518fea0d3b8c","07304ab8-b87c-4409-90d2-e06623f4149f","2316fcc1-ff93-420f-8d10-cac253c02801","bc69b871-d5e1-4f99-baec-b4ea14789639","c4d3d5a6-0fae-4dd0-980e-287e567d5566","a6ffd54a-38ba-4802-8b19-c30176031772","6c44a627-80df-4663-8bff-04507664c406","41303351-4c1a-44e2-870d-a74ca3bc84a1","4cd25afd-77c1-411b-ad1c-20c3cc894e10","e15df08b-aa77-483f-8d3a-56e3aa18e19b","038b489b-cd71-4634-ac19-b86b084b5022","56fafe42-bf1a-4ca9-b0d9-d378a55f8eac","96db03d5-ebe8-4694-af48-18c35d0f9e12","95feec79-fc4a-44ac-8014-41f2db008e72","6d563eed-0fec-47f3-8bbe-24d26db3e01a","6cb156b2-7af0-404d-89dc-38feb951daa8","c6edd20e-5dfb-414d-8f76-3e3dabec89af","f814697d-dc0d-48ca-9245-3ef37f39df18","f690374b-816a-4718-b0f9-46a34592ba44","e87e5118-98f0-40e3-93da-37376de78481","2608ec35-5f1a-4a71-9b1d-f0a66a83d765","9bdd01ae-c46b-4b18-926d-0571850150c8","8c46ff06-8d31-4951-8919-7d279604b6df","4c6d4b5b-cdaa-4a8a-84e8-fe490d0b4bb9","b5d882ac-3a3e-4809-bda4-9300a279a429","1d924a50-0d5b-4259-aeda-a91d6f068124","c567ea8e-e95e-428f-8019-e21d07a90ed9","10944649-20db-4389-a490-3d8b9599658a","4374de56-2049-45fb-855c-32ed3e07e290","e2f84abd-4cf3-4fa0-b39e-3be76bc1a94c","da738b7d-9e44-4b44-85c5-b8cde5667fb7","2b672474-ec97-4af2-9c43-081169ecb658","47ef9c57-eb80-4218-bd80-c1c59584207f","cd015379-1bab-46ad-b972-b732557cb7aa","d8e194c3-5dc1-4909-b8af-d5484b36434b","05c1ac19-d20f-43a6-a2b0-80f7935959a5","37104a9b-29dc-4a8b-9eb8-ad1b249f4a5b","c6c17316-9c94-421f-8e93-573950647774","177203d1-708e-4585-b12b-24b6cf2da5ef","49051326-2ca1-4437-b135-f33e13724ca4","4386d796-a36d-46b2-8423-09cbb50b8904","4df8c7a5-89a7-4074-b24b-9f7a97d8d847","294f9b01-1e6b-4abd-aec5-8f52d6031c86","5c70ebbb-d475-4d6b-a3d2-ce4ff807f672","6226c7e3-e640-4cf5-987e-43db44b82662","d4636021-802a-4528-9adc-a48e1a2eb087","3487a236-3b6b-4bc9-bac7-d23716c1b973","f5065d21-c744-44dd-88b8-4a42f8a30545","24cf1d93-29ec-4a6d-a648-be54880f9e41","b5185f06-6609-4b9d-80c0-2eb5a2a448fb","d9f5c7b3-6d53-4ce6-ad5d-701256499140","cd9b1557-43f5-4d22-8b0d-5b0b5800a398","c4d3d5a6-0fae-4dd0-980e-287e567d5566","95feec79-fc4a-44ac-8014-41f2db008e72","cd015379-1bab-46ad-b972-b732557cb7aa","4df8c7a5-89a7-4074-b24b-9f7a97d8d847","177203d1-708e-4585-b12b-24b6cf2da5ef","d4636021-802a-4528-9adc-a48e1a2eb087","d8c47a57-25d5-4223-a34c-acd2e1613b59","cc6cdeb9-41e3-4806-ac61-1b7aa7b5827f","f6067ee1-f1b6-43fd-9588-f6aa342d4e12","b5d882ac-3a3e-4809-bda4-9300a279a429","e2f84abd-4cf3-4fa0-b39e-3be76bc1a94c","106b935e-a294-41f1-9732-a3396153305b","35334159-26fa-4b50-8c97-f7052a58dee0","22a5dea2-22b8-4655-82eb-89eae394670d","6e2f2086-4fe4-492c-af4f-190000caac71","48e2802b-7f05-4921-b3d7-df57565ab5f8","85f70f91-e109-48d7-8e6a-8b4934548747","875d8263-3c23-40c8-839e-ea01da4d0f9c","4012cad0-1a0b-42a0-be4f-85e4b031a52a","6ea5426d-55d1-4a55-801d-e8611e07f275","418e1ace-1168-4dd7-8fc5-fd176359c47e","6384135c-a4b7-42aa-902f-3fc0fdbc5007","2bdec872-f901-41ec-9f0f-4c349019c58a","53190967-2fd7-4e33-a0c4-4125f821dc25","f1ad5c97-237e-4eff-90db-2f220f0a02de","74fc7403-dfbb-44f8-bed1-befba2417397","e7b70fc9-4149-48f6-a050-5a9e96b95594","3ac53886-c54a-48ea-91cb-12c249f93e02"
]

from fiscallizeon.answers.models import OptionAnswer, FileAnswer, TextualAnswer

application_students_with_error = ["923dde2e-82e9-496d-bed6-447262161610","b2325a03-7781-4991-973c-b6c04fde85ef","13f47e1a-1c68-476b-8ece-1ab018931a54","aa87c7bc-1f70-428e-bc00-d7691c6ed66b"]
file_answers = FileAnswer.objects.filter(
    student_application__in=application_students_with_error
)
print("FILE ANSWERS", file_answers.count())
file_answers.delete()
textual_answers = TextualAnswer.objects.filter(
    student_application__in=application_students_with_error
)
print("TEXTUAL ANSWERS", textual_answers.count())
textual_answers.delete()
options = OptionAnswer.objects.filter(
    student_application__in=application_students_with_error
)
print("OPTION ANSWERS", options.count())
options.delete()
errors = OMRDiscursiveError.objects.filter(
    application_student__in=application_students_with_error
)
print("ERRORS OMRDiscursiveError", errors.count())
errors.delete()
apps = ApplicationStudent.objects.filter(
    pk__in=application_students_with_error
)
print("APPS ANSWERS", apps.count())
apps.delete()



























omr_students = OMRStudents.objects.filter(
    Q(application_student__in=application_students_with_error),
    Q(
        Q(scan_image__isnull=False) |
        Q(omrdiscursivescan__upload_image__isnull=False)
    )
).distinct()

omr_discursives = OMRDiscursiveScan.objects.filter(
    upload_image__isnull=False,
    omr_student__in=omr_students
).distinct()

for omr in omr_students:
    if omr.scan_image and bool(omr.scan_image):
        print(f'"{omr.scan_image.url}",')

for omr in omr_discursives:
    if omr.upload_image and bool(omr.upload_image):
        print(f'"{omr.upload_image.url}",')

    
print('id,aluno,prova,id_prova')
for application_student in applications_student:
    print(f'{str(application_student.id)},{application_student.student.name},{application_student.application.exam.name}, {application_student.application.exam.pk}')


students = ApplicationStudent.objects.filter(
    application__exam__name__icontains="P1",
    student__client='a2b1158b-367a-40a4-8413-9897057c8aa2',
    application__date__year=2023,
).annotate(
    count=Subquery(
        ApplicationStudent.objects.filter(
            application=OuterRef('application_id'),
            student=OuterRef('student_id')
        ).exclude(id=OuterRef('id')).values('application', 'student').annotate(
            count=Count('id')
        ).values('count')
    )
).filter(
    count__gt=0
)
students.count()


students = Student.objects.filter(
    client='a2b1158b-367a-40a4-8413-9897057c8aa2'
).annotate(
    count=Subquery(
        Student.objects.filter(
            enrollment_number=OuterRef('enrollment_number'),
            client='a2b1158b-367a-40a4-8413-9897057c8aa2',
        ).exclude(id=OuterRef('id')).values('enrollment_number').annotate(
            count=Count('id')
        ).values('count')[:1]
    )
).filter(
    count__gt=0
)


apps = ApplicationStudent.objects.filter(
    Q(student__client='a2b1158b-367a-40a4-8413-9897057c8aa2'),
    Q(application__exam__name__icontains="p1_"),
    Q(
        Q(application__exam__name__icontains="_M1") |
        Q(application__exam__name__icontains="_M2") |
        Q(application__exam__name__icontains="_M3") |
        Q(application__exam__name__icontains="_F6") |
        Q(application__exam__name__icontains="_F7") |
        Q(application__exam__name__icontains="_F8") |
        Q(application__exam__name__icontains="_F9") 
    )
).filter(
    Q(
        Q(option_answers__isnull=False),
        Q(file_answers__isnull=True)
    ) |
    Q(
        Q(option_answers__isnull=True),
        Q(file_answers__isnull=False)
    )
).distinct()


###############3

from django.db.models import Q, Subquery, OuterRef, Count, Value, Sum, Exists, F
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.exams.models import ExamQuestion, StatusQuestion
from fiscallizeon.questions.models import Question
from django.db.models.functions import Coalesce
from fiscallizeon.omr.models import OMRStudents, OMRDiscursiveScan
from fiscallizeon.answers.models import OptionAnswer, FileAnswer, TextualAnswer
status_list = [StatusQuestion.REPROVED, StatusQuestion.ANNULLED]

subquery_availables = Subquery(
    StatusQuestion.objects.filter(
        exam_question__pk=OuterRef('pk'),
        active=True,
        status__in=status_list,
    ).distinct().values('exam_question__pk')[:1]
)

apps = ApplicationStudent.objects.filter(
    Q(application__exam__name__istartswith="p2_"),
    Q(student__client__name__icontains="decis"),
    Q(
        Q(application__exam__name__icontains="M1") |
        Q(application__exam__name__icontains="M2") |
        Q(application__exam__name__icontains="M3") |
        Q(application__exam__name__icontains="F6") |
        Q(application__exam__name__icontains="F7") |
        Q(application__exam__name__icontains="F8") |
        Q(application__exam__name__icontains="F9") 
    )
).distinct().annotate(
    count_obj=Coalesce(Subquery(
            ExamQuestion.objects.filter(
                exam=OuterRef('application__exam'),
                question__category=Question.CHOICE
            ).exclude(
                pk__in=subquery_availables
            ).values('exam').annotate(
                count_sub=Count('question', distinct=True)
            ).values('count_sub')[:1]
        ), Value(0)
    ),
    count_disc=Coalesce(Subquery(
            ExamQuestion.objects.filter(
                exam=OuterRef('application__exam')
            ).exclude(
                pk__in=subquery_availables
            ).exclude(
                question__category=Question.CHOICE
            ).values('exam').annotate(
                count_sub=Count('question', distinct=True)
            ).values('count_sub')[:1]
        ), Value(0)
    ),
    count_ans_obj=Coalesce(Subquery(
            OptionAnswer.objects.filter(
                student_application=OuterRef('pk'),
                status=OptionAnswer.ACTIVE
            ).values('student_application').annotate(
                count_sub=Count('pk', distinct=True)
            ).values('count_sub')[:1]
        ), Value(0)
    ),
    count_ans_disc=Coalesce(Subquery(
            FileAnswer.objects.filter(
                student_application=OuterRef('pk'),
                teacher_grade__isnull=False
            ).values('student_application').annotate(
                count_sub=Count('pk', distinct=True)
            ).values('count_sub')[:1]
        ), Value(0)
    ),
    count_ans_text=Coalesce(Subquery(
            TextualAnswer.objects.filter(
                student_application=OuterRef('pk'),
                teacher_grade__isnull=False
            ).values('student_application').annotate(
                count_sub=Count('pk', distinct=True)
            ).values('count_sub')[:1]
        ), Value(0)
    ),
    has_obj=Exists(
        Subquery(
            OMRStudents.objects.filter(
                application_student=OuterRef('pk'),
            ).exclude(
                scan_image=''
            ).distinct()
        )
    ),
    has_disc=Exists(
        Subquery(
            OMRDiscursiveScan.objects.filter(
                omr_student__application_student=OuterRef('pk'),
            ).exclude(
                upload_image=''
            ).distinct()
        )
    )
).annotate(
    total_ans_textual=F('count_ans_disc') + F('count_ans_text')
)

apps_with_errors = apps.filter(
    Q(
        Q(count_ans_obj__lt=F('count_obj')) |
        Q(total_ans_textual__lt=F('count_disc')) |
        Q(has_obj=False) |
        Q(has_disc=False) 
    )
).distinct()

exams = ExamQuestion.objects.filter(
    Q(weight__lt=0),
    Q(exam__coordinations__unity__client__name__icontains="decis"),
    Q(exam__name__icontains="p6"),
    Q(exam__created_at__year=2024)
).availables(exclude_annuleds=True).values_list('exam', flat=True).distinct()

for e in exams:
    print(f'{e.weight}, {e.exam.name}')


#verifica se tem algum caderno com nota maior ou menor que 10
exams = Exam.objects.filter(
    Q(coordinations__unity__client__name__icontains="decis"),
    Q(name__istartswith="p6"),
    Q(name__icontains="2024"),
    Q(
        Q(name__icontains="f1") |
        Q(name__icontains="f2") |
        Q(name__icontains="f3") |
        Q(name__icontains="f4") |
        Q(name__icontains="f5")
    )
).distinct()

for e in exams:
    eqs = e.examquestion_set.availables(exclude_annuleds=True).order_by('exam_teacher_subject__order', 'order')
    eqs_total = e.examquestion_set.availables(exclude_annuleds=False).order_by('exam_teacher_subject__order', 'order')
    count = eqs.count()
    if eqs_total.count() == 11:
        print("tem 11", count)
        for eq in eqs:
            print(eq.exam_question_number)
            if str(eq.exam_question_number) != str(11):
                eq.weight = 10/(count-1)
                print(eq.weight)
            else:
                eq.weight = 0
            eq.save(skip_hooks=True)
    else:
        for index, eq in enumerate(eqs, 1):
            eq.weight = 10/count
            eq.save(skip_hooks=True)


for e in exams:
    eqs = e.examquestion_set.availables(exclude_annuleds=True).order_by('exam_teacher_subject__order', 'order')
    # eqs_total = e.examquestion_set.availables().order_by('exam_teacher_subject__order', 'order')
    count = eqs.count()
    if count == 11:
        for index, eq in enumerate(eqs, 1):
            if index <= 10:
                eq.weight = 1
            else:
                eq.weight = 0
            eq.save(skip_hooks=True)
    else:
        for index, eq in enumerate(eqs, 1):
            eq.weight = 10/count
            eq.save(skip_hooks=True)
        


from fiscallizeon.exams.models import Exam
from django.db.models import Q
exams = Exam.objects.filter(
    Q(coordinations__unity__client__name__icontains="decis"),
    Q(name__istartswith="p2"),
    Q(name__icontains="2024")
).distinct()

for e in exams:
    print(e.name, e.total_grade, e.total_weight)

from fiscallizeon.answers.models import TextualAnswer
from django.db.models import Q, DecimalField, OuterRef, ExpressionWrapper
from django.db.models.functions import 


txs = TextualAnswer.objects.filter(
    Q(
        Q(student_application__application__exam__name__istartswith="p6_"),
        Q(student_application__application__exam__name__icontains="2024")
    )
).annotate(
    question_weight=Subquery(
        ExamQuestion.objects.filter(
            question=OuterRef('question'),
            exam=OuterRef('student_application__application__exam')
        ).values('weight')[:1],
        output_field=DecimalField()
    )
).annotate(
    question_weight_round=Round('question_weight'),
    teacher_grade_round=Round('teacher_grade')
).filter(
    teacher_grade_round__gt=F('question_weight_round')
).distinct('pk').annotate(
    modulo=ExpressionWrapper(
        Mod(F('teacher_grade_round') * 100, F('question_weight_round') * 25), output_field=FloatField()
    )
).filter(modulo=0)

for f in txs:
    print(f'{f.question_weight_round}, {f.teacher_grade}, {str(f.student_application.application.exam.pk)}')


# detecta aluos com nota maior que 10
from fiscallizeon.applications.models import ApplicationStudent
from django.db.models import Q
apps = ApplicationStudent.objects.filter(
    Q(
        Q(student__client_id="a2b1158b-367a-40a4-8413-9897057c8aa2"),
        Q(application__exam__name__istartswith="p1"),
        Q(created_at__year=2025)
    )
).get_annotation_count_answers(only_total_grade=True, exclude_annuleds=True).filter(
    Q(
        Q(total_grade__gt=10.009) |
        Q(total_grade__lt=0)
    )
).distinct()


for app in apps:
    print(f'{app.student.name}, {app.application.exam.name}, {app.total_grade}')

from fiscallizeon.answers.models import FileAnswer, TextualAnswer
from django.db.models import F, FloatField, Func
class Round(Func):
    function = 'ROUND'
    template = '%(function)s(%(expressions)s, 4)'
    output_field = FloatField()


exam_id = "513b6adb-9a09-4a83-b336-3c29d45de4c7"
actual_weight = 1.0000
before_weight =   1.0492
for grade in [round(before_weight*0.25, 4), round(before_weight*0.5, 4), round(before_weight*0.75, 4), round(before_weight*1, 4)]:
    files = FileAnswer.objects.filter(
        student_application__application__exam=exam_id,
    ).annotate(
        teacher_grade_round=Round('teacher_grade')
    ).filter(
        teacher_grade_round=grade
    )
    print(files.count(), grade, round(actual_weight*(grade/before_weight), 4))
    files.update(
        teacher_grade=round(actual_weight*(grade/before_weight), 4)
    )



files = FileAnswer.objects.filter(
    student_application__application__exam="dbf64219-2297-4071-81ff-fae5a25ad654",
).filter(
    teacher_grade=0.75
)
files.count()
files.update(
    teacher_grade=0.1786
)


for app in apps_with_errors:
    school_class = app.student.get_last_class()
    print(f'{app.pk}, {app.application.exam.name}, {app.count_obj}, {app.count_disc}, {app.student.name}, {school_class.name if school_class else ""}, {school_class.coordination.unity.name if school_class else ""}, {"sim" if app.has_obj else "não"}, {"sim" if app.has_disc else "não"}, {app.count_ans_obj}, {app.total_ans_textual}')


from django.db.models import Q
from fiscallizeon.answers.models import OptionAnswer

OptionAnswer.objects.filter(
    # Q(created_by__isnull=True),
    Q(status=OptionAnswer.ACTIVE),
    Q(student_application__application__exam__name__istartswith="P2_"),
    Q(student_application__student__client__name__icontains="decis"),
    Q(
        Q(student_application__application__exam__name__icontains="f6") |
        Q(student_application__application__exam__name__icontains="f7") |
        Q(student_application__application__exam__name__icontains="f8") |
        Q(student_application__application__exam__name__icontains="f9") |
        Q(student_application__application__exam__name__icontains="m1") |
        Q(student_application__application__exam__name__icontains="m2") |
        Q(student_application__application__exam__name__icontains="m3") 
    )
).distinct().count()

options = OptionAnswer.objects.filter(
    Q(created_by__isnull=False),
    Q(status=OptionAnswer.ACTIVE),
    Q(student_application__application__exam__name__istartswith="P2_"),
    Q(student_application__student__client__name__icontains="decis"),
    Q(
        Q(student_application__application__exam__name__icontains="f6") |
        Q(student_application__application__exam__name__icontains="f7") |
        Q(student_application__application__exam__name__icontains="f8") |
        Q(student_application__application__exam__name__icontains="f9") |
        Q(student_application__application__exam__name__icontains="m1") |
        Q(student_application__application__exam__name__icontains="m2") |
        Q(student_application__application__exam__name__icontains="m3") 
    )
).distinct()

students = options.values_list('student_application__student', flat=True)

from fiscallizeon.classes.models import SchoolClass

classes_list = SchoolClass.objects.filter(
    school_year=2023,
    coordination__unity__client__name__icontains="deci",
    students__in=students
).distinct().annotate(
    count=Subquery(
        .values()
    )
)

for c in classes_list:
    count = options.filter(
            Q(student_application__student__classes=c)
    ).distinct().count()
    print(f'{c.name}, {c.coordination.unity.name}, {count}')


from fiscallizeon.omr.models import OMRError, OMRDiscursiveError, OMRStudents, OMRDiscursiveScan


OMRDiscursiveError.objects.filter(
    Q(upload__application_students__application__exam__name__istartswith="P1_"),
    Q(upload__application_students__student__client__name__icontains="decis"),
    Q(
        Q(upload__application_students__application__exam__name__icontains="f6") |
        Q(upload__application_students__application__exam__name__icontains="f7") |
        Q(upload__application_students__application__exam__name__icontains="f8") |
        Q(upload__application_students__application__exam__name__icontains="f9") |
        Q(upload__application_students__application__exam__name__icontains="m1") |
        Q(upload__application_students__application__exam__name__icontains="m2") |
        Q(upload__application_students__application__exam__name__icontains="m3") 
    )
).distinct().count()

OMRStudents.objects.filter(
    Q(application_student__application__exam__name__istartswith="P2_"),
    Q(application_student__student__client__name__icontains="decis"),
    Q(
        Q(application_student__application__exam__name__icontains="f6") |
        Q(application_student__application__exam__name__icontains="f7") |
        Q(application_student__application__exam__name__icontains="f8") |
        Q(application_student__application__exam__name__icontains="f9") |
        Q(application_student__application__exam__name__icontains="m1") |
        Q(application_student__application__exam__name__icontains="m2") |
        Q(application_student__application__exam__name__icontains="m3") 
    )
).exclude(
    scan_image=""
).distinct().count()

OMRDiscursiveScan.objects.filter(
    Q(omr_student__application_student__application__exam__name__istartswith="P1_"),
    Q(omr_student__application_student__student__client__name__icontains="decis"),
    Q(
        Q(omr_student__application_student__application__exam__name__icontains="f6") |
        Q(omr_student__application_student__application__exam__name__icontains="f7") |
        Q(omr_student__application_student__application__exam__name__icontains="f8") |
        Q(omr_student__application_student__application__exam__name__icontains="f9") |
        Q(omr_student__application_student__application__exam__name__icontains="m1") |
        Q(omr_student__application_student__application__exam__name__icontains="m2") |
        Q(omr_student__application_student__application__exam__name__icontains="m3") 
    )
).exclude(
    upload_image=""
).distinct().count()


from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.answers.models import FileAnswer
from django.db.models import *
from django.db.models.functions import *
import datetime

filter_exam = Q(
    Q(student_application__application__exam__name__istartswith="P2_"),
    Q(student_application__student__client__name__icontains="decis"),
    Q(
        Q(student_application__application__exam__name__icontains="f6") |
        Q(student_application__application__exam__name__icontains="f7") |
        Q(student_application__application__exam__name__icontains="f8") |
        Q(student_application__application__exam__name__icontains="f9") |
        Q(student_application__application__exam__name__icontains="m1") |
        Q(student_application__application__exam__name__icontains="m2") |
        Q(student_application__application__exam__name__icontains="m3") 
    )
)

inspectors = Inspector.objects.filter(
    user__isnull=False,
    inspector_type=Inspector.TEACHER,
    coordinations__unity__client__name__icontains="decis",
).distinct().annotate(
    count_obj_answers=Coalesce(Subquery(
        OptionAnswer.objects.filter(
            Q(status=OptionAnswer.ACTIVE),
            Q(created_by=OuterRef('user')),
            Q(filter_exam)
        ).values('created_by').annotate(
            count=Count('pk')
        ).values('count')[:1]), 0
    ),
    count_file_answers=Coalesce(Subquery(
        FileAnswer.objects.filter(
            Q(teacher_grade__isnull=False),
            Q(who_corrected=OuterRef('user')),
            Q(filter_exam)
        ).values('who_corrected_id').annotate(
            count=Count('pk')
        ).values('count')[:1]), 0
    ),
    first_correct_disc=Subquery(
        FileAnswer.objects.filter(
            Q(teacher_grade__isnull=False),
            Q(who_corrected=OuterRef('user')),
            Q(filter_exam)
        ).order_by('updated_at').values('updated_at')[:1]
    ),
    last_correct_disc=Subquery(
        FileAnswer.objects.filter(
            Q(teacher_grade__isnull=False),
            Q(who_corrected=OuterRef('user')),
            Q(filter_exam)
        ).order_by('-updated_at').values('updated_at')[:1]
    ),
    first_correct_obj=Subquery(
        OptionAnswer.objects.filter(
            Q(status=OptionAnswer.ACTIVE),
            Q(created_by=OuterRef('user')),
            Q(filter_exam)
        ).order_by('updated_at').values('updated_at')[:1]
    ),
    last_correct_obj=Subquery(
        OptionAnswer.objects.filter(
            Q(status=OptionAnswer.ACTIVE),
            Q(created_by=OuterRef('user')),
            Q(filter_exam)
        ).order_by('-updated_at').values('updated_at')[:1]
    )
).order_by('-count_file_answers')

for i in inspectors:
    list_first =[ x for x in [i.first_correct_obj, i.first_correct_disc] if x is not None] 
    list_last = [ x for x in [i.last_correct_obj, i.last_correct_disc] if x is not None]
    if not list_first:
        first = '-'
        last = '-'
    else:
        first = min(list_first).strftime('%d/%m/%Y')
        last = max(list_last).strftime('%d/%m/%Y')
    print(f'{i.name}, {i.count_obj_answers}, {i.count_file_answers}, {first}, {last}')


from django.db.models import Subquery, F, OuterRef, Q
from fiscallizeon.answers.models import FileAnswer, TextualAnswer
from fiscallizeon.exams.models import ExamQuestion, Exam

textuals = TextualAnswer.objects.filter(
    Q(student_application__application__exam__name__istartswith="P3_"),
    Q(student_application__student__client__name__icontains="decis"),
    Q(
        Q(student_application__application__exam__name__icontains="f6") |
        Q(student_application__application__exam__name__icontains="f7") |
        Q(student_application__application__exam__name__icontains="f8") |
        Q(student_application__application__exam__name__icontains="f9") |
        Q(student_application__application__exam__name__icontains="m1") |
        Q(student_application__application__exam__name__icontains="m2") |
        Q(student_application__application__exam__name__icontains="m3") 
    )
).distinct()

for t in textuals:
    files = FileAnswer.objects.filter(
        student_application=t.student_application,
        question=t.question
    )
    print(files.count())

files = TextualAnswer.objects.filter(
    student_application__application__exam__name__istartswith="p3_",
    teacher_grade__isnull=False,
).annotate(
    extra=Subquery(
        TextualAnswer.objects.filter(
            question=OuterRef('question'),
            student_application=OuterRef('student_application')
        ).exclude(pk=OuterRef('pk')).values("pk")[:1]
    )
).filter(
    extra__isnull=False
).order_by('student_application__student__name')
from fiscallizeon.answers.models import OptionAnswer

textuals = OptionAnswer.objects.filter(
    student_application="2b13867a-9e3e-4ae1-a678-4f32c1e256fc"
)

for t in textuals:
    print(f'{t.pk}, {t.question_option.question.pk}, {t.created_at}, {t.get_status_display()}')

for f in files:
    print(f'{f.student_application.application.exam.name}, {f.student_application.student.name}, {f.teacher_grade}, {FileAnswer.objects.filter(pk=f.extra).first().teacher_grade}, {f.pk}, {f.extra}')

files = TextualAnswer.objects.filter(
    student_application__application__exam__name__istartswith="p3_",
    teacher_grade__isnull=False
).annotate(
    question_weight=
    )
).filter(
    Q(teacher_grade__gt=F('question_weight'))
)

files.update(
    teacher_grade=F('question_weight')
)


from fiscallizeon.exams.models import Exam, StatusQuestion, ExamQuestion
from django.db.models import Subquery, OuterRef, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
status_list = [StatusQuestion.REPROVED, StatusQuestion.ANNULLED, StatusQuestion.USE_LATER]

subquery_availables = Subquery(
    StatusQuestion.objects.filter(
        exam_question__pk=OuterRef('pk'),
        active=True,
        status__in=status_list,
    ).distinct().values('exam_question__pk')[:1]
)

exams = Exam.objects.filter(
    name__icontains="p1_",
    coordinations__unity__client__name__icontains="deci",
    examquestion__isnull=False,
    created_at__year=2024
).exclude(
    name__icontains="QUESTÕES"
).exclude(
    name__icontains="BOLSA"
).exclude(
    name__icontains="OE1"
).distinct()

for exam in exams:
    print(f'{exam.name}, {exam.examteachersubject_set.all().count()}, {exam.examteachersubject_set.all().values_list("teacher_subject__subject", flat=True).distinct().count()}')

count = 0
for exam in exams:
    total_weight = str(exam.get_total_weight())
    if total_weight in [str(10), str(10.000005), '10.000000', '10.000004']:
        continue
    count += 1
    print(f'{exam.name}, {total_weight}')

for exam in exams:
    exam.distribute_weights()




for f in files:
    f.teacher_grade = f.question_weight
    f.save(skip_hooks=True)
    print(f'{f.student_application.student.name}, {f.teacher_grade}, {f.question_weight}')

exams = Exam.objects.filter(
    pk__in=textuals.values_list('student_application__application__exam__pk', flat=True)
).distinct()

from fiscallizeon.answers.models import SumAnswer


for i in [1,2,3,4,5]:
    answers = SumAnswer.objects.filter(
        student_application__student__client_id="3117e0a3-4dde-4b41-9412-00c14fb51f79",
        created_at__month=i
    ).distinct()
    corrected = answers.filter(
        created_by__isnull=False
    ).distinct()
    print(i, answers.count(), corrected.count())


answers = OptionAnswer.objects.filter(
    Q(student_application__application__exam__name__istartswith="P2_"),
    Q(student_application__student__client__name__icontains="decis"),
    Q(
        Q(student_application__application__exam__name__icontains="f6") |
        Q(student_application__application__exam__name__icontains="f7") |
        Q(student_application__application__exam__name__icontains="f8") |
        Q(student_application__application__exam__name__icontains="f9") |
        Q(student_application__application__exam__name__icontains="m1") |
        Q(student_application__application__exam__name__icontains="m2") |
        Q(student_application__application__exam__name__icontains="m3") 
    ),
    Q(teacher_grade__isnull=False),
    Q(who_corrected__isnull=True)
).distinct()

for answer in answers:
    print(answer.student_application.application.exam.name, answer.student_application.student.name)


apps = Application.objects.filter(
    Q(exam__name__istartswith="P1_"),
    Q(exam__coordinations__unity__client__name__icontains="decis"),
    Q(
        Q(exam__name__icontains="f6") |
        Q(exam__name__icontains="f7") |
        Q(exam__name__icontains="f8") |
        Q(exam__name__icontains="f9") |
        Q(exam__name__icontains="m1") |
        Q(exam__name__icontains="m2") |
        Q(exam__name__icontains="m3") 
    )
).distinct().order_by('date')

for a in apps:
    print(a.exam.name, a.date)


#descobirr alunos colando
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.exams.models import Exam
from decimal import Decimal
from django.db.models import Q, Subquery, OuterRef, Count, Sum, F
from django.db.models.functions import Coalesce
from django.apps import apps


exams = Exam.objects.filter(
    Q(
        Q(name__icontains="P4") |
        Q(name__icontains="P5") |
        Q(name__icontains="P6") 
    ),
    Q(
        Q(name__icontains="M3")
    ),
    Q(
        Q(name__icontains="2023")
    )
).exclude(
    Q(name__icontains="prepara") |
    Q(name__icontains="bolsa")
).distinct().order_by('name')

OptionAnswer = apps.get_model('answers', 'OptionAnswer')
TextualAnswer = apps.get_model('answers', 'TextualAnswer')
FileAnswer = apps.get_model('answers', 'FileAnswer')

apps = ApplicationStudent.objects.filter(
    application__exam__in=exams,
    is_omr=True,
    missed=False
)

exam_question_choice_subquery = apps.get_exam_question_subquery(
    choice=True, exclude_annuleds=True,
)
exam_question_subquery = apps.get_exam_question_subquery(
 exclude_annuleds=True,
)

choice_count = Coalesce(
    Subquery(
        OptionAnswer.objects.filter(
            student_application__pk=OuterRef('pk'),
            status=OptionAnswer.ACTIVE,
            question_option__question=exam_question_choice_subquery.values('question')[:1],
        ).values('student_application').annotate(
            total=Count('pk')
        ).values('total')[:1]
    ), 0
)
correct_choice_count = Coalesce(
    Subquery(
        OptionAnswer.objects.filter(
            student_application__pk=OuterRef('pk'),
            status=OptionAnswer.ACTIVE,
            question_option__is_correct=True,
            question_option__question=exam_question_choice_subquery.values('question')[:1],
        ).values('student_application').annotate(
            total=Count('pk')
        ).values('total')[:1]
    ), 0
)
incorrect_choice_count = Coalesce(
    Subquery(
        OptionAnswer.objects.filter(
            student_application__pk=OuterRef('pk'),
            status=OptionAnswer.ACTIVE,
            question_option__is_correct=False,
            question_option__question=exam_question_choice_subquery.values('question')[:1],
        ).values('student_application').annotate(
            total=Count('pk')
        ).values('total')[:1]
    ), 0
)

choice_grade_sum = Coalesce(
    Subquery(
        OptionAnswer.objects.filter(
            student_application__pk=OuterRef('pk'),
            status=1,
            question_option__is_correct=True,
        ).annotate(
            grade=exam_question_choice_subquery.values('weight')[:1],                    
        ).values('student_application').annotate(
            total=Sum('grade')
        ).values('total')[:1]
    ), Decimal(0.0)
)

textual_grade_sum = Coalesce(
    Subquery(
        TextualAnswer.objects.filter(
            student_application__pk=OuterRef('pk'),
            question=exam_question_subquery.values('question')[:1],
        ).values('student_application').annotate(
            total=Sum('teacher_grade')
        ).values('total')[:1]
    ), Decimal(0.0)
)

file_grade_sum = Coalesce(
    Subquery(
        FileAnswer.objects.filter(
            student_application__pk=OuterRef('pk'),
            question=exam_question_subquery.values('question')[:1],
        ).values('student_application').annotate(
            total=Sum('teacher_grade')
        ).values('total')[:1]
    ), Decimal(0.0)
)        

apps = apps.annotate(
    total_grade=choice_grade_sum + textual_grade_sum + file_grade_sum,
    total_answers_choice=choice_count,
    total_correct_answers=correct_choice_count 
).distinct()


apps = apps.filter(
    Q(total_grade__gt=9) |
    Q(
        total_correct_answers__gte=F('total_answers_choice')-1
    )
).order_by('student__name')

",".join(list(exams.values_list('name', flat=True)))

",".join(list(apps.values_list('student__name',flat=True).distinct('student__name').order_by('student__name')))


students = list(apps.values_list('student__name',flat=True).distinct('student__name').order_by('student__name'))

for st in apps.distinct('student__name').order_by('student__name'):
    print(st.student.get_last_class())

for e in exams:
    print(e.name)

apps_final = list(apps.values('student__name', 'application__exam__name', 'total_grade'))



for exam in exams:
    grades = []
    for student in students:
        append_content = '-'
        for af in apps_final:
            if af['student__name'] == student and af['application__exam__name'] == exam.name:
                append_content = str(af['total_grade']).replace('.',',')
                break
        grades.append(append_content)
    print(";".join(grades))
#final descobrir alunos colando


#DESATIVAR USUÁRIO E DESLOGAR EM SEGUIDA
from django.core.cache import cache
from django.db.models import Q
from fiscallizeon.accounts.models import User

keys = cache.keys('django.contrib.sessions.cache*')

sts = Student.objects.filter(
    client__name__icontains="deho",
    user__is_active=False,
    user__temporarily_inactive=True,
    classes__coordination__unity__name__icontains="tubar",
    classes__grade__level__in=[1,2],
    classes__school_year=2024
).distinct()

for s in sts:
    s.user.is_active=True
    s.user.temporarily_inactive = False
    s.user.save()

for s in sts:
    for k in keys:
        data = cache.get(k)
        if data and data.get('_auth_user_id', '') == str(s.user.pk):
            cache.delete(k)



emails_manter = ["silvia.mangueira@rededecisao.com.br",
"ruth.reategui@rededecisao.com.br",
"bianca.batista@rededecisao.com.br",
"cleonice.barroso@rededecisao.com.br",
"ana.nascimento@rededecisao.com.br",
"elisatebes.carlini@rededecisao.com.br",
"eldes.fabro@rededecisao.com.br",
"marcia.haus@rededecisao.com.br",
"sheila.silva@rededecisao.com.br",
"elisa.nievas@rededecisao.com.br",
"esther.barbosa@rededecisao.com.br",
"charlene.ansanelli@rededecisao.com.br",
"sandra.ssouza@rededecisao.com.br",
"tatiana.bosco@rededecisao.com.br",
"alcione.paro@rededecisao.com.br",
"luciana.silva@rededecisao.com.br",
"macilene.silva@rededecisao.com.br",
"dancelly.coltro@rededecisao.com.br",
"elaine.andrade@rededecisao.com.br",
"edna.marcolongo@rededecisao.com.br",
"carla.santana@rededecisao.com.br",
"yuri.rivelli@rededecisao.com.br",
"silvia.hoffmann@rededecisao.com.br",
"robson.almeida@rededecisao.com.br",
"alessandra.shoyama@rededecisao.com.br",
"pedro.alcazar@rededecisao.com.br",
"daniel.bocchi@rededecisao.com.br",
"tatiana.severino@rededecisao.com.br",
"laura.yamada@rededecisao.com.br",
"thaisa.silva@rededecisao.com.br",
"sandra.novak@rededecisao.com.br",
"elaine.arashiro@rededecisao.com.br",
"ana.saldo@rededecisao.com.br",
"gilberto.roca@rededecisao.com.br",
"bianca.luciano@rededecisao.com.br",
"aparecida.fsilva@rededecisao.com.br",
"katia.alcazar@rededecisao.com.br",
"genilda.bispo@rededecisao.com.br",
"regiane.cocarelli@rededecisao.com.br",
"lucas.lucca@rededecisao.com.br",
"mychelle.rodrigues@rededecisao.com.br",
"juliana.faria@rededecisao.com.br",
"carla.ponciano@rededecisao.com.br",
"simone.pinheiro@rededecisao.com.br",
"luis.sousa@rededecisao.com.br",
"debora.heringer@rededecisao.com.br",
"suzamar.santos@rededecisao.com.br",
"marceli.melo@rededecisao.com.br",
"andreia.pereira@rededecisao.com.br",
"wenndy.horta@rededecisao.com.br",
"juliana.teixeira@rededecisao.com.br",
"janaina.andrade@rededecisao.com.br",
"fernanda.araujo@rededecisao.com.br",
"victoria.lopes@rededecisao.com.br",
"selma.passetti@rededecisao.com.br",
"caroline.schneider@rededecisao.com.br",
"renato.ramos@rededecisao.com.br",
"joyce.reolo@rededecisao.com.br",
"eliana.negrete@rededecisao.com.br",
"elaine.prado@rededecisao.com.br",
"monica.rodrigues@rededecisao.com.br",
"adriane@rededecisao.com.br",
"diogo.santos@rededecisao.com.br",
"jessica.mak@rededecisao.com.br",
"simone@rededecisao.com.br",
"isabele.gabriel@rededecisao.com.br",
"sandra.puglisi@rededecisao.com.br",
"soraia@rededecisao.com.br",
"breno.oliveira@rededecisao.com.br",
"lara.souza@rededecisao.com.br",
"sonia.andrade@rededecisao.com.br",
"alexandra.faraco@rededecisao.com.br",
"amanda.verrone@rededecisao.com.br",
"camile.passaia@rededecisao.com.br",
"bruna.sampaio@rededecisao.com.br",
"iracema.jesus@rededecisao.com.br",
"simone.souza@rededecisao.com.br",
"juliane.nascimento@rededecisao.com.br",
"juliana.rocha@rededecisao.com.br",
"cilene.carvalho@rededecisao.com.br",
"cristiane.landim@rededecisao.com.br",
"adriano.camargo@rededecisao.com.br",
"flavia.ferreira@rededecisao.com.br",
"daniele.lima@rededecisao.com.br",
"tania.barbara@rededecisao.com.br",
"andreia@rededecisao.com.br",
"juliana.cantarera@rededecisao.com.br",
"tatiane.rabelo@rededecisao.com.br",
"elida.ramos@rededecisao.com.br",
"debora.rivarolli@rededecisao.com.br",
"kathleen.silva@rededecisao.com.br",
"ana.costa@rededecisao.com.br",
"maiara.neves@rededecisao.com.br",
"rosana.novas@rededecisao.com.br",
"suelin.magalhaes@rededecisao.com.br",
"eneida.costa@rededecisao.com.br",
"felipe.pinho@rededecisao.com.br",
"maria.segovia@rededecisao.com.br",
"sandra.rodrigues@rededecisao.com.br",
"carolyne.carvalho@rededecisao.com.br",
"juliana.maria@rededecisao.com.br",
"eduardo.silva@rededecisao.com.br",
"erica.santos@rededecisao.com.br",
"jussara.costa@rededecisao.com.br",
"fernanda.pfeiffer@rededecisao.com.br",
"aryane.mantovanello@rededecisao.com.br",
"mayara.sombra@rededecisao.com.br",
"marcella.terron@rededecisao.com.br",
"sandra.lima@rededecisao.com.br",
"luiz.gomes@rededecisao.com.br",
"andressa.figueira@rededecisao.com.br",
"adriana.rodrigues@rededecisao.com.br",
"camila.barreto@rededecisao.com.br",
"renata.lettieri@rededecisao.com.br",
"sheyla.rejanne@rededecisao.com.br",
"ramon.bezerra@rededecisao.com.br",
"adriana.bento@rededecisao.com.br",
"ana.gomes@rededecisao.com.br",
"ligia.prado@rededecisao.com.br",
"jessica.oliveira@rededecisao.com.br",
"marta.alves@rededecisao.com.br",
"viviane.santos@rededecisao.com.br",
"fernanda.barbosa@rededecisao.com.br",
"tatiana.borba@rededecisao.com.br",
"denise.souza@rededecisao.com.br",
"camila.alves@rededecisao.com.br",
"amanda.fidelis@rededecisao.com.br",
"denise.ramos@rededecisao.com.br",
"andreia.reis@rededecisao.com.br",
"melina.lisboa@rededecisao.com.br",
"thais.lima@rededecisao.com.br",
"ivy.machado@rededecisao.com.br",
"paulo.brasileiro@rededecisao.com.br",
"luciana.hadad@rededecisao.com.br",
"renata.medeiros@rededecisao.com.br",
"patricia.marinho@rededecisao.com.br",
"barbara.rodrigues@rededecisao.com.br",
"alessandra.ruela@rededecisao.com.br",
"miriam.cotta@rededecisao.com.br",
"leticia.rodrigues@rededecisao.com.br",
"rosane.silva@rededecisao.com.br",
"rosinaldo.santos@rededecisao.com.br",
"tatiane.amorim@rededecisao.com.br",
"maria.becyk@rededecisao.com.br",
"jessica.reis@rededecisao.com.br",
"alessandra.chaves@rededecisao.com.br",
"edgar.morais@rededecisao.com.br",
"daiane.oliveira@rededecisao.com.br",
"angelica.holanda@rededecisao.com.br",
"celio.silva@rededecisao.com.br",
"lucas.vitalino@rededecisao.com.br",
"elisabete.abreu@rededecisao.com.br",
"ana.santos@rededecisao.com.br",
"daniele.rodrigues@rededecisao.com.br",
"danuza.rodrigues@rededecisao.com.br",
"alexandre.souza@rededecisao.com.br",
"ana.ciminelli@rededecisao.com.br",
"anapaula.oliveira@rededecisao.com.br",
"antonio.souza@rededecisao.com.br",
"aparecida.silva@rededecisao.com.br",
"bruna@rededecisao.com.br",
"bruno.moraes@rededecisao.com.br",
"carolina.silva@rededecisao.com.br",
"caroline.castro@rededecisao.com.br",
"lucimar.santana@rededecisao.com.br",
"cleusa.dellagnese@rededecisao.com.br",
"dayane.caldeira@rededecisao.com.br",
"edleuza.azevedo@rededecisao.com.br",
"eliane@rededecisao.com.br",
"gabriela.vitoriano@rededecisao.com.br",
"giovanna.hilario@rededecisao.com.br",
"giuliana.maria@rededecisao.com.br",
"iraima.bezzan@rededecisao.com.br",
"lara.belette@rededecisao.com.br",
"leandro.pinto@rededecisao.com.br",
"lis.lage@rededecisao.com.br",
"lislaine.mancini@rededecisao.com.br",
"luciandro.sodre@rededecisao.com.br",
"luciene.artioli@rededecisao.com.br",
"neliani.ruivo@rededecisao.com.br",
"nilzete.agostinho@rededecisao.com.br",
"priscila.cruz@rededecisao.com.br",
"rene.leite@rededecisao.com.br",
"rogerio.gaiotti@rededecisao.com.br",
"sandra.vasconcellos@rededecisao.com.br",
"thiago.santos@rededecisao.com.br",
"wemerson.mudesto@rededecisao.com.br",
"daniella.sargaco@rededecisao.com.br",
"danilo.fujihara@rededecisao.com.br",
"felipe.avenoso@rededecisao.com.br",
"lucas.madsen@rededecisao.com.br",
"victoria.david@rededecisao.com.br",
"ana.bazotti@rededecisao.com.br",
"andressa.rossini@rededecisao.com.br",
"ariane.labriola@rededecisao.com.br",
"atila.peixoto@rededecisao.com.br",
"bianca.lopes@rededecisao.com.br",
"bianca.succi@rededecisao.com.br",
"brenda.perini@rededecisao.com.br",
"caroline.souza@rededecisao.com.br",
"dayane.lima@rededecisao.com.br",
"deborah.costa@rededecisao.com.br",
"elaine.inacio@rededecisao.com.br",
"fernanda.marques@rededecisao.com.br",
"fernanda.pereira@rededecisao.com.br",
"gabrielle.oliveira@rededecisao.com.br",
"graziela.silva@rededecisao.com.br",
"isabella.santos@rededecisao.com.br",
"ivani.almeida@rededecisao.com.br",
"jessica.xavier@rededecisao.com.br",
"juliana.alves@rededecisao.com.br",
"karen.ditscheiner@rededecisao.com.br",
"karina.ferreira@rededecisao.com.br",
"karini.silva@rededecisao.com.br",
"ligia.pimentel@rededecisao.com.br",
"lilian.vitorelli@rededecisao.com.br",
"luciana.conejo@rededecisao.com.br",
"magda.lima@rededecisao.com.br",
"michelle.landin@rededecisao.com.br",
"michelli.rezende@rededecisao.com.br",
"michely.carvalho@rededecisao.com.br",
"nathara.canio@rededecisao.com.br",
"patricia.costa@rededecisao.com.br",
"raquel.medes@rededecisao.com.br",
"sandra.avanze@rededecisao.com.br",
"simone.gama@rededecisao.com.br",
"simone.oliveira@rededecisao.com.br",
"stephanie.oliveira@rededecisao.com.br",
"suelaine.estete@rededecisao.com.br",
"valeria.azedo@rededecisao.com.br",
"valeria.gagliano@rededecisao.com.br",
"viviane.campos@rededecisao.com.br"]

users = User.objects.filter(
    Q(is_active=True),
    Q(
        Q(inspector__coordinations__unity__client__name__icontains="tamanda") |
        Q(coordination_member__coordination__unity__client__name__icontains="tamanda")
        # Q(student__client__name__icontains="tamanda")
    )
).distinct()

for user in users:
    user.must_change_password = True
    user.set_password(user.email)
    user.save()
    print(f'{user.name}, {user.email}, {user.user_type}')
    for k in keys:
        data = cache.get(k)
        if data and data.get('_auth_user_id', '') == str(user.pk):
            cache.delete(k)
#FIM DESATIVAR USUARIO E DESLOGAR EM SEGUIDA
            



# ADICIONAR USUÁRIOS EM TODAS AS COORDENAÇÕES 
from fiscallizeon.accounts.models import User
from fiscallizeon.clients.models import SchoolCoordination, CoordinationMember

users = User.objects.filter(
    email__in=[
        "felipe.avenoso@rededecisao.com.br",
        "daniella.sargaco@rededecisao.com.br"
    ]
)
coordinations = SchoolCoordination.objects.filter(
    unity__client__name__icontains="decisão"
).distinct()

for user in users:
    for coordination in coordinations:
        coordination_member = CoordinationMember.objects.update_or_create(
            coordination=coordination,
            user=user,
            defaults={
                'is_coordinator': True,
                'is_reviewer': True,
                'is_pedagogic_reviewer': True
            }
        )

#FIM DE ADICIONAR USUÁRIOS EM TODAS AS COORDENAÇÕES
        
#SUBSTITU ALUNOS DESATIVADOS E TRANSFERE PARA O ALUNO ATIVADO COM MESMO NOME
        


from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.students.models import Student

students_disableds = ApplicationStudent.objects.filter(
    student__user__is_active=False,
    student__client__name__icontains="decis",
    application__created_at__year=2024
).distinct()

for student_disabled in students_disableds:
    new_student = Student.objects.filter(
        user__is_active=True,
        client__name__icontains="decis",
        name__iexact=student_disabled.student.name
    )
    if new_student.count() == 1:
        student_disabled.student = new_student.first()
        student_disabled.save(skip_hooks=True)
    else:
        print(f'{new_student.count()}, {student_disabled.application.exam.name}, {student_disabled.student.name}')

#FIM DE SUBSTITUIÇÃO DE ALUNO
        

from fiscallizeon.accounts.models import User

users = User.objects.filter(
    inspector__isnull=False,
    inspector__coordinations__unity__client__name__icontains="decis",
).distinct()

teacher_group, created = CustomGroup.objects.update_or_create(name='PROFESSORES', segment='teacher', client__isnull=True, defaults={ "default": True })

for user in users:
    user.custom_groups.add(teacher_group)


# MUDAR APLICAÇAO DE ALUNO QUE ESTÁ DESATIVADO
    from fiscallizeon.students.models import Student

old = Student.objects.filter(name="MATEUS MENEZES TIGRE", user__is_active=False).first()
new = Student.objects.filter(name="MATEUS MENEZES TIGRE", user__is_active=True).first()

from django.db.models import Q
from fiscallizeon.applications.models import ApplicationStudent
apps = ApplicationStudent.objects.filter(
    Q(application__exam__name__istartswith="p1"),
    Q(student=old),
    Q(created_at__year=2024),
    Q(
        Q(option_answers__isnull=False) |
        Q(file_answers__isnull=False)
    )
).distinct()

for a in apps:
    old_app = ApplicationStudent.objects.filter(
        Q(student=new),
        Q(application=a.application),
        Q(
            Q(option_answers__isnull=True) &
            Q(file_answers__isnull=True)
        )
    ).distinct().first()
    if old_app:
        old_app.student = old
        old_app.save(skip_hooks=True)
        a.student = new
        a.save(skip_hooks=True)



# REMOVE RESPOSTAS DUPLICADAS DE FILE E TEXTUAL ANSWER (TAMANDARÉ)
from fiscallizeon.answers.models import FileAnswer, TextualAnswer
from fiscallizeon.applications.models import ApplicationStudent

apps = ApplicationStudent.objects.filter(
    application__exam__name__iexact="P2_Ciências_F6_ANGLO_2024"
)

for app in apps:
    fs = FileAnswer.objects.filter(
        student_application=app
    )
    for f in fs:
        ts =  FileAnswer.objects.filter(
            student_application=app,
            question=f.question
        ).exclude(pk=f.pk)
        if ts:
            print(app.student.name, "é igual repetido", f.teacher_grade, ts.count(), ts.first().teacher_grade, ts.first().pk)
            ts.delete()



FileAnswer.objects.filter(
    pk__in=["f6d2472a-83c0-445a-aa9b-9c1f4eace65c", "a9d89b8d-455c-45c9-a72f-1079d53a9ecc", "d28cc683-131a-47e9-87e4-32dd5d8a5648"]
).delete()

#mover turmas de uma aplicaç~ao para outra aplicação igual


from uuid import uuid4
from django.db.models import Q

from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.applications.models import Application

apps = Application.objects.filter(
    Q(exam__name__istartswith="p2_"),
    Q(exam__name__icontains="OBJETIVO"),
    Q(exam__name__icontains="2024")
).exclude(
    Q(exam__name__icontains="OSB")
).exclude(
    Q(exam__name="P2_Língua Inglesa_F8_OBJETIVO_2024_")
).distinct()

from django.db import transaction

with transaction.atomic():
    for a in apps:
        duplicate_application = Application.objects.get(pk=a.pk)
        duplicate_application.pk = uuid4()
        duplicate_application.student_stats_permission_date="2500-10-10"
        classes_vin_pks = [str(c.pk) for c in a.school_classes.all().filter(
            coordination__unity__name="VIN"
        ).distinct()]
        classes_vin = SchoolClass.objects.filter(pk__in=classes_vin_pks)
        students_vin = a.applicationstudent_set.all().filter(student__classes__in=classes_vin).distinct()
        print("class", classes_vin.count())
        print("students", students_vin.count())
        classes_out_vin = a.school_classes.all().exclude(
            coordination__unity__name="VIN"
        ).distinct()
        a.school_classes.set(classes_out_vin)
        a.save()
        duplicate_application.school_classes.set(classes_vin)
        duplicate_application.save()
        for student in students_vin:
            student.application = duplicate_application
            student.save()




#mudar professores para coordenação em massa e setar permissão específica

tutores = [["giovane.albuquerque@rededecisao.com.br", "GIOVANE DE ALBUQUERQUE", "ACN"],
["janaina.nascimento@rededecisao.com.br", "JANAINA QUITERIO DO NASCIMENTO", "ACN"],
["joao.nascimento@rededecisao.com.br", "JOAO VITOR RODRIGUES DO NASCIMENTO", "CAV"],
["julia.polato@rededecisao.com.br", "JULIA POLATO", "CAV"],
["carlos.souza@rededecisao.com.br", "CARLOS HENRIQUE MARQUES DE SOUZA", "CMV"],
["rosimeire.veronezzi@rededecisao.com.br", "ROSIMEIRE DA SILVA DIAS VERONEZZI", "CMV"],
["ana.ribas@rededecisao.com.br", "ANA CAROLINA SENA RIBAS", "CNE"],
["grazielly.santos@rededecisao.com.br", "GRAZIELLY VITORIA VIEIRA SANTOS", "CNE"],
["julia.ribeiro@rededecisao.com.br", "JULIA RIBEIRO DE OLIVEIRA", "CNE"],
["karen.silva@rededecisao.com.br", "KAREN VANESSA DA SILVA", "CRE"],
["maria.regina@rededecisao.com.br", "MARIA REGINA ALVES GOMES", "CRE"],
["matheus.couras@rededecisao.com.br", "MATHEUS COURAS DOS SANTOS", "CRE"],
["analice.santos@rededecisao.com.br", "ANA ALICE DE CASTRO SANTOS", "CSB"],
["bruna.serrote@rededecisao.com.br", "BRUNA FRAZAO SERROTE DE OLIVEIRA", "CSC"],
["gabriel.martins@rededecisao.com.br", "GABRIEL HENRIQUE CHAGAS MARTINS", "CSP"],
["izabelly.santos@rededecisao.com.br", "IZABELLY GUIMARAES DOS SANTOS", "CSP"],
["geovanna.leal@rededecisao.com.br", "GEOVANNA SANTOS LEAL", "CTM"],
["lucas.nardi@rededecisao.com.br", "LUCAS DIAS NARDI", "DAF"],
["barbara.andrade@rededecisao.com.br", "BARBARA AMARAL DE ANDRADE", "DEC"],
["lucas.felix@rededecisao.com.br", "LUCAS SILVA FELIX", "DEC"],
["ana.dresler@rededecisao.com.br", "ANA CAROLINA FERNANDES DRESLER DE SOUZA", "FAT"],
["marcio.goncalves@rededecisao.com.br", "MARCIO JOAQUIM FERNANDES GONCALVES", "FAT"],
["flavia.lacerda@rededecisao.com.br", "FLAVIA JESUS LACERDA", "GRA"],
["valeria.silva@rededecisao.com.br", "VALERIA ARAUJO GOMES DA SILVA", "GRA"],
["isabella.siqueira@rededecisao.com.br", "ISABELLA SIQUEIRA SANTOS", "GRU"],
["ana.albuquerque@rededecisao.com.br", "ANA CLAUDIA CALVO ALBUQUERQUE", "HOR"],
["bruno.almeida@rededecisao.com.br", "BRUNO DOS REIS DE ALMEIDA", "HOR"],
["caio.almeida@rededecisao.com.br", "CAIO HENRIQUE MOURA DE ALMEIDA", "LOU"],
["gabriel.duarte@rededecisao.com.br", "GABRIEL GRIFFO DUARTE", "MAS"],
["carolina.isler@rededecisao.com.br", "CAROLINA ISLER DE AGUIAR PEREIRA", "OSB"],
["leonardo.scafi@rededecisao.com.br", "LEONARDO HENRIQUE DE OLIVEIRA SCAFI", "OSB"],
["leonardo.costa@rededecisao.com.br", "LEONARDO SILVA COSTA", "POP"],
["ryan.oliveira@rededecisao.com.br", "RYAN PEDRO DE CARVALHO OLIVEIRA", "POP"],
["gabrielli.carvalho@rededecisao.com.br", "GABRIELLI DE CARVALHO", "UNI"],
["giovana.gomes@rededecisao.com.br", "GIOVANA VALADARES GOMES", "VIL"],
["matheus.nolasco@rededecisao.com.br", "MATHEUS AUGUSTO SCHIMIDT NOLASCO", "VIL"],
["rogerio.miniquielo@rededecisao.com.br", "ROGERIO MAINENTI MINIQUIELO", "VIN"],
["sarah.costa@rededecisao.com.br", "SARAH CARDOSO DA COSTA", "VIN"]]

from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.clients.models import CoordinationMember, SchoolCoordination
from fiscallizeon.accounts.models import User, CustomGroup

tutor_group = CustomGroup.objects.filter(
    client__name__icontains="decis",
    name__icontains="tutores"
).first()

for tutor in tutores:
    print(tutor[0])
    inspector = Inspector.objects.filter(user__email=tutor[0]).first()
    if inspector:
        print("tinha inspector")
        inspector.user = None
        inspector.save(skip_hooks=True)
    user, user_created = User.objects.get_or_create(
        email=tutor[0],
        defaults={
            'username':tutor[0],
            'name':tutor[1],
            'is_active':True
        }
    )
    user.custom_groups.set([tutor_group])
    if user_created:
        user.set_password(tutor[0])
        user.save()
    coordinations = SchoolCoordination.objects.filter(
        unity__client__name__icontains="decisão",
        unity__name__icontains=tutor[2]
    )
    for coordination in coordinations:
        member, member_created = CoordinationMember.objects.get_or_create(
            user=user,
            coordination=coordination,
            defaults={
                'is_coordinator':True,
                'is_reviewer':True,
                'is_pedagogic_reviewer':True  
            }
        )





competences = [
    "C1 - Norma Culta",
    "C2 - Tema e Tipo de Texto",
    "C3 - Arg. e Coerência",
    "C4 - Coesão",
    "C5 -  Proposta de Intervenção"
]

from fiscallizeon.answers.models import TextualAnswer
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.corrections.models import CorrectionTextualAnswer

apps = ApplicationStudent.objects.filter(
    student__client__name__icontains="master",
    application__exam="7d64b6b0-5152-4da9-8c37-7602e5c24c07"
)

corrects = CorrectionTextualAnswer.objects.filter(
    textual_answer__student_application__application__exam="7d64b6b0-5152-4da9-8c37-7602e5c24c07"
)


for app in apps:
    text = f'{app.student.name}'
    if not corrects.filter(textual_answer__student_application=app):
        continue
    for comp in competences:
        comp_corre = corrects.filter(
            correction_criterion__name=comp,
            textual_answer__student_application=app
        ).first()
        if comp_corre:
            text+=f',{comp_corre.point}'
        else:
            text+=f',-'
    print(text)


exams = ["P5_Sociologia_M2_ANGLO_2024",
"P5_Matemática_F9_ANGLO_2024",
"P5_Matemática_F8_ANGLO_2024",
"P5_Matemática_F7_ANGLO_2024",
"P5_Matemática_F6_ANGLO_2024",
"P5_Matemática Unificada_M2_ANGLO_2024",
"P5_Matemática Unificada_M1_ANGLO_2024",
"P5_Língua Inglesa_F9_MACMILLAN_2024",
"P5_Língua Inglesa_F8_MACMILLAN_2024",
"P5_Geografia Unificada_M2_ANGLO_2024",
"P5_Geografia Unificada_M1_ANGLO_2024",
"P5_Ciências A_F9_ANGLO_2024",
"P5_Ciências A_F8_ANGLO_2024",
"P5_Ciências A_F7_ANGLO_2024",
"P5_Ciências A_F6_ANGLO_2024",
"P5_Biologia Unificada_M2_ANGLO_2024",
"P5_Biologia Unificada_M1_ANGLO_2024"]

from fiscallizeon.applications.models import ApplicationStudent, Application


application_students = ApplicationStudent.objects.filter(
    application__exam__name__in=exams,
    student__classes__coordination__unity__name="CRE",
    student__classes__school_year=2024,
    textual_answers__isnull=True,
    option_answers__isnull=True,
    file_answers__isnull=True,
)

application_students_cre_with_response = ApplicationStudent.objects.filter(
    Q(application__exam__name__in=exams),
    Q(student__classes__coordination__unity__name="CRE"),
    Q(student__classes__school_year=2024),
    Q(
        Q(textual_answers__isnull=False) |
        Q(option_answers__isnull=False) |
        Q(file_answers__isnull=False)
    )
).distinct()

for app in application_students_cre_with_response:
    print(app.application.exam.name, app.student.name)

applications = Application.objects.filter(
    exam__name__in=exams,
    applicationstudent__student__classes__coordination__unity__name="CRE",
    applicationstudent__student__classes__school_year=2024
).distinct()

for app in applications:
    school_class = app.school_classes.filter(coordination__unity__name="CRE")
    print(app.exam.name, school_class.count())
    for sc in school_class:
        app.school_classes.remove(sc)

apps.count()



from fiscallizeon.exams.models import StatusQuestion

stts = StatusQuestion.objects.filter(
    active=True,
    status=StatusQuestion.ANNULLED,
    exam_question__exam__name__icontains="2024",
    exam_question__exam__coordinations__unity__client__name__icontains="decis"
).distinct()

for st in stts:
    unities = "|".join(list(set(list(st.exam_question.exam_teacher_subject.teacher_subject.teacher.coordinations.all().values_list('unity__name', flat=True)))))
    print(f'{st.exam_question.exam.name}, {st.exam_question.exam.number_print_question(st.exam_question.question)}, {st.note.replace(",",".")}, {st.exam_question.exam_teacher_subject.teacher_subject.teacher.email}, {st.exam_question.exam_teacher_subject.teacher_subject.subject.name}, {unities}')








from fiscallizeon.events.models import Event

applications = ["afe401bb-4f53-48cb-b6a4-aa37fcabc024",
"b3aa06d6-bb03-48dd-a595-ef8c35820a51",
"cde808fb-b253-413a-9188-f2b006bb5a78",
"aca4fd7f-f758-4fbd-a5e7-18ab34f03fef",
"2a968dd0-bd35-430d-873e-dda2759562dd",
"af380370-7809-431d-9268-5a6328c6da6c",
"f30670f2-f413-461b-bf5d-56b09e6995b7",
"857b3d98-3f80-4a87-a75a-3a9f8eb8e6b7",
"a69d05ad-89f9-4c74-8a83-79dcf01d6d50",
"9c86979f-b425-4bc7-b9bc-e2504f8db564",
"a3775543-472d-4302-aa61-aad7f942ebfc"]

events = Event.objects.filter(
    student_application__application__in=applications
)

for e in events:
    print(f'{e.student_application.student.name}, {e.student_application.application.exam.name}, {e.get_event_type_display()}, {e.created_at}, {e.start}, {e.end}') 


    from fiscallizeon.omr.models import OMRUpload, OMRStudents
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.answers.models import OptionAnswer
classes = SchoolClass.objects.filter(
    coordination__unity__client__name__icontains="sesi - sp"
).distinct()

for c in classes:
    print(f'{c.name}, {c.coordination.name}, {c.coordination.unity.name}, {c.created_at.strftime("%d/%m/%Y %H:%M")}, {c.students.count()}')

for c in classes:
    students = OptionAnswer.objects.filter(
        student_application__student__classes=c,
        student_application__application__exam__name__icontains="1ª - diagnóstica"
    ).values_list('student_application__student', flat=True).distinct('student_application__student').count()
    print(f'{c.name}, {c.coordination.name}, {c.coordination.unity.name}, {c.students.count()}, {students}')



from fiscallizeon.applications.models import ApplicationStudent
from django.utils import timezone
data = ["bbdf6cbd-d5d4-4fb0-ae7a-a3d900facd33",
"3f883061-db37-4248-8981-0b2e05bda486",
"5fe0ec2a-d38f-4421-93af-f31d5214e0a8",
"71e6550f-4a1c-42f9-937c-f0513ab7e1f5",
"24474c13-fd66-4b5e-9b55-c127966884b5"]

apps = ApplicationStudent.objects.filter(
    application__in=data
)

for app in apps:
    print(f'{app.application.exam.name}, {app.student.name}, {timezone.localtime(app.start_time).strftime("%d/%m/%Y %H:%M") if app.start_time else ""}, {timezone.localtime(app.end_time).strftime("%d/%m/%Y %H:%M") if app.end_time else ""}')



from fiscallizeon.events.models import Event

events = Event.objects.filter(
    student_application__application__in=data
).distinct()

for e in events:
    print(f'{e.student_application.application.exam.name}, {e.student_application.student.name}, {e.get_event_type_display()}, {timezone.localtime(e.created_at).strftime("%d/%m/%Y %H:%M") if e.created_at else ""}, {timezone.localtime(e.start).strftime("%d/%m/%Y %H:%M") if e.start else ""}, {timezone.localtime(e.end).strftime("%d/%m/%Y %H:%M") if e.end else ""}')


from fiscallizeon.applications.models import ApplicationStudent, Application

ApplicationStudent.objects.filter(
    application__exam__coordinations__unity__client__name__icontains="paraná",
    start_time__isnull=False
).values('application__exam').distinct().count()


Application.objects.filter(
    exam__coordinations__unity__client__name__icontains="paraná",
).distinct().count()


for app in apps:
    aluno = app.student.name
    matricula = app.student.enrollment_number
    nota = 'Ausente' if not app.start_time else str(app.get_total_grade(include_give_score=True)).replace('.', ',')
    caderno = app.application.exam.name
    data = app.application.date_time_start_tz
    print(f'{aluno}; {matricula}; {nota}; {caderno}; {data.strftime("%d/%m/%Y %H:%M")}')



from django.contrib.auth.models import User
from django.core.cache import cache

keys = cache.keys('django.contrib.sessions.cache*')

sts = Student.objects.filter(
    client__name__icontains="decis",
    classes__school_year=2025,
    classes__name__istartswith="M2"
).distinct()


#DESLOGAR USUÁRIOS
from django.core.cache import cache

keys = cache.keys("django.contrib.sessions.cache*")

# Construa um set com os IDs dos usuários para busca rápida
user_ids = {str(s.user.pk) for s in students}

# Itera pelas chaves uma única vez
for k in keys:
    print(k)
    data = cache.get(k)
    if not data:
        continue
    user_id = data.get("_auth_user_id")
    if user_id in user_ids:
        cache.delete(k)

from fiscallizeon.students.models import Student
Student.objects.filter(user__nickname__isnull=False)


from fiscallizeon.applications.models import ApplicationStudent

aps = ApplicationStudent.objects.filter(
    application="d2ab483d-a760-490e-be09-79ce8dc4a241",
    is_omr=True
)

for a in aps:
    to_delete_aps = ApplicationStudent.objects.filter(
        application=a.application,f
        student=a.student,
        is_omr=True
    ).exclude(
        pk=a.pk
    )
    print(to_delete_aps.count())


from fiscallizeon.answers.models import FileAnswer, TextualAnswer, OptionAnswer


opts = OptionAnswer.objects.filter(
    student_application="60a8271c-f978-4702-b247-c9c0a85a56b6",
    status=1
).order_by('created_at')

for o in opts:
    print(o.pk, o.question_option.question.pk, o.question_option.pk, o.created_at, o.created_by)




data = ["PE1_Ciências aplicadas ENEM_M3_ANGLO_2025",
"PE1_Ciências aplicadas ENEM_M3_SAS_2025",
"PE1_Ciências aplicadas FUVEST/Unicamp_M3_ANGLO_2025",
"PE1_Ciências aplicadas FUVEST/Unicamp_M3_SAS_2025",
"PE1_Estudos de obras literárias_M3_ANGLO_2025",
"PE1_Estudos de obras literárias_M3_SAS_2025",
"PE1_Humanidades aplicadas: ENEM_M3_ANGLO_2025",
"PE1_Humanidades aplicadas: ENEM_M3_SAS_2025",
"PE1_Humanidades aplicadas: Fuvest/Unicamp_M3_ANGLO_2025",
"PE1_Humanidades aplicadas: Fuvest/Unicamp_M3_SAS_2025",
"PE1_Redação ENEM_M3_ANGLO_2025",
"PE1_Redação ENEM_M3_SAS_2025",
"PE2_Ciências aplicadas ENEM_M3_ANGLO_2025",
"PE2_Ciências aplicadas ENEM_M3_SAS_2025",
"PE2_Ciências aplicadas FUVEST/Unicamp_M3_ANGLO_2025",
"PE2_Ciências aplicadas FUVEST/Unicamp_M3_SAS_2025",
"PE2_Estudos de obras literárias_M3_ANGLO_2025",
"PE2_Estudos de obras literárias_M3_SAS_2025",
"PE2_Humanidades aplicadas: ENEM_M3_ANGLO_2025",
"PE2_Humanidades aplicadas: ENEM_M3_SAS_2025",
"PE2_Humanidades aplicadas: Fuvest/Unicamp_M3_ANGLO_2025",
"PE2_Humanidades aplicadas: Fuvest/Unicamp_M3_SAS_2025",
"PE2_Redação ENEM_M3_ANGLO_2025",
"PE2_Redação ENEM_M3_SAS_2025",
"PE3_Ciências aplicadas ENEM_M3_ANGLO_2025",
"PE3_Ciências aplicadas ENEM_M3_SAS_2025",
"PE3_Ciências aplicadas FUVEST/Unicamp_M3_ANGLO_2025",
"PE3_Ciências aplicadas FUVEST/Unicamp_M3_SAS_2025",
"PE3_Estudos de obras literárias_M3_ANGLO_2025",
"PE3_Estudos de obras literárias_M3_SAS_2025",
"PE3_Humanidades aplicadas: ENEM_M3_ANGLO_2025",
"PE3_Humanidades aplicadas: ENEM_M3_SAS_2025",
"PE3_Humanidades aplicadas: Fuvest/Unicamp_M3_ANGLO_2025",
"PE3_Humanidades aplicadas: Fuvest/Unicamp_M3_SAS_2025"]


data = ["PE3_Redação ENEM_M3_ANGLO_2025",
"PE3_Redação ENEM_M3_SAS_2025",
"PM2_Redação_F6_ANGLO_2025",
"PM2_Redação_F7_ANGLO_2025",
"PM2_Redação_F8_ANGLO_2025",
"PM2_Redação_F9_ANGLO_2025",
"PM2_Redação_M1_ANGLO_2025",
"PM2_Redação_M2_ANGLO_2025",
"PM2_Redação_M3_ANGLO_2025",
"PM3_Redação_F6_ANGLO_2025",
"PM3_Redação_F7_ANGLO_2025",
"PM3_Redação_F8_ANGLO_2025",
"PM3_Redação_F9_ANGLO_2025",
"PM3_Redação_M1_ANGLO_2025",
"PM3_Redação_M2_ANGLO_2025",
"PM4_Redação_F6_ANGLO_2025",
"PM4_Redação_F7_ANGLO_2025",
"PM4_Redação_F8_ANGLO_2025",
"PM4_Redação_F9_ANGLO_2025",
"PM4_Redação_M1_ANGLO_2025",
"PM4_Redação_M2_ANGLO_2025",
"PM4_Redação_M3_ANGLO_2025",
"PM2_Redação_F6_SAS_2025",
"PM2_Redação_F7_SAS_2025",
"PM2_Redação_F8_SAS_2025",
"PM2_Redação_F9_SAS_2025",
"PM2_Redação_M1_SAS_2025",
"PM2_Redação_M2_SAS_2025",
"PM2_Redação_M3_SAS_2025",
"PM3_Redação_F6_SAS_2025",
"PM3_Redação_F7_SAS_2025",
"PM3_Redação_F8_SAS_2025",
"PM3_Redação_F9_SAS_2025",
"PM3_Redação_M1_SAS_2025",
"PM3_Redação_M2_SAS_2025",
"PM4_Redação_F6_SAS_2025",
"PM4_Redação_F7_SAS_2025",
"PM4_Redação_F8_SAS_2025",
"PM4_Redação_F9_SAS_2025",
"PM4_Redação_M1_SAS_2025",
"PM4_Redação_M2_SAS_2025",
"PM4_Redação_M3_SAS_2025",
"P3_Redação_F6_SAS_2025",
"P3_Redação_F7_SAS_2025",
"P3_Redação_F8_SAS_2025",
"P3_Redação_F9_SAS_2025",
"P3_Redação_M1_SAS_2025",
"P3_Redação_M2_SAS_2025",
"P4_Redação_F6_SAS_2025",
"P4_Redação_F7_SAS_2025",
"P4_Redação_F8_SAS_2025",
"P4_Redação_F9_SAS_2025",
"P4_Redação_M1_SAS_2025",
"P4_Redação_M2_SAS_2025",
"P4_Redação_M3_SAS_2025",
"P5_Redação_F6_SAS_2025",
"P5_Redação_F7_SAS_2025",
"P5_Redação_F8_SAS_2025",
"P5_Redação_F9_SAS_2025",
"P5_Redação_M1_SAS_2025",
"P5_Redação_M2_SAS_2025",
"P6_Redação_F6_SAS_2025",
"P6_Redação_F7_SAS_2025",
"P6_Redação_F8_SAS_2025",
"P6_Redação_F9_SAS_2025",
"P6_Redação_M1_SAS_2025",
"P6_Redação_M2_SAS_2025",
"P6_Redação_M3_SAS_2025",
"P3_Redação_F6_ANGLO_2025",
"P3_Redação_F7_ANGLO_2025",
"P3_Redação_F8_ANGLO_2025",
"P3_Redação_F9_ANGLO_2025",
"P3_Redação_M1_ANGLO_2025",
"P3_Redação_M2_ANGLO_2025",
"P4_Redação_F6_ANGLO_2025",
"P4_Redação_F7_ANGLO_2025",
"P4_Redação_F8_ANGLO_2025",
"P4_Redação_F9_ANGLO_2025",
"P4_Redação_M1_ANGLO_2025",
"P4_Redação_M2_ANGLO_2025",
"P4_Redação_M3_ANGLO_2025",
"P5_Redação_F6_ANGLO_2025",
"P5_Redação_F7_ANGLO_2025",
"P5_Redação_F8_ANGLO_2025",
"P5_Redação_F9_ANGLO_2025",
"P5_Redação_M1_ANGLO_2025",
"P5_Redação_M2_ANGLO_2025",
"P6_Redação_F6_ANGLO_2025",
"P6_Redação_F7_ANGLO_2025",
"P6_Redação_F8_ANGLO_2025",
"P6_Redação_F9_ANGLO_2025",
"P6_Redação_M1_ANGLO_2025",
"P6_Redação_M2_ANGLO_2025",
"P6_Redação_M3_ANGLO_2025",
"PM2_Redação_F6_ANGLO_2025",
"PM2_Redação_F7_ANGLO_2025",
"PM2_Redação_F8_ANGLO_2025",
"PM2_Redação_F9_ANGLO_2025",
"PM2_Redação_M1_ANGLO_2025",
"PM2_Redação_M2_ANGLO_2025",
"PM2_Redação_M3_ANGLO_2025",
"PM3_Redação_F6_ANGLO_2025",
"PM3_Redação_F7_ANGLO_2025",
"PM3_Redação_F8_ANGLO_2025",
"PM3_Redação_F9_ANGLO_2025",
"PM3_Redação_M1_ANGLO_2025",
"PM3_Redação_M2_ANGLO_2025",
"PM4_Redação_F6_ANGLO_2025",
"PM4_Redação_F7_ANGLO_2025",
"PM4_Redação_F8_ANGLO_2025",
"PM4_Redação_F9_ANGLO_2025",
"PM4_Redação_M1_ANGLO_2025",
"PM4_Redação_M2_ANGLO_2025",
"PM4_Redação_M3_ANGLO_2025",
"PM2_Redação_F6_SAS_2025",
"PM2_Redação_F7_SAS_2025",
"PM2_Redação_F8_SAS_2025",
"PM2_Redação_F9_SAS_2025",
"PM2_Redação_M1_SAS_2025",
"PM2_Redação_M2_SAS_2025",
"PM2_Redação_M3_SAS_2025",
"PM3_Redação_F6_SAS_2025",
"PM3_Redação_F7_SAS_2025",
"PM3_Redação_F8_SAS_2025",
"PM3_Redação_F9_SAS_2025",
"PM3_Redação_M1_SAS_2025",
"PM3_Redação_M2_SAS_2025",
"PM4_Redação_F6_SAS_2025",
"PM4_Redação_F7_SAS_2025",
"PM4_Redação_F8_SAS_2025",
"PM4_Redação_F9_SAS_2025",
"PM4_Redação_M1_SAS_2025",
"PM4_Redação_M2_SAS_2025",
"PM4_Redação_M3_SAS_2025",
"SE3_Redação_M3_ANGLO_2025",
"SE4_Redação_M3_ANGLO_2025",
"SE5_Redação_M3_ANGLO_2025",
"SE6_Redação_M3_ANGLO_2025",
"SE3_Redação_M3_SAS_2025",
"SE4_Redação_M3_SAS_2025",
"SE5_Redação_M3_SAS_2025",
"SE6_Redação_M3_SAS_2025",
"SR1_Redação_M3_ANGLO_2025",
"SR2_Redação_M3_ANGLO_2025",
"SR3_Redação_M3_ANGLO_2025",
"SR1_Redação_M3_SAS_2025",
"SR2_Redação_M3_SAS_2025",
"SR3_Redação_M3_SAS_2025",
"SR1_Redação ENEM_M3_ANGLO_2025",
"SR2_Redação ENEM_M3_ANGLO_2025",
"SR3_Redação ENEM_M3_ANGLO_2025",
"SR1_Redação ENEM_M3_SAS_2025",
"SR2_Redação ENEM_M3_SAS_2025",
"SR3_Redação ENEM_M3_SAS_2025",
"SE1_Redação ENEM_M3_ANGLO_2025",
"SE2_Redação ENEM_M3_ANGLO_2025",
"SE3_Redação ENEM_M3_ANGLO_2025",
"SE4_Redação ENEM_M3_ANGLO_2025",
"SE5_Redação ENEM_M3_ANGLO_2025",
"SE6_Redação ENEM_M3_ANGLO_2025",
"SE1_Redação ENEM_M3_SAS_2025",
"SE2_Redação ENEM_M3_SAS_2025",
"SE3_Redação ENEM_M3_SAS_2025",
"SE4_Redação ENEM_M3_SAS_2025",
"SE5_Redação ENEM_M3_SAS_2025",
"SE6_Redação ENEM_M3_SAS_2025"]

from fiscallizeon.exams.models import ExamQuestion, Exam
from fiscallizeon.questions.models import Question

for index, exam_name in enumerate(data):
    exam = Exam.objects.filter(
        name=exam_name,
        coordinations__unity__client__name__icontains="decis"
    ).first()
    if not exam:
        print(f"{exam_name}, Não encontrado")
        continue
    if exam.examquestion_set.all().exists():
        print(f"{exam_name}, Já tem 1 questão")
        continue
    exam_teacher_subject = exam.examteachersubject_set.all().first()
    if not exam_teacher_subject:
        print(f"{exam_name}, Sem solicitação")
        continue
    print(exam_teacher_subject)
    question, created = Question.objects.get_or_create(
        subject=exam_teacher_subject.teacher_subject.subject,
        grade=exam_teacher_subject.grade,
        enunciation="<p>Digite a nota do aluno no instrumento de redação aplicado</p>",
        category=Question.FILE,
        created_by=exam_teacher_subject.teacher_subject.teacher.user,
    )
    ExamQuestion.objects.get_or_create(
        question=question,
        exam=exam,
        exam_teacher_subject=exam_teacher_subject,
        order=1,
        weight=10
    )



from fiscallizeon.exams.models import Exam, StatusQuestion

exams = Exam.objects.filter(
    Q(coordinations__unity__client__name__icontains="decis"),
    Q(
        Q(name__icontains="PE1_")
    ),
    Q(created_at__year=2025)
).distinct()

statusus = StatusQuestion.objects.filter(
    exam_question__exam__in=exams,
    active=True,
    status=8
)
for status in statusus:
    print(status.exam_question.exam.name)
    status.status = StatusQuestion.OPENED
    status.save(skip_hooks=True)
    print(status.get_status_display())



from fiscallizeon.exams.models import Exam, ExamQuestion, StatusQuestion
from fiscallizeon.questions.models import Question
from django.db.models import Q
exams = Exam.objects.filter(
    Q(coordinations__unity__client__name__icontains="decis",),
    Q(created_at__year=2025,),
    Q(name__istartswith="p2_"),
    Q(
        Q(name__icontains="m1") |
        Q(name__icontains="m2") |
        Q(name__icontains="m3") |
        Q(name__icontains="f6") |
        Q(name__icontains="f7") |
        Q(name__icontains="f8") |
        Q(name__icontains="f9") 
    )
).exclude(
    Q(name__icontains="redação")
).distinct()


#MODIFICAR PESO DAS QUESTÕES PARA OBJETIVAS TEREM 5 PONTOS E DISCURSIVAS TEREM 5 PONTOS
from fiscallizeon.exams.models import Exam
from django.db.models import Q

for e in exams:
    print(e.name, e.total_grade, e.total_weight)

for exam in exams:
    total_exam_questions = ExamQuestion.objects.filter(exam=exam).availables()
    exam_questions_choice = ExamQuestion.objects.filter(exam=exam, question__category=Question.CHOICE).availables()
    exam_questions_textual = ExamQuestion.objects.filter(exam=exam).exclude(question__category=Question.CHOICE).availables()
    annuleds = StatusQuestion.objects.filter(
        exam_question__exam=exam, 
        status=StatusQuestion.ANNULLED,
        active=True
    )
    grade_choice = 5/exam_questions_choice.count()
    grade_textual = 5/exam_questions_textual.count()
    factor = 0
    for annuled in annuleds:
        category_question_annuled = annuleds.first().exam_question.question.category
        if category_question_annuled == Question.CHOICE:
            factor += grade_choice/total_exam_questions.availables(exclude_annuleds=True).count()
        else:
            factor += grade_textual/total_exam_questions.availables(exclude_annuleds=True).count()
        print(factor, grade_choice, grade_textual, category_question_annuled)
    for eq_choice in exam_questions_choice:
        eq_choice.weight = grade_choice
        if eq_choice not in annuleds.values_list('exam_question', flat=True):
            eq_choice.weight += factor
        eq_choice.save(skip_hooks=True)
    for eq_textual in exam_questions_textual:
        eq_textual.weight = grade_textual
        if eq_textual not in annuleds.values_list('exam_question', flat=True):
            eq_textual.weight += factor
        eq_textual.save(skip_hooks=True)
    print(f"{exam.name}, {exam_questions_choice.count()}, {exam_questions_textual.count()}, {annuleds.count()}")


#ajustar aplicação de alunos duplicados


from fiscallizeon.accounts.models import User

users = User.objects.filter(
    student__client__name__icontains="dehon",
    student__classes__school_year=2025,
    student__classes__grade__name__in=["6","7"]
).distinct()


names = ["Maria luiza Koshiyama",
"Maria Eduarda Rueda Achiles",
"Luis Felipe de Lima Campos",
"Nicole Pereira Ramos Lira",
"Ryan Souza Abreu Silva"]

from fiscallizeon.students.models import Student

for n in names:
    students = Student.objects.filter(
        client__name__icontains="deci",
        name__icontains=n
    ).distinct()
    for s in students:
        print(s.name, s.user.is_active, s.email, s.enrollment_number)





from fiscallizeon.applications.models import Application, ApplicationStudent

apps = Application.objects.filter(
    Q(exam__coordinations__unity__client__name__icontains="deci"),
    Q(exam__name__icontains="P2"),
    Q(created_at__year=2025)
).distinct()

for app in apps:
    application_students = ApplicationStudent.objects.filter(
        Q(application=app),
        Q(
            Q(option_answers__isnull=False) |
            Q(file_answers__isnull=False) |
            Q(textual_answers__isnull=False)
        )
    ).distinct().order_by('student__name')
    repeated_students = []
    for application_student in application_students:
        repeateds = ApplicationStudent.objects.filter(
            Q(application=app),
            Q(student__name__iexact=application_student.student.name),
            Q(
                Q(option_answers__isnull=False) |
                Q(file_answers__isnull=False) |
                Q(textual_answers__isnull=False)
            )
        ).exclude(
            pk=application_student.pk
        ).distinct()
        count_repeateds = repeateds.count()
        if count_repeateds > 0:
            repeated_students.append(application_student.pk)
            student = application_student.student
            school_class = student.get_last_class()
            if app and student and school_class:
                user_is_active = student.user.is_active
                has_objective = application_student.option_answers.exists()
                has_discursive = application_student.file_answers.exists() or application_student.textual_answers.exists()
                print(
                    f'{app.exam.name},{student.pk},{student.name},{student.email},{student.enrollment_number},{school_class.name},{school_class.coordination.unity.name},{count_repeateds},{user_is_active},{has_objective},{has_discursive}'
                )



#AJUSTA DISCIPLINAS INCORRETAS EM CADERNO DE INGLES

exams = ["5b17b94c-c767-44f3-90a4-fe37f9c96e0b",
"4f07ca63-8b25-4d49-aae0-d6c83d148af0",
"50de4e23-1a3f-4ddf-8799-22df3ba3927b",
"e8b57e64-af1f-4b17-992f-f0e36311e2ea",
"0f794117-af46-4dd3-b0b0-49b444232c82",
"19c5537d-6cf8-48dc-ba6d-ec4036541d1f",
"1953f399-7ab6-4742-a036-2862e90a2f24",
"4fd7b446-ad54-46b8-92fb-3b64a565ab75",
"f90130f7-94fe-4d51-bdff-b5f1381e1d8d",
"d6ed0a73-943a-4692-935a-546189e810a4",
"f1584137-6023-4f19-a5bc-e50d2ae58250",
"528e8770-6ac5-41f2-a465-e3d47dba341b",
"f4337241-2bfb-4552-bbf5-13281096345f"]

from fiscallizeon.exams.models import Exam
from fiscallizeon.inspectors.models import TeacherSubject
from fiscallizeon.subjects.models import Subject

for exam in Exam.objects.filter(pk__in=exams):
    print("----", exam.name)
    for exam_teacher_subject in exam.examteachersubject_set.all():
        if (
            str(exam_teacher_subject.teacher_subject.subject.pk)
            == "89695ca2-59af-41c3-b53b-04e32912db0f"
        ):
            teacher_subject, _ = TeacherSubject.objects.get_or_create(
                teacher=exam_teacher_subject.teacher_subject.teacher,
                subject=Subject.objects.get(pk="78cf170c-7194-4436-b8c0-31416c883116"),
                defaults={
                    'active': True,
                    'school_year': 2025
                }
            )
            exam_teacher_subject.teacher_subject = teacher_subject
            exam_teacher_subject.save()

