import csv
from datetime import timedelta

import io
import os
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from celery.result import AsyncResult
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from django.http.response import HttpResponseRedirect
from django.core.cache import cache

import pyexcel
from django.http import HttpResponse

from django.urls import reverse
from django.utils import timezone
from django.views.generic import ListView, TemplateView
from django.views.generic.detail import DetailView
from django.db.models import Q, Count, F, ExpressionWrapper, fields
from django.views.generic.edit import CreateView, FormView, UpdateView
from django.db.models import Count
from django.db.utils import IntegrityError
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework import generics
from django_filters import rest_framework as filters_restframework

from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import SchoolClass, Grade
from fiscallizeon.students.forms import ImportForm, ImportFormV2, StudentForm, UpdateEnrollmentsForm
from fiscallizeon.students.serializers.students import StudentSerializer
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.events.models import Event
from fiscallizeon.clients.models import Client, SchoolCoordination

from fiscallizeon.materials.models import StudyMaterial
from fiscallizeon.subjects.models import Subject
from fiscallizeon.accounts.models import User
from .mixins import StudensLimitMixin

class StudentsCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, StudensLimitMixin, CreateView):
    template_name = "dashboard/students/student_create_update.html"
    model = Student
    form_class = StudentForm
    required_permissions = ['coordination', ]
    permission_required = 'students.add_student'
    success_message = "Aluno adicionado com sucesso, o aluno pode acessar o painel usando seu o e-mail como usuário e a matrícula como senha"

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super().get_form_kwargs(*args, **kwargs)
        form_kwargs['user'] = self.request.user
        form_kwargs['is_update'] = False
        return form_kwargs

    def get_context_data(self, **kwargs):
        context = super(StudentsCreateView, self).get_context_data(**kwargs)
        context['classes'] = SchoolClass.objects.filter(coordination__in=self.request.user.get_coordinations_cache())
        context["p_classe"] = self.request.POST.getlist('classe', '')
        return context

    def form_valid(self, form: StudentForm):
        form.instance.client = self.request.user.get_clients()[0]    
        self.created = form.save()
        
        if self.request.POST.get('classe'):
            for pk in self.request.POST.getlist('classe'):
                classe = SchoolClass.objects.get(coordination__in=self.request.user.get_coordinations_cache(), pk=pk)
                classe.students.add(form.instance.pk)
                classe.save()
                
                for application in classe.applications.all():
                    if not application.is_time_finished and application.student_can_be_remove_or_add:
                        application.students.add(form.instance.pk)

        if form.cleaned_data['password']:
            
            if form.cleaned_data['must_change_password']:
                form.instance.user.must_change_password = form.cleaned_data['must_change_password'] 
            
            if form.cleaned_data['username'] and form.cleaned_data['username'] != form.instance.user.username:
                form.instance.user.username = form.cleaned_data['username']
            
            form.instance.user.set_password(form.cleaned_data['password'])
            form.instance.user.save()

        self.redirect = True if form.cleaned_data['redirect'] else False
        
        form.instance.user.custom_groups.set(form.cleaned_data['custom_groups'])

        return super().form_valid(form)

    def get_success_url(self):
        if self.redirect:
            return reverse('students:students_list')
        else:
            return f'{reverse("students:students_update", kwargs={ "pk": self.created.id })}'


class StudentApiList(LoginRequiredMixin, CheckHasPermission, generics.ListCreateAPIView):
    queryset = Student.objects.all()
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    serializer_class = StudentSerializer
    filter_backends = [SearchFilter, filters_restframework.DjangoFilterBackend]
    search_fields = ['name', 'enrollment_number']
    filterset_fields = { 'id': ['in', 'exact'] }
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        without_classes = self.request.GET.get('without_classes', False)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={ 'without_classes': without_classes })
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True, context={ 'without_classes': without_classes })
        return Response(serializer.data)

    def get_queryset(self):
        user = self.request.user
        queryset = Student.objects.filter(
            client__in=self.request.user.get_clients_cache(),
            user__is_active=True
        ).order_by('name')
        
        if self.request.GET.get('classe'):
            queryset = queryset.filter(classes=self.request.GET.get('classe'))
        
        if self.request.GET.get("pk"):
            queryset = queryset.filter(pk__in=self.request.GET.getlist("pk"))
        
        if user.user_type == settings.TEACHER:
            queryset = queryset.filter(
                classes__teachersubject__active=True,
                classes__teachersubject__teacher=user.inspector, 
                classes__school_year=timezone.now().year
            )
        
        return queryset.distinct().order_by('name')

class StudentListView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'dashboard/students/student_list_new.html'
    required_permissions = ['coordination', ]
    permission_required = 'students.view_student'
    model = Student
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super(StudentListView, self).get_context_data(**kwargs)
        
        context['q_pk'] = self.request.GET.get('q_pk', '')
        context['q_name'] = self.request.GET.get('q_name', "")
        context['q_enrollment'] = self.request.GET.get('q_enrollment', "")
        context['q_classes'] = self.request.GET.getlist('q_classes', "")
        context['q_duplicated'] = self.request.GET.get('q_duplicated', '')
        context['q_without_classes'] = self.request.GET.get('q_without_classes', '')
        context['q_deactivated'] = self.request.GET.get('q_deactivated', '')
        context['q_activated_and_deactivated'] = self.request.GET.get('q_activated_and_deactivated', '')
        context['q_more_classes'] = self.request.GET.get('q_more_classes', '')
        context['q_is_atypical'] = self.request.GET.get('q_is_atypical', '')

        list_filters = [context['q_name'], context['q_enrollment'], context["q_classes"], context['q_duplicated'], context['q_without_classes'], context['q_deactivated'], context['q_activated_and_deactivated'], context['q_more_classes'], context['q_is_atypical']]

        context['count_filters'] = len(list_filters) - list_filters.count("")

        context['classes'] = SchoolClass.objects.filter(
            school_year=timezone.now().year,
            coordination__in=self.request.user.get_coordinations_cache()
        ).distinct().values('pk', 'name', 'coordination__unity__name').order_by('name')

        context['params'] = self.request.META['QUERY_STRING']
        
        return context

    def get_queryset(self, **kwargs):

        queryset = Student.objects.filter(
            Q(client__in=self.request.user.get_clients_cache()),
            Q(
                Q(classes__coordination__in=self.request.user.get_coordinations_cache()) |
                Q(classes__isnull=True)
            )
        ).distinct()

        if self.request.GET.get('q_pk', ''):
            queryset = queryset.filter(pk=self.request.GET.get('q_pk', ''))

        if self.request.GET.get('q_name'):
            queryset = queryset.filter(
                Q(
                    Q(name__icontains=self.request.GET.get('q_name')) |
                    Q(email__icontains=self.request.GET.get('q_name'))
                )
            )
        
        if self.request.GET.get('q_enrollment'):
            queryset = queryset.filter(
                enrollment_number__icontains=self.request.GET.get('q_enrollment')
            )

        if self.request.GET.get('q_classes'):
            queryset = queryset.filter(
                classes__pk__in=self.request.GET.getlist('q_classes', "")
            )
        
        
        if self.request.GET.get('q_without_classes'):
            queryset = queryset.filter(
                classes__isnull=True
            )

        if self.request.GET.get('q_deactivated'):
            queryset = queryset.filter(
                user__is_active=False
            )
            
        if self.request.GET.get('q_duplicated'):
            repeated_students = (
                Student.objects.values('enrollment_number')
                .filter(id__in=queryset)
                .annotate(repated_count=Count('enrollment_number'))
                .filter(repated_count__gt=1)
            )
            queryset = queryset.filter(enrollment_number__in=repeated_students.values('enrollment_number')).order_by('enrollment_number')
            
        if not self.request.GET.get('q_deactivated') and not self.request.GET.get('q_activated_and_deactivated'):
            queryset = queryset.filter(
                Q(
                    Q(user__is_active=True) |
                    Q(user__isnull=True)
                )
            )
            
        if self.request.GET.get('q_activated_and_deactivated'):
            queryset = queryset.filter(
                Q(user__is_active=True) | Q(user__is_active=False)
            )

        # aluno possui mais de uma enturmação no ano vigente.
        if self.request.GET.get('q_more_classes'):
            queryset = queryset.annotate(
                num_classes=Count("classes",filter=Q(classes__school_year=timezone.now().year))
            ).filter(num_classes__gt=1) 
        if self.request.GET.get('q_is_atypical', ''):
            queryset = queryset.filter(is_atypical=True)
            
            

        return queryset

class StudentImport(LoginRequiredMixin, CheckHasPermission, StudensLimitMixin, FormView):
    template_name = 'dashboard/students/import_students.html'
    permission_required = 'students.can_import_student'
    form_class = ImportForm

    def get_success_url(self):
        return reverse('students:students_import')

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super(StudentImport, self).get_form_kwargs(*args, **kwargs)
        form_kwargs['user'] = self.request.user
        return form_kwargs

    def form_valid(self, form):
        coordination = form.cleaned_data.get('coordination')
        grade = form.cleaned_data.get('grade')
        students_field = form.cleaned_data.get('students_file')
        # class_name = form.cleaned_data.get('class_name')
        replace_old_classes = form.cleaned_data.get('replace_old_classes')
        
        students_field.seek(0)
        reader = csv.DictReader(io.StringIO(students_field.read().decode('utf-8')))

        for student in reader:
            try:
                student_db = Student.objects.using('default').filter(
                    enrollment_number=student['matricula'].strip(),
                    client=coordination.unity.client
                ).first()
                
                username = f'{coordination.unity.client.code}-{student["usuario"].strip()}' if coordination.unity.client.code else student["usuario"].strip()

                count_usernames = User.objects.using('default').filter(username=username).count()
                if count_usernames:
                    username = str(count_usernames + 1) + "-" + (username) 

                if not student_db:
                    student_db = Student(
                        client=coordination.unity.client,
                        name=student['nome'].strip(),
                        email=student['email'].strip(),
                        enrollment_number=student['matricula'].strip(),
                        responsible_email=student.get('email_responsavel', ''),
                        responsible_email_two=student.get('email_responsavel_2', ''),
                    )

                    student_db.create_user(
                        username=username,
                        password=student['senha'].strip()
                    )
                else:
                    # if student["usuario"].strip() and not student_db.user:
                    #     student_db.user.username = username
                        
                    if student['senha'].strip():
                        student_db.user.set_password(student['senha'].strip())
                        
                    if email_responsavel := student.get('email_responsavel', ''):
                        student_db.responsible_email = email_responsavel
                        student_db.save(skip_hooks=True)
                        
                    if email_responsavel := student.get('email_responsavel_2', ''):
                        student_db.responsible_email_two = email_responsavel
                        student_db.save(skip_hooks=True)
                    
                    student_db.user.save()
                    
                student_db.save(skip_hooks=True)

            except IntegrityError as e:
                print(e)
                continue

            if replace_old_classes:
                old_classes = SchoolClass.objects.filter(
                    students__in=[student_db],
                    school_year=timezone.now().year
                )

                for old_class in old_classes:
                    old_class.students.remove(student_db)
                    old_class.save()

            csv_classes = student['turmas'].split(',')

            for csv_class in csv_classes:
                client_class, _ = SchoolClass.objects.update_or_create(
                    coordination=coordination,
                    name=csv_class.upper().strip(),
                    grade=grade,
                    school_year=timezone.now().year,
                )

                if student_db in client_class.students.all():
                    continue
                
                client_class.students.add(student_db)

        messages.info(self.request, 'Alunos importados com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        print(form.errors)
        return super().form_invalid(form)
    
class StudentImportV2(LoginRequiredMixin, CheckHasPermission, StudensLimitMixin, FormView):
    template_name = 'dashboard/students/import_students_v2.html'
    permission_required = 'students.can_import_student'
    form_class = ImportFormV2

    def get_success_url(self):
        return reverse('students:students_import_v2')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['coordinations'] = SchoolCoordination.objects.filter(
            pk__in=self.request.user.get_coordinations_cache()
        )  

        client = self.request.user.client

        context['client_max_students'] = client.max_students_quantity
        context['client_students_count'] = Student.objects.filter(client=client, user__is_active=True).count()
        try:
            result = AsyncResult(f'IMPORT_STUDENTS_{str(self.request.user.id)}')
            if result.ready():
                context['last_import_task_status'] = result.status
                context['last_import_task_details'] = result.result
        except Exception as e:
            print("Erro", e)
        
        return context

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super(StudentImportV2, self).get_form_kwargs(*args, **kwargs)
        form_kwargs['user'] = self.request.user
        return form_kwargs

    def form_valid(self, form):
        from fiscallizeon.students.tasks.students_import import import_students_task
        students_field = form.cleaned_data.get('students_file')
        replace_old_classes = form.cleaned_data.get('replace_old_classes')

        os.makedirs('tmp/csv_import', exist_ok=True)

        tmp_file = os.path.join('tmp/csv_import', students_field.name)
        FileSystemStorage(location="tmp/csv_import").save(students_field.name, students_field)

        fs = PrivateMediaStorage()
        saved_file = fs.save(
            f'temp/{students_field.name}',
            open(tmp_file, 'rb')
        )
        os.remove(tmp_file)
        csv_url = fs.url(saved_file)
            
        task_id = f'IMPORT_STUDENTS_{str(self.request.user.id)}'
        import_students_task.apply_async(task_id=task_id,
            kwargs={
                'user_id': self.request.user.id,
                'csv_file_url': csv_url,
                'replace_old_classes': replace_old_classes
            }
        ).forget()

        return super().form_valid(form)

    def form_invalid(self, form):
        print(form.errors)
        return super().form_invalid(form)


class StudentUpdateEnrollment(LoginRequiredMixin, CheckHasPermission, FormView):
    template_name = 'dashboard/students/update_students_enrollments.html'
    form_class = UpdateEnrollmentsForm

    def get_success_url(self):
        return reverse('students:students_update_enrollments')

    def form_valid(self, form):
        students_field = form.cleaned_data.get('students_file')
        
        students_field.seek(0)
        reader = csv.DictReader(io.StringIO(students_field.read().decode('utf-8')))

        for student in reader:
            try:
                student_db = Student.objects.filter(
                    enrollment_number=student['matricula_antiga'].strip(),
                    client__in=self.request.user.get_clients_cache()
                ).first()

                if not student_db:
                    continue

                student_db.enrollment_number = student['matricula_nova'].strip()
                student_db.save()

            except Exception as e:
                print("Aluno não encontrado, matricula antiga: {}".format(student['matricula_antiga']))
                continue

        print('### FIM DA ATUALIZAÇÃO')
        messages.info(self.request, 'Alunos atualizados com sucesso!')
        return super().form_valid(form)

    def form_invalid(self, form):
        print(form.errors)
        return super().form_invalid(form)


class StudentDetailView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/students/student_detail.html'
    model = Student
    required_permissions = ['coordination', ]

    def get_context_data(self, **kwargs):
        context = super(StudentDetailView, self).get_context_data(**kwargs)
        
        duration = ExpressionWrapper(F('end_time') - F('start_time'), output_field=fields.DurationField())

        applications = ApplicationStudent.objects.filter(
            student=self.object,
        ).annotate(
            duration=duration 
        ).order_by('-application__date').distinct()

        orderby = self.request.GET.get('orderby', '')

        if orderby:
            applications = applications.order_by(orderby)

        context['orderby'] = orderby
        context["applications"] = applications

        return context

class StudentsUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    template_name = 'dashboard/students/student_create_update.html'
    model = Student
    form_class = StudentForm
    required_permissions = ['coordination', ]
    permission_required = 'students.change_student'
    success_message = "Aluno atualizado com sucesso!"
    
    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super().get_form_kwargs(*args, **kwargs)
        form_kwargs['user'] = self.request.user
        form_kwargs['is_update'] = True
        return form_kwargs
        
    def get_object(self, queryset=None):
        return Student.objects.using('default').get(pk=self.kwargs['pk'])
    
    def get_context_data(self, **kwargs):
        context = super(StudentsUpdateView, self).get_context_data(**kwargs)
        classes = SchoolClass.objects.filter(
            coordination__unity__client__in=self.request.user.get_clients_cache()
        ).values('pk', 'name', 'coordination__unity__name', 'school_year')
        p_classe = []
        
        # Se o usuário já tiver selecionado alguma classe
        if self.request.POST.get('classe'):
            for classe in self.request.POST.getlist('classe'):
                p_classe.append(classe)
        else:
            # Se for a primeira vez que o usuário entra na página de update
            p_classes = SchoolClass.objects.filter(students__pk=self.get_object().pk)
            for classe in p_classes:
                p_classe.append(classe.pk)
            
        context['classes'] = classes
        context['p_classe'] = p_classe
        context['is_update'] = 'true'

        return context
    
    def form_valid(self, form: StudentForm):  
        
        if form.cleaned_data['must_change_password']:
            form.instance.user.must_change_password = form.cleaned_data['must_change_password'] 
        
        if form.cleaned_data['username'] and form.cleaned_data['username'] != form.instance.user.username:
            form.instance.user.username = form.cleaned_data['username']
        
        if form.cleaned_data['password']:
            form.instance.user.set_password(form.cleaned_data['password'])

        if form.cleaned_data['email']:
            if form.instance.user.email == form.instance.user.username:
                form.instance.user.username = form.cleaned_data['email']
            form.instance.user.email = form.cleaned_data['email']
            
        if self.request.POST.get('classe'):
            student = Student.objects.get(pk=form.instance.pk)

            for pk in self.request.POST.getlist('classe'):
                classe = SchoolClass.objects.get(pk=pk)
                Student.objects.filter()

                for application in classe.applications.all():
                    if student not in application.students.all() and not application.is_time_finished and application.student_can_be_remove_or_add:
                        application.students.add(student)
        
        form.instance.user.save()
        form.instance.user.custom_groups.set(form.cleaned_data['custom_groups'])

        self.redirect = True if form.cleaned_data['redirect'] else False
        
        return super().form_valid(form)

    def post(self, request, **kwargs):

        schoolclass = SchoolClass.objects.filter(coordination__in=self.request.user.get_coordinations_cache(), students__pk=self.get_object().pk)

        classe_in_form = self.request.POST.getlist('classe', '')

        new_school_class = schoolclass.exclude( Q(pk__in=classe_in_form) if classe_in_form else Q())
        for classe in new_school_class:
            for application in classe.applications.all():
                if application.student_can_be_remove_or_add:
                    application.students.remove(self.get_object().pk)
            classe.students.remove(self.get_object().pk)

        for pk in self.request.POST.getlist('classe', ''):
            classe = SchoolClass.objects.get(pk=pk)
            classe.students.add(self.get_object().pk)
            classe.save()

        return super().post(request, **kwargs)

    def get_success_url(self):
        # return f'{reverse("students:students_list")}?{self.request.META.get("QUERY_STRING", None)}'
        if self.redirect:
            return reverse('students:students_list')
        else:
            return f'{reverse("students:students_update", kwargs={ "pk": self.get_object().id })}'



class StudentsResetPasswordUpdateView(LoginRequiredMixin, CheckHasPermission, UpdateView):
    template_name = 'dashboard/students/student_create_update.html'
    model = Student
    fields = ['user']
    required_permissions = ['coordination', ]

        
    def dispatch(self, request, *args, **kwargs):
        self.object = super().get_object()
        if not self.object.user:
            self.object.user = User.objects.filter(email=self.object.email).first()
            self.object.save(skip_hooks=True)
            
        self.object.user.set_password(self.object.email)
        self.object.user.save()

        messages.success(request, f'Senha do aluno "{self.object.name}" foi resetada com sucesso!')

        return HttpResponseRedirect(request.META.get("HTTP_REFERER"))

class StudyMaterialStudentListView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'dashboard/students/study_material.html'
    required_permissions = [settings.STUDENT]
    model = StudyMaterial
    paginate_by = 24

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_study_material:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(StudyMaterialStudentListView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(StudyMaterialStudentListView, self).get_context_data(**kwargs)

        CACHE_KEY = f'study-material-context-{str(self.request.user.pk)}'

        if self.request.GET.get('menu'):
            context['menu'] = self.request.GET.get('menu')
        else:
            context['menu'] = 'all'

        CACHE_KEY += f'-{context["menu"]}'

        if self.request.GET.get('doc_type'):
            context['doc_type'] = self.request.GET.get('doc_type')
        else:
            context['doc_type'] = 'all'
        
        CACHE_KEY += f'-{context["doc_type"]}'

        if self.request.GET.get('subject'):
            context['subject'] = self.request.GET.get('subject')
            CACHE_KEY += f'-{context["subject"]}'

        if self.request.GET.get('stage'):
            context['stage'] = self.request.GET.get('stage')
            CACHE_KEY += f'-{context["stage"]}'

        if not cache.get(CACHE_KEY):
            materials = list(StudyMaterial.objects.filter(
                Q(
                    Q(client__in=self.request.user.get_clients_cache()),
                    Q(
                        Q(exam__isnull=False, exam__application__students=self.request.user.student) |
                        Q(
                            school_classes__isnull=False, school_classes__students=self.request.user.student, 
                            school_classes__school_year=timezone.now().year
                        )
                    ),
                    Q(
                        Q(release_material_study__lte=timezone.now()) |
                        Q(release_material_study__isnull=True)
                    )
                )
            ).distinct())

            subjects = Subject.objects.filter(
                Q(
                    Q(studymaterial__in=materials) |
                    Q(teachersubject__exam__materials__in=materials)
                )
            ).annotate(
                count_materials=Count('studymaterial', filter=Q(
                    Q(studymaterial__subjects__pk=F('pk')) |
                    Q(studymaterial__exam__teacher_subjects__subject=F('pk'))
                ), distinct=True)
            ).distinct()

            cache.set(CACHE_KEY, list(subjects), 6*60*60)

        context["subjects"] = cache.get(CACHE_KEY)

        return context

    def get_queryset(self, **kwargs):

        CACHE_KEY = f'study-material-queryset-{str(self.request.user.pk)}'

        if self.request.GET.get('subject'):
            CACHE_KEY += f'-{self.request.GET.get("subject")}'

        if self.request.GET.get('stage'):
            CACHE_KEY += f'-{self.request.GET.get("stage")}'
                
        if self.request.GET.get('menu'):
            CACHE_KEY += f'-{self.request.GET.get("menu")}'
                
        if self.request.GET.get('doc_type') and self.request.GET.get('doc_type') != 'all':
            CACHE_KEY += f'-{self.request.GET.get("doc_type")}'


        if not cache.get(CACHE_KEY):
            print("NÃO TEM CACHE")
            queryset = StudyMaterial.objects.filter(
                Q(
                    Q(client__in=self.request.user.get_clients_cache()),
                    Q(
                        Q(exam__isnull=False, exam__application__students=self.request.user.student) |
                        Q(
                            school_classes__isnull=False, 
                            school_classes__students=self.request.user.student, school_classes__school_year=timezone.now().year
                        )
                    ),
                    Q(
                        Q(release_material_study__lte=timezone.now()) |
                        Q(release_material_study__isnull=True)
                    )
                )
            ).distinct()
            
            if self.request.GET.get('subject'):
                queryset = queryset.filter(
                    Q(
                        Q(subjects=self.request.GET.get('subject')) |
                        Q(exam__teacher_subjects__subject=self.request.GET.get('subject'))
                    )
                )

            if self.request.GET.get('stage'):
                queryset = queryset.filter(stage=self.request.GET.get('stage'))

                
            if self.request.GET.get('menu'):
                if self.request.GET.get('menu') == 'all':
                    queryset = queryset
                else:
                    if self.request.GET.get('menu') == 'recents':
                        queryset = queryset.filter(created_at__range=[timezone.now()  - timedelta(days=7),  timezone.now()]).order_by('-created_at')
                    
                    if self.request.GET.get('menu') == 'emphasis':
                        queryset = queryset.filter(
                            Q(emphasis=True),
                        )
                
            cache.set(CACHE_KEY, list(queryset.order_by('-created_at')), 6*60*60)
                    
            if self.request.GET.get('doc_type') and self.request.GET.get('doc_type') != 'all':
                docs = []
                for doc in queryset:
                    if self.request.GET.get('doc_type') == 'doc':
                        if doc.get_extension() in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv']:
                                docs.append(doc)
                    
                    elif self.request.GET.get('doc_type') == 'image':
                        if doc.get_extension() in ['.jpg', '.png', '.jpeg', '.gif']:
                            docs.append(doc)

                    elif self.request.GET.get('doc_type') == 'presentation':
                        if doc.get_extension() in ['.ppt', '.pptx', '.pps', '.ppsx']:
                            docs.append(doc)

                    elif self.request.GET.get('doc_type') == 'video':
                        if doc.get_extension() in ['.mp4', '.mov', '.avi', '.wmv', '.flv']:
                            docs.append(doc)
                    
                    elif self.request.GET.get('doc_type') == 'audio':
                        if doc.get_extension() in ['.mp3', '.wav', '.aac', '.ogg']:
                            docs.append(doc)

                    elif self.request.GET.get('doc_type') == 'zip':
                        if doc.get_extension() in ['.zip', '.rar', '.7z']:
                            docs.append(doc)
                
                cache.set(CACHE_KEY, docs, 6*60*60)


        return cache.get(CACHE_KEY)
    
class SISUSimulatorTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'dashboard/students/sisu_simulator.html'
    required_permissions = [settings.STUDENT]    
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        
        if user.is_authenticated and (not user.student.last_class_is_high_school or not user.client_has_sisu_simulator):
            messages.error(request, 'Você não tem permissão para acessar a página')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        
        return super().dispatch(request, *args, **kwargs)


class StudentsExportCSV(LoginRequiredMixin, CheckHasPermission, ListView):
    required_permissions = [settings.COORDINATION]
    model = Student
    permission_required = ['students.can_export_student']
    
    def get_queryset(self, **kwargs):
        queryset = Student.objects.filter(
            Q(
				client__in=self.request.user.get_clients_cache()
			)
        ).distinct()
        if self.request.GET.get('q_name'):
            queryset = queryset.filter(
                Q(
                    Q(name__icontains=self.request.GET.get('q_name')) |
                    Q(email__icontains=self.request.GET.get('q_name'))
                )
            )
        
        if self.request.GET.get('q_classes'):
            queryset = queryset.filter(
                classes__pk__in=self.request.GET.getlist('q_classes', "")
            )
        
        if self.request.GET.get('q_enrollment'):
            queryset = queryset.filter(
                enrollment_number__icontains=self.request.GET.get('q_enrollment')
            )
        
        if self.request.GET.get('q_without_classes'):
            queryset = queryset.filter(
                classes__isnull=True
            )

        if self.request.GET.get('q_deactivated'):
            queryset = queryset.filter(
                user__is_active=False
            )

        if self.request.GET.get('q_duplicated'):
            repeated_students = (
                Student.objects.values('enrollment_number')
                .filter(id__in=queryset)
                .annotate(repated_count=Count('enrollment_number'))
                .filter(repated_count__gt=1)
            )
            queryset = queryset.filter(enrollment_number__in=repeated_students.values('enrollment_number')).order_by('enrollment_number')
            
        if not self.request.GET.get('q_deactivated') and not self.request.GET.get('q_activated_and_deactivated'):
            queryset = queryset.filter(
                Q(
                    Q(user__is_active=True) |
                    Q(user__isnull=True)
                )
            )
        
        if self.request.GET.get('q_activated_and_deactivated'):
            queryset = queryset.filter(
                Q(user__is_active=True) | Q(user__is_active=False)
            )
        
        return queryset
    
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        response = self._generate_csv(queryset)
        
        return response
    
    def _generate_csv(self, queryset):
        buffer = io.StringIO()  
        wr = csv.writer(buffer, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        
        csv_header = ['Aluno', 'Matrícula','Email', 'Turma', 'Ativo']  
        wr.writerow(csv_header)
        
        data_students = self._generate_students_export_data(queryset)
        wr.writerows(data_students)
        
        buffer.seek(0)
        sheet = pyexcel.load_from_memory("csv", buffer.getvalue())
        
        response = HttpResponse(sheet.csv, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="exportação.csv"' 
        
        return response
        
    def _generate_students_export_data(self, queryset):
        export_data = []

        for student in queryset:
            student_is_active = "Não"
            if student.user.is_active:
                student_is_active = "Sim"
            
            student_data = [
                student.name,
                student.enrollment_number,
                student.email,
                student.get_last_class(),
                student_is_active
            ]

            export_data.append(student_data)

        return export_data

    
students_list_api = StudentApiList.as_view()
students_create = StudentsCreateView.as_view()
students_detail = StudentDetailView.as_view()
students_update = StudentsUpdateView.as_view()
students_reset = StudentsResetPasswordUpdateView.as_view()
students_list = StudentListView.as_view()
students_import = StudentImport.as_view()
students_import_v2 = StudentImportV2.as_view()
students_update_enrollments = StudentUpdateEnrollment.as_view()
study_material_students_list = StudyMaterialStudentListView.as_view()
students_export = StudentsExportCSV.as_view()
