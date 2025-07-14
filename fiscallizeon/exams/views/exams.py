import uuid, math, itertools, re, copy, logging, sys, os
import pandas as pd
import tempfile
from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication
from fiscallizeon.exams.serializers.exams import CustomPageDuplicateSerializer
import pypandoc 
from io import BytesIO
from sentry_sdk import capture_message
from datetime import datetime
from json.encoder import JSONEncoder
from urllib.parse import urlencode

from django.core.cache import cache
from django.urls import reverse, reverse_lazy
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin  
  
from rest_framework import generics

from django.views import View
from django.views.generic import ListView, TemplateView
from django.views.generic.list import MultipleObjectMixin
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, FormView, UpdateView, DeleteView
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, resolve_url as r
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models.functions import Coalesce, Concat, Length
from django.db import transaction
from django.db.models import Q, Count, F, Case, When, Subquery, OuterRef, CharField, Sum, ExpressionWrapper, fields, Value, Exists, IntegerField, Max, BooleanField
from django.utils.functional import cached_property
from django.utils import translation
from django.utils.translation import gettext as _
from django.template.loader import render_to_string

from fiscallizeon.clients.models import QuestionTag, SchoolCoordination, Unity, ExamPrintConfig, TeachingStage, EducationSystem
from fiscallizeon.bncc.models import Abiliity, Competence
from fiscallizeon.exams.permissions import IsCoordinationExamOwner
from fiscallizeon.subjects.models import Subject, Topic, SubjectRelation
from fiscallizeon.accounts.mixins import LoginOrTokenRequiredMixin
from fiscallizeon.classes.models import SchoolClass, Grade
from fiscallizeon.questions.forms import ImportQuestionsDocxForm
from fiscallizeon.questions.models import Question, QuestionOption
from fiscallizeon.questions.docxutils import get_questions, handle_question
from fiscallizeon.applications.randomization import randomize_exam_json
from fiscallizeon.applications.models import  Application, ApplicationStudent, Annotation, RandomizationVersion, ApplicationRandomizationVersion
from fiscallizeon.answers.models import OptionAnswer, FileAnswer, TextualAnswer, SumAnswerQuestionOption, SumAnswer
from fiscallizeon.exams.models import Exam, ExamOrientation, ExamTeacherSubject, ExamQuestion, QuestionTagStatusQuestion, StatusQuestion, Wrong, ClientCustomPage, ExamHeader, ExamBackgroundImage
from fiscallizeon.exams.forms import ExamForm, ExamOrientationForm, ExamOrientationUpdateForm, ExamTeacherSubjectFormSimple, ExamHeaderUpdateForm, ExamHeaderForm, ClientCustomPageForm, ExamImportForm, ExamBackgroundImageForm
from fiscallizeon.exams.json_utils import get_exam_base_json, convert_json_to_exam_questions_list
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.core.gcp.utils import get_service_account_oauth2_token
from fiscallizeon.core.requests_utils import get_session_retry
from fiscallizeon.notifications.models import Notification
from fiscallizeon.notifications.functions import get_and_create_notifications
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.students.models import Student
from fiscallizeon.core.templatetags.exams_tags import get_correct_option_answer
from fiscallizeon.exams.tasks.copy_exam_with_ia import copy_exam_with_ia
from fiscallizeon.corrections.models import CorrectionDeviation, TextCorrection
from fiscallizeon.corrections.forms import CorrectionDeviationForm
from fiscallizeon.omr.models import  OMRStudents, OMRDiscursiveScan



class ExamListView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, ListView):
    model = Exam
    required_permissions = [settings.COORDINATION, settings.TEACHER,]
    # permission_required = 'exams.view_exam' #comentado pois foi implemetando o check permission abaixo, para verificar se o usuário tem pelo 1 das permissões necessárias para acessar essa página, lógica implementada no CHeckHasPermission
    permission_required_any = ['exams.view_exam', 'exams.export_results_exam']
    paginate_by = 18

    def get_template_names(self):
        if self.request.GET.get('v'):
            return 'dashboard/exams/exam_list.html'
        return 'dashboard/exams/exam_list_new.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_exam_elaboration:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        
        # if hasattr(request.user, 'inspector'):
        #     return redirect(reverse('exams:exam-teacher-subject-list'))
        
        return super(ExamListView, self).dispatch(request, *args, **kwargs)
    
    def get_queryset(self):

        user = self.request.user
        
        client = user.client
        
        subjects = list(user.inspector.subjects.all()) if user.user_type == settings.TEACHER else []
        
        queryset_full = super().get_queryset()
        
        today = timezone.localtime(timezone.now())

        if user.user_type == settings.TEACHER:
            if self.request.GET.get('q_unanswered') and user.inspector.can_correct_questions_other_teachers:
                query = Q(examteachersubject__teacher_subject__subject__in=subjects)
            else:
                query = Q(examteachersubject__teacher_subject__teacher__user=user)

            queryset = queryset_full.filter(
                Q(
                    Q(release_elaboration_teacher__lte=timezone.now()) | Q(release_elaboration_teacher__isnull=True)
                ),
                Q(
                    Q(
                        Q(correction_by_subject=True),
                        Q(coordinations__unity__client=client),
                        Q(examteachersubject__teacher_subject__subject__in=subjects)
                    ) |
                    Q(
                        Q(coordinations__unity__client=client),
                        query
                    ) |
                    Q(created_by=user)
                )
            )
            
            if self.request.GET.get('q_created_by'):
                queryset = queryset.filter(created_by=user)
        else:
            
            # Queryset para coordenadores
            queryset = queryset_full.filter(
                coordinations__in=user.get_coordinations_cache(),
                is_abstract=False,
            ).exclude(
                application__automatic_creation=True,
            ).distinct()

        if self.request.GET.get('q_pk', ''):
            queryset = queryset.filter(pk=self.request.GET.get('q_pk', ''))

        if self.request.GET.get('q_name'):
            
            query_terms = [Q(name__unaccent__icontains=term) for term in self.request.GET.get('q_name').split(' ')]
            query = Q()
            for quey in query_terms:
                query &= quey

            queryset = queryset.filter(
                query
            )
            
        if self.request.GET.getlist('q_status', ""):
            queryset = queryset.filter(
                status__in=self.request.GET.get('q_status', "")
            )

        if self.request.GET.get('q_has_questions', ""):
            queryset = queryset.annotate(
                count_questions=Count('questions')
            ).filter(
                count_questions__gt=0
            )

        if self.request.GET.get('q_is_unprecedented', ""):
            queryset = queryset.filter(
                application__isnull=True
            )

        if self.request.GET.getlist('q_subjects', ""):
            queryset = queryset.filter(
                examteachersubject__teacher_subject__subject__pk__in=self.request.GET.getlist('q_subjects', "")
            )

        if self.request.GET.getlist('q_grades', ""):
            queryset = queryset.filter(
                examteachersubject__grade__pk__in=self.request.GET.getlist('q_grades', "")
            )

        if self.request.GET.getlist('q_segments', ""):
            queryset = queryset.filter(
                examteachersubject__grade__level__in=self.request.GET.getlist('q_segments', "")
            )

        if self.request.GET.getlist('q_units', ""):
            queryset = queryset.filter(
                coordinations__unity__in=self.request.GET.getlist('q_units', "")
            )

        if self.request.GET.getlist('q_teaching_stages', ""):
            queryset = queryset.filter(
                teaching_stage__pk__in=self.request.GET.getlist('q_teaching_stages', "")
            )
            
        if self.request.GET.getlist('q_education_systems', ""):
            queryset = queryset.filter(
                education_system__pk__in=self.request.GET.getlist('q_education_systems', "")
            )

        if self.request.GET.get('year'):
            queryset = queryset.filter(
                created_at__year=self.request.GET.get('year'),
            )
        else:
            queryset = queryset.filter(
                created_at__year=today.year,
            )
            
        if self.request.GET.get('category') == 'homework':
            queryset = queryset.filter(
                category=Exam.HOMEWORK
            )
        
        if self.request.GET.get('category') == 'exam':
            queryset = queryset.filter(
                category=Exam.EXAM
            )
            
        if self.request.GET.get('q_is_printed'):
            queryset = queryset.filter(
                is_printed=True
            )
            
        if self.request.GET.get('q_is_late'):
            queryset = queryset.annotate(
                    count_availables_questions=Count("examquestion", filter=~Q(
                        examquestion__statusquestion__active=True, 
                        examquestion__statusquestion__status=StatusQuestion.REPROVED
                    ), distinct=True),
                    solicitation_quantity=Subquery(
                        Exam.objects.filter(
                            pk=OuterRef('pk')
                        ).annotate(
                            total=Sum('examteachersubject__quantity')
                        ).values_list('total')[:1]
                    )
                ).filter(
                    Q(
                        Q(status__in=[Exam.ELABORATING, Exam.OPENED]),
                        Q(count_availables_questions__lt=F('solicitation_quantity'))
                    ),
                    Q(elaboration_deadline__lt=today)
                ) 
        
        if self.request.GET.get('q_has_wrongs_await'):
            queryset = queryset.filter(examquestion__wrongs__status=Wrong.AWAITING_REVIEW)

        if self.request.GET.get('q_unanswered'):
            if user.user_type == settings.TEACHER:
                queryset = queryset.filter(
                    Q(      
                        Q(examquestion__question__textualanswer__isnull=False),
                        Q(examquestion__question__category=Question.TEXTUAL),
                        Q(examquestion__question__textualanswer__teacher_grade__isnull=True),
                        Q(examquestion__exam_teacher_subject__teacher_subject__subject__in=subjects)
                    ) | Q(
                        Q(examquestion__question__fileanswer__isnull=False),
                        Q(examquestion__question__category=Question.FILE),
                        Q(examquestion__question__fileanswer__teacher_grade__isnull=True),
                        Q(examquestion__exam_teacher_subject__teacher_subject__subject__in=subjects)
                    ) 
                )
            elif user.user_type == settings.COORDINATION:
                queryset = queryset.filter(
                    Q(      
                        Q(examquestion__question__textualanswer__isnull=False),
                        Q(examquestion__question__category=Question.TEXTUAL),
                        Q(examquestion__question__textualanswer__teacher_grade__isnull=True)
                    ) | Q(
                        Q(examquestion__question__fileanswer__isnull=False),
                        Q(examquestion__question__category=Question.FILE),
                        Q(examquestion__question__fileanswer__teacher_grade__isnull=True)
                    ) 
                )
        
        if self.request.GET.get("q_deadline"):
            queryset = queryset.filter(
                elaboration_deadline=self.request.GET.get("q_deadline")
            )

        queryset = queryset.annotate(question_status_with_ai=Case(
            When(Exists(ExamTeacherSubject.objects.filter(
                exam=OuterRef("pk"), 
                question_generation_status_with_ai=ExamTeacherSubject.GENERATING)), 
                then=Value("pendente")),
        
            When(Exists(ExamTeacherSubject.objects.filter(
                Q(question_generation_status_with_ai=ExamTeacherSubject.FINISHED) |
                Q(question_generation_status_with_ai=ExamTeacherSubject.ERROR) ,
                exam=OuterRef("pk")
            )), then=Value("concluido")),
            default=Value("inicial"), 
            output_field=CharField()
        ))

        if not self.request.user.has_perm('exams.can_view_confidential_exam'):
            queryset = queryset.exclude(is_confidential=True, confidential_date__lt=today)
    
        return queryset.distinct().order_by('-created_at')
    
    def get_context_data(self, *args, **kwargs):
        
        today = timezone.localtime(timezone.now())
        context = super(ExamListView, self).get_context_data(**kwargs)
        user = self.request.user
        from fiscallizeon.clients.models import TeachingStage, EducationSystem
        
        context['selected_filter'] = self.request.GET.get('selected_filter', '')
        
        context['q_pk'] = self.request.GET.get('q_pk', '')
        context['q_name'] = self.request.GET.get('q_name', "")
        context['q_status'] = self.request.GET.getlist('q_status', "")
        context['q_subjects'] = self.request.GET.getlist('q_subjects', "")
        context['q_has_questions'] = self.request.GET.get('q_has_questions', "")
        context['q_is_unprecedented'] = self.request.GET.get('q_is_unprecedented', "")
        context['q_grades'] = self.request.GET.getlist('q_grades', "")
        context['q_segments'] = self.request.GET.getlist('q_segments', "")
        context['q_units'] = self.request.GET.getlist('q_units', "")
        context['q_teaching_stages'] = self.request.GET.getlist('q_teaching_stages', "")
        context['q_education_systems'] = self.request.GET.getlist('q_education_systems', "")
        context['q_has_wrongs_await'] = self.request.GET.get('q_has_wrongs_await', "")
        context['q_unanswered'] = self.request.GET.get('q_unanswered', "")
        context['q_created_by'] = self.request.GET.get('q_created_by', "")
        context['q_is_printed'] = self.request.GET.get('q_is_printed', "")
        context['q_is_late'] = self.request.GET.get('q_is_late', "")
        context['q_deadline'] = self.request.GET.get('q_deadline', "")

        context['exam_headers'] = ExamHeader.objects.filter(
            user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache()
        ).distinct().values('pk', 'name')
        
        context['exam_backgrounds'] = ExamBackgroundImage.objects.filter(
            client=self.request.user.client
        ).distinct().values('pk', 'name')
        
        context['category'] = self.request.GET.get('category', '')


        list_filters = [context['q_name'], context['q_status'], context['q_has_questions'], context['q_is_unprecedented'], context['q_subjects'], context["q_teaching_stages"], context["q_education_systems"], context["q_grades"], context['category'], context['q_has_wrongs_await'], context['q_unanswered'], context['q_created_by'], context['q_is_printed'], context['q_deadline']]
        
        context['count_filters'] = len(list_filters) - list_filters.count("")

        filter_condition = Q()
        if user.has_high_school_coordinations:
            filter_condition |= Q(level=Grade.HIGHT_SCHOOL)

        if user.has_elementary_school_only_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL)

        if user.has_elementary_school2_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL_2)

        context["grades"] = Grade.objects.filter(filter_condition)
        context["units"] = Unity.objects.filter(client__in=self.request.user.get_clients())
        context["teaching_stages"] = TeachingStage.objects.filter(client__in=self.request.user.get_clients_cache()).order_by('name')
        context["education_systems"] = EducationSystem.objects.filter(client__in=self.request.user.get_clients_cache()).order_by('name')

        exam_subjects = self.request.user.inspector.subjects.all() if self.request.user.user_type == "teacher" else Subject.objects.filter(
            Q(parent_subject__isnull=True) |
            Q(client__isnull=True) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client__in=self.request.user.get_clients_cache())
            )
        ).order_by('created_at').distinct()

        context['subjects'] = exam_subjects.values('pk', 'name', 'knowledge_area__name')
        
        context['year'] = today.year
        context['today'] = today.date()

        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')

        return context


class ExamListViewV2(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, ListView):
    model = Exam
    required_permissions = [settings.COORDINATION, settings.TEACHER,]
    permission_required = 'exams.view_exam' 
    paginate_by = 18

    def get_template_names(self):
        return 'dashboard/exams/exam_list_new_v2.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_exam_elaboration:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        queryset_full = super().get_queryset()

        today = timezone.localtime(timezone.now())

        queryset = queryset_full.filter(
            coordinations__in=user.get_coordinations_cache(),
            is_abstract=False,
        ).exclude(
            application__automatic_creation=True,
        ).distinct()

        if user.user_type == settings.TEACHER:
            if self.request.GET.get('q_unanswered') and user.inspector.can_correct_questions_other_teachers:
                query = Q(examteachersubject__teacher_subject__subject__in=user.inspector.subjects.all())
            else:
                query = Q(examteachersubject__teacher_subject__teacher__user=user)

            queryset = queryset_full.filter(
                Q(
                    Q(release_elaboration_teacher__lte=timezone.now()) | Q(release_elaboration_teacher__isnull=True)
                ),
                Q(
                    Q(
                        Q(correction_by_subject=True),
                        Q(coordinations__unity__client__in=user.get_clients_cache()),
                        Q(examteachersubject__teacher_subject__subject__in=user.inspector.subjects.all())
                    ) |
                    Q(
                        Q(coordinations__unity__client__in=user.get_clients_cache()),
                        query
                    ) |
                    Q(created_by=user)
                )
            )

            if self.request.GET.get('q_created_by'):
                queryset = queryset.filter(created_by=user)

        if self.request.GET.get('q_pk', ''):
            queryset = queryset.filter(pk=self.request.GET.get('q_pk', ''))

        if self.request.GET.get('q_name', ""):
            queryset = queryset.filter(
                name__unaccent__icontains=self.request.GET.get('q_name', "")
            )

        if self.request.GET.getlist('q_status', ""):
            queryset = queryset.filter(
                status__in=self.request.GET.get('q_status', "")
            )

        if self.request.GET.get('q_has_questions', ""):
            queryset = queryset.annotate(
                count_questions=Count('questions')
            ).filter(
                count_questions__gt=0
            )

        if self.request.GET.get('q_is_unprecedented', ""):
            queryset = queryset.filter(
                application__isnull=True
            )

        if self.request.GET.getlist('q_subjects', ""):
            queryset = queryset.filter(
                examteachersubject__teacher_subject__subject__pk__in=self.request.GET.getlist('q_subjects', "")
            )

        if self.request.GET.getlist('q_grades', ""):
            queryset = queryset.filter(
                examteachersubject__grade__pk__in=self.request.GET.getlist('q_grades', "")
            )

        if self.request.GET.getlist('q_teaching_stages', ""):
            queryset = queryset.filter(
                teaching_stage__pk__in=self.request.GET.getlist('q_teaching_stages', "")
            )

        if self.request.GET.getlist('q_education_systems', ""):
            queryset = queryset.filter(
                education_system__pk__in=self.request.GET.getlist('q_education_systems', "")
            )

        if self.request.GET.get('year'):
            queryset = queryset.filter(
                created_at__year=self.request.GET.get('year'),
            )
        else:
            queryset = queryset.filter(
                created_at__year=today.year,
            )

        if self.request.GET.get('category') == 'homework':
            queryset = queryset.filter(
                category=Exam.HOMEWORK
            )

        if self.request.GET.get('category') == 'exam':
            queryset = queryset.filter(
                category=Exam.EXAM
            )

        if self.request.GET.get('q_is_printed'):
            queryset = queryset.filter(
                is_printed=True
            )

        if self.request.GET.get('q_is_late'):
            queryset = queryset.annotate(
                    count_availables_questions=Count("examquestion", filter=~Q(
                        examquestion__statusquestion__active=True,
                        examquestion__statusquestion__status=StatusQuestion.REPROVED
                    ), distinct=True),
                    solicitation_quantity=Subquery(
                        Exam.objects.filter(
                            pk=OuterRef('pk')
                        ).annotate(
                            total=Sum('examteachersubject__quantity')
                        ).values_list('total')[:1]
                    )
                ).filter(
                    Q(
                        Q(status__in=[Exam.ELABORATING, Exam.OPENED]),
                        Q(count_availables_questions__lt=F('solicitation_quantity'))
                    ),
                    Q(elaboration_deadline__lt=today)
                )

        if self.request.GET.get('q_has_wrongs_await'):
            queryset = queryset.filter(examquestion__wrongs__status=Wrong.AWAITING_REVIEW)

        if self.request.GET.get('q_unanswered'):
            if user.user_type == settings.TEACHER:
                queryset = queryset.filter(
                    Q(
                        Q(examquestion__question__textualanswer__isnull=False),
                        Q(examquestion__question__category=Question.TEXTUAL),
                        Q(examquestion__question__textualanswer__teacher_grade__isnull=True),
                        Q(examquestion__exam_teacher_subject__teacher_subject__subject__in=user.inspector.subjects.all())
                    ) | Q(
                        Q(examquestion__question__fileanswer__isnull=False),
                        Q(examquestion__question__category=Question.FILE),
                        Q(examquestion__question__fileanswer__teacher_grade__isnull=True),
                        Q(examquestion__exam_teacher_subject__teacher_subject__subject__in=user.inspector.subjects.all())
                    )
                )
            elif user.user_type == settings.COORDINATION:
                queryset = queryset.filter(
                    Q(
                        Q(examquestion__question__textualanswer__isnull=False),
                        Q(examquestion__question__category=Question.TEXTUAL),
                        Q(examquestion__question__textualanswer__teacher_grade__isnull=True)
                    ) | Q(
                        Q(examquestion__question__fileanswer__isnull=False),
                        Q(examquestion__question__category=Question.FILE),
                        Q(examquestion__question__fileanswer__teacher_grade__isnull=True)
                    )
                )

        if self.request.GET.get("q_deadline"):
            queryset = queryset.filter(
                elaboration_deadline=self.request.GET.get("q_deadline")
            )

        availables_subquery = ExamQuestion.objects.filter(exam_id=OuterRef('id')).availables()
        availables_with_user_later_subquery = ExamQuestion.objects.filter(exam_id=OuterRef('id')).availables(exclude_use_later=False)

        opened_wrongs_subquery = Wrong.objects.filter(
            exam_question__in=Subquery(availables_subquery.values('id')),
            status=Wrong.AWAITING_REVIEW
        ).distinct().values('id').annotate(
            total_opened_wrongs_count=Count('id')
        ).values('total_opened_wrongs_count')

        applications_subquery = Subquery(Application.objects.filter(exam_id=OuterRef('id')).order_by()
                    .values('exam').annotate(count=Count('pk'))
                    .values('count'), output_field=IntegerField())

        approved_question_count_subquery = Subquery(
            StatusQuestion.objects.filter(
                exam_question__exam_id=OuterRef('id'),
                status=StatusQuestion.APPROVED,
                active=True,
            )
            .order_by()
            .values('exam_question__exam')
            .annotate(count=Count('pk'))
            .values('count'),
            output_field=IntegerField()
        )
        use_later_question_count_subquery = Subquery(
            StatusQuestion.objects.filter(
                exam_question__exam_id=OuterRef('id'),
                status=StatusQuestion.USE_LATER,
                active=True,
            )
            .order_by()
            .values('exam_question__exam')
            .annotate(count=Count('pk'))
            .values('count'),
            output_field=IntegerField()
        )
        reproved_question_count_subquery = Subquery(
            StatusQuestion.objects.filter(
                exam_question__exam_id=OuterRef('id'),
                status=StatusQuestion.REPROVED,
                active=True,
            )
            .order_by()
            .values('exam_question__exam')
            .annotate(count=Count('pk'))
            .values('count'),
            output_field=IntegerField()
        )

        queryset = queryset.select_related('exam_print_config').annotate(
            have_file_answers=Exists(
                FileAnswer.objects.filter(
                    student_application__application__exam=OuterRef('pk'),
                )
            ),
            wrong_count=Coalesce(
                Subquery(
                    opened_wrongs_subquery,
                    output_field=IntegerField(),
                ),
                0,
            ),
            question_count=Coalesce(
                Subquery(
                    availables_subquery
                    .order_by()
                    .values('exam').annotate(count=Count('pk'))
                    .values('count'),

                    output_field=IntegerField(),
                ),
                0,
            ),
            question_with_use_later_count=Coalesce(
                Subquery(
                    availables_with_user_later_subquery
                    .order_by()
                    .values('exam').annotate(count=Count('pk'))
                    .values('count'),

                    output_field=IntegerField(),
                ),
                0,
            ),
            application_count=Coalesce(applications_subquery, 0),
            requested_questions=Coalesce(
                Subquery(
                    ExamTeacherSubject.objects.filter(exam_id=OuterRef('id'))
                    .order_by()
                    .values('exam_id')
                    .annotate(sum=Sum('quantity'))
                    .values('sum'),
                ),
                0,
            ),
            approved_question_count=Coalesce(approved_question_count_subquery, 0),
            use_later_question_count=Coalesce(use_later_question_count_subquery, 0),
            reproved_question_count=Coalesce(reproved_question_count_subquery, 0),
            approved_and_use_later_questions=F('approved_question_count') + F('use_later_question_count'),
            other_questions=F('question_with_use_later_count') - F('approved_question_count') + F('use_later_question_count'),
            total_delivered=F('approved_and_use_later_questions') + F('other_questions'),
        )

        return queryset.distinct().order_by('-created_at')

    def get_context_data(self, **kwargs):
        today = timezone.localtime(timezone.now())
        context = super().get_context_data(**kwargs)
        user = self.request.user

        from fiscallizeon.clients.models import TeachingStage, EducationSystem

        context['selected_filter'] = self.request.GET.get('selected_filter', '')
        context['q_pk'] = self.request.GET.get('q_pk', '')
        context['q_name'] = self.request.GET.get('q_name', "")
        context['q_status'] = self.request.GET.getlist('q_status', "")
        context['q_subjects'] = self.request.GET.getlist('q_subjects', "")
        context['q_has_questions'] = self.request.GET.get('q_has_questions', "")
        context['q_is_unprecedented'] = self.request.GET.get('q_is_unprecedented', "")
        context['q_grades'] = self.request.GET.getlist('q_grades', "")
        context['q_teaching_stages'] = self.request.GET.getlist('q_teaching_stages', "")
        context['q_education_systems'] = self.request.GET.getlist('q_education_systems', "")
        context['q_has_wrongs_await'] = self.request.GET.get('q_has_wrongs_await', "")
        context['q_unanswered'] = self.request.GET.get('q_unanswered', "")
        context['q_created_by'] = self.request.GET.get('q_created_by', "")
        context['q_is_printed'] = self.request.GET.get('q_is_printed', "")
        context['q_is_late'] = self.request.GET.get('q_is_late', "")
        context['q_deadline'] = self.request.GET.get('q_deadline', "")

        context['exam_headers'] = ExamHeader.objects.filter(
            user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache()
        ).distinct().values('pk', 'name')
        # context['exam_headers'] = []

        context['category'] = self.request.GET.get('category', '')


        list_filters = [context['q_name'], context['q_status'], context['q_has_questions'], context['q_is_unprecedented'], context['q_subjects'], context["q_teaching_stages"], context["q_education_systems"], context["q_grades"], context['category'], context['q_has_wrongs_await'], context['q_unanswered'], context['q_created_by'], context['q_is_printed'], context['q_deadline']]

        context['count_filters'] = len(list_filters) - list_filters.count("")

        filter_condition = Q()
        if user.has_high_school_coordinations:
            filter_condition |= Q(level=Grade.HIGHT_SCHOOL)

        if user.has_elementary_school_only_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL)

        if user.has_elementary_school2_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL_2)

        context["grades"] = Grade.objects.filter(filter_condition)
        context["teaching_stages"] = TeachingStage.objects.filter(client__in=self.request.user.get_clients_cache()).order_by('name')
        context["education_systems"] = EducationSystem.objects.filter(client__in=self.request.user.get_clients_cache()).order_by('name')
        # context["grades"] = []
        # context["teaching_stages"] = []
        # context["education_systems"] = []

        exam_subjects = self.request.user.inspector.subjects.all() if self.request.user.user_type == "teacher" else Subject.objects.filter(
            Q(parent_subject__isnull=True) |
            Q(client__isnull=True) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client__in=self.request.user.get_clients_cache())
            )
        ).order_by('created_at').distinct()

        context['subjects'] = exam_subjects.values('pk', 'name', 'knowledge_area__name')
        # context['subjects'] = []

        context['year'] = today.year
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')

        return context


class ExamReviewListView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, ListView):
    template_name = 'dashboard/exams/exam_review_list.html'
    model = Exam
    required_permissions = [settings.TEACHER,]
    paginate_by = 30
    
    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.inspector.is_discipline_coordinator:
            messages.warning(request, 'Você não tem permissão para acessar esta página.')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        return super(ExamReviewListView, self).dispatch(request, *args, **kwargs)
        
    def get_queryset(self):
        user = self.request.user
        queryset_full = super(ExamReviewListView, self).get_queryset()

        today = timezone.localtime(timezone.now())
        
        queryset = queryset_full.filter(
            coordinations__in=user.get_coordinations_cache(),
            status__in=[Exam.ELABORATING, Exam.OPENED],
        ).distinct()
        
        if user.user_type == settings.TEACHER:
            
            if user.inspector.is_discipline_coordinator:
                teacher = user.inspector
                queryset = teacher.get_exams_to_review()
            else:
                queryset = queryset_full.filter(
                    Q(
                        coordinations__in=user.get_coordinations_cache(),
                        examteachersubject__teacher_subject__teacher__user=user,
                        examteachersubject__teacher_subject__active=True,
                    ),
                ).distinct()
        
        if self.request.GET.get('q_name', ""):
            queryset = queryset.filter(
                name__icontains=self.request.GET.get('q_name', "")
            )
            
        if self.request.GET.getlist('q_status', ""):
            queryset = queryset.filter(
                status__in=self.request.GET.get('q_status', "")
            )

        if self.request.GET.get('q_has_questions', ""):
            queryset = queryset.annotate(
                count_questions=Count('questions')
            ).filter(
                count_questions__gt=0
            )

        if self.request.GET.get('q_is_unprecedented', ""):
            queryset = queryset.filter(
                application__isnull=True
            )

        if self.request.GET.getlist('q_subjects', ""):
            queryset = queryset.filter(
                examteachersubject__teacher_subject__subject__pk__in=self.request.GET.getlist('q_subjects', "")
            )

        if self.request.GET.getlist('q_grades', ""):
            queryset = queryset.filter(
                examteachersubject__grade__pk__in=self.request.GET.getlist('q_grades', "")
            )

        if self.request.GET.get('year'):
            queryset = queryset.filter(
                created_at__year=self.request.GET.get('year'),
            )
        else:
            queryset = queryset.filter(
                created_at__year=today.year,
            )

        if self.request.GET.get('category') == 'homework':
            queryset = queryset.filter(
                category=Exam.HOMEWORK
            )
        if self.request.GET.get('category') == 'exam':
            queryset = queryset.filter(
                category=Exam.EXAM
            )
        
        return queryset.order_by('-created_at')
    
    
    def get_context_data(self, **kwargs):
        today = timezone.localtime(timezone.now())
        user = self.request.user
        context = super(ExamReviewListView, self).get_context_data(**kwargs)
        context['q_name'] = self.request.GET.get('q_name', "")
        context['q_status'] = self.request.GET.getlist('q_status', "")
        context['q_subjects'] = self.request.GET.getlist('q_subjects', "")
        context['q_has_questions'] = self.request.GET.get('q_has_questions', "")
        context['q_is_unprecedented'] = self.request.GET.get('q_is_unprecedented', "")
        context['q_grades'] = self.request.GET.getlist('q_grades', "")

        context['exam_headers'] = ExamHeader.objects.filter(user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache()).distinct() 
        
        context['category'] = self.request.GET.get('category', "")

        list_filters = [context['q_name'], context['q_status'], context['q_has_questions'], context['q_is_unprecedented'], context['q_subjects'], context["q_grades"], context['category']]

        context['count_filters'] = len(list_filters) - list_filters.count("")

        context['subjects'] = self.request.user.inspector.subjects.all if self.request.user.user_type == "teacher" else Subject.objects.filter(
            Q(parent_subject__isnull=True) |
            Q(client__isnull=True) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client__in=self.request.user.get_clients_cache())
            )
        ).order_by('created_at').distinct()
        
        filter_condition = Q()
        if user.has_high_school_coordinations:
            filter_condition |= Q(level=Grade.HIGHT_SCHOOL)

        if user.has_elementary_school_only_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL)

        if user.has_elementary_school2_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL_2)

        context["grades"] = Grade.objects.filter(filter_condition)
        
        context['year'] = today.year
        
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')

        return context

class ExamCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = Exam
    required_permissions = [settings.COORDINATION]
    permission_required = 'exams.add_exam'
    form_class = ExamForm
    success_message = 'Prova cadastrada com sucesso'

    def get_template_names(self):
        if self.request.GET.get('v'):
            return 'dashboard/exams/exam_request/exam_request_create_update.html'
        return 'dashboard/exams/exam_request/exam_request_create_update_new.html'

    def get_object(self):
        return Exam.objects.using('default').get(pk=self.kwargs.get('pk'))

    def dispatch(self, request, *args, **kwargs):
        if request.user and request.user.is_authenticated and not request.user.client_has_exam_elaboration:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(ExamCreateView, self).dispatch(request, *args, **kwargs)


    def get_form_kwargs(self):
        kwargs = super(ExamCreateView, self).get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

    def get_success_url(self):
        url = reverse('exams:exams_list')

        if self.object.category == Exam.HOMEWORK:
            url += '?category=homework'

        return url

    def get_context_data(self, **kwargs):
        context = super(ExamCreateView, self).get_context_data(**kwargs)
        user = self.request.user
        context['category'] = self.request.GET.get('category', "")        
        coordinations = user.get_coordinations_cache()
        context['coordinations'] = SchoolCoordination.objects.filter(
            id__in=coordinations
        ).distinct()
        context['unities'] = Unity.objects.filter(
            coordinations__in=coordinations
        ).prefetch_related(
            'coordinations'
        ).distinct()

        filter_condition = Q()
        if user.has_high_school_coordinations:
            filter_condition |= Q(level=Grade.HIGHT_SCHOOL)

        if user.has_elementary_school_only_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL)

        if user.has_elementary_school2_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL_2)

        context['grades'] = Grade.objects.filter(filter_condition)

        context['exam_headers'] = ExamHeader.objects.filter(
            user__coordination_member__coordination__unity__client__in=user.get_clients_cache()
        ).distinct().values('pk', 'name')
        
        return context

class ExamUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = Exam
    form_class = ExamForm
    required_permissions = [settings.COORDINATION,  settings.TEACHER,]
    permission_required = 'exams.change_exam'
    success_message = 'Prova atualizada com sucesso!'

    def get_template_names(self):
        if self.request.GET.get('v'):
            return 'dashboard/exams/exam_request/exam_request_create_update.html'
        return 'dashboard/exams/exam_request/exam_request_create_update_new.html'

    def get_form_kwargs(self):
        kwargs = super(ExamUpdateView, self).get_form_kwargs()
        kwargs.update({
            'user' : self.request.user,
            'is_update': True
        })
        return kwargs
        
    def get_success_url(self):
        return f"{reverse('exams:exams_list')}?{self.request.META['QUERY_STRING']}"

    def get_context_data(self, **kwargs):
        context = super(ExamUpdateView, self).get_context_data(**kwargs)
        exam_pk = self.kwargs.get('pk')

        context = super().get_context_data(**kwargs)
        user = self.request.user
        coordinations = user.get_coordinations_cache()
        user_member = self.object
        context['category'] = self.request.GET.get('category', "")
        context['coordinations'] = SchoolCoordination.objects.filter(
            Q( # Lógica em: https://app.clickup.com/3120759/whiteboards/2z7kq-6333?shape-id=VvV4JUIKtd11FyFCpjK9K
                Q(id__in=user_member.coordinations.all()) |
                Q(id__in=coordinations)
            )
        ).distinct()

        context['unities'] = Unity.objects.filter(
            Q( # Lógica em: https://app.clickup.com/3120759/whiteboards/2z7kq-6333?shape-id=VvV4JUIKtd11FyFCpjK9K
                Q(coordinations__in=user_member.coordinations.all()) |
                Q(coordinations__in=coordinations)
            )
        ).distinct().prefetch_related('coordinations')

        filter_condition = Q()
        if user.has_high_school_coordinations:
            filter_condition |= Q(level=Grade.HIGHT_SCHOOL)

        if user.has_elementary_school_only_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL)

        if user.has_elementary_school2_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL_2)

        context["grades"] = Grade.objects.filter(filter_condition)
        context['client_tags'] = QuestionTag.objects.filter(
            Q(
                Q(type=0),
                Q(
                    Q(client__in=user.get_clients_cache()) | 
                    Q(client=None)
                )
            ),
        )
        context['questions_status_tags'] = QuestionTagStatusQuestion.objects.filter(status__exam_question__exam=exam_pk)
        context['exam_headers'] = ExamHeader.objects.filter(
            user__coordination_member__coordination__unity__client__in=user.get_clients_cache()
        ).distinct().values('pk', 'name')

        if self.request.GET.get('add_materials'):
            context["add_materials"] = True
        
        if self.request.GET.get('is_popup'):
            context['is_popup'] = 1
        
        exam_questions = ExamQuestion.objects.filter(exam=self.object)
        exam_questions_with_answer = [eq for eq in exam_questions if eq.has_answer]

        context['exam_questions_with_answer'] = True if exam_questions_with_answer else False

        context['can_remove_exam_teacher_subjects'] = not Application.objects.filter(
            Q(
                Q(exam=self.get_object()),
                Q(
                    Q(
                        Q(answer_sheet__isnull=False),
                        ~Q(answer_sheet="")
                    ) |
                    Q(
                        Q(room_distribution__exams_bag__isnull=False),
                        ~Q(room_distribution__exams_bag="")
                    )

                )
            )
        ).exists()

        if self.object.pk:  # Se o objeto já existe (no caso de edição)
            context['checkIsBagExist'] = self.object.check_is_bag_exist()
        else:
            context['checkIsBagExist'] = False

        context['today'] = timezone.now().isoformat()

        return context
    
    # def get_context_data(self, **kwargs):
    #     context = super(ExamUpdateView, self).get_context_data(**kwargs)
    #     user = self.request.user
    #     context['category'] = self.request.GET.get('category', "")
    #     context['coordinations'] = SchoolCoordination.objects.filter(
    #         unity__client__in=user.get_clients_cache()
    #     ).distinct()

    def form_valid(self, form):
        from fiscallizeon.exams.models import Exam
        if form.is_valid():
            
            self.object = form.save(commit=False)
            
            if self.request.POST.get("review", None):
                self.object.status = Exam.SEND_REVIEW

            self.object.coordinations.set(form.cleaned_data["coordinations"])
            self.object.save()

            return HttpResponseRedirect(self.get_success_url())
        
class ExamReviewView(ExamUpdateView):
    permission_required = 'exams.can_review_questions_exam'
       
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['only_review'] = True
        
        return context


class ExamDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = Exam
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    success_message = "Prova removida com sucesso!"

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        exam = self.get_object()
        
        if user.is_authenticated and user.user_type == 'teacher' and not exam.created_by == user:
            messages.error(request, 'Você não tem permissão para remover esta prova')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        try:
            self.object.delete()
            get_and_create_notifications(view=self, trigger=Notification.AFTER_DELETE)
            messages.success(self.request, self.success_message)
            
        except ProtectedError:
            messages.error(self.request, "Ocorreu um erro ao remover, a prova já foi aplicada no mínimo uma vez.")
        
        return HttpResponseRedirect(self.get_success_url())  
    
    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', None)
    
class ExamDetailMixin(LoginRequiredMixin, CheckHasPermission, DetailView):
    model = Exam
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    permission_required = 'exams.can_correct_answers_exam'
    aggregation_answers = None
    
    @property
    def exam(self):
        CACHE_KEY = f'EXAM-DETAIL-{self.kwargs["pk"]}'
        if exam_cache := cache.get(CACHE_KEY):
            return exam_cache
        
        exam_cache = cache.set(CACHE_KEY, self.get_object(), 5 * 60)
        
        return cache.get(CACHE_KEY)
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user

        if not user or not user.is_authenticated or user.is_anonymous:
            return redirect("accounts:login")
        
        coordinations = user.get_coordinations_cache()

        self.application_students_exam = self.exam.get_application_students(coordinations=coordinations)
        
        self.applications_year = set(list(self.application_students_exam.values_list("application__date__year", flat=True)))
        
        if self.request.GET.get('year'):
            self.application_students_exam = self.application_students_exam.filter(
                application__date__year=self.request.GET.get('year'),
            )
        else:
            self.application_students_exam = self.application_students_exam.filter(
                application__date__year__in=self.applications_year,
            )
        
        school_class_pk = request.GET.get('turma', '')
        if school_class_pk == 'all':
            self.application_students = self.application_students_exam
        elif school_class_pk == 'alunos-avulsos':
            self.application_students = self.application_students_exam.exclude(student__classes__school_year=self.exam.created_at.year)
        elif school_class_pk:
            self.application_students = self.application_students_exam.filter(
                student__classes=school_class_pk
            )
        else:
            self.application_students = self.application_students_exam.none()

        return super().dispatch(request, *args, **kwargs)

    @cached_property
    def get_application_student_details(self):
        subject_pks = self.request.GET.getlist('disciplinas', [])
        subjects_filter = Subject.objects.filter(pk__in=subject_pks) if subject_pks else []

        user = self.request.user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if self.object.correction_by_subject:  
                subjects = teacher.subjects.all()                
                queryset = self.application_students.get_annotation_count_answers_filter_subjects(subjects=subjects_filter or subjects, exclude_annuleds=True)
            else:          
                queryset = self.application_students.get_annotation_count_answers_filter_teacher(teacher=teacher, subjects=subjects_filter, exclude_annuleds=True)
        else:
            queryset = self.application_students.get_annotation_count_answers(subjects=subjects_filter, exclude_annuleds=True)
        
        queryset = queryset.annotate(
            has_suspicion_advantage=Subquery(
                Annotation.objects.filter(
                    application_student__pk=OuterRef('pk'),
                    suspicion_taking_advantage=True
                ).values('pk')[:1]
            )
        )
        
        return queryset.values(
            'application__pk',
            'student__name', 
            'student__enrollment_number', 
            'pk', 
            'total_answers',
            'is_omr',
            'start_time',
            'total_corrected_answers',
            'total_text_file_answers',
            'total_correct_answers',
            'total_incorrect_answers',
            'total_partial_answers',
            'total_grade',
            'has_suspicion_advantage',
            'missed',
        )

    def get_questions(self):
        questions = self.object.questions

        user = self.request.user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if self.object.correction_by_subject:
                questions = questions.filter(
                    examquestion__exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all()
                ).distinct()
            else:
                if teacher.can_correct_questions_other_teachers:
                    questions = questions.filter(
                        examquestion__exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all()
                    ).distinct()
                else:
                    questions = questions.filter(
                        examquestion__exam_teacher_subject__teacher_subject__teacher=teacher
                    ).distinct()

        return questions.availables(self.exam)
        
    def get_subjects(self):
        
        exam_subjects = self.exam.get_subjects()

        user = self.request.user
        
        if user.user_type == settings.TEACHER:
            return user.inspector.subjects.all().intersection(exam_subjects)

        return exam_subjects

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        questions = self.get_questions()
        application_student_details = self.get_application_student_details
        aggregation_answers = application_student_details.get_aggregation_answers()
        
        application_student_details_list = list(application_student_details)
        
        user = self.request.user
        
        # if user and hasattr(user, 'inspector'):
            
        #     exam = self.get_object()
            
        #     if user.inspector.can_correct_questions_other_teachers:
        #         exam_subjects = exam.get_subjects().filter(
        #             teachersubject__in=user.inspector.teachersubject_set.filter(
        #                 active=True,
        #                 school_year=exam.created_at.year,
        #             ),
        #         )
        #     else:
        #         exam_subjects = exam.get_subjects().filter(
        #             teachersubject__teacher=user.inspector,
        #         )
                
        #     teacher_subjects_classes = exam_subjects.values_list('teachersubject__classes')
            
        #     school_classes = SchoolClass.objects.filter(
        #         pk__in=teacher_subjects_classes,
        #         students__applicationstudent__in=self.application_students_exam,
        #         school_year__in=self.applications_year
        #     ).distinct()
            
        # else:

        # Substitui query por subquery para melhorar o desempenho da buscar pelas turmas
        # Essa demanda foi do dia 12/06/2025 em uma chamada de 
        school_classes = (
            SchoolClass.objects.filter(
                pk__in=self.application_students_exam.values('application__school_classes'),
                coordination__in=user.get_coordinations_cache(),
                school_year__in=self.applications_year,
            )
            .annotate(
                full_name=Concat(
                    F('name'),
                    Value(' - '),
                    F('coordination__unity__name'),
                    Value(' - '),
                    F('school_year'),
                    output_field=CharField()
                )
            )
            .distinct()
            .values('pk', 'full_name')
        )

        if not school_classes:
            school_classes = SchoolClass.objects.filter(
                pk__in=Student.objects.filter(
                    pk__in=self.exam.application_set.all().values('students__pk')
                ).values('classes__pk'),
                school_year=self.exam.created_at.year
            ).annotate(
                full_name=Concat(
                    F('name'),
                    Value(' - '),
                    F('coordination__unity__name'),
                    Value(' - '),
                    F('school_year'),
                    output_field=CharField()
                )
            ).values('pk', 'full_name')

        unities = Unity.objects.filter(
            client=user.client
        )
                
        context['grade_average'] = aggregation_answers.get('grade_average', 0)
        context['duration_average'] = aggregation_answers.get('duration_average', 0)
        context['application_student_details'] = application_student_details
        context['students_online_count'] = len([l for l in application_student_details_list if not l.get('is_omr') and l.get('start_time')])
        context['students_presential_count'] = len([l for l in application_student_details_list if l.get('is_omr')])
        context['total_questions_exam'] = questions.count()
        context['has_applications'] = len(application_student_details_list)
        context['school_classes'] = school_classes
        context['unities'] = unities
        context['exam_subjects'] = self.get_subjects()
        context['subjects_filter'] = self.request.GET.getlist('disciplinas', [])
        return context

class ExamDetailView(ExamDetailMixin):
    template_name = 'dashboard/exams/exam_detail.html'

class ExamDetailV2View(ExamDetailMixin):
    template_name = 'dashboard/exams/exam_detail_v2.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and request.user.client_enabled_new_answer_correction:
            return redirect(r('exams:exams-detail-new', self.kwargs['pk']))

        return super().dispatch(request, *args, **kwargs)

class ExamDetailNewView(ExamDetailMixin):
    template_name = 'dashboard/exams/exam_detail_new.html'

    @cached_property
    def get_application_student_details(self):
        subject_pks = self.request.GET.getlist('disciplinas', [])
        subjects_filter = Subject.objects.filter(pk__in=subject_pks) if subject_pks else []

        user = self.request.user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if self.object.correction_by_subject:
                subjects = teacher.subjects.all()
                queryset = self.application_students.get_annotation_count_answers_filter_subjects(subjects=subjects_filter or subjects, exclude_annuleds=True)
            else:
                queryset = self.application_students.get_annotation_count_answers_filter_teacher(teacher=teacher, subjects=subjects_filter, exclude_annuleds=True)
        else:
            queryset = self.application_students.get_annotation_count_answers(subjects=subjects_filter, exclude_annuleds=True)

        count_questions_choice = self.object.count_choice_and_sum_questions()
        has_questions_choices = bool(count_questions_choice)
        count_questions_discursive = self.object.count_file_and_textual_questions()
        has_questions_discursives = bool(count_questions_discursive)

        sum_answer_counts = SumAnswer.objects.filter(
            student_application=OuterRef('pk'),
        ).values('student_application').annotate(count=Count('id')).values('count')

        option_answer_counts = OptionAnswer.objects.filter(
            student_application=OuterRef('pk'),
            status=OptionAnswer.ACTIVE,
            student_application__empty_questions=False,
        ).values('student_application').annotate(count=Count('id')).values('count')

        count_answer_file = FileAnswer.objects.filter(
            Q(teacher_grade__isnull=False) | Q(empty=True),
            student_application=OuterRef('pk'),
            # student_application__application__exam__total_grade__isnull=False,
        ).values('student_application').annotate(count=Count('id')).values('count')
        count_answer_textual = TextualAnswer.objects.filter(
            Q(teacher_grade__isnull=False) | Q(empty=True),
            student_application=OuterRef('pk'),
            # student_application__application__exam__total_grade__isnull=False,
        ).values('student_application').annotate(count=Count('id')).values('count')

        queryset = queryset.annotate(
            has_suspicion_advantage=Subquery(
                Annotation.objects.filter(
                    application_student=OuterRef('pk'),
                    suspicion_taking_advantage=True
                ).values('pk')[:1]
            ),
            is_checked=Exists(
                OMRStudents.objects.filter(
                    application_student=OuterRef('pk'),
                    checked=True,
                )
            ),
            has_upload_choice=Exists(
                OMRStudents.objects.filter(
                    application_student=OuterRef('pk'),
                )
            ),
            has_upload_discursive=Exists(
                OMRDiscursiveScan.objects.filter(
                    omr_student__application_student_id=OuterRef('pk'),
                )
            ),
            has_questions_choices=Value(has_questions_choices),
            has_questions_discursives=Value(has_questions_discursives),
            count_total_blank=Count('empty_option_questions', distinct=True),
            count_answer_sum=Coalesce(Subquery(sum_answer_counts), Value(0), output_field=IntegerField()),
            count_answer_choice=Coalesce(Subquery(option_answer_counts), Value(0), output_field=IntegerField()),
            count_pendence_choice=ExpressionWrapper(
                Value(count_questions_choice)
                - F('count_total_blank')
                - F('count_answer_choice')
                - F('count_answer_sum'),
                output_field=IntegerField(),
            ),
            count_answer_file=Coalesce(Subquery(count_answer_file), Value(0), output_field=IntegerField()),
            count_answer_textual=Coalesce(Subquery(count_answer_textual), Value(0), output_field=IntegerField()),
            count_pendence_discursive=ExpressionWrapper(
                Value(count_questions_discursive)
                - F('count_answer_file')
                - F('count_answer_textual'),
                output_field=IntegerField(),
            ),
            total_pendence=F('count_pendence_choice') + F('count_pendence_discursive'),
            is_ok=ExpressionWrapper(
                Q(is_checked=True) | (Q(missed=False) & Q(total_pendence__lte=0) & Q(has_upload_choice=True) & Q(has_upload_discursive=True)),
                output_field=BooleanField(),
            ),
        )

        return queryset.values(
            'application__pk',
            'student__name',
            'student__enrollment_number',
            'pk',
            'total_answers',
            'is_omr',
            'start_time',
            'total_corrected_answers',
            'total_text_file_answers',
            'total_correct_answers',
            'total_incorrect_answers',
            'total_partial_answers',
            'total_grade',
            'has_suspicion_advantage',
            'missed',
            'is_checked',
            'is_ok',
            'has_upload_choice',
            'has_upload_discursive',
            'count_pendence_choice',
            'has_questions_discursives',
            'has_questions_choices',
            'count_pendence_discursive',
        )


class DashTeacherExamQuestionsDetailView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/exams/v2/exam_v2_detail_questions.html'
    model = Exam
    permission_required = 'exams.can_view_result_exam'
    required_permissions = [settings.COORDINATION, settings.TEACHER]

    def dispatch(self, request, *args, **kwargs):
        if not self.get_object().application_set.first():
            messages.error(request, "Este caderno não possui resultado, ele ainda não foi aplicado ou não possue respostas.")
            return redirect(self.request.META.get("HTTP_REFERER"))
        return super(DashTeacherExamQuestionsDetailView, self).dispatch(request, *args, **kwargs)
    
    
    def dispatch(self, request, *args, **kwargs):
        if not self.get_object().application_set.first():
            messages.warning(request, "Não é possível ver resultado de cadernos que não foram aplicados.")
            return redirect(request.META.get('HTTP_REFERER'))
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_questions(self):
        user = self.request.user
        coordinations = user.get_coordinations_cache()
        questions = self.get_object().questions.order_by('examquestion__exam_teacher_subject__order', 'examquestion__order').distinct()
        
        if self.request.GET.get('question_category'):
            if int(self.request.GET.get('question_category')) == Question.CHOICE:
                questions = questions.filter(category=Question.CHOICE)
            else:
                questions = questions.exclude(category=Question.CHOICE)

        user = self.request.user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if teacher.can_correct_questions_other_teachers:
                questions = questions.filter(
                    examquestion__exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all()
                ).distinct()
            else:
                questions = questions.filter(
                    examquestion__exam_teacher_subject__teacher_subject__teacher=teacher
                ).distinct()
                
        application = self.object.application_set.first()

        common_filters_options = Q(
            Q(alternatives__optionanswer__status=OptionAnswer.ACTIVE),
            Q(alternatives__optionanswer__student_application__student__classes__school_year=application.date.year if application else timezone.now().year),
            Q(alternatives__optionanswer__student_application__application__in=self.request.GET.getlist('q_applications')) if self.request.GET.get('q_applications') else Q(),
            Q(alternatives__optionanswer__student_application__student__classes__coordination__in=coordinations),
            Q(alternatives__optionanswer__student_application__student__classes__coordination__unity__in=self.request.GET.getlist('q_unities')) if self.request.GET.get('q_unities') and not self.request.GET.get('q_classes') else Q(),
            Q(alternatives__optionanswer__student_application__student__classes__in=self.request.GET.getlist('q_classes')) if self.request.GET.get('q_classes') else Q(),
        )

        common_filters_sum_answer = Q(
            Q(alternatives__sumanswer__student_application__student__classes__school_year=application.date.year if application else timezone.now().year),
            Q(alternatives__sumanswer__student_application__student__classes__coordination__in=coordinations),
            Q(alternatives__sumanswer__student_application__application__in=self.request.GET.getlist('q_applications')) if self.request.GET.get('q_applications') else Q(),
            Q(alternatives__sumanswer__student_application__student__classes__coordination__unity__in=self.request.GET.getlist('q_unities')) if self.request.GET.get('q_unities') and not self.request.GET.get('q_classes') else Q(),
            Q(alternatives__sumanswer__student_application__student__classes__in=self.request.GET.getlist('q_classes')) if self.request.GET.get('q_classes') else Q(),
        )
        
        common_filters_files = Q(
            Q(fileanswer__arquivo__isnull=False),
            Q(fileanswer__student_application__student__classes__school_year=application.date.year if application else timezone.now().year),
            Q(fileanswer__student_application__student__classes__coordination__in=coordinations),
            Q(fileanswer__student_application__application__in=self.request.GET.getlist('q_applications')) if self.request.GET.get('q_applications') else Q(),
            Q(fileanswer__student_application__student__classes__coordination__unity__in=self.request.GET.getlist('q_unities')) if self.request.GET.get('q_unities') and not self.request.GET.get('q_classes') else Q(),
            Q(fileanswer__student_application__student__classes__in=self.request.GET.getlist('q_classes')) if self.request.GET.get('q_classes') else Q(),
        )

        common_filters_textuals = Q(
            Q(textualanswer__content__isnull=False),
            Q(textualanswer__student_application__student__classes__school_year=application.date.year if application else timezone.now().year),
            Q(textualanswer__student_application__student__classes__coordination__in=coordinations),
            Q(textualanswer__student_application__application__in=self.request.GET.getlist('q_applications')) if self.request.GET.get('q_applications') else Q(),
            Q(textualanswer__student_application__student__classes__coordination__unity__in=self.request.GET.getlist('q_unities')) if self.request.GET.get('q_unities') and not self.request.GET.get('q_classes') else Q(),
            Q(textualanswer__student_application__student__classes__in=self.request.GET.getlist('q_classes')) if self.request.GET.get('q_classes') else Q(),
        )
        
        questions = questions.availables(self.get_object(), exclude_annuleds=True).annotate(
            
            objetive_answers=Count('alternatives__optionanswer', filter=Q(
                common_filters_options,
            ), distinct=True),

            sum_answers_count=Coalesce(
                Subquery(
                    SumAnswerQuestionOption.objects.filter(
                        sum_answer__question=OuterRef('pk'),
                        checked=True,
                    ).values('sum_answer__question').annotate(
                        total=Count('pk')
                    ).values('total')[:1],
                ), Value(0)
            ),
            
            correct_objetive_answers=Count('alternatives__optionanswer', filter=Q(
                common_filters_options,
                Q(alternatives__optionanswer__question_option__is_correct=True),
            ), distinct=True),
            
            incorrect_objetive_answers=Count('alternatives__optionanswer', filter=Q(
                common_filters_options,
                Q(alternatives__optionanswer__question_option__is_correct=False)
            ), distinct=True),
            
            file_answers=Count('fileanswer', filter=Q(
                common_filters_files
            ), distinct=True),
            
            textual_answers=Count('textualanswer', filter=Q(
                common_filters_textuals,
            ), distinct=True),
            
            discursive_answers=ExpressionWrapper(F('file_answers') + F('textual_answers'), output_field=fields.IntegerField()),
            
            correct_file_answers=Count('fileanswer', filter=Q(
                common_filters_files,
                fileanswer__teacher_grade=Subquery(
                    ExamQuestion.objects.filter(
                        question__pk=OuterRef('pk'), 
                        exam=self.object
                    ).values('weight')[:1]
                )
            ), distinct=True),
            
            correct_textual_answers=Count('textualanswer', filter=Q(
                common_filters_textuals,
                textualanswer__teacher_grade=Subquery(
                    ExamQuestion.objects.filter(
                        question__pk=OuterRef('pk'), 
                        exam=self.object
                    ).values('weight')[:1]
                )
            ), distinct=True),
            
            partial_hit_file_answers=Count('fileanswer', filter=Q(
                common_filters_files,
                fileanswer__teacher_grade__gt=0, 
                fileanswer__teacher_grade__lt=Subquery(
                    ExamQuestion.objects.filter(
                        question__pk=OuterRef('pk'), 
                        exam=self.object
                    ).values('weight')[:1]
                )
            ), distinct=True),
            
            partial_hit_textual_answers=Count('textualanswer', filter=Q(
                common_filters_textuals,
                textualanswer__teacher_grade__gt=0, 
                textualanswer__teacher_grade__lt=Subquery(
                    ExamQuestion.objects.filter(
                        question__pk=OuterRef('pk'), 
                        exam=self.object
                    ).values('weight')[:1]
                )
            ), distinct=True),
            
            correct_discursive_answers=ExpressionWrapper(
                F('correct_file_answers') + F('correct_textual_answers'), 
                output_field=fields.IntegerField()
            ),
            
            partial_hit_discursive_answers=ExpressionWrapper(
                F('partial_hit_file_answers') + F('partial_hit_textual_answers'), 
                output_field=fields.IntegerField()
            ),
        )

        return questions.values(
            'id',
            'objetive_answers',
            'correct_objetive_answers',
            'incorrect_objetive_answers',
            'discursive_answers',
            'correct_discursive_answers',
            'partial_hit_discursive_answers',
        )
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exam = self.get_object()
        
        questions = self.get_questions()
        questions_availables = exam.questions.availables(exam, exclude_annuleds=True).distinct()
        
        user = self.request.user
        coordinations = user.get_coordinations_cache()

        context['total_questions_exam'] = questions.count()
        context['questions'] = questions
        
        students = exam.get_application_students(coordinations=coordinations).filter(
            Q(application__in=self.request.GET.getlist('q_applications')) if self.request.GET.get('q_applications') else Q(),
            Q(student__classes__coordination__unity__in=self.request.GET.getlist('q_unities')) if self.request.GET.get('q_unities') and not self.request.GET.get('q_classes') else Q(),
            Q(student__classes__in=self.request.GET.getlist('q_classes')) if self.request.GET.get('q_classes') else Q(),
        ).only('pk').distinct()
        
        context['total_students'] = students.count()
        context['total_students_start_application'] = students.filter(Q(
            Q(start_time__isnull=False) |
            Q(is_omr=True)
        )).count()
        
        applications = exam.application_set.all()
        
        context['applications'] = applications
        context['unities'] = Unity.objects.filter(coordinations__in=coordinations)
        context['classes'] = SchoolClass.objects.filter(
            coordination__in=coordinations,
            temporary_class=False,
            school_year=applications.first().date.year if applications.first() else timezone.now().year
        )
        
        context['total_objective_questions'] = questions_availables.filter(category=Question.CHOICE).count()
        context['total_sum_questions'] = questions_availables.filter(category=Question.SUM_QUESTION).count()
        context['total_discursive_questions'] = questions_availables.exclude(category__in=[Question.CHOICE, Question.SUM_QUESTION]).count()
        
        context['total_objective_answers'] = sum([n['objetive_answers'] for n in questions])
        context['total_correct_objective_answers'] = sum([n['correct_objetive_answers'] for n in questions])
        context['total_incorrect_objective_answers'] = sum([n['incorrect_objetive_answers'] for n in questions])
        
        context['total_discursive_answers'] = sum([n['discursive_answers'] for n in questions])
        context['total_correct_discursive_answers'] = sum([n['correct_discursive_answers'] for n in questions])
        context['total_partial_hit_discursive_answers'] = sum([n['partial_hit_discursive_answers'] for n in questions])

        context['q_applications'] = self.request.GET.getlist('q_applications', [])
        context['q_unities'] = self.request.GET.getlist('q_unities', [])
        context['q_classes'] = self.request.GET.getlist('q_classes', [])

        list_filters = [context['q_applications'], context['q_unities'], context['q_classes']]
        context['count_filters'] = len(list_filters) - list_filters.count("")
        
        if self.request.GET.get('question_category'):
            context['question_category'] = self.request.GET.get('question_category')

        context['list_type'] = self.request.GET.get('list_type') or 'grid'
        
        context['coordinations'] = coordinations

        return context
    
class DashTeacherExamQuestionsBNCCDetailView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/exams/v2/exam_v2_detail_bncc.html'
    permission_required = 'exams.can_view_result_exam'
    model = Exam
    required_permissions = [settings.COORDINATION, settings.TEACHER]  
    
    def get_questions(self):
        exam = self.get_object()
        questions = exam.questions.availables(exam=exam, exclude_annuleds=True).order_by('examquestion__exam_teacher_subject__order', 'examquestion__order').distinct()
        if self.request.GET.get('question_category'):
            if int(self.request.GET.get('question_category')) == Question.CHOICE:
                questions = questions.filter(category=Question.CHOICE)
            else:
                questions = questions.exclude(category=Question.CHOICE)

        user = self.request.user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if teacher.can_correct_questions_other_teachers:
                questions = questions.filter(
                    examquestion__exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all()
                ).distinct()
            else:
                questions = questions.filter(
                    examquestion__exam_teacher_subject__teacher_subject__teacher=teacher
                ).distinct()

        questions = questions.availables(exam)
        return questions
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        coordinations = user.get_coordinations_cache()
        questions = self.get_questions()        
        exam = self.get_object()
        
        abilities = Abiliity.objects.filter(question__in=questions).distinct()
        topics = Topic.objects.filter(questions__in=questions).distinct()
        competences = Competence.objects.filter(question__in=questions).distinct()
        
        applications = exam.application_set.all().distinct()
        
        classes = SchoolClass.objects.filter(
            Q(coordination__in=coordinations),
            Q(pk__in=applications.values_list('school_classes', flat=True)),
        )
        
        if hasattr(user, 'inspector'):
            if user.inspector.classes_he_teaches.exists():
                classes = classes.filter(
                    pk__in=user.inspector.classes_he_teaches.values_list('pk', flat=True)
                )
        
        
        bncc = {
            "topics": {
                "list": topics,
            },
            "abilities": {
                "list": abilities,
            },
            "competences": {
                "list": competences,
            },
            
        }
        
        context['bncc'] = bncc
        context['classes'] = classes
        context['unities'] = Unity.objects.filter(coordinations__in=coordinations).distinct()

        context['total_topics'] = bncc['topics']['list'].count()
        context['total_abilities'] = bncc['abilities']['list'].count()
        context['total_competences'] = bncc['competences']['list'].count()
        context['applications'] = applications
        
        context['topic'] = Topic.objects.get(pk=self.request.GET.get('topic')) if self.request.GET.get('topic') else None
        context['ability'] = Abiliity.objects.get(pk=self.request.GET.get('ability')) if self.request.GET.get('ability') else None
        context['competence'] = Competence.objects.get(pk=self.request.GET.get('competence')) if self.request.GET.get('competence') else None
        
        context['q_applications'] = self.request.GET.getlist('q_applications', "")

        list_filters = [context['q_applications']]
        context['count_filters'] = len(list_filters) - list_filters.count("")

        if self.request.GET.get('question_category'):
            context['question_category'] = self.request.GET.get('question_category')

        return context
    
    
class DashTeacherExamStudentsDetailView(LoginRequiredMixin, CheckHasPermission, DetailView, MultipleObjectMixin):
    template_name = 'dashboard/exams/v2/exam_v2_detail_students.html'
    model = Exam
    paginate_by = 20
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    permission_required = 'exams.can_view_result_exam'
    permission_classes = [IsCoordinationExamOwner]
    
    def get_exam_questions(self):
        exam = self.object
        exam_questions = exam.examquestion_set.availables()

        user = self.request.user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if self.object.correction_by_subject:
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all()) |
                    Q(question__subject__in=teacher.subjects.all())
                ).distinct()
            else:
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__teacher=teacher) |
                    Q(question__subject__in=teacher.subjects.all())
                ).distinct()

        return exam_questions.order_by('exam_teacher_subject__order', 'order')
    
    def get_application_student_details(self):
        user = self.request.user
        coordinations = user.get_coordinations_cache()
        applications_student = self.get_object().get_application_students(coordinations=coordinations).filter(
            Q(application__in=self.request.GET.getlist('q_applications')) if self.request.GET.get('q_applications') else Q(),    
            Q(student__name__icontains=self.request.GET.get('q_student_name')) if self.request.GET.get('q_student_name') else Q(),
            Q(student__classes__in=self.request.GET.getlist('q_school_classes')) if self.request.GET.get('q_school_classes') else Q(),
            Q(student__client__unities__in=self.request.GET.getlist('q_unities')) if self.request.GET.get('q_unities') else Q(),
            Q(
                Q(is_omr=True) | Q(start_time__isnull=False)
            ) if not self.request.GET.get('q_all_students') else Q(),
        ).annotate(
            exam_performane=Sum('genericperformances__performance', filter=Q(genericperformances__object_id=F('pk')))
        ).order_by('-exam_performane', 'student__name')
        
        return applications_student
        
    def get_context_data(self, **kwargs):
        exam = self.get_object()
        user = self.request.user
        coordinations = user.get_coordinations_cache()

        applications = exam.application_set.all().order_by('date')
        exam_questions = self.get_exam_questions()
        
        if self.request.GET.getlist('q_subjects'):
            exam_questions = exam_questions.filter(
                Q(question__subject__in=self.request.GET.getlist('q_subjects')) if exam.is_abstract else Q(exam_teacher_subject__teacher_subject__subject__in=self.request.GET.getlist('q_subjects'))
            )
        
        applications_student = self.get_application_student_details()
        context = super().get_context_data(object_list=applications_student)
        classes = SchoolClass.objects.filter(
            Q(coordination__in=coordinations)
        ).annotate(
            students_started_application=Count(
                'students', filter=Q(students__applicationstudent__in=applications.values_list('applicationstudent').distinct())
            )
        ).filter(
            Q(pk__in=applications.values_list('school_classes', flat=True).distinct()),
            Q(students_started_application__gt=0),
        ).distinct()
        
        # if self.request.GET.get('recalculate'):
        #     from fiscallizeon.analytics.models import GenericPerformances
        #     process_time = GenericPerformances.objects.filter(exam=exam, application_student__isnull=False).aggregate(seconds=Sum('process_time'))['seconds'] or None
            
        #     context['recalculate'] = True if self.request.GET.get('recalculate') else False
        #     context['process_time'] = timezone.now() + process_time if process_time else None
            
        #     exam.run_recalculate_task(self.request.GET.get('only_students', None), self.request.GET.get('only_classes', None), self.request.GET.get('only_bnccs', None), self.request.GET.get('only_subjects', None), self.request.GET.get('only_unities', None))
            
        unities = exam.get_unities(coordinations=coordinations)

        subjects = Subject.objects.filter(pk__in=exam_questions.values_list(
            'question__subject' if exam.is_abstract else 'exam_teacher_subject__teacher_subject__subject'
        )
        ).distinct()
        
        topics = Topic.objects.filter(questions__in=exam_questions.values_list('question')).distinct()
        abilities = Abiliity.objects.filter(question__in=exam_questions.values_list('question')).distinct()
        competences = Competence.objects.filter(question__in=exam_questions.values_list('question')).distinct()
        
        context['total_students'] = applications_student.count()
        context['total_students_start_application'] = applications_student.filter(Q(
            Q(start_time__isnull=False) |
            Q(is_omr=True)
        )).count()
        
        context['applications'] = applications
        
        context['abilities'] = abilities
        context['topics'] = topics
        context['competences'] = competences
        
        context['classes'] = classes
        context['unities'] = unities

        context['subjects'] = subjects
        
        context['total_questions_exam'] = exam_questions.count()
        context['total_objective_questions'] = exam_questions.filter(question__category=Question.CHOICE).count()
        context['total_discursive_questions'] = exam_questions.exclude(question__category=Question.CHOICE).count()
        
        # Filters
        context['q_student_name'] = self.request.GET.get('q_student_name', "")
        context['q_applications'] = self.request.GET.getlist('q_applications', "")
        context['q_school_classes'] = self.request.GET.getlist('q_school_classes', "")
        context['q_subjects'] = self.request.GET.getlist('q_subjects', "")
        context['q_all_students'] = self.request.GET.get('q_all_students', "")
        context['q_unities'] = self.request.GET.getlist('q_unities', "")
        
        applied_filters = []
        if context['q_student_name']:
            applied_filters.append(f"Aluno: {context['q_student_name']}")
        if context['q_applications']:
            labels = []
            objects = applications.filter(pk__in=context['q_applications'])
            for object in objects:
                labels.append(f"{object.date.strftime('%d/%m/%Y')} de {object.start.strftime('%H:%m')} até {object.end.strftime('%H:%m')} com {object.students.count()} aluno(s)")
            applied_filters.append(f'Aplicação(ões):  {", ".join(labels)}')
        if context['q_school_classes']:
            labels = []
            objects = classes.filter(pk__in=context['q_school_classes'])
            for object in objects:
                labels.append(f"{object} {object.students.count()} alunos")
            applied_filters.append(f'Turma(s):  {", ".join(labels)}')
        if context['q_subjects']:
            labels = []
            objects = subjects.filter(pk__in=context['q_subjects'])
            for object in objects:
                labels.append(f"{object}")
            applied_filters.append(f'Disciplina(s):  {", ".join(labels)}')
        if context['q_unities']:
            labels = []
            objects = unities.filter(pk__in=context['q_unities'])
            for object in objects:
                labels.append(f"{object.name}")
            applied_filters.append(f'Unidade(s):  {", ".join(labels)}')
        if context['q_all_students']:
            applied_filters.append("Mostrar todos os alunos")
        
        context['applied_filters'] = applied_filters
        
        list_filters = [context['q_applications'], context['q_student_name'], context['q_school_classes'], context['q_all_students'], context['q_unities'], context['q_subjects']]
        
        context['count_filters'] = len(list_filters) - list_filters.count("")

        return context


class DashTeacherExamGeneralDetailView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/exams/v2/exam_v2_detail_general.html'
    model = Exam
    paginate_by = 20
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    permission_required = 'exams.can_view_result_exam'
    permission_classes = [IsCoordinationExamOwner]
    
    def get_exam_questions(self):
        exam = self.get_object()
        exam_questions = exam.examquestion_set.availables()

        user = self.request.user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if self.object.correction_by_subject:
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all()) |
                    Q(question__subject__in=teacher.subjects.all())
                ).distinct()
            else:
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__teacher=teacher) |
                    Q(question__subject__in=teacher.subjects.all())
                ).distinct()

        return exam_questions.order_by('exam_teacher_subject__order', 'order')
    
    def get_application_student_details(self):
        exam = self.get_object()
        user = self.request.user
        coordinations = user.get_coordinations_cache()
        
        applications_student = exam.get_application_students(coordinations=coordinations).filter(
            Q(application__in=self.request.GET.getlist('q_applications')) if self.request.GET.get('q_applications') else Q(),    
            Q(student__classes__in=self.request.GET.getlist('q_school_classes')) if self.request.GET.get('q_school_classes') else Q(),
            Q(student__client__unities__in=self.request.GET.getlist('q_unities')) if self.request.GET.get('q_unities') else Q(),
            Q(
                Q(is_omr=True) | Q(start_time__isnull=False)
            ) if not self.request.GET.get('q_all_students') else Q(),
        ).annotate(
            exam_performane=Sum('genericperformances__performance', filter=Q(genericperformances__object_id=F('pk')))
        ).order_by('-exam_performane', 'student__name')
        
        return applications_student
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        exam = self.get_object()
        user = self.request.user
        coordinations = user.get_coordinations_cache()
        
        applications = exam.application_set.all().order_by('date')
        exam_questions = self.get_exam_questions()
        
        if self.request.GET.getlist('q_subjects'):
            exam_questions = exam_questions.filter(
                Q(question__subject__in=self.request.GET.getlist('q_subjects')) if exam.is_abstract else Q(exam_teacher_subject__teacher_subject__subject__in=self.request.GET.getlist('q_subjects'))
            )
        applications_student = self.get_application_student_details()
        classes = exam.get_classes().filter(
            coordination__in=coordinations,
        ).annotate(
            students_started_application=Count(
                'students', filter=Q(students__applicationstudent__in=applications.values_list('applicationstudent').distinct())
            )
        ).filter(
            Q(students_started_application__gt=0)
        ).distinct()
        
        # if self.request.GET.get('recalculate'):
        #     from fiscallizeon.analytics.models import GenericPerformances
        #     process_time = GenericPerformances.objects.filter(exam=exam, application_student__isnull=False).aggregate(seconds=Sum('process_time'))['seconds'] or None
            
        #     context['recalculate'] = True if self.request.GET.get('recalculate') else False
        #     context['process_time'] = timezone.now() + process_time if process_time else None
            
        #     exam.run_recalculate_task(self.request.GET.get('only_students', None), self.request.GET.get('only_classes', None), self.request.GET.get('only_bnccs', None), self.request.GET.get('only_subjects', None), self.request.GET.get('only_unities', None))
            
        unities = exam.get_unities().filter(coordinations__in=coordinations)
        subjects = Subject.objects.filter(pk__in=self.get_exam_questions().values_list(
                'question__subject' if exam.is_abstract else 'exam_teacher_subject__teacher_subject__subject'
            )
        ).distinct()
        
        topics = Topic.objects.filter(questions__in=exam_questions.values_list('question')).distinct()
        abilities = Abiliity.objects.filter(question__in=exam_questions.values_list('question')).distinct()
        competences = Competence.objects.filter(question__in=exam_questions.values_list('question')).distinct()
        
        context['total_students'] = applications_student.count()
        context['total_students_start_application'] = applications_student.filter(Q(
            Q(start_time__isnull=False) |
            Q(is_omr=True)
        )).count()
        
        context['applications'] = applications
        
        context['abilities'] = abilities
        context['topics'] = topics
        context['competences'] = competences
        
        context['classes'] = classes
        context['unities'] = unities

        context['subjects'] = subjects
        
        context['total_questions_exam'] = exam_questions.count()
        context['total_objective_questions'] = exam_questions.filter(question__category=Question.CHOICE).count()
        context['total_discursive_questions'] = exam_questions.exclude(question__category=Question.CHOICE).count()
                
        # Filters
        context['q_applications'] = self.request.GET.getlist('q_applications', "")
        context['q_school_classes'] = self.request.GET.getlist('q_school_classes', "")
        context['q_subjects'] = self.request.GET.getlist('q_subjects', "")
        context['q_all_students'] = self.request.GET.get('q_all_students', "")
        context['q_unities'] = self.request.GET.getlist('q_unities', "")
        
        applied_filters = []
        if context['q_applications']:
            labels = []
            objects = applications.filter(pk__in=context['q_applications'])
            for object in objects:
                labels.append(f"{object.date.strftime('%d/%m/%Y')} de {object.start.strftime('%H:%m')} até {object.end.strftime('%H:%m')} com {object.students.count()} aluno(s)")
            applied_filters.append(f'Aplicação(ões):  {", ".join(labels)}')
        if context['q_school_classes']:
            labels = []
            objects = classes.filter(pk__in=context['q_school_classes'])
            for object in objects:
                labels.append(f"{object} {object.students.count()} alunos")
            applied_filters.append(f'Turma(s):  {", ".join(labels)}')
        if context['q_subjects']:
            labels = []
            objects = subjects.filter(pk__in=context['q_subjects'])
            for object in objects:
                labels.append(f"{object}")
            applied_filters.append(f'Disciplina(s):  {", ".join(labels)}')
        if context['q_unities']:
            labels = []
            objects = unities.filter(pk__in=context['q_unities'])
            for object in objects:
                labels.append(f"{object.name}")
            applied_filters.append(f'Unidade(s):  {", ".join(labels)}')
        if context['q_all_students']:
            applied_filters.append("Mostrar todos os alunos")
        
        context['applied_filters'] = applied_filters
        
        list_filters = [context['q_applications'], context['q_school_classes'], context['q_all_students'], context['q_unities'], context['q_subjects']]
        
        context['count_filters'] = len(list_filters) - list_filters.count("")

        return context


class ExamDetailEnunciationView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/exams/exam_detail_enunciation.html'
    model = Exam
    required_permissions = ['coordination', 'teacher', ]
    school_class = None
    
    def get_exam_questions(self):
        exam = self.object
        exam_questions = exam.examquestion_set.availables()

        user = self.request.user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if self.object.correction_by_subject:
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all()) |
                    Q(question__subject__in=teacher.subjects.all())
                ).distinct()
            else:
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__teacher=teacher) |
                    Q(question__subject__in=teacher.subjects.all())
                ).distinct()

        return exam_questions.order_by('exam_teacher_subject__order', 'order')

    def dispatch(self, request, *args, **kwargs):
        self.application_students_exam = ApplicationStudent.objects.filter(
            application__exam=self.get_object(),
        )

        today = timezone.localtime(timezone.now())

        if self.request.GET.get('year'):
            self.application_students_exam = self.application_students_exam.filter(
                application__date__year=self.request.GET.get('year'),
            )
        else:
            self.application_students_exam = self.application_students_exam.filter(
                application__date__year=self.get_object().created_at.year,
            )

        school_class_pk = request.GET.get('turma', '')
        if school_class_pk == 'all':
            self.application_students = self.application_students_exam
        elif school_class_pk:
            self.school_class = get_object_or_404(SchoolClass, pk=school_class_pk)
            class_students = self.school_class.students.all()
            self.application_students = self.application_students_exam.filter(
                student__in=class_students
            ).distinct()
        else:
            self.application_students = self.application_students_exam.none()

        return super(ExamDetailEnunciationView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        today = timezone.localtime(timezone.now())

        coordinations = self.request.user.get_coordinations_cache()
        
        school_classes = SchoolClass.objects.filter(
            students__applicationstudent__in=self.application_students_exam,
            school_year=self.get_object().created_at.year,
            coordination__in=coordinations
        ).distinct()

        context = super(ExamDetailEnunciationView, self).get_context_data(**kwargs)
        context['exam_questions'] = self.get_exam_questions()
        context['school_classes'] = school_classes
        context['school_class_pk'] = self.school_class.pk if self.school_class else ''
        context['application_students'] = []
        
        return context

# class ExamTeacherSubjectEditQuestionsView(LoginRequiredMixin, CheckHasPermission, DetailView):
#     template_name = 'dashboard/exams/exam_request/exam_request_teacher_subject_edit.html'
#     model = ExamTeacherSubject
#     required_permissions = [settings.TEACHER, ]

#     def get_context_data(self, **kwargs):
#         context = super(ExamTeacherSubjectEditQuestionsView, self).get_context_data(**kwargs)
        
#         return context

class ExamDetailEnunciationV2View(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/exams/exam_detail_enunciation_v2.html'
    model = Exam
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    school_class = None
    
    def get_exam_questions(self):
        exam = self.get_object()
        exam_questions = exam.examquestion_set.availables()
        application_students = self.application_students
            
        user = self.request.user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if exam.correction_by_subject:
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all()) |
                    Q(question__subject__in=teacher.subjects.all())
                ).distinct()
            else:
                return exam_questions #REMOVER ASAP
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__teacher=teacher)
                    | Q(question__subject__in=teacher.subjects.all())
                ).distinct()

        return exam_questions.get_application_students_report(application_students=application_students).order_by('exam_teacher_subject__order', 'order')

    def dispatch(self, request, *args, **kwargs):
        exam = self.get_object()
        user = self.request.user

        if not user or not user.is_authenticated or user.is_anonymous:
            return redirect("accounts:login")

        if user and not user.is_anonymous and user.client_enabled_new_answer_correction:
            return redirect(r('exams:exams-detail-enunciation-new', self.kwargs['pk']))
        
        coordinations = user.get_coordinations_cache()
        self.application_students_exam = exam.get_application_students(coordinations=coordinations)

        if self.request.GET.get('year'):
            self.application_students_exam = self.application_students_exam.filter(
                application__date__year=self.request.GET.get('year'),
            )
        else:
            self.application_students_exam = self.application_students_exam.filter(
                application__date__year=self.get_object().created_at.year,
            )

        self.school_class_pk = request.GET.get('turma', '')
        if self.school_class_pk == 'all':
            self.application_students = self.application_students_exam
        elif self.school_class_pk:
            self.school_class = get_object_or_404(SchoolClass, pk=self.school_class_pk)
            class_students = self.school_class.students.all()
            self.application_students = self.application_students_exam.filter(
                student__in=class_students
            ).distinct()
        else:
            self.application_students = self.application_students_exam.none()

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localtime(timezone.now())
        user = self.request.user
        
        # if user and hasattr(user, 'inspector'):
            
        #     exam = self.get_object()
            
        #     if user.inspector.can_correct_questions_other_teachers:
        #         exam_subjects = exam.get_subjects().filter(
        #             teachersubject__in=user.inspector.teachersubject_set.filter(
        #                 active=True,
        #                 school_year=exam.created_at.year,
        #             ),
        #         )
        #     else:
        #         exam_subjects = exam.get_subjects().filter(
        #             teachersubject__teacher=user.inspector,
        #         )
                
        #     teacher_subjects_classes = exam_subjects.values_list('teachersubject__classes')
            
        #     school_classes = SchoolClass.objects.filter(
        #         pk__in=teacher_subjects_classes,
        #         students__applicationstudent__in=self.application_students_exam,
        #         school_year__in=self.application_students_exam.values_list("application__date__year", flat=True)
        #     ).distinct()
            
        # else:
        school_classes = SchoolClass.objects.filter(
            students__applicationstudent__in=self.application_students_exam,
            school_year=self.get_object().created_at.year
        ).distinct()
        
        context['application_students'] = []

        if self.school_class_pk:
            context['exam_questions'] = self.get_exam_questions()
            context['application_students'] = self.application_students
        
        context['school_classes'] = school_classes
        context['school_class_pk'] = self.school_class_pk
        
        return context


class ExamDetailEnunciationNewView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/exams/exam_detail_enunciation_new.html'
    model = Exam
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    school_class = None

    def get_exam_questions(self):
        exam = self.get_object()
        exam_questions = exam.examquestion_set.availables()
        application_students = self.application_students

        user = self.request.user
        if user.user_type == settings.TEACHER:
            teacher = user.inspector
            if exam.correction_by_subject:
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__subject__in=teacher.subjects.all()) |
                    Q(question__subject__in=teacher.subjects.all())
                ).distinct()
            else:
                return exam_questions #REMOVER ASAP
                exam_questions = exam_questions.filter(
                    Q(exam_teacher_subject__teacher_subject__teacher=teacher)
                    | Q(question__subject__in=teacher.subjects.all())
                ).distinct()

        return exam_questions.get_application_students_report(application_students=application_students).order_by('exam_teacher_subject__order', 'order')

    def dispatch(self, request, *args, **kwargs):
        exam = self.get_object()
        user = self.request.user

        if not user or not user.is_authenticated or user.is_anonymous:
            return redirect("accounts:login")

        coordinations = user.get_coordinations_cache()
        self.application_students_exam = exam.get_application_students(coordinations=coordinations)

        if self.request.GET.get('year'):
            self.application_students_exam = self.application_students_exam.filter(
                application__date__year=self.request.GET.get('year'),
            )
        else:
            self.application_students_exam = self.application_students_exam.filter(
                application__date__year=self.get_object().created_at.year,
            )

        self.school_class_pk = request.GET.get('turma', '')
        if self.school_class_pk == 'all':
            self.application_students = self.application_students_exam
        elif self.school_class_pk:
            self.school_class = get_object_or_404(SchoolClass, pk=self.school_class_pk)
            class_students = self.school_class.students.all()
            self.application_students = self.application_students_exam.filter(
                student__in=class_students
            ).distinct()
        else:
            self.application_students = self.application_students_exam.none()

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localtime(timezone.now())
        user = self.request.user

        # if user and hasattr(user, 'inspector'):

        #     exam = self.get_object()

        #     if user.inspector.can_correct_questions_other_teachers:
        #         exam_subjects = exam.get_subjects().filter(
        #             teachersubject__in=user.inspector.teachersubject_set.filter(
        #                 active=True,
        #                 school_year=exam.created_at.year,
        #             ),
        #         )
        #     else:
        #         exam_subjects = exam.get_subjects().filter(
        #             teachersubject__teacher=user.inspector,
        #         )

        #     teacher_subjects_classes = exam_subjects.values_list('teachersubject__classes')

        #     school_classes = SchoolClass.objects.filter(
        #         pk__in=teacher_subjects_classes,
        #         students__applicationstudent__in=self.application_students_exam,
        #         school_year__in=self.application_students_exam.values_list("application__date__year", flat=True)
        #     ).distinct()

        # else:
        school_classes = SchoolClass.objects.filter(
            students__applicationstudent__in=self.application_students_exam,
            school_year=self.get_object().created_at.year
        ).distinct()

        context['application_students'] = []

        if self.school_class_pk:
            context['exam_questions'] = self.get_exam_questions()
            context['application_students'] = self.application_students

        context['school_classes'] = school_classes
        context['school_class_pk'] = self.school_class_pk

        return context


class ExamTeacherSubjectBeforeEditQuestionsView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    template_name = 'dashboard/exams/exam_request/before_exam_request_teacher_subject_edit_v2.html'
    model = ExamTeacherSubject
    required_permissions = [settings.TEACHER, settings.COORDINATION]
    form_class = ExamTeacherSubjectFormSimple
    success_message = 'Questões inseridas com sucesso'
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        
        if user.is_authenticated:
            
            exam_teacher_subject = self.get_object()
            
            if user.inspector.has_new_teacher_experience or user.client_has_new_teacher_experience or exam_teacher_subject.exam.created_by == user:
                pass
            else:
                return HttpResponseRedirect(reverse('exams:exam_teacher_subject_edit_questions', kwargs={ "pk": self.get_object().id }))
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_object(self):
        return get_object_or_404(ExamTeacherSubject, pk=self.kwargs.get('pk'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        exam_teacher_subject = self.get_object()
        
        context['elaborated_by_me'] = exam_teacher_subject.exam.created_by == user

        return context
        

class ExamTeacherSubjectEditQuestionsView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    template_name = 'dashboard/exams/exam_request/exam_request_teacher_subject_edit.html'
    model = ExamTeacherSubject
    required_permissions = [settings.TEACHER, settings.COORDINATION]
    form_class = ExamTeacherSubjectFormSimple
    success_message = 'Questões inseridas com sucesso'
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        
        if user.is_authenticated:

            exam_teacher_subject = self.get_object()

            if exam_teacher_subject.exam.check_is_bag_exist() or exam_teacher_subject.exam.check_started_applications_exist():
                messages.warning(request, "Não é possível editar cadernos que tem malote ou aplicação associada.")
                return redirect('core:redirect_dashboard')
            
            if not hasattr(user, 'inspector'):
                messages.error(request, "O usuário que você está autenticado não é do tipo professor, logue com seu usuário de professor e tente novamente!")
                return redirect('core:redirect_dashboard')

            teacher = user.inspector
            if exam_teacher_subject.teacher_subject.teacher != teacher:
                messages.error(request, "Você não tem permissão adicionar questões no caderno de outro professor!")
                return redirect('core:redirect_dashboard')

            today = timezone.localtime().date()
            exam_deadline = exam_teacher_subject.exam.elaboration_deadline
            if exam_deadline and today > exam_deadline and not user.client_has_late_questions:
                messages.error(request, "O período para adicionar questões nesse caderno terminou.")
                return redirect('core:redirect_dashboard')
            

        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self):
        user = self.request.user
        exam_teacher_subject = self.get_object()
        
        if user.is_authenticated and (user.inspector.has_new_teacher_experience or user.client_has_new_teacher_experience or exam_teacher_subject.exam.created_by == user):
            if self.request.GET.get('v'):
                return ["dashboard/exams/exam_request/exam_request_teacher_subject_edit_v2.html"]
            return ['dashboard/exams/exam_request/exam_request_teacher_subject_edit_new.html']
            
        return super().get_template_names()
    

    def get_success_url(self):
        return reverse('core:redirect_dashboard')

    def get_object(self):
        return get_object_or_404(ExamTeacherSubject, pk=self.kwargs.get('pk'))

    def get_parent_subjects(self):
        subject = self.get_object().teacher_subject.subject
        
        parents = []        
        def get_parent(parent):
            if parent and not parent == subject and not str(parent.pk) in parents:
                parents.append(str(parent.pk))
                return get_parent(parent.parent_subject)

            return

        get_parent(subject.parent_subject)
        return parents

    def get_context_data(self, **kwargs):   
        context = super().get_context_data(**kwargs)

        exam_teacher_subject = self.get_object()
        today = timezone.localtime().date()
        user = self.request.user
        exam_deadline = exam_teacher_subject.exam.elaboration_deadline

        if exam_deadline and today > exam_deadline and self.request.user.client_has_late_questions:
            context['late_questions_permit'] = self.request.user.client_has_late_questions
        
        #verificação para caso o usuário seja freemium (não tem cliente)
        if self.request.user.client:
            context['can_not_add_multiple_correct_options'] = self.request.user.client_can_disable_multiple_correct_options and self.request.user.questions_configuration.can_not_add_multiple_correct_options_question 

        context['SUPER_PROFESSOR_URL'] = settings.SUPER_PROFESSOR_URL
        context['SUPER_PROFESSOR_CLIENT_ID'] = settings.SUPER_PROFESSOR_CLIENT_ID
        context['SUPER_PROFESSOR_SECRET'] = settings.SUPER_PROFESSOR_SECRET
        context['SUPER_PROFESSOR_URL_DOCX2HTML_SERVICE'] = settings.SUPER_PROFESSOR_URL_DOCX2HTML_SERVICE
        
        context['TINYMCE_DEFAULTS'] = JSONEncoder().encode(settings.TINYMCE_DEFAULT_CONFIG)
        context['TINYMCE_DEFAULTS_SIMPLE'] = JSONEncoder().encode(settings.TINYMCE_DEFAULT_SIMPLE_CONFIG)
        
        context['creation_type'] = self.request.GET.get('creation_type')

        context['parent_subjects'] = self.get_parent_subjects()
        filter_condition = Q()
        if user.has_high_school_coordinations:
            filter_condition |= Q(level=Grade.HIGHT_SCHOOL)

        if user.has_elementary_school_only_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL)

        if user.has_elementary_school2_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL_2)

        context["grades"] = Grade.objects.filter(filter_condition)
        
        context["text_corrections"] = TextCorrection.objects.filter(Q(client__isnull=True) | Q(client=user.client))
        # context["boards"] = list(
        #     set(list(Question.objects.filter(pk__in=self.request.user.get_questions_database_cache(), board__isnull=False).values_list("board", flat=True)))
        # )
        
        context['elaborated_by_me'] = exam_teacher_subject.exam.created_by == user
        
        return context

class ExamTeacherSubjectQuestionsBankIntroduction(LoginRequiredMixin, CheckHasPermission, DetailView):
    model = ExamTeacherSubject
    required_permissions = [settings.TEACHER]
    template_name = 'exams/examteachersubject_questions_bank_introduction.html'

class ExamTeacherSubjectEditAddQuestionView(
    LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView
):
    model = ExamTeacherSubject
    fields = []
    template_name = 'exams/examteachersubject_update_form.html'
    required_permissions = [settings.TEACHER]
    
    def dispatch(self, request, *args, **kwargs):
        
        user = self.request.user

        if not user or not user.is_authenticated or user.is_anonymous:
            return redirect("accounts:login")
        
        if self.request.GET.get('skip_introduction'):
            user.inspector.skip_introduction_questions_bank = True
            user.inspector.save(skip_hooks=True)
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        filter_condition = Q()
        if user.has_high_school_coordinations:
            filter_condition |= Q(level=Grade.HIGHT_SCHOOL)

        if user.has_elementary_school_only_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL)

        if user.has_elementary_school2_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL_2)

        context["grades"] = Grade.objects.filter(filter_condition)
        context["boards"] = list(
            set(list(Question.objects.filter(pk__in=self.request.user.get_questions_database_cache()).values_list("board", flat=True)))
        )
        
        return context
    

class ExamTeacherSubjectQuestionsSelection(LoginRequiredMixin, CheckHasPermission, UpdateView):
    required_permissions = [settings.TEACHER]
    template_name = 'exams/examteachersubject_questions_selection.html'
    model = ExamTeacherSubject
    fields = []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        return context
    

class ExamTeacherSubjectViewSelectedQuestions(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.TEACHER]
    template_name = 'exams/examteachersubject_view_questions.html'
    model = ExamTeacherSubject
    fields = []

class ExamPreviewView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/exams/exam_preview/exam_preview_new.html'
    model = Exam
    required_permissions = [settings.COORDINATION, settings.TEACHER, ]
    
    @property
    def exam(self):
        return self.object

    def post(self, request, *args, **kwargs):
        
        self.object = self.exam
        self.object.status = Exam.CLOSED
        self.object.save()
        messages.success(request, "Prova revisada e fechada com sucesso!")
        context = self.get_context_data(object=self.object)

        return HttpResponseRedirect(reverse("exams:exams_list"))

    
    def get_context_data(self, **kwargs):
        context = super(ExamPreviewView, self).get_context_data(**kwargs)
        
        exam = self.exam

        # questions = exam.questions.select_related('grade', 'subject', 'subject__knowledge_area').all().order_by('examquestion__exam_teacher_subject__order', 'examquestion__order').distinct()
        user = self.request.user

        examquestions = ExamQuestion.objects.filter(exam=exam).select_related('question').order_by('exam_teacher_subject__order', 'order').availables()

        if user.user_type == settings.TEACHER:

            if user.inspector.is_discipline_coordinator:
                examquestions = examquestions.filter(
                    Q(
                        Q(exam_teacher_subject__teacher_subject__teacher__user=user) |
                        Q(exam_teacher_subject__teacher_subject__subject__in=user.inspector.subjects.all())
                    )
                ).distinct()
            else:
                examquestions = examquestions.filter(
                    Q(
                        Q(exam_teacher_subject__teacher_subject__teacher__user=user) |
                        Q( 
                            Q(exam__correction_by_subject=True) &
                            Q(exam_teacher_subject__teacher_subject__subject__in=user.inspector.subjects.all())
                        )
                    )
                ).distinct()

            examquestions = examquestions.order_by('exam_teacher_subject__order', 'order').distinct()

        for exam_question in examquestions:
            exam_question.has_alternative_duplicate = self.has_alternative_duplicate(exam_question.question)
            exam_question.can_be_updated = exam_question.question.can_be_updated(user=user)

        context['exam_questions'] = examquestions
        context["iterator"] = itertools.count(start=1)
        context["iterator_print"] = itertools.count(start=1)
        context["number_print_iterator"] = itertools.count(start=1)
        context["client_tags"] = QuestionTag.objects.filter(
            Q(
                Q(type=0),
                Q(
                    Q(client__in=user.get_clients_cache()) | 
                    Q(client=None)
                )
            ),
        ).order_by("name")

        exam_questions = ExamQuestion.objects.filter(exam=self.exam)
        exam_questions_with_answer = [eq for eq in exam_questions if eq.has_answer]
        
        context['exists_application']  = Application.objects.filter(exam=self.exam).exists()
        context['exists_bag_generate'] = Application.objects.filter(exam=self.exam).filter(
            Q(
                Q(answer_sheet__isnull=False),
                ~Q(answer_sheet="")
            )
        ).exists()
        context['can_null_questions_answer_sheet'] = Application.objects.filter(exam=self.exam, answer_sheet__isnull=False).exists() or exam_questions_with_answer
        context['application_is_finished'] = self.exam.get_application_is_finished()

        return context
    
    def has_alternative_duplicate(self, question):
        alternative_texts = question.alternatives.values_list('text', flat=True)
        return len(alternative_texts) > len(set(alternative_texts))

class ExamPreviewSimpleView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/exams/exam_preview/exam_preview_simple.html'
    model = Exam
    required_permissions = [settings.COORDINATION, settings.TEACHER, ]
    
    @property
    def exam(self):
        return self.object

    
    def get_context_data(self, **kwargs):
        context = super(ExamPreviewSimpleView, self).get_context_data(**kwargs)
        
        exam = self.exam
        user = self.request.user

        examquestions = ExamQuestion.objects.filter(exam=exam).select_related('question').order_by('exam_teacher_subject__order', 'order').availables()

        examquestions = examquestions.order_by('exam_teacher_subject__order', 'order').distinct()

        context['exam_questions'] = examquestions

        return context


class ExamInspectorPreviewView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/exams/exam_preview/exam_preview.html'
    model = Exam
    required_permissions = [settings.COORDINATION, settings.TEACHER, settings.INSPECTOR, ]


    def get_context_data(self, **kwargs):
        context = super(ExamInspectorPreviewView, self).get_context_data(**kwargs)

        questions = self.object.questions.all().order_by('examquestion__exam_teacher_subject__order', 'examquestion__order').distinct()

        context['questions'] = questions.availables(self.get_object())
        context["iterator"] = itertools.count(start=1)
        context["number_print_iterator"] = itertools.count(start=1)
        context["preview_mode"] = "inspector" 

        return context


class ExamPrintView(LoginOrTokenRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, settings.TEACHER, settings.PARTNER]
    template_name = 'dashboard/exams/exam_print.html'
    model = Exam
    
    def dispatch(self, request, *args, **kwargs):
        
        object = self.get_object()
        pass_check_can_print = self.request.GET.get('pass_check_can_print', False)

        if not pass_check_can_print and not object.can_print:
            messages.error(request, "O caderno não pode ser impresso, por que existe um malote associado, ou o caderno foi marcado como já impresso.")
            return redirect(reverse('core:redirect_dashboard'))
        
        try:
            language = int(request.GET.get('language', ExamPrintConfig.PORTUGUESE))
            if language == ExamPrintConfig.ENGLISH:
                translation.activate('en')
            elif language == ExamPrintConfig.SPANISH:
                translation.activate('es')
            else:
                translation.activate('pt_BR')
        except Exception as e:
            print("Ocorreu um erro ao traduzir a prova: ", e)
            
        response = super().dispatch(request, *args, **kwargs)
        return response

    def get_context_data(self, **kwargs):
        context = super(ExamPrintView, self).get_context_data(**kwargs)
        
        economy_mode = int(self.request.GET.get('economy_mode', 0))
        
        try:
            context['economy_mode'] = economy_mode
            context['two_columns'] = 1 if economy_mode else int(self.request.GET.get('two_columns', 0))
            context['separate_subjects'] = int(self.request.GET.get('separate_subjects', 0))
            context['line_textual'] = int(self.request.GET.get('line_textual', 1))
            context['line_spacing'] = int(self.request.GET.get('line_spacing', 0))
            context['font_family'] = int(self.request.GET.get('font_family', 0))
            context['print_correct_answers'] = int(self.request.GET.get('print_correct_answers', 0))
            context['header_full'] = int(self.request.GET.get('header_full', 0))

            font_size = self.request.GET.get('font_size', 0)
            keys_list_sizes = [item[0] for item in ExamPrintConfig.FONT_SIZES]
            exam_creation_date = self.get_object().created_at.date()
            date_creation_new_font_size_standard = datetime(2024, 7, 7, 7, 0, 0).date()
            
            #adicionado excessão para o decisão, remover após fim de ano letivo 2024
            if str(self.get_object().coordinations.all().first().unity.client.pk) == 'a2b1158b-367a-40a4-8413-9897057c8aa2':
                if not int(font_size) in keys_list_sizes:
                    context['font_size'] = int(font_size)
                elif exam_creation_date > date_creation_new_font_size_standard:
                    context['font_size'] = int(ExamPrintConfig.get_new_default_font_value(int(font_size)))
                else:
                    context['font_size'] = int(ExamPrintConfig.get_font_size(int(font_size)))
            else:
                if not int(font_size) in keys_list_sizes:
                    context['font_size'] = int(font_size)
                else: # exam_creation_date > date_creation_new_font_size_standard:
                    context['font_size'] = int(ExamPrintConfig.get_new_default_font_value(int(font_size)))
                # else:
                #     context['font_size'] = int(ExamPrintConfig.get_font_size(int(font_size)))


            
            context['hide_dialog'] = bool(self.request.GET.get('hide_dialog', False))
            context['hide_discipline_name'] = 0 if int(self.request.GET.get('hide_discipline_name', 0)) else 1
            context['hide_knowledge_area_name'] = int(self.request.GET.get('hide_knowledge_area_name', 0))
            context['hide_questions_referencies'] = int(self.request.GET.get('hide_questions_referencies', 0))
            context['print_images_with_grayscale'] = int(self.request.GET.get('print_images_with_grayscale', 0))
            context['hyphenate_text'] = int(self.request.GET.get('hyphenate_text', 0))
            context['discursive_line_height'] = float(self.request.GET.get('discursive_line_height', 1) if not self.request.GET.get('discursive_line_height') == '' else 1) 
            context["number_print_iterator"] = itertools.count(start=1)
            context['show_question_score'] = int(self.request.GET.get('show_question_score', 0))
            context['uppercase_letters'] = int(self.request.GET.get('uppercase_letters', 0))
            context['text_question_format'] = int(self.request.GET.get('text_question_format', 1))
            context['show_footer'] = int(self.request.GET.get('show_footer', 0))
            context['economy_mode'] = economy_mode
            context['force_choices_with_statement'] = int(self.request.GET.get('force_choices_with_statement', 0))
            context['hide_numbering'] = int(self.request.GET.get('hide_numbering', 0))
            context['break_enunciation'] = 1 if economy_mode else int(self.request.GET.get('break_enunciation', 0))
            context['break_all_questions'] = int(self.request.GET.get('break_all_questions', 0))
            context['discursive_question_space_type'] = int(self.request.GET.get('discursive_question_space_type', 0))
            context['break_alternatives'] = int(self.request.GET.get('break_alternatives', 0))

            margin_top = float(self.request.GET.get('margin_top', 0.6))
            margin_bottom = float(self.request.GET.get('margin_bottom', 0.6))
            margin_right = float(self.request.GET.get('margin_right', 0.0))
            margin_left = float(self.request.GET.get('margin_left', 0.0))  
            context['margin_right'] = self._normalize_margins(margin_right, "right_or_left")
            context['margin_left'] =  self._normalize_margins(margin_left, "right_or_left")
            context['margin_bottom'] = self._normalize_margins(margin_bottom, "bottom_or_top")
            context['margin_top'] =  self._normalize_margins(margin_top,"bottom_or_top" )
    
        except Exception as e:
            context['two_columns'] = 0
            context['separate_subjects'] = 0
            context['line_textual'] = 1
            context['text_question_format'] = 1
            context['show_footer'] = 0
            context['economy_mode'] = 0
            context['force_choices_with_statement'] = 0
            context['hide_numbering'] = 0
            context['break_enunciation'] = 0
            context['break_all_questions'] = 0
            context['discursive_question_space_type'] = 0
            context['line_spacing'] = 0
            context['print_correct_answers'] = int(self.request.GET.get('print_correct_answers', 0))
            context['header_full'] = 0
            context['font_size'] = 12
            context['font_family'] = 0
            context['hide_dialog'] = False
            context['uppercase_letters'] = False
            context['hide_discipline_name'] = 0
            context['hide_knowledge_area_name'] = 0
            context['hide_questions_referencies'] = 0
            context['print_images_with_grayscale'] = 0
            context['hyphenate_text'] = 0
            context['discursive_line_height'] = float(self.request.GET.get('discursive_line_height', 1) if not self.request.GET.get('discursive_line_height') == '' else 1)
            context["number_print_iterator"] = itertools.count(start=1)
            context['show_question_score'] = 0
            context['show_question_board'] = 0
            context['margin_top'] = 0.6
            context['margin_bottom'] = 0.6
            context['margin_right'] = 0.0
            context['margin_left'] = 0.0

        exam_teacher_subjects = []
        application_student = ApplicationStudent.objects.get(pk=self.request.GET.get('application_student')) if self.request.GET.get('application_student') else None 
        randomization = RandomizationVersion.objects.filter(
            application_student=application_student,
            version_number=self.request.GET.get('version_number')
        ).order_by('-created_at')
        
        if randomization:
            question_order = self.object.start_number - 1
            for exam_teacher_subject_json in randomization.last().exam_json['exam_teacher_subjects']:
                    exam_teacher_subject = ExamTeacherSubject.objects.get(pk=exam_teacher_subject_json['pk'])
                    exam_questions = []

                    for exam_question_json in exam_teacher_subject_json['exam_questions']:
                        exam_question = ExamQuestion.objects.get(pk=exam_question_json['pk'])
                        alternatives = QuestionOption.objects.filter(pk__in=exam_question_json['alternatives'])
                        
                        if not exam_question.question.number_is_hidden:
                            question_order += 1

                        _exam_question = {
                            "id": exam_question.pk,
                            "question": exam_question.question,
                            "alternatives": [
                                alternatives.get(pk=json_alternative) for json_alternative in exam_question_json['alternatives']
                            ],
                            "order": self.object.number_print_question(exam_question.question, randomization.last()) if not exam_question.question.number_is_hidden else '',
                        }
                        exam_questions.append(_exam_question)

                    _exam_teacher_subject = {
                        "id": exam_teacher_subject.pk,
                        "grade": {
                            "id": exam_teacher_subject.grade.id if exam_teacher_subject.grade else "",
                            "name": exam_teacher_subject.grade.__str__(),
                        },
                        "subject": {
                            "id": exam_teacher_subject.teacher_subject.subject.id,
                            "name": exam_teacher_subject.teacher_subject.subject.name,
                        },
                        "exam_questions": exam_questions
                    }
                    exam_teacher_subjects.append(_exam_teacher_subject)

            context['randomization'] = randomization.last()
        else:
            questions = self.object.questions.using('default').all().order_by(
                'examquestion__exam_teacher_subject__order', 'examquestion__order'
            ).distinct()

            for question in questions:
                question.in_last_questions = str(question in list(questions)[-4:]).lower()

            context['questions'] = questions.availables(self.get_object())
            context['total_questions'] = questions.count()

        if application_student:
            context['application_student'] = application_student
        
        if self.request.GET.get('header'):
            context["exam_header"] = self.get_object().get_personalized_header(self.request.GET.get('header'))
            
        if background_image_id := self.request.GET.get('background_image'):
            background = ExamBackgroundImage.objects.get(id=background_image_id)
            context["background_image"] = background.image.url 
            
        context["iterator"] = itertools.count()
        context['exam_teacher_subjects'] = exam_teacher_subjects

        return context

    def _normalize_margins(self, margin, margin_type):
        reference_margin = 0.6

        if margin_type == "right_or_left":
            new_margin = margin - reference_margin
        else: 
            new_margin = margin
        return  max(new_margin, 0)


class ExamHomeworkPrintView(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.STUDENT, ]
    template_name = 'dashboard/exams/exam_homework_print.html'
    model = Exam

    def dispatch(self, request, *args, **kwargs):
        application_student = ApplicationStudent.objects.filter(application__exam=self.get_object(), pk=self.kwargs['application_student'])
        today = timezone.now().astimezone()

        if application_student and application_student.first().application.category == Application.HOMEWORK:
            if today < application_student.first().application.date_time_start_tz:
                messages.error(request, "Você não pode imprimir este caderno.")
                return HttpResponseRedirect(reverse('applications:application_student_list'))
        else:
            messages.error(request, "Você não tem permissão para imprimir este caderno.")
            return HttpResponseRedirect(reverse('applications:application_student_list'))

        return super(ExamHomeworkPrintView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ExamHomeworkPrintView, self).get_context_data(**kwargs)

        questions = self.object.questions.all().order_by(
            'examquestion__exam_teacher_subject__order', 'examquestion__order'
        ).distinct()
        
        for question in questions:
            question.in_last_questions = str(question in list(questions)[-4:]).lower()

        context['questions'] = questions.availables(self.get_object())
        context['application_student'] = ApplicationStudent.objects.get(pk=self.kwargs['application_student'])
        context["iterator"] = itertools.count(start=1)
        context["iterator_print"] = itertools.count(start=1)
        context["number_print_iterator"] = itertools.count(start=1)
        

        return context


class ExamTemplateDetailView(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, settings.TEACHER ]
    template_name = 'dashboard/exams/exam_template_print.html'
    permission_required = 'exams.print_template_exam'
    model = Exam

    def get_context_data(self, **kwargs):
        context = super(ExamTemplateDetailView, self).get_context_data(**kwargs)
        separate_subjects = int(self.request.GET.get('separate_subjects', 0))
        subjects_data = []
        
        examquestions = self.object.examquestion_set.annotate(
            has_subject=Case(
                When(
                    Q(
                        Q(exam_teacher_subject__teacher_subject__subject__isnull=False) |
                        Q(question__subject__isnull=False)
                    )
                ), then=Value(True), default=Value(False)
            )
        ).filter(
            question__number_is_hidden=False
        ).order_by(
            'exam_teacher_subject__order', 'order'
        ).availables()
        
        question_withou_subjects = examquestions.filter(has_subject=False)
        
        if self.object.is_abstract:
            
            if separate_subjects:

                subjects = Subject.objects.filter(
                    pk__in=examquestions.values_list('question__subject')
                ).annotate(
                    order=Subquery(
                        examquestions.filter(
                            question__subject=OuterRef('question__subject'),
                        ).order_by('order').values('order')[:1]
                    )
                ).order_by('order').distinct()

            else:

                subjects = Subject.objects.filter(
                    pk__in=examquestions.values_list('question__subject')
                )
            
            for subject in subjects:
                subject_object: dict = {
                    "subject": subject.name,
                    "examquestions": examquestions.filter(
                        question__subject=subject,
                    )
                }
                subjects_data.append(subject_object)
        else:
            exam_teachers_subjects = ExamTeacherSubject.objects.filter(pk__in=examquestions.values_list('exam_teacher_subject')).distinct()       

            for exam_teacher_subject in exam_teachers_subjects:
                subject_object: dict = {
                    "subject": exam_teacher_subject.teacher_subject.subject.name,
                    "examquestions": examquestions.filter(
                        exam_teacher_subject=exam_teacher_subject
                    ).order_by(
                        'exam_teacher_subject__order', 'order'
                    )

                    # examquestions.filter(
                    #     Q(
                    #         Q(exam_teacher_subject__teacher_subject__subject=exam_teacher_subject.teacher_subject.subject) |
                    #         Q(question__subject=exam_teacher_subject.teacher_subject.subject)
                    #     )
                    # ).distinct()
                }
                subjects_data.append(subject_object)
        
        context["subjects"] = subjects_data
        context["examquestions"] = examquestions
        context["question_withou_subjects"] = question_withou_subjects
        context["separate_subjects"] = separate_subjects
        
        #Verifica se o usuário passa um parametro válido para o limite de questões por coluna (Se existe o GET limit, Se é um número e Se o número é maior que 0)
        if self.request.GET.get('limit') and self.request.GET.get('limit').isnumeric() and int(self.request.GET.get('limit')) != 0:
            limit_questions_per_column = int(self.request.GET.get('limit'))
        else: 
            limit_questions_per_column = 20

        # Separa as questões por coluna de tamanho limitado pelo get "limit" ou default de 30
        separated_questions = []
        for i in range(0, int(math.ceil(len(context['examquestions']) / limit_questions_per_column))):
            group_of_questions = context['examquestions'][i * limit_questions_per_column : limit_questions_per_column * (i + 1)]
            separated_questions.append(group_of_questions)
            
        context['separated_questions'] = separated_questions

        return context
    
class ExamRandomizedTemplateDetailView(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, settings.TEACHER ]
    template_name = 'dashboard/exams/exam_randomized_template_print.html'
    permission_required = 'exams.print_template_exam'
    model = Exam

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        current_year = datetime.now().year
        application_versions = ApplicationRandomizationVersion.objects.filter(
            application__exam=self.object,
            application__date__year=current_year,
        ).order_by('sequential', 'created_at')

        versions_ids = list(application_versions.values_list('pk', flat=True))

        application_students = ApplicationStudent.objects.filter(
            application__exam=self.object,
            application__date__year=current_year,
        ).annotate(
            randomization_version_id=Subquery(
                RandomizationVersion.objects.filter(
                    application_student=OuterRef('pk')
                ).order_by(
                    '-version_number'
                ).values(
                    'application_randomization_version_id'
                )[:1]
            )
        ).order_by('student__name')

        total_versions = len(versions_ids)
        has_avulse_students = application_students.filter(randomization_version_id=None).exists()

        for application_student in application_students:
            if not application_student.randomization_version_id:
                application_student.randomization_sequential = total_versions + 1
                continue

            application_student.randomization_sequential = versions_ids.index(application_student.randomization_version_id) + 1
        
        exam_questions_versions = []
        for index, application_version in enumerate(application_versions, 1):
            questions_json = convert_json_to_exam_questions_list(application_version.exam_json)
            questions_pks = [q['pk'] for q in questions_json]
            exam_questions = ExamQuestion.objects.get_ordered_pks(
                pk_ids=questions_pks
            ).availables().select_related(
                'question',
            ).filter(
                question__number_is_hidden=False,
                question__category__in=[Question.CHOICE, Question.SUM_QUESTION],
            )

            for exam_question in exam_questions:
                if exam_question.question.category not in [Question.CHOICE, Question.SUM_QUESTION]:
                    continue

                if exam_question.annuled:
                    exam_question.correct_alternative = '-'
                    continue

                exam_question_json = next((q for q in questions_json if q['pk'] == str(exam_question.pk)), None)

                if exam_question.question.category == Question.CHOICE:
                    correct_alternative = exam_question.question.alternatives.filter(is_correct=True).first()
                    if correct_alternative:
                        correct_index = exam_question_json['alternatives'].index(str(correct_alternative.pk))
                        exam_question.correct_alternative = 'abcdefgh'[correct_index]
                    else:
                        exam_question.correct_alternative = '-'
                    continue
                
                if exam_question.question.category == Question.SUM_QUESTION:
                    exam_question.correct_alternative = get_correct_option_answer(exam_question.question)

            exam_questions_versions.append({
                'application_version': application_version,
                'exam_questions': exam_questions,
                'index': index,
            })

        context['application_students'] = application_students
        context['exam_questions_versions'] = exam_questions_versions
        context['total_application_versions'] = application_versions.count()

        if has_avulse_students:
            context['total_application_versions'] += 1
            context['exam_questions'] = ExamQuestion.objects.filter(
                exam=self.object, 
                question__category__in=[Question.CHOICE, Question.SUM_QUESTION]
            ).availables().order_by(
                'exam_teacher_subject__order', 'order'
            )

        return context

class ExamAnsweredPrintView(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, settings.TEACHER ]
    template_name = 'dashboard/exams/exam_print.html'
    model = Exam

    def get_context_data(self, **kwargs):
        context = super(ExamAnsweredPrintView, self).get_context_data(**kwargs)

        questions = self.object.questions.all().order_by(
            'examquestion__exam_teacher_subject__order', 'examquestion__order'
        ).distinct()

        application_student = ApplicationStudent.objects.get(
            pk=self.kwargs['application_student']
        )

        questions = questions.annotate(
            answer_id=Case(
                When(category=Question.CHOICE, then=Subquery(
                    OptionAnswer.objects.filter(
                        status=OptionAnswer.ACTIVE, 
                        question_option__question__pk=OuterRef('pk'),
                        student_application=application_student
                    ).values('question_option__pk')[:1]
                )),
                When(category=Question.TEXTUAL, then=Subquery(
                    TextualAnswer.objects.filter(
                        question__pk=OuterRef('pk'),
                        student_application=application_student
                    ).values('pk')[:1]
                )),
                When(category=Question.FILE, then=Subquery(
                    FileAnswer.objects.filter(
                        question__pk=OuterRef('pk'),
                        student_application=application_student
                    ).order_by('-created_at').values('pk')[:1]
                )),
                default=None,
                output_field=CharField()
            ),
            answer_content=Case(
                When(category=Question.TEXTUAL, then=Subquery(
                    TextualAnswer.objects.filter(
                        question__pk=OuterRef('pk'),
                        student_application=application_student
                    ).values('content')[:1]
                )),
                When(category=Question.FILE, then=Subquery(
                    FileAnswer.objects.filter(
                        question__pk=OuterRef('pk'),
                        student_application=application_student
                    ).order_by('-created_at').values('arquivo')[:1]
                )),
                default=None,
                output_field=CharField()
            ),
            answer_teacher_feedback=Case(
                When(category=Question.TEXTUAL, then=Subquery(
                    TextualAnswer.objects.filter(
                        question__pk=OuterRef('pk'),
                        student_application=application_student
                    ).values('teacher_feedback')[:1]
                )),
                When(category=Question.FILE, then=Subquery(
                    FileAnswer.objects.filter(
                        question__pk=OuterRef('pk'),
                        student_application=application_student
                    ).order_by('-created_at').values('teacher_feedback')[:1]
                )),
                default=None,
                output_field=CharField()
            ),
        )
        
        context['questions'] = questions.availables(self.get_object())
        context['application_student'] = application_student
        context["iterator"] = itertools.count(start=1)
        context["number_print_iterator"] = itertools.count(start=1)
        context['two_columns'] = 'two_columns' in self.request.GET.keys()
        context['answered'] = True
        return context


class ExamCopyView(LoginRequiredMixin, CheckHasPermission, View):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    permission_required = 'exams.can_duplicate_exam'

    def duplicate_question(self, question_id, include_alternatives=True):
        original_question = Question.objects.get(pk=question_id)
        copy_question = Question.objects.get(pk=question_id)
        copy_question.pk = uuid.uuid4()
        copy_question.source_question = original_question
        copy_question.save()

        if include_alternatives and original_question.category in [Question.CHOICE, Question.SUM_QUESTION]:
            for original_alternative in original_question.alternatives.all():
                copy_alternative = QuestionOption.objects.get(
                    pk=original_alternative.pk
                )
                copy_alternative.pk = uuid.uuid4()
                copy_alternative.question = copy_question
                copy_alternative.index = original_alternative.index
                copy_alternative.save()

        copy_question.coordinations.set(original_question.coordinations.all())
        copy_question.topics.set(original_question.topics.all())
        copy_question.abilities.set(original_question.abilities.all())
        copy_question.competences.set(original_question.competences.all())
        copy_question.base_texts.set(original_question.base_texts.all())

        return copy_question

    def post(self, request, *args, **kwargs):
        full_path = self.request.get_full_path()
        params = full_path.split("?", 1)[1] if "?" in full_path else ""
        if params:
            params = re.sub(r'page=\d+', '', params).replace("?&", "?").replace("&&", "&")
            params = "?" + (params[1:] if params[0] == "&" else params)

        copy_numbers = request.POST.get('copy_numbers')
        duplicate_option = request.POST.get('duplicate_option')

        copy_questions = duplicate_option == 'copy-questions'
        no_copy_questions = duplicate_option == 'no-copy-questions'
        ia_copy_questions = duplicate_option == 'ia-copy-questions'

        reduced_enunciation = bool(request.POST.get('reduced_enunciation', False))
        reduced_quantity_alternatives = bool(request.POST.get('reduced_quantity_alternatives', False))
        reduced_text_alternatives = bool(request.POST.get('reduced_text_alternatives', False))
        randomize_questions = bool(request.POST.get('randomize_questions', False))
        randomize_alternatives = bool(request.POST.get('randomize_alternatives', False))
        group_questions = bool(request.POST.get('group_questions', False))
        randomize_subjects = bool(request.POST.get('randomize_subjects', False))
        keep_questions = bool(request.POST.get('keep_questions', False))

        try:
            with transaction.atomic():
                for i in range(0, int(copy_numbers)):
                    original_exam = Exam.objects.get(pk=self.kwargs['pk'])
                    copy_exam = Exam.objects.get(pk=self.kwargs['pk'])
                    if original_exam.exam_print_config:
                        copy_exam_print_config = ExamPrintConfig.objects.get(
                            pk=original_exam.exam_print_config.pk
                        )
                        copy_exam_print_config.pk = None
                        copy_exam_print_config.name = f'Configuração {copy_exam.name}'
                        copy_exam_print_config.save()
                        copy_exam.exam_print_config = copy_exam_print_config

                    copy_exam.pk = None
                    copy_exam.source_exam = original_exam
                    copy_exam.id_erp = None
                    copy_exam.last_erp_sync = None
                    
                    copy_exam.name = f'CÓPIA {i + 1} - {original_exam.name}'
                    if randomize_questions or randomize_alternatives or randomize_subjects:
                        copy_exam.name = f'CÓPIA RANDOMIZADA {i + 1} - {original_exam.name}'

                    copy_exam.save()

                    copy_exam.coordinations.set(original_exam.coordinations.all())

                    if original_exam.external_code and self.request.user.client_has_offset_answer_sheet:
                        Exam.objects.generate_external_code(
                            copy_exam, 
                            self.request.user.get_clients().first()
                        )

                    if copy_questions :
                        exam_json = get_exam_base_json(original_exam)
                        exam_json_copy = copy.deepcopy(exam_json)

                        randomize_exam_json(
                            exam_json=exam_json_copy,
                            random_questions=randomize_questions,
                            random_alternatives=randomize_alternatives,
                            random_subjects=randomize_subjects,
                            group_categories=group_questions
                        )

                        for index, exam_teacher_subject_json in enumerate(exam_json_copy['exam_teacher_subjects']):
                            exam_teacher_subject = ExamTeacherSubject.objects.get(
                                pk=exam_teacher_subject_json['pk'],
                            )

                            exam_teacher_subject.pk = None
                            exam_teacher_subject.exam = copy_exam
                            exam_teacher_subject.order = index
                            exam_teacher_subject.id_erp = None
                            exam_teacher_subject.save(skip_hooks=True)
                            

                            for exam_question_index, exam_question_json in enumerate(exam_teacher_subject_json['exam_questions']):
                                exam_question = ExamQuestion.objects.get(
                                    pk=exam_question_json['pk']
                                )

                                exam_question.pk = None
                                exam_question.exam = copy_exam
                                exam_question.order = exam_question_index
                                exam_question.exam_teacher_subject = exam_teacher_subject
                                exam_question.id_erp = None

                                if randomize_alternatives and exam_question_json['category'] in [1, 3]:
                                    copy_question = self.duplicate_question(exam_question.question.pk, include_alternatives=False)
                                    exam_question.question = copy_question

                                    for alternative_index, alternative_pk in enumerate(exam_question_json['alternatives'], 1):
                                        QuestionOption.objects.get(
                                            pk=alternative_pk
                                        )
                                        copy_alternative = QuestionOption.objects.get(
                                            pk=alternative_pk
                                        )
                                        copy_alternative.pk = uuid.uuid4()
                                        copy_alternative.question = copy_question
                                        copy_alternative.index = alternative_index
                                        copy_alternative.save()
                                elif not keep_questions:
                                    copy_question = self.duplicate_question(exam_question.question.pk)
                                    exam_question.question = copy_question

                                exam_question.save()

                    elif ia_copy_questions:
                        copy_exam.name = f'CÓPIA FEITA POR IA {i + 1} - {original_exam.name}'
                        exam_json = get_exam_base_json(original_exam)
                        exam_json_copy = copy.deepcopy(exam_json)
                        copy_exam.exam_used_for_copying = str(original_exam.pk)
                        
                        copy_exam_with_ia.apply_async(
                            args=[self.request.user.pk, copy_exam.pk, original_exam.pk, exam_json_copy, 
                                reduced_text_alternatives, reduced_enunciation, reduced_quantity_alternatives],
                            task_id=f'AI_QUESTION_COPY_{original_exam.pk}_{original_exam.copy_exam_with_ia_count}'
                        )

                        copy_exam.save()

                    elif not copy_questions and not ia_copy_questions:
                        for subject in original_exam.examteachersubject_set.all():
                            # new_exam_teacher_subject = ExamTeacherSubject(
                            #         teacher_subject=subject.teacher_subject,
                            #         exam=copy_exam,
                            #         grade=subject.grade,
                            #         quantity=subject.quantity,
                            #         note=subject.note,
                            #         order=subject.order,
                            #         teacher_note=subject.teacher_note,
                            # )
                            
                            # new_exam_teacher_subject.save(skip_hooks=True)

                            new_exam_teacher_subject = ExamTeacherSubject.objects.get(
                                pk=subject.pk,
                            )

                            new_exam_teacher_subject.pk = None
                            new_exam_teacher_subject.exam = copy_exam
                            new_exam_teacher_subject.id_erp = None
                            new_exam_teacher_subject.save(skip_hooks=True)

                            if not no_copy_questions:
                                for question in subject.examquestion_set.all():
                                    original_question = question.question
                                    copy_question = self.duplicate_question(question.question.pk)

                                    if original_question.category in [Question.CHOICE, Question.SUM_QUESTION]:
                                        for index, alternative in enumerate(original_question.alternatives.all().order_by('created_at'), 1):
                                            QuestionOption.objects.create(
                                                question=copy_question,
                                                text=alternative.text,
                                                is_correct=alternative.is_correct,
                                                index=index,
                                            )

                                    ExamQuestion.objects.create(
                                        question=copy_question,
                                        exam=copy_exam,
                                        exam_teacher_subject=new_exam_teacher_subject,
                                        order=question.order,
                                        weight=question.weight
                                    )
            

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno, e)
            capture_message(str(e))
            messages.error(self.request, "Houve algum erro na duplicação da prova, tente novamente!")

            return HttpResponseRedirect(reverse('exams:exams_list') + params)
        if not ia_copy_questions:
            messages.success(self.request, 'Caderno de provas duplicado com sucesso.')
        else:
            messages.success(self.request, 'A cópia do caderno de provas esta sendo processada, logo mais poderá visualizá-la.')


        return HttpResponseRedirect(reverse('exams:exams_list') + params)


class ImportExamQuestionsView(SuccessMessageMixin, LoginRequiredMixin, CheckHasPermission, FormView):
    template_name = 'dashboard/exams/exam_request/exam_request_teacher_subject_edit.html'
    required_permissions = [settings.TEACHER,  ]
    form_class = ImportQuestionsDocxForm
    success_message = 'Questões importadas com sucesso'

    def get_success_url(self):
        return reverse(
            'exams:exam_teacher_subject_edit_questions', 
            kwargs={'pk': self.kwargs.get('pk')}
        )

    def create_question(self, question_data):
        levels = {
            'f': Question.EASY,
            'm': Question.MEDIUM,
            'd': Question.HARD,
        } 
        categories = {
            'o': Question.CHOICE,
            'd': Question.TEXTUAL,
            'a': Question.FILE,
        } 

        level = levels.get(
            question_data['level'][0] if question_data['level'] else None, Question.UNDEFINED
        )
        category = categories.get(
            question_data['category'][0] if question_data['category'] else None, Question.CHOICE
        )

        question = Question.objects.create(
            subject=self.object.teacher_subject.subject,            
            level=level,
            category=category,
            grade=self.object.grade,
            enunciation=question_data['enunciation'],
            commented_awnser=question_data['commented_answer'],
            feedback=question_data['teacher_feedback'],
            created_by=self.request.user,
        )

        abilities = []
        for ability_code in question_data.get('abilities', []):
            if ability := Abiliity.objects.filter(code=ability_code.strip()).first():
                abilities.append(ability)

        question.abilities.set(abilities)

        if question.category == Question.CHOICE:
            for index, alternative in enumerate(question_data.get('alternatives', []), 1):
                alternative['question'] = question
                question_option = QuestionOption.objects.create(**alternative)
                question_option.index = index
                question_option.save(skip_hooks=True)

        question.coordinations.set(self.object.exam.coordinations.all())
        return question

    def form_valid(self, form):
        self.object = get_object_or_404(ExamTeacherSubject, pk=self.kwargs.get('pk'))
        raw_questions = get_questions(form.cleaned_data['questions_doc'])

        for index, raw_question in enumerate(raw_questions):
            question_data = handle_question(raw_question)
            question = self.create_question(question_data)
            ExamQuestion.objects.create(
                question=question,
                exam=self.object.exam,
                exam_teacher_subject=self.object,
                order=question_data.get('order', index)
            )

        return super(ImportExamQuestionsView, self).form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request, 
            'Ocorreu um erro no envio do documento, verifique a \
            extensão do arquivo e tente novamente'
        )
        return redirect(self.get_success_url())

# Exam Header Start
class ExamHeaderCreate(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    template_name = 'dashboard/exams/exam_header_create_update.html'
    model = ExamHeader
    required_permissions = ['coordination', ]
    permission_required = 'exams.add_examheader'
    form_class = ExamHeaderForm
    success_message = 'Cabeçalho adicionado com sucesso'

    def get_success_url(self):
        return reverse('exams:exam_header_list')

class ExamHeaderUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    template_name = 'dashboard/exams/exam_header_create_update.html'
    model = ExamHeader
    required_permissions = ['coordination', ]
    permission_required = 'exams.change_examheader'
    form_class = ExamHeaderUpdateForm
    success_message = 'Cabeçalho atualizado com sucesso'

    def get_success_url(self):
        return reverse('exams:exam_header_list')
    
class ExamHeaderListView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, ListView):
    template_name = 'dashboard/exams/exam_header_list.html'
    model = ExamHeader
    required_permissions = [settings.COORDINATION,]
    permission_required = 'exams.view_examheader'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_exam_elaboration:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(ExamHeaderListView, self).dispatch(request, *args, **kwargs)

    
    def get_queryset(self):
        queryset = super(ExamHeaderListView, self).get_queryset()
        queryset = queryset.filter(user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache()).distinct()

        return queryset

    def get_context_data(self, **kwargs):
        context = super(ExamHeaderListView, self).get_context_data(**kwargs)

        return context
class ExamHeaderDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = ExamHeader
    required_permissions = ['coordination', ]
    permission_required = 'exams.delete_examheader'
    success_message = "Cabeçalho removido com sucesso!"

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', None)
# Exam Header End
    
# Exam Orientations Start
class ExamOrientationsCreate(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    template_name = 'dashboard/exams/exam_orientations_create_update.html'
    model = ExamOrientation
    permission_required = 'exams.add_examorientation'
    form_class = ExamOrientationForm
    success_message = 'Orientação adicionada com sucesso'

    def get_success_url(self):
        return reverse('exams:exam_orientations_list')
    
class ExamOrientationsUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    template_name = 'dashboard/exams/exam_orientations_create_update.html'
    model = ExamOrientation
    permission_required = 'exams.change_examorientation'
    form_class = ExamOrientationUpdateForm
    success_message = 'Orientação atualizada com sucesso'

    def get_success_url(self):
        return reverse('exams:exam_orientations_list')

class ExamOrientationListView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, ListView):
    template_name = 'dashboard/exams/exam_orientations_list.html'
    model = ExamOrientation
    permission_required = 'exams.view_examorientation'
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_exam_elaboration:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(ExamOrientationListView, self).dispatch(request, *args, **kwargs)

    
    def get_queryset(self):
        queryset = super(ExamOrientationListView, self).get_queryset()
        queryset = queryset.filter(user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache()).distinct()

        return queryset

class ExamOrientationDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = ExamOrientation
    permission_required = 'exams.delete_examorientation'
    success_message = "Orientação removida com sucesso!"

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', None)
# Exam Orientations End


class ExamTeacherCreateUpdateTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'dashboard/exams/exam_create/exam_teacher_create_update.html'
    required_permissions = [settings.TEACHER]
    permission_required = 'inspectors.can_add_exercice_list'
    object = None

    def get_template_names(self):
        if version := self.request.GET.get('v'):
            return f'dashboard/exams/exam_create/exam_teacher_create_update_v{version}.html'
        return super().get_template_names()

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if kwargs.get('pk'):
            try:
                self.object = Exam.objects.using('default').get(pk=kwargs.get('pk'))
                if not user.is_authenticated or not self.object.category == Exam.HOMEWORK or not self.object.created_by or not self.object.created_by == user or not user.client_teachers_can_elaborate_exam:
                    messages.error(request, 'Você não tem permissão para acessar esta página')
                    return redirect(reverse('core:redirect_dashboard'))
            except Exam.DoesNotExist:
                messages.error(request, 'Caderno não encontrado')
                return redirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ExamTeacherCreateUpdateTemplateView, self).get_context_data(**kwargs)

        context['object'] = self.object
        
        inspetor_grades = Grade.objects.filter(
            knowledgearea__subject__in=self.request.user.inspector.subjects.all()
        ).distinct().order_by('order', 'name')

        grades = []
        
        for grade in inspetor_grades:
            grades.append({
                'id': grade.id,
                'name': grade.name_grade,
                'subjects': Subject.objects.filter(
                    knowledge_area__grades=grade, pk__in=self.request.user.inspector.subjects.all()
                ).distinct()
            })
        
        context['grades'] = grades

        context['SUPER_PROFESSOR_URL'] = settings.SUPER_PROFESSOR_URL
        context['SUPER_PROFESSOR_CLIENT_ID'] = settings.SUPER_PROFESSOR_CLIENT_ID
        context['SUPER_PROFESSOR_SECRET'] = settings.SUPER_PROFESSOR_SECRET
        context['SUPER_PROFESSOR_URL_DOCX2HTML_SERVICE'] = settings.SUPER_PROFESSOR_URL_DOCX2HTML_SERVICE
        
        if self.object:
            exam_teacher_subject = self.object.examteachersubject_set.all().first()
            exam_questions = exam_teacher_subject.examquestion_set.all()
            context['exam_teacher_subject'] = exam_teacher_subject
            context['exam_questions_count'] = exam_questions.count()
            context['objectives_quantity'] = exam_questions.filter(question__category__in=[Question.CHOICE, Question.SUM_QUESTION]).count()
            context['discursives_quantity'] = exam_questions.filter(question__category__in=[Question.TEXTUAL, Question.FILE]).count()            
        
        return context

class ExamPrintV2View(LoginOrTokenRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, settings.TEACHER ]
    permission_required = 'exams.can_diagram_exam'
    template_name = 'dashboard/exams/v2/exam_print.html'
    model = Exam

    def dispatch(self, request, *args, **kwargs):

        if self.get_object().is_printed:
            messages.error(request, f'{Exam._meta.verbose_name_plural} marcados como "já impresso" não podem ser diagramados.')
            return redirect(reverse('core:redirect_dashboard'))
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ExamPrintV2View, self).get_context_data(**kwargs)

        exam = self.get_object()

        if not exam.exam_print_config:
            config = self.request.user.client.get_exam_print_config()
            config.pk = None
            config.name = f'Configuração {exam.name}'
            config.is_default = False
            config.save()
            exam.exam_print_config = config
            exam.save(skip_hooks=True)

        questions = (
            self.object.questions.all()
            .order_by(
                'examquestion__exam_teacher_subject__order',
                'examquestion__order',
            )
            .distinct()
        )

        user = self.request.user

        if user.user_type == settings.TEACHER:
            questions = questions.filter(Q(examquestion__exam=self.object))

            if user.inspector.is_discipline_coordinator:
                questions = questions.filter(
                    Q(examquestion__exam=self.get_object()),
                    Q(
                        Q(
                            examquestion__exam_teacher_subject__teacher_subject__teacher__user=user
                        )
                        | Q(
                            examquestion__exam__examteachersubject__teacher_subject__subject__in=user.inspector.subjects.all()
                        )
                    ),
                ).distinct()
            else:
                questions = questions.filter(
                    Q(
                        Q(examquestion__exam=self.get_object()),
                        Q(
                            examquestion__exam_teacher_subject__teacher_subject__teacher__user=user
                        )
                        | Q(
                            Q(examquestion__exam__correction_by_subject=True)
                            & Q(
                                examquestion__exam__examteachersubject__teacher_subject__subject__in=user.inspector.subjects.all()
                            )
                        ),
                    )
                ).distinct()

            questions = questions.order_by(
                'examquestion__exam_teacher_subject__order',
                'examquestion__order',
            ).distinct()
            
        context['questions'] = questions.availables(self.get_object())
        context['examteachersubjects'] = ExamTeacherSubject.objects.filter(exam=exam, examquestion__question__in=context['questions']).order_by('order', 'created_at').distinct()
        context['iterator'] = itertools.count(start=1)
        context['iterator_print'] = itertools.count(start=1)
        context["number_print_iterator"] = itertools.count(start=1)

        context["can_change_questions_order"] = not Application.objects.filter(
            Q(
                Q(exam=self.get_object()),
                Q(
                    Q(answer_sheet__isnull=False),
                    ~Q(answer_sheet="")
                )
            )
        ).exists()

        context['exam_headers'] = ExamHeader.objects.filter(
            user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache()
        ).distinct().values('pk', 'name')

        return context

class ClientCustomPageListView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'dashboard/exams/custom_pages_list_new.html'
    permission_required = 'exams.view_clientcustompage'
    required_permissions = [settings.COORDINATION]
    queryset = ClientCustomPage.objects.all()
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(client__in=self.request.user.get_clients_cache()).order_by('-created_at')
        return queryset

class CustomPageDuplicateView(LoginRequiredMixin, CheckHasPermission, generics.CreateAPIView):
    serializer_class = CustomPageDuplicateSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )
    queryset = ClientCustomPage.objects.all()
    required_permissions = [settings.COORDINATION, ]

    def perform_create(self, serializer):
        original_page = ClientCustomPage.objects.get(pk=self.kwargs['pk'])

        new_page = ClientCustomPage.objects.create(
            client=original_page.client,
            name="Cópia - " + original_page.name,
            location=original_page.location,
            type=original_page.type,
            file=original_page.file,
            content=original_page.content,
        )

        serializer.instance = new_page
    
class ClientCustomPageCreateView(LoginRequiredMixin, CheckHasPermission, CreateView):
    template_name = 'dashboard/exams/custom_pages_create_update.html'
    required_permissions = [settings.COORDINATION]
    permission_required = 'exams.add_clientcustompage'
    queryset = ClientCustomPage.objects.all()
    form_class = ClientCustomPageForm
    success_url = reverse_lazy('exams:custom-pages-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs
    
class ClientCustomPageUpdateView(LoginRequiredMixin, CheckHasPermission, UpdateView):
    template_name = 'dashboard/exams/custom_pages_create_update.html'
    required_permissions = [settings.COORDINATION]
    permission_required = 'exams.change_clientcustompage'
    queryset = ClientCustomPage.objects.all()
    form_class = ClientCustomPageForm

    def get_success_url(self):
        return reverse_lazy('exams:custom-pages-list')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(client__in=self.request.user.get_clients_cache())
        return queryset
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

class ClientCustomPageDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = ClientCustomPage
    queryset = ClientCustomPage.objects.all()
    success_message = "Página removida com sucesso!"
    permission_required = 'exams.delete_clientcustompage'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(client=self.request.user.client)
        return queryset

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', None)
    
class CustomPagePrintTemplateView(LoginOrTokenRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'dashboard/exams/custom_pages_print.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.GET.get('application_student'):
            application_student = ApplicationStudent.objects.get(pk=self.request.GET.get('application_student'))
            context['application_student'] = application_student
            context['school_classe'] = application_student.get_last_class_student()
            
        if self.request.GET.get('application'):
            context['application'] = Application.objects.get(pk=self.request.GET.get('application'))
            
        if self.request.GET.get('school_classe'):
            context['school_classe'] = SchoolClass.objects.get(pk=self.request.GET.get('school_classe'))
            
        if self.request.GET.get('custom_page'):
            context['custom_pages'] = ClientCustomPage.objects.filter(pk__in=self.request.GET.getlist('custom_page'))
        
        return context

class ExamBackgroundImageListView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'dashboard/exams/exam_background_image_list.html'
    # permission_required = 'exams.view_clientcustompage'
    required_permissions = [settings.COORDINATION]
    queryset = ExamBackgroundImage.objects.all()
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(client__in=self.request.user.get_clients_cache()).order_by('-created_at')
        return queryset

class ExamBackgroundImageCreateView(LoginRequiredMixin, CheckHasPermission, CreateView):
    template_name = 'dashboard/exams/exam_background_create_update.html'
    required_permissions = [settings.COORDINATION]
    # permission_required = 'exams.add_clientcustompage'
    queryset = ExamBackgroundImage.objects.all()
    form_class = ExamBackgroundImageForm
    success_url = reverse_lazy('exams:backgrounds-list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

class ExamBackgroundImageUpdateView(LoginRequiredMixin, CheckHasPermission, UpdateView):
    template_name = 'dashboard/exams/exam_background_create_update.html'
    required_permissions = [settings.COORDINATION]
    # permission_required = 'exams.add_clientcustompage'
    queryset = ExamBackgroundImage.objects.all()
    form_class = ExamBackgroundImageForm
    success_message = "Imagem de fundo atualizada com sucesso!"    

    def get_success_url(self):
        return reverse_lazy('exams:backgrounds-list')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(client=self.request.user.client)
        return queryset
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

class ExamBackgroundImageDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = ClientCustomPage
    queryset = ExamBackgroundImage.objects.all()
    success_message = "Imagem de fundo removida com sucesso!"
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(client=self.request.user.client)
        return queryset

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', None)

class PrintExamWithPrintServiceDetailView(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, settings.TEACHER, settings.PARTNER]
    queryset = Exam.objects.all()
    
    def get_queryset(self):
        
        user = self.request.user
        queryset = super().get_queryset()
        
        if user.is_freemium:
            
            queryset.filter(
                created_by=user,
            )
        
        else:
            
            queryset = queryset.filter(
                coordinations__unity__client=user.client,
                is_abstract=False,
            )
        
        queryset = queryset.exclude(
            application__automatic_creation=True,
        ).distinct()
        
        return queryset

    def get(self, request, *args, **kwargs):
        
        try:
            exam: Exam = self.get_object()
            
            params = urlencode(self.request.GET)
            
            if not params:
                params = exam.get_printing_params()

            print_url = f'{reverse("exams:exam_print", kwargs={ "pk": exam.id })}?{params}&pass_check_can_print=true'

            data = {
                "url": settings.BASE_URL + print_url,
                "filename": f"detached_{str(exam.id)}.pdf",
                "check_loaded_element": True,
                "wait_seconds": True
            }

            auth_token = get_service_account_oauth2_token(settings.PRINTING_SERVICE_BASE_URL)
            headers = {"Authorization": f"Bearer {auth_token}"}

            print_url = settings.PRINTING_SERVICE_BASE_URL + settings.PRINTING_SERVICE_PATH
            with get_session_retry().post(print_url, json=data, headers=headers, stream=True) as r:
                file = BytesIO(r.content)
                file.seek(0)

            response = HttpResponse(file, content_type='application/pdf')
            
            return response

        except Exception as e:
            print(e)
            logger = logging.getLogger('fiscallizeon')
            remote_address = self.request.META.get('HTTP_X_FORWARDED_FOR') or self.request.META.get('REMOTE_ADDR')
            logger.error(e, extra={
                'remote_address': remote_address,
                'user': self.request.user,
                'user_pk': self.request.user.pk,
            })
            return HttpResponse('Não foi possível gerar o arquivo para impressão')

class ExamsImportTemplateView(LoginRequiredMixin, CheckHasPermission, FormView):
    template_name = 'exams/imports/exams_import.html'
    model = Exam
    form_class = ExamImportForm
    success_url = reverse_lazy('exams:exams_import')
    permission_required = 'exams.can_import_exams'

    def form_valid(self, form):
        import os
        from fiscallizeon.exams.tasks.exams_imports import exams_imports
        from django.core.files.storage import FileSystemStorage
        from fiscallizeon.core.storage_backends import PrivateMediaStorage
        
        file = form.cleaned_data.get('file')

        os.makedirs('tmp/csv_import', exist_ok=True)

        tmp_file = os.path.join('tmp/csv_import', file.name)
        FileSystemStorage(location="tmp/csv_import").save(file.name, file)

        fs = PrivateMediaStorage()
        saved_file = fs.save(
            f'temp/{file.name}',
            open(tmp_file, 'rb')
        )
        os.remove(tmp_file)
        csv_url = fs.url(saved_file)
            
        task_id = f'IMPORT_EXAMS_{str(self.request.user.id)}'
        exams_imports.apply_async(task_id=task_id,
            kwargs={
                'user_id': self.request.user.id,
                'csv_url': csv_url,
            }
        ).forget()
            
        return super().form_valid(form)
    
class ExamsRequestImportTemplateView(LoginRequiredMixin, CheckHasPermission, FormView):
    template_name = 'exams/imports/exams_request_import.html'
    model = Exam
    form_class = ExamImportForm
    success_url = reverse_lazy('exams:exams_request_import')
    permission_required = 'exams.can_import_examteachersubjects'

    def form_valid(self, form):
        import os
        from fiscallizeon.exams.tasks.exams_imports import elaboration_request_import
        from django.core.files.storage import FileSystemStorage
        from fiscallizeon.core.storage_backends import PrivateMediaStorage
        
        file = form.cleaned_data.get('file')
        force_create_teacher_subject = self.request.POST.get('force_create_teacher_subject', False)

        os.makedirs('tmp/csv_import', exist_ok=True)

        tmp_file = os.path.join('tmp/csv_import', file.name)
        FileSystemStorage(location="tmp/csv_import").save(file.name, file)

        fs = PrivateMediaStorage()
        saved_file = fs.save(
            f'temp/{file.name}',
            open(tmp_file, 'rb')
        )
        os.remove(tmp_file)
        csv_url = fs.url(saved_file)
            
        task_id = f'IMPORT_ELABORATION_REQUEST_{str(self.request.user.id)}'
        elaboration_request_import.apply_async(task_id=task_id,
            kwargs={
                'user_id': self.request.user.id,
                'csv_url': csv_url,
                'force_create_teacher_subject': force_create_teacher_subject,
            }
        ).forget()
            
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["force_create_teacher_subject"] = self.request.POST.get('force_create_teacher_subject', False)
        return context

class ExamsRequestImportAuxiliaryTemplateView(LoginRequiredMixin, CheckHasPermission, View):
    
    def get(self, request, *args, **kwargs):
        user = self.request.user

        # Obtenha todas as disciplinas disponíveis do usuário
        available_subjects = user.get_availables_subjects()
        subjects_names = list(available_subjects.annotate(full_name=Concat(F('name'), Value(' - '), F('knowledge_area__name'))).values_list('full_name', flat=True).distinct())
        inspectors = Inspector.objects.filter(user__is_active=True, coordinations__in=user.get_coordinations_cache()).annotate(
                subject_name=Concat(F('subjects__name'), Value(' - '), F('subjects__knowledge_area__name'))
            ).values_list('email', 'name', 'subject_name').distinct()
        inspectors_emails, inspectors_names, inspectors_subjects = zip(*inspectors)
        inspectors_emails = list(inspectors_emails)
        inspectors_names = list(inspectors_names)
        inspectors_subjects = list(inspectors_subjects)
        reviewers_emails, reviewers_names = zip(*inspectors.filter(is_discipline_coordinator=True).values_list('email', 'name').distinct())
        reviewers_emails = list(reviewers_emails)
        reviewers_names = list(reviewers_names)
        allow_teacher_give_grades = ['TRUE', 'FALSE']
    
        # Obtenha as séries
        series = ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'M1', 'M2', 'M3']

        # Determine o tamanho máximo entre as três listas
        max_length = max(len(subjects_names), len(series), len(inspectors_emails), len(inspectors_names), len(inspectors_subjects), len(inspectors_emails), len(reviewers_names), len(allow_teacher_give_grades))

        # Preencha as listas com valores padrão para terem o mesmo tamanho
        subjects_names += [''] * (max_length - len(subjects_names))
        series += [''] * (max_length - len(series))
        inspectors_emails += [''] * (max_length - len(inspectors_emails))
        inspectors_names += [''] * (max_length - len(inspectors_names))
        inspectors_subjects += [''] * (max_length - len(inspectors_subjects))
        reviewers_emails += [''] * (max_length - len(reviewers_emails))
        reviewers_names += [''] * (max_length - len(reviewers_names))
        allow_teacher_give_grades += [''] * (max_length - len(allow_teacher_give_grades))
        
        # Crie o dicionário de dados com listas de mesmo tamanho
        data = {
            'Professores': inspectors_emails,
            'Professores (nome)': inspectors_names,
            'Professores (disciplinas)': inspectors_subjects,
            'Disciplinas': subjects_names,
            'Séries': series,
            'Revisores': reviewers_emails,
            'Revisores (nome)': reviewers_names,
            'Permitir que o professor distribua nota': allow_teacher_give_grades,
        }

        # Crie um DataFrame com os dados
        df = pd.DataFrame(data)

        # Crie o CSV a partir do DataFrame
        csv_file = df.to_csv(index=False)

        # Crie uma resposta HTTP com o CSV
        response = HttpResponse(csv_file, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="documento auxiliar.csv"'  # Nome do arquivo

        return response

class ExamsImportAuxiliaryTemplateView(LoginRequiredMixin, CheckHasPermission, View):
    
    def get(self, request, *args, **kwargs):

        user = self.request.user

        available_subjects = user.get_availables_subjects()

        # Obtenha todas as disciplinas disponíveis do usuário
        exam_categories_list = [choice[1] for choice in Exam.CATEGORY_CHOICES]
        stages_list = list(TeachingStage.objects.filter(client=user.client).values_list('name', flat=True))
        education_system_list = list(EducationSystem.objects.filter(client=user.client).values_list('name', flat=True))
        exam_base_text_location_choices_list = [choice[1] for choice in Exam.BASE_TEXT_LOCATION_CHOICES]
        coordinations_list = list(SchoolCoordination.objects.filter(unity__client=user.client).annotate(full_name=Concat('unity__name', Value(' - '), 'name')).order_by('full_name').values_list('full_name', flat=True))
        
        # subjects_names_list = list(available_subjects.annotate(full_name=Concat(F('name'), Value(' - '), F('knowledge_area__name'))).values_list('full_name', flat=True).distinct())
        
        subjects_names_list = list(SubjectRelation.objects.filter(
            client=user.client
        ).values_list("name", flat=True))
        exists_orientations = list(ExamOrientation.objects.filter(
            user__coordination_member__coordination__unity__client=user.client
        ).values_list('title', flat=True).distinct())
        deadline_for_review = ['dd/mm/yyyy']
        # Determine o tamanho máximo entre as três listas
        max_length = max(len(exam_categories_list), len(exam_base_text_location_choices_list), len(stages_list), len(education_system_list), len(subjects_names_list), len(exists_orientations), len(coordinations_list), len(deadline_for_review))
        
        # Preencha as listas com valores padrão para terem o mesmo tamanho
        exam_categories_list += [''] * (max_length - len(exam_categories_list))
        exam_base_text_location_choices_list += [''] * (max_length - len(exam_base_text_location_choices_list))
        stages_list += [''] * (max_length - len(stages_list))
        coordinations_list += [''] * (max_length - len(coordinations_list))
        education_system_list += [''] * (max_length - len(education_system_list))
        subjects_names_list += [''] * (max_length - len(subjects_names_list))
        exists_orientations += [''] * (max_length - len(exists_orientations))
        deadline_for_review += [''] * (max_length - len(deadline_for_review))

        # Crie o dicionário de dados com listas de mesmo tamanho
        data = {
            'Tipos de avaliações': exam_categories_list,
            'Etapas do ensino': stages_list,
            'Sistemas de ensino': education_system_list,
            'Onde serão mostrados os textos base': exam_base_text_location_choices_list,
            'Disciplinas relacionadas': subjects_names_list,
            'Orientação existente': exists_orientations,
            'Coordenações': coordinations_list,
            'Data final para revisão': deadline_for_review,
        }

        # Crie um DataFrame com os dados
        df = pd.DataFrame(data)

        # Crie o CSV a partir do DataFrame
        csv_file = df.to_csv(index=False)

        # Crie uma resposta HTTP com o CSV
        response = HttpResponse(csv_file, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="documento auxiliar.csv"'  # Nome do arquivo

        return response





class ExamFreemiumDownloadFileViewView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    required_permissions = [settings.COORDINATION, settings.TEACHER, settings.PARTNER]
    queryset = Exam.objects.all()

    
    def test_func(self):
        self.user = self.request.user
        return self.user.is_freemium 
    
    def get(self, request, pk):
        template_name = "dashboard/exams/exam_preview/exam_preview_simple.html"

        exam = Exam.objects.get(pk=pk)
        client = self.request.user.client
        exam_questions = ExamQuestion.objects.filter(exam=exam).select_related('question').order_by('exam_teacher_subject__order', 'order').availables()
        exam_questions = exam_questions.order_by('exam_teacher_subject__order', 'order').distinct()
        base_texts_mapping = {}
        index = 1
        for exam_question in exam_questions:
            for base_text in exam_question.question.base_texts.all():
                if base_text not in base_texts_mapping:
                    base_texts_mapping[base_text] = []
                base_texts_mapping[base_text].append(index) 
            index += 1

        context = {
            'exam': exam,
            'client': client,
            'exam_questions': exam_questions,
            'base_texts_mapping': base_texts_mapping,
        }

        html = render_to_string(template_name, context)

        try:

            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_docx_file:
                output_file = temp_docx_file.name
                pypandoc.convert_text(html, 'docx', format='html', outputfile=output_file)
                with open(output_file, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                    response['Content-Disposition'] = 'attachment; filename="output.docx"'
                return response
        except Exception as e:
            mensagem = f"Erro ao converter o arquivo HTML: {str(e)}"
            return HttpResponse(mensagem, status=500)

class ExamEssayDetailView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/exams/exam_detail_essay.html'
    model = Exam
    required_permissions = [settings.COORDINATION, settings.TEACHER]

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated and not user.client_has_essay_system:
            messages.warning(request, 'Cliente não possui este módulo')
            return redirect('core:redirect_dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    
    def get_context_data(self, **kwargs):
        today = timezone.now().astimezone().date()
        context = super().get_context_data(**kwargs)
        
        school_class = self.request.GET.get('school_class', '')
        
        user = self.request.user
        
        self.application_students_exam = ApplicationStudent.objects.filter(
            application__exam=self.get_object(),
        )
        
        school_classes = SchoolClass.objects.filter(
            students__applicationstudent__in=self.application_students_exam,
            school_year=self.get_object().created_at.year
        ).distinct()

        context['school_classes'] = school_classes
        
        context['school_class'] = school_class
        
        list_filters = [school_class]
        context['count_filters'] = len(list_filters) - list_filters.count("")
        
        return context
    

class EssayGradeImportTemplateView(LoginRequiredMixin, CheckHasPermission, FormView):
    model = Exam
    form_class = ExamImportForm
    permission_required = 'exams.can_import_exams'
    success_url = reverse_lazy('exams:essay_grade_import')
    template_name = 'exams/imports/essay_grade_import.html'

    def form_valid(self, form):
        import os
        from fiscallizeon.exams.tasks.exams_imports import essay_grades_import
        from fiscallizeon.core.storage_backends import PrivateMediaStorage
        from django.core.files.storage import FileSystemStorage

        file = form.cleaned_data.get('file')

        os.makedirs('tmp/csv_import', exist_ok=True)
        tmp_file = os.path.join('tmp/csv_import', file.name)
        FileSystemStorage(location='tmp/csv_import').save(file.name, file)

        fs = PrivateMediaStorage()
        saved_file = fs.save(
            f'temp/{file.name}',
            open(tmp_file, 'rb')
        )
        os.remove(tmp_file)
        csv_url = fs.url(saved_file)

        task_id = f'IMPORT_ESSAY_GRADES_{str(self.request.user.id)}'
        essay_grades_import.apply_async(task_id=task_id,
            kwargs={
                'user_id': self.request.user.id,
                'csv_url': csv_url,
            }
        ).forget()

        return super().form_valid(form)
        
    



class ExamReviewsListView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, ListView):
    model = StatusQuestion
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    permission_required = 'exams.view_exam'
    template_name = 'dashboard/exams/reviews.html'
    paginate_by = 18
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        queryset = (
            queryset
            .filter(
                user__isnull=False,
                exam_question__exam__coordinations__unity__client=user.client
            )
            .order_by('-created_at')
            .distinct()
        )

        if user.user_type == settings.TEACHER:
            queryset = queryset.filter(
                exam_question__exam__coordinations__in=user.get_coordinations_cache(),
                exam_question__exam_teacher_subject__teacher_subject__subject__in=user.inspector.subjects.all()
            )   

        if q_name := self.request.GET.get('q_name'):
            queryset = queryset.filter(exam_question__exam__name__icontains=q_name)
        
        if q_user := self.request.GET.get('q_user'):
            queryset = queryset.filter(user__name__icontains=q_user)
            
        if q_teaching_stages := self.request.GET.getlist('q_teaching_stages'):
            queryset = queryset.filter(exam_question__exam__teaching_stage__in=q_teaching_stages)
        
        if q_status := self.request.GET.getlist('q_status'):
            queryset = queryset.filter(status__in=q_status)

        if q_only_with_note := self.request.GET.get('q_only_with_note'):
            queryset = queryset.filter(
                Q(note__isnull=False),
                ~Q(note__exact='')
            ).exclude(
                note__icontains="Estou de acordo com a questão"
            )

        if q_only_not_applied := self.request.GET.get('q_only_not_applied'):
            queryset = queryset.filter(
                is_checked_by__isnull=True
            )
            
        if year := self.request.GET.get('year'):
            queryset = queryset.filter(
                created_at__year=year
            )
        else:
            queryset = queryset.filter(
                created_at__year=timezone.now().year
            )
        
        return queryset

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated and not request.user.client_has_exam_elaboration:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        list_filters = []
        
        if q_name := self.request.GET.get('q_name'):
            context['q_name'] = q_name
            list_filters.append(q_name)
        
        if q_user := self.request.GET.get('q_user'):
            context['q_user'] = q_user
            list_filters.append(q_user)
        
        if q_teaching_stages := self.request.GET.getlist('q_teaching_stages'):
            context['q_teaching_stages'] = q_teaching_stages
            list_filters.append(q_teaching_stages)
        
        if q_status := self.request.GET.getlist('q_status'):
            context['q_status'] = q_status
            list_filters.append(q_status)
            
        if q_current_status := self.request.GET.getlist('q_current_status'):
            context['q_current_status'] = q_current_status
            list_filters.append(q_current_status)
        

        if q_only_with_note := self.request.GET.get('q_only_with_note'):
            context['q_only_with_note'] = q_only_with_note
            list_filters.append(q_only_with_note)

        if year := self.request.GET.get('year'):
            context['year'] = int(year)
        else:
            context['year'] = timezone.now().year

        context['count_filters'] = len(list_filters) - list_filters.count("")
        
        context["teaching_stages"] = TeachingStage.objects.annotate(length=Length('name')).filter(client__in=user.get_clients_cache()).order_by('length', 'name')
        
        context["status_choices"] = StatusQuestion.STATUS_CHOICES
        context["exam_status_choices"] = Exam.STATUS_CHOICES
        
        return context
    

class ExamAnswersCorrectionDetailView(LoginRequiredMixin, DetailView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    queryset = Exam.objects.all()
    template_name = 'dashboard/exams/exam_essay_correction.html'
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated and not user.client_has_essay_system:
            messages.warning(request, 'Cliente não possui este módulo')
            return redirect('core:redirect_dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        queryset = queryset.filter(coordinations__unity__client=user.client)
        return queryset.distinct()
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().astimezone().date()
        user = self.request.user
        exam = self.get_object()
        
        school_classes = SchoolClass.objects.filter(
            students__applicationstudent__application__in=exam.application_set.all(),
            school_year=self.get_object().created_at.year
        ).distinct()
        
        context['school_classes'] = school_classes
        
        context['school_class'] = self.request.GET.get('school_class')
        context['application_student'] = self.request.GET.get('application_student')
        
        return context
    
class DeviationsListView(LoginRequiredMixin, ListView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    queryset = CorrectionDeviation.objects.all()
    paginate_by = 10
    template_name = 'dashboard/exams/deviations_list.html'
    
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated and not user.client_has_essay_system:
            messages.warning(request, 'Cliente não possui este módulo')
            return redirect('core:redirect_dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        queryset = queryset.filter(
            Q(client=user.client)
        )
        return queryset.distinct()
    
class DeviationCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    template_name = 'dashboard/exams/deviation_create_update.html'
    queryset = CorrectionDeviation.objects.all()
    form_class = CorrectionDeviationForm
    success_message = 'Desvio de correção adicionado.'
    success_url = reverse_lazy('exams:deviations_list')
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated and not user.client_has_essay_system:
            messages.warning(request, 'Cliente não possui este módulo')
            return redirect('core:redirect_dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs
    
class DeviationUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    template_name = 'dashboard/exams/deviation_create_update.html'
    queryset = CorrectionDeviation.objects.all()
    form_class = CorrectionDeviationForm
    success_message = 'Desvio de correção atualizado.'
    success_url = reverse_lazy('exams:deviations_list')
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated and not user.client_has_essay_system:
            messages.warning(request, 'Cliente não possui este módulo')
            return redirect('core:redirect_dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        queryset = queryset.filter(
            Q(client=user.client)
        )
        return queryset.distinct()
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs
    
class DeviationDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    model = CorrectionDeviation
    queryset = CorrectionDeviation.objects.all()
    success_message = 'Desvio de correção removido!'
    success_url = reverse_lazy('exams:deviations_list')
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated and not user.client_has_essay_system:
            messages.warning(request, 'Cliente não possui este módulo')
            return redirect('core:redirect_dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        queryset = queryset.filter(
            Q(client=user.client)
        )
        return queryset.distinct()
    

exam_print_freemium = ExamFreemiumDownloadFileViewView.as_view()
exams_list = ExamListView.as_view()
exams_list_v2 = ExamListViewV2.as_view()
exams_review = ExamReviewListView.as_view()
exams_create = ExamCreateView.as_view()
exam_print_v2 = ExamPrintV2View.as_view()
exams_update = ExamUpdateView.as_view()
exam_review = ExamReviewView.as_view()
exams_delete = ExamDeleteView.as_view()
exams_detail = ExamDetailView.as_view()
exams_detail_enunciation = ExamDetailEnunciationView.as_view()
exams_preview = ExamPreviewView.as_view()
exams_preview_simple = ExamPreviewSimpleView.as_view()

exams_inspector_preview = ExamInspectorPreviewView.as_view()
exam_print = ExamPrintView.as_view()
exam_homework_print = ExamHomeworkPrintView.as_view()
exam_template_print = ExamTemplateDetailView.as_view()
exam_answered_print = ExamAnsweredPrintView.as_view()
exam_copy = ExamCopyView.as_view()
exam_questions_import = ImportExamQuestionsView.as_view()

# Exam Teacher
exam_teacher_create_update = ExamTeacherCreateUpdateTemplateView.as_view()

# Exam Header
exam_header_create = ExamHeaderCreate.as_view()
exam_header_update = ExamHeaderUpdateView.as_view()
exam_header_delete = ExamHeaderDeleteView.as_view()
exam_header_list = ExamHeaderListView.as_view()



exam_teacher_subject_edit_questions = ExamTeacherSubjectEditQuestionsView.as_view()
exam_teacher_subject_before_edit_questions = ExamTeacherSubjectBeforeEditQuestionsView.as_view()

dash_exam_teacher_detail_questions = DashTeacherExamQuestionsDetailView.as_view()
dash_exam_teacher_detail_bncc = DashTeacherExamQuestionsBNCCDetailView.as_view()
dash_exam_teacher_detail_students = DashTeacherExamStudentsDetailView.as_view()
dash_exam_teacher_detail_general = DashTeacherExamGeneralDetailView.as_view()
