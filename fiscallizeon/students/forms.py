from fiscallizeon.students.models import Student
from django import forms

from fiscallizeon.classes.models import Grade
from fiscallizeon.clients.models import SchoolCoordination, Unity
from fiscallizeon.accounts.models import User, CustomGroup
from django.core.exceptions import ValidationError
import re

class ImportForm(forms.Form):

    def __init__(self, user, *args, **kwargs):
        super(ImportForm, self).__init__(*args, **kwargs)

        has_matriz = Unity.objects.filter(
            unity_type=Unity.PARENT,
            coordinations__in=user.get_coordinations()
        ).exists()

        if has_matriz:
            self.fields['coordination'].queryset = SchoolCoordination.objects.filter(
                unity__client__in=user.get_clients()
            ).distinct()
        else:
            self.fields['coordination'].queryset = user.get_coordinations().distinct()

    # class_name = forms.CharField(required=True, label='Nome da turma')
    students_file = forms.FileField(required=True, label='Arquivo CSV')
    grade = forms.ModelChoiceField(required=False, label='Ano/Série', queryset=Grade.objects.all())
    coordination = forms.ModelChoiceField(required=True, label='Coordenação', queryset=SchoolCoordination.objects.all())
    replace_old_classes = forms.BooleanField(required=False, initial=False, label='Remover alunos de turmas anteriores')

class ImportFormV2(forms.Form):

    def __init__(self, user, *args, **kwargs):
        return super().__init__(*args, **kwargs)

    students_file = forms.FileField(required=True, label='Arquivo CSV')
    replace_old_classes = forms.BooleanField(required=False, initial=False, label='Remover alunos de turmas anteriores')

class StudentForm(forms.ModelForm):
    username = forms.CharField(label='Usuário',max_length=100, required=False)
    password = forms.CharField(label='Nova Senha',max_length=128, required=False)
    confirmation_password = forms.CharField(label='Confirmar Nova Senha',max_length=128, required=False)
    must_change_password = forms.BooleanField(label='Deve mudar a senha no próximo acesso',required=False)
    redirect = forms.CharField(widget=forms.HiddenInput(), required=False)
    custom_groups = forms.ModelMultipleChoiceField(label="Grupos de permissão", queryset=CustomGroup.objects.all(), required=False)

    def __init__(self, user, is_update, *args, **kwargs):
        
        super(StudentForm, self).__init__(*args, **kwargs)
        
        self.user = user
        self.is_update = is_update
        
        custom_groups_segment = CustomGroup.objects.filter(
            client__in=user.get_clients_cache(),
            segment='student'
        ).distinct()
        
        self.fields['custom_groups'].queryset = custom_groups_segment
        
        if self.is_update and self.instance.user:
            self.fields['custom_groups'].initial = self.instance.user.custom_groups.all()
        else:
            self.fields['custom_groups'].initial = custom_groups_segment.filter(default=True)
    
    class Meta:
        model = Student
        fields = ('name', 'enrollment_number', 'email','birth_of_date', 'username', 'password', 'confirmation_password', 'must_change_password', 'responsible_email', 'responsible_email_two', 'responsible_email_three', 'responsible_email_four',  'redirect', 'is_atypical')
        exclude = ('user', 'client')
        

    def clean(self):
        self.cleaned_data = super().clean()

        client = self.user.get_clients()[0]

        if (
            Student.objects.using('default')
            .filter(client=client, enrollment_number=self.cleaned_data.get('enrollment_number'))
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            self.add_error(
                'enrollment_number',
                ValidationError(f'Já existe um aluno com essa matrícula ({self.cleaned_data.get("enrollment_number")}).')
            )

        if (
            Student.objects.using('default')
            .filter(client=client, email=self.cleaned_data.get('email'))
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            self.add_error(
                'email',
                ValidationError(f'Já existe um aluno com esse e-mail ({self.cleaned_data.get("email")}).'),
            )

        if self.cleaned_data.get("username"):
            if self.instance.user:
                if (
                    User.objects.using('default')
                    .filter(username=self.cleaned_data.get('username'))
                    .exclude(pk=self.instance.user.pk)
                    .exists()
                ):
                    self.add_error(
                        'username',
                        ValidationError(
                            f'Já existe um aluno com esse username ({self.cleaned_data.get("username")}).'
                        ),
                    )
            else:
                if self.cleaned_data.get('username') and (
                    User.objects.using('default').filter(username=self.cleaned_data.get('username')).exists()
                ):
                    self.add_error(
                        'username',
                        ValidationError(
                            f'Já existe um aluno com esse username ({self.cleaned_data.get("username")}).'
                        ),
                    )

        must_change_password = self.cleaned_data.get('must_change_password')
        password = self.cleaned_data.get('password')
        confirmation_password = self.cleaned_data.get('confirmation_password')

        if not must_change_password:
            if password and confirmation_password:  
                if len(password) & len(confirmation_password) < 8:
                    self.add_error('password', ValidationError("Sua senha precisa conter pelo menos 8 caracteres"))
                if len(re.findall(r"[a-z]", password)) < 1:
                    self.add_error('password', ValidationError("Sua senha precisa conter letras minusculas"))
                if len(re.findall("['`()_><;:!~@#$%^&+=]",password)) < 1:
                    self.add_error('password', ValidationError("Sua senha precisa conter caracteres especiais"))   

        if password != confirmation_password:
            self.add_error('password', ValidationError("As senhas não conferem"))

        return self.cleaned_data


class UpdateEnrollmentsForm(forms.Form):
    students_file = forms.FileField(required=True, label='Arquivo CSV')
