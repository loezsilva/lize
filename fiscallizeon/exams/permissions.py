from rest_framework import permissions
from django.conf import settings

class IsTeacherSubject(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.user_type == settings.TEACHER:
            return True

        return False

class IsCoordinationExamQuestion(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_authenticated and user.user_type == settings.COORDINATION:
            return len(obj.exam.coordinations.all().intersection(user.get_coordinations())) > 0
        
        return False
    
class IsCoordinationExamOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_authenticated:
            return len(obj.coordinations.all().intersection(user.get_coordinations())) > 0
        
        return False

class IsTeacherSubjectExamQuestion(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_authenticated and user.user_type == settings.TEACHER:
            return obj.exam_teacher_subject.teacher_subject.subject in user.inspector.subjects.all()

        return False