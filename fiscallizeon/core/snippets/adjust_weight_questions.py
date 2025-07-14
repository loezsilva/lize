from decimal import Decimal
from fiscallizeon.core.utils import round_half_up
from fiscallizeon.exams.models import ExamTeacherSubject

exam_teacher_subjecs = ExamTeacherSubject.objects.filter(subject_note__isnull=False)
    
for exam_teacher_subjec in exam_teacher_subjecs:
    total_weight = exam_teacher_subjec.subject_note
    exam_questions = exam_teacher_subjec.examquestion_set.all().availables()
    total_questions = exam_questions.count()
    if total_questions > 0:
        unique_weight = round_half_up(Decimal(total_weight/total_questions), 6)
        for question in exam_questions:
            question_weight = round_half_up(Decimal(question.weight), 6)
            if question_weight != unique_weight:
                question.weight = unique_weight
                question.save()
                print(question.weight, unique_weight, question.exam.coordinations.all().first().unity.client.name, question.exam.name)