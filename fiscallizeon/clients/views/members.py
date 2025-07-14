import io
import csv
import pyexcel

from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.conf import settings
from django.core.cache import cache
from django.views.generic import ListView
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from fiscallizeon.core.utils import CheckHasPermission
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import TemplateView
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponse


from fiscallizeon.clients.models import CoordinationMember, ClientTeacherObligationConfiguration, ClientQuestionsConfiguration, ConfigNotification, QuestionTag, SchoolCoordination, Unity, Client
from fiscallizeon.clients.forms import ClientTagsForm, ClientTeacherObligationConfigurationForm, ClientQuestionsConfigurationForm, UserForm, ClientConfigNotificationsForm, ClientForm
from fiscallizeon.accounts.models import User


class MemberListView(LoginRequiredMixin, CheckHasPermission,  ListView):
    model = User
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'clients.view_coordinationmember'
    paginate_by = 20
    template_name = "dashboard/members/member_list_new.html"

    def get_context_data(self, **kwargs):
        context = super(MemberListView, self).get_context_data(**kwargs)

        context['q_name_email'] = self.request.GET.get('q_name_email', "")
        context['q_coordination'] = self.request.GET.getlist('q_coordination', "")
        context['q_deactivated'] = self.request.GET.getlist('q_deactivated', "")

        list_filters = [context['q_name_email'],  context["q_coordination"], context["q_deactivated"]]

        context['count_filters'] = len(list_filters) - list_filters.count("")

        context['members'] = CoordinationMember.objects.filter(
            coordination__unity__client__in=self.request.user.get_clients_cache(),
        ).distinct().order_by()

        context['coordinations'] = SchoolCoordination.objects.filter(
            pk__in=self.request.user.get_coordinations_cache(),
        ).distinct().order_by()

        return context

    def get_queryset(self):
        queryset = User.objects.filter(
            Q(
				coordination_member__coordination__in=self.request.user.get_coordinations_cache(),
			)
        ).exclude(id=self.request.user.id).distinct()

        if self.request.GET.get('q_name_email', ""):
            queryset = queryset.filter(
                Q(name__icontains=self.request.GET.get('q_name_email', "")) |
                Q(email__icontains=self.request.GET.get('q_name_email', ""))
            )
        if self.request.GET.get('q_coordination', ""):
            queryset = queryset.filter(
                coordination_member__coordination__in=self.request.GET.getlist('q_coordination', [])
            )
        
        deactivated_filter = self.request.GET.get('q_deactivated', "")
        if deactivated_filter:
            queryset = queryset.filter(
                is_active=False
            )

        if not deactivated_filter:
            queryset = queryset.filter(
                Q(is_active=True)
            )
        return queryset

from fiscallizeon.inspectors.models import Inspector
class MemberCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = User
    required_permissions = ['coordination', ]
    permission_required = 'clients.add_coordinationmember'
    form_class = UserForm
    context_object_name = 'object_member'
    template_name = "dashboard/members/member_create_update_new.html"
    success_message = "Membro cadastrado com sucesso!"

    def get_form_kwargs(self):
        kwargs = super(MemberCreateView, self).get_form_kwargs()
        kwargs.update({'user' : self.request.user, 'create': True})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(MemberCreateView, self).get_context_data(**kwargs)
        
        user = self.request.user
        coordinations = user.get_coordinations_cache()

        context['unities'] = Unity.objects.filter(
            coordinations__in=coordinations
        ).distinct().prefetch_related(
            'coordinations'
        )
        
        context['coordinations'] = (
            SchoolCoordination.objects.only('id', 'name').filter(
                id__in=coordinations
            ).distinct()
        )
        return context

    def form_valid(self, form):
        user = self.request.user
        email = form.cleaned_data.get('email')
        
        associate_professor_coordinator = Inspector.objects.filter(email=email).exists()
        groups_inspector = []
        if associate_professor_coordinator:  
            user_instance = form.instance 
            for custom_group in user_instance.custom_groups.all():
                groups_inspector.append(str(custom_group.pk))
        else:
            user_instance = form.save(commit=False)
            user_instance.username = email
            user_instance.is_active = True
            user_instance.set_password(email)
            user_instance.must_change_password = True
            user_instance.save()
                
        if form.is_valid():
            self.object = user_instance

            coordinations_pks = self.request.POST.get('coordinations').split(',')
            coordinations = SchoolCoordination.objects.filter(pk__in=coordinations_pks)
            
            existing_members = CoordinationMember.objects.filter(
                user=user_instance, coordination__in=coordinations
            ).values_list('coordination', flat=True)
            
            CoordinationMember.objects.bulk_create(
                [
                    CoordinationMember(
                        user=user_instance,
                        coordination=coordination,
                        is_coordinator=True,
                        is_reviewer=True,
                        is_pedagogic_reviewer=True
                    )
                    for coordination in coordinations
                    if coordination.id not in existing_members

                ]
            )

            if user.client.has_default_groups('coordination'):
                self.object.custom_groups.set(user.client.get_groups().filter(client__isnull=False, segment='coordination', default=True))
            else:
                self.object.custom_groups.set(user.client.get_groups().filter(client__isnull=True, segment='coordination', default=True))

            if (associate_professor_coordinator and groups_inspector):
                self.object.custom_groups.add(*groups_inspector)
            
            if self.request.POST.get('redirect_to_change_permissions') == 'true': # Não remover o == 'true', pq aqui eu comparo se é uma string mesmo.
                return JsonResponse({'success': True, 'redirect_url': reverse('accounts:user_permissions', kwargs={ "pk": self.object.id })})
            
            return JsonResponse({'success': True, 'redirect_url': self.get_success_url()})

    def form_invalid(self, form):
        errors = {field: error for field, error in form.errors.items()}
        return JsonResponse({'success': False, 'errors': errors})


    def get_success_url(self):
        return reverse('clients:members_list')


class MemberUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = User
    queryset = User.objects.filter(is_active=True)
    required_permissions = ['coordination', ]
    permission_required = 'clients.change_coordinationmember'
    form_class = UserForm
    context_object_name = 'object_member'
    template_name = "dashboard/members/member_create_update_new.html"
    success_message = "Membro atualizado com sucesso!"

    def dispatch(self, request, *args, **kwargs):
        member = self.get_object()
        if member == request.user:
            messages.error(request, "Você não pode editar seu próprio cadastro.")
            return redirect(reverse("clients:members_list"))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(MemberUpdateView, self).get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse('clients:members_list')

    def get_context_data(self, **kwargs):
        context = super(MemberUpdateView, self).get_context_data(**kwargs)
        user = self.request.user
        coordinations = user.get_coordinations_cache()
        user_member = self.object
        context['coordinations'] = SchoolCoordination.objects.filter(
            Q( # Lógica em: https://app.clickup.com/3120759/whiteboards/2z7kq-6333?shape-id=VvV4JUIKtd11FyFCpjK9K
                Q(id__in=user_member.get_coordinations_cache()) |
                Q(id__in=coordinations)
            )
        ).distinct()
        context['user_coordinations'] = CoordinationMember.objects.filter(user=user_member).values_list('coordination', flat=True)
        context['unities'] = Unity.objects.filter(
            Q( # Lógica em: https://app.clickup.com/3120759/whiteboards/2z7kq-6333?shape-id=VvV4JUIKtd11FyFCpjK9K
                Q(coordinations__in=user_member.get_coordinations_cache()) |
                Q(coordinations__in=coordinations)
            )
        ).distinct().prefetch_related('coordinations')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        user_coordinations = {str(uuid) for uuid in context['user_coordinations']}
        
        if form.is_valid():
            if form.cleaned_data['username'] and form.cleaned_data['username'] != form.instance.username:
                form.instance.username = form.cleaned_data['username']
            if form.cleaned_data['password']:
                form.instance.set_password(form.cleaned_data['password'])
            if form.cleaned_data['must_change_password']:
                form.instance.must_change_password = True
            if form.cleaned_data['name']:
                form.instance.name = form.cleaned_data['name']
            
            self.object = form.save()

            # atualizar as coordenações com base no que foi enviado, removendo ou adicionando
            submitted_coordinations = set(self.request.POST.get('coordinations').split(','))
            coordinations_to_remove = user_coordinations.difference(submitted_coordinations)
            coordinations_to_add = submitted_coordinations.difference(user_coordinations)

            if coordinations_to_add:
                queryset_to_add = SchoolCoordination.objects.filter(pk__in=coordinations_to_add)
                CoordinationMember.objects.bulk_create(
                    [
                        CoordinationMember(
                            user=form.instance,
                            coordination=coordination,
                            is_coordinator=True,
                            is_reviewer=True,
                            is_pedagogic_reviewer=True
                        )
                        for coordination in queryset_to_add
                    ]
                )
            elif coordinations_to_remove:
                CoordinationMember.objects.filter(
                    user=form.instance,
                    coordination__pk__in=coordinations_to_remove
                ).delete()
            else:
                pass


            CACHE_KEY = f'USER_COORDINATIONS_{self.object.pk}'
            if cache.get(CACHE_KEY):
                cache.delete(CACHE_KEY)

            if not self.object.custom_groups.exists():
                if self.object.client.has_default_groups('coordination'):
                    self.object.custom_groups.set(self.object.client.get_groups().filter(client__isnull=False, segment='coordination', default=True))
                else:
                    self.object.custom_groups.set(self.object.client.get_groups().filter(client__isnull=True, segment='coordination', default=True))

                groups_inspector = []
                associate_professor_coordinator = Inspector.objects.filter(
                    user__email=form.cleaned_data["email"]
                ).first()
                if associate_professor_coordinator:
                    for (
                        custom_group
                    ) in associate_professor_coordinator.user.custom_groups.all():
                        groups_inspector.append(str(custom_group.pk))
                        
                if groups_inspector:
                    self.object.custom_groups.add(*groups_inspector)        

            return JsonResponse({'success': True, 'redirect_url': self.get_success_url()})

    def form_invalid(self, form):
        errors = {field: error for field, error in form.errors.items()}
        return JsonResponse({'success': False, 'errors': errors})



class MemberDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = User
    required_permissions = ['coordination', ]
    permission_required = 'clients.delete_coordinationmember'
    success_message = "Membro removido com sucesso!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(MemberDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('clients:members_list')

class MemberResetPasswordUpdateView(LoginRequiredMixin, CheckHasPermission, UpdateView):
    model = User
    fields = ['must_change_password']
    required_permissions = [settings.COORDINATION]

    def dispatch(self, request, *args, **kwargs):
        self.object = super().get_object()
        self.object.set_password(self.object.email)
        self.object.must_change_password = True
        self.object.save()

        messages.success(request, f'Senha do membro "{self.object.name}" foi resetada com sucesso!')

        return HttpResponseRedirect(request.META.get("HTTP_REFERER"))
    
class ObligationTeacherConfigurationTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'dashboard/members/obligation_teacher.html'
    permission_required = 'clients.change_clientteacherobligationconfiguration'
    configuration = None
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:

            configuration = ClientTeacherObligationConfiguration.objects.filter(
                client=request.user.client
            )
            if configuration.exists():
                self.configuration = configuration.first()

        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = ClientTeacherObligationConfigurationForm()
        context["form"] = form
        return context
    
class ConfigNotificationsCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    template_name = 'dashboard/members/config_notifications.html'
    queryset = ConfigNotification.objects.all()
    form_class = ClientConfigNotificationsForm
    permission_required = 'clients.change_confignotification'
    success_message = 'Configurações criadas com sucesso.'
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        
        if user.is_authenticated and user.client_confignotification:
            return redirect(user.client_confignotification.get_absolute_url())
        
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        client = self.request.user.get_clients().first()
        initial.update({
            'send_email_to_student_after_create': client.send_email_to_student_after_create,
        })
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        client = self.request.user.get_clients().first()
        client.send_email_to_student_after_create = form.cleaned_data['send_email_to_student_after_create']
        client.save()
        return response


class ConfigNotificationsUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    template_name = 'dashboard/members/config_notifications.html'
    queryset = ConfigNotification.objects.all()
    form_class = ClientConfigNotificationsForm
    permission_required = 'clients.change_confignotification'
    success_message = 'Configurações atualizadas com sucesso.'

    def dispatch(self, request, *args, **kwargs):

        # Iniciei as variáveis aqui para o caso e precisar
        # reutilizar lá na frente.
        user = self.request.user
        configuration: ConfigNotification = self.get_object()

        if user.is_authenticated:
            # Lógicas que utiliza algum atributo de user deve ficar dentro 
            # do is_authenticated
            client = user.client
            if configuration.client != client:
                messages.error(request, 'Você não tem acesso a essa página.')
                return redirect('core:redirect_dashboard')
            
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        client = self.request.user.get_clients().first()
        initial.update({
            'send_email_to_student_after_create': client.send_email_to_student_after_create,
        })
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        client = self.request.user.get_clients().first()
        client.send_email_to_student_after_create = form.cleaned_data['send_email_to_student_after_create']
        client.save()
        return response


class QuestionTagListView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'dashboard/members/question_tag_list.html'
    permission_required = 'clients.view_questiontag'
    model = QuestionTag
    paginate_by = 30

    def get_queryset(self):
        queryset = super().get_queryset()

        return queryset.filter(client__in=self.request.user.get_clients_cache())

class QuestionTagCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    template_name = 'dashboard/members/question_tag_create_update.html'
    form_class = ClientTagsForm
    queryset = QuestionTag.objects.all()
    permission_required = 'clients.add_questiontag'
    success_message = 'Tag adicionada.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context

class QuestionTagUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    template_name = 'dashboard/members/question_tag_create_update.html'
    permission_required = 'clients.change_questiontag'
    model = QuestionTag
    form_class = ClientTagsForm
    success_message = 'Tag editada'


class QuestionTagDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = QuestionTag
    required_permissions = ['coordination', ]
    permission_required = 'clients.delete_questiontag'
    success_message = "Tag removida!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(QuestionTagDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('clients:question_tag_list')

class QuestionsConfigurationsTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'dashboard/members/questions_configutation.html'
    permission_required = 'clients.change_clientquestionsconfiguration'
    configuration = None
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if user and user.is_authenticated and hasattr(user.get_clients().first(), 'questions_configuration'):
            self.configuration = user.get_clients().first().questions_configuration
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = ClientQuestionsConfigurationForm(instance=self.configuration) if self.configuration else ClientQuestionsConfigurationForm()
        context["form"] = form
        return context
    
    def post(self, request):
        form = ClientQuestionsConfigurationForm(instance=self.configuration, data=request.POST)
        
        if form.is_valid():
            form.save()
            messages.success(request, f'As configurações foram salvas com sucesso!')
        else:
            messages.error(request, f'Ocorreu um erro ao tentar salvar as configurações, tente novamente.')
            
        return HttpResponseRedirect(reverse('core:redirect_dashboard'))

class ConfigOMRConfigurationUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    template_name = 'dashboard/members/omr_print_separation_update_or_create.html'
    queryset = Client.objects.all()
    form_class = ClientForm
    permission_required = 'clients.change_confignotification'
    success_message = 'Configuração de malote alterado com sucesso.'
    success_url = reverse_lazy('core:redirect_dashboard')


class MembersExportCSV(LoginRequiredMixin, CheckHasPermission, ListView):
    required_permissions = [settings.COORDINATION]
    model = User
    permission_required = ['clients.can_export_coodinator']

    
    def get_queryset(self, **kwargs):
        queryset = User.objects.filter(
            Q(
				coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache(),
                is_active=True,
			)
        ).distinct()

        if self.request.GET.get('q_name_email', ""):
            queryset = queryset.filter(
                Q(name__icontains=self.request.GET.get('q_name_email', "")) |
                Q(email__icontains=self.request.GET.get('q_name_email', ""))
            )
        if self.request.GET.get('q_member', ""):
            queryset = queryset.filter(
            coordination_member__in=self.request.GET.getlist('q_member', "")
            )
        return queryset

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        response = self._generate_csv(queryset)
        
        return response
    
    def _generate_csv(self, queryset):
        buffer = io.StringIO()  
        wr = csv.writer(buffer, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        
        csv_header = ['Nome', 'Email', 'Coordenações', 'Grupo de Acesso']  
        wr.writerow(csv_header)
        
        data_members = self._generate_member_export_data(queryset)
        wr.writerows(data_members)
        
        buffer.seek(0)
        sheet = pyexcel.load_from_memory("csv", buffer.getvalue())
        
        response = HttpResponse(sheet.csv, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="exportação.csv"' 
        
        return response
        
    def _generate_member_export_data(self, queryset):
        export_data = []
        
        for member in queryset:
            member_coordinations = ' | '.join(member.get_coordinations().values_list('name', flat=True))
            
            member_access_group = ' | '.join(group.name for group in member.custom_groups.all())

            member_data = [
                member.name,
                member.email,
                member_coordinations,
                member_access_group,
            ]

            export_data.append(member_data)

        return export_data


members_export = MembersExportCSV.as_view()
members_list = MemberListView.as_view()
members_create = MemberCreateView.as_view()
members_update = MemberUpdateView.as_view()
members_delete = MemberDeleteView.as_view()

members_password_reset = MemberResetPasswordUpdateView.as_view()

obligation_teacher_configuration = ObligationTeacherConfigurationTemplateView.as_view()