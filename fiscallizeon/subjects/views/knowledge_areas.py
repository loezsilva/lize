from fiscallizeon.classes.models import Grade
from rest_framework import viewsets
from rest_framework.generics import ListAPIView

from fiscallizeon.subjects.serializers.knowledge_areas import KnowledgeAreaSerializer, KnowledgeAreaSimpleSerializer
from fiscallizeon.subjects.models import KnowledgeArea, Subject
from django.db.models import Exists, OuterRef

class KnowledgeAreaViewSet(viewsets.ModelViewSet):
	serializer_class = KnowledgeAreaSerializer
	queryset = KnowledgeArea.objects.all()
	# search_fields = ()
	# filterset_fields = ()


class KnowledgeAreaListView(ListAPIView):
    serializer_class = KnowledgeAreaSimpleSerializer
    queryset = KnowledgeArea.objects.all()
    filterset_fields = ['id', 'grades', ]


class KnowledgeAreaWithLanguageSubjectsAPIView(ListAPIView):
    serializer_class = KnowledgeAreaSerializer 
    filterset_fields = ['id', 'grades', ]

    def get_queryset(self):
        queryset = KnowledgeArea.objects.filter(subject__is_foreign_language_subject=True).distinct()

        return queryset
    
    
knowledge_area_list_api = KnowledgeAreaListView.as_view()
knowledge_area_with_language_subject_list_api = KnowledgeAreaWithLanguageSubjectsAPIView.as_view()