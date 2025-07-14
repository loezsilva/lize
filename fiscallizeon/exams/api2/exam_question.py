from django.db.models import Subquery, F, Case, When, Value, CharField, OuterRef
from django.db.models.functions import Coalesce

from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from fiscallizeon.core.paginations import LimitOffsetPagination

from ..models import ExamQuestion, StatusQuestion
from ..serializers2.exam_question import ExamQuestionSerializer


@extend_schema(tags=['Questões dos cadernos'])
class ExamQuestionListView(ListAPIView):
    serializer_class = ExamQuestionSerializer
    pagination_class = LimitOffsetPagination
    required_scopes = ['read', 'write']
    filterset_fields = ('exam', )

    def get_queryset(self):
        queryset = ExamQuestion.objects.filter(
            exam__coordinations__unity__client__in=self.request.user.get_clients_cache(),
        ).annotate(
            request_id=F('exam_teacher_subject_id'),
            status=Coalesce(
                Subquery(
                    StatusQuestion.objects.filter(
                        exam_question=OuterRef('pk')
                    ).order_by('-created_at').values('status')[:1]
                ), 2),
            status_description=Case(
                When(status=0, then=Value('Aprovada')),
                When(status=1, then=Value('Reprovada')),
                When(status=3, then=Value('Aguardando correção')),
                When(status=4, then=Value('Corrigido')),
                When(status=5, then=Value('Visto')),
                default=Value('Em aberto')
            )
        ).values().distinct()

        return queryset
