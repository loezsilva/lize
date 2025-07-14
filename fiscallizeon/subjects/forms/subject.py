from django import forms
from django.db.models import Q

from fiscallizeon.subjects.models import Subject, SubjectRelation

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = "__all__"
        exclude = ('created_by', 'client', 'knowledge_area')

    def __init__(self, user, *args, **kwargs):
        super(SubjectForm, self).__init__(*args, **kwargs)
        
        queryset = Subject.objects.filter(
            Q(
                Q(parent_subject__isnull=True) &
                Q(client__isnull=True)
            ) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client__in=user.get_clients_cache())
            ) | 
            Q(client__isnull=True)
        ).distinct()
        
        if hasattr(self, 'instance'):
            queryset = queryset.exclude(pk=self.instance.pk)
            
        self.fields['parent_subject'].queryset = queryset
        
class SubjectRelationForm(forms.ModelForm):
    class Meta:
        model = SubjectRelation
        exclude = ('client', 'created_by', )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        queryset = user.get_availables_subjects()
        
        self.fields['subjects'].queryset = queryset
        
class SubjectRelationCreationForm(forms.ModelForm):
    class Meta:
        model = SubjectRelation
        fields = "__all__"

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        queryset = user.get_availables_subjects()
        
        self.fields['subjects'].queryset = queryset