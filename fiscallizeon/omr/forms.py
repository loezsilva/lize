from django import forms
from django.apps import apps
from django.core.validators import FileExtensionValidator
from django.forms import formset_factory

from fiscallizeon.students.models import Student
from fiscallizeon.omr.models import OMRCategory, OMRDiscursiveError
from fiscallizeon.exams.models import ExamQuestion

class AnswerSheetForm(forms.Form):
    Application = apps.get_model('applications', 'Application')

    pdf_scan = forms.FileField(
        label='Arquivo escaneado',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    omr_category = forms.ModelChoiceField(
        label='Modelo de gabarito', 
        queryset=OMRCategory.objects.all(),
        empty_label='Lize ou ENEM',
        blank=True,
        required=False,
    )
    ignore_qr_codes = forms.BooleanField(
        required=False,
        label='Ignorar QR codes',
    )
    gamma_option = forms.ChoiceField(
        label='Tipo de marcação',
        choices=[
            ('1', 'Marcação normal'),
            ('2.5', 'Marcação em caneta clara'),
            ('3.5', 'Marcação a lapis ou escaneamento claro'),
        ],
        initial='1',
        widget=forms.Select()
    )
    application = forms.UUIDField(
        label='Aplicação', 
        help_text='Atenção! Esta opção ignora a aplicação da folha de respostas e move os alunos desse upload para a aplicação informada abaixo. Utilize apenas em situações pontuais.',
        widget=forms.Select, 
        required=False
    )

class OffsetSchoolClassAnswerSheetForm(forms.Form):
    Application = apps.get_model('applications', 'Application')

    pdf_scan = forms.FileField(
        label='Arquivo escaneado',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    gamma_option = forms.ChoiceField(
        label='Tipo de marcação',
        choices=[
            ('1', 'Marcação normal'),
            ('2.5', 'Marcação em caneta clara'),
            ('3.5', 'Marcação a lapis ou escaneamento claro'),
        ],
        initial='1',
        widget=forms.Select()
    )
    application = forms.UUIDField(
        label='Aplicação', 
        widget=forms.Select, 
        required=True
    )
    school_class = forms.UUIDField(
        label='Turma', 
        widget=forms.Select, 
        required=True
    )


class OMRErrorForm(forms.Form):
    omr_error = forms.UUIDField(label='omr_error')
    application = forms.UUIDField(label='Aplicação', widget=forms.Select, required=False)
    category_description = forms.CharField(label='Descrição', required=False)
    error_image = forms.URLField(label='Imagem escaneada', required=False)
    page_number = forms.IntegerField(label='Página')
    randomization_version = forms.IntegerField(label='Versão de randomização', initial=0, min_value=0)
    omr_category = forms.ModelChoiceField(
        label='Modelo de gabarito', 
        queryset=OMRCategory.objects.all(),
        empty_label='Selecione...',
        required=False
    )
    student = forms.ModelChoiceField(
        label='Aluno', 
        queryset=Student.objects.all(),
        empty_label='Selecione...',
        required=False,
    )

    def clean_omr_category(self):
        data = self.cleaned_data['omr_category']
        return data.sequential if data else None


class OMRDiscursiveErrorForm(forms.Form):
    omr_error = forms.UUIDField(label='omr_error')
    application_student = forms.UUIDField(label='aluno')
    category_description = forms.CharField(label='Descrição', required=False)
    error_image = forms.URLField(label='Imagem escaneada', required=False)
    exam_question = forms.ModelChoiceField(
        label='Questão', 
        queryset=ExamQuestion.objects.all().availables(),
        empty_label='Selecione...',
        required=False
    )
    omr_category = forms.ModelChoiceField(
        label='Modelo de gabarito', 
        queryset=OMRCategory.objects.all(),
        empty_label='Selecione...',
        required=False,
    )


OMRErrorFormSet = formset_factory(
    OMRErrorForm,
    extra=0,
    can_delete=False
)

OMRDiscursiveErrorFormSet = formset_factory(
    OMRDiscursiveErrorForm,
    extra=0,
    can_delete=False
)