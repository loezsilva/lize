import uuid
import os

from django.db.models import Q, Exists, OuterRef
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.expressions import F
from django.core.files.storage import FileSystemStorage
from django.utils.html import strip_tags

from rest_framework import status
from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView, UpdateAPIView, RetrieveAPIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.decorators import action

from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer

from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication
from fiscallizeon.core.utils import CheckHasPermission, SimpleAPIPagination, CheckHasPermissionAPI
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.exams.permissions import IsTeacherSubject
from fiscallizeon.notifications.models import Notification
from fiscallizeon.notifications.functions import get_and_create_notifications
from fiscallizeon.questions.models import Question, QuestionOption, SugestionTags
from fiscallizeon.exams.permissions import IsTeacherSubject
from fiscallizeon.questions.permissions import IsStudentOwner
from fiscallizeon.questions.serializers.questions import QuestionAndFileAnswerSerializer, QuestionSerializer, QuestionSerializerSimple, QuestionSerializerNoAnswer, QuestionOptionSimpleSerializer
from fiscallizeon.core.storage_backends import PrivateMediaStorage, PublicMediaStorage
from fiscallizeon.clients.permissions import IsCoordinationMember, IsInspectorMember
from fiscallizeon.questions.serializers.questions import QuestionSerializer, QuestionExamElaborationSerializer, QuestionSerializerSimple, QuestionSerializerNoAnswer, AlternativeSerializer, SugestionTagsSerializer, QuestionImageUpdateSerializer, ExamQuestionBlockWeightSerializer
from fiscallizeon.questions.handle import handle_question_duplication
from fiscallizeon.exams.models import Exam
from fiscallizeon.ai.models import QuestionImprove
from fiscallizeon.bncc.models import Abiliity, Competence
from fiscallizeon.subjects.models import Topic, KnowledgeArea
from fiscallizeon.ai.openai.questions import create_new_question, create_new_image_question, create_new_question_efaf, improve_question, solve_question, handle_textual_answer
from fiscallizeon.ai.openai.essays import handle_essay
from fiscallizeon.weaviatedb.queries.abilities import search_ability
from fiscallizeon.weaviatedb.queries.competences import search_competence
from fiscallizeon.weaviatedb.queries.topics import search_topic
from fiscallizeon.ai.serializers.questions import CreateAiQuestionSerializer, ImproveAiQuestionSerializer, ClassifyQuestionAbilitySerializer, ClassifyQuestionCompetenceSerializer, ClassifyQuestionTopicSerializer, QuestionImproveSerializer, QuestionImproveSimpleSerializer

class QuestionViewSet(CheckHasPermissionAPI, viewsets.ModelViewSet):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    serializer_class = QuestionExamElaborationSerializer
    queryset = Question.objects.all()
    pagination_class = SimpleAPIPagination
    authentication_classes = (CsrfExemptSessionAuthentication, TokenAuthentication,)
    parser_classes = (CamelCaseJSONParser, MultiPartParser, FormParser, )
    renderer_classes = (CamelCaseJSONRenderer,)
    model = Question
    
    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        instance = self.perform_create(serializer)
        
        headers = self.get_success_headers(serializer.data)
        
        return Response(self.get_serializer(instance=Question.objects.using('default').get(id=instance.id)).data, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_create(self, serializer):
        
        user = self.request.user
        
        instance = serializer.save(created_by=user)
        
        instance.coordinations.set(user.get_coordinations())
        
        for alternative_data in self.request.data.get('alternatives'):
            try:
                alternative_serializer = QuestionOptionSimpleSerializer(data=alternative_data)
                alternative_serializer.is_valid(raise_exception=True)
                alternative_serializer.save(question=instance)
                
            except Exception as e:
                
                print(e)
        
        exam_question_id = self.request.data.get("exam_question_id")
        block_weight = self.request.data.get("block_weight")
        weight = self.request.data.get("weight")

        if exam_question_id is not None and block_weight is not None and weight is not None :
            try:
                exam_question = ExamQuestion.objects.get(pk=exam_question_id)
                
                block_weight_data = {'block_weight': block_weight, 'weight': weight}
                serializer = ExamQuestionBlockWeightSerializer(exam_question, data=block_weight_data, partial=True)
                
                if serializer.is_valid():
                    serializer.save()
            except Exception as e:
                print(e)

        get_and_create_notifications(view=self, trigger=Notification.AFTER_CREATE)
        
        return instance
    
    def perform_update(self, serializer):
        instance = serializer.save()
        
        alternatives = self.request.data.get('alternatives')
        
        if alternatives:
            for alternative_data in alternatives:
                try:
                    if alternative_data.get('is_new'):
                        alternative_serializer = QuestionOptionSimpleSerializer(data=alternative_data)
                        alternative_serializer.is_valid(raise_exception=True)
                        alternative_serializer.save(question=instance)
                    
                except Exception as e:
                    print(e)

        exam_question_id = self.request.data.get("exam_question_id")
        block_weight = self.request.data.get("block_weight")
        weight = self.request.data.get("weight")

        if exam_question_id is not None and block_weight is not None:
            try:
                exam_question = ExamQuestion.objects.get(pk=exam_question_id)
                
                block_weight_data = {'block_weight': block_weight, 'weight': weight}
                serializer = ExamQuestionBlockWeightSerializer(exam_question, data=block_weight_data, partial=True)
                
                if serializer.is_valid():
                    serializer.save()
            except Exception as e:
                print(e)

        get_and_create_notifications(view=self, trigger=Notification.AFTER_UPDATE)
    
    @action(detail=False, methods=["GET"], serializer_class=SugestionTagsSerializer)
    def sugestion_tags(self, request, pk=None):
        
        user = self.request.user
        
        tags = SugestionTags.objects.filter(Q(user__isnull=True) | Q(user=user))
        
        serializer = SugestionTagsSerializer(instance=tags, many=True)
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get', 'post'])
    def create_with_ai(self, request):
        serializer = CreateAiQuestionSerializer(data=request.data)
        
        user = self.request.user
        
        alternatives_quantity = request.data.get('alternatives_quantity', None)

        if serializer.is_valid():
            base_image_url = None
            if memory_file := request.data.get('base_image', None):
                os.makedirs('tmp/questions_ai', exist_ok=True)
                tmp_file = os.path.join('tmp/questions_ai', memory_file.name)
                FileSystemStorage(location="tmp/questions_ai").save(memory_file.name, memory_file)

                fs = PublicMediaStorage()
                saved_file = fs.save(
                    f'withai/{memory_file.name}',
                    open(tmp_file, 'rb')
                )
                os.remove(tmp_file)
                base_image_url = fs.url(saved_file)
            
            try:
                if base_image_url:
                    gpt_question = create_new_image_question(user, serializer.data.get('user_prompt'), base_image_url, alternatives_quantity)
                else:
                    items = serializer.data.get('items')
                    gpt_question = create_new_question(user, serializer.data.get('user_prompt'), items, alternatives_quantity)
                    
                gpt_question['created_with_ai'] = True
                
                if user.is_freemium and (gpt_question and gpt_question.get('enunciation')):
                    user.create_ai_credit_use()

                return Response(gpt_question, status=200 if gpt_question else 400)
            
            except Exception as e:
                print("🚀 ~ e:", e)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def correct_essay(self, request):
        essay_file = request.data.get('file')
        theme = request.data.get('theme')
        content = request.data.get('content')
        
        if essay_file:
            os.makedirs('tmp/essays_ai', exist_ok=True)
            tmp_file = os.path.join('tmp/essays_ai', essay_file.name)
            tmp_url = FileSystemStorage(location="tmp/essays_ai").save(essay_file.name, essay_file)

            fs = PublicMediaStorage()
            saved_file = fs.save(
                f'withai/{essay_file.name}',
                open(tmp_file, 'rb')
            )
            os.remove(tmp_file)
            image_url = fs.url(saved_file)

            results = handle_essay(theme, content=None, essay_file=image_url)
        else:
            results = handle_essay(theme, content, essay_file=None)
        
        return Response(results, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def correct_textual_answer(self, request):
        question_file = request.data.get('file')
        enunciation = request.data.get('enunciation')
        commented_answer = request.data.get('commented_answer')
        student_answer = request.data.get('student_answer')

        results = {}
        if question_file:
            os.makedirs('tmp/discursives_ai', exist_ok=True)
            tmp_file = os.path.join('tmp/discursives_ai', question_file.name)
            tmp_url = FileSystemStorage(location="tmp/discursives_ai").save(question_file.name, question_file)

            fs = PublicMediaStorage()
            saved_file = fs.save(
                f'withai/{question_file.name}',
                open(tmp_file, 'rb')
            )
            os.remove(tmp_file)
            image_url = fs.url(saved_file)

            results = handle_textual_answer(enunciation, commented_answer, student_answer=None, question_file=image_url)

        else:
            results = handle_textual_answer(enunciation, commented_answer, student_answer, question_file=None)

        
        return Response(results, status=status.HTTP_200_OK)

    @action(detail=True, methods=["POST"])
    def improve(self, request, pk):
        serializer = ImproveAiQuestionSerializer(data=request.data)
        
        question_improve = None
        
        user = self.request.user
        
        if serializer.is_valid():

            question = {
                "enunciation": serializer.data.get('enunciation'),
                "alternatives": serializer.data.get('alternatives')
            }

            [ gpt_response, status_code ] = improve_question(user, str(question))
            
            if status_code == 200:
                question_improve = self.get_object().get_improve()
                question_improve.enunciation = gpt_response.get('enunciation')
                question_improve.alternatives = gpt_response.get('alternatives')
                question_improve.enunciation_correction_detail = gpt_response.get('correction_detail')
                question_improve.save(skip_hooks=True)
                
                if user.is_freemium and (gpt_response.get('enunciation') or gpt_response.get('alternatives')):
                    user.create_ai_credit_use()

            return Response(QuestionImproveSerializer(instance=question_improve).data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=["POST"])
    def solve(self, request, pk):
        serializer = ImproveAiQuestionSerializer(data=request.data)
        question_improve = None
        user = self.request.user
        if serializer.is_valid():
            question = {
                "enunciation": serializer.data.get('enunciation'),
                "alternatives": serializer.data.get('alternatives')
            }
            
            gpt_response = solve_question(user, str(question))

            question_improve = self.get_object().get_improve()
            question_improve.commented_answer = gpt_response.get('resolution')
            question_improve.save(skip_hooks=True)

            return Response(QuestionImproveSerializer(instance=question_improve).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["POST"])
    def classify_ability(self, request, pk):
        serializer = ClassifyQuestionAbilitySerializer(data=request.data)

        if serializer.is_valid():
            enunciation = strip_tags(serializer.data.get('enunciation'))
            alternatives = strip_tags(serializer.data.get('alternatives'))
            grade = serializer.data.get('grade')
            subjects = serializer.data.get('subjects')
            knowledge_area = serializer.data.get('knowledge_area', None)
            limit = serializer.data.get('limit', 1)

            question_improve = None

            client = None
            if user_clients := request.user.get_clients_cache():
                client = user_clients[0] if Abiliity.check_client(user_clients[0]) else None 
            
            query = f'{enunciation}\n\n{alternatives}'
            response = search_ability(query, grade, client_id=client, subject_ids=subjects, knowledge_area_id=knowledge_area, limit=limit)
            
            if len(response):
                question_improve = self.get_object().get_improve()
                question_improve.applied_abilities.clear()
                if(type(response) == list):
                    question_improve.abilities.set(list(map(lambda x: x['id'], response)))
            
            return Response(QuestionImproveSerializer(instance=question_improve).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=["POST"])
    def classify_competence(self, request, pk):
        serializer = ClassifyQuestionCompetenceSerializer(data=request.data)

        if serializer.is_valid():
            enunciation = strip_tags(serializer.data.get('enunciation'))
            alternatives = strip_tags(serializer.data.get('alternatives'))
            subjects = serializer.data.get('subjects')
            knowledge_area = serializer.data.get('knowledge_area', None)
            limit = serializer.data.get('limit', 1)

            question_improve = None
            
            client = None
            if user_clients := request.user.get_clients_cache():
                client = user_clients[0] if Competence.check_client(user_clients[0]) else None
            
            query = f'{enunciation}\n\n{alternatives}'
            response = search_competence(query, client_id=client, subject_ids=subjects, knowledge_area_id=knowledge_area, limit=limit)
            
            if len(response):
                question_improve = self.get_object().get_improve()                
                question_improve.applied_competences.clear()
                if(type(response) == list):
                    question_improve.competences.set(list(map(lambda x: x['id'], response)))
            
            return Response(QuestionImproveSerializer(instance=question_improve).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=["POST"])
    def classify_topic(self, request, pk):
        serializer = ClassifyQuestionTopicSerializer(data=request.data)

        if serializer.is_valid():
            enunciation = strip_tags(serializer.data.get('enunciation'))
            alternatives = strip_tags(serializer.data.get('alternatives'))
            subjects = serializer.data.get('subjects')
            grade = serializer.data.get('grade', None)
            limit = serializer.data.get('limit', 1)
            
            question_improve = None

            client = None
            if user_clients := request.user.get_clients_cache():
                client = user_clients[0] if Topic.check_client(user_clients[0]) else None
            
            query = f'{enunciation}\n\n{alternatives}'
            response = search_topic(query, subjects, grade_id=grade, client_id=client, limit=limit)

            if len(response):
                question_improve = self.get_object().get_improve()
                question_improve.applied_topics.clear()
                if(type(response) == list):
                    question_improve.topics.set(list(map(lambda x: x['id'], response)))
            
            return Response(QuestionImproveSerializer(instance=question_improve).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["GET"])
    def get_exam_question(self, request, pk=None):
        
        from fiscallizeon.exams.serializers.exam_questions import ExamQuestionExamElaborationSerializer

        user = request.user
        
        exam_question = ExamQuestion.objects.using('default').get(pk=pk, exam_teacher_subject__teacher_subject__teacher__user=user)
        return Response(
            ExamQuestionExamElaborationSerializer(
                instance=exam_question, context={'request': request}
            ).data
        )
    
    @action(detail=True, methods=["PATCH"])
    def update_improve(self, request, pk=None):

        question_improve = self.get_object().get_improve()
        
        serializer = QuestionImproveSimpleSerializer(instance=question_improve, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return self.get_improve(request, pk=pk)
    
    @action(detail=True, methods=["PATCH"])
    def get_improve(self, request, pk=None):
        question_improve = QuestionImprove.objects.using('default').get(question=self.get_object())
        return Response(QuestionImproveSerializer(instance=question_improve).data)
    
    @action(detail=False, methods=["GET"])
    def get_boards(self, request, pk=None):
        boards = Question.objects.get_public_boards()
        return Response(boards)

    @action(detail=False, methods=["GET"])
    def get_knowledge_areas(self, request, pk=None):
        CACHE_KEY = f'USER_QUESTIONS_DATABASE_KNOWLEDGE_AREAS_{self.request.user.get_clients_cache()[0]}'
        
        if not cache.get(CACHE_KEY):
            public_knowledge_area = KnowledgeArea.objects.has_public_questions().values('pk', 'name')
            client_knowledge_area = KnowledgeArea.objects.annotate(
                has_questions=Exists(
                    Question.objects.filter(
                        subject__knowledge_area=OuterRef('pk'),
                        coordinations__unity__client__in=self.request.user.get_clients_cache(),
                    ).select_related('subject')
                )
            ).filter(
                has_questions=True,
            ).values('pk', 'name')

            knowledge_areas = [
                {
                    'knowledge_area_id': knowledge_area['pk'],
                    'knowledge_area_name': knowledge_area['name'],
                }
                for knowledge_area in public_knowledge_area.union(client_knowledge_area)
            ]

            cache.set(CACHE_KEY, knowledge_areas, 4 * 60 * 60)

        return Response(cache.get(CACHE_KEY))

class QuestionOptionViewSet(CheckHasPermissionAPI, viewsets.ModelViewSet):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    serializer_class = AlternativeSerializer
    queryset = QuestionOption.objects.all()
    pagination_class = SimpleAPIPagination
    authentication_classes = (CsrfExemptSessionAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)    

class QuestionListView(LoginRequiredMixin, CheckHasPermission, ListAPIView):
    serializer_class = QuestionSerializerSimple
    search_fields = ('enunciation', 'id', )
    required_scopes = ['read', 'write']
    required_permissions = [settings.COORDINATION, settings.TEACHER]

    def get_queryset(self):
        user = self.request.user
        queryset = Question.objects.filter(
            Q(
				coordinations__unity__client__in=user.get_clients_cache(),
                is_abstract=False
			)
        ).distinct().order_by('-created_at')

        if user.user_type == settings.TEACHER:
            queryset = queryset.filter(
                Q(subject__in=user.inspector.subjects.all()) |
                Q(created_by=user)
            )

        return queryset

class QuestionDetailView(LoginRequiredMixin, CheckHasPermission, RetrieveAPIView):
    serializer_class = QuestionSerializer
    queryset = Question.objects.all()
    required_permissions = [settings.INSPECTOR, settings.STUDENT, settings.TEACHER, settings.COORDINATION]
    permission_classes = [IsCoordinationMember|IsStudentOwner|IsTeacherSubject]
    
    def get_serializer_context(self):
        context = super(QuestionDetailView, self).get_serializer_context()
        context["randomization_version_pk"] = self.request.GET.get('randomization_version_pk', None) # Utilizado para pegar as alterativas randomizadas
        context["application_student"] = self.request.GET.get('application_student', None)
        
        return context



class QuestionFileAnswerStudentRetrieveAPIView(LoginRequiredMixin, CheckHasPermission, RetrieveAPIView):
    serializer_class = QuestionAndFileAnswerSerializer
    queryset = Question.objects.all()
    required_permissions = [settings.STUDENT]
    permission_classes = []

    def get_serializer_context(self):
        context = super(QuestionFileAnswerStudentRetrieveAPIView, self).get_serializer_context()
        context["student_application"] = self.kwargs['student_application']
        return context

    def get_object(self):
        queryset = Question.objects.filter(pk=self.kwargs['pk'], fileanswer__student_application=self.kwargs['student_application'])
        return queryset

class  QuestionSelectOnlyAPIView(LoginRequiredMixin, CheckHasPermission, RetrieveAPIView):
    serializer_class = QuestionSerializerSimple
    queryset = Question.objects.all()
    required_permissions = [settings.TEACHER, settings.COORDINATION]
    # permission_classes = [IsTeacherSubject]
    model = Question
    
class QuestionCopyDetailView(QuestionSelectOnlyAPIView):
    permission_required = 'questions.can_duplicate_question'
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        original_question = Question.objects.get(pk=instance.pk)
        
        if self.request.GET.get('exam'):
            exam = Exam.objects.using('default').get(pk=self.request.GET.get('exam'))
            if instance in exam.questions.all():
                return handle_question_duplication()
        
        already_copied = Question.objects.filter(
            source_question=original_question,
            created_by=request.user,
            is_public=False
        )
        
        adapted = self.request.GET.get('adapted')

        if not already_copied or adapted:
            copy_question = Question.objects.get(pk=instance.pk)
            copy_question.pk = uuid.uuid4()
            copy_question.source_question = original_question
            copy_question.is_public = False
            copy_question.created_by = request.user
            if adapted:
                copy_question.adapted = True
            copy_question.save()

            copy_question.topics.set(original_question.topics.all())
            copy_question.coordinations.set(request.user.get_coordinations())
            copy_question.abilities.set(original_question.abilities.all())
            copy_question.competences.set(original_question.competences.all())

            if original_question.category == Question.CHOICE:
                for index, alternative in enumerate(original_question.alternatives.all().order_by('created_at'), 1):
                    QuestionOption.objects.create(
                        question=copy_question,
                        text=alternative.text,
                        is_correct=alternative.is_correct,
                        index=index,
                    )
        else:
            copy_question = already_copied.first()
        serializer = self.get_serializer(copy_question)
        return Response(serializer.data)

class QuestionDetailNoAnswerView(LoginRequiredMixin, CheckHasPermission, RetrieveAPIView):
    serializer_class = QuestionSerializerNoAnswer
    queryset = Question.objects.filter(is_abstract=False)
    required_permissions = [settings.INSPECTOR, settings.COORDINATION, settings.TEACHER]
    permission_classes = [IsCoordinationMember|IsInspectorMember]



class QuestionHistoricalAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    required_permissions = [settings.INSPECTOR, settings.COORDINATION, settings.TEACHER]
    permission_classes = [IsCoordinationMember|IsInspectorMember]

    def get(self, request, *args, **kwargs):

        exam_question = ExamQuestion.objects.filter(question__pk=self.kwargs['pk']).annotate(
            id_exam=F('exam__id'),
            exam_name=F('exam__name'),
            application_date=F('exam__application__date'),
            teacher_name=F('exam_teacher_subject__teacher_subject__teacher__name'),
            teacher_subject=F('exam_teacher_subject__teacher_subject__subject__name'),
        ).distinct()
        
        return Response(status=status.HTTP_200_OK,
            data = {
                "exam_question": exam_question.values('id_exam', 'exam_name', 'application_date', 'teacher_name', 'teacher_subject')
            }, content_type="application/json")

class QuestionImageUpdateView(LoginRequiredMixin, CheckHasPermission, UpdateAPIView):
    required_permissions = [settings.INSPECTOR, settings.COORDINATION, settings.TEACHER]
    queryset = Question.objects.all()
    serializer_class = QuestionImageUpdateSerializer
    parser_classes = (MultiPartParser, FormParser)
    
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


questions_api_list = QuestionListView.as_view()
questions_api_detail = QuestionDetailView.as_view()
questions_api_detail_no_answer = QuestionDetailNoAnswerView.as_view()
questions_select_only = QuestionSelectOnlyAPIView.as_view()
question_copy_detail_view = QuestionCopyDetailView.as_view()
questions_historical = QuestionHistoricalAPIView.as_view()
question_api_image_update =QuestionImageUpdateView.as_view()

question_fileanswer_student_api = QuestionFileAnswerStudentRetrieveAPIView.as_view()