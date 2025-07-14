from datetime import datetime

from fiscallizeon.students.models import Student
from fiscallizeon.answers.models import OptionAnswer, SumAnswer, TextualAnswer, FileAnswer, QuestionOption, SumAnswerQuestionOption
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.core.permissions import IsStudentUser, CanAccessApp
from fiscallizeon.applications.models import ApplicationStudent, Application
from fiscallizeon.core.utils import SimpleAPIPagination 
from fiscallizeon.questions.models import Question
from fiscallizeon.exams.models import StatusQuestion
from fiscallizeon.subjects.models import Subject, KnowledgeArea
from fiscallizeon.materials.models import StudyMaterial, FavoriteStudyMaterial
from fiscallizeon.inspectors.models import TeacherSubject

from django_filters.rest_framework import DjangoFilterBackend

from django.db import transaction
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from fiscallizeon.core.utils import CamelCaseAPIMixin
from .serializers import (
    ApplicationStudentSerializer,
    StudentSerializer,
    SchoolClassSerializer,
    ColleaguesSerializer,
    StudyMaterialSerializer,
    TakeTestExamQuestionSerializer,
    SimpleExamQuestionSerializer,
    PreviousFeedbackSerializer,
    ExamQuestionResultSerializer,
    SimpleSubjectSerializer,
)
from ..answers.serializers import (
    CreateAnswerSerializer,
)
from ..answers.functions import get_answer_object
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Avg, Q, Value, Subquery, OuterRef, Case, When, BooleanField
from fiscallizeon.core.utils import (
    format_value, percentage_formatted
)

class ApplicationStudentViewSet(CamelCaseAPIMixin, viewsets.ModelViewSet):
    serializer_class = ApplicationStudentSerializer
    permission_classes = (permissions.IsAuthenticated, IsStudentUser, CanAccessApp)
    model = ApplicationStudent
    queryset = ApplicationStudent.objects.all()
    filter_backends = [DjangoFilterBackend]
    pagination_class = SimpleAPIPagination
    filterset_fields = { 
        'application__date' : ['in', 'exact', 'year'],
        'application__exam__teacher_subjects__subject' : ['in', 'exact'],
        'application__category' : ['in', 'exact'],
        'application__exam__name' : ['icontains'],
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        queryset = queryset.filter(student=user.student)
        
        if self.request.GET.get('only_scheduled'):
            only_scheduled_ids = queryset.only_scheduled().values_list('id', flat=True)
            queryset = queryset.filter(id__in=only_scheduled_ids)
        
        if self.request.GET.get('without_scheduled'):
            only_scheduled_ids = queryset.only_scheduled().values_list('id', flat=True)
            queryset = queryset.exclude(id__in=only_scheduled_ids)
        
        if self.request.GET.get('recently_released_results'):
            queryset = queryset.recently_released_results(return_all=True)
            
        if self.request.GET.get('without_finished_in'):
            queryset = queryset.filter(start_time__isnull=True, end_time__isnull=True)
        
        return queryset.order_by('-application__date', '-application__student_stats_permission_date')
    
    def can_access_application(self, application_student):
        
        user = self.request.user
        
        if application_student.application.category == Application.HOMEWORK:
            if application_student.already_reached_max_time_finish:
                print('O tempo dessa atividade já foi encerrado!')
                return Response({ 'message':'O tempo dessa atividade já foi encerrado!'}, status=status.HTTP_403_FORBIDDEN)
        else:
            if application_student.application.is_time_finished:
                print('O tempo dessa avaliação já foi encerrado!')
                return Response({ 'message':'O tempo dessa avaliação já foi encerrado!'}, status=status.HTTP_403_FORBIDDEN)

        if not application_student.application.is_happening:
            print('A avaliação não esta disponível!')
            return Response({ 'message':'A avaliação não esta disponível!'}, status=status.HTTP_403_FORBIDDEN)

        if application_student.application_state == 'finished' and not application_student.application.allow_student_redo_list:
            print('Sua avaliação já foi finalizada!')
            return Response({ 'message':'Sua avaliação já foi finalizada!'}, status=status.HTTP_403_FORBIDDEN)

        if application_student.student.user != user:
            print('Você não tem permissão para acessar esta avaliação!')
            return Response({ 'message':'Você não tem permissão para acessar esta avaliação!'}, status=status.HTTP_403_FORBIDDEN)
    
    def can_access_application_after_result(self, application_student):
        deny_student_stats_view = False
        
        view_exam_permission_date = application_student.application.student_stats_permission_date
        
        if view_exam_permission_date:
            today = timezone.now().astimezone()
            deny_student_stats_view = (
                view_exam_permission_date > today
            )

        if not application_student.application.student_stats_permission_date and not application_student.application.release_result_at_end:
            return Response({ 'message':'Você não tem permissão para ver o resultado da avaliação'}, status=status.HTTP_401_UNAUTHORIZED)
        if application_student.application.release_result_at_end:
            if not application_student.end_time and not application_student.application.is_time_finished:
                return Response({ 'message':'Você não tem permissão para ver o resultado da avaliação'}, status=status.HTTP_401_UNAUTHORIZED)
        elif not application_student.application.is_time_finished or deny_student_stats_view:
            return Response({ 'message':'Você não tem permissão para ver o resultado da avaliação'}, status=status.HTTP_401_UNAUTHORIZED)
    
    @action(detail=False, methods=["GET"])
    def availables_today(self, request, pk=None):
        """
            Todas as aplicações disponíveis para o aluno realizar
        """
        
        queryset = self.get_queryset().is_online().availables_today()
        
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        
        return Response(serializer.data)
    
    @action(detail=True, methods=["GET"])
    def questions(self, request, pk=None):
        """
            Trás os dados das questões, mas não pode trazer nenhuma resposta, nem alernativa correta
        """
        application_student = self.get_object()
        exam_questions = application_student.application.exam.examquestion_set.availables()
        
        return Response(SimpleExamQuestionSerializer(instance=exam_questions, many=True).data)
    
    @action(detail=True, methods=["GET"])
    def previous_feedback(self, request, pk=None):
        """
            Trás os dados do gabarito prévio, muito cuidado com qualquer alteração feita nessa rota.
        """
        user = self.request.user
        application_student = self.get_object()
        
        if  not user.client_show_previews_template_student:
            return Response({ 'message':'Sua instituição não tem acesso a este serviço.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if application_student.application.has_open_applications_exam or not application_student.application.is_time_finished:
            return Response({ 'message':'Só é possível acessar o gabarito prévio após a finalização da avaliação.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(PreviousFeedbackSerializer(instance=application_student).data)
    
    @action(detail=True, methods=["GET"])
    def take_test(self, request, pk=None):
        """
            Iniciar uma avaliação, deve trazer todos os dados das questões e as respostas dos alunos
        """
        from .serializers import KnowledgeAreaSerializer
        application_student = self.get_object()

        if error := self.can_access_application(application_student):
            return error
        
        subjects = []
        
        for exam_teacher_subject in application_student.application.exam.examteachersubject_set.order_by('order'):
            
            subject = exam_teacher_subject.teacher_subject.subject
            subject_id = str(subject.id)
            exam_questions = exam_teacher_subject.examquestion_set.availables().order_by('order')

            if founded_subject := next((x for x in subjects if x['subject_id'] == subject_id), None):
                if subjects[-1]['subject_id'] == subject_id:
                    subjects[-1]['exam_questions'].extend(TakeTestExamQuestionSerializer(instance=exam_questions, many=True, context={ 'application_student': application_student }).data)
                    continue
                 
            subjects.append({
                'id': subject_id,
                'subject_id': subject_id,
                'name': subject.name,
                'knowledge_area': KnowledgeAreaSerializer(instance=subject.knowledge_area).data,
                'exam_questions': TakeTestExamQuestionSerializer(instance=exam_questions, many=True, context={ 'application_student': application_student }).data,
            })
        data = {
            'id': application_student.id,
            'started_in': application_student.start_time,
            'ended_in': application_student.end_time,
            'application': {
                'id': application_student.application.id,
                'start_date': datetime.combine(application_student.application.date, application_student.application.start),
                'end_date': datetime.combine(application_student.application.date_end if application_student.application.category == Application.HOMEWORK else application_student.application.date , application_student.application.end),
                'exam': {
                    'id': application_student.application.exam.id,
                    'name': application_student.application.exam.name,
                    'subjects': subjects,
                },
                'orientations': application_student.application.orientations,
            },
        }
        return Response(data)
    
    @action(detail=True, methods=["GET"])
    def grade(self, request, pk=None):
        """
            Ver resultado de uma aplicação
        """
        user = self.request.user
        application_student: ApplicationStudent = self.get_object()
        
        if not application_student.can_view_grade:
            return Response({ 'message': 'Você não tem permissão para acessar o resultado dessa avaliação.' }, status=status.HTTP_403_FORBIDDEN)
        
        application_student_id = str(application_student.id)
        
        grade = self.get_queryset().filter(id=application_student_id).get_annotation_count_answers(only_total_grade=True).first().total_grade

        result_object = {
            'id': application_student_id,
            'grade': grade,
        }
        
        CACHE_KEY = f'APPLICATION_STUDENT_GRADE_{application_student.id}'
        
        if not cache.get(CACHE_KEY):
            cache.set(CACHE_KEY, result_object, 60)

        return Response(cache.get(CACHE_KEY))
    
    @action(detail=True, methods=["GET"])
    def result(self, request, pk=None):
        """
            Ver resultado de uma aplicação
        """
        user = self.request.user
        application_student: ApplicationStudent = self.get_object()
        exam = application_student.application.exam
        subjects = []
        randomization_version = application_student.randomization_versions.filter(version_number=application_student.read_randomization_version).first()
        
        
        if error := self.can_access_application_after_result(application_student=application_student):
            return error
        
        APPLICATIONS_CACHE_KEY = f'APPLICATION_STUDENT_RESULTS_QUESTIONS_{application_student.id}'
        
        if not cache.get(APPLICATIONS_CACHE_KEY):
            questions = (
                Question.objects.availables(exam)
                .select_related('subject', 'subject__knowledge_area','grade')
                .get_application_student_report(application_student, only_answers=True)
                .order_by(
                    'examquestion__exam_teacher_subject__order', 'examquestion__order'
                ).annotate(
                    last_status=Subquery(
                        StatusQuestion.objects.filter(
                            active=True, 
                            exam_question__question=OuterRef('pk'), 
                            exam_question__exam=exam
                        ).order_by('-created_at').values('status')[:1]),
                    give_score=Subquery(
                        StatusQuestion.objects.filter(
                            active=True,
                            exam_question__question=OuterRef('pk'),
                            exam_question__exam=exam,
                            annuled_give_score=True
                        ).order_by('-created_at').values('annuled_give_score')[:1]
                    ),
                    annuled=Case(
                        When(
                            Q(last_status=StatusQuestion.ANNULLED),
                            then=Value(True)
                        ), default=Value(False)
                    )
                )
            )
            cache.set(APPLICATIONS_CACHE_KEY, questions, 60)
        else:
            questions = cache.get(APPLICATIONS_CACHE_KEY)
        
        EXAMTEACHER_CACHE_KEY = f'APPLICATION_STUDENT_RESULTS_EXAMTEACHER_SUBJECTS_{application_student.id}'

        if not cache.get(EXAMTEACHER_CACHE_KEY):
            exam = application_student.application.exam
            exam_questions = exam.examquestion_set.all()
            is_enem_simulator = exam.is_enem_simulator
            examteacher_subjects = exam.examteachersubject_set.select_related('teacher_subject', 'teacher_subject__subject').order_by().distinct('teacher_subject__subject')

            for exam_teacher_subject in examteacher_subjects:

                details = ApplicationStudent.objects.filter(pk=application_student.id).get_annotation_count_answers(subjects=[exam_teacher_subject.teacher_subject.subject], exclude_annuleds=True, only_total_answers=True).first()

                subjects.append({
                    "subject": exam_teacher_subject.teacher_subject.subject.name,
                    "subject_id": exam_teacher_subject.teacher_subject.subject.id,
                    "knowledge_area": exam_teacher_subject.teacher_subject.subject.knowledge_area.name if exam_teacher_subject.teacher_subject.subject.knowledge_area else "Sem disciplina",
                    "examquestions_count": exam_questions.filter(
                        exam_teacher_subject__teacher_subject__subject=exam_teacher_subject.teacher_subject.subject
                    ).distinct().availables().count(),
                    "correct_count": details.total_correct_answers,
                    "incorrect_count": details.total_incorrect_answers,
                    "partial_count": details.total_partial_answers,
                    "score": application_student.get_total_grade(subject=exam_teacher_subject.teacher_subject.subject) if not is_enem_simulator else 0,
                    "performance": percentage_formatted(application_student.get_performance_v2(subject=exam_teacher_subject.teacher_subject.subject)),
                    "total_weight": exam.get_total_weight(extra_filters=Q(exam_teacher_subject__teacher_subject__subject=exam_teacher_subject.teacher_subject.subject)),
                })

            cache.set(EXAMTEACHER_CACHE_KEY, subjects, 60)
        else:
            subjects = cache.get(EXAMTEACHER_CACHE_KEY)
        
        # dados das questões
        questions_data = []
        for question in questions:
            question_data = {}
            question_data['id'] = question.pk
            question_data['number'] = exam.number_print_question(question, randomization_version=randomization_version)
            question_data['give_score'] = question.give_score
            question_data['annuled'] = question.annuled
            question_data['percent_grade'] = (question.percent_grade or 0) * 100
            question_data['teacher_grade'] = question.teacher_grade
            question_data['is_correct'] = question.is_correct
            question_data['is_incorrect'] = question.is_incorrect
            question_data['is_partial'] = question.is_partial
            question_data['category'] = question.category
            question_data['category_display'] = question.get_category_display()
            question_data['await_correction'] = True if not question.teacher_grade else False
            
            questions_data.append(question_data)
        
        # dados da aplicação
        questions_count = questions.count()
        questions_without_annuleds = questions.availables(exam, exclude_annuleds=True)
        correct_count = questions_without_annuleds.filter(is_correct=True).distinct().count()
        partial_count = questions_without_annuleds.filter(is_partial=True).count()
        incorrect_count = questions_without_annuleds.filter(is_incorrect=True).count()
        
        application_data = {
            "application": {
                "date": application_student.application.date,
                "start": application_student.application.start,
                "end": application_student.application.end,
                "exam": {
                    "name": application_student.application.exam.name,
                }
            },
            "correct_count": correct_count,
            "partial_count": partial_count,
            "incorrect_count": incorrect_count,
            "performance": application_student.get_performance_v2(),
            "score": application_student.get_total_grade(),
            "questions_count": questions_count,
            "questions_data": questions_data,
            "subjects": subjects,
            "files": application_student.get_files_urls(return_object=True)
        }
        
        return Response(application_data)
    
    @action(detail=True, methods=["POST"])
    def create_answer(self, request, pk=None):
        """
            Cria as respostas do aluno,
            Peguei a mesma lógica que ta em fiscallizeon/answers/mixins.py SaveRestrictionUserMixin
        """
        user = self.request.user
        student = user.student
        application_student: ApplicationStudent = self.get_object()
        
        if error := self.can_access_application(application_student):
            return error
        
        serializer = CreateAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        question_category = serializer.data.get('category')
        exam_question = ExamQuestion.objects.get(pk=serializer.data.get('exam_question'))
        
        CATEGORIES = {
            'option': Question.CHOICE,
            'sum': Question.SUM_QUESTION,
            'textual': Question.TEXTUAL,
            'file': Question.FILE,
            Question.CHOICE: Question.CHOICE,
            Question.SUM_QUESTION: Question.SUM_QUESTION,
            Question.TEXTUAL: Question.TEXTUAL,
            Question.FILE: Question.FILE,
        }
        
        if CATEGORIES[question_category] != exam_question.question.category:
            return Response({ 'message': f'Você não pode salvar a questão do tipo {question_category} em uma questão do tipo {exam_question.question.get_category_display()}'}, status=status.HTTP_401_UNAUTHORIZED)
        
        options = serializer.data.get('options')
        max_index = max(list(map(lambda x: x.get('index'), options))) if options else 0
        
        if question_category == 'option':
            
            option, index = options[0].get('option'), options[0].get('index')
            OptionAnswer.objects.create(
                created_by=user,
                student_application=application_student,
                question_option=QuestionOption.objects.get(id=option),
                index_alternative=index,
            )
                
        elif question_category == 'sum':
            indexes = []
            alternatives = exam_question.question.alternatives.all().order_by('index')
            
            # faz a checagem para ver se tem algum index incorreto
            if max_index > alternatives.count() - 1:
                return Response({ 'message': 'O index da alternativa não existe.' }, status=status.HTTP_401_UNAUTHORIZED)
            
            sum_answer, created = SumAnswer.objects.update_or_create(
                question=exam_question.question,
                student_application=application_student,
                defaults={
                    'empty': False,
                    'created_by': user,
                }
            )
            
            if not created:
                sum_answer.question_options.clear()
                        
            for opt in options:
                option, index = opt.get('option'), opt.get('index')
                question_option = alternatives.get(id=option)
                SumAnswerQuestionOption.objects.create(
                    sum_answer=sum_answer,
                    question_option=question_option,
                    checked=True
                )
                indexes.append(index)
            
            sum_answer.value = sum_answer.get_value_using_indexes(indexes)
            sum_answer.grade = sum_answer.get_grade_proportion()
            sum_answer.save()
            
        elif question_category == 'textual':
            textual_answer, created = TextualAnswer.objects.update_or_create(
                student_application=application_student,
                question=exam_question.question,
                defaults={
                    'exam_question': exam_question,
                    'content': serializer.data.get('text'),
                }
            )
            if created:
                textual_answer.created_by = user
                textual_answer.save(skip_hooks=True)
        
        return Response(get_answer_object(application_student=application_student, question=exam_question.question))
    
    @action(detail=True, methods=["PATCH"])
    def start(self, request, pk=None):
        application_student = self.get_object()
        data = request.data            
        
        if error := self.can_access_application(application_student):
            return error
        
        if justification_delay := data.get('justification_delay'):
            application_student.justification_delay = justification_delay
            application_student.save(skip_hooks=True)

        if not application_student.start_time:
            application_student.start_time = timezone.now()
            application_student.save(skip_hooks=True)
        return Response({'detail': 'Ok.'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=["PATCH"])
    def finish(self, request, pk=None):
        application_student = self.get_object()
        empty_questions = request.data.get('empty_questions', 0)

        if application_student.can_be_finished or application_student.application.category == Application.HOMEWORK:
            application_student.end_time = timezone.now().astimezone()
            application_student.empty_questions = empty_questions
            application_student.save()
            return Response({'detail': 'Ok.'}, status=status.HTTP_200_OK)
        else:
            return Response({ 'message': 'Não é possível finalizar a avaliação.' },status=status.HTTP_403_FORBIDDEN)
        
    @action(detail=True, methods=["GET"])
    def question_detail_with_answer(self, request, pk=None, question_id=None):
                
        application_student = self.get_object()
        question_id = self.request.GET.get("question_id")
        
        if error := self.can_access_application_after_result(application_student=application_student):
            return error
        
        if not question_id:
            return Response({ 'message': 'Você deve informar question_id para utilizar esta rota' }, status=status.HTTP_400_BAD_REQUEST)
        
        exam_question = application_student.application.exam.examquestion_set.get(question=question_id)
        randomization_version = application_student.randomization_versions.filter(version_number=application_student.read_randomization_version).first()

        return Response(ExamQuestionResultSerializer(instance=exam_question, context={'application_student': application_student, 'randomization_version': randomization_version}).data)

    
    @action(detail=False, methods=["GET"])
    def get_filters(self, request, pk=None, question_id=None):
        
        return Response({
            'subjects': SimpleSubjectSerializer(instance=self.request.user.get_availables_subjects(), many=True).data,
        })
            
    @action(detail=True, methods=["GET"])
    def redo_application(self, request, pk=None):
        application_student = self.get_object()
        application_student.start_time = None
        application_student.end_time = None
        application_student.save()

        with transaction.atomic():            
            OptionAnswer.objects.filter(student_application=application_student).delete()
            
            TextualAnswer.objects.filter(student_application=application_student).delete()
            
            SumAnswer.objects.filter(student_application=application_student).delete()
            
            FileAnswer.objects.filter(student_application=application_student).delete()
            
        return Response("ok")

class StudentViewSet(CamelCaseAPIMixin, viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    permission_classes = (permissions.IsAuthenticated, IsStudentUser, CanAccessApp)
    model = Student
    queryset = Student.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(id=self.request.user.student.id)
        return queryset

    def get_object(self):
        return self.request.user.student
    
    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_object())
        return Response(serializer.data)
    
    @action(detail=False, methods=["GET"])
    def current_school_class(self, request, pk=None):
        user = self.request.user
        student = user.student
        last_school_class = student.classes.filter(
            temporary_class=False,
            is_itinerary=False,
        ).distinct().order_by(
            'school_year', 'name'
        ).last()
                
        return Response(SchoolClassSerializer(instance=last_school_class).data)
    
    @action(detail=False, methods=["GET"])
    def performance_summary(self, request, pk=None):
        user = self.request.user
        type = self.request.GET.get('type', 'all')
        
        summaries = []
        
        questions_count = user.student.get_option_answers_current_year().count()
        currects_count = user.student.get_correct_option_answers().count()
        
        if type in ['question', 'all']:
            summaries.append({
                'type': 'question',
                'total': questions_count,
                'corrects': currects_count,
                'incorrects': questions_count - currects_count,
            })
            
        if type in ['performance', 'all']:
            summaries.append({
                'type': 'performance',
                'performance': (currects_count / questions_count if questions_count else 0) * 100,
                'partial_performance': (currects_count / questions_count if questions_count else 0) * 100,
                'incorrect_performance': ((questions_count - currects_count) / questions_count if questions_count else 0) * 100,
            })
            
        if type in ['grade', 'all']:
            summaries.append({
                'type': 'grade',
                'grade_avg': user.student.applicationstudent_set.get_finished_application_student().get_annotation_count_answers(exclude_annuleds=True, only_total_grade=True).aggregate(grade_avg=Avg('total_grade')).get('grade_avg') or 0,
            })
        
        return Response(summaries[0] if type != 'all' else summaries)
    
    
    @action(detail=False, methods=["GET"])
    def colleagues(self, request, pk=None):
        user = self.request.user
        student = user.student
        last_school_class = student.classes.filter(
            temporary_class=False,
            is_itinerary=False,
        ).distinct().order_by(
            'school_year', 'name'
        ).last()
        students = []
        if last_school_class:
            students = last_school_class.students.exclude(pk=student.pk)
        
        return Response(ColleaguesSerializer(instance=students, many=True).data)

    @action(detail=False, methods=["GET"])
    def materials(self, request, pk=None):
        """
            Trás os materiais de estudo do aluno
        """
        user = self.request.user
        student = user.student
        materials = StudyMaterial.objects.filter(client__in=user.get_clients_cache())
        favorites = FavoriteStudyMaterial.objects.filter(student=student).values_list('study_material', flat=True)

        materials = materials.annotate(
            is_favorite=Case(
                When(id__in=favorites, then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            )
        )

        subjects = []
        for material in materials:
            for subject in material.subjects.all():
                    if subject.id not in [s['id'] for s in subjects]:
                        subjects.append({
                            'id': subject.id,
                            'name': subject.name,
                        })

        stages = []
        for material in materials:
            if material.stage not in stages:
                stages.append(material.stage)

        teachers = []
        for material in materials:
            if not material.send_by:
                continue
            if material.send_by.id not in [t['id'] for t in teachers]:
                teachers.append({
                    'id': material.send_by.id,
                    'name': material.send_by.name,
                })

        if self.request.GET.get('q_stage'):
            materials = materials.filter(
                stage__in=self.request.GET.getlist('q_stage', "")
            )

        if self.request.GET.get('favorites'):
            materials = materials.filter(
                is_favorite=True
            )

        if self.request.GET.get('title'):
            materials = materials.filter(
                title__icontains=self.request.GET.get('title', "")
            )

        if self.request.GET.get('q_subjects'):
            materials = materials.filter(
                subjects__in=self.request.GET.getlist('q_subjects', "")
            )
        
        if self.request.GET.get('q_teacher'):
            teacher_pk = self.request.GET.get('q_teacher', "")
            materials = materials.filter(
                send_by__id=teacher_pk
            )

        paginator = SimpleAPIPagination()
        instances = paginator.paginate_queryset(materials, request)
        
        serialized = StudyMaterialSerializer(instance=instances, many=True).data
        serialized = {
            'items': serialized,
            'subjects': subjects,
            'stages': stages,
            'teachers': teachers
        }
        
        return paginator.get_paginated_response(serialized)

    @action(detail=False, methods=["POST"])
    def favorite_material(self, request, pk=None):
        """
            Favoritar um material de estudo
        """
        user = self.request.user
        student = user.student
        study_material = StudyMaterial.objects.get(pk=request.data.get('material_id'))

        favorite, created = FavoriteStudyMaterial.objects.get_or_create(study_material=study_material, student=student)
        
        if created:
            favorite.save()
            return Response({"id": pk, "status": "success", 'removed': False, "message": "Material favoritado com sucesso!"})
        else:
            favorite.delete()
        return Response({"id": pk, "status": "success", 'removed': True, "message": "Material removido da lista de favoritos!"})
