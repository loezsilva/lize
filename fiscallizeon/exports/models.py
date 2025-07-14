from django.db import models
from fiscallizeon.core.models import BaseModel
from fiscallizeon.core.fields import ChoiceArrayField

class ExportExams(models.Model):
    PRESENT_STUDENTS = 'present'
    ABSENT_STUDENTS = 'absent'

    FORMAT_CSV = 'csv'
    FORMAT_XLS = 'xlsx'

    SUBJECT_GRADES_SUMMED = 'subject_summed'
    SUBJECT_GRADES_COLUMNS = 'subject_columns'
    SUBJECT_GRADES_ROWS = 'subject_rows'

    EXPORT_ROWS = 'rows'
    EXPORT_COLUMNS = 'columns'
    class Meta:
        abstract = True

class Import(BaseModel):
    STUDENTS, TEACHERS, COORDINATIONS, EXAMS, ELABORATION_REQUEST, APPLICATION_STUDENTS, ESSAY_GRADES = 'students', 'students', 'coordinations', 'exams', 'elaboration_request', 'application_students', 'essay_grades'
    TYPE_CHOICES = (
        (STUDENTS, 'students'),
        (TEACHERS, 'teacher'),
        (COORDINATIONS, 'coordinations'),
        (EXAMS, 'Instrumentos avaliativos'),
        (ELABORATION_REQUEST, 'Solicitação de elaboração'),
        (APPLICATION_STUDENTS, 'Alunos em aplicação'),
        (ESSAY_GRADES, 'Notas de redação'),
    )
    type = models.CharField("Onde foi a importação", default='students', choices=TYPE_CHOICES, max_length=50)
    errors = ChoiceArrayField(models.TextField("Erro"), verbose_name="Erro", blank=True, null=True)
    file_url = models.URLField("Arquivo enviado", max_length=500)
    created_by = models.ForeignKey("accounts.User", verbose_name=("Criado por"), on_delete=models.CASCADE)