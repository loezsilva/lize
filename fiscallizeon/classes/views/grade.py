
from rest_framework.generics import ListAPIView
from fiscallizeon.classes.serializers import GradeSerializer
from fiscallizeon.classes.models import Grade

class GradeListView(ListAPIView):
    serializer_class = GradeSerializer
    queryset = Grade.objects.all().order_by('name')
    required_scopes = ['read', 'write']
    filterset_fields = ['level', ]

grade_list_api = GradeListView.as_view()