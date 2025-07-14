from rest_framework import permissions

from django.conf import settings

class IsOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        return request.user and obj.student_application.student.user == request.user

class IsTeacherSubject(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.user_type == settings.TEACHER:
            return True

        return False
