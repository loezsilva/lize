from rest_framework import permissions
from django.conf import settings

class IsStudentOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        user = request.user
        return not obj.application.is_happening and obj.student.user == user


class IsCoordinationMember(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.user_type == settings.COORDINATION:
            if obj.student.user:
                if not obj.student.user.get_coordinations(obj.application.date.year):
                    return True
                return len(obj.student.user.get_coordinations(obj.application.date.year).intersection(user.get_coordinations())) > 0
            else:
                return obj.student.client.pk in user.get_clients_cache()

        return False

class IsCoordinationMemberCanSeeAll(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.user_type == settings.COORDINATION:
            return user.can_see_all() and obj.student.client.pk in user.get_clients_cache()
        return False

class IsTeacherSubject(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.user_type == settings.TEACHER:
            return True

        return False