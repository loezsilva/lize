from django.urls import path
from .views import DashboardsTemplateView, GetDataFromServiceAPIView, StudentFollowupView, GenerateLinksView

app_name = 'dashboards'

urlpatterns = [
    path('get/service/data/<client_pk>/', GetDataFromServiceAPIView.as_view(), name='get-data-from-service'),
    path('generate/links/<client_pk>/', GenerateLinksView.as_view(), name='generate-links'),
    path('externo/resultados-aluno/<uuid:application_student_pk>/', StudentFollowupView.as_view(), name='student-followup'),
    path('', DashboardsTemplateView.as_view(), name='dashboards'),
]