from django.urls import path

from fiscallizeon.omr import views
from fiscallizeon.omr.api import exam_template, omr_upload_task_status, omr_export_task_status, omr_upload
from fiscallizeon.omr.api.print_preview import OMRDiscursivePreviewApi

app_name = 'omr'

urlpatterns = [
	path('', views.omr_upload_list, name='omr_upload_list'),
	path('offset/listar/', views.OffsetSchoolUploadListView.as_view(), name='omr_upload_offset_schoolclass_list'),
	path('detalhes/<uuid:pk>/', views.omr_upload_detail, name='omr_upload_detail'),
	path('correcao/', views.OMRCorrectionListView.as_view(), name='omr_correction'),
	path('correcao/<uuid:pk>/', views.OMRCorrectionListView.as_view(), name='omr_correction_detail'),
	path('corrigir/<uuid:pk>/', views.omr_upload_fix, name='omr_upload_fix'),
	path('corrigir-discursivas/<uuid:pk>/', views.omr_discursive_upload_fix, name='omr_discursive_upload_fix'),
	path('imprimir_caderno_respostas_aluno/<uuid:pk>/', views.print_application_student_answer_sheet, name='print_application_student_answer_sheet'),
	path('imprimir_caderno_respostas_avulso/<uuid:pk>/', views.print_detached_answer_sheet, name='print_detached_answer_sheet'),
	path('imprimir_lista_presenca_aplicacao/<uuid:pk>/', views.print_application_attendance_list, name='print_application_attendance_list'),
	path('imprimir_caderno_respostas_avulso_elit/<uuid:pk>/', views.PrintELITAvulseAnswerSheet.as_view(), name='print_detached_elit_answer_sheet'),
	path('imprimir_caderno_respostas_offset/<uuid:pk>/', views.PrintOffsetAnswerSheetView.as_view(), name='print_offset_answer_sheet'),
	path('imprimir_caderno_respostas_offset_turma/<uuid:pk>/', views.PrintOffsetSchoolClassAnswerSheetView.as_view(), name='print_offset_answer_sheet_schoolclass'),
	path('imprimir_caderno_respostas_efai/<uuid:pk>/', views.PrintEfaiDetachedAnswerSheetView.as_view(), name='print_efai_answer_sheet'),

	path('exportar_modelo_reduzido/', views.export_answer_sheet_reduce_model, name='export_answer_sheet_reduce_model'),
	path(
        'imprimir_folha_redacao_aluno/<uuid:pk>/', 
        views.PrintApplicationStudentEssayAnswerSheet.as_view(),  
        name='export_application_student_essay_sheet'
	),
	path(
        'imprimir_folha_redacao_avulsa/<uuid:pk>/', 
        views.PrintDetachedEssayAnswerSheet.as_view(), 
        name='export_detached_essay_sheet'
    ),
	path(
		'exportar-caderno-respostas-avulso/<uuid:pk>/',
		views.export_answer_sheet_application_detached,
		name='export_answer_sheet_application_detached'
	),
	path(
		'exportar-caderno-respostas-discursivo-avulso/<uuid:pk>/',
		views.export_answer_sheet_discursive_detached,
		name='export_answer_sheet_discursive_detached'
	),
	path(
		'exportar-caderno-respostas-elit-avulso/<uuid:pk>/',
		views.ExportELITAnswerSheetDetachedView.as_view(),
		name='export_elit_answer_sheet_detached'
	),
	path(
		'exportar-folha-respostas-offset/',
		views.ExportOffsetAnswerSheetView.as_view(),
		name='export_offset_answer_sheet'
	),
	path('importar-folhas-respostas/', views.import_answer_sheets, name='import_answer_sheets'),
	path('reimportar-folhas-respostas/<uuid:pk>/', views.retry_import_answer_sheets, name='retry_import_answer_sheets'),
	path('importar-folhas-respostas-offset-schoolclass/', views.ImportOffsetSchoolClassAnswerSheetsView.as_view(), name='import_offset_schoolclass_answer_sheets'),

	path('api/importar-folhas-respostas/', views.api_import_answer_sheets, name='api_import_answer_sheets'),
	
	path('imprimir-caderno-discursivas/<uuid:pk>/', views.print_discursive_answer_sheet, name='print_discursive_answer_sheet'),
	path('imprimir-caderno-discursivas-avulso/<uuid:pk>/', views.print_detached_discursive_answer_sheet, name='print_detached_discursive_answer_sheet'),
	path('imprimir-caderno-discursivas-preview/<uuid:pk>/', views.print_preview_discursive_answer_sheet, name='print_preview_discursive_answer_sheet'),
	
	path('avulsos/', views.template_list, name='template_list'),
	path('cadastrar/gabarito/avulso/', views.template_create, name='template_create'),
	path('gabarito/<uuid:pk>/avulso/edit', views.template_update, name='template_update'),
	path('gabarito/<uuid:pk>/avulso/delete', views.template_delete, name='template_delete'),

	#API
	path('api/get_upload_omr_task_status/<uuid:pk>/', omr_upload_task_status.omr_upload_task_status, name='omr_upload_task_status'),
	path('api/omr_export_task_status/<uuid:pk>/<int:export_verion>/', omr_export_task_status.omr_export_task_status, name='omr_export_task_status'),
	path('api/omr_upload_details/<uuid:pk>/', omr_upload.omr_upload_status, name='omr_upload_status'),
	path('api/omr_students_upload/check/<uuid:pk>/', omr_upload.OmrStudentsUploadCheckUpdateAPIView.as_view(), name='omr_students_upload_check'),
	path('api/omr_students_upload/historical/<uuid:pk>/', omr_upload.OMRStudentsHistoricalRerieveAPIView.as_view(), name='omr_students_upload_historical'),
	path('api/omr_upload_details/get_student_page_error_count/<uuid:pk>/', omr_upload.OmrUploadStudentPageErrorCount.as_view(), name='omr_upload_student_page_error_count'),
	path('api/omr_discursive_print_preview/<uuid:exam_id>/', OMRDiscursivePreviewApi.as_view(), name='omr_discursive_print_preview'),
	path('api/omr_delete_error', omr_upload.OMRDeleteErrorApi.as_view(), name='omr_delete_error'),
  path('api/omr_soft_delete/<uuid:pk>/', omr_upload.OMRSoftDeleteAPi.as_view(), name='omr_soft_delete'),
  path('api/<uuid:pk>/omr_is_associated_file/', omr_upload.OMRAssociatedFileApi.as_view(), name='omr_is_associated_file'),

	path('api/exam_template/create/', exam_template.exam_template_create, name='exam_template_create'),
	path('api/exam_template/<uuid:pk>/update/', exam_template.exam_template_update, name='exam_template_update'),
	path('api/exam_template/<uuid:pk>/detail/', exam_template.exam_template_detail, name='exam_template_detail'),
	
	path('api/exam_template/<uuid:pk>/duplicate/', exam_template.exam_template_duplicate ,name= 'exam_template_duplicate'),

	path('api/v2/exam_template/create/', exam_template.exam_template_v2_create, name='exam_template_v2_create'),
	path('api/v2/exam_template/<uuid:pk>/update/', exam_template.exam_template_v2_update, name='exam_template_v2_update'),

	# API Personalizada apenas para a correção de uploads
	path('api/omr_upload_details/get_student_page_error_count_and_students/<uuid:pk>/', omr_upload.OmrUploadStudentPageErrorCountAndStudents.as_view(), name='omr_errors_and_students'),
	path('api/corrected/update/<uuid:pk>/', omr_upload.OMRUploadSimpleUpdateAPIView.as_view(), name='omr_upload_corrected'),


]