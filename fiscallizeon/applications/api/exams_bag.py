from rest_framework import status 
from rest_framework.views import APIView
from rest_framework.response import Response
from djangorestframework_camel_case.util import underscoreize

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin

from fiscallizeon.applications.models import Application
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.omr.tasks import export_answer_sheet
from fiscallizeon.omr.tasks.elit.export_answer_sheets import export_answer_sheets


class ExportApplicationExamsBagAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    required_permissions = ['coordination']
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def post(self, request, *args, **kwargs):
        application = get_object_or_404(Application, pk=self.kwargs.get('pk'))
        
        if not application.exam.can_print:
            return Response("O caderno não pode ser impresso, por que existe um malote associado, ou o caderno foi marcado como já impresso.", status=status.HTTP_401_UNAUTHORIZED)
        
        application.last_answer_sheet_generation = timezone.localtime(timezone.now())
        application.sheet_exporting_status = Application.EXPORTING
        application.sheet_exporting_count += 1
        application.save()

        sheet_model = request.data.get('sheet_model', None)
        blank_pages = request.data.get('blank_pages', False)
        include_discursives = request.data.get('include_discursives', False)
        include_exams = request.data.get('include_exams', False)
        raw_exam_params = request.data.get('exam_params', {})
        discursive_params = underscoreize(request.data.get('discursive_params', {}))
        custom_pages = raw_exam_params.get('customPages', [])
        task_id=f'EXPORT_SHEETS_{application.pk}_{application.sheet_exporting_count}'

        if application.exam and application.exam.is_abstract:
            include_exams = False

        if sheet_model == 'subjects' and not application.exam.is_subject_sheet_allowed:
            return Response('Modelo de gabarito EFAI não pode ser utilizado para este caderno!', status=status.HTTP_401_UNAUTHORIZED)

        if sheet_model == 'reduced' and not application.exam.is_reduced_allowed_max_questions:
            return Response('Modelo de gabarito reduzido não pode ser utilizado para este caderno!', status=status.HTTP_401_UNAUTHORIZED)

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
        }
        
        export_answer_sheet.apply_async(
            kwargs={
                "application_pk": str(application.pk),
                "blank_pages": blank_pages,
                "sheet_model": sheet_model,
                "export_version": application.sheet_exporting_count,
                "include_discursives": include_discursives,
                "include_exams": include_exams,
                "exam_params": exam_params,
                "custom_pages_pks": custom_pages,
                "discursive_params": discursive_params,
            },
            task_id=task_id,
        )

        return Response(
            status=status.HTTP_200_OK,
            data={'task_id': task_id},
        )

class RemoveApplicationExamBagAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    required_permissions = ['coordination']
    authentication_classes = (CsrfExemptSessionAuthentication, )
    permission_required = 'applications.can_remove_generated_bag'

    def post(self, request, *args, **kwargs):
        application = get_object_or_404(Application, pk=self.kwargs.get("pk"))
        application.answer_sheet = None
        application.save()

        return Response(f"Malote removido para aplicação {application.exam}", status=status.HTTP_200_OK)
    
class ExportApplicationELITExamsBagAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    required_permissions = ['coordination']
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def post(self, request, *args, **kwargs):
        application = get_object_or_404(Application, pk=self.kwargs.get('pk'))
        application.last_answer_sheet_generation = timezone.localtime(timezone.now())
        application.sheet_exporting_status = Application.EXPORTING
        application.sheet_exporting_count += 1
        application.save()

        task_id=f'EXPORT_SHEETS_{application.pk}_{application.sheet_exporting_count}'

        export_answer_sheets.apply_async(
            kwargs={
                'application_pk': str(application.pk),
                'export_version': application.sheet_exporting_count,
            },
            task_id=task_id,
        )

        return Response(
            status=status.HTTP_200_OK,
            data={'task_id': task_id},
        )
    


    
export_application_exams_bag = ExportApplicationExamsBagAPIView.as_view()
export_application_elit_exams_bag = ExportApplicationELITExamsBagAPIView.as_view()
remove_application_exam_bag = RemoveApplicationExamBagAPIView.as_view()