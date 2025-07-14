from rest_framework.routers import DefaultRouter

from fiscallizeon.subjects.views import knowledge_areas as knowledge_areas_views
from fiscallizeon.subjects.views import subjects as subject_views
from fiscallizeon.subjects.api import theme as theme_views
from fiscallizeon.subjects.api import main_topic as main_topic_views

from fiscallizeon.subjects.api import subjects as subjects_api
from fiscallizeon.subjects.api import topics as topics_api

from fiscallizeon.subjects.views import topics as topic_views

from django.urls import path


app_name = 'subjects'
router = DefaultRouter()

router.register(r'api/', subject_views.SubjectViewSet)
router.register(r'api/knowledge_areas', knowledge_areas_views.KnowledgeAreaViewSet)
router.register(r'api/topics', topic_views.TopicViewSet)
router.register(r'api/theme', theme_views.ThemeViewSet)
router.register(r'api/theme', main_topic_views.MainTopicViewSet)

urlpatterns = [
    path('api/areas_conhecimento', knowledge_areas_views.knowledge_area_list_api, name='knowledge_area_list_api'),
    path('api/areas_conhecimento_com_lingua_estangeira', knowledge_areas_views.knowledge_area_with_language_subject_list_api, name='knowledge_area_with_language_subject_list_api'),
    path('api/disciplinas', subject_views.subject_list_api, name='subject_list_api'),
    path('api/disciplinas/criar', subjects_api.SubjectsCreateApiView.as_view(), name='subject_create_api'),
    path('api/topicos', topic_views.topic_list_api, name='topic_list_api'),
    path('api/temas', theme_views.theme_list_api, name='theme_list_api'),\
    path('api/temas/criar', theme_views.theme_create_api, name='theme_create_api'),
    path('api/topico', main_topic_views.main_topic_list_api, name='main_topic_list_api'),
    path('api/topico/criar', main_topic_views.main_topic_create_api, name='main_topic_create_api'),
    path('api/lista_disciplinas_professor/<uuid:pk>/', subjects_api.InspectorSubjectsView.as_view(), name='list_subjects_inspector'),

    path('disciplinas/', subject_views.subjects_list, name='subjects_list'),
    path('disciplinas/cadastrar/', subject_views.subjects_create, name='subjects_create'),
    path('disciplinas/<uuid:pk>/editar/', subject_views.subjects_update, name='subjects_update'),
	path('disciplinas/<uuid:pk>/remover/', subject_views.subjects_delete, name='subjects_delete'),

    path('relacoes/', subject_views.SubjectRelationtList.as_view(), name='subjects_relation_list'),
    path('relacoes/cadastrar/', subject_views.SubjectRelationCreateView.as_view(), name='subjects_relation_create'),
    path('relacoes/<uuid:pk>/editar/', subject_views.SubjectRelationUpdateView.as_view(), name='subjects_relation_update'),
	path('relacoes/<uuid:pk>/remover/', subject_views.SubjectRelationUpdateView.as_view(), name='subjects_relation_delete'),

    path('assuntos/', topic_views.topic_list, name='topic_list'),
    path('assuntos/importar/', topic_views.topic_import, name='topic_import'),
    path('assuntos/importar/completo', topic_views.topic_complete_topic, name='topic_complete_topic'),

    path('assuntos/cadastrar/', topic_views.topic_create, name='topic_create'),
    path('assuntos/<uuid:pk>/editar/', topic_views.topic_update, name='topic_update'),
	path('assuntos/<uuid:pk>/remover/', topic_views.topic_delete, name='topic_delete'),
    path('assuntos/cadastrar_completo/', topics_api.TopicsCreateApiView.as_view(), name='topic_create_complete'),


    #New API
    path('api/materials/subjects/list', subject_views.subject_study_material_list_api, name='subject_study_material_list_api'),
]

urlpatterns += router.urls