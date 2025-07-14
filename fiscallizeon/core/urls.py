from django.urls import path

from fiscallizeon.core import views
from fiscallizeon.core.api import celery_task_status
from fiscallizeon.mentorize.views import (
	DashboardStudentExamPreviewDetailsView,
	DashboardStudentView,
	DashboardStudentFirstAccessView
)

app_name = 'core'

urlpatterns = [
	path('tmp-page/<uuid:inspector_id>/', views.TmpAnswerPage.as_view(), name='tmp-page'),
	path('dashboard/', views.redirect_dashboard, name='redirect_dashboard'),
	path('coordenacao/', views.dashboard_coordination, name='dashboard_coordination'),
	path('fiscal/', views.dashboard_inspector, name='dashboard_inspector'),
	path('aluno/', views.dashboard_student, name='dashboard_student'),
	path('aluno/mentorize/first', DashboardStudentFirstAccessView.as_view(), name='dashboard_student_first_mentorize'),
	path('parceiro/', views.dashboard_partner, name='dashboard_partner'),
	path('', views.DashboardFreemiumView.as_view(), name='dashboard_freemium'),

	path('professor/', views.dashboard_teacher, name='dashboard_teacher'),
	path('professor/dashboard/', views.DashboardGenericTeacherView.as_view(), name='dashboard_generic_teacher'),

	path('webhook/new-student', views.webhook_new_student, name='webhook_new_student'),

	path('upload-image-paste/', views.upload_image_paste, name='upload_image_paste'),
    path('upload-image-ia/', views.upload_image_to_generate_question_with_AI, name='upload_image_ia'),


	path('upload-image/', views.upload_image, name='upload_image'),
	path('image-proxy/', views.image_proxy, name='image-proxy'),
	#APIget_generic_task_status
	path('api/task-status/', celery_task_status.get_generic_task_status, name='get_generic_task_status'),

	path('aluno/mentorize/', DashboardStudentView.as_view(), name='dashboard_student_mentorize'),
	path('aluno/mentorize/revisar/conteudo/<uuid:pk>', DashboardStudentExamPreviewDetailsView.as_view(), name='dashboard_student_mentorize_exam_review'),
	path('find-themes/', views.FindThemes.as_view(), name='find-themes'),

	path('responsaveis/', views.dashboard_parent, name='dashboard_parent'),
    
	path('hijack/login/user/', views.CustomAcquireUserView.as_view(), name='hijack-login-user'),
    path('switch-profile/', views.SwitchUserProfileView.as_view(), name='switch_user_profile'),

]