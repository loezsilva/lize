import json

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db import transaction

from fiscallizeon.answers.models import SumAnswer
from fiscallizeon.questions.models import Question
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.answers.serializers.sum_answers import SumAnswerSerializer
from fiscallizeon.core.utils import CheckHasPermissionAPI
from fiscallizeon.answers.models import SumAnswer, SumAnswerQuestionOption, QuestionOption
class SumAnswerUpdateView(APIView):
    required_permissions = [settings.TEACHER, settings.COORDINATION]
    permission_classes = [CheckHasPermissionAPI]
    authentication_classes = (CsrfExemptSessionAuthentication, TokenAuthentication, )

    def post(self, request, format=None):
        serializer = SumAnswerSerializer(data=request.data)

        if serializer.is_valid():
            question = Question.objects.filter(pk=serializer.data.get('question'))
            application_student = ApplicationStudent.objects.filter(pk=serializer.data.get('application_student'))

            if not question or not application_student:
                return Response({"erro": "Aplicação ou questão não encontrada(s)"}, status=status.HTTP_400_BAD_REQUEST)

            sum_answer, created = SumAnswer.objects.update_or_create(
                question=question.first(),
                student_application=application_student.first(),
                defaults={
                    'empty': False,
                    'value': serializer.data.get('sum_value'),
                    'created_by': request.user, 
                }
            )

            if not created:
                sum_answer.question_options.clear()

            sum_answer.create_sum_option_answers()
            sum_answer.grade = sum_answer.get_grade_proportion()
            sum_answer.save()

            data = {**serializer.data}
            data['grade'] = sum_answer.grade
            data['created_by'] = sum_answer.created_by_id
            data['created_by_name'] = sum_answer.created_by.name
            data['created_at'] = sum_answer.updated_at
            data['sum_question_sum_value'] = sum_answer.value
            data['checked_answers'] = list(sum_answer.sumanswerquestionoption_set.filter(checked=True).values_list('question_option_id', flat=True))

            return Response(data=data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class SumAnswerDeleteAPIView(CheckHasPermissionAPI, generics.DestroyAPIView):
    queryset = SumAnswer.objects.all()
    authentication_classes = (CsrfExemptSessionAuthentication, )

class SumAnswerCreateUpdateView(CheckHasPermissionAPI, generics.RetrieveUpdateAPIView):
    required_permissions = [settings.STUDENT,]
    permission_classes = [CheckHasPermissionAPI]
    authentication_classes = (CsrfExemptSessionAuthentication, TokenAuthentication, )

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            student_application_id = data.get("student_application")
            question_id = data.get("question")
            question_option_checked_ids = data.get("question_option_checked", []) 
            value = data.get("value", 0)

            if not all([student_application_id, question_id]):
                return JsonResponse({"error": "Parâmetros obrigatórios ausentes."}, status=400)

            question = Question.objects.filter(pk=question_id)
            application_student = ApplicationStudent.objects.filter(pk=student_application_id)

            sum_answer, created = SumAnswer.objects.update_or_create(
                question=question.first(),
                student_application=application_student.first(),
                defaults={
                    'empty': False,
                    'value': value,
                    'created_by': request.user, 
                }
            )

            if not created:
                sum_answer.question_options.clear()

            sum_answer.create_sum_option_answers()
            sum_answer.grade = sum_answer.get_grade_proportion()
            sum_answer.save()

            return JsonResponse(
                {
                    "question_option_checked": question_option_checked_ids,
                    "created": created,
                },
                status=201,
        )
        except json.JSONDecodeError:
            return JsonResponse({"error": "Formato de dados inválido."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)