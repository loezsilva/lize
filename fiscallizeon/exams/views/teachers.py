from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q, Count, F, Sum, Exists

from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.exams.models import Exam, ExamTeacherSubject, StatusQuestion, ExamQuestion
from fiscallizeon.exams.mixins import ExamTeacherSubjectMixin
from fiscallizeon.applications.models import  Application
from fiscallizeon.core.print_colors import *

class ExamTeacherSubjectListView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, ExamTeacherSubjectMixin, ListView):
    template_name = 'dashboard/exams/teacher_exam_list.html'
    model = ExamTeacherSubject
    required_permissions = [settings.TEACHER]
    paginate_by = 12
    
    def get_template_names(self):
        if version := self.request.GET.get('v'):
            return [f'dashboard/exams/teacher_exam_list_v{version}.html']
        return super().get_template_names()

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_exam_elaboration:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        
        queryset = self.get_exams().select_related(
            'teacher_subject', 
            'teacher_subject__subject', 
            'grade'
        )
    
        if self.request.GET.get('q_name', ""):
            queryset = queryset.filter(
                exam__name__icontains=self.request.GET.get('q_name', "")
            )

        if self.request.GET.get('q_status'):
            queryset = queryset.filter(
                status=self.request.GET.get('q_status')
            )
            
        if self.request.GET.get('q_is_opened'):
            queryset = queryset.filter(
                count_total_questions__lt=F('quantity')
            )

        if self.request.GET.get('exam'):
            queryset = queryset.filter(
                exam=self.request.GET.get('exam')
            )
            
        if self.request.GET.get('q_deadline'):
            queryset = queryset.filter(
                exam__elaboration_deadline=self.request.GET.get('q_deadline')
            )

        if self.request.GET.get('q_not_exam_bag'):
            queryset = queryset.exclude(
                Q(Q(exam__application__answer_sheet__isnull=False) & ~Q(exam__application__answer_sheet="")) |
                Q(Q(exam__application__room_distribution__exams_bag__isnull=False) & ~Q(exam__application__room_distribution__exams_bag=""))
            )
            
        if self.request.GET.get('q_status_question') ==  "reprovado": 
            
            exam_questions = ExamQuestion.objects.filter(
                exam_teacher_subject__in=queryset
            ).distinct()
              
            reproved_exam_questions_ids = StatusQuestion.objects.filter(
                exam_question__in=exam_questions,
                status=StatusQuestion.REPROVED
            ).values_list('exam_question_id', flat=True).distinct()

            queryset = queryset.filter(
                examquestion__in=reproved_exam_questions_ids
            ).distinct()
        
        if self.request.GET.get('q_status_question') ==  "aguardando_correcao":   
            
            exam_questions = ExamQuestion.objects.filter(
                exam_teacher_subject__in=queryset
            ).distinct()
            
            pending_correction = StatusQuestion.objects.filter(
                exam_question__in=exam_questions,
                status=StatusQuestion.CORRECTION_PENDING
            ).values_list('exam_question_id', flat=True).distinct()

            queryset = queryset.filter(
                examquestion__in=pending_correction
            ).distinct()
            
        return queryset.distinct().order_by('exam__elaboration_deadline')
    
    def get_context_data(self, **kwargs):
        
        today = timezone.localtime(timezone.now())
        context = super().get_context_data(**kwargs)
        
        context['selected_filter'] = self.request.GET.get('selected_filter', '')
        
        context['q_name'] = self.request.GET.get('q_name', "")
        context['q_status'] = self.request.GET.get('q_status', "")
        context['q_status_question'] = self.request.GET.get('q_status_question', "")
        
        context['year'] = today.year
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')

        return context
    

class ExamTeacherCorrectionPendenceView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, ExamTeacherSubjectMixin, ListView):
    template_name = 'dashboard/exams/teacher_correction_pendence_list.html'
    model = Exam
    queryset = Exam.objects.all()
    required_permissions = [settings.TEACHER]
    paginate_by = 12
    
    def get_template_names(self):
        if version := self.request.GET.get('v'):
            return [f'dashboard/exams/teacher_correction_pendence_list_v{version}.html']
        return super().get_template_names()

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_followup_dashboard:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        
        today = timezone.now()
        
        user = self.request.user
        
        queryset = super().get_queryset().filter(
            performances_followup__quantity__gt=0,
            performances_followup__deadline__gte=timezone.localtime(today),
            performances_followup__inspectors=user.inspector,
            performances_followup__coordination__in=user.get_coordinations_cache(),
        ).annotate(
            deadline=F('performances_followup__deadline'),
            total=Sum('performances_followup__total'),
            quantity=Sum('performances_followup__quantity'),
        ).order_by('-quantity').distinct()

        if self.request.GET.get('q_name', ""):
            queryset = queryset.filter(
                name__icontains=self.request.GET.get('q_name', "")
            )
        
        if self.request.GET.get('q_status'):
            queryset = queryset.filter(
                status=self.request.GET.get('q_status')
            )
            
        if self.request.GET.get('q_is_opened'):
            queryset = queryset.filter(
                count_total_questions__lt=F('quantity')
            )
        
        return queryset.distinct()
    
    def get_context_data(self, **kwargs):
        
        today = timezone.localtime(timezone.now())
        context = super().get_context_data(**kwargs)
        
        context['selected_filter'] = self.request.GET.get('selected_filter', '')
        
        context['q_name'] = self.request.GET.get('q_name', "")
        context['q_status'] = self.request.GET.get('q_status', "")
        
        context['year'] = today.year
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')

        return context
    
class ExamTeacherReprovedPendenceView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, ExamTeacherSubjectMixin, ListView):
    """
        Essa View deverá ser descontinuada a partir de 04/02/2025
        Ela foi unida ao exams:exams_list, o filtro da queryset foi movido para lá 
    """
    template_name = 'dashboard/exams/teacher_exam_reproved_and_pendence_correction_list.html'
    model = Exam
    queryset = Exam.objects.all()
    required_permissions = [settings.TEACHER]
    paginate_by = 12
    
    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_followup_dashboard:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        
        queryset = self.get_exams().select_related(
            'teacher_subject', 
            'teacher_subject__subject', 
            'grade'
        )

        exam_questions = ExamQuestion.objects.filter(
            exam_teacher_subject__in=queryset
        ).distinct()

        if self.request.GET.get('q_status_question') ==  "reprovado":   
            reproved_exam_questions_ids = StatusQuestion.objects.filter(
                exam_question__in=exam_questions,
                status=StatusQuestion.REPROVED
            ).values_list('exam_question_id', flat=True).distinct()

            queryset = queryset.filter(
                examquestion__in=reproved_exam_questions_ids
            ).distinct()
        
        if self.request.GET.get('q_status_question') ==  "aguardando_correcao":   
            pending_correction = StatusQuestion.objects.filter(
                exam_question__in=exam_questions,
                status=StatusQuestion.CORRECTION_PENDING
            ).values_list('exam_question_id', flat=True).distinct()

            queryset = queryset.filter(
                examquestion__in=pending_correction
            ).distinct()
        
        return queryset.distinct().order_by('exam__elaboration_deadline')
    
    def get_context_data(self, **kwargs):
        
        today = timezone.localtime(timezone.now())
        context = super().get_context_data(**kwargs)
        
        context['selected_filter'] = self.request.GET.get('selected_filter', '')
        
        context['q_name'] = self.request.GET.get('q_name', "")
        context['q_status'] = self.request.GET.get('q_status', "")
        context['q_status_question'] = self.request.GET.get('q_status_question')
        context['year'] = today.year
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')

        return context

class ExamTeacherSubjectToReviewListView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, ExamTeacherSubjectMixin, ListView):
    template_name = 'dashboard/exams/teacher_exam_to_review_list.html'
    model = ExamTeacherSubject
    required_permissions = [settings.TEACHER]
    paginate_by = 12

    def get_template_names(self):
        if version := self.request.GET.get('v'):
            return [f'dashboard/exams/teacher_exam_to_review_list_v{version}.html']
        return super().get_template_names()
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        
        if user and not user.is_anonymous and not user.inspector.is_discipline_coordinator:
            messages.warning(request, 'Você não tem permissão para acessar esta página.')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        user = self.request.user
        teacher = user.inspector
        
        queryset = teacher.get_exams_to_review(return_exam_teacher_subjects=True).annotate(
            count=Count('exam__examquestion', distinct=True),
            count_reviewed_questions=Count(
                'exam__examquestion', 
                filter=Q(
                    Q(exam__examquestion__statusquestion__user=user),
                    Q(
                        Q(exam__examquestion__statusquestion__active=True) |
                        Q(exam__examquestion__statusquestion__status=StatusQuestion.SEEN)
                    )
                ), 
                distinct=True
            )
        ).filter(count__gt=0)
        #.exclude(
        #    count_reviewed_questions__gte=F('count')
        #)
        
        if self.request.GET.get('q_status') == 'await_review':
            queryset = queryset.filter(count_reviewed_questions=0)

        elif self.request.GET.get('q_status') == 'in_review':
            queryset = queryset.filter(count_reviewed_questions__gt=0)

        if self.request.GET.get('q_name', ""):
            queryset = queryset.filter(
                exam__name__icontains=self.request.GET.get('q_name', "")
            )

        return queryset.distinct().order_by('exam__elaboration_deadline')
    
    def get_context_data(self, **kwargs):
        
        today = timezone.localtime(timezone.now())
        context = super().get_context_data(**kwargs)
        
        context['selected_filter'] = self.request.GET.get("selected_filter", "")
        
        context['q_name'] = self.request.GET.get("q_name", "")
        
        context['q_status'] = self.request.GET.get('q_status', "")
        
        context['year'] = today.year
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')

        return context
   
class ExamTeacherSubjectToReviewPDFListView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, ExamTeacherSubjectMixin, ListView):
    template_name = 'dashboard/exams/teacher_exam_to_review_pdf_list.html'
    model = ExamTeacherSubject
    required_permissions = [settings.TEACHER]
    paginate_by = 12
    
    def get_template_names(self):
        if version := self.request.GET.get('v'):
            return [f'dashboard/exams/teacher_exam_to_review_pdf_list_v{version}.html']
        return super().get_template_names()

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        
        if user.is_authenticated and not user.inspector.is_discipline_coordinator:
            messages.warning(request, 'Você não tem permissão para acessar esta página.')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        user = self.request.user
        teacher = user.inspector
        
        filtered_exams = Exam.objects.filter(
            teacher_subjects__teacher=teacher, 
            status=Exam.PDF_REVIEW,
            review_deadline_pdf__gte=timezone.now()
        )

        filtered_exam_ids = filtered_exams.values_list('id', flat=True)

        applications_with_answer_sheets = Application.objects.exclude(
            Q(answer_sheet__isnull=False) & Q(answer_sheet="") 
        ).filter(
            exam__in=filtered_exam_ids 
        )

        exams_without_answer_sheets = filtered_exams.exclude(
            Exists(applications_with_answer_sheets)
        )

        teacher_exam_subjects = ExamTeacherSubject.objects.filter(
            teacher_subject__teacher=teacher,
            exam__in=exams_without_answer_sheets
        )

        exam_questions_in_review_pdf = ExamQuestion.objects.filter(
            exam_teacher_subject__in=teacher_exam_subjects, 
        ).distinct()

        reviewed_exam_question = StatusQuestion.objects.filter(
            exam_question__in=exam_questions_in_review_pdf,
            user=user
        ).filter(
            Q(status=StatusQuestion.APPROVED) |
            Q(status=StatusQuestion.REPROVED) |
            Q(status=StatusQuestion.CORRECTION_PENDING) |
            Q(status=StatusQuestion.CORRECTED) |
            Q(status=StatusQuestion.SEEN) |
            Q(status=StatusQuestion.ANNULLED) |
            Q(status=StatusQuestion.USE_LATER) |
            Q(status=StatusQuestion.DRAFT) |
            Q(status=StatusQuestion.RESPONSE)
        ).values_list('exam_question', flat=True).distinct() 

        unreviewed_exam_questions = exam_questions_in_review_pdf.exclude(id__in=reviewed_exam_question)

        teacher_exam_subjects = teacher_exam_subjects.annotate(
            pending_questions_count=Count(
                'examquestion',  
                filter=Q(examquestion__in=unreviewed_exam_questions) 
            ),
            total_questions=Count('exam__questions')
        ).distinct() 

        if self.request.GET.get('q_status') == 'await_review':
            teacher_exam_subjects = teacher_exam_subjects.filter(
                pending_questions_count=F('total_questions')  
        )
        elif self.request.GET.get('q_status') == 'in_review':
            teacher_exam_subjects = teacher_exam_subjects.filter(
                pending_questions_count__lt=F('total_questions')  
        )
        
        teacher_exam_subjects = teacher_exam_subjects.filter(pending_questions_count__gt=0)

        if self.request.GET.get('q_name', ""):
            teacher_exam_subjects = teacher_exam_subjects.filter(
                exam__name__icontains=self.request.GET.get('q_name', "")
            )

        return teacher_exam_subjects.distinct().order_by('exam__elaboration_deadline')
    
    def get_context_data(self, **kwargs):
        
        today = timezone.now().astimezone().date()
        context = super().get_context_data(**kwargs)
        
        context['selected_filter'] = self.request.GET.get("selected_filter", "")
        
        context['q_name'] = self.request.GET.get("q_name", "")
        
        context['q_status'] = self.request.GET.get('q_status', "")
        
        context['year'] = today.year
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')

        return context