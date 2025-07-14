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
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from fiscallizeon.clients.models import ExamPrintConfig
from fiscallizeon.clients.permissions import IsCoordinationMember
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.core.print_service import print_to_file
from fiscallizeon.core.utils import CheckHasPermissionAPI
from fiscallizeon.exams.models import ExamHeader, ClientCustomPage, ExamBackgroundImage
from fiscallizeon.questions.models import Question
from django.template.defaultfilters import truncatechars

from .models import Exam, ExamTeacherSubjectFile
from .permissions import IsTeacherSubject
from .serializers.exams import ExamTeacherSubjectFileUploadSerializer
from django.contrib.auth.mixins import PermissionRequiredMixin


class ExamPdfPreviewApi(APIView):
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    permission_classes = (CheckHasPermissionAPI, IsCoordinationMember, IsTeacherSubject)
    required_permissions = [settings.TEACHER, settings.COORDINATION]
    authentication_classes = (SessionAuthentication,)

    class OutputSerializer(serializers.Serializer):
        url = serializers.CharField()
        total_pages = serializers.IntegerField()

    def get(self, request, exam_id):
        exam = get_object_or_404(Exam.objects.using('default').all(), pk=exam_id)
        exam.clear_questions_numbers_cache()

        blank_pages = False
        data = {
            'url': f'{settings.K8S_FISCALLIZE_SERVICE_URL}{r("exams:exam_print", pk=exam_id)}?{urlencode(exam.get_filters_to_print())}&pass_check_can_print=true',
            # 'url': f'http://fiscallize-service{r("exams:exam_print", pk=exam_id)}?{urlencode(exam.get_filters_to_print())}',
            'filename': f'{slugify(str(exam.name))}-{exam_id}.pdf',
            'blank_pages': 'odd' if blank_pages else '',
            'wait_seconds': True,
            'check_loaded_element': True,
        }

        if exam.get_filters_to_print().get('show_footer'):
            data['footer_text'] = truncatechars(exam.name, 100)

        if exam.get_filters_to_print().get('add_page_number') and exam.get_filters_to_print().get('separate_subjects') == 0:
            data['add_page_number'] = True

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
class ClientCustomPagePreviewApi(APIView):
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    # permission_classes = (CheckHasPermissionAPI, IsCoordinationMember, IsTeacherSubject)
    # required_permissions = [settings.TEACHER, settings.COORDINATION]
    # authentication_classes = (SessionAuthentication,)

    class OutputSerializer(serializers.Serializer):
        url = serializers.CharField()

    def get(self, request, custom_page_id):
        data = {
            'url': f'{settings.K8S_FISCALLIZE_SERVICE_URL}{r("exams:custom-pages-print")}?custom_page={custom_page_id}',
            'filename': f'{custom_page_id}.pdf'
        }

        os.makedirs('tmp', exist_ok=True)
        tmp_file = os.path.join('tmp', str(uuid.uuid4()))
        print_to_file(tmp_file, data, local=True)

        encoded_string = ''
        with open(tmp_file, 'rb') as pdf_file:
            encoded_string = base64.b64encode(pdf_file.read())

        serializer = self.OutputSerializer(
            {
                'url': f'data:application/pdf;base64,{encoded_string.decode("utf-8")}',
            }
        )

        return Response(serializer.data)


class ExamPrintConfigUpdateApi(APIView):
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    permission_classes = (CheckHasPermissionAPI, IsCoordinationMember, IsTeacherSubject)
    required_permissions = [settings.INSPECTOR, settings.TEACHER, settings.COORDINATION]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    class BaseSerializer(serializers.Serializer):
        header = serializers.PrimaryKeyRelatedField(
            queryset=ExamHeader.objects.all(), allow_null=True
        )
        background_image = serializers.PrimaryKeyRelatedField(
            queryset=ExamBackgroundImage.objects.all(), allow_null=True
        )
        header_format = serializers.IntegerField()
        column_type = serializers.IntegerField()
        kind = serializers.IntegerField()
        text_question_format = serializers.IntegerField()
        line_height = serializers.IntegerField()
        font_size = serializers.IntegerField()
        font_family = serializers.IntegerField()
        print_subjects_name = serializers.BooleanField()
        print_with_correct_answers = serializers.BooleanField()
        hide_alternatives_indicator = serializers.BooleanField()
        hide_knowledge_areas_name = serializers.BooleanField()
        hide_questions_referencies = serializers.BooleanField()
        print_black_and_white_images = serializers.BooleanField()
        hyphenate = serializers.BooleanField()
        discursive_line_height = serializers.FloatField()
        show_question_score = serializers.BooleanField()
        show_question_board = serializers.BooleanField()
        margin_top = serializers.FloatField()
        margin_bottom = serializers.FloatField()
        margin_right = serializers.FloatField()
        margin_left = serializers.FloatField()
        uppercase_letters = serializers.BooleanField()
        show_footer = serializers.BooleanField()
        add_page_number = serializers.BooleanField()
        economy_mode = serializers.BooleanField()
        force_choices_with_statement = serializers.BooleanField()
        hide_numbering = serializers.BooleanField()
        break_enunciation = serializers.BooleanField()
        break_all_questions = serializers.BooleanField()
        discursive_question_space_type = serializers.IntegerField()
        language = serializers.IntegerField()
        break_alternatives = serializers.BooleanField()


    class InputSerializer(BaseSerializer):
        def update(self, instance, validated_data):
            instance.header = validated_data.get('header', instance.header)
            instance.background_image = validated_data.get('background_image', instance.background_image)
            instance.header_format = validated_data.get(
                'header_format', instance.header_format
            )
            instance.column_type = validated_data.get(
                'column_type', instance.column_type
            )
            instance.kind = validated_data.get('kind', instance.kind)
            instance.text_question_format = validated_data.get(
                'text_question_format', instance.text_question_format
            )
            instance.line_height = validated_data.get(
                'line_height', instance.line_height
            )
            instance.font_size = validated_data.get('font_size', instance.font_size)
            
            instance.font_family = validated_data.get('font_family', instance.font_family)
            
            instance.hide_questions_referencies = validated_data.get('hide_questions_referencies', instance.hide_questions_referencies)
            
            instance.discursive_line_height = validated_data.get('discursive_line_height', instance.discursive_line_height)
            
            instance.print_subjects_name = validated_data.get(
                'print_subjects_name', instance.print_subjects_name
            )
            instance.print_with_correct_answers = validated_data.get(
                'print_with_correct_answers', instance.print_with_correct_answers
            )
            instance.hide_alternatives_indicator = validated_data.get(
                'hide_alternatives_indicator', instance.hide_alternatives_indicator
            )
            instance.hide_knowledge_areas_name = validated_data.get(
                'hide_knowledge_areas_name', instance.hide_knowledge_areas_name
            )
            instance.print_black_and_white_images = validated_data.get(
                'print_black_and_white_images', instance.print_black_and_white_images
            )
            instance.uppercase_letters = validated_data.get(
                'uppercase_letters', instance.uppercase_letters
            )

            instance.hyphenate = validated_data.get('hyphenate', instance.hyphenate)
            instance.show_question_score = validated_data.get('show_question_score', instance.show_question_score)
            instance.show_question_board = validated_data.get('show_question_board', instance.show_question_board)
            instance.margin_top = validated_data.get('margin_top', instance.margin_top)
            instance.margin_bottom = validated_data.get('margin_bottom', instance.margin_bottom)
            instance.margin_right = validated_data.get('margin_right', instance.margin_right)
            instance.margin_left = validated_data.get('margin_left', instance.margin_left)
            instance.show_footer = validated_data.get('show_footer', instance.show_footer)
            instance.add_page_number = validated_data.get('add_page_number', instance.add_page_number)
            instance.economy_mode = validated_data.get('economy_mode', instance.economy_mode)
            instance.force_choices_with_statement = validated_data.get('force_choices_with_statement', instance.force_choices_with_statement)
            instance.hide_numbering = validated_data.get('hide_numbering', instance.hide_numbering)
            instance.break_enunciation = validated_data.get('break_enunciation', instance.break_enunciation)
            instance.break_all_questions = validated_data.get('break_all_questions', instance.break_all_questions)
            instance.discursive_question_space_type = validated_data.get('discursive_question_space_type', instance.discursive_question_space_type)
            instance.language = validated_data.get('language', instance.language)
            instance.break_alternatives = validated_data.get('break_alternatives', instance.break_alternatives)
            instance.save()
            return instance

    class OutputSerializer(serializers.Serializer):
        pk = serializers.CharField()

    def patch(self, request, exam_id):
        exam = get_object_or_404(Exam.objects.all(), pk=exam_id)

        serializer = self.InputSerializer(
            exam.exam_print_config, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        exam_print_config = serializer.save()

        return Response(self.OutputSerializer(exam_print_config).data)
    
class ExamQuestionPrintConfigUpdateApi(APIView):
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    permission_classes = (CheckHasPermissionAPI, IsCoordinationMember, IsTeacherSubject)
    required_permissions = [settings.INSPECTOR, settings.TEACHER, settings.COORDINATION]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    class BaseSerializer(serializers.Serializer):
        SUPPORT_CONTENT_POSITION_CHOICES = [
            ('center', 'Centralizado'),
            ('left', 'À Esquerda'),
            ('right', 'À Direita'),
        ]

        print_only_enunciation = serializers.BooleanField()
        break_enunciation = serializers.BooleanField()
        break_alternatives = serializers.BooleanField()
        force_one_column = serializers.BooleanField()
        quantity_lines = serializers.IntegerField()
        draft_rows_number = serializers.IntegerField()
        text_question_format = serializers.IntegerField()
        force_break_page = serializers.BooleanField()
        number_is_hidden = serializers.BooleanField()
        support_content_position = serializers.ChoiceField(
            choices=SUPPORT_CONTENT_POSITION_CHOICES,
        )
        force_choices_with_statement = serializers.BooleanField()
        
    class InputSerializer(BaseSerializer):
        def update(self, instance, validated_data):
            
            instance.print_only_enunciation = validated_data.get(
                'print_only_enunciation', instance.print_only_enunciation
            )
            instance.break_enunciation = validated_data.get(
                'break_enunciation', instance.break_enunciation
            )
            instance.break_alternatives = validated_data.get(
                'break_alternatives', instance.break_alternatives
            )
            instance.force_one_column = validated_data.get(
                'force_one_column', instance.force_one_column
            )
            instance.quantity_lines = validated_data.get(
                'quantity_lines', instance.quantity_lines
            )
            instance.draft_rows_number = validated_data.get(
                'draft_rows_number', instance.draft_rows_number
            )
            instance.text_question_format = validated_data.get(
                'text_question_format', instance.text_question_format
            )
            instance.force_break_page = validated_data.get(
                'force_break_page', instance.force_break_page
            )
            instance.number_is_hidden = validated_data.get(
                'number_is_hidden', instance.number_is_hidden
            )
            instance.support_content_position = validated_data.get(
                'support_content_position', instance.support_content_position
            )
            instance.force_choices_with_statement = validated_data.get(
                'force_choices_with_statement', instance.force_choices_with_statement
            )

            instance.save()
            
            return instance

    class OutputSerializer(serializers.Serializer):
        pk = serializers.CharField()

    def patch(self, request, exam_id, question_id):
        question = get_object_or_404(Question.objects.all(), pk=question_id)

        serializer = self.InputSerializer(question, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        question = serializer.save()

        return Response(self.OutputSerializer(question).data)


class ExamTeacherSubjectFileUpload(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def post(self, request, format=None):
        serializer = ExamTeacherSubjectFileUploadSerializer(
            data=request.data, context={'request': request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data)


class ExamUpdateStatusApi(PermissionRequiredMixin, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_required = 'exams.can_change_status_exam'

    class InputSerializer(serializers.Serializer):
        status = serializers.IntegerField()

        def update(self, instance, validated_data):                         
            if 'status' not in validated_data:
                raise serializers.ValidationError("The 'status' field is required.")

            instance.status = validated_data.get('status', instance.status)
            instance.save()
            return instance

    class OutputSerializer(serializers.Serializer):
        status = serializers.IntegerField()
        status_display = serializers.CharField(source='get_status_display')

    def get(self, request, exam_id):
        exam = get_object_or_404(Exam.objects.using('default').all(), pk=exam_id)
        return Response(self.OutputSerializer(exam).data)

    def patch(self, request, exam_id):
        exam = get_object_or_404(Exam.objects.using('default').all(), pk=exam_id)
        print(request.data)
        serializer = self.InputSerializer(exam, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        exam = serializer.save()
        return Response(self.OutputSerializer(exam).data)
