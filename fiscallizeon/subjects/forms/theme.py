from django import forms
from fiscallizeon.subjects.models import Theme

class ThemeForm(forms.ModelForm):
    class Meta:
        model = Theme
        fields = ['name', 'client', 'created_by']