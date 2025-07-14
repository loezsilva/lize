from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone

from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.core.utils import SimpleAPIPagination

from ...models import Tutorial, TutorialCategory, TutorialFeedback
from ..serializers.tutoriais import TutorialSerializer, TutorialCategorySerializer, TutorialFeedbackSerializer


class TutorialsViewSet(LoginRequiredMixin, viewsets.ModelViewSet):
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    serializer_class = TutorialSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    queryset = Tutorial.objects.filter(status=Tutorial.PUBLISHED).order_by('-created_at')
    pagination_class = SimpleAPIPagination
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['title']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        user = self.request.user
        queryset = queryset.filter(
            Q(
                Q(segments__isnull=True) | Q(segments__len__lte=0) | Q(segments__contains=[user.user_type])
            ) 
        )
        if self.request.GET.get('category'):
            queryset = queryset.filter(categories=self.request.GET.get('category'))
    
        return queryset
    
    @action(detail=False, methods=["GET"], serializer_class=TutorialCategorySerializer)
    def categories(self, request, pk=None):
        user = self.request.user
        
        categories = TutorialCategory.objects.filter(
            Q(tutorial__status=Tutorial.PUBLISHED),
            Q(
                Q(tutorial__segments__isnull=True) |
                Q(tutorial__segments__len__lte=0) |
                Q(tutorial__segments__contains=[user.user_type])
            )
        ).order_by('name').distinct()
        
        return Response(self.get_serializer(instance=categories, many=True).data)

    @action(detail=True)
    def feedback(self, request, pk=None):
        tutorial = self.get_object()
        try:
            tutorial_feedback = TutorialFeedback.objects.get(
                tutorial=tutorial, user=request.user, date=timezone.now().date()
            )
            serializer = TutorialFeedbackSerializer(tutorial_feedback)
            return Response(serializer.data)
        except TutorialFeedback.DoesNotExist:
            return Response(status=status.HTTP_204_NO_CONTENT)

    @feedback.mapping.post
    def feedback_post(self, request, pk=None):
        tutorial = self.get_object()
        now = timezone.now()
        try:
            tutorial_feedback = TutorialFeedback.objects.create(
                tutorial=tutorial, user=request.user, date=now.date(), value=request.data['value']
            )
        except IntegrityError as e:
            if e.args[0].startswith('duplicate key value violates unique constraint'):
                tutorial_feedback = TutorialFeedback.objects.get(
                    tutorial=tutorial, user=request.user, date=now.date()
                )
                tutorial_feedback.value = request.data['value']
                tutorial_feedback.save()

        return Response(TutorialFeedbackSerializer(tutorial_feedback).data, status=status.HTTP_200_OK)
