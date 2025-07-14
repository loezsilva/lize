from rest_framework.generics import RetrieveAPIView
from fiscallizeon.analytics.api.serializers.application_student import ApplicationStudentGeneralPerformanceSerialize

from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication

    
class StudentGeneralPerformanceRetrieveAPIView(RetrieveAPIView):
    model = ApplicationStudent
    queryset = ApplicationStudent.objects.all()
    serializer_class = ApplicationStudentGeneralPerformanceSerialize
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['classes'] = self.request.GET.get('classes').split(',') if self.request.GET.get('classes') else []
        context['unities'] = self.request.GET.get('unities').split(',') if self.request.GET.get('unities') else []
        context['q_subjects'] = self.request.GET.getlist('q_subjects') if self.request.GET.get('q_subjects') else None
        
        return context

    