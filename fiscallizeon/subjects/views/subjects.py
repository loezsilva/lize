from rest_framework import viewsets, status
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.filters import SearchFilter

from django.apps import apps
from django.conf import settings
from django.views.generic import ListView
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.cache import cache
from django.contrib import messages
from django.db.models import Q, Exists, OuterRef
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from fiscallizeon.core.print_colors import *
from fiscallizeon.subjects.serializers.subjects import SubjectSerializer, SubjectSimpleSerializer, SubjectVerySimpleSerializer, SubjectTreeSerializer, CommonTreeSerializer
from fiscallizeon.subjects.models import Subject, Topic, MainTopic, Theme, SubjectRelation
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.questions.models import Question
from fiscallizeon.subjects.forms.subject import SubjectForm, SubjectRelationForm, SubjectRelationCreationForm
from fiscallizeon.inspectors.models import Inspector


class SubjectViewSet(viewsets.ModelViewSet):
	serializer_class = SubjectSerializer
	queryset = Subject.objects.all()
	# search_fields = ()
	# filterset_fields = ()

class SubjectListView(ListAPIView):
    serializer_class = SubjectSimpleSerializer
    queryset = Subject.objects.all()
    required_scopes = ['read', 'write']
    filterset_fields = [
        'id', 
        'knowledge_area', 
        'knowledge_area__grades', 
        'parent_subject',
        'teachersubject__teacher',
    ]

    def get_queryset(self, **kwargs):
        queryset = super(SubjectListView, self).get_queryset(**kwargs)
        
        queryset = queryset.filter(
            Q(
                Q(client__isnull=True) |
                Q(client=self.request.user.client)
            )
        )

        if self.request.user.client_use_only_own_subjects:
            queryset = queryset.exclude(
                client__isnull=True
            )
        
        return (
            queryset
            .distinct()
            .order_by('name')
        )


class SubjectList(LoginRequiredMixin, CheckHasPermission,  ListView):
    model = Subject
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'subjects.view_subject'
    paginate_by = 30
    template_name = "dashboard/subjects/subject_list.html"


    def get_context_data(self, **kwargs):
        context = super(SubjectList, self).get_context_data(**kwargs)

        return context

    def get_queryset(self, **kwargs):
        queryset = Subject.objects.filter(
            client=self.request.user.client
        ).distinct().order_by('-created_at')

        return queryset

class SubjectCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = Subject
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'subjects.add_subject'
    form_class = SubjectForm
    template_name = "dashboard/subjects/subject_create_update.html"
    success_message = "Disciplina cadastrada com sucesso!"

    def get_form_kwargs(self):
        kwargs = super(SubjectCreateView, self).get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse('subjects:subjects_list')

    def get_context_data(self, **kwargs):    
        context = super().get_context_data(**kwargs)

        return context

    def form_valid(self, form):
        if form.is_valid():
            self.object = form.save(commit=False)
            self.object.created_by = self.request.user
            self.object.knowledge_area = self.object.parent_subject.knowledge_area
            self.object.client = self.request.user.get_clients().first()
            self.object.is_foreign_language_subject = self.object.is_foreign_language_subject

            self.object.save()

            return HttpResponseRedirect(self.get_success_url())

        return super(self, SubjectCreateView).form_valid(form)

class SubjectUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = Subject
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'subjects.change_subject'
    form_class = SubjectForm
    template_name = "dashboard/subjects/subject_create_update.html"
    success_message = "Disciplina atualizada com sucesso!"

    def get_form_kwargs(self):
        kwargs = super(SubjectUpdateView, self).get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse('subjects:subjects_list')

    def get_context_data(self, **kwargs):    
        context = super().get_context_data(**kwargs)

        return context
    def form_valid(self, form):
        if form.is_valid():
            self.object = form.save(commit=False)
            self.object.knowledge_area = self.object.parent_subject.knowledge_area
            self.object.is_foreign_language_subject = self.object.is_foreign_language_subject
            
            self.object.save()
            
            return HttpResponseRedirect(self.get_success_url())

        return super(self, SubjectCreateView).form_valid(form)

class SubjectDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = Subject
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'subjects.delete_subject'
    success_message = "Assunto removido com sucesso!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(SubjectDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('subjects:subjects_list')
    

class SubjectStudyMaterialListAPIView(LoginRequiredMixin, CheckHasPermission, ListAPIView):
    model = Subject
    serializer_class = SubjectVerySimpleSerializer
    required_permissions = [settings.COORDINATION,settings.TEACHER]
    search_fields = ['name']

    def get_queryset(self, **kwargs):
        user = self.request.user

        if user.user_type == settings.TEACHER:
            inspector_instance = Inspector.objects.filter(user=self.request.user).first()
            return inspector_instance.subjects.all().distinct().order_by('-created_at')
        
        queryset = Subject.objects.filter(
            Q(parent_subject__isnull=True) |
            Q(client__isnull=True) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client__in=user.get_clients_cache())
            )
        ).distinct().order_by('-created_at')
        return queryset


class CommonTreeModel:
    def __init__(self, id, text, leaf, model, subject_name):
        self.id = id
        self.text = text
        self.leaf = leaf
        self.checked = False
        self.expanded = False
        self.model = model
        self.subject_name = subject_name


class SubjectTreeQuerysetMixin(object):
    
    def get_filters(self):
        self.user = self.request.user
        
        categories = self.request.GET.getlist('q_category', "")
        levels = self.request.GET.getlist('q_level', "")
        grades = self.request.GET.getlist('q_grade', "")
        segment = self.request.GET.get("segment")
        only_my_questions = self.request.GET.get("only_my_questions", "")
        request_subject = self.request.GET.get("request_subject", "")

        return categories, levels, grades, segment, only_my_questions, request_subject
    
    def get_cache_key(self):
        categories, levels, grades, segment, only_my_questions, request_subject = self.get_filters()
        key = f'{self.user.get_clients_cache()[0]}-{"_".join(categories)}-{"_".join(levels)}-{"_".join(grades)}-{segment}-{request_subject}'
        if only_my_questions:
            key += "-only_my_questions"
        return key

    def get_filtred_questions(self):
        categories, levels, grades, segment, only_my_questions, request_subject = self.get_filters()
        
        CACHE_KEY = f'FILTRED_QUESTIONS-{self.get_cache_key()}'
        
        if not cache.get(CACHE_KEY): 
            
            questions = Question.objects.filter(
                Q(pk__in=self.user.get_questions_database_cache()),
                Q(coordinations__in=self.user.get_coordinations_cache()) if only_my_questions else Q(),
                Q(is_public=True) if not only_my_questions else Q(),
                Q(grade__level=segment),
                Q(category__in=categories) if categories else Q(),
                Q(level__in=levels) if levels else Q(),
                Q(grade__in=grades) if grades else Q(),
            ).values('pk')
                        
            cache.set(CACHE_KEY, questions, 4 * 60 * 60)
            
        return cache.get(CACHE_KEY)

class SubjectTreeListView(ListAPIView, SubjectTreeQuerysetMixin):
    serializer_class = SubjectTreeSerializer
    filter_backends = [SearchFilter]

    search_fields = [
        'name',
        'topic__name',
        'topic__theme__name',
        'topic__main_topic__name',
    ]
    
    def get(self, request, *args, **kwargs):
        CACHE_KEY = f'TREE-DATABASE-{self.get_cache_key()}'
        if not cache.get(CACHE_KEY):
            queryset = self.get_queryset()
            cache.set(CACHE_KEY, self.get_serializer(queryset, many=True).data, 4*60*60)

        return Response(cache.get(CACHE_KEY))

    def get_queryset(self):
        
        CACHE_KEY = f'FILTRED_SUJECTS-{self.get_cache_key()}'

        if not cache.get(CACHE_KEY): 
            request_subject = self.get_filters()[5]

            client_subjects = []
            if request_subject:
                client_subjects = Subject.objects.annotate(
                    has_questions=Exists(
                        Question.objects.filter(
                            Q(
                                Q(subject=request_subject) |
                                Q(subject__parent_subject=request_subject) |
                                Q(subject__parent_subject__parent_subject=request_subject) |
                                Q(subject__parent_subject__parent_subject__parent_subject=request_subject) |
                                Q(subject__parent_subject__parent_subject__parent_subject__parent_subject=request_subject) 
                            ),
                            Q(coordinations__unity__client__in=self.user.get_clients_cache())
                        )
                    )
                ).filter(
                    Q(id=request_subject),
                    Q(has_questions=True),
                    Q(knowledge_area__grades__level=self.get_filters()[3]),
                    Q(
                        Q(client__isnull=True) |
                        Q(client__in=self.user.get_clients_cache())
                    )
                ).distinct().values_list('pk', flat=True)

            else:
                client_subjects = Subject.objects.annotate(
                    has_questions=Exists(
                        Question.objects.filter(
                            Q(
                                Q(subject=OuterRef('pk')) |
                                Q(subject__parent_subject=OuterRef('pk')) |
                                Q(subject__parent_subject__parent_subject=OuterRef('pk')) |
                                Q(subject__parent_subject__parent_subject__parent_subject=OuterRef('pk')) |
                                Q(subject__parent_subject__parent_subject__parent_subject__parent_subject=OuterRef('pk')) 
                            ),
                            Q(coordinations__unity__client__in=self.user.get_clients_cache())
                        )
                    )
                ).filter(
                    Q(has_questions=True),
                    Q(knowledge_area__grades__level=self.get_filters()[3]),
                    Q(
                        Q(client__isnull=True) |
                        Q(client__in=self.user.get_clients_cache())
                    )
                ).distinct().values_list('pk', flat=True)
        
            public_questions_subjects = []
            public_questions_subjects = Subject.objects.get_public_questions_subjects(self.get_filters()[3], request_subject).values_list('pk', flat=True)
            subjects_list = list(client_subjects) + list(public_questions_subjects)

            cache.set(CACHE_KEY, set(subjects_list), 4 * 60 * 60)
        
        return Subject.objects.filter(pk__in=cache.get(CACHE_KEY)).order_by('-client', 'name')

class SubjectTreeDetailView(APIView, SubjectTreeQuerysetMixin):
    def get_object(self, model, pk):
        try:
            return model.objects.get(pk=pk)
        except model.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
    
    def subject_tree(self, obj):
        public_topics_pks = Topic.objects.get_public_questions_topics_by_subject(obj).values_list(
            'pk', flat=True
        )
        
        client_topics_pks = Topic.objects.annotate(
            has_questions=Exists(
                Question.objects.filter(
                    subject=OuterRef('pk'),
                    is_abstract=False,
                    coordinations__unity__client__in=self.user.get_clients_cache()
                )
            )
        ).filter(
            has_questions=True,
            main_topic__isnull=True,
            theme__isnull=True,
            subject=obj,
        ).distinct().values_list('pk', flat=True)

        topics_db = Topic.objects.filter(pk__in=set(list(public_topics_pks) + list(client_topics_pks)))
        topics = [
            {
                'id': f'{topic.pk}',
                'text': topic.name,
                'leaf': True,
                'model': 'Topic',
                'subject_name': obj.name,
            }
            for topic in topics_db
        ]

        #####
        
        public_main_topics = MainTopic.objects.get_public_questions_main_topics_by_subject(obj).values_list(
            'pk', flat=True
        )
        client_main_topics = MainTopic.objects.filter(
            topic__questions__subject=obj,
            topic__subject=obj,
            topic__questions__coordinations__unity__client__in=self.user.get_clients_cache()
        ).distinct().values_list('pk', flat=True)
        
        main_topics_db = MainTopic.objects.filter(pk__in=set(list(public_main_topics) + list(client_main_topics)))
        main_topics = [
            {
                'id': f'{main_topic.pk}',
                'text': main_topic.name,
                'leaf': False,
                'model': 'MainTopic',
                'subject_name': obj.name,
            }
            for main_topic in main_topics_db
        ]

        #####

        themes_db = Theme.objects.filter(
            Q(maintopic__in=main_topics_db) |
            Q(topic__in=topics_db)
        ).distinct()

        themes = []
        for theme in themes_db:
            themes.append(
                {
                    'id': f'{theme.pk}',
                    'text': theme.name,
                    'leaf': False,
                    'model': 'Theme',
                    'subject_name': obj.name,
                }
            )

        return *themes, *main_topics, *topics

    def theme_tree(self, obj):
        public_topics_pks = Topic.objects.get_public_questions_topics_by_theme(obj).values_list(
            'pk', flat=True
        )
        
        client_topics_pks = Topic.objects.annotate(
            has_questions=Exists(
                Question.objects.filter(
                    subject=OuterRef('pk'),
                    is_abstract=False,
                    coordinations__unity__client__in=self.user.get_clients_cache()
                )
            )
        ).filter(
            has_questions=True,
            main_topic__isnull=True,
            theme=obj,
        ).distinct().values_list('pk', flat=True)

        topics = [
            {
                'id': f'{topic.pk}',
                'text': topic.name,
                'leaf': True,
                'model': 'Topic',
                'subject_name': topic.subject.name,
            }
            for topic in Topic.objects.filter(
                pk__in=set(list(public_topics_pks) + list(client_topics_pks))
            ).select_related('subject')
        ]

        public_main_topics = MainTopic.objects.get_public_questions_main_topics_by_theme(obj).values_list(
            'pk', flat=True
        )

        client_main_topics = MainTopic.objects.filter(
            theme=obj,
            topic__questions__coordinations__unity__client__in=self.user.get_clients_cache()
        ).distinct().values_list('pk', flat=True)

        main_topics = [
            {
                'id': f'{main_topic.pk}',
                'text': main_topic.name,
                'leaf': False,
                'model': 'MainTopic',
                'subject_name': main_topic.topic_set.all().first().subject.name,
            }
            for main_topic in MainTopic.objects.filter(
                pk__in=set(list(public_main_topics) + list(client_main_topics))
            )
        ]

        return *main_topics, *topics

    def main_topic_tree(self, obj):
        public_topics_pks = Topic.objects.get_public_questions_topics_by_main_topic(obj).values_list(
            'pk', flat=True
        )
        
        client_topics_pks = Topic.objects.annotate(
            has_questions=Exists(
                Question.objects.filter(
                    subject=OuterRef('pk'),
                    is_abstract=False,
                    coordinations__unity__client__in=self.user.get_clients_cache()
                )
            )
        ).filter(
            has_questions=True,
            main_topic=obj,
        ).distinct().values_list('pk', flat=True)

        topics = [
            {
                'id': f'{topic.pk}',
                'text': topic.name,
                'leaf': True,
                'model': 'Topic',
                'subject_name': topic.subject.name,
            }
            for topic in Topic.objects.filter(
                pk__in=set(list(public_topics_pks) + list(client_topics_pks))
            )
        ]

        return topics

    def get_tree(self, model, obj):
        if model == 'Subject':
            return self.subject_tree(obj)
        elif model == 'Theme':
            return self.theme_tree(obj)
        elif model == 'MainTopic':
            return self.main_topic_tree(obj)

    def get(self, request, pk, format=None):
        app = request.GET.get('app', None)
        cls_name = request.GET.get('cls', None)
        if not app or not cls_name:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        CACHE_KEY = f'FILTRED_TREE-{self.get_cache_key()}-{cls_name}-{pk}'
        
        if not cache.get(CACHE_KEY): 
            obj = self.get_object(apps.get_model(app, cls_name), pk)
            commons = self.get_tree(cls_name, obj)
            serializer = CommonTreeSerializer(
                [
                    CommonTreeModel(
                        id=q['id'],
                        text=q['text'],
                        leaf=q['leaf'],
                        model=q['model'],
                        subject_name=q['subject_name'],
                    )
                    for q in commons
                ],
                many=True,
            )
            
            cache.set(CACHE_KEY, serializer.data, 4 * 60 * 60)

        return Response(cache.get(CACHE_KEY))
    

class SubjectRelationtList(LoginRequiredMixin, CheckHasPermission,  ListView):
    model = SubjectRelation
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'subjects.view_subjectrelation'
    paginate_by = 30
    queryset = SubjectRelation.objects.all()
    template_name = "dashboard/subjects/subject_relation_list.html"


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context

    def get_queryset(self, **kwargs):
        queryset = super().get_queryset()
        
        queryset = queryset.filter(
            client__in=self.request.user.get_clients_cache()
        ).distinct().order_by('-created_at')

        return queryset

class SubjectRelationCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = SubjectRelation
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'subjects.add_subjectrelation'
    form_class = SubjectRelationCreationForm
    template_name = "dashboard/subjects/subject_relation_create_update.html"
    success_message = "Relação entre disciplinas cadastrada com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse('subjects:subjects_relation_list')

    def get_context_data(self, **kwargs):    
        context = super().get_context_data(**kwargs)

        return context
    
class SubjectRelationUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = SubjectRelation
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'subjects.change_subjectrelation'
    form_class = SubjectRelationForm
    template_name = "dashboard/subjects/subject_relation_create_update.html"
    success_message = "Relação entre disciplinas atualizada com sucesso!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse('subjects:subjects_relation_list')

    def get_context_data(self, **kwargs):    
        context = super().get_context_data(**kwargs)

        return context
    
class SubjectRelationDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = SubjectRelation
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'subjects.delete_subjectrelation'
    success_message = "Relação entre disciplinas removida com sucesso!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('subjects:subjects_relation_list')
        


subjects_list = SubjectList.as_view()
subjects_create = SubjectCreateView.as_view()
subjects_update = SubjectUpdateView.as_view()
subjects_delete = SubjectDeleteView.as_view()

subject_list_api = SubjectListView.as_view()
subject_study_material_list_api = SubjectStudyMaterialListAPIView.as_view()