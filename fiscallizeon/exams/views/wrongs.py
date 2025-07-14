from django.conf import settings
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q, Count
from django.views.generic import ListView
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin

from fiscallizeon.students.models import Student
from fiscallizeon.exams.models import Exam, Wrong
from fiscallizeon.core.utils import CheckHasPermission

class WrongsStudentListView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'dashboard/wrongs/wrongs_student_detail.html'
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    permission_required = 'exams.view_wrong'
    model = Wrong
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated and self.request.user.user_type  == 'teacher' and not self.request.user.inspector.can_response_wrongs:
            messages.warning(request, 'Acesso negado! Você não tem permissão para responder erros.')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        return super(WrongsStudentListView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(WrongsStudentListView, self).get_queryset()

        queryset = queryset.filter(
            student=self.kwargs['student'],
            student__client__in=self.request.user.get_clients_cache()
        ).order_by('created_at')
        
        if self.request.GET.get('exam'):
            queryset = queryset.filter(exam_question__exam=self.request.GET.get('exam'))

        if self.request.GET.get('status'):
            queryset = queryset.filter(status__in=self.request.GET.getlist('status'))
        
        if self.request.GET.get('exam_name'):
            queryset = queryset.filter(exam_question__exam__name__icontains=self.request.GET.get('exam_name'))

        else:
            queryset = queryset.filter(
                Q(status=Wrong.AWAITING_REVIEW) | 
                Q(status=Wrong.REOPENED)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if not self.request.GET.get('status'):
            context['status'] = [str(Wrong.AWAITING_REVIEW), str(Wrong.REOPENED)]
        else:
            context['status'] = self.request.GET.getlist('status')

        context["params"] = self.request.META['QUERY_STRING']
        if self.request.GET.get('exam'):
            context["exam"] = Exam.objects.filter(pk=self.request.GET.get('exam'))

        context['student'] = Student.objects.get(pk=self.kwargs['student'])
        context["exam_name"] = self.request.GET.get('exam_name', '') 

        list_filters = [context['status'], context['exam_name']]
        context['count_filters'] = len(list_filters) - list_filters.count("")

        return context

class WrongsExamsListView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'dashboard/wrongs/wrongs_exams_list.html'
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    permission_required = 'exams.view_wrong'
    model = Wrong
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        
        if self.request.user.is_authenticated:
            if not self.request.user.client_has_wrongs:
                messages.warning(request, 'Acesso negado! Você não possui este módulo.')
                return HttpResponseRedirect(reverse('core:redirect_dashboard'))

            if self.request.user.user_type  == 'teacher' and not self.request.user.inspector.can_response_wrongs:
                messages.warning(request, 'Acesso negado! Você não tem permissão para responder erros.')
                return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        return super(WrongsExamsListView, self).dispatch(request, *args, **kwargs)
    

    def get_queryset(self):
        queryset = super(WrongsExamsListView, self).get_queryset()
        
        queryset = queryset.filter(
            student__client__in=self.request.user.get_clients_cache()
        ).order_by('created_at')

        if hasattr(self.request.user, 'inspector'):
            if not self.request.user.inspector.can_answer_wrongs_others_teachers:
                queryset = queryset.filter(
                    exam_question__exam_teacher_subject__teacher_subject__teacher=self.request.user.inspector
                )
            queryset = queryset.filter(
                exam_question__exam_teacher_subject__teacher_subject__subject__in=self.request.user.inspector.subjects.all()
            )

        if self.request.GET.get('status'):
            queryset = queryset.filter(status__in=self.request.GET.getlist('status'))
        else:
            queryset = queryset.filter(
                Q(status=Wrong.AWAITING_REVIEW) | 
                Q(status=Wrong.REOPENED)
            )
        if self.request.GET.get('student'):
            queryset = queryset.filter(student=self.request.GET.get('student'))

        if self.request.GET.get('student_name'):
            queryset = queryset.filter(student__name__icontains=self.request.GET.get('student_name'))

        if self.request.GET.get('exam'):
            queryset = queryset.filter(exam_question__exam=self.request.GET.get('exam'))

        if self.request.GET.get('exam_name'):
            queryset = queryset.filter(exam_question__exam__name__icontains=self.request.GET.get('exam_name'))
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()

        if not self.request.GET.get('status'):
            context['status'] = [str(Wrong.AWAITING_REVIEW), str(Wrong.REOPENED)]
        else:
            context['status'] = self.request.GET.getlist('status')

        students = Student.objects.filter(pk__in=self.get_queryset().values_list('student', flat=True).distinct()).annotate(
            opened_wrongs=Count('wrongs', filter=Q(wrongs__status=Wrong.AWAITING_REVIEW, wrongs__pk__in=queryset)),
            opened_accepteds=Count('wrongs', filter=Q(wrongs__status=Wrong.ACCEPTED, wrongs__pk__in=queryset)),
            opened_refuseds=Count('wrongs', filter=Q(wrongs__status=Wrong.REFUSED, wrongs__pk__in=queryset)),
            opened_reopeneds=Count('wrongs', filter=Q(wrongs__status=Wrong.REOPENED, wrongs__pk__in=queryset)),
        ).order_by('-opened_wrongs')
        
        context["student_list"] = students

        context["params"] = self.request.META['QUERY_STRING']

        context["student_name"] = self.request.GET.get('student_name', '') 
        context["exam_name"] = self.request.GET.get('exam_name', '') 
        if self.request.GET.get('exam'):
            context["exam"] = Exam.objects.get(pk=self.request.GET.get('exam') )
        
        list_filters = [context['status'], context['student_name'], context['exam_name']]

        context['count_filters'] = len(list_filters) - list_filters.count("")

        return context

class StudentWrongsListView(LoginRequiredMixin, ListView):
    queryset = Wrong.objects.all()
    template_name = 'dashboard/wrongs/student_wrongs_list.html'
    permission_classes = [settings.STUDENT]

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user

        if not user or not user.is_authenticated or user.is_anonymous:
            return HttpResponseRedirect(reverse('accounts:login'))
        
        if not user.client_has_wrongs:
            messages.warning(request, 'Acesso negado! Você não tem permissão para acessar esta página.')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        
        return super(StudentWrongsListView, self).dispatch(request, *args, **kwargs)
        

    def get_queryset(self):
        queryset = super(StudentWrongsListView, self).get_queryset()
        queryset = queryset.filter(
            student=self.kwargs['student'],
        ).order_by('created_at')

        if self.request.GET.get('status'):
            queryset = queryset.filter(status__in=self.request.GET.getlist('status'))
        else:
            queryset = queryset.filter(status__in=[str(Wrong.AWAITING_REVIEW), str(Wrong.REOPENED)])

        if self.request.GET.get('exam_name'):
            queryset = queryset.filter(exam_question__exam__name__icontains=self.request.GET.get('exam_name'))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['status'] = self.request.GET.getlist('status')
        context['exam_name'] = self.request.GET.get('exam_name') if self.request.GET.get('exam_name') else ''

        if not context['status']:
            context['status'] = [str(Wrong.AWAITING_REVIEW), str(Wrong.REOPENED)]

        list_filters = [context['status'], context['exam_name']]
        context['count_filters'] = len(list_filters) - list_filters.count("")

        return context

wrongs_student_detail = WrongsStudentListView.as_view()
wrongs_list = WrongsExamsListView.as_view()
student_wrongs_list = StudentWrongsListView.as_view()