from django.utils import timezone

from rest_framework import generics, permissions, status

from fiscallizeon.core.permissions import IsStudentUser
from fiscallizeon.core.utils import CamelCaseAPIMixin

from .serializers import ColleagueSerializer


class ColleagueListView(CamelCaseAPIMixin, generics.ListAPIView):
    serializer_class = ColleagueSerializer
    permission_classes = (permissions.IsAuthenticated, IsStudentUser,)

    def get_queryset(self):
        school_class = self.request.user.student.classes.filter(school_year=timezone.now().year).first()
        return school_class.students.exclude(pk=self.request.user.student.pk)
