from django.shortcuts import render
from django.views.generic import TemplateView

# Create your views here.
class TextualDemoView(TemplateView):
    template_name = "textual_demo.html"

    
