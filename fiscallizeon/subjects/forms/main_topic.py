from django import forms
from fiscallizeon.subjects.models import MainTopic

class MainTopicForm(forms.ModelForm):
    class Meta:
        model = MainTopic
        fields = ['name', 'theme'] 
