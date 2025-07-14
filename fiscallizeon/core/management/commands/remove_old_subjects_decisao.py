from django.core.management.base import BaseCommand
from fiscallizeon.clients.models import Client
from fiscallizeon.subjects.models import KnowledgeArea, Subject
from fiscallizeon.exams.models import ExamTeacherSubject, Exam, ExamQuestion
from fiscallizeon.inspectors.models import TeacherSubject
from django.db import transaction



class Command(BaseCommand):
    help = 'Remove disciplinas antigas das provas do decisao'

    def handle(self, *args, **kwargs):
        with transaction.atomic():

            client = Client.objects.get(pk="a2b1158b-367a-40a4-8413-9897057c8aa2")
            subjects_client = Subject.objects.filter(
                client=client,
                parent_subject__isnull=False
            )
            subjects_fiscallize = Subject.objects.filter(
                client__isnull=True
            )

            old_exam_teacher_subjects = list(ExamTeacherSubject.objects.filter(
                exam__coordinations__unity__client=client,
                teacher_subject__subject__in=subjects_fiscallize
            ).distinct().values(
                "pk",
                "teacher_subject__subject", "teacher_subject__subject__knowledge_area",
                "teacher_subject__teacher",
                "teacher_subject__subject__name",
                "teacher_subject"
                )
            )

            for old_exam_teacher_subject in old_exam_teacher_subjects:
                new_teacher_subject = None

                new_subject = subjects_client.filter(
                    parent_subject=old_exam_teacher_subject["teacher_subject__subject"],
                    knowledge_area=old_exam_teacher_subject["teacher_subject__subject__knowledge_area"]
                ).first()
                
                new_teacher_subject = TeacherSubject.objects.filter(
                    teacher=old_exam_teacher_subject["teacher_subject__teacher"],
                    subject=new_subject
                ).first()

                if not new_teacher_subject:
                    new_teacher_subject = TeacherSubject.objects.get(pk=old_exam_teacher_subject["teacher_subject"])
                    new_teacher_subject.subject = new_subject
                    new_teacher_subject.save()

                exam_questions = ExamQuestion.objects.filter(
                    exam_teacher_subject=old_exam_teacher_subject['pk']
                ).distinct()

                for exam_question in exam_questions:
                    exam_question.question.subject = new_subject
                    exam_question.question.save()

                print(
                    old_exam_teacher_subject["teacher_subject__subject__name"], "||",
                    new_subject.name, "##",
                    new_teacher_subject
                )

                TeacherSubject.objects.filter(
                    subject__in=subjects_fiscallize,
                    teacher__coordinations__unity__client=client
                ).distinct().update(
                    active=False,
                    school_year=2021
                )