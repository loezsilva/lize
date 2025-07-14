import uuid
from datetime import datetime

from django.db import models
from django.db.models import Q, Count, Sum, Subquery, OuterRef, Case, When
from django.apps import apps

class KnowledgeAreaQuerySet(models.QuerySet):
    def student_general_report(self, student, start_date=None, end_date=None):
        KnowledgeArea = apps.get_model('subjects', 'KnowledgeArea')
        OptionAnswer = apps.get_model('answers', 'OptionAnswer')

        start_date = start_date or datetime.min.date()
        end_date = end_date or datetime.max.date()

        finished_applications_student = student.get_finished_application_student()

        last_answers = OptionAnswer.objects.filter(
            question_option__question__topic__subject__knowledge_area=OuterRef('pk'),
            student_application__in=finished_applications_student,
            status=OptionAnswer.ACTIVE,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )

        knowledge_areas = KnowledgeArea.objects.filter(
            subject__topic__question__exams__application__applicationstudent__in=finished_applications_student,
            subject__topic__question__exams__application__date__lte=end_date,
            subject__topic__question__exams__application__date__gte=start_date,
        ).distinct()
        
        return knowledge_areas.annotate(
            answered_questions=Subquery(
                last_answers.values('question_option__question__topic__subject__knowledge_area').annotate(c=Count('pk')).values('c')[:1]
            ),
            correct_answered_questions=Subquery(
                last_answers.filter(
                    question_option__is_correct=True
                ).values(
                    'question_option__question__topic__subject__knowledge_area'
                ).annotate(
                    c=Count('pk')
                ).values('c')[:1]
            ),
            total_time=Sum(
                'subject__topic__question__alternatives__optionanswer__duration',
                filter=Q(
                    Q(subject__topic__question__alternatives__optionanswer__student_application__in=finished_applications_student),
                    Q(subject__topic__question__alternatives__optionanswer__created_at__date__gte=start_date),
                    Q(subject__topic__question__alternatives__optionanswer__created_at__date__lte=end_date),
                ),
                distinct=True
            )
        ).distinct()


    def student_application_general_report(self, student_application):
        KnowledgeArea = apps.get_model('subjects', 'KnowledgeArea')
        OptionAnswer = apps.get_model('answers', 'OptionAnswer')

        last_answers = OptionAnswer.objects.filter(
            question_option__question__topic__subject__knowledge_area=OuterRef('pk'),
            student_application=student_application,
            status=OptionAnswer.ACTIVE,
        )
        
        knowledge_areas = KnowledgeArea.objects.filter(
            subject__topic__question__exams__application__applicationstudent=student_application,
            subject__topic__question__exams__application__applicationstudent__end_time__isnull=False,
        ).distinct()
        
        return knowledge_areas.annotate(
            answered_questions=Subquery(
                last_answers.values('question_option__question__topic__subject__knowledge_area').annotate(c=Count('pk')).values('c')[:1]
            ),
            correct_answered_questions=Subquery(
                last_answers.filter(
                    question_option__is_correct=True
                ).values(
                    'question_option__question__topic__subject__knowledge_area'
                ).annotate(
                    c=Count('pk')
                ).values('c')[:1]
            ),
            total_time=Sum(
                'subject__topic__question__alternatives__optionanswer__duration',
                filter=Q(subject__topic__question__alternatives__optionanswer__student_application=student_application),
                distinct=True
            )
        ).distinct()


    def has_public_questions(self):
        return self.filter(pk__in=[
            "11228db6-f401-4ac7-8fd8-e6717bc4e553",
            "cbafbbba-323e-4e46-be76-abcb5c537490",
            "b9eceae4-855a-40f9-9f5e-aa8c942485b2",
            "990d414c-ebd1-49f1-a185-005c229178d5",
            "41c911a2-9597-4c8f-8e8f-178749fc11db",
        ])

class SubjectQuerySet(models.QuerySet):
    def get_clients_subjects(self, clients):
        return self.filter(
            Q(client__isnull=True) |
            Q(client__in=clients)
        ).distinct()
    
    def get_ordered_pks(self, pk_ids):
        preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(pk_ids)])
        return self.filter(pk__in=pk_ids).order_by(preserved)
    
    def annotate_questions_count(self, exam):
        ExamQuestion = apps.get_model('exams', 'ExamQuestion')

        if exam.is_abstract:
            return self.annotate(
                questions_count=Subquery(
                    ExamQuestion.objects.filter(
                        exam=exam,
                        question__subject=OuterRef('pk')
                    ).availables().order_by().values('question__subject').annotate(
                        total=Count('pk')
                    ).values('total')[:1]
                )
            )
        
        return self.annotate(
            questions_count=Subquery(
                    ExamQuestion.objects.filter(
                        exam=exam,
                        exam_teacher_subject__teacher_subject__subject=OuterRef('pk')
                    ).availables().order_by().values(
                        'exam_teacher_subject__teacher_subject__subject'
                    ).annotate(
                        total=Count('pk')
                    ).values('total')[:1]
                )
        )

    def get_public_questions_subjects(self, segment, request_subject):

        if request_subject:
            subjects_ids = [uuid.UUID(str(request_subject))]
        else:
            subjects_ids = [
                uuid.UUID('0efcdaa7-6b9c-45f7-a7c5-db4d5598a792'),
                uuid.UUID('5bb08bf4-9023-4a54-99a7-d8abcfe82269'),
                uuid.UUID('fbbb4435-1df9-4812-ae29-34f3e6c78cfa'),
                uuid.UUID('90b3c199-77b4-43b7-b7e6-90e72b16a669'),
                uuid.UUID('5fe8484c-559e-4e75-9af6-4df9cf8847a1'),
                uuid.UUID('02664d36-c9ce-4341-9722-101379960eda'),
                uuid.UUID('53ddfea3-6c2b-46bd-a1e2-d04f26fabee4'),
                uuid.UUID('f109c14f-bd66-4241-bb61-06d0930b5c00'),
                uuid.UUID('50546b9b-b82e-4004-8f5a-f03eba7c14f2'),
                uuid.UUID('d8ffdbed-a6e5-4b9f-8f11-1eb2d944769e'),
                uuid.UUID('3cfde1cf-5e9c-4461-b904-8d3854359f7c'),
                uuid.UUID('904d690c-6c74-4f92-833e-d736188a79a1'),
                uuid.UUID('29b82131-5ab7-4822-b5cc-4052cc1d5443'),
                uuid.UUID('35a9bee8-ac00-4d0d-b75c-fc6a16db4745'),
                uuid.UUID('a4fd4568-5809-4d56-bb81-3a96c2914a81'),
                uuid.UUID('b63dc2f9-ec1d-4060-b300-89c8d53049bc'),
                uuid.UUID('d172fe20-31f1-4b96-8128-16bea752ca84'),
                uuid.UUID('2a771795-d43a-47b6-bbc5-90e60f6082ce'),
                uuid.UUID('dd970eef-c68a-4831-a144-f97901a0e615'),
            ]

        return self.filter(
            pk__in=subjects_ids, 
            knowledge_area__grades__level=segment
        )


class TopicQuerySet(models.QuerySet):
    def get_public_questions_topics_by_subject(self, subject_id):
        return self.filter(
            Q(questions__is_public=True),
            main_topic__isnull=True,
            theme__isnull=True,
            subject_id=subject_id
        ).distinct()
    
    def get_public_questions_topics_by_theme(self, theme):
        return self.filter(
            questions__is_public=True,
            theme=theme,
        ).distinct()
    
    def get_public_questions_topics_by_main_topic(self, main_topic):
        return self.filter(
            questions__is_public=True,
            main_topic=main_topic,
        ).distinct()

class MainTopicQuerySet(models.QuerySet):
    def get_public_questions_main_topics_by_subject(self, subject_id):
        return self.filter(
            topic__questions__is_public=True,
            topic__subject=subject_id,
        ).distinct()
    
    def get_public_questions_main_topics_by_theme(self, theme):
        return self.filter(
            topic__questions__is_public=True,
            theme=theme,
        ).distinct()

KnowledgeAreaManager = models.Manager.from_queryset(KnowledgeAreaQuerySet)
SubjectManager = models.Manager.from_queryset(SubjectQuerySet)
TopicManager = models.Manager.from_queryset(TopicQuerySet)
MainTopicManager = models.Manager.from_queryset(MainTopicQuerySet)