from django.shortcuts import render
from django.views.generic import TemplateView, DetailView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Tutorial, TutorialCategory


class TutorialTemplateView(LoginRequiredMixin, TemplateView):
    template_name = 'help/tutoriais.html'
    
class TutorialDetailTemplateView(LoginRequiredMixin, DetailView):
    template_name = 'help/tutorial_detail.html'
    queryset = Tutorial.objects.all()
    model = Tutorial

class TutorialListView(LoginRequiredMixin, TemplateView):
    template_name = 'help/tutoriais_results.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search')
        return context
    
    
class TutorialCategoryDetailTemplateView(LoginRequiredMixin, DetailView):
    template_name = 'help/tutoriais_category_detail.html'
    queryset = TutorialCategory.objects.all()
    model = TutorialCategory