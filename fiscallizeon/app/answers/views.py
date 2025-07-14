from rest_framework import generics, permissions, status
from rest_framework.response import Response

from fiscallizeon.accounts.models import User
from fiscallizeon.students.models import Student
from fiscallizeon.core.permissions import IsStudentUser, CanAccessApp
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.core.utils import SimpleAPIPagination 
from fiscallizeon.subjects.models import Subject
from fiscallizeon.answers.models import OptionAnswer, SumAnswer, TextualAnswer, FileAnswer

from django_filters.rest_framework import DjangoFilterBackend, BooleanFilter, FilterSet

from rest_framework import viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.decorators import action
from fiscallizeon.core.utils import CamelCaseAPIMixin

from .serializers import (
    CreateAnswerSerializer,
)

class AnswerViewSet(CamelCaseAPIMixin, viewsets.GenericViewSet):
    permission_classes = (permissions.IsAuthenticated, IsStudentUser, CanAccessApp)
    filter_backends = [DjangoFilterBackend]
    pagination_class = SimpleAPIPagination
    # filterset_fields = { 
    #     'application__date' : ['in', 'exact'],
    #     'application__category' : ['in', 'exact'],
    #     'application__exam__name' : ['icontains'],
    # }
    
    @action(detail=False, methods=["POST"], serializer_class=CreateAnswerSerializer)
    def create_answer(self, request, pk=None):
        """
            Cria as respostas do aluno
        """
        user = self.request.user
        student = user.student
        
        applications_student = student.applicationstudent_set.filter()
        
        return Response()