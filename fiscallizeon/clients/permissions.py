from django.conf import settings
from rest_framework import permissions

from fiscallizeon.applications.models import ApplicationStudent
class IsCoordinationMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        application_student_pk = request.GET.get('application_student', None)
        
        questions_coordinations = obj.coordinations.all()
        all_coordinations = questions_coordinations

        if application_student_pk:
            exam = ApplicationStudent.objects.get(pk=application_student_pk).application.exam
            exam_coordinations = exam.coordinations.all()
            all_coordinations = questions_coordinations.union(exam_coordinations)

        if user.user_type == settings.COORDINATION:
            return len(all_coordinations.intersection(user.get_coordinations())) > 0

        return False

class IsInspectorMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.user_type == settings.INSPECTOR:
            return len(obj.coordinations.all().intersection(user.get_coordinations())) > 0

        return False