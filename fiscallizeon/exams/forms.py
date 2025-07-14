from django import forms
from django.forms import inlineformset_factory

from fiscallizeon.classes.models import Grade, SchoolCoordination
from fiscallizeon.exams.models import Exam, ExamHeader, ExamOrientation, ExamQuestion, ExamTeacherSubject
from fiscallizeon.materials.forms import SimpleStudyMaterialForm
from fiscallizeon.materials.models import StudyMaterial
from fiscallizeon.exams.models import ClientCustomPage, ExamBackgroundImage
from fiscallizeon.subjects.models import SubjectRelation
from django.db.models import Q



class ExamForm(forms.ModelForm):
    grades = forms.ModelChoiceField(
        required=False,
        queryset=Grade.objects.all(), 
        label="Escolha uma série",
        widget=forms.Select(
            attrs={'v-model': 'selectedGrade'}
        )
    )
    release_material_study = forms.DateField(label="Data de liberação", help_text="Data para liberação dos materiais para os alunos", required=False)


    class Meta:
        model = Exam
        exclude = ["questions", ]

    def __init__(self, user, is_update = False, *args, **kwargs):
        from fiscallizeon.clients.models import TeachingStage, EducationSystem
        super(ExamForm, self).__init__(*args, **kwargs)
        self.fields['teacher_subjects'].required = False
        self.fields['coordinations'].required = True
        self.fields['four_alternatives'].required = False
        coordinations = user.get_coordinations_cache()
        
        if is_update:
            self.fields['coordinations'].queryset = SchoolCoordination.objects.filter(
                Q( # Lógica em: https://app.clickup.com/3120759/whiteboards/2z7kq-6333?shape-id=VvV4JUIKtd11FyFCpjK9K
                    Q(id__in=self.instance.coordinations.values('id')) |
                    Q(id__in=coordinations)
                )
            ).distinct()
        else:
            self.fields['coordinations'].queryset = SchoolCoordination.objects.filter(
                id__in=coordinations
            ).distinct()
            
        self.fields['relations'].queryset = SubjectRelation.objects.filter(
            client__in=user.get_clients_cache()
        ).distinct()
        
        self.fields['teaching_stage'].queryset = TeachingStage.objects.filter(client__in=user.get_clients_cache()).distinct()
        self.fields['education_system'].queryset = EducationSystem.objects.filter(client__in=user.get_clients_cache()).distinct()
    
    def clean_related_subjects(self):
        relations = self.cleaned_data["relations"]
        data = self.cleaned_data["related_subjects"]
        
        if data and not relations:
            self.add_error('relations', 'Você precisa selecionar pelo menos um relacionamento ao ativar "Relacionar disciplinas"')
        
        return data
    


class ExamQuestionForm(forms.ModelForm):
    class Meta:
        model = ExamQuestion
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(ExamQuestionForm, self).__init__(*args, **kwargs)
        self.fields['question'].required = False

        # self.fields['weight'].localize = True
        # self.fields['weight'].widget.is_localized = True

class ExamHeaderForm(forms.ModelForm):
    class Meta:
        model = ExamHeader
        fields = "__all__"

class ExamHeaderUpdateForm(forms.ModelForm):
    class Meta:
        model = ExamHeader
        exclude = ('id', 'user')
class ExamOrientationForm(forms.ModelForm):
    class Meta:
        model = ExamOrientation
        fields = "__all__"

class ExamOrientationUpdateForm(forms.ModelForm):
    class Meta:
        model = ExamOrientation
        exclude = ('id', 'user')

class ExamTeacherSubjectForm(forms.ModelForm):
    class Meta:
        model = ExamTeacherSubject
        fields = "__all__"


class ExamTeacherSubjectFormSimple(forms.ModelForm):
    class Meta:
        model = ExamTeacherSubject
        exclude = ("teacher_subject", "exam", "grade", "quantity", "note", "order", )


QuestionFormSet = inlineformset_factory(
    Exam, 
    ExamQuestion,
    extra=0,
    fields=('question',  ),
    can_delete=True,
    form=ExamQuestionForm
)

TeacherSubjectQuestionFormSet = inlineformset_factory(
    ExamTeacherSubject, 
    ExamQuestion,
    extra=0,
    fk_name="exam_teacher_subject",
    fields=('question', 'exam_teacher_subject', 'order', 'weight'),
    can_delete=True,
    form=ExamQuestionForm
)

TeacherSubjectFormSet = inlineformset_factory(
    Exam, 
    ExamTeacherSubject,
    fields=('teacher_subject', 'quantity', 'note', 'order', 'grade', 'subject_note'),
    extra=0,
    can_delete=True,
    form=ExamTeacherSubjectForm
)
StudyMaterialFormSet = inlineformset_factory(
    Exam, 
    StudyMaterial,
    extra=1,
    can_delete=True,
    form=SimpleStudyMaterialForm,
)

class ClientCustomPageForm(forms.ModelForm):
    class Meta:
        model = ClientCustomPage
        fields = '__all__'
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
class ExamBackgroundImageForm(forms.ModelForm):
    class Meta:
        model = ExamBackgroundImage
        fields = '__all__'
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ExamImportForm(forms.Form):
    file = forms.FileField()