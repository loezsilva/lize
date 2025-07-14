from fiscallizeon.students.models import Student
from django import forms
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from fiscallizeon.applications.models import Application
from fiscallizeon.inspectors.models import Inspector

class ApplicationForm(forms.ModelForm):
    date = forms.DateField(input_formats=['%d-%m-%Y','%Y-%m-%d'], label="Data da aplicação", required=True)

    class Meta:
        model = Application
        fields = '__all__'
        exclude = [
            'orchestrator_id', 'prefix', 'chat_room_id', 'chat_room_pin', 'last_answer_sheet_generation',
            'answer_sheet', 'sheet_exporting_status','sheet_exporting_count', 'duplicate_application', 'leveling_test',
            'book_pages', 'bag_pages'
        ]
        widgets = {
            'orientations': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super(ApplicationForm, self).__init__(*args, **kwargs)
        self.fields['student_stats_permission_date'].input_formats = ['%d-%m-%Y','%Y-%m-%d']
        self.fields['exam'].required = True
        if self.instance.category == Application.PRESENTIAL:
            self.fields['min_time_finish'].required = False
            self.fields['min_time_pause'].required = False
            self.fields['max_time_tolerance'].required = False 
        
    def get_form(self, request, *args, **kwargs):
        form = super(ApplicationForm, self).get_form(request, *args, **kwargs)
        form.current_user = request.user
        return form  

    def clean(self):
        super(ApplicationForm, self).clean()
        

        if not self.cleaned_data['students'] and not self.cleaned_data['school_classes']:
            self.add_error('students',  ValidationError("Você deve selecionar pelo menos um aluno ou uma turma para esta aplicação"))

        start = self.cleaned_data['start']
        date = self.cleaned_data['date']
        end = self.cleaned_data['end']
        category = self.cleaned_data['category']
        homework_date_end = self.cleaned_data['date_end'] 
        
        if self.cleaned_data['inspectors_fiscallize']:
            self.cleaned_data['inspectors'] = []

        now = timezone.now().astimezone()

        date_start = timezone.make_aware(datetime.combine(date, start))
        date_end = timezone.make_aware(datetime.combine(date, end))
        
        if category == Application.HOMEWORK:
            date_end = timezone.make_aware(datetime.combine(homework_date_end, end))
            
        student_stats_permission_date = self.cleaned_data['student_stats_permission_date']
        
        

        diff = (date_start - now).total_seconds() / 60
        min_difference = settings.MIN_MINUTES_CREATE_BEFORE_START
        
        if not self.cleaned_data['release_result_at_end'] and student_stats_permission_date and student_stats_permission_date < date_end:
            self.add_error('student_stats_permission_date',  ValidationError("A data de liberação dos resultados deve ser maior que a data de fim da aplicação"))
            
        if end <= start:
            self.add_error('end',  ValidationError("Horário final deve ser maior que o horário inicial")) 
        
        if diff <= min_difference and not Application.objects.filter(pk=self.instance.pk).exists():
            self.add_error('start', ValidationError(f'Aplicação deve iniciar pelo menos {min_difference} minutos depois de agora')) 

        return self.cleaned_data

class ApplicationMultipleForm(forms.ModelForm):
    date = forms.DateField(input_formats=['%d-%m-%Y','%Y-%m-%d'], label="Data da aplicação", required=True)

    class Meta:
        model = Application
        fields = '__all__'
        exclude = [
            'orchestrator_id', 'prefix', 'chat_room_id', 'chat_room_pin', 'last_answer_sheet_generation',
            'answer_sheet', 'sheet_exporting_status','sheet_exporting_count', 'duplicate_application', 'leveling_test',
            'book_pages', 'bag_pages'
        ]
        widgets = {
            'orientations': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super(ApplicationMultipleForm, self).__init__(*args, **kwargs)
        self.fields['student_stats_permission_date'].input_formats = ['%d-%m-%Y','%Y-%m-%d']
        self.fields['exam'].required = True

    def get_form(self, request, *args, **kwargs):
        form = super(ApplicationMultipleForm, self).get_form(request, *args, **kwargs)
        form.current_user = request.user
        return form  

    def clean(self):
        super(ApplicationMultipleForm, self).clean()
        
        if not self.cleaned_data['students'] and not self.cleaned_data['school_classes']:
            self.add_error('students',  ValidationError("Você deve selecionar pelo menos um aluno ou uma turma para esta aplicação"))

        start = self.cleaned_data['start']
        date = self.cleaned_data['date']
        end = self.cleaned_data['end']
        category = self.cleaned_data['category']
        homework_date_end = self.cleaned_data['date_end'] 
        
        if self.cleaned_data['inspectors_fiscallize']:
            self.cleaned_data['inspectors'] = []

        now = timezone.now().astimezone()

        date_start = timezone.make_aware(datetime.combine(date, start))
        date_end = timezone.make_aware(datetime.combine(date, end))
        
        if category == Application.HOMEWORK:
            date_end = timezone.make_aware(datetime.combine(homework_date_end, end))
            
        student_stats_permission_date = self.cleaned_data['student_stats_permission_date']
        
        

        diff = (date_start - now).total_seconds() / 60
        min_difference = settings.MIN_MINUTES_CREATE_BEFORE_START
        
        if not self.cleaned_data['release_result_at_end'] and student_stats_permission_date and student_stats_permission_date < date_end:
            self.add_error('student_stats_permission_date',  ValidationError("A data de liberação dos resultados deve ser maior que a data de fim da aplicação"))
            
        if end <= start:
            self.add_error('end',  ValidationError("Horário final deve ser maior que o horário inicial")) 
        
        if diff <= min_difference and not Application.objects.filter(pk=self.instance.pk).exists():
            self.add_error('start', ValidationError(f'Aplicação deve iniciar pelo menos {min_difference} minutos depois de agora')) 

        return self.cleaned_data


class ApplicationEditForm(forms.ModelForm):
    MAX_MINUTES_START_DIFF = 60
    MAX_MINUTES_END_DIFF = 120

    class Meta:
        model = Application
        fields = '__all__'
        exclude = ['students', 'school_classes', 
            'orchestrator_id', 'prefix', 'text_room_id', 'text_room_pin', 'video_room_id', 
            'video_room_pin', 'video_room_secret', 'last_answer_sheet_generation', 'answer_sheet', 
            'sheet_exporting_status','sheet_exporting_count','duplicate_application',
            'book_pages', 'bag_pages'
        ]

        widgets = {
            'orientations': forms.HiddenInput()
        }

    def __init__(self, *args, **kwargs):
        super(ApplicationEditForm, self).__init__(*args, **kwargs)
        self.fields['exam'].required = True

        if self.instance.pk:
            self.fields['category'].required = False

            if self.instance.category == Application.PRESENTIAL:
                self.fields['min_time_finish'].required = False
                self.fields['min_time_pause'].required = False
                self.fields['max_time_tolerance'].required = False      

    def get_form(self, request, *args, **kwargs):
        form = super(ApplicationEditForm, self).get_form(request, *args, **kwargs)
        form.current_user = request.user
        return form

    def clean(self):
        super(ApplicationEditForm, self).clean()

        date = self.instance.date
        start = self.cleaned_data['start']
        end = self.cleaned_data['end']
        category = self.instance.category
        homework_date_end = self.cleaned_data['date_end']        
        
        list_inspectors = []
        for inspectors in self.cleaned_data['inspectors']:
            if self.cleaned_data['inspectors_fiscallize'] and inspectors.inspector_type == Inspector.INSPECTOR:
                list_inspectors.append(inspectors)
            elif self.cleaned_data['inspectors_fiscallize'] == False and inspectors.inspector_type != Inspector.INSPECTOR:
                list_inspectors.append(inspectors)
                
        self.cleaned_data['inspectors'] = list_inspectors
        
        if category == Application.HOMEWORK:
            new_end_aware = timezone.make_aware(datetime.combine(homework_date_end, end))
        if not category == Application.HOMEWORK:
            old_start_aware = timezone.make_aware(datetime.combine(date, self.instance.start))
            new_start_aware = timezone.make_aware(datetime.combine(date, start))
            old_end_aware = timezone.make_aware(datetime.combine(date, self.instance.end))
            new_end_aware = timezone.make_aware(datetime.combine(date, end))
        
            diff_start = (new_start_aware - old_start_aware).total_seconds() / 60
            diff_end = (new_end_aware - old_end_aware).total_seconds() / 60
                
            """
            if abs(diff_start) > self.MAX_MINUTES_START_DIFF:
                self.add_error('start',  ValidationError(
                    f'Horário inicial não pode ser alterado em mais de {self.MAX_MINUTES_START_DIFF} minutos'
                ))

            if abs(diff_end) > self.MAX_MINUTES_END_DIFF:
                self.add_error('end',  ValidationError(
                    f'Horário final não pode ser alterado em mais de {self.MAX_MINUTES_END_DIFF} minutos'
                ))
            """
        
        new_student_stats_permission_date = self.cleaned_data['student_stats_permission_date']
        if new_student_stats_permission_date:
            if not self.cleaned_data['release_result_at_end'] and new_student_stats_permission_date < new_end_aware:
                self.add_error('student_stats_permission_date',  ValidationError("A data de liberação dos resultados deve ser maior que a data de fim da aplicação"))
        
        return self.cleaned_data


class ApplicationEditStudentsForm(forms.ModelForm):

    class Meta:
        model = Application
        fields = ['students', 'school_classes']

    def clean_students(self):
        if len(self.cleaned_data['students']) == 0:
            raise ValidationError('É necessário selecionar pelo menos um aluno')
        return self.cleaned_data['students']
    
    def clean(self):
        cleaned_data = super().clean()
        students = cleaned_data.get("students")
        school_classes = cleaned_data.get("school_classes")

        exclude_classes_pks = []
        for school_class in school_classes:
            if not students.filter(pk__in=school_class.students.all().values('pk')):
                exclude_classes_pks.append(school_class.pk)

        cleaned_data['school_classes'] = school_classes.exclude(pk__in=exclude_classes_pks)
        
class ApplicationStudentImportForm(forms.Form):
    file = forms.FileField()