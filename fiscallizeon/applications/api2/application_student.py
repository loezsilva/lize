from django.db.models import (
    Q, F, Subquery, OuterRef, Case, When, Value, DecimalField, BooleanField, CharField, UUIDField
)


from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from fiscallizeon.answers.models import FileAnswer, TextualAnswer, OptionAnswer
from fiscallizeon.core.paginations import LimitOffsetPagination
from fiscallizeon.exams.models import ExamQuestion

from ..models import ApplicationStudent
from ..serializers2.application_student import (
    ApplicationStudentResultSerializer, ApplicationStudentAnswerSerializer,
)


@extend_schema(tags=['Resultados'])
class ApplicationStudentResultListView(ListAPIView):
    serializer_class = ApplicationStudentResultSerializer
    pagination_class = LimitOffsetPagination
    required_scopes = ['read', 'write']

    filterset_fields = (
        'application__exam',
        'application__exam__examteachersubject__teacher_subject__subject',
        'application__date',
        'student',
    )

    def get_queryset(self):
        queryset = (
            ApplicationStudent.objects.filter(
                Q(
                    missed=False,
                    # application__exam__is_abstract=False,
                    student__client_id=self.request.user.client_pk,
                    # application__exam__examteachersubject__teacher_subject__subject__isnull=False,
                )
                # & Q(
                #     Q(option_answers__isnull=False)
                #     | Q(file_answers__isnull=False)
                #     | Q(textual_answers__isnull=False)
                # ),
            )
            .annotate(
                has_answer=Case(
                    When(
                        Q(textual_answers__isnull=False)
                        | Q(file_answers__isnull=False)
                        | Q(option_answers__isnull=False)
                        | Q(sum_answers__isnull=False),
                        then=Value(True),
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                )
            )
            .annotate(
                subject_id=Case(
                    When(
                        Q(application__exam__is_abstract=False),
                        then=F('application__exam__examteachersubject__teacher_subject__subject__id')
                    ),
                    default=F('application__exam__examquestion__question__subject__id'),
                    output_field=UUIDField(),
                )
            )
            .annotate(
                subject_name=Case(
                    When(
                        Q(application__exam__is_abstract=False),
                        then=F('application__exam__examteachersubject__teacher_subject__subject__name')
                    ),
                    default=F('application__exam__examquestion__question__subject__name'),
                    output_field=CharField(),
                )
            )
            .filter(has_answer=True)
            .values(
                'id',
                'subject_id',
                'subject_name',
                # 'application__exam__examteachersubject__teacher_subject__subject__id',
                # 'application__exam__examteachersubject__teacher_subject__subject__name',
                'application__id',
                'student__id',
                'student__name',
                'student__enrollment_number',
                'application__exam__id',
                'application__exam__name',
                'application__exam__id_erp',
                'application__exam__teaching_stage__code_export',
            )
            .order_by('-application__date')
            .distinct()
        )

        return queryset


@extend_schema(tags=['Respostas'])
class ApplicationStudentAnswerListView(ListAPIView):
    serializer_class = ApplicationStudentAnswerSerializer
    pagination_class = LimitOffsetPagination
    required_scopes = ['read', 'write']

    def get_queryset(self):
        client_ids = self.request.user.get_clients_cache()
        option_answers = OptionAnswer.objects.filter(
            student_application__student__client__in=client_ids,
        ).annotate(
            content=F('question_option__text'),
            student_id=F('student_application__student'),
            exam_question=Subquery(
                ExamQuestion.objects.filter(
                    exam=OuterRef('student_application__application__exam'),
                    question=OuterRef('question_option__question')
                ).values('pk')[:1]
            ),
            weight=Subquery(
                ExamQuestion.objects.filter(
                    exam=OuterRef('student_application__application__exam'),
                    question=OuterRef('question_option__question')
                ).values('weight')[:1]
            ),
            grade=Case(
                When(question_option__is_correct=True, then=F('weight')),
                default=Value(0, output_field=DecimalField())
            ),
            category=Value('choice')
        ).values('id', 'exam_question', 'content', 'student_id', 'weight', 'grade', 'category')

        textual_answers = TextualAnswer.objects.filter(
            student_application__student__client__in=client_ids,
        ).annotate(
            student_id=F('student_application__student'),
            exam_question=Subquery(
                ExamQuestion.objects.filter(
                    exam=OuterRef('student_application__application__exam'),
                    question=OuterRef('question')
                ).values('pk')[:1]
            ),
            weight=Subquery(
                ExamQuestion.objects.filter(
                    exam=OuterRef('student_application__application__exam'),
                    question=OuterRef('question')
                ).values('weight')[:1]
            ),
            grade=F('teacher_grade'),
            category=Value('textual'),
        ).values('id', 'exam_question', 'content', 'student_id', 'weight', 'grade', 'category')

        file_answers = FileAnswer.objects.filter(
            student_application__student__client__in=client_ids,
        ).annotate(
            content=F('arquivo'),
            student_id=F('student_application__student'),
            exam_question=Subquery(
                ExamQuestion.objects.filter(
                    exam=OuterRef('student_application__application__exam'),
                    question=OuterRef('question')
                ).values('pk')[:1]
            ),
            weight=Subquery(
                ExamQuestion.objects.filter(
                    exam=OuterRef('student_application__application__exam'),
                    question=OuterRef('question')
                ).values('weight')[:1]
            ),
            grade=F('teacher_grade'),
            category=Value('file'),
        ).values('id', 'exam_question', 'content', 'student_id', 'weight', 'grade', 'category')

        answers = option_answers.union(textual_answers).union(file_answers)
        return answers
