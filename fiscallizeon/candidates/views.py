from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login

from django.views.generic.edit import CreateView
from fiscallizeon.candidates.forms import Candidate
from django.views.generic import TemplateView, FormView
from django.contrib.messages.views import SuccessMessageMixin
from fiscallizeon.candidates.forms import CandidateForm, SubscribeInClassForm

from fiscallizeon.clients.models import Client
from fiscallizeon.classes.models import SchoolClass
from django.shortcuts import get_object_or_404


class CandidateCreateView(SuccessMessageMixin, CreateView):
    template_name = 'candidates/candidate_create.html'
    model = Candidate
    form_class = CandidateForm
    success_message = 'Cadastro realizado com sucesso! Utilize seu email e a senha "1234" para acessar sua conta.'

    def get_success_url(self):
        return reverse('accounts:login')

    def get_context_data(self, **kwargs):
        context = super(CandidateCreateView, self).get_context_data(**kwargs)

        context["client"] = get_object_or_404(Client.objects.all(), pk=self.kwargs.get("pk"))

        return context

candidate_create_view = CandidateCreateView.as_view()

# class SubscribeInClassView(CheckHasPermission, TemplateView):
#     template_name = 'candidates/subscribe_in_class.html'
#     model = SchoolClass

#     def get_context_data(self, **kwargs):
#         context = super(SubscribeInClassView, self).get_context_data(**kwargs)
#         context['form'] = SubscribeInClassForm(data=self.request.POST) if self.request.POST else SubscribeInClassForm()
#         context['object'] = SchoolClass.objects.get(
#             slug=self.kwargs.get('slug')
#         )

#         return context
    
#     def post(self, request, *args, **kwargs):
#         form = SubscribeInClassForm(data=self.request.POST)
        
#         if form.is_valid():
#             form.save()
#             messages.success(request, f'Conta criada com sucesso! Entre no seu perfil e tenha acesso aos simulados!')
#             return HttpResponseRedirect(reverse('core:redirect_dashboard'))
#         else:
#             messages.error(request, f'Ocorreu algum problema, verifique as informações abaixo e tente novamente!')
#             return self.render_to_response(self.get_context_data(form=form))
        

class SubscribeInClassView(TemplateView, FormView):
    template_name = 'candidates/subscribe_in_class.html'
    form_class = SubscribeInClassForm
    model = SchoolClass

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = SchoolClass.objects.get(slug=self.kwargs.get('slug'))
        return context

    def form_valid(self, form):
        form.save()
        user = authenticate(self.request, username=form.cleaned_data["username"], password=form.cleaned_data["password"])
        login(self.request, user)
        messages.success(self.request, f'Conta criada com sucesso! Aproveite agora os simulados ENEM e nosso Simulador SISU!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, f'Ocorreu algum problema, verifique as informações abaixo e tente novamente!')
        return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse('core:redirect_dashboard')
            
subscribe_class = SubscribeInClassView.as_view()