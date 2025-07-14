from django import forms
from fiscallizeon.integrations.models import Integration
from django.core.exceptions import ValidationError

class IntegrationForm(forms.ModelForm):
    class Meta:
        model = Integration
        fields = ['erp', 'token', 'school_code']

                
    def clean(self):
        data = self.cleaned_data
        if data['erp'] == Integration.ISCHOLAR and not data['school_code']:
            self.add_error('school_code', f'O código da escola é obrigatório para esta integração')