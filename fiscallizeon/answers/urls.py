from rest_framework.routers import DefaultRouter

from django.urls import path
from fiscallizeon.answers.api.attachements import AttachmentsViewSet

from fiscallizeon.answers.api.file_answers import FileAnswerDeleteAnswerDeleteAPIView, FileAnswerRemoveGradeUpdateView, FileAnswerCreateView, FileAnswerImgAnnotationsRetrieveView, FileAnswerImgAnnotationsUpdateAPIView, FileAnswerQRCodeCreateView, FileAnswerQRCodeRetrieveView, FileAnswerResponseSearchListAPIView, FileAnswerTeacherCoordinationCreateView, FileAnswerUpdateRetrieveView, FileAnswerFeedbackUpdateView, FileAnswerTeacherFeedbackUpdateView
from fiscallizeon.answers.api.option_answers import OptionAnswerCreateView, OptionAnswerRetrieveUpdateView, OptionAnswerDeleteAnswerDeleteAPIView, OptionAnswerCoordinationCreateView, OptionAnswerRetrieveCoordinationUpdateView
from fiscallizeon.answers.api.proof_answers import ProofAnswerListAPIView
from fiscallizeon.answers.api.textual_answers import TextualAnswerRemoveGradeUpdateView, TextualAnswerCreateView, TextualAnswerRetreiveUpdateView, TextualAnswerFeedbackUpdateView, TextualAnswerDeleteAnswerDeleteAPIView
from fiscallizeon.answers.api.sum_answers import SumAnswerUpdateView, SumAnswerDeleteAPIView, SumAnswerCreateUpdateView
from fiscallizeon.answers.views import ProofAnswerCreateView, ProofOfAnswersCoordinationTemplateView, ProofOfAnswersTemplateView, AnswersPendentCorrectionTemplateView

app_name = 'answers'
router = DefaultRouter()
router.register(r'api/anexos/listar/criar', AttachmentsViewSet, basename='api-attachments')

urlpatterns = [
    path('arquivos/', FileAnswerCreateView.as_view(), name='file_create'),
    path('arquivos/professor/coordenacao/', FileAnswerTeacherCoordinationCreateView.as_view(), name='file_teacher_coordination_create'),
    path('arquivos/<uuid:pk>/', FileAnswerUpdateRetrieveView.as_view(), name='file_retrieve_update'),
    path('opcoes/', OptionAnswerCreateView.as_view(), name='create_option'),
    path('opcoes/<uuid:pk>/', OptionAnswerRetrieveUpdateView.as_view(), name='option'),
    path('opcoes/coordenacao/', OptionAnswerCoordinationCreateView.as_view(), name='create_option_coordination'),
    path('opcoes/coordenacao/<uuid:pk>/', OptionAnswerRetrieveCoordinationUpdateView.as_view(), name='option_coordination'),
    path('textuais/', TextualAnswerCreateView.as_view(), name='text_create'),
    path('textuais/<uuid:pk>/', TextualAnswerRetreiveUpdateView.as_view(), name='text_retrieve_update'),
    path('textuais/<uuid:pk>/feedback', TextualAnswerFeedbackUpdateView.as_view(), name='text_update_feedback'),
    path('arquivos/<uuid:pk>/feedback', FileAnswerFeedbackUpdateView.as_view(), name='file_update_feedback'),
    path('arquivos/<uuid:pk>/teacher_feedback/', FileAnswerTeacherFeedbackUpdateView.as_view(), name='file_update_teacher_feedback'),
    path('api/sum_question/update', SumAnswerUpdateView.as_view(), name='sum_question_update'),
    path('api/sum_question/create-update', SumAnswerCreateUpdateView.as_view(), name='create_update_sum_answer'),

    # APIS REMOÇÂO DE NOTAS OU RESPOSTA
    path('textuais/<uuid:pk>/remove/grade/', TextualAnswerRemoveGradeUpdateView.as_view(), name='text_remove_grade_update'),
    path('arquivos/<uuid:pk>/remove/grade/', FileAnswerRemoveGradeUpdateView.as_view(), name='file_remove_grade_update'),
    path('textuais/<uuid:pk>/delete/answer/', TextualAnswerDeleteAnswerDeleteAPIView.as_view(), name='textual_delete_answer'),
    path('arquivos/<uuid:pk>/delete/answer/', FileAnswerDeleteAnswerDeleteAPIView.as_view(), name='file_delete_answer'),
    path('options/<uuid:pk>/delete/answer/', OptionAnswerDeleteAnswerDeleteAPIView.as_view(), name='option_delete_answer'),
    path('sum/<uuid:pk>/delete/answer/', SumAnswerDeleteAPIView.as_view(), name='sum_answer_delete_answer'),
    
    path('arquivos/qrcode', FileAnswerQRCodeCreateView.as_view(), name='file_create_qrcode'),
    path('arquivos/<uuid:pk>/qrcode', FileAnswerQRCodeRetrieveView.as_view(), name='file_retrieve_update_qrcode'),
    path('buscar/', FileAnswerResponseSearchListAPIView.as_view(), name='file_answer_search'),
    
    path('<uuid:pk>/comentarios/criar/', FileAnswerImgAnnotationsUpdateAPIView.as_view(), name='api_fileanswer_annotations_create_or_update'),
    path('<uuid:pk>/buscar/comentarios/', FileAnswerImgAnnotationsRetrieveView.as_view(), name='api_fileanswer_annotations'),

    # Comprovantes de resposta
	path('comprovante/<uuid:pk>/', ProofOfAnswersTemplateView.as_view(), name='proof_of_answers'),
	path('comprovante/consultar/<uuid:pk>/', ProofOfAnswersCoordinationTemplateView.as_view(), name='proof_of_answers_coordination'),
	path('comprovante/criar/<uuid:pk>/', ProofAnswerCreateView.as_view(), name='proof_of_answers_create'),
    # API Comprovantes
	path('api/comprovante/list', ProofAnswerListAPIView.as_view(), name='api-proof-answers-list'),
    
    path('correcao/pendente/', AnswersPendentCorrectionTemplateView.as_view(), name='answers-pendent-correction')
]

urlpatterns += router.urls