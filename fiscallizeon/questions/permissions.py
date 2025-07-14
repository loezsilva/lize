from rest_framework import permissions

from django.db.models import Q
from django.utils import timezone

from fiscallizeon.applications.models import Application

class IsStudentOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        user = request.user
        now = timezone.make_naive(timezone.now().astimezone())
        if hasattr(user, 'student'):
            applications = Application.objects.filter(
                exam__isnull=False,
                date__gte=now.date(),
                end__gte=now.time(),
                exam__in=obj.exams.all(),
            )
            return not applications.exists()
        return False