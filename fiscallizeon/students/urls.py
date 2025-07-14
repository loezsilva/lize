from django.urls import path

from fiscallizeon.students.api import students
from fiscallizeon.students.api import students_activesoft
from fiscallizeon.students.api import students_sisu
from fiscallizeon.students import views

app_name = 'students'

urlpatterns = [
	path('', views.students_list, name='students_list'),
	path('material/', views.study_material_students_list, name='study_material_students_list'),
	path('cadastrar/', views.students_create, name='students_create'),
	path('<uuid:pk>', views.students_detail, name='students_detail'),
	path('<uuid:pk>/editar', views.students_update, name='students_update'),
	path('<uuid:pk>/resetar', views.students_reset, name='students_reset'),
	path('importar/', views.students_import, name='students_import'),
	path('importar/v2/', views.students_import_v2, name='students_import_v2'),
 	path('exportar_alunos/', views.students_export, name='export_students_csv'),
	path(
		'atualizar-matriculas/', 
		views.students_update_enrollments, 
		name='students_update_enrollments'
	),
	path('api', views.students_list_api, name='students_list_api'),
	path('api/listagem-2', students.students_list_api, name='students_list_api_2'),
	path('api/send_mail/parent/', students.StudentSendEmailToParentAPIView.as_view(), name='send-email-to-parent'),

	path('api/get/applications/', students.StudentGetApplications.as_view(), name='get-applications'),
	path('api/deactivate-student/<uuid:student_pk>/', students.StudentDeactivate.as_view(), name='deactivate-student'),
    path('api/students_massive_reset_password', students.students_massive_reset_password, name='students_massive_reset_password'),

	path('simulador/sisu/', views.SISUSimulatorTemplateView.as_view(), name='sisusimulator'),

	#API Exclusiva para activesoft
	path('api/students/list/composition/note/', students_activesoft.StudentNoteCompositionAPIView.as_view(), name='students-list-composition'),
	
 	# API para os cursos do SISU
	path('api/students/sisu/course/', students_sisu.StudentSisuCourseAPIView.as_view(), name='get-sisu-course'),
	path('api/students/sisu/course/update/create/', students_sisu.StudentSisuCourseUpdateOrCreateAPIView.as_view(), name='update-or-create-sisu-course')
]