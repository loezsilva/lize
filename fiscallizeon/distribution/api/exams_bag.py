from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from celery.result import AsyncResult
from celery import states

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404

from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.core.templatetags.cdn_url import cdn_url
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.distribution.models import RoomDistribution
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.distribution.tasks.export_exams_bag import export_exams_bag
from fiscallizeon.distribution.tasks.export_application_students_bag import export_application_students_bag

class ExportDistributionExamsBagAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    required_permissions = ['coordination']
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def post(self, request, *args, **kwargs):
        room_distribution = get_object_or_404(RoomDistribution, pk=kwargs['pk'])
        
        if not room_distribution.can_print:
            return Response("O caderno não pode ser impresso, por que existe um malote associado, ou o caderno foi marcado como já impresso.", status=status.HTTP_401_UNAUTHORIZED)
            
        task_id = f'EXPORT_DISTRIBUTION_EXAMS_BAG_{room_distribution.pk}_{room_distribution.exams_bag_generation_count}'
        room_distribution.exams_bag_generation_count += 1
        room_distribution.status = RoomDistribution.EXPORTING
        room_distribution.save()

        raw_exam_params = request.data.get('exam_params', {})
        sheet_model = request.data.get('sheet_model', None)
        include_discursives = request.data.get('include_discursives', False)
        discursive_params = request.data.get('discursive_params', {})
        include_exams = request.data.get('include_exams', False)
        blank_pages = request.data.get('blank_pages', False)
        custom_pages_pks = raw_exam_params.get('customPages', [])

        economy_mode = int(raw_exam_params.get('economyMode', 0))

        exam_params = {
            'two_columns': 1 if economy_mode else raw_exam_params.get('columnType', 0),
            'separate_subjects': raw_exam_params.get('kind', 0),
            'line_textual': raw_exam_params.get('textQuestionFormat', 0),
            'text_question_format': int(raw_exam_params.get('textQuestionFormat', 1)),
            'line_spacing': raw_exam_params.get('lineHeight', 0),
            'font_family': raw_exam_params.get('fontFamily', 0),
            'header': raw_exam_params.get('header', 0),
            'header_full': raw_exam_params.get('headerFormat', 0),
            'font_size': raw_exam_params.get('fontSize', 0),
            'hide_discipline_name': 0 if int(raw_exam_params.get('printSubjectsName', 0)) else 1,
            'hide_knowledge_area_name': int(raw_exam_params.get('hideKnowledgeAreasName', 0)),
            'hide_questions_referencies': int(raw_exam_params.get('hideQuestionsReferencies', 0)),
            'print_images_with_grayscale': int(raw_exam_params.get('printBlackAndWhiteImages', 0)),
            'hyphenate_text': int(raw_exam_params.get('hyphenate', 0)),
            'discursive_line_height': raw_exam_params.get('discursiveLineHeight', 0),
            'show_question_board': raw_exam_params.get('showQuestionBoard', 0),
            'show_question_score': int(raw_exam_params.get('showQuestionScore', 0)),
            'hide_dialog': 1,
            'margin_top': float(raw_exam_params.get('marginTop', 0.6)),
            'margin_bottom': float(raw_exam_params.get('marginBottom', 0.6)),
            'margin_right': float(raw_exam_params.get('marginRight', 0)),
            'margin_left': float(raw_exam_params.get('marginLeft', 0)),
            'uppercase_letters': int(raw_exam_params.get('uppercaseLetters', 0)),
            'show_footer': int(raw_exam_params.get('showFooter', 0)),
            'add_page_number': int(raw_exam_params.get('addPageNumber', 0)),
            'economy_mode': economy_mode,
            'force_choices_with_statement': int(raw_exam_params.get('forceChoicesWithStatement', 0)),
            'hide_numbering': int(raw_exam_params.get('hideNumbering', 0)),
            'break_enunciation': 1 if economy_mode else int(raw_exam_params.get('breakEnunciation', 0)),
            'discursive_question_space_type': int(raw_exam_params.get('discursiveQuestionSpaceType', 0)),
            'language': int(raw_exam_params.get('language', 0)),
            'break_alternatives': 1 if economy_mode else int(raw_exam_params.get('breakAlternatives', 0)),
            'break_all_questions': int(raw_exam_params.get('breakAllQuestions', 0)),
            'use_custom_params': int(raw_exam_params.get('useCustomParams', 0)),
        }

        export_exams_bag.apply_async(
            kwargs={
                'room_distribution_pk': room_distribution.pk,
                'include_exams': include_exams,
                'sheet_model': sheet_model,
                'blank_pages': blank_pages,
                'exam_params': exam_params,
                'export_version': room_distribution.exams_bag_generation_count,
                'include_discursives': include_discursives,
                'discursive_params': discursive_params,
                'custom_pages_pks': custom_pages_pks,
            },
            task_id=task_id,
        )

        return Response(
            status=status.HTTP_200_OK,
            data={'task_id': task_id},
        )


class ExportApplicationStudentsExamsBagAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    required_permissions = ['coordination']
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def post(self, request, *args, **kwargs):
        room_distribution = get_object_or_404(RoomDistribution, pk=kwargs['pk'])
        students = request.data.get('students', [])
        print_params = request.data.get('print_params', {})

        application_students = ApplicationStudent.objects.filter(
            student__in=students,
            application__in=room_distribution.application_set.all(),
        ).distinct()
        application_students_pks = list(application_students.values_list('pk', flat=True))

        result = export_application_students_bag.apply_async(
            args=[application_students_pks, print_params],
        )

        return Response(status=status.HTTP_200_OK, data=result.get())


class GetDistributionExamsBagExportStatusAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    required_permissions = ['coordination']
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get(self, request, *args, **kwargs):
        room_distribution = get_object_or_404(RoomDistribution, pk=kwargs['pk'])
        task_id = f'EXPORT_DISTRIBUTION_EXAMS_BAG_{room_distribution.pk}_{room_distribution.exams_bag_generation_count-1}'
        result = AsyncResult(task_id)

        percent = 0
        if result.children:
            total_tasks = len(list(result.children[0]))
            pending_tasks = len(list(filter(lambda x: x.status == states.PENDING, list(result.children[0]))))
            percent = (total_tasks - pending_tasks) / total_tasks

        task_status = states.PENDING
        if room_distribution.status == RoomDistribution.EXPORTING:
            task_status = states.STARTED
        elif room_distribution.status == RoomDistribution.EXPORTED:
            task_status = states.SUCCESS
            result.forget()

        return Response(
            status=status.HTTP_200_OK,
            data={
                'task_status': task_status,
                'percent': percent,
                'file_link': cdn_url(room_distribution.exams_bag.url) if task_status == states.SUCCESS else None,
            },
        )


export_distribution_exams_bag = ExportDistributionExamsBagAPIView.as_view()
export_application_students_bag_view = ExportApplicationStudentsExamsBagAPIView.as_view()
get_export_distribution_exams_bag_status = GetDistributionExamsBagExportStatusAPIView.as_view()