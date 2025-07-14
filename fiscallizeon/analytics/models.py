from django.db import models
from django.contrib.contenttypes.models import ContentType

from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.inspectors.models import TeacherSubject
from fiscallizeon.core.models import BaseModel

from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.inspectors.models import TeacherSubject
from fiscallizeon.questions.models import Question
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.applications.models import Application
from fiscallizeon.analytics.managers import AnalyticsManager

class ApplicationStudentLevelQuestion(BaseModel):
    performance = models.DecimalField(verbose_name="Performance", max_digits=5, decimal_places=2)
    application_student = models.ForeignKey(ApplicationStudent, verbose_name="Aplicação do Aluno", on_delete=models.CASCADE)
    teacher_subject = models.ForeignKey(TeacherSubject, on_delete=models.CASCADE)
    level = models.PositiveSmallIntegerField(choices=Question.LEVEL_CHOICES)
    
    class Meta:
        unique_together=('application_student', 'teacher_subject', 'level')

    def get_exam_name(self):
        return self.application_student.application.exam.name


class ClassSubjectApplicationLevel(BaseModel):
    performance = models.DecimalField(verbose_name="Performance", max_digits=5, decimal_places=2)
    application = models.ForeignKey(Application, verbose_name="Aplicação", on_delete=models.CASCADE, null=True, blank=True)
    teacher_subject = models.ForeignKey(TeacherSubject, on_delete=models.CASCADE)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)
    level = models.PositiveSmallIntegerField(choices=Question.LEVEL_CHOICES, default=0)
    students_quantity = models.PositiveSmallIntegerField(default=1)

    objects = AnalyticsManager()
    
    class Meta:
        unique_together=('application', 'teacher_subject', 'school_class', 'level')

    def get_exam_name(self):
        return self.application.exam.name
    

class GenericPerformances(BaseModel):
    application_student = models.ForeignKey('applications.ApplicationStudent', verbose_name="Aplicação do aluno", on_delete=models.CASCADE, null=True, blank=True)
    student = models.ForeignKey('students.Student', verbose_name="Aluno", on_delete=models.CASCADE, null=True, blank=True)
    subject = models.ForeignKey('subjects.Subject', verbose_name="Disciplina", on_delete=models.CASCADE, null=True, blank=True)
    exam = models.ForeignKey('exams.Exam', verbose_name="Prova", on_delete=models.CASCADE, null=True, blank=True)
    school_class = models.ForeignKey('classes.SchoolClass', verbose_name="Turma", on_delete=models.CASCADE, null=True, blank=True)
    
    performance = models.DecimalField("Desempenho", max_digits=5, decimal_places=2)
    histogram = models.JSONField("Histograma", max_length=255, blank=True, null=True)
    process_time = models.DurationField("Tempo de processamento", null=True, blank=True)
    
    weight = models.PositiveSmallIntegerField(default=1)
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.UUIDField(null=True, blank=True)


class GenericPerformancesFollowUp(BaseModel):
    
    deadline = models.DateField("Data final para correção de respostas", blank=True, null=True)
    cards_deadline = models.DateField("Data final para envio de respostas", blank=True, null=True)
    
    unity = models.ForeignKey('clients.Unity', verbose_name="Unidade", on_delete=models.CASCADE, null=True, blank=True)
    
    inspectors = models.ManyToManyField('inspectors.Inspector', verbose_name="Professor", blank=True)
    
    school_class = models.ForeignKey('classes.SchoolClass', verbose_name="Turma", on_delete=models.CASCADE, null=True, blank=True)
    
    coordination = models.ForeignKey('clients.SchoolCoordination', verbose_name="Coordenação", on_delete=models.CASCADE, null=True, blank=True)
    
    objective_examquestions = models.ManyToManyField('exams.ExamQuestion', related_name="objective_performances", verbose_name="Questões objetivas", blank=True)
    discursive_examquestions = models.ManyToManyField('exams.ExamQuestion', related_name="discursive_performances", verbose_name="Questões Discursivas", blank=True)
    
    # Cards
    objective_cards_quantity = models.IntegerField("Pendencias cartões objetivas", default=0)
    objective_cards_total = models.IntegerField("Total cartões objetivas", default=0)
    
    discursive_cards_quantity = models.IntegerField("Pendencias cartões discursivas", default=0)
    discursive_cards_total = models.IntegerField("Total cartões discursivas", default=0)
    
    
    cards_quantity = models.IntegerField("Pendências total cartões", default=0)
    cards_total = models.IntegerField("Total cartões", default=0)
    
    # Fim
    
    # Respostas
    objective_quantity = models.IntegerField("Pendencias", default=0)
    objective_total = models.IntegerField("Total", default=0)
    
    discursive_quantity = models.IntegerField("Pendencias", default=0)
    discursive_total = models.IntegerField("Total", default=0)
    
    quantity = models.IntegerField("Total", default=0)
    total = models.IntegerField("Total", default=0)
    
    # Fim
    ANSWERS, CARDS, QUESTIONS = range(3)
    TYPES_CHOICES = (
        (ANSWERS, 'Respostas'),
        (CARDS, 'Upaload de cartões'),
        (QUESTIONS, 'Questões solicitadas'),
    )
    
    type = models.SmallIntegerField(("Tipo"), default=ANSWERS, choices=TYPES_CHOICES)
    
    process_time = models.DurationField("Tempo de processamento", null=True, blank=True)
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    
    object_id = models.UUIDField(null=True, blank=True)
    
    class Meta:
        unique_together = (
            ('object_id', 'deadline', 'unity', 'coordination', 'school_class', 'type')
        ),
        
    @staticmethod
    def update_answer_quantity(answer=None, operation_type = 'add', question_id=None, application_student=None):
        
        if not question_id:
            try:
                question_id = answer.question_option.question.id
            except:
                question_id = answer.question.id
                
        application_student = application_student or answer.student_application
        exam = application_student.application.exam
            
        classe = application_student.get_last_class_student()
        try:
            examquestion = ExamQuestion.objects.get(question=question_id, exam=exam)
            question_category = examquestion.question.category
            
        except:
            pass
        
        try:
            if examquestion.weight:
                performance = GenericPerformancesFollowUp.objects.get(
                    models.Q(objective_examquestions=examquestion) if question_category == Question.CHOICE else models.Q(),
                    models.Q(discursive_examquestions=examquestion) if question_category != Question.CHOICE else models.Q(),
                    models.Q(
                        school_class=classe,
                        coordination=classe.coordination,
                    )
                )
                
                if operation_type == 'add':
                    
                    if question_category == Question.CHOICE:
                        performance.objective_quantity = performance.objective_quantity + 1
                    else:
                        performance.discursive_quantity = performance.discursive_quantity + 1

                    performance.quantity = performance.quantity + 1

                else:
                    
                    if performance.quantity > 0:
                        
                        if question_category == Question.CHOICE:
                            performance.objective_quantity = performance.objective_quantity - 1
                        else:
                            performance.discursive_quantity = performance.discursive_quantity - 1                

                        performance.quantity = performance.quantity - 1
                
                performance.save(skip_hooks=True)
        
            
        except:
            pass
            #print("Nenhum performance encontrada")


class MetabaseDashboard(BaseModel):
    name = models.CharField('Título', max_length=255)
    short_name = models.CharField('Título curto', max_length=32)
    embbed_url = models.URLField('URL pública', max_length=500)
    client = models.ForeignKey("clients.Client", verbose_name=("Cliente"), on_delete=models.PROTECT)
    is_active = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Dashboard Metabase'
        verbose_name_plural = 'Dashboards Metabase'