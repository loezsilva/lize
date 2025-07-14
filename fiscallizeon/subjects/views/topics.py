import sys, os
import pandas as pd

from rest_framework import viewsets
from rest_framework.generics import ListAPIView
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.views.generic import ListView
from django.http import HttpResponseRedirect
from fiscallizeon.core.utils import CheckHasPermission
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views import View

from fiscallizeon.subjects.serializers.topics import TopicSerializer, TopicSimpleSerializer
from fiscallizeon.subjects.models import Topic, Subject, MainTopic, Theme
from fiscallizeon.classes.models import Grade
from fiscallizeon.subjects.forms.topics import TopicForm

class TopicViewSet(viewsets.ModelViewSet):
    serializer_class = TopicSerializer
    queryset = Topic.objects.all()
    # search_fields = ()
    # filterset_fields = ()

class TopicListView(ListAPIView):
    serializer_class = TopicSimpleSerializer
    queryset = Topic.objects.all()
    filterset_fields = ['subject', 'grade']
    required_scopes = ['read', 'write']

    def get_queryset(self, **kwargs):
        subject_pk = self.request.GET.get('subject_pk', None)
        subject = get_object_or_404(Subject, pk=subject_pk) if subject_pk else None
        subjects = self.request.GET.get('subject__in')
        subjects = subjects.split(",") if subjects else []
        
        queryset = Topic.objects.filter(
            Q(client__isnull=True) |
            Q(
                Q(client__in=self.request.user.get_clients_cache()),

            )
        ).order_by('created_at').distinct()

        queryset = queryset.filter(
            Q(
                Q(subject=subject) |
                Q(subject__subject=subject) |
                Q(subject__subject__subject=subject) |
                Q(subject__subject__subject__subject=subject) 
            )       
        )

        if self.request.user.client and self.request.user.client.use_only_own_topics:
            queryset = queryset.exclude(
                client__isnull=True
            )
    
        return queryset.order_by('name')

class TopicList(LoginRequiredMixin, CheckHasPermission,  ListView):
    model = Topic
    required_permissions = [settings.COORDINATION, settings.TEACHER, ]
    permission_required = 'subjects.view_topic'
    paginate_by = 30
    template_name = "dashboard/topics/topic_list.html"
    
    def get_context_data(self, **kwargs):
        context = super(TopicList, self).get_context_data(**kwargs)
        context["current_knowledge_area"] =  ""
        context["current_subject"] =  ""
        context["current_grade"] = ""
        context['selected_filter'] = self.request.GET.get("selected_filter", "")
        
        context['subjects'] = Subject.objects.filter(
            Q(parent_subject__isnull=True) |
            Q(client__isnull=True) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client__in=self.request.user.get_clients_cache())
            )
        ).order_by('created_at').distinct()
        
        context["grades"] = Grade.objects.all()
        
        # Filters
        context['q_name'] = self.request.GET.get('q_name', '')
        context['q_grades'] = self.request.GET.get('q_grades', '')
        context['q_subjects'] = self.request.GET.get('q_subjects', '')

        return context
        
    def get_queryset(self, **kwargs):
        queryset = Topic.objects.filter(
            Q(
                client__in=self.request.user.get_clients_cache()
            )
        ).distinct().order_by('-created_at')
        
        if self.request.GET.get('q_name'):
            queryset = queryset.filter(name__icontains=self.request.GET.get('q_name'))
            
        if self.request.GET.get('q_grades'):
            queryset = queryset.filter(grade__in=self.request.GET.getlist('q_grades'))
        
        if self.request.GET.get('q_subjects'):
            queryset = queryset.filter(subject__in=self.request.GET.getlist('q_subjects'))

        user = self.request.user
        if user.user_type == settings.TEACHER:
            queryset = queryset.filter(
                Q(subject__in=user.inspector.subjects.all()) |
                Q(created_by=user)
            )
        return queryset

class TopicCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = Topic
    required_permissions = [settings.COORDINATION, settings.TEACHER,]
    permission_required = 'subjects.add_topic'
    form_class = TopicForm
    template_name = "dashboard/topics/topic_create_update.html"
    success_message = "Habilidade cadastrada com sucesso!"

    def get_success_url(self):
        return reverse('subjects:topic_list')

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

        return super(self, TopicCreateView).form_valid(form)

class TopicUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = Topic
    required_permissions = [settings.COORDINATION, settings.TEACHER, ]
    permission_required = 'subjects.change_topic'
    form_class = TopicForm
    template_name = "dashboard/topics/topic_create_update.html"
    success_message = "Habilidade atualizada com sucesso!"

    def get_success_url(self):
        return reverse('subjects:topic_list')

    def get_context_data(self, **kwargs):    
        context = super().get_context_data(**kwargs)
        context["current_knowledge_area"] =  ""
        context["current_grade"] = ""
        context["current_subject"] =  ""

        return context

class TopicDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = Topic
    required_permissions = [settings.COORDINATION,  settings.TEACHER,]
    permission_required = 'subjects.delete_topic'
    success_message = "Habilidade removida com sucesso!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(TopicDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('subjects:topic_list')


class ImportTopicView(View):
    def post(self, request, *args, **kwargs):
        user = request.user
        client = user.client
        try:
            with transaction.atomic():
                
                subject = Subject.objects.get(pk=request.POST.get('subject'))
                grade = Grade.objects.get(pk=request.POST.get('grade'))

                topics_file = request.FILES['topics_file']
                topics_file_name = request.FILES['topics_file'].name
                extension = topics_file_name.split(".")[-1]

                if extension in ['xlsx', 'xls']:
                    reader = pd.read_excel(topics_file)

                elif extension in ['csv']:
                    reader = pd.read_csv(topics_file)

                counts = {'created': 0, 'updated': 0}

                for (index, row) in reader.iterrows():
                    try:
                        if not row.empty: 
                            new_topic, created = Topic.objects.update_or_create(
                                subject=subject,
                                grade=grade,
                                name=f'{row["topico"]}: {row["assunto"]}',
                                client=client,
                                created_by=user,
                                stage=int(row["etapa"])
                            )

                            if created:
                                counts['created'] += 1
                            else:
                                counts['updated'] += 1


                    except Exception as e:
                        exc_type, exc_obj, exc_tb = sys.exc_info()
                        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                        print(exc_type, fname, exc_tb.tb_lineno, e)
                        messages.error(self.request, "Houve algum erro na leitura do arquivo, ajuste a planilha e tente novamente")

                        return HttpResponseRedirect(reverse('subjects:topic_list'))

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno, e)
            messages.error(self.request, "Houve algum erro na leitura do arquivo, ajuste a planilha e tente novamente")

            return HttpResponseRedirect(reverse('subjects:topic_list'))
        
        messages.success(self.request, f'Importação realizada com sucesso. <b>{counts["created"]} Criados</b> e <b>{counts["updated"]} atualizados</b>.')

        return HttpResponseRedirect(reverse('subjects:topic_list'))

        
class ImportCompleteTopicView(View):
    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                user = request.user
                client = user.get_clients().first()

                topics_file = request.FILES['topics_file']
                topics_file_name = request.FILES['topics_file'].name
                extension = topics_file_name.split(".")[-1]

                if extension not in ['xlsx', 'xls', 'csv']:
                    messages.error(request, "Formato de arquivo não suportado. Use XLSX, XLS ou CSV.")
                    return HttpResponseRedirect(reverse('subjects:topic_list'))

                reader = self.process_topics_file(topics_file, extension)

                counts = {'created': 0, 'updated': 0}
                for index, (row_index, row) in enumerate(reader.iterrows(), start=2):                    
                    try:
                        if not row.empty: 
                            theme = None
                            main_topic = None
                            
                            theme_name = self.replace_row_nan(row['tema'])
                            main_topic_name = self.replace_row_nan(row['tópico'])
                            
                            topic = self.get_error_topic_is_nan(row["assunto"],  "O campo Assunto está vazio.")

                            try:
                                subject_name, knowledge_area, segment = str(row["disciplina"]).split(' - ')
                            except ValueError:
                                raise ValueError(f"O campo Disciplina está com formato errado ou não existe na sua base de dados.")
                            subject_object = self._get_subject_object(user, subject_name, knowledge_area, segment)
                            subject =  self._get_or_error(subject_object, f"O campo Disciplina está com formato errado ou não existe na sua base de dados.")
                            
                            grade_obj = Grade.get_grade_by_code(row["série"])
                            grade = self._get_or_error(grade_obj ,f"O campo Série '{row['série']}' está com formato errado.")

                            stage_row = row['etapa']
                            stage = self._get_stage_valid(stage_row, f"O campo Etapa '{stage_row}' está com formato errado. Só é permitido o preenchimento com números de 1 a 7.")

                            if theme_name:
                                theme, created = Theme.objects.update_or_create(name=theme_name, client=client, defaults={'created_by':user})

                            if main_topic_name:
                                main_topic, created = MainTopic.objects.update_or_create(name=main_topic_name, theme=theme,client=client, defaults={'created_by':user})
                            
                            new_topic, created = Topic.objects.update_or_create(
                                subject=subject,
                                grade=grade,
                                name=topic,
                                stage=stage,
                                theme=theme,
                                main_topic=main_topic,
                                client=client,
                                defaults={
                                    'created_by':user,
                                }
                            )

                            if created: 
                                counts['created'] += 1
                            else:
                                counts['updated'] += 1

                    except ValueError as e:
                        messages.error(request, f"Erro na linha {index}: {e}")
                        raise
                    except Exception as e:
                        messages.error(request, f"Erro na linha {index}. Corrija o campo e tente novamente")
                        raise

                        
        except Exception as e:
            return HttpResponseRedirect(reverse('subjects:topic_list'))
        
        messages.success(request, f'Importação realizada com sucesso. <b>{counts["created"]} Criados</b> e <b>{counts["updated"]} atualizados</b>.')
        return HttpResponseRedirect(reverse('subjects:topic_list'))
        
    def process_topics_file(self, topics_file, extension):
        if extension in ['xlsx', 'xls']:
            return pd.read_excel(topics_file)
        elif extension in ['csv']:
            return pd.read_csv(topics_file)
    
    def replace_row_nan(self, row):
        if pd.isna(row):
            row = ""
        return row

    def get_error_topic_is_nan(self, topic, error_message):
        if pd.isna(topic):
            raise ValueError(error_message)
        return topic
    
    def _get_or_error(self, obj, error_message):
        if not obj:
            raise ValueError(error_message)
        return obj
    
    def _get_stage_valid(self, stage, error_message):
        if str(stage).isnumeric():
            numero = int(stage)
            if 1 <= numero <= 7:
                return int(stage)
        raise ValueError(error_message)

    def _handle_error(self, error, row_number=None):
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno, error)
        messages.error(self.request, "Houve algum erro na leitura do arquivo, ajuste a planilha e tente novamente")

    def _get_subject_object(self, user, subject_name, knowledge_area, segment):
        subject_object = user.get_availables_subjects().filter(
            name__iexact=subject_name,
            knowledge_area__name__icontains=knowledge_area,
            parent_subject__client__isnull=True,
            knowledge_area__grades__level__in=[
                Grade.HIGHT_SCHOOL
            ] if 'ensino médio' in segment.lower() else [
                Grade.ELEMENTARY_SCHOOL,
                Grade.ELEMENTARY_SCHOOL_2
            ]
        ).distinct()
        return subject_object.first()


topic_list = TopicList.as_view()
topic_create = TopicCreateView.as_view()
topic_update = TopicUpdateView.as_view()
topic_delete = TopicDeleteView.as_view()
topic_import = ImportTopicView.as_view()
topic_complete_topic = ImportCompleteTopicView.as_view()

topic_list_api = TopicListView.as_view()