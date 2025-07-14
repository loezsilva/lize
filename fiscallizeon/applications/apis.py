from decimal import Decimal
from fiscallizeon.core.utils import round_half_up
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Case, Count, F, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import formats, timezone

from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from rest_framework import serializers, status, viewsets
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from fiscallizeon.answers.models import (
    OptionAnswer, FileAnswer, TextualAnswer, RetryAnswer, SumAnswer, SumAnswerQuestionOption
)
from fiscallizeon.clients.permissions import IsCoordinationMember
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.core.authentication import ParentAuthentication
from fiscallizeon.core.utils import (
    CheckHasPermission,
    CheckHasPermissionAPI,
    format_value,
    percentage_value,
    percentage_formatted,
)
from fiscallizeon.exams.models import ExamQuestion, StatusQuestion
from fiscallizeon.exams.permissions import IsTeacherSubject
from fiscallizeon.inspectors.models import TeacherSubject
from fiscallizeon.questions.models import (
    Question, QuestionOption, Topic, Abiliity, Competence
)
from fiscallizeon.questions.permissions import IsStudentOwner
from fiscallizeon.subjects.models import Subject

from fiscallizeon.corrections.models import CorrectionTextualAnswer, CorrectionFileAnswer
from .models import Application, ApplicationStudent
from .serializers import ApplicationSerializer

from rest_framework.authentication import SessionAuthentication
from fiscallizeon.applications.mixins import StudentCanViewResultsMixin


class ExamQuestionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    question_pk = serializers.CharField(source='question.pk')
    enunciation = serializers.CharField(source='question.enunciation')
    alternatives = serializers.SerializerMethodField()
    answer = serializers.SerializerMethodField()
    checked_answers = serializers.SerializerMethodField()
    percent_grade = serializers.SerializerMethodField()
    teacher_grade = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    commented_awnser = serializers.CharField(source='question.commented_awnser')
    teacher_feedback = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    textual_answer = serializers.SerializerMethodField()
    file_answer = serializers.SerializerMethodField()
    img_annotations = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    subject_pk = serializers.SerializerMethodField()
    topics = serializers.SerializerMethodField()
    abilities = serializers.SerializerMethodField()
    competences = serializers.SerializerMethodField()
    number_print = serializers.SerializerMethodField()
    text_correction_answer = serializers.SerializerMethodField()
    have_correction_answer = serializers.SerializerMethodField()
    embbeded_answer_video = serializers.CharField(source='question.get_emmbbeded_video_answer')
    annuled = serializers.SerializerMethodField()
    annuled_give_score = serializers.SerializerMethodField()

    def get_annuled(self, obj):
        status = StatusQuestion.objects.filter(exam_question=obj, active=True).first()
        return status.status == StatusQuestion.ANNULLED if status else False
        
    def get_annuled_give_score(self, obj):
        status = StatusQuestion.objects.filter(exam_question=obj, active=True).first()
        return status.annuled_give_score if status else False
        
    class AlternativeSerializer(serializers.ModelSerializer):
        class Meta:
            model = QuestionOption
            fields = ('id', 'text', 'is_correct')

    class TopicSerializer(serializers.ModelSerializer):
        class Meta:
            model = Topic
            fields = ('id', 'name')

    class AbiliitySerializer(serializers.ModelSerializer):
        class Meta:
            model = Abiliity
            fields = ('id', 'text')

    class CompetenceSerializer(serializers.ModelSerializer):
        class Meta:
            model = Competence
            fields = ('id', 'text')

    def get_subject_object(self, obj):
        if obj.exam.is_abstract:
            return obj.question.subject if obj.question.subject else ""
        return obj.exam_teacher_subject.teacher_subject.subject
    
    def get_subject(self, obj):
        subject = self.get_subject_object(obj)
        if subject:
            return str(subject)
        return ""

    def get_subject_pk(self, obj):
        subject = self.get_subject_object(obj)
        if subject:
            return str(subject.pk)
        return ""
    
    def get_have_correction_answer(self, obj):
        if obj.question.category == Question.TEXTUAL:
            return CorrectionTextualAnswer.objects.filter(
                textual_answer__question=obj.question,
                textual_answer__student_application=self.context['application_student'],
            ).exists()
        if obj.question.category == Question.FILE:
            return CorrectionFileAnswer.objects.filter(
                file_answer__question=obj.question,
                file_answer__student_application=self.context['application_student'],
            ).exists()
        return False

    def get_text_correction_answer(self, obj):
        if obj.question.category == Question.TEXTUAL:
            textual = TextualAnswer.objects.filter(question=obj.question.pk, 
                student_application=self.context['application_student'],
                ).first()
            return CorrectionTextualAnswer.objects.filter(textual_answer=textual,
                ).values('correction_criterion__name', 'point').order_by('correction_criterion__order')
        
        if obj.question.category == Question.FILE:
            file = FileAnswer.objects.filter(question=obj.question.pk, 
                student_application=self.context['application_student'],
                ).first()
            return CorrectionFileAnswer.objects.filter(file_answer=file,
                ).values('correction_criterion__name', 'point').order_by('correction_criterion__order')
        
        return []


    def _get_student_answer(self, application_student, question):
        if question.category == Question.CHOICE:
            return (
                OptionAnswer.objects.filter(
                    question_option__question=question,
                    student_application=application_student,
                )
                .filter(status=OptionAnswer.ACTIVE)
                .order_by('-created_at')
            )
        elif question.category == Question.SUM_QUESTION:
            return SumAnswer.objects.filter(
                question=question,
                student_application=application_student,
            )
        elif question.category == Question.TEXTUAL:
            return TextualAnswer.objects.filter(
                question=question,
                student_application=application_student,
            )
        elif question.category == Question.FILE:
            return FileAnswer.objects.filter(
                question=question,
                student_application=application_student,
            )

        return None

    # def get_alternatives(self, obj):
    #     if obj.question.category not in [Question.CHOICE, Question.SUM_QUESTION]:
    #         return []

    #     return self.AlternativeSerializer(
    #         obj.question.alternatives.distinct(), many=True
    #     ).data
    

    def get_alternatives(self, exam_question):

        from fiscallizeon.applications.models import RandomizationVersion 
        from fiscallizeon.exams import json_utils

        if exam_question.question.category in [Question.CHOICE, Question.SUM_QUESTION]:
            alternatives = exam_question.question.alternatives.distinct()
            
            if self.context['application_student'].read_randomization_version > 0:
                randomization_version = RandomizationVersion.objects.filter(
                    application_student=self.context['application_student'],
                    version_number=self.context['application_student'].read_randomization_version
                ).first()
                
                question_json = list(filter(lambda _question: _question["pk"] == exam_question.question.id, json_utils.convert_json_to_choice_questions_list(randomization_version.exam_json)))
                alternatives_pks = [alternative for alternative in question_json[0]['alternatives']]
                preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(alternatives_pks)])
                alternatives = alternatives.order_by(preserved)
            
            return self.AlternativeSerializer(alternatives, many=True).data
        
        return []


    def get_category(self, obj):
        return obj.question.get_category_display()

    def get_textual_answer(self, obj):
        answers = TextualAnswer.objects.filter(
            question=obj.question,
            student_application=self.context['application_student'],
        ).order_by('-created_at')

        if answers:
            return answers[0].content

        return None

    def get_file_answer(self, obj):
        answers = FileAnswer.objects.filter(
            question=obj.question,
            student_application=self.context['application_student'],
        ).order_by('-created_at')

        if answers and answers[0].arquivo:
            return answers[0].arquivo.url

        return None

    def get_img_annotations(self, obj):
        answers = FileAnswer.objects.filter(
            question=obj.question,
            student_application=self.context['application_student'],
        ).order_by('-created_at')

        if answers and answers[0].arquivo:
            return answers[0].img_annotations

        return None

    def get_answer(self, obj):
        active_answers = (
            OptionAnswer.objects.filter(
                question_option__question=obj.question,
                student_application=self.context['application_student'],
            )
            .filter(status=OptionAnswer.ACTIVE)
            .order_by('-created_at')
        )

        answer = active_answers.values('question_option__pk')

        if answer:
            return answer[0]['question_option__pk']

        return None
    
    def get_checked_answers(self, obj):
        sum_answers = SumAnswer.objects.filter(
            question=obj.question,
            student_application=self.context['application_student'], 
        )
        if sum_answers:
            return list(
                sum_answers[0].sumanswerquestionoption_set.filter(
                    checked=True
                ).values_list(
                    'question_option_id', flat=True
                )
            )        
        return []

    def get_percent_grade(self, obj):
        active_answers = self._get_student_answer(
            self.context['application_student'], obj.question
        )

        score = 0
        if obj.question.category == Question.CHOICE:
            active_answers_option = active_answers.values(
                'question_option__is_correct'
            )

            question_is_correct = None
            if active_answers_option:
                question_is_correct = active_answers_option[0][
                    'question_option__is_correct'
                ]

            if question_is_correct:
                score = Decimal(1.0)
        elif obj.question.category == Question.SUM_QUESTION:
            if active_answers:
                active_answer = active_answers[0]
                score = active_answer.grade
        else:
            if active_answers:
                active_answer = active_answers[0]
                if active_answer.grade:
                    score = active_answer.grade

        return score
    
    def get_teacher_grade(self, obj):
        active_answers = self._get_student_answer(
            self.context['application_student'], obj.question
        )

        score = 0
        if obj.question.category == Question.CHOICE:
            active_answers_option = active_answers.values(
                'question_option__is_correct'
            )

            question_is_correct = None
            if active_answers_option:
                question_is_correct = active_answers_option[0][
                    'question_option__is_correct'
                ]

            if question_is_correct:
                score = obj.weight
        elif obj.question.category == Question.SUM_QUESTION:
            if active_answers:
                active_answer = active_answers[0]
                score = active_answer.grade * obj.weight
        else:
            if active_answers:
                active_answer = active_answers[0]
                if active_answer.teacher_grade:
                    score = active_answer.teacher_grade

        return score

    def get_weight(self, obj):
        return obj.weight

    def get_teacher_feedback(self, obj):
        if obj.question.category in [Question.CHOICE, Question.SUM_QUESTION]:
            return None

        active_answers = self._get_student_answer(
            self.context['application_student'], obj.question
        )

        if not active_answers:
            return None

        return active_answers[0].teacher_feedback

    def get_topics(self, obj):
        return self.TopicSerializer(
            obj.question.topics.distinct(), many=True
        ).data

    def get_abilities(self, obj):
        return self.AbiliitySerializer(
            obj.question.abilities.distinct(), many=True
        ).data

    def get_competences(self, obj):
        return self.CompetenceSerializer(
            obj.question.competences.distinct(), many=True
        ).data

    def get_number_print(self, obj):
        return self.context['application_student'].application.exam.number_print_question(obj.question)


class ApplicationStudentSubjectDetailApi(LoginRequiredMixin, StudentCanViewResultsMixin, APIView):
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    permission_classes = (CheckHasPermissionAPI, IsCoordinationMember, IsStudentOwner, IsTeacherSubject)
    required_permissions = [
        settings.INSPECTOR,
        settings.STUDENT,
        settings.TEACHER,
        settings.COORDINATION,
        settings.PARENT,
    ]
    authentication_classes = (ParentAuthentication, SessionAuthentication)

    class OutputSerializer(serializers.Serializer):
        id = serializers.CharField()
        name = serializers.CharField()
        knowledge_area = serializers.CharField(source='knowledge_area.name')
        score = serializers.SerializerMethodField()
        performance = serializers.SerializerMethodField()
        topics = serializers.SerializerMethodField()
        abilities = serializers.SerializerMethodField()
        competences = serializers.SerializerMethodField()
        rank = serializers.SerializerMethodField() 

        def get_rank(self, obj):
            show_ranking = self.context['application_student'].application.exam.show_ranking
            if not show_ranking:
                return None

            application_student = self.context['application_student']
            rank_class, count_class = ApplicationStudent.get_rank(
                application_student,
                {'student__classes': application_student.get_last_class_student()},
                obj,
            )
            rank_unity, count_unity = ApplicationStudent.get_rank(
                application_student,
                {
                    'student__classes__coordination__unity': application_student.get_last_class_student().coordination.unity
                },
                obj,
            )
            rank_client, count_client = ApplicationStudent.get_rank(
                application_student,
                {'student__client': application_student.student.client},
                obj,
            )
            return {
                'class': {'value': rank_class, 'total': count_class},
                'unity': {'value': rank_unity, 'total': count_unity},
                'client': {'value': rank_client, 'total': count_client},
            }

        def get_score(self, obj):
            return format_value(self.context['application_student'].get_total_grade(subject=obj))

        def get_performance(self, obj):
            return percentage_formatted(
                self.context['application_student'].get_performance_v2(subject=obj)
            )

        def _get_performance(self, total, correct):
            if total <= 0:
                return 0

            return correct / total

        def _get_result(self, queryset, field):
            result = []
            for obj in queryset:
                name = obj[field]
                if not name:
                    name = 'Não definido'

                result.append(
                    {
                        'name': name,
                        'count': obj['count'],
                        'performance': percentage_value(
                            self._get_performance(
                                round_half_up(obj['weight'], 2), round_half_up(obj['score'], 2)
                            )
                        ),
                    }
                )

            return result

        def get_topics(self, obj):
            option_correct = (
                OptionAnswer.objects.filter(
                    question_option__question=OuterRef('question__pk'),
                    student_application=self.context['application_student'],
                    status=OptionAnswer.ACTIVE,
                ).order_by('-created_at')
            )

            textual_correct = (
                TextualAnswer.objects.filter(
                    question=OuterRef('question__pk'),
                    student_application=self.context['application_student'],
                    teacher_grade=OuterRef('weight'),
                ).annotate(
                    is_correct=Case(
                        When(teacher_grade=OuterRef('weight'), then=True),
                        default=False,
                    )
                )
                .order_by('-created_at')
            )

            file_correct = (
                FileAnswer.objects.filter(
                    question=OuterRef('question__pk'),
                    student_application=self.context['application_student'],
                    teacher_grade=OuterRef('weight'),
                ).annotate(
                    is_correct=Case(
                        When(teacher_grade=OuterRef('weight'), then=True),
                        default=False,
                    )
                )
                .order_by('-created_at')
            )

            extra_filters = {'exam_teacher_subject__teacher_subject__subject': obj}
            if self.context['application_student'].application.exam.is_abstract:
                extra_filters = {'question__subject': obj}

            exam_questions = (
                ExamQuestion.objects.filter(
                    exam=self.context['application_student'].application.exam,
                    **extra_filters,
                )
                .annotate(
                    is_correct=Subquery(
                        option_correct.values('question_option__is_correct')[:1]
                    ),
                    is_correct_textual=Subquery(
                        textual_correct.values('is_correct')[:1]
                    ),
                    is_correct_file=Subquery(
                        file_correct.values('is_correct')[:1]
                    ),
                )
                .values('question__topics__name')
                .annotate(
                    count=Count('pk'),
                    score=Coalesce(
                        Sum('weight', filter=Q(
                            Q(is_correct=True) | Q(is_correct_textual=True) | Q(is_correct_file=True)
                        )), Decimal('0')
                    ),
                    weight=Sum('weight'),
                )
            )

            return self._get_result(exam_questions, 'question__topics__name')

        def get_abilities(self, obj):
            option_correct = (
                OptionAnswer.objects.filter(
                    question_option__question=OuterRef('question__pk'),
                    student_application=self.context['application_student'],
                    status=OptionAnswer.ACTIVE,
                ).order_by('-created_at')
            )

            textual_correct = (
                TextualAnswer.objects.filter(
                    question=OuterRef('question__pk'),
                    student_application=self.context['application_student'],
                    teacher_grade=OuterRef('weight'),
                ).annotate(
                    is_correct=Case(
                        When(teacher_grade=OuterRef('weight'), then=True),
                        default=False,
                    )
                )
                .order_by('-created_at')
            )

            file_correct = (
                FileAnswer.objects.filter(
                    question=OuterRef('question__pk'),
                    student_application=self.context['application_student'],
                    teacher_grade=OuterRef('weight'),
                ).annotate(
                    is_correct=Case(
                        When(teacher_grade=OuterRef('weight'), then=True),
                        default=False,
                    )
                )
                .order_by('-created_at')
            )

            extra_filters = {'exam_teacher_subject__teacher_subject__subject': obj}
            if self.context['application_student'].application.exam.is_abstract:
                extra_filters = {'question__subject': obj}

            exam_questions = (
                ExamQuestion.objects.filter(
                    exam=self.context['application_student'].application.exam,
                    **extra_filters,
                )
                .annotate(
                    is_correct=Subquery(
                        option_correct.values('question_option__is_correct')[:1]
                    ),
                    is_correct_textual=Subquery(
                        textual_correct.values('is_correct')[:1]
                    ),
                    is_correct_file=Subquery(
                        file_correct.values('is_correct')[:1]
                    ),
                )
                .values('question__abilities__text')
                .annotate(
                    count=Count('pk'),
                    score=Coalesce(
                        Sum('weight', filter=Q(
                            Q(is_correct=True) | Q(is_correct_textual=True) | Q(is_correct_file=True)
                        )), Decimal('0')
                    ),
                    weight=Sum('weight'),
                )
            )

            return self._get_result(exam_questions, 'question__abilities__text')

        def get_competences(self, obj):
            option_correct = (
                OptionAnswer.objects.filter(
                    question_option__question=OuterRef('question__pk'),
                    student_application=self.context['application_student'],
                    status=OptionAnswer.ACTIVE,
                ).order_by('-created_at')
            )

            textual_correct = (
                TextualAnswer.objects.filter(
                    question=OuterRef('question__pk'),
                    student_application=self.context['application_student'],
                    teacher_grade=OuterRef('weight'),
                ).annotate(
                    is_correct=Case(
                        When(teacher_grade=OuterRef('weight'), then=True),
                        default=False,
                    )
                )
                .order_by('-created_at')
            )

            file_correct = (
                FileAnswer.objects.filter(
                    question=OuterRef('question__pk'),
                    student_application=self.context['application_student'],
                    teacher_grade=OuterRef('weight'),
                ).annotate(
                    is_correct=Case(
                        When(teacher_grade=OuterRef('weight'), then=True),
                        default=False,
                    )
                )
                .order_by('-created_at')
            )

            extra_filters = {'exam_teacher_subject__teacher_subject__subject': obj}
            if self.context['application_student'].application.exam.is_abstract:
                extra_filters = {'question__subject': obj}

            exam_questions = (
                ExamQuestion.objects.filter(
                    exam=self.context['application_student'].application.exam,
                    **extra_filters,
                )
                .annotate(
                    is_correct=Subquery(
                        option_correct.values('question_option__is_correct')[:1]
                    ),
                    is_correct_textual=Subquery(
                        textual_correct.values('is_correct')[:1]
                    ),
                    is_correct_file=Subquery(
                        file_correct.values('is_correct')[:1]
                    ),
                )
                .values('question__competences__text')
                .annotate(
                    count=Count('pk'),
                    score=Coalesce(
                        Sum('weight', filter=Q(
                            Q(is_correct=True) | Q(is_correct_textual=True) | Q(is_correct_file=True)
                        )), Decimal('0')
                    ),
                    weight=Sum('weight'),
                )
            )

            return self._get_result(exam_questions, 'question__competences__text')

    def get_object(self):
        return get_object_or_404(
            ApplicationStudent.objects.all(),
            pk=self.kwargs.get('application_student_id'),
        )

    def get(self, request, application_student_id, subject_id):
        application_student = self.get_object()

        subject = get_object_or_404(Subject.objects.all(), pk=subject_id)

        serializer = self.OutputSerializer(
            subject,
            context={'application_student': application_student},
        )

        return Response(serializer.data)


class ApplicationStudentQuestionDetailApi(LoginRequiredMixin, StudentCanViewResultsMixin, APIView):
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    permission_classes = (CheckHasPermissionAPI, IsCoordinationMember, IsStudentOwner, IsTeacherSubject)
    required_permissions = [
        settings.INSPECTOR,
        settings.STUDENT,
        settings.TEACHER,
        settings.COORDINATION,
        settings.PARENT,
    ]
    authentication_classes = (ParentAuthentication, SessionAuthentication)

    class OutputSerializer(ExamQuestionSerializer):
        pass

    def get_object(self):
        return get_object_or_404(
            ApplicationStudent.objects.all(),
            pk=self.kwargs.get('application_student_id'),
        )

    def get(self, request, application_student_id, question_id):
        application_student = self.get_object()
        
        exam_question = get_object_or_404(
            ExamQuestion.objects.all(),
            question=question_id,
            exam=application_student.application.exam,
        )

        serializer = self.OutputSerializer(
            exam_question,
            context={'application_student': application_student},
        )

        return Response(serializer.data)


class ApplicationStudentSubjectChartDetailApi(LoginRequiredMixin, StudentCanViewResultsMixin, APIView):
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    permission_classes = (CheckHasPermissionAPI, IsCoordinationMember, IsStudentOwner, IsTeacherSubject)
    required_permissions = [
        settings.INSPECTOR,
        settings.STUDENT,
        settings.TEACHER,
        settings.COORDINATION,
        settings.PARENT,
    ]
    authentication_classes = (ParentAuthentication, SessionAuthentication)

    class OutputSerializer(serializers.Serializer):
        id = serializers.CharField()
        name = serializers.CharField()
        applications_student = serializers.SerializerMethodField()

        def get_applications_student(self, obj):
            application_student = self.context['application_student']

            extra_filters = {
                'application__exam__examquestion__exam_teacher_subject__teacher_subject__subject': obj
            }
            if application_student.application.exam.is_abstract:
                extra_filters = {
                    'application__exam__examquestion__question__subject': obj
                }

            applications_student = (
                ApplicationStudent.objects.filter(
                    student=application_student.student.pk,
                    application__date__lte=application_student.application.date,
                    application__date__year=application_student.application.date.year,
                    application__exam__category=application_student.application.exam.category,
                    **extra_filters,
                )

                .order_by('-application__date')
                .distinct()
            )
            
            """ Verifica se o aluno é da mentorizze """
            if application_student.student.client.type_client == 3: 
                applications_student = applications_student.filter(
                    end_time__isnull=False
                )
            else:
                applications_student = applications_student.filter(
                    application__student_stats_permission_date__lte=timezone.now(),
                )
                
            return list(
                reversed(
                    [
                        {
                            'name': f'{application_student.application.exam.name} - {formats.date_format(application_student.application.date, "SHORT_DATE_FORMAT")}',
                            'performance': format_value(
                                application_student.get_performance(obj)
                            ),
                        }
                        for application_student in applications_student[:5]
                    ]
                )
            )

    def get_object(self):
        return get_object_or_404(
            ApplicationStudent.objects.all(),
            pk=self.kwargs.get('application_student_id'),
        )

    def get(self, request, application_student_id, subject_id):
        application_student = self.get_object()

        subject = get_object_or_404(Subject.objects.all(), pk=subject_id)

        serializer = self.OutputSerializer(
            subject,
            context={'application_student': application_student},
        )

        return Response(serializer.data)


class ApplicationStudentQuestionListApi(LoginRequiredMixin, StudentCanViewResultsMixin, APIView):
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    permission_classes = (CheckHasPermissionAPI, IsCoordinationMember, IsStudentOwner, IsTeacherSubject)
    required_permissions = [
        settings.STUDENT,
    ]
    authentication_classes = (ParentAuthentication, SessionAuthentication)
    
    class FilterSerializer(serializers.Serializer):
        subject = serializers.UUIDField(required=False)
        topic = serializers.UUIDField(required=False)
        ability = serializers.UUIDField(required=False)
        competence = serializers.UUIDField(required=False)
        empty = serializers.BooleanField(required=False)

        def validate(self, data):
            if not data:
                raise serializers.ValidationError('Must include at least one field.')

            return data

    class OutputSerializer(serializers.Serializer):
        id = serializers.UUIDField()
        number_print = serializers.SerializerMethodField()
        category = serializers.SerializerMethodField()
        kind = serializers.SerializerMethodField()
        absolute_url = serializers.SerializerMethodField()
        enunciation = serializers.CharField()
        weight = serializers.SerializerMethodField()
        knowledge_area = serializers.SerializerMethodField()
        topics = serializers.SerializerMethodField()
        abilities = serializers.SerializerMethodField()
        competences = serializers.SerializerMethodField()
        already_retry = serializers.SerializerMethodField()

        class TopicSerializer(serializers.ModelSerializer):
            class Meta:
                model = Topic
                fields = ('id', 'name')

        class AbiliitySerializer(serializers.ModelSerializer):
            class Meta:
                model = Abiliity
                fields = ('id', 'text')

        class CompetenceSerializer(serializers.ModelSerializer):
            class Meta:
                model = Competence
                fields = ('id', 'text')

        def get_number_print(self, obj):
            return self.context['application_student'].application.exam.number_print_question(obj)

        def get_category(self, obj):
            return obj.category

        def get_kind(self, obj):
            kind = ''
            if obj.is_partial:
                kind = 'Parcial'
            elif obj.is_incorrect:
                kind = 'Errou'
            elif not obj.teacher_grade:
                kind = 'Aguar/ c.'
            else:
                kind = 'S/ resp.'

            return kind

        def get_absolute_url(self, obj):
            return obj.get_absolute_url(self.context['application_student'].pk)

        def get_weight(self, obj):
            return obj.question_weight

        def get_knowledge_area(self, obj):
            if not obj.subject:
                return ''

            return obj.subject.knowledge_area.name

        def get_topics(self, obj):
            return self.TopicSerializer(obj.topics.distinct(), many=True).data

        def get_abilities(self, obj):
            return self.AbiliitySerializer(obj.abilities.distinct(), many=True).data

        def get_competences(self, obj):
            return self.CompetenceSerializer(obj.competences.distinct(), many=True).data

        def get_already_retry(self, obj):
            exam_question = ExamQuestion.objects.get(
                question=obj,
                exam__application__applicationstudent=self.context['application_student'],
            )
            return RetryAnswer.objects.filter(
                application_student=self.context['application_student'],
                exam_question=exam_question,
            ).exists()

    def get_object(self):
        return get_object_or_404(
            ApplicationStudent.objects.all(),
            pk=self.kwargs.get('application_student_id'),
        )

    def get(self, request, application_student_id):
        application_student = self.get_object()

        filters_serializer = self.FilterSerializer(data=request.query_params)
        filters_serializer.is_valid(raise_exception=True)

        order_by_list = ['examquestion__exam_teacher_subject__order', 'examquestion__order']
        filter_field = 'examquestion__exam_teacher_subject__teacher_subject__subject'
        if application_student.application.exam.is_abstract:
            order_by_list = ['examquestion__order']
            filter_field = 'examquestion__question__subject'

        qs = (
            Question.objects.availables(application_student.application.exam, exclude_annuleds=True)
            .get_application_student_report(application_student)
            .filter(
                Q(
                    Q(
                        is_correct=False
                    ) | 
                    Q(
                        is_none=True
                    )
                )
            )
            .order_by(*order_by_list)
        )

        exam_questions = []
        if filters_serializer.validated_data.get('empty', False):
            exam_questions = qs.filter(
                examquestion__exam=application_student.application.exam,
                **{filter_field: None},
            )
        elif subject := filters_serializer.validated_data.get('subject', None):
            exam_questions = qs.filter(
                examquestion__exam=application_student.application.exam,
                **{filter_field: subject},
            )

        elif topic := filters_serializer.validated_data.get('topic', None):
            exam_questions = qs.filter(topics=topic)
        elif ability := filters_serializer.validated_data.get('ability', None):
            exam_questions = qs.filter(abilities=ability)
        elif competence := filters_serializer.validated_data.get('competence', None):
            exam_questions = qs.filter(competences=competence)

        serializer = self.OutputSerializer(
            exam_questions.distinct(),
            many=True,
            context={'application_student': application_student}
        )

        return Response(serializer.data)


class ApplicationStudentQuestionRetryApi(LoginRequiredMixin, StudentCanViewResultsMixin, APIView):
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    permission_classes = (CheckHasPermissionAPI, IsCoordinationMember, IsStudentOwner, IsTeacherSubject)
    required_permissions = [
        settings.INSPECTOR,
        settings.STUDENT,
        settings.TEACHER,
        settings.COORDINATION,
    ]
    authentication_classes = (CsrfExemptSessionAuthentication,)

    class InputSerializer(serializers.Serializer):
        option = serializers.UUIDField()

    def get_object(self):
        return get_object_or_404(
            ApplicationStudent.objects.all(),
            pk=self.kwargs.get('application_student_id'),
        )

    def post(self, request, application_student_id, question_id):
        application_student = self.get_object()

        exam_question = get_object_or_404(
            ExamQuestion.objects.all(),
            question=question_id,
            exam=application_student.application.exam,
        )

        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        option = get_object_or_404(
            QuestionOption.objects.all(),
            pk=serializer.validated_data['option'],
        )

        try:
            retry_answer = RetryAnswer.objects.get(
                application_student=application_student, exam_question=exam_question
            )
            retry_answer.option = option
            retry_answer.save()
        except RetryAnswer.DoesNotExist:
            RetryAnswer.objects.create(
                application_student=application_student,
                exam_question=exam_question,
                option=option,
            )

        return Response({'detail': 'Ok'})


class CustomLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 10


class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    pagination_class = CustomLimitOffsetPagination
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        
        queryset = queryset.filter(exam__coordinations__unity__client=user.client)
        
        if user.user_type == settings.TEACHER:
            queryset = queryset.filter(exam__created_by=user)
                
        return queryset.distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context