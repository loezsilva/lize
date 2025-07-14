from fiscallizeon.exams.models import Exam, ExamTeacherSubject
from fiscallizeon.subjects.models import Subject
from fiscallizeon.inspectors.models import TeacherSubject

exams_names = [
    # "P1 - BLOCO 03 - PV1",
    # "P1 - BLOCO 04 - PV1",
    # "P1 - BLOCO 03 - PV2",
    # "P1 - BLOCO 04 - PV2",
    "P1 - BLOCO 02 - 3000"
]

disc_name = "Matemática"
disc_a = Subject.objects.filter(name=f'{disc_name} A', client__name__icontains="tamandar").distinct()
disc_b = Subject.objects.filter(name=f'{disc_name} B', client__name__icontains="tamandar").distinct()
disc_c = Subject.objects.filter(name=f'{disc_name} C', client__name__icontains="tamandar").distinct()

if disc_a.count() > 1 or disc_b.count() > 1 or disc_c.count() > 1:
    print("error mais q 1")

for exam_name in exams_names:
    exam = Exam.objects.filter(
        coordinations__unity__client__name__icontains="tamand",
        name=exam_name
    ).distinct()
    exam_teacher_subjects = exam.first().examteachersubject_set.filter(
        teacher_subject__subject__name__icontains=disc_name
    ).order_by('order')
    if exam_teacher_subjects.count() > 3 or exam_teacher_subjects.count() < 3:
        print("maior que 3", exam_teacher_subjects.count(), exam_name)
        continue
    teacher_subject_a, created = TeacherSubject.objects.get_or_create(
        subject=disc_a.first(),
        teacher=exam_teacher_subjects[0].teacher_subject.teacher
    )
    exam_teacher_subject_a = exam_teacher_subjects[0]
    exam_teacher_subject_b = exam_teacher_subjects[1]
    exam_teacher_subject_c = exam_teacher_subjects[2]
    exam_teacher_subject_a.teacher_subject = teacher_subject_a
    exam_teacher_subject_a.save(skip_hooks=True)
    print(exam_teacher_subject_a.teacher_subject.subject.name, teacher_subject_a.subject.name)
    teacher_subject_b, _ = TeacherSubject.objects.get_or_create(
        subject=disc_b.first(),
        teacher=exam_teacher_subject_b.teacher_subject.teacher
    )
    exam_teacher_subject_b.teacher_subject = teacher_subject_b 
    exam_teacher_subject_b.save(skip_hooks=True)
    teacher_subject_c, _ = TeacherSubject.objects.get_or_create(
        subject=disc_c.first(),
        teacher=exam_teacher_subject_c.teacher_subject.teacher
    )
    exam_teacher_subject_c.teacher_subject = teacher_subject_c 
    exam_teacher_subject_c.save(skip_hooks=True)
    print(exam_teacher_subject_b.teacher_subject.subject.name, teacher_subject_c.subject.name)
    print("mudou", exam_name)