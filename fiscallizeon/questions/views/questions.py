import json
from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from django.contrib import messages
from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404, render
from json.encoder import JSONEncoder
from itertools import chain
from fiscallizeon.clients.models import QuestionTag

from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.classes.models import Grade
from fiscallizeon.corrections.models import CorrectionFileAnswer, CorrectionTextualAnswer
from fiscallizeon.subjects.models import Subject
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.base import TemplateView

from fiscallizeon.questions.models import BaseText, Question, QuestionHistoryTags
from fiscallizeon.exams.models import ExamTeacherSubject, ExamQuestion, StatusQuestion
from fiscallizeon.questions.forms import QuestionBaseTextSimpleForm, QuestionForm, QuestionOptionFormSet, QuestionUpdateForm

from fiscallizeon.questions.serializers.questions import QuestionSerializerSimple
from fiscallizeon.notifications.models import Notification
from fiscallizeon.notifications.functions import get_and_create_notifications
from django.core.exceptions import ValidationError

class QuestionList(LoginRequiredMixin, CheckHasPermission, ListView):
    model = Question
    required_permissions = [settings.COORDINATION, settings.TEACHER, ]
    paginate_by = 20
    permission_required = 'questions.view_question'
    template_name = "dashboard/questions/question_list.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_exam_elaboration:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(QuestionList, self).dispatch(request, *args, **kwargs)


    def get_context_data(self, **kwargs):
        context = super(QuestionList, self).get_context_data(**kwargs)
        context["q_enunciation"] = self.request.GET.get("q_enunciation", "")
        context["q_category"] = self.request.GET.getlist("q_category", "")
        context["q_subject"] = self.request.GET.getlist("q_subject", "")
        context["q_level"] = self.request.GET.getlist("q_level", "")
        context['q_grade'] = self.request.GET.getlist('q_grade', "")
        context['q_created_by_myself'] = self.request.GET.get('q_created_by_myself', "")
        context['q_ability_code'] = self.request.GET.get('q_ability_code', "")
        context['q_competence_code'] = self.request.GET.get('q_competence_code', "")

        list_filters = [context['q_enunciation'], context["q_category"], context["q_subject"], context["q_level"], context['q_grade'], context['q_created_by_myself'], context['q_ability_code'], context['q_competence_code']]
        
        context['count_filters'] = len(list_filters) - list_filters.count("")

        context['subjects'] = self.request.user.inspector.subjects.all() if self.request.user.user_type == "teacher" else Subject.objects.filter(
            Q(parent_subject__isnull=True) |
            Q(client__isnull=True) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client__in=self.request.user.get_clients_cache())
            )
        ).order_by('created_at').distinct('created_at', 'pk')
        
        context["grades"] = Grade.objects.filter(
            question__subject__in=context['subjects']
        ).distinct('name', 'pk').order_by('name')

        context['is_popup'] = self.request.GET.get('is_popup', "")
        context['q_search_alternative_text'] = self.request.GET.get("q_search_alternative_text", "")

        return context


    def get_queryset(self, **kwargs):
        from fiscallizeon.accounts.models import User
        user = self.request.user
        
        users_coordination = User.objects.filter(
            Q(
                Q(coordination_member__coordination__in=user.get_coordinations_cache()) |
                Q(inspector__coordinations__in=user.get_coordinations_cache())
            )
        )
        queryset = Question.objects.filter(
            Q(
				created_by__in=users_coordination,
                is_public=False,
                is_abstract=False,
			)
        ).order_by('-created_at').distinct()

        if user.user_type == settings.TEACHER:
            queryset = queryset.filter(
                Q(subject__in=user.inspector.subjects.all()) |
                Q(created_by=user)
            )

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


        q_category = self.request.GET.getlist("q_category", None)
        if q_category:
            queryset = queryset.filter(
                Q(category__in=q_category)
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

        q_grade = self.request.GET.getlist("q_grade", None)
        if q_grade:
            queryset = queryset.filter(
                Q(grade__in=q_grade)
            )

        q_created_by_myself = self.request.GET.get("q_created_by_myself", None)
        if q_created_by_myself:
            queryset = queryset.filter(
                Q(created_by=user)
            )

        q_ability_code = self.request.GET.get("q_ability_code", None)
        if q_ability_code:
            queryset = queryset.filter(
                Q(abilities__code__icontains=q_ability_code)
            )
        
        q_competence_code = self.request.GET.get("q_competence_code", None)
        if q_competence_code:
            queryset = queryset.filter(
                Q(competences__code__icontains=q_competence_code)
            )
            
        return queryset

class SelectQuestionToExamView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/questions/question_popup_response.html'
    required_permissions = [settings.TEACHER, settings.COORDINATION ]
    model = Question

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_exam_elaboration:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(SelectQuestionToExamView, self).dispatch(request, *args, **kwargs)


    def dispatch(self, request, *args, **kwargs):
        if self.get_object().is_public:
            messages.warning(request, 'Operação não permitida para esse tipo de questão')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(SelectQuestionToExamView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(SelectQuestionToExamView, self).get_context_data(**kwargs)
        context["question"] = QuestionSerializerSimple(self.object).data
        context["question"]["updated"] = False

        return context

class QuestionCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = Question
    required_permissions = [settings.COORDINATION, settings.TEACHER, ]
    form_class = QuestionForm
    # template_name = "dashboard/questions/question_create_update.html"
    permission_required = 'questions.add_question'
    success_message = "Questão cadastrada com sucesso!"

    def get_template_names(self):
        if self.request.GET.get('v') == '2':
            return 'dashboard/questions/question_create_update_new.html'
        elif self.request.GET.get('v') == 'new':
            return 'dashboard/questions/question_create_update_v2.html'
        return 'dashboard/questions/question_create_update.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_exam_elaboration:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(QuestionCreateView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(QuestionCreateView, self).get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

    def get_success_url(self):
        get_and_create_notifications(view=self, trigger=Notification.AFTER_CREATE)
        return reverse('questions:questions_list')

    def get_object(self):
        return Question.objects.using('default').get(pk=self.kwargs.get('pk'))

    def form_valid(self, form):
        ctx = self.get_context_data()
        question_option_formset = ctx['question_option_formset']
        # exam_teacher_pk = self.request.GET.get("exam_teacher", None)
        exam_question = ""

        if not form.instance.category in [Question.CHOICE, Question.SUM_QUESTION]:
            question_option_formset.min_num = 0
        
        if self.request.user.client and self.request.user.questions_configuration and question_option_formset.is_valid() and form.instance.category ==  Question.CHOICE: 
            corretas = [questao for questao in question_option_formset.cleaned_data if questao.get('is_correct', False)]
            client_has_module_disable_multiple_correct_options = self.request.user.client_can_disable_multiple_correct_options
            
            can_not_add_multiple_correct_options_question = True
            if self.request.user.questions_configuration:
                can_not_add_multiple_correct_options_question = self.request.user.questions_configuration.can_not_add_multiple_correct_options_question
            
            if client_has_module_disable_multiple_correct_options and can_not_add_multiple_correct_options_question and len(corretas) > 1:
                form.add_error(None, "Não é possível cadastrar duas alternativas corretas para uma questão.")


        if question_option_formset.is_valid() and form.is_valid():
            self.object = form.save()
            self.object.created_by = self.request.user
            self.object.save()
            instances = question_option_formset.save(commit=False)

            
            for index, instance in enumerate(instances, start=1):                
                instance.question = self.object
                instance.question.created_by = self.request.user
                instance.index = index
                instance.save()


            if not self.request.POST.get("is_popup", False):
                return HttpResponseRedirect(self.get_success_url())
            else:
                # if exam_teacher_pk:
                #     exam_teacher = ExamTeacherSubject.objects.get(pk=exam_teacher_pk)
                #     exam_question = ExamQuestion.objects.create(
                #         question=self.object,
                #         exam=exam_teacher.exam,
                #         exam_teacher_subject=exam_teacher,
                #         order=ExamQuestion.objects.filter(
                #             exam=exam_teacher.exam,
                #             exam_teacher_subject=exam_teacher
                #         ).count()
                #     )
                context = {}
                context["question"] = QuestionSerializerSimple(self.object).data
                # context["question"]["id"] = str(exam_question.pk) if exam_question else ""
                context["question"]["updated"] = False

                return render(self.request, "dashboard/questions/question_popup_response.html", context)
        else:
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    erros = form.non_field_errors, 
                    question_option_formset=question_option_formset,
                    is_popup=self.request.POST.get("is_popup", False)
                )
            )

    def form_invalid(self, form):
        ctx = self.get_context_data(form=form)
        
        obligation_error = json.loads(form.errors.as_json())

        ctx['obligation_error'] = obligation_error
        ctx['is_popup'] = self.request.POST.get("is_popup", False)
        ctx['exam_teacher'] = self.request.POST.get("exam_teacher", "")
        
        return self.render_to_response(ctx)

    def get_context_data(self, **kwargs):
        ctx = super(QuestionCreateView, self).get_context_data(**kwargs)

        ctx['current_grade'] = ""
        ctx['current_knowledge_area'] = ""
        ctx['current_subject'] = ""
        ctx['current_selected_level'] = None
        ctx['tinymce_configs'] = JSONEncoder().encode(settings.TINYMCE_DEFAULT_CONFIG)
        
        if self.request.POST:
            ctx['form'] = QuestionForm(user=self.request.user, data=self.request.POST)
            ctx['question_option_formset'] = QuestionOptionFormSet(self.request.POST, prefix="question-option-form")
        else:
            coordinations = self.request.user.get_coordinations()
            exam_teacher_pk = self.request.GET.get("exam_teacher", None)

            if exam_teacher_pk:
                exam_teacher = ExamTeacherSubject.objects.get(pk=exam_teacher_pk)
                coordinations_exam = exam_teacher.exam.coordinations.all()
                coordinations = list(chain(coordinations, coordinations_exam))

                ctx['exam_teacher'] = str(exam_teacher_pk)
                ctx['current_grade'] = str(exam_teacher.grade.pk)
                ctx['current_subject'] = str(exam_teacher.teacher_subject.subject.pk)
                ctx['current_knowledge_area'] = str(exam_teacher.teacher_subject.subject.knowledge_area.pk)
                ctx['current_selected_level'] = str(exam_teacher.grade.level) if exam_teacher.grade else None

            ctx['form'] = QuestionForm(
                user=self.request.user, 
                initial={'coordinations': coordinations}
            )
            ctx['is_popup'] = self.request.GET.get("is_popup", False)
            ctx['question_option_formset'] = QuestionOptionFormSet(prefix="question-option-form")

        ctx['form_base_texts'] = QuestionBaseTextSimpleForm()
        ctx['base_texts'] = BaseText.objects.filter(pk__in=self.request.POST.getlist('base_texts'))

        return ctx

class QuestionUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = Question
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    form_class = QuestionUpdateForm
    permission_required = 'questions.change_question'
    # template_name = "dashboard/questions/question_create_update.html"
    success_message = "Questão atualizada com sucesso!"
    grade_level = None

    def get_template_names(self):
        if self.request.GET.get('v') == '2':
            return 'dashboard/questions/question_create_update_new.html'
        elif self.request.GET.get('v') == 'new':
            return 'dashboard/questions/question_create_update_v2.html'
        return 'dashboard/questions/question_create_update.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        
        if user and not user.is_anonymous and not user.client_has_exam_elaboration:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        if self.get_object().is_public:
            messages.warning(request, 'Operação não permitida para esse tipo de questão')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        
        return super(QuestionUpdateView, self).dispatch(request, *args, **kwargs)

    def get_object(self):
        return get_object_or_404(Question.objects.using('default'), pk=self.kwargs.get('pk'))
    
    def get_form_kwargs(self):
        kwargs = super(QuestionUpdateView, self).get_form_kwargs()
        if exam_question_id := self.request.GET.get('exam_question_id'):
            exam_question = ExamQuestion.objects.get(id=exam_question_id)
            self.grade_level = exam_question.exam_teacher_subject.grade.level
        else:
            question = self.get_object()
            if last_examquestion := question.examquestion_set.using('default').last():
                self.grade_level = last_examquestion.exam_teacher_subject.grade.level
            
        kwargs.update({'user': self.request.user})
        kwargs.update({'grade_level': self.grade_level })
        return kwargs

    def get_success_url(self):
        get_and_create_notifications(view=self, trigger=Notification.AFTER_UPDATE)
        return reverse('questions:questions_list')

    def form_valid(self, form):
        ctx = self.get_context_data()
        question_option_formset = ctx['question_option_formset']
        exam_question_id = ctx['exam_question_id']
        user = self.request.user
        
        if form.instance.category not in [Question.CHOICE, Question.SUM_QUESTION]:
            question_option_formset.min_num = 0

        if user.client and question_option_formset.is_valid() and form.instance.category ==  Question.CHOICE:
            
            corrects_alternatives = [questao for questao in question_option_formset.cleaned_data if questao.get('is_correct', False)]
            
            has_correct_alternative = len(corrects_alternatives)
            
            if teacher_obligation_configuration := user.client_teacher_configuration(level=self.grade_level):
                if form.instance.category == Question.CHOICE and teacher_obligation_configuration.template and not has_correct_alternative:
                    form.add_error('has_correct_alternative',  ValidationError("Você precisa adicionar gabarito a pelo menos uma alternativa!"))

            can_not_add_multiple_correct_options_question = True
                
            if user.questions_configuration:
                can_not_add_multiple_correct_options_question = user.questions_configuration.can_not_add_multiple_correct_options_question
            
            if can_not_add_multiple_correct_options_question and len(corrects_alternatives) > 1:
                form.add_error(None, "Não é possível cadastrar duas alternativas corretas para uma questão.")
        
        if form.is_valid():
            if not self.object.created_by:
                self.object.created_by = user
            question_instance = form.save()
            
            # Remove todas as disciplinas que não são da disciplina da questão
            # Demanda da task: https://app.clickup.com/t/86a910mfq
            if topics := question_instance.topics.all():
                # se tiver disciplina, filtra os tópicos pela disciplina atual
                if question_instance.subject:
                    question_instance.topics.set(
                        topics.filter(
                            subject=question_instance.subject,
                            grade=question_instance.grade
                        ).values_list('pk', flat=True)
                    )
                # se não tiver disciplina, limpa os tópicos
                else:
                    question_instance.topics.clear()
            
            if question_option_formset.is_valid():
                instances = question_option_formset.save(commit=False)
                
                # Retorna condição no dia 09/07/2025 para resolver o problema apontado na task:
                # https://app.clickup.com/t/86aa39hdr
                if not question_instance.can_be_updated(user=user): # Verifica se houve alteração nas alternativas, isso deve mostrar um erro no front e não pode salvar o form
                    formset_has_change = ['text' in formset.changed_data for formset in question_option_formset]
                    if any(formset_has_change): 
                        form.add_error('enunciation', 'Enunciado e texto das alternativas não podem ser alterados pois já foram utilizados em uma aplicação e possui respostas associadas.')
                        return self.form_invalid(form)

                if deleted_instances:= question_option_formset.deleted_objects:
                    for instance in deleted_instances:
                        instance.delete()

                for instance in instances:
                    instance.question = question_instance
                    instance.save()

                alternatives = question_instance.alternatives.using('default').all()
                
                for index, alternative in enumerate(alternatives, start=1):
                    alternative.index = index
                    alternative.save()

            req_tags = self.request.POST.get("selected_tags", "").split(',')
            
            if exam_question_id:
                exam_question = ExamQuestion.objects.get(id=exam_question_id)
                if last_status := exam_question.last_status_v2:
                    if last_status.status == StatusQuestion.CORRECTION_PENDING:
                        StatusQuestion.objects.create(
                            status=StatusQuestion.CORRECTED,
                            exam_question=exam_question,
                            user=self.request.user,
                        )

            if not req_tags == ['']:
                question_tag_history_instance = QuestionHistoryTags()
                question_tag_history_instance.question = question_instance
                question_tag_history_instance.record_id = question_instance.history.first().history_id
                question_tag_history_instance.note = self.request.POST.get('status_note', "")
                question_tag_history_instance.save()
                question_tag_history_instance.tags.set(QuestionTag.objects.filter(pk__in=req_tags))

            if not self.request.POST.get("is_popup", False):
                return HttpResponseRedirect(self.get_success_url())
            else:
                context = {}
                context["question"] = QuestionSerializerSimple(question_instance).data
                context["question"]["updated"] = True
                ctx['current_grade'] = ""
                ctx['current_knowledge_area'] = ""
                ctx['current_subject'] = ""
                ctx['current_selected_level'] = None
            
                return render(self.request, "dashboard/questions/question_popup_response.html", context)
            
        else:
            return self.render_to_response(self.get_context_data(form=form, erros = form.non_field_errors, question_option_formset=question_option_formset))

    def form_invalid(self, form):        
        ctx = self.get_context_data(form=form)
        print("entrou no form invalid", form.errors)

        obligation_error = json.loads(form.errors.as_json())

        ctx['obligation_error'] = obligation_error
        ctx['is_popup'] = self.request.POST.get("is_popup", False)
        ctx['exam_teacher'] = self.request.POST.get("exam_teacher", "")
        
        return self.render_to_response(ctx)

    def get_context_data(self, **kwargs):
        ctx = super(QuestionUpdateView, self).get_context_data(**kwargs)
        
        ctx['current_grade'] = ""
        ctx['current_knowledge_area'] = ""
        ctx['current_subject'] = ""
        ctx['current_selected_level'] = None
        ctx['question_editing'] = True
        ctx['exam_question_id'] = self.request.GET.get('exam_question_id', None)
        ctx['tinymce_configs'] = JSONEncoder().encode(settings.TINYMCE_DEFAULT_CONFIG)

        if self.request.POST:
            ctx['question_option_formset'] = QuestionOptionFormSet(self.request.POST, prefix="question-option-form", instance=self.get_object())
        else:
            ctx['is_popup'] = self.request.GET.get("is_popup", False)
            ctx['request_tags'] = self.request.GET.get("request_tags", False)
            ctx['tags'] = QuestionTag.objects.filter(
                Q(type=1),
                Q(
                    Q(client__in=self.request.user.get_clients_cache()) |
                    Q(client=None)
                )
            )
            ctx['tags_history'] = QuestionHistoryTags.objects.filter(question_id=self.get_object())
            ctx['question_option_formset'] = QuestionOptionFormSet(prefix="question-option-form", instance=self.get_object())

        if self.request.POST.get('base_texts'):
            ctx['base_texts'] = BaseText.objects.filter(pk__in=self.request.POST.getlist('base_texts'))
        else:
            ctx['base_texts'] = BaseText.objects.filter(pk__in=self.get_object().base_texts.all())

        ctx['form_base_texts'] = QuestionBaseTextSimpleForm()

        ctx['correction_textual_answer'] = CorrectionTextualAnswer.objects.filter(
            correction_criterion__text_correction=self.get_object().text_correction
        )
    
        ctx['correction_file_answer'] = CorrectionFileAnswer.objects.filter(
            correction_criterion__text_correction=self.get_object().text_correction
        )
        
        return ctx

class QuestionDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = Question
    required_permissions = [settings.COORDINATION, settings.TEACHER, ]
    success_message = "Questão removida com sucesso!"

    def dispatch(self, request, *args, **kwargs):
        from django.shortcuts import redirect
        user = request.user
        if user and not user.is_anonymous and not user.client_has_exam_elaboration:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        if self.get_object().is_public:
            messages.warning(request, 'Operação não permitida para esse tipo de questão')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        
        linked_question = ExamQuestion.objects.filter(question=self.get_object())
        if linked_question:
            messages.warning(request, 'Operação não permitida, questão está vinculado a um caderno')
            return HttpResponseRedirect(reverse('questions:questions_list'))
        
        if hasattr(user, 'inspector') and not self.get_object().can_be_updated(user):
            messages.warning(request, "Você não pode deletar a questão, pois a mesma já foi aprovada ou utilizada em algum caderno ou você não tem permissão para realizar esta ação.")
            return redirect('questions:questions_list')
    
        return super(QuestionDeleteView, self).dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(QuestionDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        
        get_and_create_notifications(view=self, trigger=Notification.AFTER_DELETE)
        
        return reverse('questions:questions_list')
    
class CreateAIQuestion(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'dashboard/questions/question_ai.html'
    required_permissions = [settings.COORDINATION, settings.INSPECTOR, settings.TEACHER]


questions_list = QuestionList.as_view()
questions_create = QuestionCreateView.as_view()
questions_update = QuestionUpdateView.as_view()
questions_delete = QuestionDeleteView.as_view()
questions_select = SelectQuestionToExamView.as_view()


