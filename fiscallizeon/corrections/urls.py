from django.urls import path
from fiscallizeon.corrections.api import correction
from rest_framework.routers import DefaultRouter
from .api.correction import TextCorrectionViewSet
app_name = 'corrections'
router = DefaultRouter()
router.register(r'api/v1/text_corrections', TextCorrectionViewSet, basename='text-corrections')

urlpatterns = [	

 	path('api/textuais/adicionar/', correction.CorrectionTextualAnswerListCreateAPIView.as_view(), name='correction_textual_answer_list_create'),
    path('api/textuais/<uuid:pk>/atualizar', correction.CorrectionTextualAnswerRetrieveUpdateAPIView.as_view(), name='correction_textual_answer_update'),

    path('api/arquivos/adicionar/', correction.CorrectionFileAnswerListCreateAPIView.as_view(), name='correction_file_answer_list_create'),
    path('api/arquivos/<uuid:pk>/atualizar', correction.CorrectionFileAnswerRetrieveUpdateAPIView.as_view(), name='correction_file_answer_update'),

    path('api/textual-correction-criterion/', correction.CorrectionTextualCriterionAPIListView.as_view(), name='get_textual_correction_criterion'),
    path('api/file-correction-criterion/', correction.CorrectionFileCriterionAPIListView.as_view(), name='get_file_correction_criterion'),

] + router.urls