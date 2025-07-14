from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models.aggregates import Count
from django.db.models.expressions import F, Subquery
from django.http.response import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.utils import timezone

from fiscallizeon.applications.models import Application
from fiscallizeon.exams.models import ClientCustomPage
from fiscallizeon.classes.models import Grade
from fiscallizeon.clients.models import SchoolCoordination, Unity
from fiscallizeon.distribution.tasks.distribute_students import distribute_students
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.accounts.mixins import LoginOrTokenRequiredMixin
from fiscallizeon.exams.models import ExamHeader
from fiscallizeon.distribution.forms import RoomCreateForm, RoomDistributionForm
from fiscallizeon.distribution.models import Room, RoomDistribution, RoomDistributionStudent
from fiscallizeon.distribution.functions import distribute_students_coordination, distribute_students_grade, distribute_students_by_class


class RoomDistributionList(LoginRequiredMixin, CheckHasPermission, ListView):
    model = RoomDistribution
    paginate_by = 20
    template_name = "distribution/distribution_list.html"

    def get_queryset(self):
        queryset = super(RoomDistributionList, self).get_queryset()
        queryset = queryset.filter(
            application__exam__coordinations__unity__client__in=self.request.user.get_clients_cache()
        ).distinct().order_by('-application__date')

        if self.request.GET.get('q_data', ""):
            queryset = queryset.filter(
                application__date=self.request.GET.get('q_data', "")
            )
        if self.request.GET.get('q_prova', ""):
            queryset = queryset.filter(
                application__exam__name__icontains=self.request.GET.get('q_prova', "")
            )

        if self.request.GET.getlist('q_salas', ""):
            queryset = queryset.filter(
                room_distribution__room__in=self.request.GET.getlist('q_salas', "")
            )

        return queryset

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_distribution:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(RoomDistributionList, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['exam_headers'] = ExamHeader.objects.filter(
            user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache()
        ).distinct()

        context['exam_custom_pages'] = ClientCustomPage.objects.filter(
            client__in=self.request.user.get_clients_cache()
        ).distinct()

        context['q_prova'] = self.request.GET.get('q_prova', "")
        context['q_data'] = self.request.GET.get('q_data', "")
        context['q_salas'] = self.request.GET.getlist('q_salas', "")

        list_filters = context['q_prova'], context['q_data'], context["q_salas"]

        context['count_filters'] = len(list_filters) - list_filters.count("")

        context['salas'] = Room.objects.filter(
            coordination__unity__client__in=self.request.user.get_clients_cache()
        ).distinct()
       
        return context


class RoomDistributionCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = RoomDistribution
    required_permissions = ['coordination', ]
    form_class = RoomDistributionForm
    template_name = "distribution/distribution_create_update.html"
    success_message = "O ensalamento foi cadastrado com sucesso!"

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_distribution:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(RoomDistributionCreateView, self).dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super(RoomDistributionCreateView, self).get_context_data(**kwargs)
        
        if self.request.GET.get('application_id'):
            context['application'] = Application.objects.using('default').get(pk=self.request.GET.get('application_id'))

        context['grades'] = Grade.objects.all()
        context['unitys'] = Unity.objects.filter(
            coordinations__in=self.request.user.get_coordinations()
        ).distinct()
        
        context['school_coordinations'] = SchoolCoordination.objects.filter(
            unity__client__in=self.request.user.get_clients_cache()
        ).distinct()
        
        context['params'] = self.request.META['QUERY_STRING']
        context['q_date'] = self.request.GET.get('date')
        context['q_school_classes'] = self.request.GET.getlist('school_classes')
        context['q_school_coodinations'] = self.request.GET.getlist('coordinations')
        context['q_unitys'] = self.request.GET.getlist('unitys')
        context['q_grades'] = self.request.GET.getlist('grades')
        context['today'] = timezone.now()
        return context
    
    def get_success_url(self):
        return reverse('distribution:distribution_list')

    def form_valid(self, form):
        form_return = super(RoomDistributionCreateView, self).form_valid(form)
        
        selected_rooms = form.cleaned_data['rooms']
        applications = form.cleaned_data['applications']
        applications.update(room_distribution=self.object)

        self.object.status = RoomDistribution.DISTRIBUTING
        self.object.save()

        distribute_students.apply_async(
            task_id=f'DISTRIBUTE_STUDENTS_{self.object.pk}',
            args=(
                self.object.pk, 
                list(selected_rooms.values_list('pk', flat=True)), 
                list(applications.values_list('pk', flat=True)),
            ),
        )

        return form_return

class RoomDistributionUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = RoomDistribution
    required_permissions = ['coordination', ]
    form_class = RoomDistributionForm
    template_name = "distribution/distribution_create_update.html"
    success_message = "O ensalamento foi atualizado com sucesso!"

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_distribution:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        
        return super(RoomDistributionUpdateView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(RoomDistributionUpdateView, self).get_context_data(**kwargs)
        context['today'] = timezone.now()
        
        return context

    def get_success_url(self):
        return reverse('distribution:distribution_list')


class RoomDistributionDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = RoomDistribution
    required_permissions = ['coordination', ]
    success_message = "Sala removido com sucesso!"

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_distribution:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(RoomDistributionDeleteView, self).dispatch(request, *args, **kwargs)


    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', None)


################### ROOMS VIEWS #################
class RoomListView(LoginRequiredMixin, CheckHasPermission, ListView):
    model = Room
    paginate_by = 20
    permission_required = 'distribution.view_room'
    template_name = "distribution/rooms/room_list.html"


    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_distribution:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(RoomListView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(RoomListView, self).get_queryset()
        queryset = queryset.filter(coordination__unity__client__in=self.request.user.get_clients_cache())
        
        if self.request.GET.get('name'):
            queryset = queryset.filter(
                name__icontains=self.request.GET.get('name')
            )
            
        if self.request.GET.get('larger'):
            queryset = queryset.filter(
                capacity__gt=self.request.GET.get('larger')
            )
            
        if self.request.GET.get('smaller'):
            queryset = queryset.filter(
                capacity__lt=self.request.GET.get('smaller')
            )      
            
        if self.request.GET.get('q_coordination'):
            queryset = queryset.filter(
                coordination__in=self.request.GET.getlist('q_coordination')
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super(RoomListView, self).get_context_data(**kwargs)
        
        context['name'] = self.request.GET.get('name', "")
        context['larger'] = self.request.GET.get('larger', "")
        context['smaller'] = self.request.GET.get('smaller', "")
        context['q_coordination'] = self.request.GET.getlist('q_coordination', "")
        
        list_filters = [context['name'], context['smaller'], context['larger'], context['q_coordination']]
        context['count_filters'] = len(list_filters) - list_filters.count("")
        
        context['coordination'] = SchoolCoordination.objects.filter(
            unity__client__in=self.request.user.get_clients_cache()
        ).order_by('name').distinct()
        
        return context


class RoomCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = Room
    required_permissions = ['coordination', ]
    permission_required = 'distribution.add_room'
    form_class = RoomCreateForm
    template_name = "distribution/rooms/room_create_update.html"
    success_message = "Sala adicionada com sucesso!"

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_distribution:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        
        return super(RoomCreateView, self).dispatch(request, *args, **kwargs)


    def get_form_kwargs(self):
        kwargs = super(RoomCreateView, self).get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs
    
    def get_success_url(self):
        return reverse('distribution:room_list')


class RoomUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = Room
    required_permissions = ['coordination', ]
    permission_required = 'distribution.change_room'
    form_class = RoomCreateForm
    template_name = "distribution/rooms/room_create_update.html"
    success_message = "Sala atualizada com sucesso!"

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_distribution:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(RoomUpdateView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(RoomUpdateView, self).get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse('distribution:room_list')


class RoomDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = Room
    required_permissions = ['coordination', ]
    permission_required = 'distribution.delete_room'
    success_message = "Sala removida com sucesso!"

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_distribution:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        
        return super(RoomDeleteView, self).dispatch(request, *args, **kwargs)


    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', None)


################### STUDENTS AND ROOMS VIEWS #################
class RoomDistributionDetailtView(LoginRequiredMixin, CheckHasPermission, DetailView):
    model = RoomDistribution
    required_permissions = ['coordination', ]
    template_name = "distribution/rooms/room_distribution_detail.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_distribution:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(RoomDistributionDetailtView, self).dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super(RoomDistributionDetailtView, self).get_context_data(**kwargs)
        
        rooms_students = RoomDistributionStudent.objects.filter(distribution=self.get_object())
        
        if self.request.GET.get('school_coordination'):
            rooms_students = rooms_students.filter(distribution__application__exam__coordinations__in=self.request.GET.getlist('school_coordination'), room__coordination__in=self.request.GET.getlist('school_coordination'))
        
        if self.request.GET.get('unity'):
            rooms_students = rooms_students.filter(distribution__application__exam__coordinations__unity__in=self.request.GET.getlist('unity'), room__coordination__unity__in=self.request.GET.getlist('unity'))

        context['rooms'] = rooms_students.values('room').annotate(
            room_distribution_id=F('distribution__id'),
            id=F('room__id'),
            name=F('room__name'),
            students_count=Count('student', distinct=True),
            unity_name=F('room__coordination__unity__name')
        ).order_by('unity_name', 'room__name')

        context['aggragations'] = rooms_students.aggregate(
            applications_count=Count('distribution__application', distinct=True),
            rooms_count=Count('room', distinct=True),
            students_count=Count('student', distinct=True),
        )

        context['coordinations'] = SchoolCoordination.objects.filter(
            pk__in=self.get_object().application_set.all().values('exam__coordinations')
        )
        context['unitys'] = Unity.objects.filter(
            pk__in=self.get_object().application_set.all().values('exam__coordinations__unity')
        )

        context['q_school_coordinations'] = self.request.GET.getlist('school_coordination')
        context['q_unitys'] = self.request.GET.getlist('unity')
        context['exam_headers'] = ExamHeader.objects.filter(
            user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache()
        ).distinct()

        return context



# Listas de Presença e de Pátio
class RoomAttendanceListDetailView(LoginOrTokenRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = ['coordination', ]
    template_name = "distribution/lists/attendance_list.html"
    model = Room

    def get_room_applications(self):
        room_distribution = RoomDistribution(pk=self.kwargs['distribution'])
        students_ids = RoomDistributionStudent.objects.filter(
            room=self.object, 
            distribution=room_distribution
        ).values_list('student_id', flat=True)

        applications = room_distribution.get_applications()
        room_applications = applications.filter(
            students__in=students_ids
        ).select_related('exam').distinct()

        return room_applications
    
    def get_context_data(self, **kwargs):
        room_applications = self.get_room_applications()
        context = super(RoomAttendanceListDetailView, self).get_context_data(**kwargs)
        context['rooms_distributions_student'] = RoomDistributionStudent.objects.filter(room=self.get_object().pk, distribution=self.kwargs['distribution']).order_by('student__name') 
        context['distribution'] = RoomDistribution(pk=self.kwargs['distribution'])
        context['room_applications'] = room_applications
        context['room_exams_names'] = set(list(room_applications.values_list('exam__name', flat=True).distinct()))
        context['hide_dialog'] = bool(self.request.GET.get('hide_dialog', False))
        return context

class DistributionPatioListDetailView(DetailView):
    template_name = "distribution/lists/patio_list.html"
    model = RoomDistribution

    def get_context_data(self, **kwargs):
        context = super(DistributionPatioListDetailView, self).get_context_data(**kwargs)
        
        rooms = Room.objects.filter(room_distribution__distribution=self.get_object()).distinct().order_by('name')
        query_unities = Unity.objects.filter(pk__in=rooms.values_list('coordination__unity')).distinct()

        if unity_q := self.request.GET.getlist('unity'):
            query_unities = query_unities.filter(pk__in=unity_q)

        unities = []
        for unity in query_unities:
            object_unity = {
                "name": unity.name,
                "distributions": RoomDistributionStudent.objects.filter(distribution=self.get_object(), room__coordination__unity=unity).order_by('student__name'),
                "client_logo": unity.client.logo.url if unity.client.logo else None,
            }
            unities.append(object_unity)

        context['unities'] = unities
        context['hide_dialog'] = bool(self.request.GET.get('hide_dialog', False))
        context['two_columns'] = bool(self.request.GET.get('two_columns', False))
        return context