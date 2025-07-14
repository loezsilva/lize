import csv
from django.db.models import Q
from fiscallizeon.exams.models import Exam
from fiscallizeon.answers.models import Attachments
from fiscallizeon.applications.models import ApplicationStudent
exams = Exam.objects.filter(
    Q(
        Q(name__icontains="ph 09") |
        Q(name__icontains="ph 10") |
        Q(name__icontains="ph 11")

    )
).exclude(
    Q(name__icontains="curso")
)
for exam in exams:
    print(text_exam)
    header = []
    header.append(exam.name)
    header.append("Iniciou?")
    for exam_teacher_subject in exam.examteachersubject_set.all().order_by('order'):
        header.append(exam_teacher_subject.teacher_subject.subject.name)
    application_students = ApplicationStudent.objects.filter(
        application__exam=exam
    )
    line_result = []
    for application_student in application_students:
        line = []
        line.append(application_student.student.name)
        if application_student.start_time:
            line.append("Sim")
        else:
            line.append("Não")
        for exam_teacher_subject in exam.examteachersubject_set.all().order_by('order'):
            count = Attachments.objects.filter(
                application_student=application_student,
                exam_teacher_subject=exam_teacher_subject
            ).distinct().count()
            line.append(count)
        line_result.append(line)
    with open(f'tmp/{exam.name.replace(" ", "_").replace("-", "").replace("__", "_")}.csv', 'w', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(line_result)