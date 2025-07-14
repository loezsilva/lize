from django.urls import path

from fiscallizeon.candidates import views

app_name = 'candidates'

urlpatterns = [
	path('cadastrar/<uuid:pk>', views.candidate_create_view, name='candidate_create_view'),
]