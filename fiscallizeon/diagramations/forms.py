from django import forms
from django.db.models import Q

from fiscallizeon.diagramations.models import DiagramationRequest
from fiscallizeon.subjects.models import Subject

class DiagramationRequestForm(forms.ModelForm):
    class Meta:
        model = DiagramationRequest
        fields = "__all__"
        exclude = ("status", "created_by", )

    def __init__(self, user, *args, **kwargs):
        super(DiagramationRequestForm, self).__init__(*args, **kwargs)
        self.fields['subjects'].queryset = Subject.objects.filter(
            Q(
                Q(client__isnull=True) |
                Q(client__in=user.get_clients_cache())
            )
        )

        if user.client_use_only_own_subjects:
            self.fields['subjects'].queryset = self.fields['subjects'].queryset.exclude(
                client__isnull=True
            )

        