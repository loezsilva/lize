import re
import random
import json

import openai

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F, Case, When, Value, CharField, Q
from django.db.models.functions import Cast
from django.conf import settings

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework import serializers


from fiscallizeon.core.utils import CheckHasPermissionAPI


from fiscallizeon.core.paginations import LimitOffsetPagination
from fiscallizeon.subjects.models import Topic, Theme, MainTopic, Subject
from fiscallizeon.ai.openai.questions import create_new_version_question_ia
from django_filters import FilterSet, ModelMultipleChoiceFilter

from rest_framework.response import Response
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

from ..models import Question, QuestionOption
from ..serializers2.question import QuestionSerializer, QuestionSimpleSerializer, QuestionVerySimpleSerializer

from fiscallizeon.questions.serializers.questions import QuestionExamElaborationSerializer, QuestionSerializerSimple
from fiscallizeon.corrections.models import CorrectionCriterion, CorrectionTextualAnswer, CorrectionFileAnswer
from fiscallizeon.ai.serializers.questions import QuestionImproveSerializer
from fiscallizeon.corrections.serializers.correction import CorrectionTextualAnswerOrderSerializer, CorrectionFileAnsweOrderSerializer
from rest_framework import status

from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer

import logging

logger = logging.getLogger('fiscallizeon')

@extend_schema(tags=['Questões'])
class QuestionListView(ListAPIView):
    serializer_class = QuestionSerializer
    pagination_class = LimitOffsetPagination
    required_scopes = ['read', 'write']

    def get_queryset(self):
        queryset = Question.objects.filter(
            coordinations__unity__client__in=self.request.user.get_clients_cache(),
            is_abstract=False,
        ).annotate(
            alternatives_list=ArrayAgg(Cast('alternatives__text', output_field=CharField())),
            topics_list=ArrayAgg(Cast('topics__name', output_field=CharField()), distinct=True, default=[]),
            abilities_list=ArrayAgg(Cast('abilities__pk', output_field=CharField()), distinct=True, default=[]),
            competences_list=ArrayAgg(Cast('competences__pk', output_field=CharField()), distinct=True, default=[]),
            base_texts_list=ArrayAgg(Cast('base_texts__pk', output_field=CharField()), distinct=True, default=[]),
            creator=F('created_by__name'),
            level_description=Case(
                When(level=0, then=Value('Fácil')),
                When(level=1, then=Value('Médio')),
                When(level=2, then=Value('Difícil')),
                default=Value('Indefinido')
            ),
            category_description=Case(
                When(category=0, then=Value('Discursiva')),
                When(category=1, then=Value('Objetiva')),
                When(category=2, then=Value('Arquivo anexado')),
                default=Value('Indefinido')
            )
        ).distinct().values()

        return queryset
    

class QuestionsQuerysetMixin(object):
    
    def questions_queryset(self):
        user = self.request.user
        
        topics = self.request.GET.getlist("topics", None)
        themes = self.request.GET.getlist("themes", None)
        main_topics = self.request.GET.getlist("main_topics", None)
        
        subjects = self.request.GET.getlist("subjects", None)
        
        categories = self.request.GET.getlist('q_category', None)
        levels = self.request.GET.getlist('q_level', None)
        grades = self.request.GET.getlist('q_grade', None)
        boards = self.request.GET.getlist('q_board', None)
        knowledge_areas = self.request.GET.getlist('q_knowledge_area', None)
        enunciation_search = self.request.GET.get("q_enunciation_search")
        alternatives_search = self.request.GET.get("q_alternatives_search")
        start_year = self.request.GET.get("start_year") 
        end_year = self.request.GET.get("end_year")
        only_my_questions = self.request.GET.get('only_my_questions', False)


        topics_queryset = Topic.objects.filter(
            Q(pk__in=topics) |
            Q(theme__in=themes) | 
            Q(main_topic__in=main_topics)
        )
        
        client_questions = Question.objects.filter(
            Q(coordinations__in=user.get_coordinations_cache()) if only_my_questions else Q(),
            Q(category__in=categories) if categories else Q(),
            Q(enunciation__icontains=enunciation_search) if enunciation_search else Q(),
            Q(alternatives__text__icontains=alternatives_search) if alternatives_search else Q(),
            Q(level__in=levels) if levels else Q(),
            Q(grade__in=grades) if grades else Q(),
            Q(board__in=boards) if boards else Q(),
            Q(subject__knowledge_area__in=knowledge_areas) if knowledge_areas else Q(),
            Q(
                Q(elaboration_year__gte=start_year, elaboration_year__lte=end_year) |
                Q(elaboration_year__isnull=True, created_at__year__gte=start_year, created_at__year__lte=end_year)
            ) if start_year and end_year else Q()
        )
        
        public_questions = Question.objects.filter(
            Q(is_public=True),
            Q(category__in=categories) if categories else Q(),
            Q(enunciation__icontains=enunciation_search) if enunciation_search else Q(),
            Q(alternatives__text__icontains=alternatives_search) if alternatives_search else Q(),
            Q(level__in=levels) if levels else Q(),
            Q(grade__in=grades) if grades else Q(),
            Q(board__in=boards) if boards else Q(),
            Q(subject__knowledge_area__in=knowledge_areas) if knowledge_areas else Q(),
            Q(
                Q(elaboration_year__gte=start_year, elaboration_year__lte=end_year) |
                Q(elaboration_year__isnull=True, created_at__year__gte=start_year, created_at__year__lte=end_year)
            ) if start_year and end_year else Q()
        )
        
        if subjects and topics_queryset:
            client_questions = client_questions.filter(Q(subject__in=subjects) | Q(topics__in=topics_queryset))
            public_questions = public_questions.filter(Q(subject__in=subjects) | Q(topics__in=topics_queryset))
            
        elif subjects:
            client_questions = client_questions.filter(subject__in=subjects)
            public_questions = public_questions.filter(subject__in=subjects)
            
        elif topics_queryset:
            client_questions = client_questions.filter(topics__in=topics_queryset)
            public_questions = public_questions.filter(topics__in=topics_queryset)
            
        else:
            return self.queryset.none()

        if only_my_questions:
            return client_questions.order_by('?').distinct()
        
        # if random.choice([True, False]): #Solução para contornar problema de order_by randomizado
        #     return client_questions.order_by('?').distinct().union(public_questions.distinct().order_by('?'))
        
        return public_questions.order_by('?').distinct()
    
    
class QuestionSelectListView(ListAPIView, QuestionsQuerysetMixin):
    serializer_class = QuestionVerySimpleSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [SearchFilter]
    search_fields = ["enunciation"]
    queryset = Question.objects.all()
    
    def get_queryset(self):        
        return self.questions_queryset()
    
class QuestionSelectExamElaborationListView(ListAPIView, QuestionsQuerysetMixin):
    serializer_class = QuestionExamElaborationSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [SearchFilter]
    search_fields = ["enunciation"]
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    queryset = Question.objects.all()
    
    def get_queryset(self):        
        return self.questions_queryset()

class QuestionCountView(ListAPIView, QuestionsQuerysetMixin):    
    class QuestionCountSerializer(serializers.ModelSerializer):
        class Meta:
            fields = ['id']
            model = Question
            
    queryset = Question.objects.all()
    serializer_class = QuestionCountSerializer
    pagination_class = LimitOffsetPagination
    
    def get_queryset(self):
        return self.questions_queryset()
    

class QuestionSelectRetrieveAPIView(RetrieveAPIView):
    serializer_class = QuestionSimpleSerializer
    queryset = Question.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        
        user = self.request.user
        
        queryset = queryset.filter(
            Q(is_abstract=False),
            Q(
                Q(coordinations__unity__client__in=user.get_clients_cache()) #|
                # Q(is_public=True),
            )
        ).distinct()
        
        return queryset

class QuestionFormatterAPIView(CheckHasPermissionAPI, APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    def post(self, request):
        
        openai.api_key = settings.OPENAI_API_KEY
        
        model_engine = "gpt-3.5-turbo"
        
        data = request.data
        text = data.get('text')
        
        # Remove espaços duplicados e quebras de linha
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Comporte-se como um formatador de questões enem de html para json... Formate essa questão em HTML para o seguinte formato JSON: 'enunciation': '', alternatives: 'text', 'is_correct', não remova as tags html e diferencie o que é alternativa de enunciado. remova a letra (a,b,c,d..) que fica no antes do texto da alternativa, não escolha a alternativa correta, só marque o is_correct como true se o usuário informar qual é a resposta correta e não coloque o texto que identificou a alternativa correta na alternativa"
        messages = [
            { "role": "system", "content": "Formate questão HTML em JSON: 'enunciation':'', 'alternatives': [{'text':'', 'is_correct':''}], mantenha as tags HTML, diferencie enunciado de alternativas, remova letra que identifica a alternativa, is_correct=true se usuário definir resposta correta, não inclua texto que identifica a correta na alternativa." },
            { "role": "user", "content": f"{text}" },
        ]
        
        try:
            
            response = openai.ChatCompletion.create(
                model=model_engine,
                messages=messages,
                temperature=0.1
            )
            
        except Exception as e:
            logger.error(repr(e))
        
        chat_response = response['choices'][0]['message']['content']
        
        return Response(json.loads(chat_response))
    

class GetCorrectionAnswersView(APIView):
    def get(self, request, *args, **kwargs):
        student_id = request.query_params.get('student_id')
        question_id = request.query_params.get('question_id')

        if not student_id or not question_id:
            return Response({'error': 'student_id and question_id are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            return Response({'error': 'Question not found'}, status=status.HTTP_404_NOT_FOUND)

        if question.category == Question.TEXTUAL:
            answers = CorrectionTextualAnswer.objects.filter(
                textual_answer__student_application__id=student_id,
                correction_criterion__text_correction=question.text_correction
            )
            serializer = CorrectionTextualAnswerOrderSerializer(answers, many=True)
        
        elif question.category == Question.FILE:
            answers = CorrectionFileAnswer.objects.filter(
                file_answer__student_application__id=student_id,
                correction_criterion__text_correction=question.text_correction
            )
            serializer = CorrectionFileAnsweOrderSerializer(answers, many=True)

        else:
            return Response({'error': 'Invalid question category'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.data, status=status.HTTP_200_OK)
    



class ChangeQuestionAPIView(APIView):
    def post(self, request, *args, **kwargs):
        question_id = request.data.get('question_id')
        change_type = request.data.get('change_type', False)
        reduce_statement = request.data.get('reduce_statement', False)
        reduce_alternatives = request.data.get('reduce_alternatives', False)
        reduce_texts_in_alternatives = request.data.get('reduce_texts_in_alternatives', False)
        context_text = request.data.get('context', '')

        if not question_id:
            return Response({'error': 'ID da questão e tipo da questão são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            return Response({'error': 'Questão não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        user_prompt = self.create_user_prompt(question, change_type,
                                            reduce_statement, reduce_alternatives, reduce_texts_in_alternatives, context_text)        
        
        response_data = create_new_version_question_ia(request.user, user_prompt)

        if 'error' in response_data:
            return Response({'error': 'Erro ao processar a questão.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        enunciation = response_data.get('enunciation', '')
        response_data['enunciation'] = enunciation

        return Response(response_data, status=status.HTTP_200_OK)

    
    def create_user_prompt(self, question, change_type, reduce_statement, reduce_alternatives, reduce_texts_in_alternatives, context_text):
        user_prompt = f"Enunciado da Questão: <enunciado>{question.enunciation}</enunciado>"    

        if question.category == Question.CHOICE:
            options = QuestionOption.objects.filter(question=question)
            options_texts = []
            correct_option_text = 'Nenhuma alternativa correta encontrada.'
            for option in options:
                options_texts.append("<alternativa_errada>" + option.text + "</alternativa_errada>")
                if option.is_correct:
                    correct_option_text = option.text
            options_texts_str = "\n".join(options_texts)
            total_options = len(options)
            user_prompt += f"- \n{options_texts_str}"
            user_prompt += f"- <alternativa_correta>{correct_option_text}<alternativa_correta>"

        elif question.category in [Question.TEXTUAL, Question.FILE]:
            commented_answer = question.commented_answer if hasattr(question, 'commented_answer') else 'Nenhuma resposta comentada encontrada.'
            user_prompt += f"- Resposta comentada original: {commented_answer}\n"
        
        user_prompt += f"<tipo_da_questao>O tipo da questão é {'Objetiva' if question.category == Question.CHOICE else 'Discursiva'}</tipo_da_questao>"
        user_prompt += "<instrucoes>Elabore a nova versão da questão considerando as seguintes modificações, conforme aplicável:\n"
        
        if change_type: 
            if question.category in [Question.TEXTUAL, Question.FILE]:
                user_prompt += "A questão original fornecida é do tipo discursiva. Você deve transformá-la em uma questão objetiva. \
                    A nova versão deve incluir um enunciado claro com uma pergunta e CINCO alternativas, das quais apenas uma deve ser correta. \
                    Se a questão discursiva já tiver uma resposta comentada e essa for correta, utilize-a como base para gerar a alternativa correta."
            else:
                user_prompt += f" A questão original fornecida é do tipo objetiva. Você deve transformá-la em uma questão discursiva. \
                A nova versão deve conter um enunciado claro com uma pergunta e uma resposta comentada, se a alternativa correta tiver sido fornecida."

        if reduce_statement:
            user_prompt += "- Simplifique o enunciado da questão, reduzindo a quantidade de palavras, sem alterar o significado. Preserve as imagens.\n"

        if reduce_alternatives:
            user_prompt += f"- Apague uma alternativa. A questão deverá ficar com apenas {total_options - 1} \n"

        if reduce_texts_in_alternatives:
            user_prompt += "- Reduza o texto nas alternativas sem apagá-las, preservando imagens e o HTML.\n"

        if context_text:
            user_prompt += f"- Ajuste o enunciado da questão para o seguinte contexto: {context_text}\n"

        user_prompt +=  "</instrucoes>"

        return user_prompt

    

class ConfirmChangeQuestionAPIView(APIView):
    def post(self, request, *args, **kwargs):
        question_id = request.data.get('question_id')
        new_enunciation = request.data.get('enunciation')
        new_category = request.data.get('category')
        alternatives_data = request.data.get('alternatives', [])  
        keep_change_type = request.data.get('keep_change_type')  

        if not question_id or not new_enunciation or not new_category:
            return Response({'error': 'ID da questão, novo enunciado e categoria são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            return Response({'error': 'Questão não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        
        if  not keep_change_type:
            CATEGORY_MAP = {label: value for value, label in Question.CATEGORY_TYPES}
            category_value = CATEGORY_MAP.get(new_category)
            question.category = category_value
        
        question.enunciation = new_enunciation
        
        if alternatives_data:
            question.alternatives.all().delete()  
            for alt in alternatives_data:
                QuestionOption.objects.create(
                    question=question,
                    text=alt['text'],
                    is_correct=alt.get('is_correct', False),
                    index=alt.get('index', 0)
                )
        question.created_with_ai = True
        question.save()

        return Response({'message': 'Questão e alternativas atualizadas com sucesso.'}, status=status.HTTP_200_OK)
