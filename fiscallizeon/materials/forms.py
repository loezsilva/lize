from django import forms
from django.db.models import Q
from fiscallizeon.clients.models import TeachingStage
from fiscallizeon.exams.models import Exam
from fiscallizeon.subjects.models import Subject
from fiscallizeon.materials.models import StudyMaterial
from django.db.models.functions import Length

from django.conf import settings

# Material Start
class StudyMaterialForm(forms.ModelForm):
    class Meta:
        model = StudyMaterial
        fields = "__all__"
        exclude = ['stage',]

    def __init__(self, user, *args, **kwargs):
        super(StudyMaterialForm, self).__init__(*args, **kwargs)
        self.fields['subjects'].queryset = Subject.objects.filter(
            Q(parent_subject__isnull=True) |
            Q(client__isnull=True) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client=user.client)
            )
        ).order_by('name').distinct()
        self.fields['teaching_stage'].queryset = TeachingStage.objects.annotate(
            name_length=Length('name')
        ).filter(
            client=user.client,
        ).order_by('name_length', 'name').distinct()

        if user.client_use_only_own_subjects:
            self.fields['subjects'].queryset = self.fields['subjects'].queryset.exclude(
                client__isnull=True
            )

        if user.user_type == settings.TEACHER:
            self.fields['exam'].queryset = Exam.objects.filter(
                coordinations__in=user.get_coordinations_cache(),
                examteachersubject__teacher_subject__teacher__user=user
            ).distinct()
        else:
            self.fields['exam'].queryset = Exam.objects.filter(
                coordinations__in=user.get_coordinations_cache(),
            ).distinct()
        
    def clean_thumbnail(self):
        thumbnail = self.cleaned_data.get("thumbnail")
        if thumbnail and hasattr(thumbnail, 'content_type'):
            if not thumbnail.content_type in ["image/jpeg", "image/png", "image/gif", "image/jpg", "image/webp"]:
                raise forms.ValidationError("Arquivo de imagem inválido")
        return thumbnail
    

    def clean(self):
        cleaned_data = super(StudyMaterialForm, self).clean()
        exam = cleaned_data['exam']
        subjects = cleaned_data['subjects']
        
        material = cleaned_data['material']
        material_video = cleaned_data['material_video']
        
        if not material and not material_video:
            self.add_error('material', 'Você precisa selecionar um material ou adicionar um vídeo como material de estudo')

        school_classes = cleaned_data['school_classes']

        if not exam:
            if not subjects:
                self.add_error('subjects', 'Selecione pelo menos uma disciplina')
            if not school_classes:
                self.add_error('school_classes', 'Selecione pelo menos uma turma')

        return cleaned_data

class StudyMaterialUpdateForm(forms.ModelForm):

    class Meta:
        model = StudyMaterial
        fields = ['title', 'material', 'thumbnail', 'subjects', 'grades', 'school_classes', 'teaching_stage', 'release_material_study', 'emphasis', 'exam', 'material_video_type', 'material_video']

    def __init__(self, user, *args, **kwargs):
        super(StudyMaterialUpdateForm, self).__init__(*args, **kwargs)
        self.fields['subjects'].queryset = Subject.objects.filter(
            Q(parent_subject__isnull=True) |
            Q(client__isnull=True) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client=user.client)
            )
        ).order_by('name').distinct()
        self.fields['teaching_stage'].queryset = TeachingStage.objects.annotate(
            name_length=Length('name')
        ).filter(
            client=user.client,
        ).order_by('name_length', 'name').distinct()

        if user.client_use_only_own_subjects:
            self.fields['subjects'].queryset = self.fields['subjects'].queryset.exclude(
                client__isnull=True
            )
            
        self.fields['exam'].queryset = Exam.objects.filter(coordinations__unity__client__in=user.get_clients_cache()).distinct()

    def clean_thumbnail(self):
        thumbnail = self.cleaned_data.get("thumbnail")
        if thumbnail and hasattr(thumbnail, 'content_type'):
            if not thumbnail.content_type in ["image/jpeg", "image/png", "image/gif", "image/jpg", "image/webp"]:
                raise forms.ValidationError("Arquivo de imagem inválido")
        return thumbnail
    
    def clean(self):
        cleaned_data = super(StudyMaterialUpdateForm, self).clean()
        exam = cleaned_data.get('exam')
        subjects = cleaned_data.get('subjects')
        school_classes = cleaned_data.get('school_classes')

        material = cleaned_data['material']
        material_video = cleaned_data['material_video']
        
        if not material and not material_video:
            self.add_error('material', 'Você precisa selecionar um material ou adicionar um vídeo como material de estudo')
            
        if not exam:
            if not subjects:
                self.add_error('subjects', 'Selecione pelo menos uma disciplina')
            if not school_classes:
                self.add_error('school_classes', 'Selecione pelo menos uma turma')

        return cleaned_data

class SimpleStudyMaterialForm(forms.ModelForm):
    class Meta:
        model = StudyMaterial
        fields = ["title", "material", "thumbnail", "stage", "emphasis"]

    def clean_thumbnail(self):
        thumbnail = self.cleaned_data.get("thumbnail")
        if thumbnail and hasattr(thumbnail, 'content_type'):
            if not thumbnail.content_type in ["image/jpeg", "image/png", "image/gif", "image/jpg", "image/webp"]:
                raise forms.ValidationError("Arquivo de imagem inválido")
        return thumbnail
        

# Material End
