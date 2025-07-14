from django.urls import path

from fiscallizeon.applications import views
from fiscallizeon.applications.api import annotation, application, notice, application_student, exams_bag
from fiscallizeon.mentorize.views import ApplicationStudentListView

app_name = 'applications'

urlpatterns = [
	path('', views.applications_list, name='applications_list'),
	path('monitoramento/', views.applications_monitoring, name='applications_monitoring'),
	path('aluno/', views.application_student_list, name='application_student_list'),
	path('aluno/<uuid:pk>', views.application_exam_student_detail, name='application_exam_student_detail'),
	path(
		'prova/<uuid:pk>/detalhe/',
		views.application_exam_student_detail_v2,
		name='application_exam_student_detail_v2',
	),
	path(
		'prova/<uuid:pk>/detalhe/melhorias/',
		views.application_exam_student_detail_insight,
		name='application_exam_student_detail_insight',
	),
	path(
		'prova/<uuid:pk>/redacao/detalhe/',
		views.ApplicationEssayDetailView.as_view(),
		name='application_student_essay_detail',
	),
	path('previo/<uuid:pk>', views.application_previous_feedback, name='application_previous_feedback'),
	# path('aluno/<uuid:pk>', views.application_student_detail, name='application_student_detail'),
	
	path('<uuid:pk>', views.applications_detail, name='applications_detail'),
	path('cadastrar/', views.applications_create, name='applications_create'),
	path('cadastrar/multiplas', views.applications_create_multiple, name='applications_create_multiple'),
	path('<uuid:pk>/editar', views.applications_update, name='applications_update'),
	path('<uuid:pk>/remover', views.applications_delete, name='applications_delete'),
	path('<uuid:pk>/divulgar', views.applications_disclose, name='applications_disclose'),
	path('<uuid:pk>/adicionar', views.applications_add_del_student, name='applications_add_del_student'),
	path('<uuid:pk>/monitorar', views.applications_monitoring_inspector, name='applications_monitoring_inspector'),
	path('<uuid:pk>/orientacoes', views.applications_orientations_student, name='applications_orientations_student'),
	path('<uuid:pk>/realizar-avaliacao', views.applications_monitoring_student, name='applications_monitoring_student'),

	path('<uuid:pk>/realizar-atividade', views.applications_homework_student, name='applications_homework_student'),

	path('impressao/', views.print_applications_list, name='print_applications_list'),
    path('tipos-aplicacoes/', views.type_application_list, name='type_application_list'),
    path('tipos-aplicacoes/cadastrar/', views.type_application_create, name='type_application_create'),
    path('tipos-aplicacoes/editar/<uuid:pk>/', views.type_application_update, name='type_application_update'),
    path('tipos-aplicacoes/remover/<uuid:pk>/', views.type_application_delete, name='type_application_delete'),
	path('exportacao-aplicacoes-pdf/', views.applications_export_pdf, name='applications_export_pdf'),
	path('importar/alunos-em-aplicacoes/', views.application_students_import, name='application_students_import'),

	#API
	path('api/', application.application_list, name='api_applications_list'),
	path('api/<uuid:pk>/change_is_printed/', application.ApplicationChangeIsPrintedAPIView.as_view(), name='api-change-is-printed'),
	path('api/<uuid:pk>/change_book_is_printed/', application.ApplicationChangeBookIsPrintedAPIView.as_view(), name='api_change_book_is_printed'),
	path('api/<uuid:pk>/change_print_ready/', application.ApplicationChangePrintReadyAPIView.as_view(), name='api_change_print_ready'),
	path('api/<uuid:pk>/iniciar-avaliacao', application.application_start_view, name='application_start'),
	path('api/<uuid:pk>/finalizar-avaliacao', application.application_end_view, name='application_end'),
	path('api/<uuid:pk>/check-finalizar-avaliacao', application.application_check_end_view, name='application_check_end'),
	path('api/<uuid:pk>/remover-aplicacao', application.application_delete_api, name='application_delete_api'),
    path('api/<uuid:pk>/token_online', application.application_token_online, name='application_token_online'),
	path('api/<uuid:pk>/exportar-malote-provas', exams_bag.export_application_exams_bag, name='export_application_exams_bag'),
	path('api/<uuid:pk>/remover-malote', exams_bag.remove_application_exam_bag, name='remove_application_exam_bag'),
	path('api/<uuid:pk>/exportar-malote-elit', exams_bag.export_application_elit_exams_bag, name='export_application_elit_exams_bag'),

	
	path('api/<uuid:pk>/duplicar', application.application_duplicate, name='application_duplicate'),

	path('api/<uuid:pk>/justificar-atraso', application.application_student_justify_delay, name='application_student_justify_delay'),
	path('api/anotacao/criar', annotation.annotation_create_api, name="annotation_create_api"),
	path('api/anotacao-aplicacao/criar', annotation.application_annotation_create_api, name="application_annotation_create_api"),
	path('api/aviso-aplicacao/criar', notice.application_notice_create_api, name="application_notice_create_api"),
	path('api/aplicacao-aluno/<uuid:pk>', application_student.application_student_exam_api, name="application_student_exam_api"),
	path('api/upload-alunos', application.application_student_upload, name="application_student_upload"),
	path('api/quantidade-paginas/<uuid:pk>', application.application_pages_amount, name="application_pages_quantity"),
	path('api/exportar-listagem-impressao/', application.export_print_list, name="application_export_print_list"),
    path('api/excecao-horario', application_student.application_student_exception_api, name="application_student_exception_api"),

 	# API para zerar prova do aluno
	path('api/clear/applicationstudent/<uuid:pk>/', application_student.ApplicationStudentClearUpdateAPIView.as_view(), name='api_clear_and_missed_applicationstudent'),
	path('api/empty/questions/applicationstudent/<uuid:pk>/', application_student.ApplicationStudentEmptyQuestionsAPIView.as_view(), name='api-set-empty-questions-applicationstudent'),
	
	
	path('api/listar/apicacoes/alunos/', application.applications_students_coordination, name='api_applications_students_coordination'),
   
	path('api/applications/checkexam/<uuid:pk>/', application.ApplicationCheckExamView.as_view(), name='application_exam_exist'),

	path('api/application-teachersubjects/<uuid:pk>/', application.teacher_subject_list_from_application, name='teacher_subject_list_from_application'),
	path('api/application-questions-report/<uuid:pk>/', application.questions_report_from_application, name='questions_report_from_application'),
	
	# Mentorize views
	path('aluno/mentorize/', ApplicationStudentListView.as_view(), name='mentorize_application_student_list'),
	
	path('api/applicationstudent/<uuid:pk>/choose/language', application_student.ApplicationStudentChooseLanguageUpdateAPIView.as_view(), name='api-applicationstudent-choose-language'),
    
	path('clear_answers/<uuid:pk>/', views.ClearAllAnswersAndRedirectView.as_view(), name='clear_all_answers')


]