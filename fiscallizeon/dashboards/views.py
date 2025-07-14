import io
import csv
import uuid

from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import TemplateView
from fiscallizeon.applications.managers import ApplicationStudentQuerySet
from fiscallizeon.students.models import Student
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.clients.models import Unity, TeachingStage
from fiscallizeon.exams.models import Exam
from fiscallizeon.applications.models import Application, ApplicationStudent
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
import requests
from django.conf import settings
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny
from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication
from django.contrib.auth.mixins import LoginRequiredMixin
import logging
logger = logging.getLogger('')


class GetDataFromServiceAPIView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, TokenAuthentication, )
    external_exam = None
    
    def get_authenticators(self):
        referer = self.request.META.get('HTTP_REFERER', '')
        if 'externo' in referer:
            # caso o acesso seja externo, verificar que a origem possui uma pk de application_student no final da url
            # isso garante que se um usuário malicioso acessar a url não possa acessar dados diferentes daquele application_student, que já é público de qualquer forma
            url_bits = referer.split('/')
            applications_student_pk = url_bits[-2]

            if not applications_student_pk or not ApplicationStudent.objects.filter(pk=applications_student_pk).exists():
                return super().get_authenticators()
            else:
                self.external_exam = str(ApplicationStudent.objects.get(pk=applications_student_pk).application.exam.id)
                return []

        return super().get_authenticators()
    
    def get_permissions(self):
        referer = self.request.META.get('HTTP_REFERER', '')
        if 'externo' in referer:
            url_bits = referer.split('/')
            applications_student_pk = url_bits[-2]
            if not applications_student_pk or not ApplicationStudent.objects.filter(pk=applications_student_pk).exists():
                return super().get_permissions()
            else:
                return [AllowAny()]
            
        return super().get_permissions()

    def post(self, request, client_pk, format=None):
        data = request.data

        if data['who'] == 'student' and self.external_exam:
            data['what_ids'] = [self.external_exam] # um acesso externo sempre deve consultar o caderno do application_student

        response = requests.post(
            settings.ANALYTICS_SERVICE_URL + f'/dashboards/get_data/{client_pk}/',
            json=data
        )

        try:
            if response.status_code <= 300:
                return Response(response.json())
            else:
                logger.exception(f"A API dos dashs retornou: {response.text}")
                return Response(response.text, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print("Erro ao obter dados dos dashs:", e)
            logger.exception(f"Erro ao obter dados dos dashs: {repr(e)}")
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DashboardsTemplateView(LoginRequiredMixin, TemplateView):
    who = None

    def dispatch(self, request, *args, **kwargs):
        who = request.GET.get('who')
        
        whos = {
            'alunos': 'student', 
            'student': 'student',
            'turmas': 'classe', 
            'classe': 'classe',
            'escola': 'school', 
            'school': 'school',
            'professores': 'teacher',
            'teacher': 'teacher',
            'exam': 'school',
            'exams': 'school',
            'cadernos': 'school',
        }
        
        self.who = whos[who] if who else None
        
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        if self.who:
            return 'dashboards/details/generic.html'
        return 'dashboards/details/school.html'
    
    def get_object(self):
        who_id = self.request.GET.get('who_id')

        if self.who == 'student':
            return Student.objects.get(pk=who_id)
        elif self.who == 'classe':
            return SchoolClass.objects.get(pk=who_id)
        elif self.who == 'teacher':
            return Inspector.objects.get(pk=who_id)
        
        return self.request.user.client
    
    def get_context_data(self, **kwargs):
        
        user = self.request.user
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_object()
        context["who"] = self.who
        context["who_id"] = self.request.GET.get('who_id')
        context["what"] = self.request.GET.get('what')
        context["what_ids"] = self.request.GET.get('what_ids')
        context["period"] = self.request.GET.get('period')
        
        context["unities"] = Unity.objects.filter(
            Q(coordinations__in=user.get_coordinations_cache()),
        ).distinct()
        
        return context
        

class GenerateLinksView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, TokenAuthentication, )
    exam_possibilities = ["exam", "exams", "cadernos"]
    whos_dict = {
            'alunos': 'student', 
            'student': 'student',
            'turmas': 'classe', 
            'classe': 'classe',
            'escola': 'school', 
            'school': 'school',
            'professores': 'teacher',
            'teacher': 'teacher',
            'exam': 'school',
            'exams': 'school',
            'cadernos': 'school',
        }

    def generate_csv_and_response(self, applications_students_queryset):
        buffer = io.StringIO()

        writer = csv.DictWriter(buffer, fieldnames=['Nome', 'Link', 'Unidade', 'Turma'])
        writer.writeheader()

        application_student: ApplicationStudent
        for application_student in applications_students_queryset:
            link = settings.BASE_URL + reverse('dashboards:student-followup', kwargs={'application_student_pk': application_student.pk})
            school_class = application_student.get_last_class_student()
            writer.writerow({
                'Nome': application_student.student.name,
                'Link': link,
                'Unidade': school_class.coordination.unity.name if school_class else 'Unidade não encontrada',
                'Turma': school_class.name if school_class else 'Turma não encontrada',
            })

        response = Response(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="links-students.csv"'
        buffer.close()

        return response

    def post(self, request, client_pk, format=None):
        data = request.data
        who = data.get('who')
        who = self.whos_dict[who] if who else None
        who_ids = data.get('who_ids')
        what = data.get('what')
        what_ids = data.get('what_ids')

        if not what or what not in self.exam_possibilities:
            # tratar caso em que não seja enviado um caderno válido
            return Response(status=status.HTTP_400_BAD_REQUEST, )
            
        if who and who == 'school' and what == 'exams':
            # Caso em que um caderno é pesquisado diretamente, sem turma
            applications = Application.objects.filter(exam=what_ids[0]).first()
            applications_students_queryset = ApplicationStudent.objects.filter(application=applications).order_by('student__name')
            
            response = self.generate_csv_and_response(applications_students_queryset)

            return response

        # Encontrar uma aplicação para gerar os links para cada aluno
        applications = Application.objects.filter(exam=what_ids[0], school_classes=who_ids[0]).first()
        applications_students_queryset = ApplicationStudent.objects.filter(application=applications).order_by('student__name')
        response = self.generate_csv_and_response(applications_students_queryset)

        return response

class StudentFollowupView(TemplateView):
    application_student = None
    who = None
    what = None

    def dispatch(self, request, *args, **kwargs):
        self.application_student = get_object_or_404(ApplicationStudent, pk=kwargs.get("application_student_pk"))
        
        self.who = self.application_student.student
        self.what = self.application_student.application.exam

        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        return 'dashboards/details/student.html'
    
    def get_object(self, **kwargs):
        return self.who
    
    def get_context_data(self, **kwargs):
        
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_object()
        context["who"] = "student"
        context["who_id"] = str(self.who.id)
        context["what"] = "exams"
        context["exam"] = self.what
        context["what_id"] = str(self.what.id)
        context["period"] = self.request.GET.get('period')
        context["user"] = self.who # setando o user como aluno apenas para pegar o cliente no template sem precisar de usuário
        
        context["unities"] = Unity.objects.filter(
            Q(coordinations__in=self.what.coordinations.all()),
        ).distinct()
        
        return context