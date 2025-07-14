from django.urls import path
from .views import PrintClassApplicationAnswerSheetDetailView, PrintClassApplicationAttendanceListView, NPSApplicationListView, \
    OMRNPSUploadList, ImportOMRNPSSheetsView, OMRNPSUploadDetail, OMRNPSUploadFixView, OMRNPSUploadDeleteView
from .api.nps_application_export import ExportApplicationBagApiView, ExportNPSApplicationBagStatusApiView
from .api.nps_application import NPSApplicationApiListView, NPSApplicationRetrieve
from .api.omr_nps_upload import OMRNPSUploadStatusView, OMRNPSIngestTaskStatusView, OMRNPSUploadErrorsView
from .api.teacher_order import TeacherOrderListView
from .api.omr_nps_error import OMRNPSErrorDeleteView
from .api.teacher_answer import TeacherAnswerCreateUpdateView, TeacherAnswerDeleteView
from .api.unity_answer import UnityAnswerCreateUpdateView, UnityAnswerDeleteView
from .api.nps_application_results import ExportNPSApplicationResultsApiView, ExportNPSApplicationResultsStatusApiView, NPSApplicationExportResultsTaskStatusView

app_name = 'omrnps'

urlpatterns = [
    path('', NPSApplicationListView.as_view(), name="list"),
    path('avaliacao/professores/<uuid:pk>/', PrintClassApplicationAnswerSheetDetailView.as_view(), name="print-class-application"),
    path('avaliacao/lista-presenca/<uuid:pk>/', PrintClassApplicationAttendanceListView.as_view(), name="print-class-attendance-list"),
    path('uploads/', OMRNPSUploadList.as_view(), name="omrnps-list"),
    path('uploads/enviar/', ImportOMRNPSSheetsView.as_view(), name="upload-create"),
    path('uploads/detalhes/<uuid:pk>/', OMRNPSUploadDetail.as_view(), name="upload-details"),
    path('uploads/corrigir/<uuid:pk>/', OMRNPSUploadFixView.as_view(), name="upload-fix"),
    path('uploads/excluir/<uuid:pk>/', OMRNPSUploadDeleteView.as_view(), name="upload-delete"),
    #API
    path('api/nps_application_list/', NPSApplicationApiListView.as_view(), name="nps_application_list"),
    path('api/nps_application_detail/<uuid:pk>/', NPSApplicationRetrieve.as_view(), name="nps_application_detail"),
    path('api/export_application_bag/', ExportApplicationBagApiView.as_view(), name="export_application_bag"),
    path('api/export_application_bag_status/', ExportNPSApplicationBagStatusApiView.as_view(), name="export_application_bag_status"),
	path('api/omr_upload_details/<uuid:pk>/', OMRNPSUploadStatusView.as_view(), name='omr_upload_status'),
	path('api/omr_ingest_task_status/<uuid:pk>/', OMRNPSIngestTaskStatusView.as_view(), name='omr_ingest_task_status'),
	path('api/teacher_order_page_answers/<uuid:pk>/', TeacherOrderListView.as_view(), name='teacher_order_page_answers'),
	path('api/create_update_teacher_answer/', TeacherAnswerCreateUpdateView.as_view(), name='create_update_teacher_answer'),
	path('api/create_update_unity_answer/', UnityAnswerCreateUpdateView.as_view(), name='create_update_unity_answer'),
	path('api/delete_teacher_answer/<uuid:pk>/', TeacherAnswerDeleteView.as_view(), name='delete_teacher_answer'),
	path('api/delete_unity_answer/<uuid:pk>/', UnityAnswerDeleteView.as_view(), name='delete_unity_answer'),
	path('api/export_results/', ExportNPSApplicationResultsApiView.as_view(), name='export_results'),
	path('api/nps/applications/<uuid:export_id>/', NPSApplicationExportResultsTaskStatusView.as_view(), name='npsapplication_export_results'),
	path('api/export_results_status/', ExportNPSApplicationResultsStatusApiView.as_view(), name='export_results_status'),
	path('api/delete_omr_nps_error/<uuid:pk>/', OMRNPSErrorDeleteView.as_view(), name='delete_omr_nps_error'),
	path('api/omr_nps_upload_error/<uuid:pk>/', OMRNPSUploadErrorsView.as_view(), name='omr_nps_upload_error'),
]