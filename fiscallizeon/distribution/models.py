from django.db import models
from django.apps import apps
from django.utils import timezone

from fiscallizeon.core.models import BaseModel
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.clients.models import SchoolCoordination
from fiscallizeon.distribution.managers import RoomManager
from django_lifecycle import hook

def exams_bag_file_directory_path(instance, filename):
    return f'ensalamentos/{str(instance.pk)}/{filename}'

class Room(BaseModel):
    coordination = models.ForeignKey(SchoolCoordination, on_delete=models.CASCADE, related_name='rooms')
    name = models.CharField('Nome', max_length=255)
    capacity = models.PositiveSmallIntegerField('Capacidade máxima de alunos')

    objects = RoomManager()
    class Meta:
        verbose_name = 'Sala'
        verbose_name_plural = 'Salas'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} - {self.coordination.name}'

    def get_last_grade(self, date, start, end):
        Student = apps.get_model('students', 'Student')
        Grade = apps.get_model('classes', 'Grade')

        room_students = Student.objects.using('default').filter(
            pk__in=self.room_distribution.filter(
                distribution__application__date=date,
                distribution__application__start=start,
                distribution__application__end=end,
            ).values_list('student', flat=True)
        ).distinct()

        return Grade.objects.using('default').filter(
            schoolclass__students__in=room_students
        ).distinct().order_by('name').last()

    def get_last_class(self, date, start, end):
        Student = apps.get_model('students', 'Student')
        SchoolClass = apps.get_model('classes', 'SchoolClass')

        room_students = Student.objects.using('default').filter(
            pk__in=self.room_distribution.filter(
                distribution__application__date=date,
                distribution__application__start=start,
                distribution__application__end=end,
            ).values_list('student', flat=True)
        ).distinct()

        return SchoolClass.objects.using('default').filter(
            students__in=room_students,
            temporary_class=False,
            school_year=timezone.now().year,
        ).distinct().order_by('name').last()


class RoomDistribution(BaseModel):
    NAME_GRADE, NAME_SCHOOLCLASS, NAME_SCHOOL_COORDINATION = range(3)
    CATEGORY_CHOICES = (
        (NAME_SCHOOL_COORDINATION, 'Por nome e coordenação'),
        (NAME_GRADE, 'Por nome e série'),
        (NAME_SCHOOLCLASS, 'Por nome e turma'),
    )

    OTHER, WAITING_EXPORT, EXPORTING, EXPORTED, EXPORT_ERROR, DISTRIBUTING = range(6)
    STATUS_CHOICES = (
        (OTHER, 'Desconhecido'),
        (WAITING_EXPORT, 'Sem malote gerado'),
        (EXPORTING, 'Exportando malote'),
        (EXPORTED, 'Malote exportado'),
        (EXPORT_ERROR, 'Erro de exportação'),
        (DISTRIBUTING, 'Distribuindo alunos'),
    )

    category = models.PositiveSmallIntegerField('Categoria', choices=CATEGORY_CHOICES)
    status = models.PositiveSmallIntegerField(
        'Status da exportação', 
        choices=STATUS_CHOICES, 
        default=WAITING_EXPORT
    )
    exams_bag = models.FileField(
        'Malote de provas',
        upload_to=exams_bag_file_directory_path, 
        storage=PrivateMediaStorage(),
        blank=True,
        null=True,
    )
    last_exams_bag_generation = models.DateTimeField(
        'Última geração de malote de provas',
        blank=True,
        null=True,
    )
    exams_bag_generation_count = models.PositiveSmallIntegerField(
        'Número de gerações de malote de provas',
        default=0,
    )
    
    is_printed = models.BooleanField("Já foi impresso", default=False, blank=True)
    shuffle_students = models.BooleanField(
        "Ignorar ordenação alfabética?", 
        help_text="O sistema respeitará o tipo de ensalamento selecionado mas não irá alocar os alunos de modo alfabético", 
        default=False
    )
    balance_rooms = models.BooleanField(
        "Equilibrar quantidade de alunos entre as salas selecionadas?", 
        help_text="O sistema tentará equilibrar a quantidade de alunos por sala, de modo que a ocupação percentual entre elas seja o mais próximo possível", 
        default=False
    )

    class Meta:
        verbose_name = 'Ensalamento'
        verbose_name_plural = 'Ensalamentos'

    def __str__(self):
        return str(self.pk)

    def get_rooms(self):
        first_application = self.application_set.first()
        if not first_application:
            return []
        
        return Room.objects.filter_by_application_date(
            first_application.date, 
            first_application.start, 
            first_application.end
        )
        
    def get_rooms_in_use(self):
        return Room.objects.filter(pk__in=self.room_distribution.all().values_list('room', flat=True))

    def get_applications(self):
        return self.application_set.all().order_by('exam__name')
    
    def get_exams(self):
        from fiscallizeon.exams.models import Exam
        return Exam.objects.filter(pk__in=self.get_applications().values('exam')).order_by('name').distinct()
    
    @property
    def urls(self):
        from django.urls import reverse
        return {
            "api_roomdistribution_update": reverse("distribution:api_roomdistribution_update", kwargs={ "pk": self.pk })
        }
    
    @hook('after_update', when="is_printed", has_changed=True)
    def change_is_printed(self):
        from fiscallizeon.exams.models import Exam
        exams = Exam.objects.filter(application__in=self.get_applications())
        exams.update(is_printed=self.is_printed)
        
    @property
    def can_print(self):
        if self.is_printed:
            return False
        return True
        

class RoomDistributionStudent(BaseModel):
    distribution = models.ForeignKey(RoomDistribution, on_delete=models.CASCADE, related_name='room_distribution')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='room_distribution')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='room_distribution')

    class Meta:
        verbose_name = 'Aluno ensalado'
        verbose_name_plural = 'Alunos ensalados'
        unique_together = ('distribution', 'student', 'room')