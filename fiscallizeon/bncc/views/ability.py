import io
import csv
import pyexcel

from django.db import transaction
from rest_framework.generics import ListAPIView

from fiscallizeon.bncc.serializers.ability import AbilitySimpleSerializer
from fiscallizeon.bncc.models import Abiliity
from django.views import View

from django.db.models import Q, F
from django.db.models.functions import Length
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.views.generic import ListView
from django.http import HttpResponseRedirect
from rest_framework.generics import ListAPIView

import django_filters
from django_filters import FilterSet
from django_filters.rest_framework import DjangoFilterBackend

from fiscallizeon.core.utils import CheckHasPermission
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from fiscallizeon.subjects.models import Subject
from fiscallizeon.classes.models import Grade

from fiscallizeon.bncc.forms.ability import AbilityForm

class SubjectInOrNoneFilterSet(FilterSet):
    subject_in_or_none = django_filters.ModelMultipleChoiceFilter(
        method='subject_in_or_none_method',
        queryset=Subject.objects.all(),
    )

    def subject_in_or_none_method(self, queryset, name, value):
        if not value:
            return queryset
            
        query = queryset.filter(
           Q(
                Q(subject__in=value) |
                Q(subject__isnull=True)
            )
        )

        return query

    class Meta:
        model = Abiliity
        fields = ['subject_in_or_none', 'subject', 'knowledge_area', 'code']

class AbiliityListView(ListAPIView):
    serializer_class = AbilitySimpleSerializer
    queryset = Abiliity.objects.all().order_by('code')
    # filter_class = SubjectInOrNoneFilterSet

    def get_queryset(self, **kwargs):
        search = self.request.GET.get('search')
        queryset = Abiliity.objects.filter(
            Q(
                Q(client__isnull=True) |
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
                Q(Q(text__icontains=search) | Q(code__icontains=search)) if search else Q()
            )
        ).annotate(
            code_lenght=Length('code')
        )

        grades = self.request.GET.getlist("grades", None)
        if grades:
             queryset = queryset.filter(
                  grades__in=grades
             )
        
        return queryset.order_by("code_lenght", "code", F('subject').desc(nulls_last=True), "text")

class AbilityList(LoginRequiredMixin, CheckHasPermission,  ListView):
    model = Abiliity
    required_permissions = [settings.COORDINATION, settings.TEACHER, ]
    permission_required = 'bncc.view_abiliity'
    paginate_by = 30
    template_name = "dashboard/abilities/ability_list.html"


    def get_context_data(self, **kwargs):
        context = super(AbilityList, self).get_context_data(**kwargs)
        context["current_knowledge_area"] =  ""
        context["current_subject"] =  ""
        context["current_grade"] = ""

        return context

    def get_queryset(self, **kwargs):
        queryset = Abiliity.objects.filter(
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

class AbilityCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = Abiliity
    required_permissions = [settings.COORDINATION, settings.TEACHER,]
    permission_required = 'bncc.add_abiliity'
    form_class = AbilityForm
    template_name = "dashboard/abilities/ability_create_update.html"
    success_message = "Habilidade cadastrada com sucesso!"

    def get_success_url(self):
        return reverse('bncc:abilities_list')

    def get_context_data(self, **kwargs):    
        context = super().get_context_data(**kwargs)
        context["current_knowledge_area"] =  ""
        context["current_subject"] =  ""
        context["current_grade"] = ""

        return context
    
    def form_valid(self, form):
        if form.is_valid():
            self.object = form.save(commit=False)
            self.object.created_by = self.request.user
            self.object.client = self.request.user.get_clients().first()
            self.object.save()
            form.save_m2m()

            return HttpResponseRedirect(self.get_success_url())

        return super(self, AbilityCreateView).form_valid(form)

class AbilityUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = Abiliity
    required_permissions = [settings.COORDINATION, settings.TEACHER, ]
    permission_required = 'bncc.change_abiliity'
    form_class = AbilityForm
    template_name = "dashboard/abilities/ability_create_update.html"
    success_message = "Habilidade atualizada com sucesso!"

    def get_success_url(self):
        return reverse('bncc:abilities_list')

    def get_context_data(self, **kwargs):    
        context = super().get_context_data(**kwargs)
        context["current_knowledge_area"] = self.object.subject.knowledge_area.pk if self.object.subject else self.object.knowledge_area.pk
        context["current_subject"] =  ""
        context["current_grade"] = ""

        return context

class AbilityDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = Abiliity
    required_permissions = [settings.COORDINATION,  settings.TEACHER,]
    permission_required = 'bncc.delete_abiliity'
    success_message = "Habilidade removida com sucesso!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(AbilityDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('bncc:abilities_list')


class ImportAbilityView(View):
	def post(self, request, *args, **kwargs):
		try:
			with transaction.atomic():
				user = request.user
				client = user.get_clients().first()
				
				print("#####", request.POST)
                
				subject = Subject.objects.get(pk=request.POST.get('subject'))
				grade = Grade.objects.get(pk=request.POST.get('grade'))

				abilities_file = request.FILES['abilities_file']
				abilities_file_name = request.FILES['abilities_file'].name
				extension = abilities_file_name.split(".")[-1]

				sheet = pyexcel.load_from_memory(extension, abilities_file.read())
				
				reader = csv.DictReader(io.StringIO(sheet.csv))

				counts = {'created': 0, 'updated': 0}

				for ability in reader:
					try:
						if '' not in ability.values(): 
							grades = Grade.objects.filter(
                                name__in=ability["ano"].replace(' ', '').split(';'),
                                level=grade.level
                            )

							new_ability, created = Abiliity.objects.update_or_create(
                                code=f'{ability["codigo"]}',
                                text=f'{ability["texto"]}',
                                knowledge_area=subject.knowledge_area,
                                subject=subject,
                                client=client,
                                created_by=user
							)

							new_ability.grades.set(grades)

							if created:
								counts['created'] += 1
							else:
								counts['updated'] += 1


					except Exception as e:
						import sys, os
						exc_type, exc_obj, exc_tb = sys.exc_info()
						fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
						print(exc_type, fname, exc_tb.tb_lineno, e)
						messages.error(self.request, "Houve algum erro na leitura do arquivo, ajuste a planilha e tente novamente")

						return HttpResponseRedirect(reverse('bncc:abilities_list'))

		except Exception as e:
			import sys, os
			exc_type, exc_obj, exc_tb = sys.exc_info()
			fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
			print(exc_type, fname, exc_tb.tb_lineno, e)
			messages.error(self.request, "Houve algum erro na leitura do arquivo, ajuste a planilha e tente novamente")

			return HttpResponseRedirect(reverse('bncc:abilities_list'))
		
		messages.success(self.request, f'Importação realizada com sucesso. <b>{counts["created"]} Criados</b> e <b>{counts["updated"]} atualizados</b>.')

		return HttpResponseRedirect(reverse('bncc:abilities_list'))



abilities_list = AbilityList.as_view()
abilities_create = AbilityCreateView.as_view()
abilities_update = AbilityUpdateView.as_view()
abilities_delete = AbilityDeleteView.as_view()

ability_list_api = AbiliityListView.as_view()

ability_import = ImportAbilityView.as_view()

