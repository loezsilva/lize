from django.urls import include, path
from fiscallizeon.analytics.api import application_student as applications_student_api

from fiscallizeon.applications.apis import (
    ApplicationStudentQuestionDetailApi,
    ApplicationStudentSubjectDetailApi,
    ApplicationStudentSubjectChartDetailApi,
    ApplicationStudentQuestionListApi,
    ApplicationStudentQuestionRetryApi,
    ApplicationViewSet,
)
from fiscallizeon.applications.api.application import (
    ApplicationDeadlineCorrectionResponseExceptionCreateDeleteAPIView,
)
from fiscallizeon.core.apis import SearchView, FeedbackOnboardingAPIView
from fiscallizeon.exams.api import widgets as exam_widgets
from fiscallizeon.exams.api import exams as exam_api
from fiscallizeon.exams.apis import (
    ExamPdfPreviewApi,
    ClientCustomPagePreviewApi,
    ExamPrintConfigUpdateApi,
    ExamQuestionPrintConfigUpdateApi,
    ExamTeacherSubjectFileUpload,
    ExamUpdateStatusApi,
)
from fiscallizeon.inspectors.apis import TeacherSuperProfDataApi
from fiscallizeon.questions.apis import QuestionDetailApi, QuestionVerySimpleAPI

from fiscallizeon.bncc.api import abilities as abilities_apis
from fiscallizeon.bncc.api import competences as competences_apis
from fiscallizeon.bncc.api import topics as topics_apis

from fiscallizeon.analytics.api import students as students_apis
from fiscallizeon.inspectors.api import inspectors as inspectors_api
from fiscallizeon.integrations.apis import superprof as superprof_apis

from fiscallizeon.subjects.views.subjects import SubjectTreeListView, SubjectTreeDetailView

from fiscallizeon.clients.api import clients, print_configs, custom_filters, teaching_stages, education_systems
from fiscallizeon.analytics.api import calendar
from fiscallizeon.help.api.views import tutoriais

from fiscallizeon.ai.api import SuperSearchAPIView

from rest_framework.routers import DefaultRouter

applications_student_routers = DefaultRouter()
routers = DefaultRouter()
bncc_routers = DefaultRouter()
clients_routers = DefaultRouter()

routers.register(r'inspectors', inspectors_api.InspectorViewSet, basename='inspectors')
routers.register(r'superprof', superprof_apis.SuperProfIntegrationViewSet, basename='superprof')
routers.register(r'calendar', calendar.CalendarViewSet, basename='calendar')
routers.register(r'applications', ApplicationViewSet, basename='applications')

applications_student_routers.register(r'analysis', applications_student_api.ApplicationStudentAnalysisViewSet, basename='student-analysis')

bncc_routers.register(r'topics', topics_apis.TopicViewSet, basename='topics')
bncc_routers.register(r'abilities', abilities_apis.AbilityViewSet, basename='abilities')
bncc_routers.register(r'competences', competences_apis.CompetenceViewSet, basename='competences')

clients_routers.register(r'print-configs', print_configs.ExamPrintConfigViewSet, basename='print-configs')
clients_routers.register(r'teaching-stage', teaching_stages.TeachingStageViewSet, basename='teaching-stage')
clients_routers.register(r'education-system', education_systems.EducationSystemViewSet, basename='education-system')
clients_routers.register(r'custom-filters', custom_filters.ClientCustomFiltersViewSet, basename='custom-filters')
clients_routers.register(r'tutoriais', tutoriais.TutorialsViewSet, basename='tutoriais')
clients_routers.register(r'', clients.ClientViewSet, basename='client')
clients_routers.register(r'client-configurations', clients.ClientConfigurationsViewSet, basename='client-configurations')


app_name = 'api'

question_patterns = [
    path('<uuid:question_id>/', QuestionDetailApi.as_view(), name='detail'),
    path('simple/questions/list/', QuestionVerySimpleAPI.as_view(), name='simple-questions-list'),
    
]
exams_patterns = [
    path('optionanswers/widget/', exam_widgets.WidgetObjectiveAnswers.as_view(), name='optionanswers_widget'),
    path('discursiveanswers/widget/', exam_widgets.WidgetDiscursiveAnswers.as_view(), name='discursiveanswers_widget'),
    path('bncc/performance/<uuid:pk>/', exam_api.ExamBnccPerformance.as_view(), name='exam_bncc_performance'),
    path('performance/<uuid:pk>/subject/', exam_api.ExamSubjectsPerformance.as_view(), name='exam_subjects_performance'),
    path('performance/students/', exam_api.ApplicationStudentPerformance.as_view(), name='exam_students_performance'),
    path('performance/classes/<uuid:pk>/', exam_api.ClassesPerformances.as_view(), name='exam_classes_performance'),
    path('performance/unities/<uuid:pk>/', exam_api.ExamUnitiesPerformance.as_view(), name='exam_unities_performance'),
    path('histogram/<uuid:pk>/', exam_api.ExamHistograms.as_view(), name='exam_histograms_performance'),
]

application_student_patterns = [
    path(
        '<uuid:application_student_id>/questions/<uuid:question_id>/',
        ApplicationStudentQuestionDetailApi.as_view(),
        name='question-detail',
    ),
    path(
        '<uuid:application_student_id>/subjects/<uuid:subject_id>/',
        ApplicationStudentSubjectDetailApi.as_view(),
        name='subject-detail',
    ),
    path(
        '<uuid:application_student_id>/subjects/<uuid:subject_id>/chart/',
        ApplicationStudentSubjectChartDetailApi.as_view(),
        name='subject-detail-chart',
    ),
    path(
        '<uuid:application_student_id>/questions/',
        ApplicationStudentQuestionListApi.as_view(),
        name='question-list',
    ),
    path(
        '<uuid:application_student_id>/questions/<uuid:question_id>/retry/',
        ApplicationStudentQuestionRetryApi.as_view(),
        name='question-retry',
    ),
] + applications_student_routers.urls

clients_patterns = [] + clients_routers.urls

exam_patterns = [
    path(
        '<uuid:exam_id>/pdf-preview/',
        ExamPdfPreviewApi.as_view(),
        name='exam-pdf-preview',
    ),
    path(
        '<uuid:custom_page_id>/custom-page-pdf-preview/',
        ClientCustomPagePreviewApi.as_view(),
        name='custom-page-pdf-preview',
    ),
    path(
        '<uuid:exam_id>/print-config/',
        ExamPrintConfigUpdateApi.as_view(),
        name='exam-print-config-update',
    ),
    path(
        '<uuid:exam_id>/questions/<uuid:question_id>/print-config/',
        ExamQuestionPrintConfigUpdateApi.as_view(),
        name='exam-question-print-config-update',
    ),
    path(
        '<uuid:exam_id>/status/',
        ExamUpdateStatusApi.as_view(),
        name='exam-update-status',
    ),
]

bncc_patterns = [
    path('habilidade/<uuid:pk>/', abilities_apis.AbilityRetrieveAPIView.as_view(), name='ability_retrieve_api'),
    path('competencia/<uuid:pk>/', competences_apis.CompetenceRetrieveAPIView.as_view(), name='competence_retrieve_api'),
    path('topico/<uuid:pk>/', topics_apis.TopicRetrieveAPIView.as_view(), name='topic_retrieve_api'),
] + bncc_routers.urls
students_performance_patterns = [
    path('<uuid:pk>/general-performance/', students_apis.StudentGeneralPerformanceRetrieveAPIView.as_view(), name='student_general_performance_retrieve'),
]
user_patterns = [
    path(
        'super-prof/',
        TeacherSuperProfDataApi.as_view(),
        name='teacher-super-prof-data'
    ),
]
urlpatterns = [
    path(
        'subjects/tree/',
        SubjectTreeListView.as_view(),
        name='subject-tree-list-view',
    ),
    path(
        'subjects/tree/<uuid:pk>/',
        SubjectTreeDetailView.as_view(),
        name='subject-tree-detail-view',
    ),
    path(
        'exams-teacher-subject/files/',
        ExamTeacherSubjectFileUpload.as_view(),
        name='exam-teacher-subject-file-upload',
    ),
    path('user/', include((user_patterns, 'user'))),
    path('clients/', include((clients_patterns, 'clients'))),
    path('questions/', include((question_patterns, 'questions'))),
    path('exams/', include((exam_patterns, 'exams-api'))),
    path('exam/', include((exams_patterns, 'exams'))),
    path(
        'applications-student/',
        include((application_student_patterns, 'applications-student')),
    ),
    path('bncc/', include((bncc_patterns, 'bncc'))),
    path('desempenho/', include((students_performance_patterns, 'performance'))),
    path('search/', SearchView.as_view(), name='search-view'),
    path(
        'applications/<uuid:application_id>/deadline-correction-response-exceptions/',
        ApplicationDeadlineCorrectionResponseExceptionCreateDeleteAPIView.as_view(),
        name='application-deadline-correction-response-exception',
    ),
    path(
        'applications/<uuid:application_id>/deadline-correction-response-exceptions/<uuid:pk>/',
        ApplicationDeadlineCorrectionResponseExceptionCreateDeleteAPIView.as_view(),
        name='application-deadline-correction-response-exception-instance',
    ),
    path('teachers/', inspectors_api.TeacherListView.as_view(), name='teacher-list-view'),
    # path('super-search/', SuperSearchAPIView.as_view(), name='super-search'),
    path('feedback/onboarding/', FeedbackOnboardingAPIView.as_view(), name='feedback-generic'),
] + routers.urls