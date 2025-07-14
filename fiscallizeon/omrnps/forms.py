from django import forms
from django.core.validators import FileExtensionValidator
from django.forms import formset_factory
from django.core.exceptions import ValidationError

from fiscallizeon.omrnps.models import NPSApplication, ClassApplication
from fiscallizeon.classes.models import SchoolClass

class OMRNPSUploadForm(forms.Form):
    pdf_scan = forms.FileField(
        label='Arquivo escaneado',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )

class OMRNPSErrorForm(forms.Form):
    omr_nps_error = forms.UUIDField(label='omr_error')
    category_description = forms.CharField(label='Descrição', required=False)
    error_image = forms.URLField(label='Imagem escaneada', required=False)
    page_number = forms.IntegerField(label='Página')
    
    application = forms.ModelChoiceField(
        label='Aplicação', 
        queryset=NPSApplication.objects.all(),
        empty_label='Selecione...',
        required=False,
    )

    school_class = forms.ModelChoiceField(
        label='Turma', 
        queryset=SchoolClass.objects.all(),
        empty_label='Selecione...',
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        application = cleaned_data.get("application")
        school_class = cleaned_data.get("school_class")

        if not application or not school_class:
            return cleaned_data

        class_application = ClassApplication.objects.filter(
            nps_application=application,
            school_class=school_class,
        )

        if not class_application:
            raise ValidationError(
                f'Turma {school_class} não cadastrada para a aplicação {application}'
            )

OMRNPSErrorFormSet = formset_factory(
    OMRNPSErrorForm,
    extra=0,
    can_delete=False
)