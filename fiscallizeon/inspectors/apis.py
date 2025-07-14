from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fiscallizeon.core.api import CsrfExemptSessionAuthentication


class TeacherSuperProfDataApi(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)

    class InputSerializer(serializers.Serializer):
        superpro_data = serializers.JSONField()

    class OutputSerializer(serializers.Serializer):
        already_integrated_with_superpro = serializers.BooleanField()
        superpro_data = serializers.JSONField()

    def get(self, request):
        data = self.OutputSerializer(request.user.inspector).data

        return Response(data)

    def patch(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request.user.inspector.already_integrated_with_superpro = True
        request.user.inspector.superpro_data = serializer.validated_data['superpro_data']
        request.user.inspector.save()

        data = self.OutputSerializer(request.user.inspector).data

        return Response(data)
