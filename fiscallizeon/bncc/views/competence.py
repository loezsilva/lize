from django.db.models import Q, F
from django.db.models.functions import Length
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.views.generic import ListView
from django.http import HttpResponseRedirect
from rest_framework.generics import ListAPIView
from django_filters.rest_framework import DjangoFilterBackend

from fiscallizeon.core.utils import CheckHasPermission
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.edit import CreateView, UpdateView, DeleteView

import django_filters
from django_filters import FilterSet

from fiscallizeon.bncc.models import Competence
from fiscallizeon.bncc.forms.competence import CompetenceForm
from fiscallizeon.bncc.serializers.competence import CompetenceSimpleSerializer
from fiscallizeon.subjects.models import Subject

class SubjectInOrNoneFilterSet(FilterSet):
    subject_in_or_none = django_filters.ModelMultipleChoiceFilter(
        method='subject_in_or_none_method',
        queryset=Subject.objects.all(),
    )

    def subject_in_or_none_method(self, queryset, name, value):
        if not value:
            return queryset

        return queryset.filter(
           Q(
                Q(subject__in=value) |
                Q(subject__isnull=True)
            )
        )

    class Meta:
        model = Competence
        fields = ['subject_in_or_none', 'subject', 'knowledge_area', 'code']



class CompetenceListView(ListAPIView):
    serializer_class = CompetenceSimpleSerializer
    queryset = Competence.objects.all()
    required_scopes = ['read', 'write']
    # filter_class = SubjectInOrNoneFilterSet


    def get_queryset(self, **kwargs):
        search = self.request.GET.get('search')

        queryset = Competence.objects.filter(
            Q(client__isnull=True) |
            Q(
                Q(client__in=self.request.user.get_clients_cache())
            )
        ).order_by('client', '-created_at').distinct()
        
        knowledge_area_pk = self.request.GET.get('knowledge_area', None)

        queryset = queryset.filter(
            Q(
                Q(subject__in=self.request.GET.getlist('subject_in_or_none')) |
                Q(
                    Q(subject__isnull=True),
                    Q(knowledge_area=knowledge_area_pk) if knowledge_area_pk else Q()
                ),
                Q(text__icontains=search) if search else Q()
            )
        ).annotate(
            code_lenght=Length('code')
        )

        return queryset.order_by("code_lenght", "code", F('subject').desc(nulls_last=True), "text")



class CompetenceList(LoginRequiredMixin, CheckHasPermission,  ListView):
    model = Competence
    required_permissions = [settings.COORDINATION, settings.TEACHER, ]
    permission_required = 'bncc.view_competence'
    paginate_by = 30
    template_name = "dashboard/competences/competence_list.html"


    def get_context_data(self, **kwargs):
        context = super(CompetenceList, self).get_context_data(**kwargs)

        return context

    def get_queryset(self, **kwargs):
        queryset = Competence.objects.filter(
            Q(
				client__in=self.request.user.get_clients_cache()
			)
        ).distinct().order_by('-created_at')

        user = self.request.user
        if user.user_type == settings.TEACHER:
            queryset = queryset.filter(
                Q(subject__in=user.inspector.subjects.all()) |
                Q(created_by=user)
            )

        return queryset


class CompetenceCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = Competence
    required_permissions = [settings.COORDINATION, settings.TEACHER, ]
    permission_required = 'bncc.add_competence'
    form_class = CompetenceForm
    template_name = "dashboard/competences/competence_create_update.html"
    success_message = "Competência cadastrada com sucesso!"

    def get_success_url(self):
        return reverse('bncc:competences_list')

    def get_context_data(self, **kwargs):    
        context = super().get_context_data(**kwargs)
        context["current_knowledge_area"] =  ""
        context["current_subject"] =  ""

        return context
    
    def form_valid(self, form):
        if form.is_valid():
            self.object = form.save(commit=False)
            self.object.created_by = self.request.user
            self.object.client = self.request.user.get_clients().first()
            self.object.save()

            return HttpResponseRedirect(self.get_success_url())

        return super(self, CompetenceCreateView).form_valid(form)



class CompetenceUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = Competence
    required_permissions = [settings.COORDINATION, settings.TEACHER, ]
    permission_required = 'bncc.change_competence'
    form_class = CompetenceForm
    template_name = "dashboard/competences/competence_create_update.html"
    success_message = "Competência atualizada com sucesso!"

    def get_success_url(self):
        return reverse('bncc:competences_list')

    def get_context_data(self, **kwargs):    
        context = super().get_context_data(**kwargs)
        context["current_knowledge_area"] = self.object.subject.knowledge_area.pk if self.object.subject else self.object.knowledge_area.pk
        context["current_subject"] =  ""

        return context


class CompetenceDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = Competence
    required_permissions = [settings.COORDINATION, settings.TEACHER, ]
    permission_required = 'bncc.delete_competence'
    success_message = "Competência removida com sucesso!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(CompetenceDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('bncc:competences_list')



competences_list = CompetenceList.as_view()
competences_create = CompetenceCreateView.as_view()
competences_update = CompetenceUpdateView.as_view()
competences_delete = CompetenceDeleteView.as_view()

competence_list_api = CompetenceListView.as_view()