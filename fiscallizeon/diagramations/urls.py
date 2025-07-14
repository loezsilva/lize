from django.urls import path

from fiscallizeon.diagramations import views

app_name = 'diagramations'

urlpatterns = [
	path('', views.diagramation_request_list, name='diagramation_request_list'),
	path('cadastrar/', views.diagramation_request_create, name='diagramation_request_create'),
	path('<uuid:pk>/editar/', views.diagramation_request_update, name='diagramation_request_update'),
	path('<uuid:pk>/remover/', views.diagramation_request_delete, name='diagramation_request_delete'),
]