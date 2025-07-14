from datetime import timedelta
from decimal import Decimal

import json
import os
import math

from django.db import models
from decimal import Decimal
from django_lifecycle import hook

from django.urls import reverse

from simple_history.models import HistoricalRecords
from tinymce.models import HTMLField

from fiscallizeon.accounts.models import User
from fiscallizeon.corrections.models import CorrectionCriterion

from fiscallizeon.exams.models import ExamTeacherSubject, ExamQuestion

from fiscallizeon.questions.models import Question, QuestionOption

from fiscallizeon.core.models import BaseModel
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from django.utils.html import strip_tags

def material_file_directory_path(instance, filename):
    return 'answers/file/{0}/{1}'.format(str(instance.pk), filename)

def teachers_audio_firectory_path(instance, filename):
    return 'answers/teachers/audio/file/{0}/{1}'.format(str(instance.pk), filename)


class RetryAnswer(BaseModel):
    option = models.ForeignKey(
        QuestionOption, verbose_name='alternativa', on_delete=models.PROTECT
    )
    application_student = models.ForeignKey(
        'applications.ApplicationStudent',
        verbose_name='aluno',
        on_delete=models.PROTECT,
    )
    exam_question = models.ForeignKey(
        ExamQuestion,
        verbose_name='questão na prova',
        on_delete=models.PROTECT
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'resposta refeita'
        verbose_name_plural = 'respostas refeitas'

    def __str__(self):
        return f'{self.application_student} - {self.option}'


class OptionAnswer(BaseModel):
    INACTIVE, ACTIVE = range(2)
    STATUS_CHOICES = (
        (INACTIVE, "Inativa"),
        (ACTIVE, "Ativa"),
    )
    question_option = models.ForeignKey(QuestionOption, verbose_name='Alternativa', on_delete=models.PROTECT)
    student_application = models.ForeignKey('applications.ApplicationStudent', verbose_name='Aluno', on_delete=models.PROTECT, related_name="option_answers")
    duration = models.DurationField('Tempo de resposta', default=timedelta(seconds=0))
    status = models.PositiveSmallIntegerField('Status', default=ACTIVE, choices=STATUS_CHOICES)
    index_alternative = models.CharField("Posição da questão na prova", max_length=1, null=True, blank=True)
    created_by = models.ForeignKey(User, verbose_name='Criado por', on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        verbose_name = 'Resposta da alternativa'
        verbose_name_plural = 'Respostas das alternativas'

    def __str__(self):
        return str(self.question_option.question)

    
    def get_teacher_grade(self):
        if self.question_option.is_correct:
            return ExamQuestion.objects.get(exam=self.student_application.application.exam, question=self.question_option.question).weight
        return 0
    
    @hook("before_create")
    def deactivate_before_answers(self):
        from fiscallizeon.analytics.models import GenericPerformancesFollowUp
        
        answers = OptionAnswer.objects.using('default').filter(
            question_option__question=self.question_option.question,
            student_application=self.student_application,
        )
        
        if answers.count() == 0 and not self.question_option.question.id in self.student_application.empty_option_questions.all():
            GenericPerformancesFollowUp.update_answer_quantity(answer=self, operation_type='remove')
        
        answers.using('default').filter(status=self.ACTIVE).update(status=self.INACTIVE)
            
        self.student_application.empty_option_questions.remove(self.question_option.question.id)        
        
    @hook('before_delete')
    def remove_answer_and_generic_performance(self):
        from fiscallizeon.analytics.models import GenericPerformancesFollowUp
        
        # Remove option answers
        answers = OptionAnswer.objects.using('default').filter(
            question_option__question=self.question_option.question,
            student_application=self.student_application,
        )
        
        try:
            GenericPerformancesFollowUp.update_answer_quantity(answer=self, operation_type='remove')
        except Exception as e:
            pass
        
        answers.delete()
        
class DiscursiveHooksMixin:
    
    @hook('after_create')
    def hook_after_create(self):
        from fiscallizeon.analytics.models import GenericPerformancesFollowUp
        GenericPerformancesFollowUp.update_answer_quantity(answer=self, operation_type='remove')
    
    @hook('after_delete')
    def hook_remove_answer(self):
        from fiscallizeon.analytics.models import GenericPerformancesFollowUp
        GenericPerformancesFollowUp.update_answer_quantity(answer=self, operation_type='add')
    
    @hook('before_update', when='empty', has_changed=True, is_now=True)
    def remove_teacher_grade(self):
        self.teacher_grade = None
    
    @hook('before_update', when='teacher_grade', has_changed=True)
    def remove_empty(self):
        from fiscallizeon.analytics.models import GenericPerformancesFollowUp
        if self.initial_value('teacher_grade') is None and self.teacher_grade is not None:
            
            if not self.empty:
                GenericPerformancesFollowUp.update_answer_quantity(answer=self, operation_type='remove')
            
            self.empty = False
        
class TextualAnswer(BaseModel, DiscursiveHooksMixin):
    question = models.ForeignKey(Question, verbose_name='Questão', on_delete=models.PROTECT)
    exam_question = models.ForeignKey(ExamQuestion, verbose_name='Questão da prova', on_delete=models.PROTECT, blank=True, null=True)
    student_application = models.ForeignKey('applications.ApplicationStudent', verbose_name='Aluno', on_delete=models.PROTECT, related_name="textual_answers")
    duration = models.DurationField('Tempo de resposta', default=timedelta(seconds=0))

    content = HTMLField('Texto da resposta', null=True, blank=True)

    teacher_feedback = models.TextField('Correção do professor', null=True, blank=True)
    teacher_grade = models.DecimalField("Nota atribuída", max_digits=10, decimal_places=6, null=True, blank=True)

    grade = models.DecimalField("Nota percentual", max_digits=7, decimal_places=6, null=True, blank=True)

    who_corrected = models.ForeignKey(User, verbose_name='Corrigido por', on_delete=models.PROTECT, null=True, blank=True)
    corrected_but_no_answer = models.BooleanField('Resposta corrigida mas sem resposta do aluno', default=False, blank=True)

    correction_textual_answer = models.ManyToManyField(CorrectionCriterion, through='corrections.CorrectionTextualAnswer', verbose_name='Correção textual')

    empty = models.BooleanField("Deixou em branco", default=False)

    class Meta:
        verbose_name = 'Resposta textual'
        verbose_name_plural = 'Respostas textual'
        unique_together = ('question', 'student_application',)

    def __str__(self):
        return str(self.question)

    def content_escaped(self):
        return self.content.replace("\\", "\\\\").replace('&quot;', '\\"').replace('"', '\\"')

    @hook('before_save')
    def set_grade(self):
        exam_question = self.exam_question
        if not exam_question:
            exam_question = ExamQuestion.objects.filter(
                exam=self.student_application.application.exam_id,
                question=self.question,
            ).first()
            self.exam_question = exam_question

        if not self.exam_question:
            return

        proportion = 0
        if exam_question.weight and self.teacher_grade is not None:
            proportion = Decimal(self.teacher_grade / exam_question.weight)
        
            self.grade = proportion if proportion <= 1 else Decimal(1)
    
    @property
    def urls(self):
        return {
            "update_api": reverse("answers:text_retrieve_update", kwargs={ "pk": self.pk })
        }
    

class FileAnswer(BaseModel, DiscursiveHooksMixin):
    question = models.ForeignKey(Question, verbose_name='Questão', on_delete=models.PROTECT)
    exam_question = models.ForeignKey(ExamQuestion, verbose_name='Questão da prova', on_delete=models.PROTECT, blank=True, null=True)
    student_application = models.ForeignKey('applications.ApplicationStudent', verbose_name='Aluno', on_delete=models.PROTECT, related_name="file_answers")
    duration = models.DurationField('Tempo de resposta', default=timedelta(seconds=0))

    arquivo = models.FileField(verbose_name='Arquivo anexado', upload_to=material_file_directory_path, null=True, blank=True, storage=PrivateMediaStorage())

    teacher_audio_feedback = models.FileField(verbose_name='Arquivo de audio do professor', upload_to=teachers_audio_firectory_path, null=True, blank=True, storage=PrivateMediaStorage())
    teacher_feedback = models.TextField('Correção do professor', null=True, blank=True)
    teacher_grade = models.DecimalField("Nota atribuída", max_digits=10, decimal_places=6, null=True, blank=True)

    grade = models.DecimalField("Nota percentual", max_digits=7, decimal_places=6, null=True, blank=True)
    
    img_annotations = models.JSONField(("Anotações das imagens"), null=True, blank=True)

    ip = models.GenericIPAddressField(blank=True, null=True)
    send_on_qrcode = models.BooleanField('Via QRCode', default=False)

    annotations_teaher = models.JSONField(verbose_name='Anotações do professor', null=True, blank=True)

    who_corrected = models.ForeignKey(User, verbose_name='Corrigido por', on_delete=models.PROTECT, null=True, blank=True)
    corrected_but_no_answer = models.BooleanField('Corrigida mas sem resposta do aluno', default=False, blank=True)
    
    correction_file_answer = models.ManyToManyField(CorrectionCriterion, through='corrections.CorrectionFileAnswer', verbose_name='Correções', blank=True)

    empty = models.BooleanField("Deixou em branco", default=False)
    
    essay_was_corrected = models.BooleanField("A redação foi corrigida", default=False, blank=True)

    ai_grade = models.DecimalField("Nota atribuída pela IA", max_digits=7, decimal_places=6, null=True, blank=True)
    ai_teacher_feedback = models.TextField('Feedback para o professor', null=True, blank=True)
    ai_student_feedback = models.TextField('Feedback para o aluno', null=True, blank=True)
    ai_suggestion_accepted = models.BooleanField('Sugestão da IA aceita pelo professor', default=False)

    class Meta:
        verbose_name = 'Arquivo anexado'
        verbose_name_plural = 'Arquivos anexados'

    def __str__(self):
        return str(self.question)
    
    @hook('before_save')
    def set_grade(self):
        exam_question = self.exam_question
        if not exam_question:
            exam_question = ExamQuestion.objects.filter(
                exam=self.student_application.application.exam_id,
                question=self.question,
            ).first()
            self.exam_question = exam_question

        if not self.exam_question:
            return

        proportion = 0
        if exam_question.weight and self.teacher_grade is not None:
            proportion = Decimal(self.teacher_grade / exam_question.weight)
        
            self.grade = proportion if proportion <= 1 else Decimal(1)

class Attachments(BaseModel):
    application_student = models.ForeignKey('applications.ApplicationStudent', verbose_name='Aplicação do aluno', related_name="attachments", on_delete=models.PROTECT)
    file = models.FileField(verbose_name='Arquivo anexado', upload_to=material_file_directory_path, storage=PrivateMediaStorage())
    exam_teacher_subject = models.ForeignKey(ExamTeacherSubject, verbose_name='Anexado por', on_delete=models.PROTECT, related_name="attachments")
    send_on_qrcode = models.BooleanField('Via QRCode', default=False)

    @hook('before_create')
    def before_create(self):
        exist = Attachments.objects.filter(application_student=self.application_student, exam_teacher_subject=self.exam_teacher_subject).exists()

        if exist:
            return
        
        exam_questions = self.application_student.application.exam.examquestion_set.filter(question__category=Question.FILE, exam_teacher_subject=self.exam_teacher_subject).availables()
        for exam_question in exam_questions:
            FileAnswer.objects.get_or_create(
                question = exam_question.question,
                student_application = self.application_student,
            )
            
    @property
    def filename(self):
        return os.path.basename(self.file.name)
    
class ProofAnswer(BaseModel):
    code = models.CharField("Código do comprovante", max_length=8)
    application_student = models.ForeignKey('applications.ApplicationStudent', verbose_name='Aluno', on_delete=models.PROTECT, related_name="proofs")
    exam_name = models.CharField("Nome do caderno", max_length=150)
    start_date = models.DateTimeField("Data inicial da aplicação")
    end_date = models.DateTimeField("Data final da aplicação")
    group_attachments = models.BooleanField("Os anexos são agrupados", default=False)
    is_randomized = models.BooleanField("É randomizado", default=False)
    answers_json = models.JSONField("Respostas das alternativas")
    
    class Meta:
        verbose_name = 'Comprovante de resposta'
        verbose_name_plural = 'Comprovantes de respostas'

    def __str__(self):
        return f"{self.application_student} - {self.exam_name}"
    
    def answers_json_serailized(self):
        return json.dumps(self.answers_json)


class SumAnswerQuestionOption(BaseModel):
    sum_answer = models.ForeignKey('answers.SumAnswer', verbose_name='Resposta de somatório', on_delete=models.CASCADE)
    question_option = models.ForeignKey(QuestionOption, verbose_name='Alternativa', on_delete=models.CASCADE)
    checked = models.BooleanField('Marcada', default=False)

    def __str__(self):
        return str(self.question_option.pk)

    class Meta:
        verbose_name = 'Resposta de alternativa de somatório'
        verbose_name_plural = 'Respostas de alternativas de somatório'


class SumAnswer(BaseModel):
    value = models.PositiveSmallIntegerField('Valor do somatório', default=0)
    empty = models.BooleanField('Resposta em branco ou anulada', default=False)
    grade = models.DecimalField('Nota calculada', max_digits=10, decimal_places=6, null=True, blank=True)
    question = models.ForeignKey(Question, verbose_name='Questão', on_delete=models.PROTECT, related_name="sum_answers")
    student_application = models.ForeignKey('applications.ApplicationStudent', verbose_name='Aluno', on_delete=models.PROTECT, related_name="sum_answers")
    question_options = models.ManyToManyField(QuestionOption, through=SumAnswerQuestionOption, verbose_name='Alternativas')
    created_by = models.ForeignKey(User, verbose_name='Criado por', on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        verbose_name = 'Resposta de somatório'
        verbose_name_plural = 'Respostas de somatório'

    def __str__(self):
        return str(self.question)
    
    def get_value_using_indexes(self, indexes):
        values = [1, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768] # Vai depender da questidade de options que tem no front.
        total_sum = sum(values[i] for i in indexes)
        return total_sum
    
    def get_factors(self):
        _value = int(self.value)
        powers = [2**i for i, _ in enumerate(self.question.alternatives.using('default').all().order_by('-index'))]
        powers.reverse()
        factors = [p for p in powers if _value >= p and (_value := _value - p) >= 0]

        if sum(factors) == int(self.value):
            return sorted(factors)
        return []
    
    def create_sum_option_answers(self):
        factors = self.get_factors()

        if not factors:
            self.empty = True
            self.save()
            return False

        indexes = [int(math.log2(int(x))) for x in factors]

        for index, question_option in enumerate(self.question.alternatives.using('default').all().order_by('index')):
            SumAnswerQuestionOption.objects.create(
                sum_answer=self,
                question_option=question_option,
                checked=index in indexes
            )

        return True
    
    def get_grade_proportion(self):
        """
        Baseado no edital da UFSC 2024
        """
        if self.empty:
            return 0
        
        total_items = self.question.alternatives.using('default').all().count()
        total_correct_items = self.question.alternatives.using('default').filter(
            is_correct=True
        ).count()

        correct_assumptions = self.sumanswerquestionoption_set.using('default').filter(
            checked=True,
            question_option__is_correct=True,
        ).count()

        incorrect_assumptions = self.sumanswerquestionoption_set.using('default').filter(
            checked=True,
            question_option__is_correct=False,
        ).count()

        if incorrect_assumptions >= correct_assumptions:
            return 0
        
        assumptions_diff = correct_assumptions - incorrect_assumptions
        grade = (total_items - (total_correct_items - assumptions_diff)) / total_items
        return Decimal.from_float(round(grade, 2))
    
    def reset_sum_answer(self):
        self.question_options.clear() 
        self.value = 0  
        self.grade = None 
        self.save() 