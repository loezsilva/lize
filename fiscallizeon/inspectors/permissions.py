from rest_framework.permissions import BasePermission

class IsInspectorOwner(BasePermission):

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        user_client = request.user.client

        if obj.user:
            return obj.user.client == user_client

        coordination = obj.coordinations.all().first()
        if coordination:
            return coordination.unity.client == user_client

        return False