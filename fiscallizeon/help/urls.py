from django.urls import path

from .views import TutorialTemplateView, TutorialListView, TutorialDetailTemplateView, TutorialCategoryDetailTemplateView

app_name = 'help'

urlpatterns = [
	path('tutoriais/', TutorialTemplateView.as_view(), name='tutoriais'),
	path('tutoriais/buscar/', TutorialListView.as_view(), name='tutorial-search-list'),
	path('tutoriais/<uuid:pk>/', TutorialDetailTemplateView.as_view(), name='tutorial-detail'),
	path('tutoriais/categoria/<uuid:pk>/', TutorialCategoryDetailTemplateView.as_view(), name='tutorial-category-detail'),
]