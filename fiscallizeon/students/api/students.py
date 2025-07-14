from django.conf import settings
from django.db.models import Q, F
from django.db.models.functions import Length
from django.contrib import messages

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from fiscallizeon.students.models import Student
from fiscallizeon.parents.models import Parent
from fiscallizeon.core.utils import CheckHasPermission
from django.contrib.auth.mixins import LoginRequiredMixin
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer

import json


class StudentApiListView(LoginRequiredMixin, CheckHasPermission, APIView):
    renderer_classes = [JSONRenderer]
    required_permissions = [settings.COORDINATION]
    def get(self, request, format=None):
        term = request.GET.get("term", "") 

        students = Student.objects.filter(
            Q(name__icontains=term)
        ).order_by(Length('name').asc())

        data = {
            "results": [],
            "pagination": {
                "more": False
            }
        }

        for student in students:
            data['results'].append(
                {
                    "id": student.pk,
                    "text": student.name 
                },
            )

        return Response(data)
    
class StudentSendEmailToParentAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    renderer_classes = [JSONRenderer]
    required_permissions = [settings.COORDINATION]
    authentication_classes = [CsrfExemptSessionAuthentication]
    
    def post(self, request):
        data = request.data
        responsible_email = data.get('responsible_email')
        
        parent, created = Parent.objects.get_or_create(
            email=responsible_email
        )
        if not created:
            parent.send_mail_to_first_access()
        
        return Response(f"E-mail enviado para o {responsible_email}")
    

class StudentGetApplications(LoginRequiredMixin, CheckHasPermission, APIView):
    required_permissions = [settings.STUDENT]
    authentication_classes = [CsrfExemptSessionAuthentication]
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    
    def get(self, request):
        user = self.request.user
        student = user.student
        
        applications = student.get_finished_application_student().annotate(
            date=F('application__date'),
            exam_name=F('application__exam__name'),
            exam_id=F('application__exam__id'),
        )
        
        return Response(applications.values('id', 'date', 'exam_id', 'exam_name'))

class StudentDeactivate(LoginRequiredMixin, CheckHasPermission, APIView):
    required_permissions = [settings.COORDINATION]
    authentication_classes = [CsrfExemptSessionAuthentication]

    def post(self, request, student_pk):
        student = Student.objects.get(id=student_pk)
        student.switch_student_status()

        if not student.user.is_active:
            messages.success(request, f'O aluno "{student.name}" foi desativado com sucesso!')
        else:
            messages.success(request, f'O aluno "{student.name}" foi ativado com sucesso!')

        return Response(request.META.get("HTTP_REFERER"))
    
class StudentsMassiveResetPasswordView(LoginRequiredMixin, CheckHasPermission, APIView):
    required_permissions = [settings.COORDINATION]
    authentication_classes = [CsrfExemptSessionAuthentication]
    renderer_classes = [JSONRenderer]

    def post(self, request):
        body = json.loads(request.body)
        client = request.user.client
        students_ids = body.get('students_ids', [])

        if not students_ids:
            messages.error(request, "Nenhum ID de aluno fornecido.")
            return Response({"detail": "Nenhum ID de aluno fornecido."}, status=status.HTTP_400_BAD_REQUEST)
        
        students = Student.objects.filter(id__in=students_ids, client=client)

        if not students:
            messages.error(request, "Nenhum aluno encontrado.")
            return Response({"detail":  "Nenhum aluno encontrado."}, status=status.HTTP_404_NOT_FOUND)
        
        counter = 0

        for student in students:

            if student.user:
                student.user.set_password(student.email)
                student.user.must_change_password = True
                student.user.save()
                counter += 1
        
        if len(students) > 1:
            return Response({"detail": f"{counter} senhas de alunos foram resetadas com sucesso!"}, status=status.HTTP_200_OK)

        return Response({"detail": f"A senha do aluno foi resetada com sucesso!"}, status=status.HTTP_200_OK)

students_list_api = StudentApiListView.as_view()
students_massive_reset_password = StudentsMassiveResetPasswordView.as_view()