from django.urls import path

from fiscallizeon.exports import views
from fiscallizeon.exports import api
from fiscallizeon.exports.api.importation import ImportationErrorsAPIView
from fiscallizeon.omrnps.api.nps_application_results import NPSApplicationExportResultsTaskStatusView

app_name = 'exports'

urlpatterns = [
	path('prova/<uuid:pk>', views.exam_export, name='exam_export'),
	path('prova/<uuid:pk>/erp', views.exam_export_report, name='exam_export_report'),
	path('prova/<uuid:pk>/respostas', views.exam_export_report_answers, name='exam_export_report_answers'),
	path('prova/<uuid:pk>/acertos-erros', views.ExamExportSimpleReportView.as_view(), name='exam_export_simple_report'),
	path('prova/<uuid:pk>/competencias', views.ExamExporCorrectionsReportView.as_view(), name='exam_export_corrections'),
	path('provas/erp', views.exams_export_erp, name='exams_export_erp'),
	path('provas/respostas', views.exams_export_answers, name='exams_export_answers'),
	path('provas/acertos-erros', views.ExamsSimpleExportView.as_view(), name='exams_export_simple_report'),
	path('provas/redacao/<uuid:pk>/', views.ExamExportEssayDetailView.as_view(), name='exams_export_essay'),
	
	# NPS application
	path('gabaritos/nps/', views.NPSApplicationExport.as_view(), name='nps_applications_export'),
 
	#API
	path('api/export_exams_status/<uuid:export_id>', api.exams_export_results, name='exams_export_results'),
	path('api/list_exam_results/<uuid:exam_id>', api.list_exam_results, name='list_exam_results'),
    path('api/get/errors/<uuid:pk>/', ImportationErrorsAPIView.as_view(), name='get-importation-errors')
]