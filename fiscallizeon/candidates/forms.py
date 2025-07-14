from django import forms
from django.utils import timezone
from django.forms import ModelChoiceField

# from captcha.fields import ReCaptchaField
from localflavor.br.forms import BRStateChoiceField

from fiscallizeon.clients.models import Client
from fiscallizeon.students.models import Student
from fiscallizeon.candidates.models import Candidate
from fiscallizeon.classes.models import SchoolClass, Grade

from fiscallizeon.accounts.models import User
from fiscallizeon.applications.models import Application, ApplicationStudent

class CandidateForm(forms.ModelForm):
    # captcha = ReCaptchaField()
    name = forms.CharField(label="Digite seu nome")
    client = forms.CharField(widget=forms.HiddenInput())
    email = forms.EmailField(label="Digite seu email")
    classes = forms.ModelMultipleChoiceField(queryset=SchoolClass.objects.all())

    class Meta:
        model = Candidate
        fields = '__all__'
        exclude = ["student"]


    def save(self, commit=True):
        candidate = super(CandidateForm, self).save(commit=False)
        student = Student.objects.create(
            client=Client.objects.get(pk=self.cleaned_data["client"]),
            name=self.cleaned_data["name"],
            email=self.cleaned_data["email"],
            enrollment_number="1234"
        )
        candidate.student = student
        candidate.save()

        classes = self.cleaned_data["classes"]

        for selectedSchoolClass in classes:
            selectedSchoolClass.students.add(student)

        return candidate
    
class SubscribeInClassForm(forms.Form):
    name = forms.CharField(label="Digite seu nome completo")
    username = forms.CharField(label="Digite um novo usuário para login")
    password = forms.CharField(label="Senha", widget=forms.PasswordInput)
    confirm_password = forms.CharField(label="Confirme sua senha", widget=forms.PasswordInput)
    school_class = forms.CharField(widget=forms.HiddenInput())

    email = forms.EmailField(label="Digite um novo email")
    state = BRStateChoiceField(label="Você estuda em qual estado?", 
        widget=forms.Select(attrs={'class': 'select2 form-control'})
    )
    school_name = forms.CharField(label="Qual o nome da escola/cursinho que você estuda?")

    def clean(self):
        clean_data = super().clean()
        password = clean_data.get("password")
        confirm_password = clean_data.get("confirm_password")

        print(password, confirm_password)

        if not (password == confirm_password):
            self.add_error('password', 'As senhas não coincidem, digite novamente!')
            
        return clean_data

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            self.add_error('username', 'Você já possui um cadastro com esse username, por favor insira um novo email para acessar os simulados!')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            self.add_error('email', 'Você já possui um cadastro com esse email, por favor insira um novo email para acessar os simulados!')
        return email

    def save(self, commit=True):
        school_class = self.cleaned_data["school_class"]
        school_class = SchoolClass.objects.get(pk=school_class)
        print(self.cleaned_data)
        user = User.objects.create_user(
            name=self.cleaned_data['name'],
            email=self.cleaned_data['email'],
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
        )
        user.save()

        student = Student(
            user=user,
            client=school_class.coordination.unity.client,
            name=self.cleaned_data['name'],
            email=self.cleaned_data['email'],
            state=self.cleaned_data['state'],
            school_name=self.cleaned_data['school_name']
        )

        applications = Application.objects.filter(
            school_classes=school_class
        ).annotate_date_end().filter(
            datetime_end__gt=timezone.localtime(timezone.now())
        ).distinct()

        student.save(skip_hooks=True)
        school_class.students.add(student)

        for application in applications:
            ApplicationStudent.objects.create(
                student=student,
                application=application
            )

        return student