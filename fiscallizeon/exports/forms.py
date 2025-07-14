from django import forms
from django.utils import timezone

from fiscallizeon.clients.models import Unity
from fiscallizeon.exams.models import Exam
from fiscallizeon.classes.models import SchoolClass, CourseType, Stage
from fiscallizeon.subjects.models import Subject


class ExamExportAnswerForm(forms.Form):
    start_date = forms.DateField(label='Data Inicial', required=False)
    end_date = forms.DateField(label='Data Final', required=False)
    file_format = forms.CharField(label='Formato do arquivo')
    export_disposition = forms.CharField(label='Disposição do arquivo')
    add_topic = forms.BooleanField(label='Adicionar assuntos abordados', required=False)
    add_bncc = forms.BooleanField(label='Adicionar habilidades e competências', required=False)
    only_correct_wrong = forms.BooleanField(label='Apenas acerto ou erro', required=False)
    add_teacher_name = forms.BooleanField(label='Adicionar nome do professor', required=False)




class ExamsExportErpForm(forms.Form):
    start_date = forms.DateField(label='Data Inicial', required=False)
    end_date = forms.DateField(label='Data Final', required=False)
    exams = forms.ModelMultipleChoiceField(label='Provas', required=False, queryset=Exam.objects.all())
    unity = forms.ModelChoiceField(label='Unidade', queryset=Unity.objects.all(), required=False)
    school_class = forms.ModelChoiceField(label='Turma', queryset=Unity.objects.all(), required=False)
    subjects = forms.ModelMultipleChoiceField(label='Disciplinas', queryset=Unity.objects.all(), required=False)
    export_format = forms.CharField(label='Formato de exportação')
    students = forms.CharField(label='Alunos')
    application_category = forms.CharField(label='Tipo de aplicação')
    subjects_format = forms.CharField(label='Formato de exibição das disciplinas')
    extra_columns = forms.BooleanField(label='Colunas extras', required=False)
    add_exam_name = forms.BooleanField(label='Adicionar nome do caderno', required=False)
    course_type = forms.ModelChoiceField(label="Curso", queryset=CourseType.objects.all(), required=False)
    stage = forms.ModelChoiceField(label="Etapa", queryset=Stage.objects.all(), required=False)
    export_standard = forms.CharField(label='Formato de exportação', required=False)
    unique_file = forms.BooleanField(label='Exportar em um único arquivo', required=False)
    get_abstracts = forms.BooleanField(label='Considerar gabaritos avulsos', required=False)
    
    def __init__(self, user, *args, **kwargs):
        super(ExamsExportErpForm, self).__init__(*args, **kwargs)
        user_coordinations = user.get_coordinations_cache()
        
        self.fields['unity'].queryset = Unity.objects.filter(
            coordinations__in=user_coordinations
        ).distinct()

        self.fields['school_class'].queryset = SchoolClass.objects.filter(
            coordination__in=user_coordinations,
            school_year=timezone.now().year
        ).distinct()

        self.fields['subjects'].queryset = Subject.objects.get_clients_subjects(
            clients=user.get_clients_cache()
        ).distinct()

        if user.client_use_only_own_subjects:
            self.fields['subjects'].queryset = self.fields['subjects'].queryset.exclude(
                client__isnull=True
            )
    
    def clean(self):
        cleaned_data = super(ExamsExportErpForm, self).clean()

        exams = cleaned_data.get('exams')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date > end_date:
            self.add_error('start_date', 'A data inicial deve ser menor que a data final')

        if not exams and not start_date and not end_date:
            self.add_error('exams', 'Selecione pelo menos uma prova ou uma data de início e fim')


class ExamsExportAnswerForm(forms.Form):
    start_date = forms.DateField(label='Data inicial')
    end_date = forms.DateField(label='Data final')
    export_format = forms.CharField(label='Formato de exportação')
    add_topic = forms.BooleanField(label='Adicionar assuntos abordados', required=False)
    add_bncc = forms.BooleanField(label='Adicionar habilidades e competências', required=False)

    

    def clean(self):
        cleaned_data = super(ExamsExportAnswerForm, self).clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date > end_date:
            self.add_error('start_date', 'A data inicial deve ser menor que a data final')
        
        return super().clean()
    

class ExamsSimpleExportForm(forms.Form):
    start_date = forms.DateField(label='Data inicial', required=False,)
    end_date = forms.DateField(label='Data final', required=False,)
    exams = forms.ModelMultipleChoiceField(
        label='Provas', 
        required=False, 
        queryset=Exam.objects.all()
    )
    export_format = forms.CharField(label='Formato de exportação')
    students_filter = forms.CharField(label='Alunos')
    separate_subjects = forms.BooleanField(
        label='Separar por disciplina', 
        help_text="Selecione essa opção se deseja separar os acertos e erros por disciplina", 
        required=False,
    )
    extra_fields = forms.BooleanField(
        label='Adicionar unidade e turma',
        help_text="Serão adicionadas duas colunas com unidade e turma dos alunos", 
        required=False
    )    
    add_teacher_name = forms.BooleanField(
        label='Adicionar nome do professor',
        help_text="Serão adicionados os nomes dos professores que criaram as questões", 
        required=False
    )   

    def clean(self):
        cleaned_data = super(ExamsSimpleExportForm, self).clean()
        exams = cleaned_data.get('exams')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and start_date > end_date:
            self.add_error('start_date', 'A data inicial deve ser menor que a data final')

        if not exams and not start_date and not end_date:
            self.add_error('exams', 'Selecione pelo menos uma prova ou uma data de início e fim')
        
        return super().clean()