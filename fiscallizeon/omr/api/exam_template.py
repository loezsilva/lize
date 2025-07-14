import uuid
import copy
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.query import prefetch_related_objects
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse

from rest_framework import status
from rest_framework.authentication import BasicAuthentication
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from fiscallizeon.core.utils import CheckHasPermission

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.core.print_colors import print_error
from fiscallizeon.exams.models import Exam, ExamQuestion
from fiscallizeon.exams.serializers.exams import (
    ExamQuestionSimpleUpdateTemplateSerializer,
    ExamTemplateRetrieveSerializer,
    ExamTemplateSerializer,
    ExamTemplateUpdateSerializer,
)
from fiscallizeon.questions.models import Question, QuestionOption 
from fiscallizeon.questions.serializers.questions import (
    ExamTemplateQuestionCreateSerializer,
    QuestionOptionCreateSimpleSerializer,
    ExamOMRCreateSerializer,
    ExamOMRUpdateSerializer,
)

from fiscallizeon.notifications.functions import get_and_create_notifications
from fiscallizeon.notifications.models import Notification
from fiscallizeon.exams.utils import is_exam_name_unique


class ExamTemplateCreateAPIView(LoginRequiredMixin, CreateAPIView):
    model = Exam
    serializer_class = ExamTemplateSerializer
    required_permissions = [settings.COORDINATION, ]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def create(self, request, *args, **kwargs):
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        if self.request.data.get('examquestions'):
            
            for examquestion in self.request.data.get('examquestions'):

                question_serialized = ExamTemplateQuestionCreateSerializer(data=examquestion.get('question'))

                if question_serialized.is_valid(raise_exception=True):

                    question_instance = Question.objects.using('default').create(
                        grade=question_serialized.validated_data.get('grade'),
                        subject=question_serialized.validated_data.get('subject'),
                        category=question_serialized.validated_data.get('category'),
                        feedback=question_serialized.validated_data.get('feedback'),
                        is_abstract=question_serialized.validated_data.get('is_abstract'),
                        commented_awnser=question_serialized.validated_data.get('commented_awnser'),
                        quantity_lines=question_serialized.validated_data.get('quantity_lines'),
                    )
                    question_instance.topics.set(question_serialized.validated_data.get('topics'))
                    question_instance.abilities.set(question_serialized.validated_data.get('abilities'))
                    question_instance.competences.set(question_serialized.validated_data.get('competences'))
                    question_instance.coordinations.set(question_serialized.validated_data.get('coordinations'))
                    question_instance.save()

                    if(question_instance.get_category_display() == 'Objetiva'):
                        
                        for alternative in examquestion.get('question').get('alternatives'):

                            alternative_instance = QuestionOption.objects.using('default').create(
                                question=question_instance,
                                text=alternative['text'],
                                is_correct=alternative['is_correct'],
                                index=alternative['index'],
                            )
                            alternative_instance.save()

                    #Cria o Exam Question
                    if not examquestion.get('weight') or float(examquestion.get('weight')) < 0:
                        examquestion['weight'] = 0

                    examquestion_instance = ExamQuestion.objects.using('default').create(
                        exam=serializer.instance,
                        question=question_instance,
                        order=examquestion['order'],
                        weight=examquestion['weight'],
                        is_foreign_language=examquestion['is_foreign_language'],
                    )
                    examquestion_instance.save()
                    
            messages.success(self.request, 'Gabarito adicionado com sucesso')

        else:
            raise Exception('Nenhuma questão foi informada')

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ExamTemplateUpdateAPIView(LoginRequiredMixin, UpdateAPIView):
    model = Exam
    serializer_class = ExamTemplateUpdateSerializer
    required_permissions = [settings.COORDINATION, ]
    queryset = Exam.objects.all()
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def update(self, request, *args, **kwargs):
        if self.request.data.get('examquestions'):

            # Deleta questões que não estão na lista
            examquestions_list = list(examquestion.get('id') for examquestion in self.request.data.get('examquestions'))
            
            ExamQuestion.objects.using('default').filter(exam=self.get_object()).exclude(pk__in=examquestions_list).delete()

            for examquestion in self.request.data.get('examquestions'):
                
                if examquestion.get('question').get('id'):
                    
                    question_serialized = ExamTemplateQuestionCreateSerializer(instance=Question.objects.using('default').get(pk=examquestion.get('question').get('id')), data=examquestion.get('question'))

                    if question_serialized.is_valid():

                        question_instance = question_serialized.save()

                        if(question_instance.get_category_display() == 'Objetiva'):
                            
                            for alternative in examquestion.get('question').get('alternatives'):

                                alternative['question'] = question_instance.id
                                if alternative.get('id'):
                                    alternative_serialized = QuestionOptionCreateSimpleSerializer(instance=QuestionOption.objects.using('default').get(pk=alternative.get('id')), data=alternative)
                                else:
                                    alternative_serialized = QuestionOptionCreateSimpleSerializer(data=alternative)
                                
                                if alternative_serialized.is_valid():
                                    alternative_serialized.save()
                        else:
                            #Remove todas as alternativas da questão caso elas existam
                            QuestionOption.objects.using('default').filter(question=question_instance).delete()

                        # Altera o ExamQuestion
                        if not examquestion.get('weight') or float(examquestion.get('weight')) < 0:
                            examquestion['weight'] = 0
                        examquestion_serialized = ExamQuestionSimpleUpdateTemplateSerializer(instance=ExamQuestion.objects.using('default').get(pk=examquestion.get('id')), data=examquestion)
                        if examquestion_serialized.is_valid():
                            examquestion_serialized.save()
                        else:
                            print_error(f'Erro ao salvar o ExamQuestion: {examquestion_serialized.errors}')
                    else: 
                        print_error(f'Erro ao salvar o Question: {question_serialized.errors}')
                else:

                    #Cria novos Exam Questions
                    question_serialized = ExamTemplateQuestionCreateSerializer(data=examquestion.get('question'))
                    
                    if question_serialized.is_valid():
                        
                        question_instance = Question.objects.using('default').create(
                            grade=question_serialized.validated_data.get('grade'),
                            subject=question_serialized.validated_data.get('subject'),
                            category=question_serialized.validated_data.get('category'),
                            feedback=question_serialized.validated_data.get('feedback'),
                            is_abstract=question_serialized.validated_data.get('is_abstract'),
                            commented_awnser=question_serialized.validated_data.get('commented_awnser'),
                        )

                        question_instance.topics.set(question_serialized.validated_data.get('topics'))
                        question_instance.abilities.set(question_serialized.validated_data.get('abilities'))
                        question_instance.competences.set(question_serialized.validated_data.get('competences'))
                        question_instance.coordinations.set(question_serialized.validated_data.get('coordinations'))
                        question_instance.save()

                        if(question_instance.get_category_display() == 'Objetiva'):
                            
                            for alternative in examquestion.get('question').get('alternatives'):

                                alternative_instance = QuestionOption.objects.using('default').create(
                                    question=question_instance,
                                    text=alternative['text'],
                                    is_correct=alternative['is_correct'],
                                    index=alternative['index'],
                                )
                                alternative_instance.save()

                        #Cria o Exam Question
                        if not examquestion.get('weight') or float(examquestion.get('weight')) < 0:
                            examquestion['weight'] = 0

                        examquestion_instance = ExamQuestion.objects.using('default').create(
                            exam=self.get_object(),
                            question=question_instance,
                            order=examquestion['order'],
                            weight=examquestion['weight'],
                            is_foreign_language=examquestion['is_foreign_language'],
                        )
                        examquestion_instance.save()

            messages.success(request, 'Gabarito atualizado com sucesso')

        else:
            raise Exception('Nenhuma questão foi informada')

        return super(ExamTemplateUpdateAPIView, self).update(request, *args, **kwargs)


class ExamTemplateV2CreateAPIView(LoginRequiredMixin, CreateAPIView):
    model = Exam
    serializer_class = ExamOMRCreateSerializer
    required_permissions = [settings.COORDINATION]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    nps_app_label = "ExamTemplate"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not is_exam_name_unique(request.data.get('coordinations'), request.data.get('name')):
             return Response(f"Já existe um gabarito ou caderno com o nome '{request.data.get('name')}'", status=status.HTTP_400_BAD_REQUEST)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        get_and_create_notifications(view=self, trigger=Notification.AFTER_CREATE)
        messages.success(request, 'Gabarito adicionado com sucesso')
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ExamTemplateV2UpdateAPIView(LoginRequiredMixin, UpdateAPIView):
    model = Exam
    serializer_class = ExamOMRUpdateSerializer
    required_permissions = [settings.COORDINATION]
    authentication_classes = (CsrfExemptSessionAuthentication,)
    queryset = Exam.objects.all()
    nps_app_label = "ExamTemplate"

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        if not is_exam_name_unique(request.data.get('coordinations'), request.data.get('name'), update=True, pk=instance.pk):
             return Response(f"Já existe um gabarito ou caderno com o nome '{request.data.get('name')}'", status=status.HTTP_400_BAD_REQUEST)

        self.perform_update(serializer)
        
        queryset = self.filter_queryset(self.get_queryset())
        if queryset._prefetch_related_lookups:
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance,
            # and then re-prefetch related objects
            instance._prefetched_objects_cache = {}
            prefetch_related_objects([instance], *queryset._prefetch_related_lookups)

        get_and_create_notifications(view=self, trigger=Notification.AFTER_UPDATE)
        messages.success(request, 'Gabarito atualizado com sucesso')
        return Response(serializer.data)


class ExamTemplateRetrieveAPIView(LoginRequiredMixin, RetrieveAPIView):
    model = Exam
    serializer_class = ExamTemplateRetrieveSerializer
    permission_classes = []
    required_permissions = [settings.COORDINATION, ]
    queryset = Exam.objects.using('default').all()
    authentication_classes = (CsrfExemptSessionAuthentication, )


class ExamTemplateDuplicate(LoginRequiredMixin, CheckHasPermission, RetrieveUpdateAPIView):
    Model = Exam
    serializer_class = ExamTemplateRetrieveSerializer
    required_permissions = [settings.COORDINATION, ]
    queryset = Exam.objects.all()
    
    def duplicate_exam_questions(self, question,new_exam, duplicated_question):
        original_exam_questions = ExamQuestion.objects.filter(question=question).availables()
        
        for exam_question in original_exam_questions:
            new_exam_question = ExamQuestion.objects.create(
                exam=new_exam,
                question=duplicated_question,
                order=exam_question.order,
                weight=exam_question.weight,
                is_foreign_language=exam_question.is_foreign_language,
            )
        return new_exam_question

    def duplicate_exam_template(self, original_exam, keep_alternatives, keep_pedagogical_data):
        new_exam = copy.deepcopy(original_exam)
        new_exam.pk = uuid.uuid4()
        new_exam.name = "CÓPIA - " + original_exam.name
        
        with transaction.atomic():
            new_exam.save()

            for coordination in original_exam.coordinations.all():
                new_exam.coordinations.add(coordination)
    
            for question in original_exam.questions.all():
                duplicated_question = question.duplicate_question_with_conditions(user=self.request.user, keep_alternatives=keep_alternatives, keep_pedagogical_data=keep_pedagogical_data)
                new_exam_question = self.duplicate_exam_questions(question, new_exam, duplicated_question)
                new_exam.examquestion_set.add(new_exam_question)

            for teacher_subject in original_exam.teacher_subjects.all():
                new_exam.teacher_subjects.add(teacher_subject)
        
        return new_exam
    
    def post(self, request, *args, **kwargs):
        keep_alternatives = request.POST.get('keep_alternatives')
        keep_pedagogical_data = request.POST.get('keep_pedagogical_data')
        original_exam = Exam.objects.get(pk=self.kwargs['pk'], )
        
        self.duplicate_exam_template(original_exam, keep_alternatives, keep_pedagogical_data)

        return HttpResponseRedirect(reverse('omr:template_list') )
    

exam_template_create = ExamTemplateCreateAPIView.as_view()
exam_template_update = ExamTemplateUpdateAPIView.as_view()
exam_template_detail = ExamTemplateRetrieveAPIView.as_view()
exam_template_duplicate = ExamTemplateDuplicate.as_view()
exam_template_v2_create = ExamTemplateV2CreateAPIView.as_view()
exam_template_v2_update = ExamTemplateV2UpdateAPIView.as_view()
