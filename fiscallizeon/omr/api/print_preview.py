import base64
import os
import uuid

from urllib.parse import urlencode

from django.conf import settings
from django.template.defaultfilters import slugify
from django.shortcuts import get_object_or_404, resolve_url as r

from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from PyPDF2 import PdfReader
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from fiscallizeon.clients.permissions import IsCoordinationMember
from fiscallizeon.core.print_service import print_to_file
from fiscallizeon.core.utils import CheckHasPermissionAPI
from fiscallizeon.exams.models import Exam
from fiscallizeon.exams.permissions import IsTeacherSubject


class OMRDiscursivePreviewApi(APIView):
    parser_classes = (CamelCaseJSONParser, )
    renderer_classes = (CamelCaseJSONRenderer, )
    permission_classes = (CheckHasPermissionAPI, IsCoordinationMember, IsTeacherSubject)
    required_permissions = [settings.TEACHER, settings.COORDINATION]
    authentication_classes = (SessionAuthentication,)

    class OutputSerializer(serializers.Serializer):
        url = serializers.CharField()
        total_pages = serializers.IntegerField()

    def get(self, request, exam_id):
        data = {
            'url': f'{settings.K8S_FISCALLIZE_SERVICE_URL}{r("omr:print_preview_discursive_answer_sheet", pk=exam_id)}',
            'filename': f'{exam_id}_discursive-omr.pdf',
            'blank_pages': '',
            'wait_seconds': True,
        }

        os.makedirs('tmp', exist_ok=True)
        tmp_file = os.path.join('tmp', str(uuid.uuid4()))
        print_to_file(tmp_file, data, local=True)

        encoded_string = ''
        with open(tmp_file, 'rb') as pdf_file:
            encoded_string = base64.b64encode(pdf_file.read())

        read_pdf = PdfReader(tmp_file)
        total_pages = len(read_pdf.pages)

        serializer = self.OutputSerializer(
            {
                'url': f'data:application/pdf;base64,{encoded_string.decode("utf-8")}',
                'total_pages': total_pages,
            }
        )

        return Response(serializer.data)