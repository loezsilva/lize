from rest_framework.views import APIView
from rest_framework.response import Response

from django.utils import timezone

from fiscallizeon.students.models import StudentSisuCourse
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

class StudentSisuCourseUpdateOrCreateAPIView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    
    def post(self, request, pk=None):
        user = self.request.user
        
        data = request.data
        
        try:
            instance, updated = StudentSisuCourse.objects.using('default').update_or_create(
                student=user.student, 
                year=data.get('year'),
                defaults={
                    "courses_ids": data.get('courses_ids'),
                    "states": data.get('states')
                },
            )
            
        except Exception as e:
            print(e)
        
        return Response({
            "courses_ids": data.get('courses_ids'),
            "states": data.get('states')
        })
    
class StudentSisuCourseAPIView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    
    def get(self, request, pk=None):
        user = self.request.user
        course_id = None
        
        try:
            instance = StudentSisuCourse.objects.get(student=user.student, year=timezone.localtime(timezone.now()).year)
            course_id = instance.course_id
        except:
            pass
        
        return Response(course_id)