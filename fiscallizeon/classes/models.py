from django.db import models

from fiscallizeon.core.models import BaseModel
from fiscallizeon.students.models import Student
from fiscallizeon.clients.models import SchoolCoordination
from fiscallizeon.classes.managers import SchoolClassManager
from fiscallizeon.clients.models import Client
from django.contrib.contenttypes.fields import GenericRelation
from fiscallizeon.core.storage_backends import PublicMediaStorage


class Grade(BaseModel):
    name = models.CharField("Nome", max_length=50, db_index=True)
    
    HIGHT_SCHOOL, ELEMENTARY_SCHOOL, ELEMENTARY_SCHOOL_2 = range(3)
    LEVEL_CHOICES = (
        (ELEMENTARY_SCHOOL, "Anos iniciais"),
        (ELEMENTARY_SCHOOL_2, "Anos finais"),
        (HIGHT_SCHOOL, "Ensino Médio"),
    )
    level = models.PositiveIntegerField("Ensino", choices=LEVEL_CHOICES, db_index=True)
    order = models.PositiveIntegerField("Index da grade para listagem", default=0, blank=True)

    def __str__(self):
        if self.name.lower() in ["curso", "concurso"]:
            return self.name
        if self.level == self.HIGHT_SCHOOL:
            return f'{self.get_level_display()} - {self.name}ª Série'
        else:
            return f'{self.get_level_display()} - {self.name}º Ano'
    @classmethod
    def get_grade_by_code(cls, code):
        code_to_level = {
            'f1': cls.ELEMENTARY_SCHOOL,
            'f2': cls.ELEMENTARY_SCHOOL,
            'f3': cls.ELEMENTARY_SCHOOL,
            'f4': cls.ELEMENTARY_SCHOOL,
            'f5': cls.ELEMENTARY_SCHOOL,
            'f6': cls.ELEMENTARY_SCHOOL_2,
            'f7': cls.ELEMENTARY_SCHOOL_2,
            'f8': cls.ELEMENTARY_SCHOOL_2,
            'f9': cls.ELEMENTARY_SCHOOL_2,
            'm1': cls.HIGHT_SCHOOL,
            'm2': cls.HIGHT_SCHOOL,
            'm3': cls.HIGHT_SCHOOL,
        }

        level = code_to_level.get(code.lower())
        if level is not None:
            return cls.objects.filter(name=code[1], level=level).first()
        else:
            return None
        
    @property
    def full_name(self):
        if self.level == self.HIGHT_SCHOOL:
            return f'{self.get_level_display()} - {self.name}ª Série'
        else:
            return f'{self.get_level_display()} - {self.name}º Ano'

    def get_complete_name(self):
        if self.level == self.HIGHT_SCHOOL:
            return f'{self.name}ª Série'
        else:
            return f'{self.name}º Ano'

    @property
    def formatted_name(self):
        if self.name.lower() in ['curso', 'concurso']:
            return self.name
        if self.level == self.HIGHT_SCHOOL:
            return f'{self.name}ª Série - {self.get_level_display()}'
        else:
            return f'{self.name}º Ano - {self.get_level_display()}'

    @property
    def name_grade(self):
        if self.level == self.HIGHT_SCHOOL:
            return f'{self.name}ª Série'
        else:
            return f'{self.name}º Ano'
        
    class Meta:
        ordering = ['order']
        
class CourseType(BaseModel):
    name = models.CharField("Nome", max_length=50)
    id_erp = models.CharField("ID ERP", max_length=255, blank=True, null=True)
    client = models.ForeignKey(Client, verbose_name="Cliente", on_delete=models.PROTECT, blank=True)
    class Meta:
        verbose_name = "Tipo de Curso"
        verbose_name_plural = "Tipos de Cursos"
        ordering = ['created_at']
    
    def __str__(self):
        return self.name 
    
class Course(BaseModel):
    name = models.CharField("Nome", max_length=50)
    id_erp = models.CharField("ID ERP", max_length=255, blank=True, null=True)
    client = models.ForeignKey(Client, verbose_name="Cliente", on_delete=models.CASCADE, blank=True)
    course_type = models.ForeignKey(CourseType, verbose_name="Tipo de Curso", on_delete=models.PROTECT)
    class Meta:
        verbose_name = "Cursos"
        verbose_name_plural = "Cursos"
        ordering = ['created_at']
    
    def __str__(self):
        return self.name 

class SchoolClass(BaseModel):
    name = models.CharField("Nome", max_length=250, db_index=True)
    grade = models.ForeignKey(Grade, verbose_name="Série", on_delete=models.CASCADE, null=True, blank=True)
    grade_old = models.CharField("Série antiga", max_length=50, null=True, blank=True)
    coordination = models.ForeignKey(SchoolCoordination, verbose_name="Coordenação responsável", on_delete=models.CASCADE, related_name="school_classes")
    students = models.ManyToManyField(Student, verbose_name="Alunos dessa turma", help_text="Selecione acima os alunos que fazem parte dessa turma", related_name="classes", blank=True)
    is_itinerary = models.BooleanField("É turma itinerária", default=False, help_text="Marque esta opção caso essa turma seja uma turma itinerária.")

    REGULAR, PROBE = range(2)
    CLASS_TYPE_CHOICE = (
        (REGULAR, "Turma Regular"),
        (PROBE, "Turma de Sondagem")
    )
    class_type = models.PositiveSmallIntegerField("Tipo de Turma", choices=CLASS_TYPE_CHOICE, default=REGULAR)

    date = models.DateField("Data da aplicação", null=True, blank=True)
    start = models.TimeField("Início previsto da aplicação", null=True, blank=True)
    end = models.TimeField("Fim previsto da aplicação", null=True, blank=True)

    school_year = models.SmallIntegerField("Ano letivo da turma", default="2025", blank=True, db_index=True)
    temporary_class = models.BooleanField("Turma temporária ou rotativa", default=False, help_text="Marque esta opção caso essa turma não seja regular.")

    id_erp = models.CharField("ID ERP", max_length=255, null=True, blank=True)
    
    integration_token = models.ForeignKey('integrations.IntegrationToken', verbose_name="Token utilizado para integração", on_delete=models.CASCADE, related_name="school_classes", blank=True, null=True)
    
    logo = models.ImageField('Logo da escola', upload_to='classes/clients/logos/', blank=True, null=True, storage=PublicMediaStorage())
    slug = models.CharField('Slug', max_length=255, null=True, blank=True)

    MORNING, AFTERNOON, NIGHT, ALL = range(4)
    COURSE_TYPE_CHOICE = (
        (MORNING, "Manhã"),
        (AFTERNOON, "Tarde"),
        (NIGHT, "Noite"),
        (ALL, "Integral")
    )
    
    turn = models.PositiveSmallIntegerField("Turno", choices=COURSE_TYPE_CHOICE, blank=True, null=True)
    course = models.ForeignKey(Course, verbose_name="Curso", on_delete=models.PROTECT, blank=True, null=True)
    
    performances = GenericRelation('analytics.GenericPerformances', related_query_name="classe_performance")
    
    objects = SchoolClassManager()

    def __str__(self):
        return f'{self.name} - {self.coordination.unity.name if self.coordination.unity else ""} - {self.school_year if self.school_year else ""}'

    class Meta:
        verbose_name = "Turma"
        verbose_name_plural = "Turmas"
        ordering = ['created_at']
        unique_together = ('name', 'school_year', 'coordination', )

    @property
    def count_students(self):
        return self.students.all().count()
    
    def remove_student(self, student):
        self.students.remove(student)
        return
    
    def last_performance(self, exam):
        return self.performances.using('default').filter(exam=exam).order_by('-created_at')
    
class Stage(BaseModel):
    name = models.CharField("Nome", max_length=50)
    id_erp = models.CharField("ID ERP", max_length=255, null=True, blank=True)
    STAGE_TYPE_CHOICE = (
        (1, "N"),
    )
    stage_type = models.PositiveSmallIntegerField("Etapa", choices=STAGE_TYPE_CHOICE, default=1, blank=True, null=True)
    
    def __str__(self):
        return self.name 
    class Meta:
        verbose_name = "Etapas"
        verbose_name_plural = "Etapas"
        ordering = ['created_at']