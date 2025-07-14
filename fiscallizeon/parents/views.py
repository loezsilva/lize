from django.contrib.auth.mixins import LoginRequiredMixin 
from django.shortcuts import get_object_or_404, redirect
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, ListView
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.students.models import Student
from .models import Parent
from django.contrib import messages
from .forms import UserCreationParentForm
from django.conf import settings
from fiscallizeon.applications.views import ApplicationStudentListMixin
from django.urls import reverse, reverse_lazy
# Create your views here.

class ParentSignUpView(SuccessMessageMixin, CreateView):
	template_name='accounts/parent_signup.html'
	form_class = UserCreationParentForm
	parent = None
	success_message = "Usuário criado com sucesso, agora faça login com seu email e a senha que você definiu."
	success_url = reverse_lazy('core:dashboard_parent')

	def dispatch(self, request, *args, **kwargs):
		try:
			self.parent = Parent.objects.get(hash=self.kwargs['hash'])
			if not self.parent.hash_is_valid:
				messages.warning(request, "Esse link expirou, ou você já possui um usuário, tente fazer login com seu e-mail e senha ou entre em contato com o suporte.")
				return redirect(reverse('core:dashboard_parent'))

		except Exception as e:
			messages.error(request, "Esse link expirado ou inexistente, entre em contato com o suporte.")
			return redirect(reverse('core:dashboard_parent'))

		return super().dispatch(request, *args, **kwargs)

	def form_valid(self, form):
		user = form.save()

		user.set_password(form.cleaned_data['password2'])
		user.save()

		self.parent.user = user
		self.parent.save(skip_hooks=True)

		messages.success(self.request, self.success_message)
		return redirect(reverse('core:dashboard_parent'))

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context["parent"] = self.parent
		return context

class ChildrenApplicationsStudentListView(LoginRequiredMixin, CheckHasPermission, ApplicationStudentListMixin, ListView):
    template_name = 'parents/applications_student_list.html'
    required_permissions = [settings.PARENT]
    queryset = ApplicationStudent.objects.all()
    student = None
    paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and user.user_type == settings.PARENT:
            if not self.kwargs['pk'] in user.parent.students.all().values_list('pk', flat=True):
                messages.error(request, "Você não tem permissão para realizar esta ação.")
                return redirect('core:dashboard_parent')
        
        self.student = get_object_or_404(Student, pk=self.kwargs['pk'])
	
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        return super().get_queryset(student=self.student).order_by('-application__date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['is_external'] = True
        context['object'] = self.student
        
        return context
	