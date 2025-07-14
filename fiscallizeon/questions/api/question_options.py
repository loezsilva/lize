from rest_framework import viewsets

from fiscallizeon.questions.serializers.question_options import QuestionOptionSerializer
from fiscallizeon.questions.models import QuestionOption

class QuestionOptionViewSet(viewsets.ModelViewSet):
	serializer_class = QuestionOptionSerializer
	queryset = QuestionOption.objects.all()
	# search_fields = ()
	# filterset_fields = ()