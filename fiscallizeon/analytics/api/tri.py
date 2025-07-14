import csv
import tempfile
import requests

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication

from django.conf import settings
from django.http import HttpResponse

from fiscallizeon.analytics.api.serializers.tri import TriSerializer, SisuMetadataSerializer, SisuSerializer, ItemsParamsSerializer
from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication
from fiscallizeon.core.gcp.utils import get_service_account_oauth2_token
from fiscallizeon.applications.models import Application
from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.exams.models import Exam

    
class TriAPIView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, TokenAuthentication, )

    def post(self, request, format=None):
        is_student = request.user.user_type == settings.STUDENT
        serializer = TriSerializer(data=request.data)
        if serializer.is_valid():
            applications = Application.objects.filter(exam__in=serializer.data.get('exams')).order_by('date')
            
            #Verificando se o aluno está acessando informações dele mesmo
            if is_student:
                if len(serializer.data.get('students', [])) != 1:
                    return Response(status=status.HTTP_400_BAD_REQUEST)

                if Student.objects.get(pk__in=serializer.data.get('students', [])).user != request.user:
                    return Response(status=status.HTTP_400_BAD_REQUEST)

            if not applications:
                return Response(
                    {'message': 'Aplicações não encontradas para os cadenos informados'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            response = requests.post(
                settings.ANALYTICS_SERVICE_URL + '/tri',
                json=serializer.data
            )
            try:
                response_json = response.json()
                if is_student:
                    if not any(Exam.objects.filter(pk__in=serializer.data['exams']).values_list('show_ranking', flat=True)):
                        for knowledge_area in response_json['students'][0]['knowledge_areas']:
                            knowledge_area['ranking'] = None

                return Response(response_json)
            except Exception as e:
                print("Erro ao obter dados TRI:", e)
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ExportTriCsvAPIView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, TokenAuthentication, )

    def post(self, request, format=None):
        serializer = TriSerializer(data=request.data)

        areas_initials = {
            'cbafbbba-323e-4e46-be76-abcb5c537490': 'CN',
            'b9eceae4-855a-40f9-9f5e-aa8c942485b2': 'CH',
            '990d414c-ebd1-49f1-a185-005c229178d5': 'MT',
            '41c911a2-9597-4c8f-8e8f-178749fc11db': 'LC',
        }

        if serializer.is_valid():
            applications = Application.objects.filter(exam__in=serializer.data.get('exams')).order_by('date')
            
            if not applications:
                return Response(
                    {'message': 'Aplicações não encontradas para os cadenos informados'}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            response = requests.post(
                settings.ANALYTICS_SERVICE_URL + '/tri',
                json=serializer.data
            )

            try:
                json_response = response.json()
                tmp_file = tempfile.NamedTemporaryFile()

                with open(tmp_file.name, 'w+') as csvfile:
                    fieldnames = ['Nome', 'Matricula', 'Turma', 'Unidade', 'Area', 'Nota', 'Acertos']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for entry in json_response['students']:
                        student = Student.objects.get(pk=entry['student_id'])
                        school_class = SchoolClass.objects.get(pk=entry['school_class_id'])
                        for area in entry['knowledge_areas']:
                            writer.writerow({
                                'Nome': entry['student_name'],
                                'Matricula': student.enrollment_number,
                                'Turma': school_class.name,
                                'Unidade': school_class.coordination.unity.name,
                                'Area': areas_initials.get(area['id'], area['name']),
                                'Nota': area['grade'].replace(".", ","),
                                'Acertos': area['correct_count']
                            })

                with open(tmp_file.name, 'rb') as csvfile:
                    response = HttpResponse(csvfile, content_type='text/csv')
                    response['Content-Disposition'] = 'attachment; filename="dados-tri.csv"'
                    return response
            except Exception as e:
                print("Erro ao exportar TRI em CSV:", e)
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SisuDataAPIView(APIView):
    authentication_classes = []
    permission_classes = []
    
    def post(self, request, format=None):
        serializer = SisuMetadataSerializer(data=request.data)
        
        if serializer.is_valid():
            auth_token = get_service_account_oauth2_token(settings.ANALYTICS_SERVICE_URL)
            headers = {"Authorization": f"Bearer {auth_token}"}

            year = serializer.data.get('year')
            response = requests.post(
                settings.ANALYTICS_SERVICE_URL + f'/sisu-data?year={year}',
                headers=headers,
                json=serializer.data
            )
            
            return Response(response.json())
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SisuAPIView(APIView):
    permission_classes = []
    authentication_classes = (CsrfExemptSessionAuthentication, TokenAuthentication, )

    def post(self, request, format=None):
        serializer = SisuSerializer(data=request.data)
        if serializer.is_valid():
            auth_token = get_service_account_oauth2_token(settings.ANALYTICS_SERVICE_URL)
            headers = {"Authorization": f"Bearer {auth_token}"}

            year = serializer.data.get('year')
            response = requests.post(
                settings.ANALYTICS_SERVICE_URL + f'/sisu?year={year}',
                headers=headers,
                json=serializer.data
            )
            
            return Response(response.json())
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ItemsParamsAPIView(APIView):
    permission_classes = []
    authentication_classes = (CsrfExemptSessionAuthentication, TokenAuthentication, )

    def post(self, request, format=None):
        serializer = ItemsParamsSerializer(data=request.data)
        if serializer.is_valid():
            auth_token = get_service_account_oauth2_token(settings.ANALYTICS_SERVICE_URL)
            headers = {"Authorization": f"Bearer {auth_token}"}

            response = requests.post(
                settings.ANALYTICS_SERVICE_URL + '/items',
                headers=headers,
                json=serializer.data
            )
            
            return Response(response.json())
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)