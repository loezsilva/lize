from django.urls import path

from fiscallizeon.inspectors.views import inspectors
from fiscallizeon.inspectors.views import teachers

app_name = 'inspectors'

urlpatterns = [
	path('', inspectors.inspectors_list, name='inspectors_list'),
	path('cadastrar/', inspectors.inspectors_create, name='inspectors_create'),
	path('<uuid:pk>/editar/', inspectors.inspectors_update, name='inspectors_update'),
	path('<uuid:pk>/remover/', inspectors.inspectors_delete, name='inspectors_delete'),
	path('api/', inspectors.inspectors_list_api, name='inspectors_list_api'),
	path('api/teacher', teachers.teachers_list_api, name='teacher_list_api'),
	path('api/teacher/simple/', teachers.teacher_simple_list_api, name='teacher_simple_list_api'),
	path('api/teacher-change-experience/<uuid:pk>/', teachers.teachers_experience_change_api, name='teachers_experience_change_api'),
 	path('api/teacher-update-questions-bank-tutorial/', teachers.teacher_update_questions_bank_tutoria, name='teacher_update_questions_bank_tutoria'),

 
	path('professor/', teachers.teachers_list, name='teachers_list'),
	path('professor/cadastrar/', teachers.teachers_create, name='teachers_create'),
	path('professor/<uuid:pk>/editar/', teachers.teachers_update, name='teachers_update'),
	path('professor/<uuid:pk>/remover/', teachers.teachers_delete, name='teachers_delete'),
	path('professor/<uuid:pk>/reset/', teachers.teachers_password_reset, name='teachers_password_reset'),
	path('professor/importar/', teachers.ImportTeacher.as_view(), name='import_teachers'),
	path('professor/exportar/', teachers.teachers_export, name='export_teachers_csv'),

]