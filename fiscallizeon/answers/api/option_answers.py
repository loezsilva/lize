from django.conf import settings

from rest_framework import generics, permissions
from rest_framework.authentication import BasicAuthentication 
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

from fiscallizeon.answers.serializers.option_answers import OptionAnswerSerializer, OptionAnswerWithoutAnswerSerializer
from fiscallizeon.answers.models import OptionAnswer
from fiscallizeon.answers.permissions import IsOwner

from fiscallizeon.core.utils import CheckHasPermissionAPI

class OptionAnswerCreateView(generics.CreateAPIView):
    model = OptionAnswer
    serializer_class = OptionAnswerWithoutAnswerSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )
    permission_classes = [IsOwner]

class OptionAnswerRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    model = OptionAnswer
    serializer_class = OptionAnswerWithoutAnswerSerializer
    queryset = OptionAnswer.objects.all()
    permission_classes = [permissions.IsAdminUser, IsOwner]


class OptionAnswerCoordinationCreateView(CheckHasPermissionAPI, generics.CreateAPIView):
    model = OptionAnswer
    serializer_class = OptionAnswerSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )
    permission_classes = [IsOwner]
    required_permissions = [settings.TEACHER, settings.COORDINATION]


class OptionAnswerRetrieveCoordinationUpdateView(CheckHasPermissionAPI, generics.RetrieveUpdateAPIView):
    model = OptionAnswer
    serializer_class = OptionAnswerSerializer
    queryset = OptionAnswer.objects.all()
    permission_classes = [permissions.IsAdminUser, IsOwner]
    required_permissions = [settings.TEACHER, settings.COORDINATION]


class OptionAnswerDeleteAnswerDeleteAPIView(CheckHasPermissionAPI, generics.DestroyAPIView):
    queryset = OptionAnswer.objects.all()
    authentication_classes = (CsrfExemptSessionAuthentication, )