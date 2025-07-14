
import uuid

from django.urls import reverse
from django.conf import settings
from django.db.models import Q, F
from django.contrib import messages
from django.views.generic import ListView
from django.views.generic.base import RedirectView
from django.http.response import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect

from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.classes.models import Grade
from fiscallizeon.subjects.models import Subject, Topic
from django.contrib.auth.mixins import LoginRequiredMixin

from fiscallizeon.questions.models import Question, QuestionOption


class PublicQuestionList(LoginRequiredMixin, CheckHasPermission, ListView):
    model = Question
    required_permissions = [settings.TEACHER, ]
    paginate_by = 20
    template_name = "dashboard/public_questions/public_question_list.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_public_questions:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('applications:applications_list'))

        return super(PublicQuestionList, self).dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super(PublicQuestionList, self).get_context_data(**kwargs)
        context["q_enunciation"] = self.request.GET.get("q_enunciation", "")
        context["q_subject"] = self.request.GET.getlist("q_subject", "")
        context["q_level"] = self.request.GET.getlist("q_level", "")
        context["q_board"] = self.request.GET.getlist("q_board", "")
        context["q_topic"] = self.request.GET.getlist("q_topic", "")

        context['q_created_by_myself'] = self.request.GET.get('q_created_by_myself', "")

        list_filters = [context['q_enunciation'], context["q_subject"], context["q_level"], context['q_created_by_myself']]
        
        context['count_filters'] = len(list_filters) - list_filters.count("")

        context['subjects'] = Subject.objects.filter(
            Q(parent_subject__isnull=True) |
            Q(client__isnull=True) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client__in=self.request.user.get_clients_cache())
            )
        ).order_by('created_at').distinct()

        context["boards"] = list(
            set(list(Question.objects.filter(
                is_public=True,
                institution__isnull=False,
            ).exclude(
                institution=""
            ).values_list("institution", flat=True)))
        )

        context["topics"] = Topic.objects.filter(
            questions__in=self.get_queryset()
        ).distinct()

        context['is_popup'] = self.request.GET.get('is_popup', "")
        context['q_search_alternative_text'] = self.request.GET.get("q_search_alternative_text", "")

        return context


    def get_queryset(self, **kwargs):
        queryset = Question.objects.filter(
            Q(
				is_public=True,
                source_question__isnull=True,
                is_abstract=False,
			)
        ).distinct().order_by('-created_at')

        already_copied = Question.objects.filter(
            source_question__in=queryset,
            created_by=self.request.user,
            is_public=False
        ).values("source_question__pk")

        queryset = queryset.exclude(
            pk__in=already_copied
        ).distinct()

        # user = self.request.user

        # if user.user_type == settings.TEACHER:
        #     parent_subjects = user.inspector.subjects.all().values_list("parent_subject", flat=True)
            
        #     queryset = queryset.filter(
        #         Q(subject__in=user.inspector.subjects.all()) |
        #         Q(subject__in=parent_subjects) |
        #         Q(created_by=user)
        #     )

        q_enunciation = self.request.GET.get("q_enunciation", None)
        q_search_alternative_text = self.request.GET.get("q_search_alternative_text", None)

        if q_enunciation and q_search_alternative_text:
            queryset = queryset.filter(
                Q(
                    Q(enunciation__icontains=q_enunciation) |
                    Q(alternatives__text__icontains=q_enunciation)
                )
            )
        elif q_enunciation:
            queryset = queryset.filter(
                Q(enunciation__icontains=q_enunciation)
            )

        q_subject = self.request.GET.getlist("q_subject", None)
        if q_subject:
            queryset = queryset.filter(
                Q(subject__in=q_subject)
            )

        q_level = self.request.GET.getlist("q_level", None)
        if q_level:
            queryset = queryset.filter(
                Q(level__in=q_level)
            )

        q_board = self.request.GET.getlist("q_board", None)
        if q_board:
            queryset = queryset.filter(
                Q(institution__in=q_board)
            )

        q_topic = self.request.GET.getlist("q_topic", None)
        if q_topic:
            queryset = queryset.filter(
                Q(topics__in=q_topic)
            )

        return queryset



class PublicQuestionCopy(LoginRequiredMixin, CheckHasPermission, RedirectView):
    required_permissions = [settings.TEACHER, ]

    def dispatch(self, request, *args, **kwargs):
        question = get_object_or_404(Question, pk=self.kwargs.get('pk'))

        already_copied = Question.objects.filter(
            source_question=question,
            created_by=request.user,
            is_public=False
        )

        if not question.is_public or already_copied:
            messages.warning(request, 'Essa questão não pode ser/ou já foi copiada para seu banco')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(PublicQuestionCopy, self).dispatch(request, *args, **kwargs)

    def get_redirect_url(self, *args, **kwargs):   
        question = get_object_or_404(Question, pk=self.kwargs.get('pk'))

        copy_question = Question.objects.get(pk=question.pk)
        copy_question.pk = uuid.uuid4()
        copy_question.source_question = question
        copy_question.is_public = False
        copy_question.created_by = self.request.user
        copy_question.save()

        copy_question.topics.set(question.topics.all())
        copy_question.coordinations.set(self.request.user.get_coordinations())
        copy_question.abilities.set(question.abilities.all())
        copy_question.competences.set(question.competences.all())

        if question.category == Question.CHOICE:
            for index, alternative in enumerate(question.alternatives.all().order_by('created_at'), 1):
                QuestionOption.objects.create(
                    question=copy_question,
                    text=alternative.text,
                    is_correct=alternative.is_correct,
                    index=index,
                )

        messages.success(self.request, "Questão copiada com sucesso, faça as alterações que achar necessárias.")
        
        return reverse('questions:questions_update', kwargs={"pk":copy_question.pk})

public_questions_list = PublicQuestionList.as_view()
public_questions_copy = PublicQuestionCopy.as_view()

