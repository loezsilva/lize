from django.db import models
from fiscallizeon.core.models import BaseModel
# Create your models here.
from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import Grade


class Candidate(BaseModel):
    student = models.OneToOneField(Student, verbose_name="Aluno", on_delete=models.CASCADE)
    financial_responsible_name = models.CharField("Nome do responsável financeiro", max_length=255, null=True, blank=True)
    financial_responsible_phone = models.CharField("Telefone do responsável financeiro", max_length=255, null=True, blank=True)
    previous_school = models.CharField("Instituição anterior", max_length=255, null=True, blank=True)
    note = models.TextField("Alguma observação?", null=True, blank=True)
    cpf = models.CharField("Digite seu CPF", max_length=14, null=True, blank=True)
    
    next_grade = models.ForeignKey(Grade, verbose_name="Qual série irá cursar em 2023?", on_delete=models.PROTECT, null=True, blank=True)


    def __str__(self):
        return self.student.name

    class Meta:
        verbose_name = "Candidato"
        verbose_name_plural = "Candidatos"
        ordering = ['-created_at']