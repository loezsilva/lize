from django.urls import path

from . import views


app_name = 'onboarding'

urlpatterns = [
    path('', views.index, name='index'),
    path('<int:step>/', views.detail, name='detail'),
    path('<int:step>/debug/', views.detail_debug, name='detail-debug'),

    path('<int:step>/coordinators/upload-file/', views.upload_file_coordinators, name='upload-file-coordinators'),
    path('<int:step>/teachers/upload-file/', views.upload_file_teachers, name='upload-file-teachers'),
    path('<int:step>/students/upload-file/', views.upload_file_students, name='upload-file-students'),

    path('<int:step>/students/external-system/', views.external_system_students, name='external-system-students'),

    path('<int:step>/segments/', views.detail_segments, name='detail-segments'),

    path('<int:step>/permissions/', views.define_permissions, name='define-permissions'),
    path('<int:step>/feedback/', views.feedback, name='feedback'),

    path('import/coordinators/', views.upload_import_coordinators, name='upload-import-coordinators'),
    path('import/teachers/', views.upload_import_teachers, name='upload-import-teachers'),
    path('import/students/', views.upload_import_students, name='upload-import-students'),

    # path('import/task/<uuid:task_pk>/status/', views.get_task_status, name='get_task_status'),
]
