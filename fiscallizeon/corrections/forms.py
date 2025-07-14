import re
from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import CorrectionDeviation, CorrectionCriterion

class CorrectionDeviationForm(forms.ModelForm):
    class Meta:
        model = CorrectionDeviation
        fields = "__all__"
        
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['criterion'].queryset = CorrectionCriterion.objects.filter(
            Q(text_correction__client=user.client) |
            Q(text_correction__client__isnull=True)
        )
        
    