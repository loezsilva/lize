from django.db.models import Prefetch

from rest_framework import generics, permissions, status

from fiscallizeon.applications.models import Application
from fiscallizeon.core.permissions import IsStudentUser, CanAccessApp
from fiscallizeon.core.utils import CamelCaseAPIMixin
from fiscallizeon.exams.models import ExamTeacherSubject
from fiscallizeon.inspectors.models import TeacherSubject

from .serializers import ApplicationSerializer


class ApplicationDetailView(CamelCaseAPIMixin, generics.RetrieveAPIView):
    # queryset = Application.objects.select_related('exam').prefetch_related('exam__examquestion_set')
    serializer_class = ApplicationSerializer
    # permission_classes = (permissions.IsAuthenticated, IsStudentUser, CanAccessApp,)
    required_scopes = ['read']

    def get_queryset(self):
        print('<ApplicationDetailView> get queryset')
        # teacher_subject_prefetch = Prefetch(
        #     'teacher_subject',
        #     queryset=TeacherSubject.objects.select_related('teacher', 'subject')
        # )
        # exam_teacher_subject_prefetch = Prefetch(
        #     'exam__examteachersubject_set',
        #     queryset=ExamTeacherSubject.objects.prefetch_related(
        #         'examquestion_set',
        #         teacher_subject_prefetch,
        #     )
        # )

        return Application.objects.select_related('exam').prefetch_related(
            'exam__examteachersubject_set',
            # 'exam__examteachersubject_set__examquestion_set',
            # 'exam__examteachersubject_set__teacher_subject',
            # 'exam__examteachersubject_set__teacher_subject__teacher',
            # 'exam__examteachersubject_set__teacher_subject__subject',
            # 'inspectors_teachersubject',
        )
        # return Application.objects.select_related('exam').prefetch_related('examteachersubject_set')

        # .prefetch_related(
        #     'books',
        #     'books__chapters'
        # )
