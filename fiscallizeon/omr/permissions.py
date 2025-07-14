from rest_framework import permissions

class IsOMRUploadOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        object_coordinations = obj.user.get_coordinations()
        user_coordinations = request.user.get_coordinations()
        return any(x in object_coordinations for x in user_coordinations)