from rest_framework.routers import DefaultRouter

from fiscallizeon.bncc.views import competence as competence_views
from fiscallizeon.bncc.views import ability as ability_views
from fiscallizeon.bncc.api.competences import CompetenceCreateApiView
from fiscallizeon.bncc.api.abilities import AbiliityCreateApiView


from django.urls import path


app_name = 'bncc'
router = DefaultRouter()


urlpatterns = [
    path('api/competencias', competence_views.competence_list_api, name='competence_list_api'),
    path('competencias', competence_views.competences_list, name='competences_list'),
    path('api/competencia/criar', CompetenceCreateApiView.as_view(), name='competence_create_api'),

    
    path('competencias/cadastrar', competence_views.competences_create, name='competences_create'),
    path('competencias/<uuid:pk>/editar/', competence_views.competences_update, name='competences_update'),
	path('competencias/<uuid:pk>/remover/', competence_views.competences_delete, name='competences_delete'),
    
    path('api/habilidades', ability_views.ability_list_api, name='ability_list_api'),
    path('api/habilidades/criar', AbiliityCreateApiView.as_view(), name='ability_create_api'),
    path('habilidades', ability_views.abilities_list, name='abilities_list'),
    path('habilidades/importar', ability_views.ability_import, name='ability_import'),
    path('habilidades/cadastrar', ability_views.abilities_create, name='abilities_create'),
    path('habilidades/<uuid:pk>/editar/', ability_views.abilities_update, name='abilities_update'),
	path('habilidades/<uuid:pk>/remover/', ability_views.abilities_delete, name='abilities_delete'),
]

urlpatterns += router.urls