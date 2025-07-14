import io
import csv

from datetime import datetime
from django.db.models import Q
from django.conf import settings
from django.db.models.deletion import ProtectedError
from django.http.response import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.views.generic import ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from rest_framework.generics import ListAPIView
from django.core.cache import cache
from django.apps import apps
from django.db.utils import IntegrityError

from fiscallizeon.classes.models import Grade, SchoolClass

from fiscallizeon.inspectors.models import Inspector, TeacherSubject
from fiscallizeon.inspectors.serializers.inspectors import TeacherSubjectVerySimpleSerializer, TeacherSerializerChangeExperience, InspectorSimpleSerializer
from fiscallizeon.inspectors.forms import InspectorForm
from fiscallizeon.core.utils import CheckHasPermission

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

from fiscallizeon.clients.models import Unity, SchoolCoordination

from fiscallizeon.notifications.models import Notification
from fiscallizeon.notifications.functions import get_and_create_notifications
from rest_framework.response import Response
from rest_framework.generics import UpdateAPIView
from rest_framework import status
from rest_framework.views import APIView

import pyexcel
from django.http import HttpResponse

class TeacherList(LoginRequiredMixin, CheckHasPermission,  ListView):
    model = Inspector
    required_permissions = [settings.COORDINATION, ]
    paginate_by = 30
    permission_required = 'inspectors.view_teacher'
    template_name = "dashboard/teachers/teacher_list_new.html"

    def get_queryset(self):
        queryset = Inspector.objects.filter(
            Q(
                inspector_type=Inspector.TEACHER,
				coordinations__in=self.request.user.get_coordinations_cache(),
                is_inspector_ia=False
			)
        ).distinct()

        if self.request.GET.get('q_pk', ''):
            queryset = queryset.filter(pk=self.request.GET.get('q_pk', ''))

        if self.request.GET.get("q_name", ""):
            queryset = queryset.filter(
                Q(
                    Q(name__icontains=self.request.GET.get("q_name", "")) |
                    Q(email__icontains=self.request.GET.get("q_name", ""))
                )
            )
        
        if self.request.GET.get('q_subject', ""):
            queryset = queryset.filter(
                subjects__name__icontains=self.request.GET.get('q_subject', "")
            )

        if self.request.GET.getlist('q_levels', ""):
            queryset = queryset.filter(
                subjects__knowledge_area__grades__pk__in=self.request.GET.getlist('q_levels', "")
            )

        if self.request.GET.get('q_coordination', ""):
            queryset = queryset.filter(
                coordinations__pk__in=self.request.GET.getlist('q_coordination', [])
            )

        if self.request.GET.get('q_unit', ""):
            queryset = queryset.filter(
                coordinations__unity__pk__in=self.request.GET.getlist('q_unit', [])
            )

        queryset = queryset.filter(
            user__is_active=True
        )

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super(TeacherList, self).get_context_data(**kwargs)
        context['q_pk'] = self.request.GET.get('q_pk', '')
        context['q_name'] = self.request.GET.get("q_name", "")
        context['q_subject'] = self.request.GET.get('q_subject', "")
        context['q_levels'] = self.request.GET.getlist('q_levels', "")
        context['q_coordination'] = self.request.GET.getlist('q_coordination', "")
        context['q_unit'] = self.request.GET.get('q_unit', "")

        list_filters = [context['q_name'], context['q_subject'], context["q_levels"], context["q_coordination"], context["q_unit"]]

        context['count_filters'] = len(list_filters) - list_filters.count("")

        context['levels'] = Grade.objects.all()

        context['coordinations'] = SchoolCoordination.objects.filter(
            pk__in=self.request.user.get_coordinations_cache(),
        ).distinct().order_by()

        context["units"] = Unity.objects.filter(coordinations__in=self.request.user.get_coordinations_cache()).distinct()

        context['q_levels_processed'] = Grade.objects.filter(pk__in=context['q_levels']).count() if context['q_levels'] else ""

        context['q_coordinations_processed'] = len(self.request.GET.getlist('q_coordination', "")) if self.request.GET.getlist('q_coordination', "") else ""
        
        context['q_units_processed'] = len(self.request.GET.getlist('q_unit', "")) if self.request.GET.getlist('q_unit', "") else ""

        return context


class TeacherCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = Inspector
    required_permissions = [settings.COORDINATION, ]
    form_class = InspectorForm
    permission_required = 'inspectors.add_teacher'
    template_name = "dashboard/teachers/teacher_create_update_new.html"
    success_message = "Professor cadastrado com sucesso!"

    def get_form_kwargs(self):
        kwargs = super(TeacherCreateView, self).get_form_kwargs()
        kwargs.update({ 'user' : self.request.user, 'create': True })
        return kwargs

    def get_success_url(self):        
        return reverse('inspectors:teachers_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["classes"] = SchoolClass.objects.filter(
            coordination__in=self.request.user.get_coordinations_cache(),
            school_year=timezone.now().year
        ).distinct().order_by('name')
        context["grades"] = Grade.objects.all()
        
        return context


class TeacherUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = Inspector
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'inspectors.change_teacher'
    form_class = InspectorForm
    template_name = "dashboard/teachers/teacher_create_update_new.html"
    success_message = "Professor atualizado com sucesso!"

    def get_form_kwargs(self):
        kwargs = super(TeacherUpdateView, self).get_form_kwargs()
        kwargs.update({
            'user' : self.request.user,
            'is_update': True
        })
        return kwargs

    def get_success_url(self):        
        return reverse('inspectors:teachers_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context["classes"] = SchoolClass.objects.filter(
            coordination__unity__client__in=self.request.user.get_clients_cache(),
            school_year=timezone.now().year
        ).distinct().order_by('name')
        
        context["grades"] = Grade.objects.all()
        
        return context


class TeacherDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = Inspector
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'inspectors.delete_teacher'
    success_message = "Professor removido com sucesso!"


    def form_valid(self, form):
        CoordinationMember = apps.get_model("clients", "CoordinationMember")

        try:
            coordination_member = CoordinationMember.objects.filter(
                user__email=self.object.email,
            ).first()

            if coordination_member:
                CACHE_KEY = f'USER_TYPE_{self.object.user.pk}'
                
                cache.set(CACHE_KEY, settings.COORDINATION) 

                current_datetime = datetime.now().strftime('%Y%m%d%H%M%S') 
                inspector_groups = self.object.user.custom_groups.filter(segment=settings.TEACHER)
                
                self.object.user.custom_groups.remove(*inspector_groups)
                self.object.email = f'teacher_deleted_{self.object.pk}_{current_datetime}@gmail.com'
                self.object.user = None
                self.object.save()
            else:
                self.object.delete()
            
            get_and_create_notifications(view=self, trigger=Notification.AFTER_DELETE)
            
            messages.success(self.request, self.success_message)
            
        except ProtectedError:
            messages.error(self.request, "Ocorreu um erro ao remover, o professor tem disciplinas ou coordenações adicionadas.")
            
        return HttpResponseRedirect(self.get_success_url())  

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', None)


class TeacherApiList(LoginRequiredMixin, CheckHasPermission, ListAPIView):
    queryset = TeacherSubject.objects.filter(
        Q(
            teacher__inspector_type=Inspector.TEACHER,
            teacher__user__is_active=True
        ),
        Q(
            Q(active=True) |
            Q(
                school_year=timezone.now().year
            )
        )
    )
    required_permissions = [settings.COORDINATION, ]
    serializer_class = TeacherSubjectVerySimpleSerializer
    filterset_fields = ['subject', 'teacher__can_elaborate_questions', 'teacher__is_inspector_ia']

    def get_queryset(self):
        queryset = super(TeacherApiList, self).get_queryset()
        queryset = queryset.filter(
            Q(
				teacher__coordinations__in=self.request.user.get_coordinations_cache(),
                teacher__user__is_active=True

			)
        ).distinct('teacher', 'subject')

        is_inspector_ia = self.request.query_params.get('teacher__is_inspector_ia')
        if is_inspector_ia is not None and is_inspector_ia.lower() == 'true':
            queryset = queryset.filter(
            teacher__is_inspector_ia=True
        ).distinct()

        return queryset

class TeacherResetPasswordUpdateView(LoginRequiredMixin, CheckHasPermission, UpdateView):
    model = Inspector
    fields = ['user']
    required_permissions = [settings.COORDINATION]

        
    def dispatch(self, request, *args, **kwargs):
        self.object = super(TeacherResetPasswordUpdateView, self).get_object()
        self.object.user.set_password(self.object.user.email)
        self.object.user.must_change_password = True
        self.object.user.save()

        messages.success(request, f'Senha do professor "{self.object.name}" foi resetada com sucesso!')

        return HttpResponseRedirect(request.META.get("HTTP_REFERER"))


class ImportTeacher(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'dashboard/teachers/import_teachers.html'
    permission_required = 'inspectors.can_import_teacher'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)     
        user = self.request.user

        if Unity.objects.filter(unity_type=Unity.PARENT, coordinations__in=user.get_coordinations()).exists():
            context["coordinations"] = SchoolCoordination.objects.filter(
                unity__client__in=user.get_clients_cache()
            ).distinct()
        else:
            context["coordinations"] = user.get_coordinations().distinct()
        
        context["classes"] = SchoolClass.objects.filter(coordination__in=user.get_coordinations(), school_year=timezone.now().year)
        
        context["subjects"] = user.get_availables_subjects()
        
        return context


class TeacherExportCSV(LoginRequiredMixin, CheckHasPermission, ListView):
    required_permissions = [settings.COORDINATION]
    model = Inspector
    permission_required = ['inspectors.can_export_teacher']

    def get_queryset(self, **kwargs):
        queryset = Inspector.objects.filter(
            Q(
                inspector_type=Inspector.TEACHER,
				coordinations__unity__client__in=self.request.user.get_clients_cache()
			)
        ).distinct()
        
        if self.request.GET.get("q_name", ""):
            queryset = queryset.filter(
                Q(
                    Q(name__icontains=self.request.GET.get("q_name", "")) |
                    Q(email__icontains=self.request.GET.get("q_name", ""))
                )
            )
        
        if self.request.GET.get('q_subject', ""):
            queryset = queryset.filter(
                subjects__name__icontains=self.request.GET.get('q_subject', "")
            )

        if self.request.GET.getlist('q_levels', ""):
            queryset = queryset.filter(
                subjects__knowledge_area__grades__pk__in=self.request.GET.getlist('q_levels', "")
            )

        queryset = queryset.filter(
            user__is_active=True
        )

        return queryset.order_by("-created_at")
        
    
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        response = self._generate_csv(queryset)
        
        return response
    
    def _generate_csv(self, queryset):
        buffer = io.StringIO()  
        wr = csv.writer(buffer, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        
        csv_header = ['Nome', 'Email', 'Disciplinas', 'Grupo de Acesso', 'Coordenações', 'Turmas']  
        wr.writerow(csv_header)
        
        data_teachers = self._generate_teacher_export_data(queryset)
        wr.writerows(data_teachers)
        
        buffer.seek(0)
        sheet = pyexcel.load_from_memory("csv", buffer.getvalue())
        
        response = HttpResponse(sheet.csv, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="exportação.csv"' 
        
        return response
        
    def _generate_teacher_export_data(self, queryset):
        export_data = []

        for teacher in queryset:
            teacher_subject = ' | '.join([subject.name for subject in teacher.subjects.all()])
            
            teacher_coordinations = ' | '.join(teacher.user.get_coordinations().values_list('name', flat=True))

            teacher_access_group = ' | '.join(group.name for group in teacher.user.custom_groups.all())
            
            school_class_list = list(teacher.teachersubject_set.filter(
                active=True,
                school_year=timezone.localtime(timezone.now()).date().year
            ).values_list('classes__name', flat=True).distinct())
            teacher_school_classes = ''
            
            if school_class_list:
                teacher_school_classes = ' | '.join([nome for nome in school_class_list if nome is not None])                
                
            
            teacher_data = [
                teacher.name,
                teacher.email,
                teacher_subject,
                teacher_access_group,
                teacher_coordinations,
                teacher_school_classes
            ]

            export_data.append(teacher_data)

        return export_data



class TeacherExperienceChange(UpdateAPIView):
    serializer_class = TeacherSerializerChangeExperience

    def get_object(self):
        pk = self.kwargs.get('pk')
        return Inspector.objects.get(user_id=pk)

    def post(self, request, *args, **kwargs):
        inspector = self.get_object()
        inspector.has_new_teacher_experience = not inspector.has_new_teacher_experience
        inspector.save()
        return Response(status=status.HTTP_200_OK)



class TeacherSimpleApiList(LoginRequiredMixin, CheckHasPermission, ListAPIView):
    queryset = Inspector.objects.all()
    required_permissions = [settings.COORDINATION, ]
    serializer_class = InspectorSimpleSerializer
    filterset_fields = ['teachersubject__subject', 'can_elaborate_questions', 'is_discipline_coordinator']

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(
            Q(
                inspector_type=Inspector.TEACHER,
                user__is_active=True,
                coordinations__in=self.request.user.get_coordinations_cache(),
            ),
            Q(
                Q(teachersubject__active=True, teachersubject__school_year=timezone.now().year)
            )
        )
        
        return queryset.distinct()
    
class TeacherUpdateQuestionsBankTutorialView(APIView, CheckHasPermission):
    required_permissions = [settings.TEACHER]

    def post(self, request):
        teacher = request.user  
        data = {'show_questions_bank_tutorial': request.data.get('show_tutorial')}
        print(data)
        
        try:
            inspector = Inspector.objects.get(user=teacher)
        except Inspector.DoesNotExist:
            return Response({"error": "Inspector not found for this teacher."}, status=status.HTTP_404_NOT_FOUND)

        inspector.show_questions_bank_tutorial = data['show_questions_bank_tutorial']
        inspector.save()

        return Response({"success": "Tutorial visibility updated."}, status=status.HTTP_200_OK)

teachers_list = TeacherList.as_view()
teachers_create = TeacherCreateView.as_view()
teachers_update = TeacherUpdateView.as_view()
teachers_delete = TeacherDeleteView.as_view()
teachers_list_api = TeacherApiList.as_view()
teacher_update_questions_bank_tutoria = TeacherUpdateQuestionsBankTutorialView.as_view()
teacher_simple_list_api = TeacherSimpleApiList.as_view()
teachers_password_reset = TeacherResetPasswordUpdateView.as_view()
teachers_export = TeacherExportCSV.as_view()
teachers_experience_change_api = TeacherExperienceChange.as_view()

