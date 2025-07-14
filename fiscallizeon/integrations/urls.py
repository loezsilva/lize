from django.urls import path

from fiscallizeon.integrations import views as integrations
from .apis import syncronzinations, activesoft, exams, ischolar, athenaweb, sophia, realms
from .apis import integrations as integrations_api
from .apis.subjects import subject_code
from rest_framework.routers import DefaultRouter
from fiscallizeon.integrations.apis.integrations import IntegrationViewSet

router = DefaultRouter()
router.register(r'api/v1/integrations', IntegrationViewSet, basename='integrations')

app_name = 'integrations'

urlpatterns = [
	path('', integrations.IntegrationCreateView.as_view(), name='integration_create_update'),
	path('sincronizacoes/', integrations.IntegrationsSynconizationsTemplateView.as_view(), name='integration_synconizations'),
	path('sincronizacoes/<int:token>/', integrations.IntegrationsSynconizationsTemplateView.as_view(), name='integration_synconizations_token'),
	path('codigos/disciplinas/', integrations.SubjectCodeTemplateView.as_view(), name='integration_subject_code_list_create'),
 	path('api/update/', integrations_api.IntegrationUpdateAPIView.as_view(), name='api-integration-update'),
	path('sincronizacoes/notas/', integrations.IntegrationNotesTemplateView.as_view(), name='integration-notes'),
	path('sincronizacoes/notas/<int:token>/', integrations.IntegrationNotesTemplateView.as_view(), name='integration-notes-token'),

	# CHECKS
	path('api/prova-migracao/', activesoft.NotesMigrationProofCreate.as_view(), name='notes-migration-proof-create'),
	path('api/unidades/check/', activesoft.CheckSincronizationUnities.as_view(), name='check-sincronization-unities'),
	path('api/classes/check/', activesoft.CheckSincronizationClasses.as_view(), name='check-sincronization-classes'),
 
	
	# APIS APENAS PARA ACTIVESOFT
	path('api/activesoft/enturmacoes/check/', activesoft.CheckSincronizationIntership.as_view(), name='check-sincronization-interships'),
	path('api/students_to_clear_school_classes/', activesoft.CheckStudentsToClearSchoolClassesAPIView.as_view(), name='check-students-to-clear-school-classes'),
	path('api/clear_students_school_classes/', activesoft.clearStudentsSchoolClassesAPIView.as_view(), name='clear-students-school-classes'),
	# END API ACTIVESOFT

	# APIS APENAS PARA  ISCHOLAR
	path('api/ischolar/enturmacoes/check/', ischolar.CheckSincronizationIntership.as_view(), name='ischolar-check-sincronization-interships'),
	path('api/ischolar/webhook/', ischolar.WebhookAPIView.as_view(), name='ischolar-webhook'),
	# END API ISCHOLAR
    
    # APIS APENAS PARA ATHENAWEB
    path('api/athenaweb/enturmacoes/check/', athenaweb.CheckSincronizationIntership.as_view(), name='athenaweb-check-sincronization-interships'),
    # END API ATHENAWEB
    
    # APIS APENAS PARA REALMS
    path('api/realms/exams/', realms.SyncExam.as_view(), name='realms-sync-exams'),
    # END API REALMS
	
	path('api/sincronizar/unidades', syncronzinations.SyncUnities.as_view(), name='sync_unities'),
	path('api/sincronizar/turmas', syncronzinations.SyncClasses.as_view(), name='sync_classes'),
	path('api/sincronizar/enturmacoes', syncronzinations.SyncInterships.as_view(), name='sync_interships'),
 	# APIS APENAS PARA SOPHIA
    path('api/sophia/enturmacoes/check/', sophia.CheckSincronizationIntership.as_view(), name='sophia-check-sincronization-interships'),
    # END API ATHENAWEB
			
	# APIS Subject Code
	path('api/disciplinas/', subject_code.api_subject_code_list_create, name='api_subject_code_list_create'),
	path('api/disciplinas/<uuid:pk>/', subject_code.api_subject_code_retrieve_update_destroy, name='api_subject_code_retrieve_update_destroy'),

	# APIS Exams
	path('api/exams/list/', exams.ExamsGradeListAPIView.as_view(), name='api-get-exams'),
	path('api/exams/students/list/', exams.StudentsExamListAPIView.as_view(), name='api-get-exams-students'),
 
] + router.urls