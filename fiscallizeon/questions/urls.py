from django.urls import path, include

from rest_framework.routers import DefaultRouter

from fiscallizeon.questions.api import base_texts, questions as api_questions
from fiscallizeon.questions.api2 import question as api2_questions
from fiscallizeon.questions.views import questions, public_questions

app_name = 'questions'
router = DefaultRouter()

router.register(r'api/v1', api_questions.QuestionViewSet, basename='questions')
router.register(r'api/v1/alternatives', api_questions.QuestionOptionViewSet, basename='alternatives')

urlpatterns = [	
    path('', questions.questions_list, name='questions_list'),
    path('publicas', public_questions.public_questions_list, name='public_questions_list'),
    path('criar-com-ia/', questions.CreateAIQuestion.as_view(), name='create_ai'),

	path('cadastrar/', questions.questions_create, name='questions_create'),
	path('<uuid:pk>/editar/', questions.questions_update, name='questions_update'),
	path('<uuid:pk>/selecionar/', questions.questions_select, name='questions_select'),
	path('<uuid:pk>/remover/', questions.questions_delete, name='questions_delete'),
	path('<uuid:pk>/copiar/', public_questions.public_questions_copy, name='public_questions_copy'),
	
	path('api/listar/', api_questions.questions_api_list, name='questions_api_list'),
	path('api/<uuid:pk>/', api_questions.questions_api_detail, name='questions_api_detail'),
	path('api/<uuid:pk>/<uuid:student_application>/', api_questions.question_fileanswer_student_api, name='question_fileanswer_student_api'),
	path('api/na/<uuid:pk>/', api_questions.questions_api_detail_no_answer, name='questions_api_detail_no_answer'),
	path('api/<uuid:pk>/selecionar/', api_questions.questions_select_only, name='questions_select_only'),
	path('api/<uuid:pk>/copiar-selecionar/', api_questions.question_copy_detail_view, name='question_copy_detail_view'),
	path('api/<uuid:pk>/historical/', api_questions.questions_historical, name='question_historical'),
    path('api/correction-answers/', api2_questions.GetCorrectionAnswersView.as_view(), name='get_correction_answers'),

	#Base Text
	path('api/texto_base/listar/adicionar/', base_texts.base_text_list_create, name='base_text_list_create'),
	path('api/texto_base/editar/remover/<uuid:pk>/', base_texts.base_text_retrive_update_destroy, name='base_text_retrive_update_destroy'),
	path('api/texto_base/prova/<uuid:pk>', base_texts.base_text_exam, name='base_text_exam'),

	path('api/formatador/', api2_questions.QuestionFormatterAPIView.as_view(), name="formatter"),
    path('api/change-question-type/', api2_questions.ChangeQuestionAPIView.as_view(), name='change_question_ia'),
    path('api/confirm-change-question-type/', api2_questions.ConfirmChangeQuestionAPIView.as_view(), name='confirm_change_question_type'),

]

urlpatterns += router.urls