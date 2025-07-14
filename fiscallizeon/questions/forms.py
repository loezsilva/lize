from email.policy import default
from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import inlineformset_factory
from django.core.validators import FileExtensionValidator

from tinymce.models import HTMLField
from tinymce.widgets import TinyMCE
from django.db.models import Q
from fiscallizeon.core.print_colors import print_success

from fiscallizeon.questions.models import Question, QuestionOption
from fiscallizeon.clients.models import SchoolCoordination
from fiscallizeon.corrections.models import TextCorrection

class QuestionForm(forms.ModelForm):
    user = None
    has_correct_alternative = forms.BooleanField(required=False)
    
    class Meta:
        model = Question
        fields = "__all__"
        exclude = ["coordination", ]

    def __init__(self, user, grade_level=None, *args, **kwargs):
        super(QuestionForm, self).__init__(*args, **kwargs)
        self.fields['coordinations'].required = True
        self.user = user
        self.grade_level = grade_level
        
        if obligation := user.client_teacher_configuration(level=self.grade_level):
            if obligation.commented_response:
                self.fields['commented_awnser'].required = True

        self.fields['coordinations'].queryset = SchoolCoordination.objects.filter(
            pk__in=user.get_coordinations_cache()
        ).distinct()

        self.fields['text_correction'].queryset = TextCorrection.objects.filter(
            Q(client__in=user.get_clients_cache()) | Q(client__isnull=True))

    def clean(self,):
        super().clean()
        
        if teacher_obligation_configuration := self.user.client_teacher_configuration(level=self.grade_level):
                
            if self.cleaned_data['category'] == Question.CHOICE and teacher_obligation_configuration.topics and not len(self.cleaned_data['topics']):
                self.add_error('topics',  ValidationError("Você precisa selecionar pelo menos um assunto abordado!"))
                
            if teacher_obligation_configuration.abilities and not len(self.cleaned_data['abilities']):
                self.add_error('abilities',  ValidationError("Você precisa selecionar pelo menos uma habilidade!"))
                
            if teacher_obligation_configuration.competences and not len(self.cleaned_data['competences']):
                self.add_error('competences',  ValidationError("Você precisa selecionar pelo menos uma competência!"))
                
            if teacher_obligation_configuration.pedagogical_data and (not self.cleaned_data['grade'] or not self.cleaned_data['subject']):
                if not self.cleaned_data['grade']:
                    self.add_error('grade',  ValidationError("Você deve selecionar a série."))
                if not self.cleaned_data['subject']:
                    self.add_error('subject',  ValidationError("Você deve selecionar a disciplina."))
            
            if teacher_obligation_configuration.commented_response and (not self.cleaned_data.get('commented_awnser', None)):
                self.add_error('commented_awnser',  ValidationError("Você deve informar a resposta comentada da questão."))
                
        return self.cleaned_data
    
    
class QuestionUpdateForm(forms.ModelForm):
    user = None
    has_correct_alternative = forms.BooleanField(required=False)
    
    class Meta:
        model = Question
        exclude = ["coordination", "created_by", "adapted"]
        widgets = {
            'cloze_content': forms.Textarea(attrs={'rows': 4, 'style': 'resize: none;'}),
        }

    def __init__(self, user, grade_level=None, *args, **kwargs):
        super(QuestionUpdateForm, self).__init__(*args, **kwargs)
        self.fields['coordinations'].required = True
        self.user = user
        self.grade_level = grade_level
        
        if obligation := user.client_teacher_configuration(level=self.grade_level):
            if obligation.commented_response:
                self.fields['commented_awnser'].required = True
        
        self.fields['coordinations'].queryset = SchoolCoordination.objects.filter(
            pk__in=user.get_coordinations_cache()
        ).distinct()

        self.fields['text_correction'].queryset = TextCorrection.objects.filter(
            Q(client__in=user.get_clients_cache()) | Q(client__isnull=True))
        
        if not user.client_has_cloze_questions:
            self.fields['category'].choices = [
                (value, label) for value, label in self.fields['category'].choices if value != Question.CLOZE
            ]
    
    def clean(self):
        super().clean()
        
        if teacher_obligation_configuration := self.user.client_teacher_configuration(level=self.grade_level):
                
            if self.cleaned_data['category'] == Question.CHOICE and teacher_obligation_configuration.topics and not len(self.cleaned_data['topics']):
                self.add_error('topics',  ValidationError("Você precisa selecionar pelo menos um assunto abordado!"))
                
            if teacher_obligation_configuration.abilities and not len(self.cleaned_data['abilities']):
                self.add_error('abilities',  ValidationError("Você precisa selecionar pelo menos uma habilidade!"))
                
            if teacher_obligation_configuration.competences and not len(self.cleaned_data['competences']):
                self.add_error('competences',  ValidationError("Você precisa selecionar pelo menos uma competência!"))
                
            if teacher_obligation_configuration.pedagogical_data and (not self.cleaned_data['grade'] or not self.cleaned_data['subject']):
                if not self.cleaned_data['grade']:
                    self.add_error('grade',  ValidationError("Você deve selecionar a série."))
                if not self.cleaned_data['subject']:
                    self.add_error('subject',  ValidationError("Você deve selecionar a disciplina."))
            
            if teacher_obligation_configuration.commented_response and (not self.cleaned_data.get('commented_awnser', None)):
                self.add_error('commented_awnser',  ValidationError("Você deve informar a resposta comentada da questão."))
        
        # Retorna condição no dia 09/07/2025 para resolver o problema apontado na task:
        # https://app.clickup.com/t/86aa39hdr
        if not self.instance.can_be_updated(user=self.user) and 'enunciation' in self.changed_data:
            self.add_error('enunciation',  'Enunciado e texto das alternativas não podem ser alterados pois já foram utilizados em uma aplicação e possui respostas associadas.')
                
        return self.cleaned_data

class QuestionOptionForm(forms.ModelForm):
    class Meta:
        model = QuestionOption
        fields = ['text', 'is_correct' ]

    def clean_enunciation(self):
        has_changed = 'text' in self.changed_data
        if self.instance.question.can_be_updated() and has_changed:
            raise ValidationError('Texto de alternativa não pode ser alterado...')
        
        return self.cleaned_data['text']
        

class ImportQuestionsDocxForm(forms.Form):
    questions_doc = forms.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['docx'])]
    )

QuestionOptionFormSet = inlineformset_factory(
    Question, QuestionOption, 
    fields=('text', 'is_correct'),
    extra=5, max_num=5, 
    min_num=2, form=QuestionOptionForm,
    can_delete=True,
)


class QuestionBaseTextSimpleForm(forms.Form):
    text = forms.CharField(widget=TinyMCE(attrs={'id':'id_new_base_text'}))