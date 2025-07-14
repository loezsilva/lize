import re
from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from django.db.models import Q

from fiscallizeon.clients.models import ClientTeacherObligationConfiguration, ClientQuestionsConfiguration, CoordinationMember, Partner, QuestionTag, SchoolCoordination, EducationSystem, ConfigNotification, Client
from fiscallizeon.accounts.models import CustomGroup, User
from fiscallizeon.inspectors.models import Inspector

class UserForm(forms.ModelForm):
    username = forms.CharField(label='Usuário',max_length=100, required=False)
    password = forms.CharField(label='Nova Senha',max_length=128, required=False)
    confirmation_password = forms.CharField(label='Confirmar Nova Senha',max_length=128, required=False)
    must_change_password = forms.BooleanField(label='Deve mudar a senha no próximo acesso',required=False)
    
    class Meta:
        model = User
        fields = "__all__"
        exclude = ("date_joined",  "password", "username", "is_active")

    def __init__(self, user, create = None, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        custom_groups_segment = CustomGroup.objects.filter(
            Q(
                Q(client__isnull=True) |
                Q(client__in=user.get_clients_cache())
            ),
            Q(segment='coordination')
        ).distinct()
        self.fields['custom_groups'].queryset = custom_groups_segment
        
        if create:
            if user.client.has_default_groups(segment='coordination'):
                self.fields['custom_groups'].initial = custom_groups_segment.filter(client__isnull=False, default=True)
            else:
                self.fields['custom_groups'].initial = custom_groups_segment.filter(default=True)

    def clean(self):
        cleaned_data = super(UserForm, self).clean()

        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        confirmation_password = cleaned_data.get('confirmation_password')
        must_change_password = cleaned_data.get('must_change_password')
        email = cleaned_data.get('email')

        check_username = User.objects.filter(username=username).exclude(username=self.instance.username)

        if username and check_username.exists():
            self.add_error('username', ValidationError(f'Usuario {username} já existe'))
        
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
            
        if email:
            try:
                inspector = Inspector.objects.get(email=email)
                self.instance = inspector.user
            except Inspector.DoesNotExist:
                check_email = User.objects.filter(email=email).exclude(email=self.instance.email)
                if check_email.exists():
                    self.add_error('email', ValidationError("Já existe um usuário com este e-mail."))
        return cleaned_data
    

class CoordinationMemberForm(forms.ModelForm):
    class Meta:
        model = CoordinationMember
        fields = "__all__"

    def __init__(self, user, *args, **kwargs):
        super(CoordinationMemberForm, self).__init__(*args, **kwargs)
        self.fields['coordination'].queryset = SchoolCoordination.objects.filter(
            unity__client__in=user.get_clients_cache()
        ).distinct()
class ClientTeacherObligationConfigurationForm(forms.ModelForm):
    class Meta:
        model = ClientTeacherObligationConfiguration
        fields = "__all__"

class ClientConfigNotificationsForm(forms.ModelForm):
    send_email_to_student_after_create = forms.BooleanField(label='Enviar email para o aluno após a criação', required=False)

    class Meta:
        model = ConfigNotification
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        first_notification = cleaned_data.get('first_notification')
        second_notification = cleaned_data.get('second_notification')
        
        if second_notification and (second_notification >= first_notification):
            self.add_error('second_notification', ValidationError('A primeira notificação deve vir antes da segunda.'))
        
        return cleaned_data

class ClientTagsForm(forms.ModelForm):
    class Meta:
        model = QuestionTag
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')

        if not name:
            self.add_error('name', ValidationError('Um nome precisa ser informado.'))
        
        return cleaned_data

class ClientQuestionsConfigurationForm(forms.ModelForm):
    class Meta:
        model = ClientQuestionsConfiguration
        fields = "__all__"


CoordinationMemberFormSet = inlineformset_factory(
    User, 
    CoordinationMember,
    extra=5,
    fields=('coordination', 'user', 'is_coordinator', 'is_reviewer', 'is_pedagogic_reviewer', ),
    can_delete=True,
    form=CoordinationMemberForm,
    min_num=1
)

class EducationSystemForm(forms.ModelForm):
    class Meta:
        model = EducationSystem
        fields = '__all__'
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from fiscallizeon.clients.models import Unity
        self.fields['unities'].queryset = Unity.objects.filter(
            client__in=user.get_clients_cache()
        ).distinct()

class PartnerForm(forms.ModelForm):
    username = forms.CharField(label='Usuário',max_length=100, required=False)
    password = forms.CharField(label='Nova Senha',max_length=128, required=False)
    confirmation_password = forms.CharField(label='Confirmar Nova Senha',max_length=128, required=False)
    must_change_password = forms.BooleanField(label='Deve mudar a senha no próximo acesso',required=False)
    email = forms.EmailField(label="Endereço de email", max_length=128, required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        self.is_update = kwargs.pop('is_update')
        return super(PartnerForm, self).__init__(*args, **kwargs)
    
    class Meta:
        model = Partner
        fields = ('name', 'email', 'password', 'confirmation_password', 'is_printing_staff')
        exclude = ('user', 'client')
        
    def clean(self):
        cleaned_data = super(PartnerForm, self).clean()

        email = cleaned_data.get('email')
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        confirmation_password = cleaned_data.get('confirmation_password')
        must_change_password = cleaned_data.get('must_change_password')

        check_username = User.objects.filter(username=username)
        check_email = User.objects.filter(email=email)

        if self.is_update:
            check_username = check_username.exclude(username=self.instance.user.username)
            check_email = check_email.exclude(email=self.instance.email)

        if username and check_username.exists():
            self.add_error('username', ValidationError(f'Usuario {username} já existe'))

        if email and check_email.exists():
            self.add_error('email', ValidationError(f'Já existe um usuário com o email {email} cadastrado'))
        
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
                
        return cleaned_data
    

class ClientForm(forms.ModelForm):

    class Meta:
        model = Client
        fields = ['omr_print_file_separation']
        
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['omr_print_file_separation'].required = True