from django.urls import reverse
from datetime import timedelta
import logging
from django.conf import settings
import requests

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import viewsets
from rest_framework import serializers
from django.utils import timezone
from fiscallizeon.core.utils import CheckHasPermissionAPI
from fiscallizeon.exams.api.exams import ExamCoordinationAndTeacherViewSet
from fiscallizeon.exams.models import ExamTeacherSubject
from fiscallizeon.integrations.models import SuperProfIntegration
from fiscallizeon.integrations.serializers.superprof import SuperProfIntegrationSerializer, SuperProfIntegrationSimpleSerializer
from fiscallizeon.questions.models import Question, QuestionOption, BaseText

logger = logging.Logger('')

# SP_BASE_URL = settings.SP_BASE_URL
# SP_API_URL = settings.SP_API_URL
# SP_SSO_URL = settings.SP_SSO_URL

SIGNUP, AUTHORIZE, TOKEN, EXAMS, EXAM = "signup", "oauth/authorize", "oauth/token", "provas", "provas/examID"

def get_url(endpoint):
    url = SP_API_URL
    if endpoint:
        url += f"/{endpoint}"
    return url 

def headers(token=None):        
    return {
        "Authorization": "Bearer "+ token,
        "accept": "application/x-www-form-urlencoded",
    }
    
class SuperProfIntegrationViewSet(viewsets.ModelViewSet):
    serializer_class = SuperProfIntegrationSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = (CheckHasPermissionAPI, )
    required_permissions = [settings.TEACHER, settings.COORDINATION]
    
    def get_queryset(self):
        queryset = SuperProfIntegration.objects.all()
        queryset = queryset.filter(user=self.request.user)
        return queryset

    def get_serializer_class(self):
        if not self.request.method == 'POST':
            return SuperProfIntegrationSimpleSerializer
        return super().get_serializer_class()
    
    class ExamSerializerResponse(serializers.Serializer):
        idProva = serializers.IntegerField()
        nomeArquivo = serializers.CharField(max_length=255)
        data = serializers.DateTimeField()
        totalQuestoes = serializers.IntegerField()
        questoes = serializers.JSONField()
    
    @action(detail=True, methods=['GET'])
    def authorize(self, request, pk=None, generate_new=False):
        now = timezone.now() - timedelta(hours=3) # REMOVER ESSE - 3 ANTES DE SUBIR PARA PRODUÇÃO
        integration = self.get_object()
        
        if integration.authorization_expires_at and integration.authorization_expires_at > now and not generate_new:
            return Response({
                "authorization_code": integration.authorization_code,
                "authorization_expires_at": integration.authorization_expires_at,
            })
        
        data = {
            "response_type": "code",
            "redirect_uri": "http://localhost/oauth/callback",
            "username": integration.login,
            "password": integration.password,
            "client_id": 2,
        }
        
        response = requests.post(url=get_url(AUTHORIZE), headers={
            "Content-Type": "application/x-www-form-urlencoded",
        }, data=data)
        
        if response.status_code >= 200 and response.status_code <= 208:
            json = response.json()
            integration.authorization_code = json.get('authorizationCode')
            integration.authorization_expires_at = json.get('expiresAt')
            integration.save()
            return Response({
                "authorization_code": integration.authorization_code,
                "authorization_expires_at": integration.authorization_expires_at,
            })
        
        
        return Response("O processo de autorização falhou, certifique-se que digitou a chave de acesso corretamente.", status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['GET'])
    def token(self, request, pk=None):
        now = timezone.now() - timedelta(hours=3) # REMOVER ESSE - 3 ANTES DE SUBIR PARA PRODUÇÃO
        integration = self.get_object()
        authorization = None
        generate_new = self.request.GET.get('generate_new', False)
        
        if not integration.authorization_code:
            authorization = self.authorize(request=request)
            integration.authorization_code = authorization.data.get('authorization_code')
            integration.authorization_expires_at = authorization.data.get('authorization_expires_at')
        
        if not generate_new and (integration.sso_token_expires_at and integration.sso_token_expires_at > now):
            return Response({
                "sso_token": integration.sso_token,
                "sso_token_expires_at": integration.sso_token_expires_at,
                "access_token": integration.access_token,
                "access_token_expires_at": integration.access_token_expires_at,
                "sso_url": SP_SSO_URL.replace('sso_token', integration.sso_token) if authorization else SP_BASE_URL
            })
        
        headers = {
            "Authorization": "Basic MjoxMjM0NTY=",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        data = {
            "grant_type": "authorization_code",
            "redirect_uri": "http://localhost/oauth/callback",
            "code": integration.authorization_code,
        }
        
        response = requests.post(url=get_url(TOKEN), headers=headers, data=data)
        
        if response.status_code == 401:
            new_authorization = self.authorize(request=request, generate_new=True)
            data["code"] = new_authorization.data.get('authorization_code')
            response = requests.post(url=get_url(TOKEN), headers=headers, data=data)
        
        if response.status_code >= 200 and response.status_code <= 208:
            json = response.json()
            
            integration.sso_token = json.get('user').get('sso').get('token')
            integration.sso_token_expires_at = json.get('user').get('sso').get('dataValidade')
            
            integration.access_token = json.get('accessToken')
            integration.access_token_expires_at = json.get('accessTokenExpiresAt')
            integration.save()
            
            json["sso_url"] = SP_SSO_URL.replace('sso_token', integration.sso_token)
            
            return Response(json)
        
        return Response("Não foi possível obter o token de acesso, o processo de autorização falhou.", status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['GET'])
    def exams(self, request, pk=None):
        integration = self.get_object()

        headers = {
            "Authorization": f"Bearer {integration.access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        
        response = requests.get(url=get_url(EXAMS), headers=headers)
        
        if response.status_code >= 200 and response.status_code <= 208:
            json = response.json()
            exams = json.get('responseList')
            if exams:
                exams_serialized = self.ExamSerializerResponse  (data=exams, many=True)
                exams_serialized.is_valid(raise_exception=True)
                return Response(exams_serialized.data)
            
        return Response([])
    
    @action(detail=True, methods=['GET'])
    def exam(self, request, pk=None):
        integration = self.get_object()
        exam_id = self.request.GET.get('exam_id', None)
        if not exam_id:
            return Response('O ID da prova não foi informado')
        
        response = requests.get(url=get_url(EXAM.replace('examID', exam_id)), headers={
            "Authorization": f"Bearer {integration.access_token}",
        })

        if response.status_code >= 200 and response.status_code <= 208:
            json = response.json()
            
        return Response(json)
    
    @action(detail=False, methods=['GET'])
    def check_question(self, request, question_id=None):        
        
        question_id = self.request.GET.get('question_id', question_id)
        
        questions_id = self.request.GET.getlist('questions_id', None)
        
        relation = Question.objects.filter(created_by=self.request.user, superpro_id=question_id).first()
        
        if question_id:
            return Response({ "exist": True, "question_id": str(relation.question.id)} if relation else { "exist" : False})
        
        ids_list = []
        if questions_id:
            
            for id in questions_id:
                
                if Question.objects.filter(created_by=self.request.user, superpro_id=id).exists():
                
                    ids_list.append(int(id))
            
            return Response(ids_list)

        return Response("Ocorreu um erro ao tentar realizar a consulta", status=status.HTTP_400_BAD_REQUEST)
    
    def create_question(self, request, data, exam_teacher_subject_id, simple_import = False):
        if simple_import:
            category = None
            elaboration_year = None
            if data.get('type') == 'Objetiva':
                category = Question.CHOICE
            else:
                category = Question.TEXTUAL

            exam_teacher_subject = ExamTeacherSubject.objects.using('default').get(
                pk=exam_teacher_subject_id
            )
            
            institution = data.get('institution'), 
            try:
                elaboration_year = int(data.get('elaboration_year'))
            except:
                pass
            
            question = Question.objects.create(
                enunciation=data.get('enunciation'),
                created_by=self.request.user,
                category=category,
                commented_awnser=data.get('commented_answer'),
                elaboration_year=elaboration_year,
                institution=institution,
                subject=exam_teacher_subject.teacher_subject.subject,
                grade=exam_teacher_subject.grade,
            )

            answer_options = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5}
            
            index_answer = None
            
            if category == Question.CHOICE:
                
                if data.get('alternatives') and data.get('correct_answer'):
                    index_answer = answer_options[str(data.get('correct_answer')).upper()]

                
                for index, alternative in enumerate(data.get('alternatives'), start=1):
                    QuestionOption.objects.using('default').create(
                        question=question,
                        text=alternative,
                        is_correct=True if index_answer and index == index_answer else False,
                    )

            question.coordinations.set(self.request.user.get_coordinations_cache())

            return str(question.id)
        
        else:
            
            if not data.get('id'):
                return Response(
                    'Nenhuma questão foi informada.', status=status.HTTP_404_NOT_FOUND
                )
            # Clean answer
            answer = data.get('answer')
            if answer:
                answer = answer.strip()
                answer = answer.replace('[', '').replace(']', '')

            category = None
            if data.get('kind') == 'choice':
                category = Question.CHOICE
            else:
                category = Question.TEXTUAL

            level = None
            if data.get('level') == 'Fácil':
                level = Question.EASY
            elif data.get('level') == 'Média':
                level = Question.MEDIUM
            elif data.get('level') == 'Difícil':
                level = Question.HARD
            else:
                level = Question.UNDEFINED

            institution, elaboration_year = data.get('source').split('/')

            exam_teacher_subject = ExamTeacherSubject.objects.using('default').get(
                pk=exam_teacher_subject_id
            )

            answer_textual = ''
            if category == Question.TEXTUAL:
                answer_textual = answer

            question = Question.objects.using(
                'default'
            ).create(
                created_by=self.request.user,
                superpro_id=data.get('id'),
                category=category,
                level=level,
                enunciation=data.get('enunciation'),
                commented_awnser=data.get('commented_answer') or answer_textual,
                elaboration_year=elaboration_year,
                institution=institution,
                subject=exam_teacher_subject.teacher_subject.subject,
                grade= exam_teacher_subject.grade,
            )

            if data.get('base_text'):
                base_text = BaseText(
                    title='Texto base 1',
                    text=data.get('base_text'),
                    created_by=self.request.user,
                )
                base_text.save()

                question.base_texts.add(base_text)

            answer_options = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5}
            index_answer = None
            if data.get('alternatives') and category == Question.CHOICE:
                if data.get('answer'):
                    index_answer = answer_options[answer]

            if category == Question.CHOICE:
                if not question.alternatives.exists():
                    for index, alternative in enumerate(data.get('alternatives'), start=1):
                        QuestionOption.objects.using('default').create(
                            question=question,
                            text=alternative,
                            is_correct=True if index == index_answer else False,
                        )

            question.coordinations.set(self.request.user.get_coordinations_cache())

            return str(question.id)
        
    @action(detail=False, methods=['POST'])
    def import_questions(self, request, pk=None):        
        data = request.data
        question_data = data.get('question')
        questions_data = data.get('questions')
        
        if question_data:
            result = self.create_question(request, question_data)
            if result:
                return Response(status=status.HTTP_201_CREATED)
            else:
                return Response(status=status.HTTP_302_FOUND)
        
        questions_alread_imported = []
        questions_imported = []
        
        if questions_data:
            for question in questions_data:
                result = self.create_question(request, question)
                if result:
                    questions_imported.append(question.get('id'))
                else:
                    questions_alread_imported.append(question.get('id'))
            return Response({
                "questions_imported": questions_imported,
                "questions_alread_imported": questions_alread_imported,
            })
        
        return Response('Nenhuma questão foi importada') 
    
    @action(detail=False, methods=['POST'])
    def import_questions_and_create_exam_question(self, request, pk=None):
        data = request.data
        question_data = data.get('question')
        exam_teacher_subject_id = data.get('exam_teacher_subject_id')
        simple_import = request.GET.get('simple_import', False)

        if simple_import == 'false':
            simple_import = False

        if question_data:
            question_id = self.create_question(
                request, question_data, exam_teacher_subject_id, simple_import
            )
            question = Question.objects.using('default').get(pk=question_id)
            
            request.data.update({
                "id": question.id,
                "weight": 1,
            })
            
            api_instance = ExamCoordinationAndTeacherViewSet()
            
            result = api_instance.create_exam_question(request=request, pk=exam_teacher_subject_id)
            
            if result.status_code >= 200 and result.status_code <= 208:
                return Response(result.data, status=status.HTTP_201_CREATED)
            else:
                return Response(status=status.HTTP_302_FOUND)
        
        return Response('Nenhuma questão foi adicionada')
