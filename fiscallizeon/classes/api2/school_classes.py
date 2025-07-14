from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView, ListCreateAPIView
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.classes.models import SchoolClass, Grade
from fiscallizeon.classes.serializers2.school_class import SchoolClassSimpleSerializer, SchoolClassStudentsSerializer, SchoolClassCreateSerializer
from fiscallizeon.classes.serializers2.grade import GradeSerializer
from fiscallizeon.core.paginations import LimitOffsetPagination
from fiscallizeon.core.utils import CheckHasPermissionAPI


@extend_schema(tags=['Turmas'])
class GradeListView(CheckHasPermissionAPI, ListAPIView):
    serializer_class = GradeSerializer
    pagination_class = LimitOffsetPagination
    required_scopes = ['read', 'write']
    search_fields = ['name']
    filterset_fields = ['level', ]

    def get_queryset(self):
        return Grade.objects.all()

@extend_schema(tags=['Turmas'],
               description="class_type: 0 - Turma regular | 1 - Turma de sondagem <br> \
                            turn: 0 - Manhã | 1 - Tarde | 2 - Noite | 3 - Integral    ",)
class SchoolClassListView(CheckHasPermissionAPI, ListCreateAPIView):
    serializer_class = SchoolClassSimpleSerializer
    pagination_class = LimitOffsetPagination
    required_scopes = ['read', 'write']
    search_fields = ['name']
    filterset_fields = ['coordination', 'school_year']
    

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SchoolClassCreateSerializer
        return SchoolClassSimpleSerializer

    def get_queryset(self):
        return SchoolClass.objects.filter(
            coordination__in=self.request.user.get_coordinations()
        )

@extend_schema(tags=['Turmas'])
class SchoolClassDetailView(CheckHasPermissionAPI, RetrieveAPIView):
    serializer_class = SchoolClassStudentsSerializer
    required_scopes = ['read', 'write']

    def get_queryset(self):
        return SchoolClass.objects.filter(
            coordination__in=self.request.user.get_coordinations()
        )