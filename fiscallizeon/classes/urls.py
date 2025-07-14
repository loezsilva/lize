from django.urls import path

from fiscallizeon.classes.views import school_class as school_class_view, course_type as course_type_view, stage as stage_view, course as course_view
from fiscallizeon.classes.views import grade as grade_view

app_name = 'classes'

urlpatterns = [
	path('', school_class_view.classes_list, name='classes_list'),
	path('cadastrar/', school_class_view.classes_create, name='classes_create'),
	path('<uuid:pk>/editar/', school_class_view.classes_update, name='classes_update'),
	path('<uuid:pk>/remover/', school_class_view.classes_delete, name='classes_delete'),
 
	path('tipo-cursos', course_type_view.courses_type_list, name='courses_type_list'),
 	path('tipo-cursos/cadastrar/', course_type_view.courses_type_create, name='courses_type_create'),
  	path('tipo-cursos/<uuid:pk>/editar/', course_type_view.courses_type_update, name='courses_type_update'),
	path('tipo-cursos/<uuid:pk>/remover/', course_type_view.courses_type_delete, name='courses_type_delete'),
 
 	path('cursos', course_view.courses_list, name='courses_list'),
 	path('cursos/cadastrar/', course_view.courses_create, name='courses_create'),
  	path('cursos/<uuid:pk>/editar/', course_view.courses_update, name='courses_update'),
	path('cursos/<uuid:pk>/remover/', course_view.courses_delete, name='courses_delete'),
 
 	path('etapas', stage_view.stage_list, name='stage_list'),
	path('etapas/cadastrar/', stage_view.stage_create, name='stage_create'),
  	path('etapas/<uuid:pk>/editar/', stage_view.stage_update, name='stage_update'),
	path('etapas/<uuid:pk>/remover/', stage_view.stage_delete, name='stage_delete'),
  
	path('api/turmas', school_class_view.classes_list_api, name='classes_list_api'),
	path('api/public/turmas/<uuid:client_id>', school_class_view.classes_list_public_api, name='classes_list_public_api'),
	path('api/series', grade_view.grade_list_api, name='grade_list_api'),
]