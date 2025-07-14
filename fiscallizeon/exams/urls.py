from django.urls import path

from fiscallizeon.exams.views import wrongs as  wrongs_views
from fiscallizeon.exams.views import exams as exams_views
from fiscallizeon.exams.views import teachers as teachers_views
from fiscallizeon.exams.api import exams, exam_questions, export_attachments, wrongs, randomizations, \
    freemium, exams_teacher_subject_status, exam_copy_task_status, client_custom_page
from rest_framework.routers import DefaultRouter

app_name = 'exams'
router = DefaultRouter()
router.register(r'api/prova', exams.ExamCoordinationAndTeacherViewSet, basename='api-exam')
router.register(r'randomization', randomizations.RandomizationViewSet, basename='randomization')
router.register(r'examteachersubject', exams.ExamTeacherSubjectViewSet, basename='examteachersubject')
router.register(r'api/freemium', freemium.ExamFreemiumViewset, basename='freemium')

urlpatterns = [
	path('', exams_views.exams_list, name='exams_list'),
	path('v2/', exams_views.exams_list_v2, name='exams_list_v2'),
	path('revisar/', exams_views.exams_review, name='exams_review'),
	path('cadastrar/', exams_views.exams_create, name='exams_create'),
	path('<uuid:pk>/editar/', exams_views.exams_update, name='exams_update'),
    path('<uuid:pk>/revisar/', exams_views.exam_review, name='exam_review'),
	path('<uuid:pk>/remover/', exams_views.exams_delete, name='exams_delete'),
	path('<uuid:pk>', exams_views.exams_detail, name='exams_detail'),
	path('<uuid:pk>/v2/', exams_views.ExamDetailV2View.as_view(), name='exams_detail_v2'),
	path('<uuid:pk>/detalhes/', exams_views.ExamDetailNewView.as_view(), name='exams-detail-new'),
	path('importar/cadernos/', exams_views.ExamsImportTemplateView.as_view(), name='exams_import'),
	path('importar/cadernos/auxiliar/', exams_views.ExamsImportAuxiliaryTemplateView.as_view(), name='exams_import_auxiliary'),
	path('importar/solicitacoes/', exams_views.ExamsRequestImportTemplateView.as_view(), name='exams_request_import'),
	path('importar/solicitacoes/auxiliar/', exams_views.ExamsRequestImportAuxiliaryTemplateView.as_view(), name='exams_request_import_auxiliary'),
	path('importar/notas/redacao', exams_views.EssayGradeImportTemplateView.as_view(), name='essay_grade_import'),

	path('<uuid:pk>/detalhes/alunos/', exams_views.dash_exam_teacher_detail_students, name='dash_exam_teacher_detail_students'),
	path('<uuid:pk>/detalhes/geral/', exams_views.dash_exam_teacher_detail_general, name='dash_exam_teacher_detail_general'),
	path('<uuid:pk>/detalhes/questoes/', exams_views.dash_exam_teacher_detail_questions, name='dash_exam_teacher_detail_questions'),
	path('<uuid:pk>/detalhes/questoes/bncc/', exams_views.dash_exam_teacher_detail_bncc, name='dash_exam_teacher_detail_bncc'),
	
	path('<uuid:pk>/enunciados', exams_views.exams_detail_enunciation, name='exams_detail_enunciation'),
	path('<uuid:pk>/enunciados/v2/', exams_views.ExamDetailEnunciationV2View.as_view(), name='exams_detail_enunciation_v2'),
	path('<uuid:pk>/enunciados/detalhes/', exams_views.ExamDetailEnunciationNewView.as_view(), name='exams-detail-enunciation-new'),
	path('<uuid:pk>/visualizar', exams_views.exams_preview, name='exams_preview'),
	path('<uuid:pk>/visualizar/simples', exams_views.exams_preview_simple, name='exams_preview_simple'),
    
	path('desvios/', exams_views.DeviationsListView.as_view(), name='deviations_list'),
	path('desvios/criar/', exams_views.DeviationCreateView.as_view(), name='deviations_create'),
	path('desvios/<uuid:pk>/', exams_views.DeviationUpdateView.as_view(), name='deviations_update'),
	path('desvios/<uuid:pk>/deletar/', exams_views.DeviationDeleteView.as_view(), name='deviations_delete'),
	
	path('<uuid:pk>/redacoes/', exams_views.ExamEssayDetailView.as_view(), name='exams_detail_essay'),
	path('<uuid:pk>/redacoes/correcao/', exams_views.ExamAnswersCorrectionDetailView.as_view(), name='exam_answers_correction'),
 
	path('<uuid:pk>/visualizar/fiscal', exams_views.exams_inspector_preview, name='exams_inspector_preview'),
	path('<uuid:pk>/imprimir', exams_views.exam_print, name='exam_print'),
	path('<uuid:pk>/imprimir/servico-impressao/', exams_views.PrintExamWithPrintServiceDetailView.as_view(), name="print-exam-with-print-service"),
	path('<uuid:pk>/v2/imprimir/', exams_views.exam_print_v2, name='exam-print-v2'),
	path('<uuid:pk>/<uuid:application_student>/imprimir/lista-exercicio', exams_views.exam_homework_print, name='exam_homework_print'),
	path('<uuid:pk>/gabarito', exams_views.exam_template_print, name='exam_template_print'),
	path('<uuid:pk>/gabarito-randomizado', exams_views.ExamRandomizedTemplateDetailView.as_view(), name='exam_randomized_template_print'),
	path('<uuid:pk>/copy', exams_views.exam_copy, name='exams_copy'),
	path('<uuid:pk>/<uuid:application_student>/imprimir', exams_views.exam_answered_print, name='exam_answered_print'),
	path('prova/<uuid:pk>/editar/', exams_views.exam_teacher_subject_edit_questions, name='exam_teacher_subject_edit_questions'),
	path('prova/<uuid:pk>/antes/editar/', exams_views.exam_teacher_subject_before_edit_questions, name='exam_teacher_subject_before_edit_questions'),
	path('prova/<uuid:pk>/importar-docx/', exams_views.exam_questions_import, name='exam_questions_import'),
	path('<uuid:pk>/imprimir-freemium/', exams_views.exam_print_freemium, name='exam_print_freemium'),

	
	path('prova/professor/', exams_views.exam_teacher_create_update, name='exam_teacher_create'),
	path('prova/professor/<uuid:pk>/', exams_views.exam_teacher_create_update, name='exam_teacher_update'),

	# Exam Header
	path('cadastrar/cabecalhos/', exams_views.exam_header_create, name='exam_header_create'),
	path('cabecalhos/<uuid:pk>/editar', exams_views.exam_header_update, name='exam_header_update'),
	path('cabecalhos/<uuid:pk>/remover', exams_views.exam_header_delete, name='exam_header_delete'),
	path('cabecalhos/', exams_views.exam_header_list, name='exam_header_list'),
 
	# Páginas padrões
	path('pagina/customizada/', exams_views.ClientCustomPageListView.as_view(), name='custom-pages-list'),
	path('pagina/customizada/criar/', exams_views.ClientCustomPageCreateView.as_view(), name='custom-pages-create'),
	path('pagina/customizada/<uuid:pk>/update/', exams_views.ClientCustomPageUpdateView.as_view(), name='custom-pages-update'),
	path('api/pagina/customizada/<uuid:pk>/duplicate/', exams_views.CustomPageDuplicateView.as_view(), name='custom-pages-duplicate'),
	path('pagina/customizada/<uuid:pk>/delete/', exams_views.ClientCustomPageDeleteView.as_view(), name='custom-pages-delete'),
    
	path('api/pagina/customizada/<uuid:pk>/delete', exams.custom_pages_delete_all, name="exams_api_custom_pages_delete_all"),
	path('api/pagina/customizada/<uuid:pk>/update', client_custom_page.ClientCustomPageRetrieveUpdateAPIView.as_view(), name="client_custom_page_update"),
 
	# Backgrounds
	path('imagens/fundo/', exams_views.ExamBackgroundImageListView.as_view(), name='backgrounds-list'),
	path('imagens/fundo/criar/', exams_views.ExamBackgroundImageCreateView.as_view(), name='backgrounds-create'),
	path('imagens/fundo/<uuid:pk>/update/', exams_views.ExamBackgroundImageUpdateView.as_view(), name='backgrounds-update'),
	path('imagens/fundo/<uuid:pk>/delete/', exams_views.ExamBackgroundImageDeleteView.as_view(), name='backgrounds-delete'),
	path('api/imagens/fundo/<uuid:pk>/delete', exams.BackgroundsDestroyAPIView.as_view(), name="exams-api-background-delete-all"),

	# Exam Orientations
	path('cadastrar/orientacao/', exams_views.ExamOrientationsCreate.as_view(), name='exam_orientation_create'),
	path('orientacoes/<uuid:pk>/editar', exams_views.ExamOrientationsUpdateView.as_view(), name='exam_orientation_update'),
	path('orientacoes/<uuid:pk>/remover', exams_views.ExamOrientationDeleteView.as_view(), name='exam_orientation_delete'),
	path('orientacoes/', exams_views.ExamOrientationListView.as_view(), name='exam_orientations_list'),

	path('api/listar/', exams.exams_api_list, name='exams_api_list'),
	path('api/<uuid:pk>/', exams.exam_api_detail, name='exam_api_detail'),
	path('api/<uuid:pk>/status-questao/cadastrar/', exams.exams_status_question_api_create, name="exams_status_question_api_create"),
	path('api/<uuid:pk>/status-questao/atualizar/', exams.exams_status_question_api_update, name="exams_status_question_api_update"),
	path('api/<uuid:pk>/tags-status/cadastrar/', exams.exams_status_tags_api_create, name="exams_status_tags_api_create"),
	path('api/exam-question/<uuid:pk>/answers/', exam_questions.exam_question_answers_detail, name='exam_question_answers_detail'),
	path('api/exam-question/<uuid:pk>/answers/v2/', exam_questions.exam_question_answers_detail_v2, name='exam_question_answers_detail_v2'),
	path('api/exam-question/<uuid:pk>/partial-update/', exam_questions.exam_question_partial_update, name='exam_question_partial_update'),
	path('api/export-attachments/<uuid:pk>/<int:task_id>/', export_attachments.exam_export_attachments, name='exam_export_attachments'),
	path('api/export-attachments/<uuid:pk>/<int:task_id>/status/', export_attachments.exam_export_attachments_status, name='exam_export_attachments_status'),
	path('api/exam-status-generate-question-ia/', exams_teacher_subject_status.get_generate_question_ia_task_status, name='get_generate_question_ia_task_status'),
    path('api/exam-question/essays/', exam_questions.exam_question_essay_grade, name='exam_question_essay_grade'),
    path('api/<uuid:pk>/check-exam-application', exams.exam_bag_existence_check, name='exam_bag_existence_check'),

	# API listar ExamTeacherSubject em um Exam específico
	path('api/exam-teacher-subjects-from-exam/', exams.exam_teacher_subjects_from_exam, name='exam_teacher_subjects_from_exam'),

	path('api/copy-question/', exams.exam_question_copy, name='exam_question_copy'),

	path('api/revert-status/', exams.revert_status_question_api_view, name='revert_status_question'),
	path('api/templates/listar/', exams.exams_template_api_list, name='exams_template_api_list'),


	# Erratas views
	path('erratas/aluno/<uuid:student>/detalhes/', wrongs_views.wrongs_student_detail, name='wrongs_student_detail'),
	path('erratas/listar/', wrongs_views.wrongs_list, name='wrongs_list'),
	path('erratas/aluno/<uuid:student>/listar/', wrongs_views.student_wrongs_list, name='student_wrongs_list'),

	# API'S ERRATAS
	path('api/erratas/listar/', wrongs.student_correccion_contestation_list, name='student_correccion_contestation_list'),
	path('api/errata/criar/', wrongs.student_correccion_contestation_create, name='student_correccion_contestation_create'),
	path('api/errata/<uuid:pk>/reenviar/', wrongs.student_correccion_contestation_resend_update, name='student_correccion_contestation_resend_update'),
	path('api/errata/<uuid:pk>/detalhes/', wrongs.student_correccion_contestation_retrieve_update, name='student_correccion_contestation_retrieve_update'),
	
	path('api/errata/<uuid:pk>/alterar/gabarito', wrongs.wrongs_change_option_answer, name='wrongs_change_option_answer'),

	path('api/<uuid:pk>/remove-all/', exams.exams_api_delete_all, name='exams_api_delete_all'),

	# NOVO FLUXO DE ADICIONAR QUESTÕES PELO PROFESSOR
	path('prova/<uuid:pk>/introducao/', exams_views.ExamTeacherSubjectQuestionsBankIntroduction.as_view(), name='teacher-questions-bank-introduction'),
	path(
		'prova/<uuid:pk>/adicionar-questoes/',
		exams_views.ExamTeacherSubjectEditAddQuestionView.as_view(),
		name='exam_teacher_subject_add_questions',
	),
	path('prova/<uuid:pk>/selecionar-questoes/', exams_views.ExamTeacherSubjectQuestionsSelection.as_view(), name='teacher-questions-selection'),
	path('prova/<uuid:pk>/ver-questoes/', exams_views.ExamTeacherSubjectViewSelectedQuestions.as_view(), name='teacher-view-selected-questions'),

	# Exam Teacher Subjects
	path('professor/', teachers_views.ExamTeacherSubjectListView.as_view(), name="exam-teacher-subject-list"),
	path('professor/correcao/pendencias', teachers_views.ExamTeacherCorrectionPendenceView.as_view(), name="exam-teacher-correction-pendence-list"),
    path('professor/correcao/pendencias/reproved', teachers_views.ExamTeacherReprovedPendenceView.as_view(), name="exam-teacher-reproved-list"),
    path('professor/revisar-pdf/', teachers_views.ExamTeacherSubjectToReviewPDFListView.as_view(), name="exam-teacher-subject-to-review-pdf-list"),

	
	path('professor/revisar/', teachers_views.ExamTeacherSubjectToReviewListView.as_view(), name="exam-teacher-subject-to-review-list"),

	path('imprimir/paginas/customizada/', exams_views.CustomPagePrintTemplateView.as_view(), name="custom-pages-print"),
	
	path('api/copia-caderno-ia/', exam_copy_task_status.exam_copy_ia_task_status, name='exam_copy_ia_task_status'),
 
	path('revisoes/', exams_views.ExamReviewsListView.as_view(), name='reviews'),

] + router.urls
