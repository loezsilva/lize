import csv
from django.conf import settings
from django.urls import reverse
from django.db.models import F, Q, Count, Func, Case, When
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.views.generic.base import RedirectView
from django.utils import timezone

from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.accounts.mixins import LoginOrTokenRequiredMixin
from .models import NPSApplication, ClassApplication, OMRNPSUpload, OMRNPSPage, ClassApplication, TeacherAnswer
from fiscallizeon.omrnps.forms import OMRNPSUploadForm, OMRNPSErrorFormSet
from fiscallizeon.classes.models import SchoolClass, Grade
from fiscallizeon.clients.models import Unity
from fiscallizeon.omrnps.tasks.ingest.proccess_sheets import proccess_sheets
from fiscallizeon.omrnps.tasks.ingest.reprocess.reproccess_sheets import reproccess_sheets
from django.http import HttpResponse

class NPSApplicationListView(LoginOrTokenRequiredMixin, CheckHasPermission, ListView):
    template_name = 'omrnps/npsapplication_list.html'
    queryset = NPSApplication.objects.all().order_by('-created_at')
    paginate_by = 18
    permission_required = [
        'omrnps.view_npsapplication'
    ]
    
    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        queryset = queryset.filter(
            client__in=user.get_clients_cache()
        )
        
        if self.request.GET.get('year'):
            queryset = queryset.filter(
                date__year=self.request.GET.get('year'),
            )
        else:
            queryset = queryset.filter(
                date__year=timezone.now().year,
            )
        
        if q_name := self.request.GET.get('q_name'):
            queryset = queryset.filter(
                name__unaccent__icontains=q_name
            )
        
        if q_unity := self.request.GET.getlist('q_unity'):
            queryset = queryset.filter(
                school_classes__coordination__unity__in=q_unity
            )
            
        if q_school_class := self.request.GET.getlist('q_school_class'):
            queryset = queryset.filter(
                school_classes__in=q_school_class
            )
            
        if q_grade := self.request.GET.getlist('q_grade'):
            queryset = queryset.filter(
                school_classes__grade__in=q_grade
            )
        
        return queryset.distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        list_filters = []
        
        user = self.request.user

        filter_condition = Q()
        if user.has_high_school_coordinations:
            filter_condition |= Q(level=Grade.HIGHT_SCHOOL)

        if user.has_elementary_school_only_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL)

        if user.has_elementary_school2_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL_2)
        
        context["grades"] = Grade.objects.filter(filter_condition)
        context["unities"] = Unity.objects.filter(client=user.client)
        context['school_classes'] = SchoolClass.objects.filter(
            Q(
				Q(coordination__unity__client=user.client)
			)
        ).distinct('created_at', 'pk').order_by('-created_at').values('pk', 'name', 'coordination__unity__name',  'school_year')
        
        if year := self.request.GET.get('year'):
            context['year'] = year
        else:
            context['year'] = timezone.now().year
        
        if q_name := self.request.GET.get('q_name'):
            context['q_name'] = q_name
            list_filters.append(q_name)
        
        if q_unity := self.request.GET.getlist('q_unity'):
            context['q_unity'] = q_unity
            list_filters.append(q_unity)
            
        if q_school_class := self.request.GET.getlist('q_school_class'):
            context['q_school_class'] = q_school_class
            list_filters.append(q_school_class)
            
        if q_grade := self.request.GET.getlist('q_grade'):
            context['q_grade'] = q_grade
            list_filters.append(q_grade)
            
        context['count_filters'] = len(list_filters) - list_filters.count("")
        
        return context
    

class PrintClassApplicationAnswerSheetDetailView(LoginOrTokenRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'omrnps/export_answer_sheets.html'
    required_permissions = [settings.COORDINATION, ]
    model = ClassApplication

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        qr_code_text = f'{self.object.pk}'
        
        teacher_orders = self.object.teacherorder_set.all().order_by('order')
        
        context['orders'] = [
            teacher_orders[0:4],
            teacher_orders[4:8],
            teacher_orders[8:12],
            teacher_orders[12:16],
        ]
        
        context['qr_code_text'] = f'N:1:{qr_code_text}'
        context['disable_support_chat'] = True
        context['disable_sleek'] = True
        
        return context

class PrintClassApplicationAttendanceListView(LoginOrTokenRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = ['coordination', ]
    template_name = "distribution/lists/attendance_list.html"
    model = ClassApplication

    def get_school_class_students(self):
        return SchoolClass.students.through.objects.filter(
            schoolclass=self.object.school_class,
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rooms_distributions_student'] = self.get_school_class_students()
        context['object'] = self.object.school_class
        context['application'] = self.object.nps_application
        context['hide_dialog'] = True
        return context

class OMRNPSUploadList(LoginOrTokenRequiredMixin, CheckHasPermission, ListView):
    template_name = 'omrnps/npsupload_list.html'
    model = OMRNPSUpload
    paginate_by = 18
    permission_required = [
        'omrnps.view_omrnpsupload'
    ]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        class Unaccent(Func):
            function = 'unaccent'
    
        if user.can_see_all():
            queryset = queryset.filter(
                user__coordination_member__coordination__unity__client=user.client
            ).distinct().select_related('user').order_by('-created_at')
        else:
            queryset = queryset.filter(
                user__coordination_member__coordination__in=user.get_coordinations_cache()
            ).distinct().select_related('user').order_by('-created_at')
        
        if self.request.GET.get('year'):            
            queryset = queryset.filter(
                created_at__date__year=self.request.GET.get('year'),
            )
        else:
            queryset = queryset.filter(
                created_at__date__year=timezone.now().year,
            )
        
        if q_name := self.request.GET.get('q_name'):
            queryset = queryset.filter(
                omrnpspage__class_application__nps_application__name__unaccent__icontains=q_name
            )
            
        if q_file_name := self.request.GET.get('q_file_name'):
            queryset = queryset.annotate(
                normalized_name=Unaccent('raw_pdf')
            ).filter(
                Q(normalized_name__icontains=q_file_name) |
                Q(raw_pdf__icontains=q_file_name)
            )
        
        if q_unity := self.request.GET.getlist('q_unity'):
            queryset = queryset.filter(
                omrnpspage__class_application__school_class__coordination__unity__in=q_unity
            )
            
        if q_school_class := self.request.GET.getlist('q_school_class'):
            queryset = queryset.filter(
                omrnpspage__class_application__school_class__in=q_school_class
            )
            
        if q_grade := self.request.GET.getlist('q_grade'):
            queryset = queryset.filter(
                omrnpspage__class_application__school_class__grade__in=q_grade
            )

        return queryset.distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = OMRNPSUploadForm()
        
        list_filters = []
        
        user = self.request.user

        filter_condition = Q()
        if user.has_high_school_coordinations:
            filter_condition |= Q(level=Grade.HIGHT_SCHOOL)

        if user.has_elementary_school_only_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL)

        if user.has_elementary_school2_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL_2)
        
        context["grades"] = Grade.objects.filter(filter_condition)
        context["unities"] = Unity.objects.filter(client=user.client)
        context['school_classes'] = SchoolClass.objects.filter(
            Q(
				Q(coordination__unity__client=user.client)
			)
        ).distinct('created_at', 'pk').order_by('-created_at').values('pk', 'name', 'coordination__unity__name',  'school_year')
        
        if year := self.request.GET.get('year'):
            context['year'] = year
        else:
            context['year'] = timezone.now().year
        
        if q_name := self.request.GET.get('q_name'):
            context['q_name'] = q_name
            list_filters.append(q_name)
            
        if q_file_name := self.request.GET.get('q_file_name'):
            context['q_file_name'] = q_file_name
            list_filters.append(q_file_name)
        
        if q_unity := self.request.GET.getlist('q_unity'):
            context['q_unity'] = q_unity
            list_filters.append(q_unity)
            
        if q_school_class := self.request.GET.getlist('q_school_class'):
            context['q_school_class'] = q_school_class
            list_filters.append(q_school_class)
            
        if q_grade := self.request.GET.getlist('q_grade'):
            context['q_grade'] = q_grade
            list_filters.append(q_grade)
            
        context['count_filters'] = len(list_filters) - list_filters.count("")
        
        return context
    
class ImportOMRNPSSheetsView(LoginRequiredMixin, CheckHasPermission, FormView):
    template_name = 'omrnps/npsupload_list.html'
    form_class = OMRNPSUploadForm
    required_permissions = [settings.COORDINATION, ]
    permission_required = [
        'omrnps.add_omrnpsupload'
    ]

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_omrnps:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('applications:applications_list'))

        return super(ImportOMRNPSSheetsView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self, **kwargs):
        return reverse('omrnps:omrnps-list')

    def form_invalid(self, form):
        print(form.errors)
        return super().form_invalid(form)

    def form_valid(self, form):
        nps_upload = OMRNPSUpload.objects.create(
            user=self.request.user,
            raw_pdf=form.cleaned_data.get('pdf_scan'),
        )

        proccess_sheets.apply_async(args=[nps_upload.pk])

        return super().form_valid(form)
    
class OMRNPSUploadDetail(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'omrnps/npsupload_detail.html'
    required_permissions = [settings.COORDINATION, ]
    model = OMRNPSUpload
    permission_required = [
        'omrnps.view_omrnpsupload'
    ]

    def get_error_list(self):
        errors = []
        for error in self.object.get_unsolved_errors():
            errors.append({
                'omr_nps_error': str(error.pk),
                'error_image': error.error_image.url if error.error_image else "",
                'page_number': error.page_number,
                'category_description': error.get_category_display(),
            })

        return errors

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        errors_list = self.get_error_list()
        formset = OMRNPSErrorFormSet(initial=errors_list)

        nps_pages = OMRNPSPage.objects.filter(
            upload=self.object
        ).annotate(
            unity_grade=F('unityanswer__grade'),
            unity_grade_id=F('unityanswer__id'),
            unity_grade_created_by=F('unityanswer__created_by'),
            total_read_answers_count=Count('teacheranswer', filter=Q(teacheranswer__created_by__isnull=True), distinct=True),
            total_read_unity_answers=Count('unityanswer', filter=Q(unityanswer__created_by__isnull=True), distinct=True),
            total_corrected_answers=Count('teacheranswer', filter=Q(teacheranswer__created_by__isnull=False), distinct=True),
            total_corrected_unity_answers=Count('unityanswer', filter=Q(unityanswer__created_by__isnull=False), distinct=True),
            total_corrected_and_unity_answers=F('total_read_answers_count') + F('total_read_unity_answers'),
            total_read_answers=Case(
                When(
                    Q(total_corrected_and_unity_answers__gt=F('total_read_answers_count')),
                    then=F('total_read_answers_count')
                ), default=F('total_corrected_and_unity_answers')
            )
        ).distinct()

        context['nps_pages'] = nps_pages
        context['formset'] = formset
        return context

class OMRNPSUploadFixView(LoginRequiredMixin, RedirectView):
    permission_required = [
        'omrnps.add_omrnpsupload'
    ]
    def get_redirect_url(self, *args, **kwargs):
        formset = OMRNPSErrorFormSet(self.request.POST, self.request.FILES)

        if formset.is_valid():
            cleaned_data = formset.cleaned_data
            valid_corrections = []
            
            for form_data in cleaned_data:
                del form_data['error_image']
                school_class = form_data.get('school_class', None)
                application = form_data.get('application', None)

                form_data['application'] = application.pk if application else None
                form_data['school_class'] = school_class.pk if school_class else None

                if school_class and application:
                    valid_corrections.append(form_data)

            if valid_corrections:
                reproccess_sheets.apply_async(
                    args=[self.kwargs['pk'], valid_corrections],
                )

                OMRNPSUpload.objects.filter(
                    pk=kwargs['pk']
                ).update(
                    status=OMRNPSUpload.REPROCESSING
                )

            return reverse('omrnps:upload-details', kwargs={'pk': kwargs['pk']})
        else:
            try:
                messages.warning(self.request, formset.errors[0].get('__all__', [''])[0])
            except:
                messages.warning(self.request, str(formset.errors))
            return reverse('omrnps:upload-details', kwargs={'pk': kwargs['pk']})

class OMRNPSUploadDeleteView(LoginRequiredMixin, RedirectView):
    permission_required = [
        'omrnps.add_omrnpsupload'
    ]

    def get_redirect_url(self, *args, **kwargs):
        TeacherAnswer.objects.filter(omr_nps_page__upload=kwargs['pk']).delete()
        OMRNPSUpload.objects.get(pk=kwargs['pk']).delete()
        return reverse('omrnps:omrnps-list')
