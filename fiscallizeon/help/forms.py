from django import forms
from .models import Tutorial

class HelpForm(forms.ModelForm):
    
    class Meta:
        fields = "__all__"
        model = Tutorial