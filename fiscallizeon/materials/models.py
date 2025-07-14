import os, re
from django.db import models
from fiscallizeon.exams.models import Exam
from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import Grade, SchoolClass
from fiscallizeon.clients.models import Client,User
from fiscallizeon.core.models import BaseModel
from fiscallizeon.subjects.models import Subject, Topic
from fiscallizeon.core.storage_backends import PrivateMediaStorage

def study_material_file_directory_path(instance, filename):
    return f'study_materail/{str(instance.pk)}/{filename}'

def study_material_thumbnail_file_directory_path(instance, filename):
    return f'study_materail/thumbnails/{str(instance.pk)}/{filename}'

class StudyMaterial(BaseModel):
   # VIDEO, FILE = range(2)
   # MATERIAL_TYPE_CHOICES = (
    #    (VIDEO, "Vídeo"),
    #    (FILE, "Arquivo")
    #)
   # material_type = models.SmallIntegerField("Tipo de material", choices=MATERIAL_TYPE_CHOICES, default=FILE)
    title = models.CharField("Título", max_length=100)
    client = models.ForeignKey(Client, verbose_name="Cliente", on_delete=models.CASCADE)
    material = models.FileField(
        "Arquivo", 
        upload_to=study_material_file_directory_path,
        storage=PrivateMediaStorage(),
        default="",
        blank=True, 
        null=True
    )
    thumbnail = models.FileField(
        "Capa do material (imagem)", 
        upload_to=study_material_thumbnail_file_directory_path,
        help_text="Arquivo de imagem: .png, .jpg, .jpeg, .gif",
        storage=PrivateMediaStorage(),
        blank=True,
        null=True
    )
    grades = models.ManyToManyField(Grade, verbose_name="Série", blank=True)
    subjects = models.ManyToManyField(Subject, verbose_name="Disciplinas", blank=True)
    school_classes = models.ManyToManyField(SchoolClass, verbose_name="Turmas", blank=True)
    FIRST, SECOND, THIRD, FOURTH, FIFTH, SIXTH, GENERAL = range(1, 8)
    STAGE_CHOICES = (
        (FIRST, '1ª Etapa'),
        (SECOND, '2ª Etapa'),
        (THIRD, '3ª Etapa'),
        (FOURTH, '4ª Etapa'),
        (FIFTH, '5ª Etapa'),
        (SIXTH, '6ª Etapa'),
        (GENERAL, 'Geral')
    )
    stage = models.SmallIntegerField("Etapa de Ensino", choices=STAGE_CHOICES, default=GENERAL)
    teaching_stage = models.ForeignKey(
        'clients.TeachingStage',
        on_delete=models.PROTECT,
        verbose_name='etapa do ensino',
        null=True,
        blank=True,
    )
    release_material_study = models.DateTimeField(verbose_name="Liberação de material de estudo", auto_now=False, null=True)
    emphasis = models.BooleanField("Em destaque", help_text="Marque esta opção se deseja que o material fique em destaque para o aluno", default=False)
    exam = models.ForeignKey(Exam, verbose_name="Caderno", on_delete=models.CASCADE, related_name="materials", null=True, blank=True)
    material_video = models.URLField("Vídeo do material", null=True, blank=True)
    PANDA, YOUTUBE = range(2)
    MATERIAL_VIDEO_TYPE_CHOICE = (
        (PANDA, "Panda Vídeo"),
        (YOUTUBE, "Youtube")
    )
    material_video_type = models.SmallIntegerField("Fonte do vídeo", choices=MATERIAL_VIDEO_TYPE_CHOICE, default=YOUTUBE, null=True, blank=True)
    send_by = models.ForeignKey(User, verbose_name="Enviado por", on_delete=models.CASCADE, related_name="send_materials", null=True, blank=True)
   # topics = models.ManyToManyField(Topic, verbose_name="Assuntos abordados", related_name="materials", blank=True)

    class Meta:
        verbose_name = 'Material de estudo'
        verbose_name_plural = 'Materiais de estudo'
        ordering = ['-created_at']

    @property
    def get_emmbbeded_video(self):
        if self.material_video == self.PANDA and self.answer_video:
            return f'<iframe style="position: absolute; top: 0; left: 0; bottom: 0; right: 0; width: 100%; height: 100%; border:none; overflow:hidden;" src="{self.answer_video}" allow="accelerometer;gyroscope;encrypted-media;picture-in-picture" allowfullscreen=true></iframe>'
        elif self.material_video == self.YOUTUBE and self.answer_video:
            if not "embed" in self.answer_video:
                if "watch?v=" in self.answer_video:
                    self.answer_video = self.answer_video.replace("watch?v=", "embed/")
                elif "youtu.be" in self.answer_video:
                    self.answer_video = self.answer_video.replace("youtu.be/", "youtube.com/embed/")
                    
                src = re.split(r'\b[&]+.*$', self.answer_video)
                src = re.split(r'\b[=]+.*$', src[0])[0]
            
            return f'<iframe style="position: absolute; top: 0; left: 0; bottom: 0; right: 0; width: 100%; height: 100%; border:none; overflow:hidden;" src="{src}" title="Resposta comentada em vídeo" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
        
        return ''
        
    def __str__(self):
        return self.title

    def get_extension(self):
        name, extension = os.path.splitext(self.material.name)
        return extension

class FavoriteStudyMaterial(BaseModel):
    study_material = models.ForeignKey(StudyMaterial, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, related_name="favorites_files", on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Material de estudo favorito'
        verbose_name_plural = 'Materiais de estudo favoritos'
        
    def __str__(self):
        return f'{self.study_material.title} - {self.student.name}'