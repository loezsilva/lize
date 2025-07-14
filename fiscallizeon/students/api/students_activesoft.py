from django.conf import settings
from django.db.models import Q
from django.db.models.functions import Length

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from fiscallizeon.students.models import Student
from fiscallizeon.parents.models import Parent
from fiscallizeon.core.utils import CheckHasPermission
from django.contrib.auth.mixins import LoginRequiredMixin
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from rest_framework import serializers


class StudentNoteCompositionAPIView(LoginRequiredMixin, CheckHasPermission, ListAPIView):
    """
        API criada unicamente para a sincronização de alunos pela Activesoft
    """
    class StudentSerializer(serializers.ModelSerializer):
        classe = serializers.SerializerMethodField()
        class Meta:
            model = Student
            fields = ['id', 'name', 'id_erp', 'classe', 'enrollment_number']
            ref_name = 'student_activesoft'
        
        def get_classe(self, obj):
            if classe := obj.get_last_class():
                return classe.id
            return None
        
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    required_permissions = [settings.COORDINATION]
    authentication_classes = [CsrfExemptSessionAuthentication]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        user = self.request.user
        classes = self.request.GET.getlist('classe')
        
        queryset = queryset.filter(
            client__in=user.get_clients_cache(),
            id_erp__isnull=False,
            classes__in=classes,
        )
        
        return queryset