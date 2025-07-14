import json
import requests

from django.http.response import HttpResponse, JsonResponse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from django.utils import timezone

from fiscallizeon.exams.models import Exam
from fiscallizeon.integrations.models import NotesMigrationProof, Integration
from fiscallizeon.students.models import Student
from django.utils.crypto import get_random_string

class CheckSincronizationUnities(APIView):
    render_classes = JsonResponse
    authentication_classes = [CsrfExemptSessionAuthentication]

    def post(self, request):
        data = request.data.get('unities') if isinstance(request.data, dict) and request.data.get('unities') else request.data
        token = request.data.get('token') if isinstance(request.data, dict) else None
        user = self.request.user
        client = user.client
        integration = client.integration
        unities = client.unities.filter(id_erp__in=data)
        
        if integration.erp == Integration.ACTIVESOFT:
            sincronizeds = list(unities.filter(integration_token=token).values_list('id_erp', flat=True))
        else:
            sincronizeds = list(unities.values_list('id_erp', flat=True))
        
        return Response(sincronizeds)
    
class CheckSincronizationStudents(APIView):
    render_classes = JsonResponse
    authentication_classes = [CsrfExemptSessionAuthentication]

    def post(self, request):
        data = request.data
        sincronizeds = list(self.request.user.get_clients().first().student_set.filter(id_erp__in=data).values_list('id_erp', flat=True))
        
        return Response(sincronizeds)
    
class CheckSincronizationClasses(APIView):
    render_classes = JsonResponse
    authentication_classes = [CsrfExemptSessionAuthentication]

    def post(self, request):
        
        data = request.data.get('school_classes') if isinstance(request.data, dict) and request.data.get('school_classes') else request.data
        token = request.data.get('token') if isinstance(request.data, dict) else None
        user = self.request.user
        client = user.client
        integration = client.integration
        
        sincronizeds = SchoolClass.objects.filter(
            id_erp__in=data,
            school_year=timezone.now().year, 
            coordination__unity__client=client
        )

        if integration.erp == Integration.ACTIVESOFT:
            sincronizeds = sincronizeds.filter(integration_token=token)
            itinerary_bools = list(sincronizeds.values_list('is_itinerary', flat=True))
            sincronizeds = list(sincronizeds.values_list('id_erp', flat=True))
            return Response(list(zip(sincronizeds, itinerary_bools)))
        else:
            return Response(list(sincronizeds.values_list('id_erp', flat=True)))

        
class CheckSincronizationIntership(APIView):
    render_classes = JsonResponse
    authentication_classes = [CsrfExemptSessionAuthentication]

    def post(self, request):
        data = request.data.get('interships') if isinstance(request.data, dict) and request.data.get('interships') else request.data
        token = request.data.get('token') if isinstance(request.data, dict) else None
        user = self.request.user
        client = user.client
        integration = client.integration
        sincronizeds = []
        
        school_classes = SchoolClass.objects.filter(
            coordination__in=self.request.user.get_coordinations_cache(),
            integration_token=token if integration.erp == Integration.ACTIVESOFT else None
        )
        
        for _intership in data:
            intership = school_classes.filter(
                id_erp=str(_intership['turma_id']), 
                students__id_erp=str(_intership['aluno_id']),
                students__integration_token=token if integration.erp == Integration.ACTIVESOFT else None
            ).first()
            
            if intership:
                sincronizeds.append(_intership)
                
        return Response(sincronizeds)

class NotesMigrationProofCreate(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]

    def post(self, request):
        proofs = request.data.get('proofs')
        user = self.request.user
        integration = user.client.integration
        for proof_data in proofs:
            exam = Exam.objects.get(pk=proof_data['exam'])
            students_data = proof_data['students']
            students_pks = [student['pk'] for student in students_data]
            students = Student.objects.filter(pk__in=students_pks)
            
            data = {
                'code': get_random_string(8),
                'created_by': user,
                'exam': exam,
                'migration_json': []
            }

            for student in students_data:

                data['migration_json'].append({
                    'notas': student['composition']['notas'] if integration.erp == Integration.ACTIVESOFT or integration.erp == Integration.ATHENAWEB else student['composition']['valor'],
                    'relation': student['relation'],
                    'errors': student['errorMessage']
                })

            proof = NotesMigrationProof.objects.create(**data)
            proof.students.set(students)

        return Response("Comprovante de migração cadastrado")


class CheckStudentsToClearSchoolClassesAPIView(APIView):
    render_classes = JsonResponse
    authentication_classes = [CsrfExemptSessionAuthentication]

    def post(self, request):
        token = request.GET.get('token')
        students_id_erps = request.data
        students = Student.objects.filter(
            user__is_active=True,
            classes__isnull=False,
            classes__school_year=timezone.now().year,
            id_erp__isnull=False,
            integration_token=token,
        ).exclude(
            id_erp__in=students_id_erps
        ).distinct()
                
        return Response(students.values('id', 'name', 'email', 'enrollment_number')) 
    

class clearStudentsSchoolClassesAPIView(APIView):
    render_classes = JsonResponse
    authentication_classes = [CsrfExemptSessionAuthentication]

    def post(self, request):
        students_ids = request.data
        students = Student.objects.filter(
            id__in=students_ids
        ).distinct()
        
        for student in students:
            for classe in student.classes.filter(school_year=timezone.now().year):
                classe.students.remove(student)
        
        return Response() 