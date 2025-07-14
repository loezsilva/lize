from django.urls import include, path

from fiscallizeon.applications.api2 import (
    application as application_api,
    application_student as application_student_api,
)
from fiscallizeon.bncc.api2 import (
    abiliity as abiliity_api,
    competence as competence_api,
)
from fiscallizeon.exams.api2 import (
    exam as exam_api,
    exam_question as exam_question_api,
    exam_teacher_subject as exam_teacher_subject_api,
)
from fiscallizeon.accounts.api2 import accounts as accounts_api
from fiscallizeon.students.api2 import students as students_api
from fiscallizeon.classes.api2 import school_classes as school_classes_api
from fiscallizeon.clients.api2 import school_coordination as school_coordionation_api
from fiscallizeon.clients.api2 import coordination_member as coordination_member_api
from fiscallizeon.subjects.api2 import (
    topic as topic_api,
    subjects as subject_api,
)
from fiscallizeon.inspectors.api2 import inspector as inspector_api
from fiscallizeon.clients.api2 import unity as unity_api
from fiscallizeon.questions.api2 import (
    base_text as base_text_api,
    question as question_api,
)
from fiscallizeon.accounts.api2 import sso as sso_api
from fiscallizeon.accounts.api2 import two_factor 

from fiscallizeon.dashboards.apis import dashs as dashboards_api

from fiscallizeon.core.api import permissions as permissions_api

from rest_framework.routers import DefaultRouter

app_name = 'api2'

router = DefaultRouter()
router.register(r'users', accounts_api.UsersViewSet, basename="users")
router.register(r'sso', sso_api.SSOViewSet, basename='sso')
router.register(r'students', students_api.StudentsViewSet, basename="students")
router.register(r'teachers', inspector_api.InspectorViewSet, basename="inspectors")
router.register(r'permissions', permissions_api.PermissionsViewSet, basename="permissions")
# router.register(r'dashboards', dashboards_api.DashboardsViewSet, basename="dashboards")
# router.register(r'dashboards_chart', dashboards_api.DashboardsChartViewSet, basename="dashboards-chart")


urlpatterns = [
    path('', include(router.urls)),
    path('abilities/', abiliity_api.AbiliityListView.as_view()),
    path('applications/', application_api.ApplicationListView.as_view()),
    path('application-students-answers/', application_student_api.ApplicationStudentAnswerListView.as_view()),
    path('application-students-results/', application_student_api.ApplicationStudentResultListView.as_view()),
    path('base-texts/', base_text_api.BaseTextListView.as_view()),
    path('classes/', school_classes_api.SchoolClassListView.as_view()),
    path('series/', school_classes_api.GradeListView.as_view()),
    path('classes/<uuid:pk>/', school_classes_api.SchoolClassDetailView.as_view()),
    path('competences/', competence_api.CompetenceListView.as_view()),
    path('coordinations/', school_coordionation_api.SchoolCoordinationListView.as_view()),
    path('coordinations/members/', coordination_member_api.UserCoordinationMemberListAPIView.as_view()),
    path('coordinations/members/add/', coordination_member_api.UserCoordinationMemberCreateAPIView.as_view()),
    path('coordinations/members/user/<uuid:pk>/disable/', coordination_member_api.UserCoordinationMemberDisableAPIView.as_view(), name='disable-coordination-member'),
    path('coordinations/members/user/<uuid:pk>/activate/', coordination_member_api.UserCoordinationMemberActivateAPIView.as_view(), name='activate-coordination-member'),
    path('coordinations/members/<uuid:pk>/remove/', coordination_member_api.CoordinatiomMemberDestroyAPIView.as_view()),
    path('coordinations/members/check-inspector-association/', coordination_member_api.CheckInspectorAssociationAPI.as_view(), name='check-inspector-association-api'),
    path('inspector/check-coordination-association/', inspector_api.CheckCoordinationAssociationAPI.as_view(), name='check-coordination-association-api'),
    path('exams/', exam_api.ExamListView.as_view()),
    path('exam-questions/', exam_question_api.ExamQuestionListView.as_view()),
    path('exam-teachers-subjects/', exam_teacher_subject_api.ExamTeacherSubjectListView.as_view()),
    path('questions/', question_api.QuestionListView.as_view()),
    path('exam-teachers-subjects/questions/select/', question_api.QuestionSelectListView.as_view(), name='select-questions'),
    path('exam-teachers-subjects/questions/select/v2/', question_api.QuestionSelectExamElaborationListView.as_view(), name='select-questions-v2'),
    path('exam-teachers-subjects/questions/select/<uuid:pk>/', question_api.QuestionSelectRetrieveAPIView.as_view(), name='select-questions-detail'),
    path('exam-teachers-subjects/questions/count/', question_api.QuestionCountView.as_view(), name='count-questions'),
    path('exam-teacher-subject/data/<uuid:pk>/', exam_teacher_subject_api.ExamTeacherSubjectRetrieveAPIView.as_view(), name='exam-teacher-data'),
    path('subjects/', subject_api.SubjectListView.as_view(), name='subjects'),
    path('topics/', topic_api.TopicListView.as_view()),
    path('units/', unity_api.UnityListView.as_view()),
    path('api/send_two_factor_code/', two_factor.SendTwoFactorCodeAPIView.as_view(), name='send_two_factor_code'),
    path('api/verify_two_factor_code/', two_factor.VerifyTwoFactorCodeAPIView.as_view(), name='verify_two_factor_code'),

]