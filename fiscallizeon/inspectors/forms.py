from django import forms
from django.utils import timezone
from fiscallizeon.accounts.models import User
from django.db.models import Q

from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.classes.models import SchoolClass, SchoolCoordination
from fiscallizeon.accounts.models import CustomGroup

class InspectorForm(forms.ModelForm):
    username = forms.CharField(label='Usuário',max_length=100, required=False)
    password = forms.CharField(label='Nova Senha',max_length=128, required=False)
    confirmation_password = forms.CharField(label='Confirmar Nova Senha',max_length=128, required=False)
    must_change_password = forms.BooleanField(label='Deve mudar a senha no próximo acesso',required=False)
    custom_groups = forms.ModelMultipleChoiceField(label="Grupos de permissão", queryset=CustomGroup.objects.all(), required=False)

    class Meta:
        model = Inspector
        fields = "__all__"
        exclude = ('user', )

    def __init__(self, user, is_update = False, create = None, *args, **kwargs):
        super(InspectorForm, self).__init__(*args, **kwargs)
        self.fields['coordinations'].required = True
        if is_update:
            self.fields['coordinations'].queryset = SchoolCoordination.objects.filter(
                Q(id__in=self.instance.coordinations.all()) |
                Q(id__in=user.get_coordinations_cache())
            ).distinct()
        else:
            self.fields['coordinations'].queryset = SchoolCoordination.objects.filter(
                id__in=user.get_coordinations_cache() 
            ).distinct()
        
        custom_groups_segment = CustomGroup.objects.filter(
            Q(
                Q(client__isnull=True) |
                Q(client__in=user.get_clients_cache())
            ),
            Q(segment='teacher')
        ).distinct()
        
        self.fields['custom_groups'].queryset = custom_groups_segment
        
        if create:
            if user.client.has_default_groups(segment='teacher'):
                self.fields['custom_groups'].initial = custom_groups_segment.filter(client__isnull=False, default=True)
            else:
                self.fields['custom_groups'].initial = custom_groups_segment.filter(default=True)
        elif self.instance.user:
            self.fields['custom_groups'].initial = self.instance.user.custom_groups.all()
        
        self.fields['subjects'].queryset = user.get_availables_subjects()

        self.fields['classes_he_teaches'].queryset = SchoolClass.objects.filter(
            coordination__in=user.get_coordinations(),
            school_year=timezone.now().year
        ).distinct()