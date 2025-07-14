from django.urls import path

from fiscallizeon.materials import views
from fiscallizeon.materials.api import favorite
from fiscallizeon.materials.api import materials

app_name = 'materials'

urlpatterns = [
	# Meterials
	path('', views.study_material_list, name='study_material_list'),
	path('criar/', views.study_material_create, name='study_material_create'),
	path('<uuid:pk>/editar/', views.study_material_update, name='study_material_update'),
	path('<uuid:pk>/remover/', views.study_material_delete, name='study_material_delete'),
	
	# Favorites
	path('api/<uuid:pk>/favoritar/', favorite.favorite_study_material, name='favorite_study_material'),
	path('api/<uuid:pk>/detalhe/', materials.api_study_material_detail, name='api_study_material_detail'),
]