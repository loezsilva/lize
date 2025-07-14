import time
import uuid
import math

from itertools import tee
from datetime import timedelta
from decimal import Decimal
from statistics import fmean

import numpy as np

from django_lifecycle import hook
from tinymce.models import HTMLField
from simple_history.models import HistoricalRecords
from urllib.parse import urlencode

from django.urls import reverse
from django.apps import apps
from django.db import models
from django.conf import settings
from django.core.cache import cache
from django.forms import model_to_dict
from django.utils import timezone
from django.template.loader import get_template
from django.db.models import (
    Avg, Count, F, IntegerField, OuterRef, Q, Subquery, Sum, Value, Case, When, Value
)
from django.contrib.contenttypes.fields import GenericRelation
from django.db.models.functions import Coalesce, Round
from django.core.validators import MinValueValidator
from django.utils.functional import cached_property


from fiscallizeon.classes.models import Grade, SchoolClass
from fiscallizeon.core.models import BaseModel
from fiscallizeon.core.utils import round_half_up, generate_random_string
from fiscallizeon.questions.models import Question
from fiscallizeon.clients.models import QuestionTag, SchoolCoordination, Unity
from fiscallizeon.inspectors.models import TeacherSubject
from fiscallizeon.accounts.models import User
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.core.threadings.sendemail import EmailThread
from fiscallizeon.integrations import realms
from fiscallizeon.exams.managers import ExamManager, ExamTeacherSubjectManager, ExamQuestionManager
from fiscallizeon.core.gcp.utils import get_service_account_oauth2_token
from fiscallizeon.applications.threadings import IgnoreCacheTriDataThread

def to_percentage(value, total):
    result = round((value / total) * 100, 2) if total else 0

    if result % 2 == 0:
        return int(result)

    return result


class Exam(BaseModel):
    questions = models.ManyToManyField(Question, through='exams.ExamQuestion', verbose_name='Questões', related_name="exams")
    teacher_subjects = models.ManyToManyField(TeacherSubject, through='exams.ExamTeacherSubject', verbose_name="Professor/Disciplina") 
    coordinations = models.ManyToManyField(SchoolCoordination, verbose_name="Coordenações autorizadas a acessar este caderno", related_name="exams")
    correction_by_subject = models.BooleanField('Permitir correção/visualização por professores da mesma disciplina', default=False)
    source_exam = models.ForeignKey('Exam', related_name="exam_copies", on_delete=models.SET_NULL, null=True, blank=True)

    ELABORATING, OPENED, CLOSED, SEND_REVIEW, TEXT_REVIEW, READY_PRINT, PDF_REVIEW= range(7)
    STATUS_CHOICES = (
        (ELABORATING, 'Elaborando'),
        (OPENED, 'Revisão de itens'),
        (CLOSED, 'Fechada'),
        (SEND_REVIEW, 'Diagramação'),
        (TEXT_REVIEW, 'Revisão de texto'),
        (READY_PRINT, 'Pronto para impressão'),
        (PDF_REVIEW, "Revisão de PDF"),
    )
    EXAM, HOMEWORK = range(2)
    CATEGORY_CHOICES = (
        (EXAM, 'Prova'),
        (HOMEWORK, 'Lista de Exercício'),     
    )
    name = models.CharField('Título da avaliação', max_length=255)
    status = models.PositiveSmallIntegerField('Situação do caderno', choices=STATUS_CHOICES, default=ELABORATING)
    random_alternatives = models.BooleanField(verbose_name="Embaralhar alternativas?", default=False)
    random_questions = models.BooleanField(verbose_name="Embaralhar questões?", default=False)
    elaboration_deadline = models.DateField(verbose_name="Prazo para elaboração", auto_now=False, null=True)
    review_deadline = models.DateField(verbose_name="Prazo para revisão de questões", auto_now=False, null=True, blank=True)
    release_elaboration_teacher = models.DateField(verbose_name="Liberação para elaboração do professor", auto_now=False, null=True)
    review_deadline_pdf = models.DateField(verbose_name="Prazo para elaborador revisar o PDF", auto_now=False, null=True, blank=True)
    group_by_topic = models.BooleanField(verbose_name="Embaralhar disciplinas?", default=False)

    category = models.PositiveSmallIntegerField('Tipo da avaliação', choices=CATEGORY_CHOICES, default=EXAM)
    is_abstract = models.BooleanField('O caderno é abstrato, usada apenas na geração de gabarito avulso', default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exams_created", verbose_name="Criado por", null=True, blank=True)

    PER_QUESTION, SUBJECT_TOP, EXAM_TOP, EXAM_BOTTOM = range(4)
    BASE_TEXT_LOCATION_CHOICES = (
        (PER_QUESTION, 'Textos base por questão'),
        (SUBJECT_TOP, 'Textos base por disciplina'),
        (EXAM_TOP, 'Textos base no início do caderno'),
        (EXAM_BOTTOM, 'Textos base no final do caderno'),
    )
    base_text_location = models.PositiveSmallIntegerField('Situação da prova', choices=BASE_TEXT_LOCATION_CHOICES, default=PER_QUESTION)
    
    history = HistoricalRecords(excluded_fields=['created_at', 'updated_at']) 

    is_english_spanish = models.BooleanField("Caderno com língua estrangeira", help_text="Ative esta opção se deseja que o aluno selecione uma língua estrangeira para realizar a prova", default=False)
    start_number = models.PositiveIntegerField("Qual número irá iniciar este caderno?", default=1, validators=[MinValueValidator(1)])
    
    total_grade = models.DecimalField("Nota geral do caderno", help_text="Você pode deixar essa valor em branco caso deseje escolher as notas de acordo com os professores inseridos no caderno", blank=True, null=True, decimal_places=2, max_digits=10)
    
    group_attachments = models.BooleanField(verbose_name="Agrupar anexos", default=False, help_text="Ativa esta opção se deseja que os alunos envie as respostas de anexo agrupadas ao final de cada disciplina.")
    show_ranking = models.BooleanField(
        verbose_name='mostrar colocação do aluno na avaliação',
        default=False,
        help_text='Ativa esta opção se deseja que os alunos vejam sua posição na prova.'
    )

    performances = GenericRelation('analytics.GenericPerformances', related_query_name="exam_performance")

    exam_print_config = models.OneToOneField(
        'clients.ExamPrintConfig',
        verbose_name='configuração de impressão',
        on_delete=models.PROTECT,
        related_name='exams',
        null=True,
        blank=True,
    )
    
    teaching_stage = models.ForeignKey('clients.TeachingStage', on_delete=models.PROTECT, verbose_name="Etapa do ensino", null=True, blank=True)
    education_system = models.ForeignKey('clients.EducationSystem', on_delete=models.PROTECT, verbose_name="Sistema de ensino", null=True, blank=True)
    
    is_printed = models.BooleanField("Já foi impresso", default=False)
    
    ELEMENTARY_SCHOOL, ELEMENTARY_SCHOOL_2, HIGHT_SCHOOL = range(3)
    
    orientations = HTMLField("Orientações para a prova", blank=True, null=True)
    id_erp = models.CharField(
        'código de exportação', max_length=255, blank=True, null=True,
    )
    last_erp_sync = models.DateTimeField("Data da última sincronização com o ERP", null=True, blank=True)
    
    related_subjects = models.BooleanField("Relacionar disciplinas", default=False)
    relations = models.ManyToManyField("subjects.SubjectRelation", verbose_name=("Disciplinas relacionadas"), blank=True)
    
    performances_followup = GenericRelation('analytics.GenericPerformancesFollowUp', related_query_name="followup_performances")
    
    is_enem_simulator = models.BooleanField("É um simulado Enem", default=False, blank=True)
    external_code = models.PositiveIntegerField(
        "Código de prova",
        help_text="Código a ser utilizado para o aluno identificar o caderno no cartão resposta",
        blank=True,
        null=True
    )
    not_applicable = models.BooleanField("não permitir aplicação do caderno", default=False, help_text="Marque esta opção se deseja que esse caderno não seja usado em aplicações.")
    four_alternatives = models.BooleanField("Caderno com 4 alternativas por questão", default=False, help_text="Ative esta opção se deseja que o caderno tenha 4 alternativas por questão")
    
    ALTERNATIVE_CHOICES = [(i, str(i)) for i in range(2, 6)]
    template_quantity_alternatives = models.PositiveSmallIntegerField(
        'quantidade de alternativas',
        choices=ALTERNATIVE_CHOICES,
        blank=True,
        null=True
    )
    quantity_alternatives = models.PositiveSmallIntegerField(
        'quantidade de alternativas', validators=[MinValueValidator(2)], blank=True, null=True,
    )
    copy_exam_with_ia_count = models.PositiveSmallIntegerField('Quantidade de copias feitas por IA', default=0)
    exam_used_for_copying = models.CharField('Exam usado para realizar a copia',max_length=255, blank=True, null=True)

    WAITING, COPYING, FINISHED, ERROR, OTHER = range(5)
    
    COPY_EXAM_WITH_IA_STATUS = (
        (WAITING, "Aguardando"),
        (COPYING, "Copiando"),
        (FINISHED, "Finalizado"),
        (ERROR, "Erro"),
        (OTHER, "Desconhecido"),
    )

    copy_exam_with_ia_status = models.PositiveSmallIntegerField(
        'Status da cópia do caderno com Ia', 
        choices=COPY_EXAM_WITH_IA_STATUS, 
        default=WAITING
    )

    enable_discursive_ai_correction = models.BooleanField(
        "Habilitar correção automática de discursivas", 
        default=False, 
        help_text="Marque esta opção se deseja que esse caderno traga sugestões de correção das questões discursivas"
    )

    is_confidential = models.BooleanField(
        "Caderno confidencial",
        default=False,
        help_text="Marque esta opção se deseja que o caderno seja confidencial"
    )

    confidential_date = models.DateField(
        "Data que passa a ser confidencial",
        auto_now=False,
        blank=True,
        null=True
    )
    
    objects = ExamManager()
    
    class Meta:
        verbose_name = 'Caderno'
        verbose_name_plural = 'Cadernos'
        ordering = ('-created_at', )
        permissions = (
            ('can_change_status_exam', 'Pode alterar o status dos cadernos'),
            ('can_diagram_exam', 'Pode diagramar cadernos'),
            ('can_review_questions_exam', 'Pode revisar questões dos caderno'),
            ('can_view_result_exam', 'Pode visualizar resultado dos caderno'),
            ('can_correct_answers_exam', 'Pode corrigir respostas dos cadernos'),
            ('can_print_exam', 'Pode imprimir cadernos'),
            ('can_duplicate_exam', 'Pode duplicar cadernos'),

            ('export_results_exam', 'Pode exportar dados dos cadernos'),
            ('can_import_exams', 'Pode importar cadernos'),
            ('can_import_examteachersubjects', 'Pode importar solicitações a professores'),
            # Gabarito avulso
            ('view_template_exam', 'Pode visualizar gabarito avulso'),
            ('add_template_exam', 'Pode adicionar gabarito avulso'),
            ('change_template_exam', 'Pode alterar gabarito avulso'),
            ('delete_template_exam', 'Pode deletar gabarito avulso'),
            ('print_template_exam', 'Pode imprimir gabarito para divulgação'),
            ('export_template_exam_results', 'Pode exportar dados de gabarito avulso'),
            ('can_duplicate_template_exam', 'Pode duplicar gabarito avulso'),
            ('can_view_confidential_exam', 'Pode visualizar caderno confidencial'),

        )

    def can_edit_content(self):
        if (self.status in [self.CLOSED, self.READY_PRINT]) or self.application_set.filter(
            Q(
                Q(answer_sheet__isnull=False),
                ~Q(answer_sheet="")
            )
        ).exists():
            return False
        
        return True
        
    def _pair_iterable_for_delta_changes(self, iterable):
        a, b = tee(iterable)
        next(b, None)
        return zip(a,b)
    
    def elaboration_deadline_is_past(self):
        now = timezone.localtime(timezone.now())
        if self.elaboration_deadline:
            return self.elaboration_deadline <= now
        return False
    def changes(self):
        poll_iterator = self.history.all().order_by('history_date').iterator()
        list_changes = []
        for record_pair in self._pair_iterable_for_delta_changes(poll_iterator):
            old_record, new_record = record_pair
            delta = new_record.diff_against(old_record)

            # if not delta.changes:
            #     continue

            fields = []
            for change in delta.changes:
                fields.append(getattr(type(self), change.field).field.verbose_name.capitalize())

            list_changes.append({
                'history_date': new_record.history_date,
                'history_user': new_record.history_user,
                'fields': ', '.join(fields),
            })

        return reversed(list_changes)
    
    @property
    def urls(self):
        
        data = {
            "change_is_printed": reverse('exams:api-exam-change-is-printed', kwargs={ "pk": self.pk }),
            "print_exam_with_print_service": reverse('exams:print-exam-with-print-service', kwargs={ "pk": self.pk }),
            
            # APIS Freemium
            "api_freemium_detail": reverse('exams:freemium-detail', kwargs={ "pk": self.pk }),
            
            "get_applications_student": reverse('exams:api-exam-get-applications-student', kwargs={ 'pk': self.pk })
        }

        if self.exam_print_config:
            data["print_configs"] = reverse('api:clients:print-configs-get-config', kwargs={ "pk": self.exam_print_config.pk })

        return data
    
    @property
    def urls_v3(self):
        return {
            
        }

    @property
    def exam_detailed_history(self):
        detailed_history = []
        fields_name_map = {
            "total_grade": "Nota geral",
            "elaboration_deadline": "Prazo para elaboração",
            "release_elaboration_teacher": "Liberação para elaboração do professor",
        }

        records = self.history.all()

        for i in range(len(records) - 1):
            record = records[i]
            detailed_record = {
                "history_date": record.history_date,
                "history_user": record.history_user,
                "status": record.get_status_display(),
                "diffs": []
            }
            for diff in record.diff_against(record.prev_record, included_fields=['elaboration_deadline', 'release_elaboration_teacher', 'total_grade']).changes:
                if diff.field in fields_name_map:
                    detailed_record['diffs'].append({
                        "field": fields_name_map[diff.field],
                        "old_value": diff.old,
                        "new_value": diff.new,
                    })

            detailed_history.append(detailed_record)

        return detailed_history

    def check_teacher_subjects(self, teacher):
        count = self.examteachersubject_set.filter(teacher_subject__teacher=teacher).count()
        
        check_data = {"count": count}
        
        if count == 1:
            check_data["pk"] = self.examteachersubject_set.get(teacher_subject__teacher=teacher).pk
        
        return check_data

    def get_printing_params(self):
        return urlencode(self.get_filters_to_print())
    
    def get_discursive_questions(self):
        return self.questions.availables(self).filter(
            category__in=[Question.TEXTUAL, Question.FILE] 
        )

    @property
    def is_randomized(self):
        return self.random_alternatives or self.random_questions or self.group_by_topic

    @property
    def has_choice_questions(self):
        return self.questions.availables(self).filter(
            category=Question.CHOICE
        ).exists()

    @property
    def has_discursive_questions(self):
        return self.get_discursive_questions().exists()
    
    @property
    def has_sum_questions(self):
        return self.questions.availables(self).filter(
            category__in=[Question.SUM_QUESTION] 
        ).exists()
    
    @property
    def has_essay_questions(self):
        return self.get_discursive_questions().filter(
            is_essay=True,
        ).exists()
    
    def has_text_correction_questions(self):
        return self.questions.availables(self).filter(
            text_correction__isnull=False
        ).exists()
    
    @property
    def is_subject_sheet_allowed(self):
        if self.has_foreign_languages:
            return False

        return not self.get_subject_questions_count().filter(total__gt=15).exists()
    
    @property
    def is_reduced_allowed_max_questions(self):
        total_questions_objective = self.get_questions().filter(category=Question.CHOICE).count()
        total_questions_foreing = self.get_foreign_exam_questions().count() / 2
        total_question_without_foreign = total_questions_objective - total_questions_foreing

        if total_question_without_foreign is None or total_question_without_foreign < 0:
            total_question_without_foreign = 0

        return total_question_without_foreign <=36

    def get_is_inspector_ia(self):
        return self.teacher_subjects.all().filter(
            teacher__is_inspector_ia=True 
        ).exists()

        # for teacher_subjec in self.teacher_subjects.all():
        #     if teacher_subjec.teacher.is_inspector_ia:
        #         return True
        # return False
            
    @hook("after_save", when="is_english_spanish", is_now=False, has_changed=True)
    def update_exam_teacher_subjects(self):
        if not self.is_abstract:
            self.examteachersubject_set.all().update(
                is_foreign_language=False
            )

    @hook("after_save", when="release_elaboration_teacher", has_changed=True)
    def update_send_email_exam_teachers(self):
        self.examteachersubject_set.all().update(elaboration_email_sent=False)

    @hook("after_save")
    def clear_cache(self):
        self.clear_questions_numbers_cache()
        
    @hook("after_update", when="total_grade", has_changed=True)
    def distribute_weights(self, exam_teacher_subject=None, force_distribute_weights=0, distribute_exam_teacher_subject=False):
        """
            DOC_GTMPHNN6
            A idéia é distribuir os pesos igualmente entre as questões do caderno
        """
        # Início: Obtendo todos os professores adicionados ao EXAM
        # Nesse caso, o parâmetro exam_teacher_subject pode ou não ser passado 
        examteachersubjects = self.examteachersubject_set.using('default').filter(
            
            Q(pk=exam_teacher_subject.id) if exam_teacher_subject and not self.total_grade and not force_distribute_weights else Q()
        )
        
        # Variável responsável por armazenar a quantidade total de pesos bloqueados por questão ou por solicitação (ExamTeacherSubject)
        blocked_weights_total = 0

        # Caso seja uma anulação e a distribuição seja apenas para a solicitação, fazer o processo apenas para essa solicitação
        examteachersubjects = examteachersubjects.filter(Q(pk=exam_teacher_subject.id) if exam_teacher_subject and distribute_exam_teacher_subject else Q())

        # Filtrando apenas as solicitações que foram bloqueadas
        examteachersubjects_blockeds = examteachersubjects.filter(Q(block_subject_note=True) | Q(subject_note__gte=0))

        # Filtrando todas as solicitações que não foram bloqueadas
        examteachersubjects_without_blockeds = examteachersubjects.exclude(pk__in=examteachersubjects_blockeds)
        
        # Looping através das solicitações que foram bloqueadas
        for examteachersubject in examteachersubjects_blockeds:

            # Pego as questões dessa solicitação
            exam_questions = self.examquestion_set.using('default').filter(exam_teacher_subject=examteachersubject).availables(exclude_annuleds=True, include_give_score=True)

            # Calculando a soma dos pesos bloqueados
            blocked_weights = exam_questions.filter(block_weight=True).aggregate(Sum('weight')).get('weight__sum') or 0
            exam_question_without_block_weight = exam_questions.exclude(block_weight=True)
            
            # Calculando o peso a ser distribuído para as questões desbloqueadas
            weight_to_distribute = (examteachersubject.subject_note or 0) - (blocked_weights or 0)

            # Adicionando o peso bloqueado ao total de pesos bloqueados
            blocked_weights_total += (examteachersubject.subject_note if examteachersubject.subject_note else 0)
            
            # Atualizando os pesos das questões desbloqueadas, se houver
            if exam_question_without_block_weight:
                exam_question_without_block_weight.using('default').update(weight=round_half_up(Decimal(weight_to_distribute / exam_question_without_block_weight.count()), 6))        
    
        # Filtrando as questões associadas às solicitações que não foram bloqueadas
        exam_questions = self.examquestion_set.using('default').filter(exam_teacher_subject__in=examteachersubjects_without_blockeds).availables(exclude_annuleds=True, include_give_score=True)

        # Verificando se há questões e se há uma nota total e a distribuição é para o caderno todo
        if exam_questions and self.total_grade and not distribute_exam_teacher_subject:
            # Filtrando as questões desbloqueadas
            exam_question_without_block_weight = exam_questions.exclude(block_weight=True)
            
            # Calculando a soma dos pesos bloqueados
            blocked_weights = exam_questions.filter(block_weight=True).aggregate(Sum('weight')).get('weight__sum') or 0
            
            # Calculando o peso a ser distribuído para as questões desbloqueadas
            weight_to_distribute = self.total_grade - blocked_weights - blocked_weights_total
            
            # Atualizando os pesos das questões desbloqueadas, se houver
            if exam_question_without_block_weight:
                exam_question_without_block_weight.using('default').update(weight=round_half_up(Decimal(weight_to_distribute / exam_question_without_block_weight.count()), 6))
        
        # Lógica para questões que são anuladas, forçar a redistribuição dos pontos da questão que foi anulada
        elif exam_questions and force_distribute_weights:
            
            # Filtrando as questões desbloqueadas
            exam_question_without_block_weight = exam_questions.exclude(block_weight=True)

            # Filtrando as questões com pesos bloqueados
            blocked_weights = exam_questions.filter(block_weight=True)
            
            # Faz o calculo para saber quando será acrescentado a cada questão desbloqueada 
            proportion = (force_distribute_weights / exam_question_without_block_weight.count())
            weight_to_distribute = (force_distribute_weights - (proportion * blocked_weights.count())) / exam_question_without_block_weight.count()

            exam_question_without_block_weight.using('default').update(weight=F('weight') + round_half_up(Decimal(weight_to_distribute), 6))

    @hook("before_delete")
    def delete_erp(self):
        Integration = apps.get_model('integrations', 'Integration')
        client = self.coordinations.first().unity.client
        if not client:
            return
        
        has_realms_integration = Integration.objects.filter(
            client=client,
            erp=Integration.REALMS,
        ).exists()

        if not has_realms_integration:
            return
        
        if self.id_erp:
            realms.delete_exam(client, self)

    def __str__(self):
        return self.name + '-'

    @cached_property
    def total_weight(self):
        if self.is_english_spanish:
            questions_language = self.examquestion_set.availables().filter(is_foreign_language=True)
            pks = [f'{examquestion.pk}' for examquestion in questions_language[:questions_language.count()/2]]
            
            return self.examquestion_set.availables(exclude_annuleds=True).exclude(pk__in=pks).aggregate(
                total_weight=Coalesce(Sum('weight'), Decimal('0'))
            )['total_weight']

        return self.examquestion_set.availables(exclude_annuleds=True).aggregate(
            total_weight=Coalesce(Sum('weight'), Decimal('0'))
        )['total_weight']

    @cached_property
    def total_question(self):
        if self.is_english_spanish:
            quantity_foreign_language_questions = self.examquestion_set.availables().filter(is_foreign_language=True).count() / 2
            pks = [f'{examquestion.pk}' for examquestion in self.examquestion_set.availables().filter(is_foreign_language=True)[:quantity_foreign_language_questions]]
            return self.examquestion_set.availables().exclude(pk__in=pks).count()

        return self.examquestion_set.availables().count()
    
    def count_availables_questions(self):
        return self.examquestion_set.availables().count()

    def quantity_questions_requested(self):
        return self.examteachersubject_set.aggregate(
            quantity_questions_requested=Sum('quantity')
        )['quantity_questions_requested']

    @cached_property
    def percentage_questions_status(self):
        if self.count_availables_questions() == 0:
            return 0

        percentage = self.count_availables_questions() / (self.quantity_questions_requested() or 1) * 100

        if percentage >= 100:
            return 100
        
        return round(percentage)

    @cached_property
    def new_percentage_status_questions(self):
        
        exam_questions = self.examquestion_set.only('pk')
        
        status_question_query = StatusQuestion.objects.filter(exam_question__in=exam_questions).distinct().only('pk')

        approved_questions = status_question_query.filter(status=StatusQuestion.APPROVED, active=True).count()
        use_later_questions = status_question_query.filter(status=StatusQuestion.USE_LATER, active=True).count()

        approved_and_use_later_questions = approved_questions + use_later_questions
        requested_questions = self.quantity_questions_requested() or 0
        total = exam_questions.availables(exclude_use_later=False).count()
        other_questions = total - approved_and_use_later_questions
        missing_questions = requested_questions - approved_and_use_later_questions - other_questions
        total_delivered = approved_and_use_later_questions + other_questions
        
        return {
            'requested': requested_questions,
            'approved_and_use_later_questions': approved_and_use_later_questions,
            'other_questions': other_questions,
            'missing_questions': missing_questions,
            'approved_and_use_later_questions_percentage': f'{to_percentage(approved_and_use_later_questions, requested_questions)}'.replace(',', '.'),
            'total_delivered_percentage': f'{to_percentage(total_delivered, requested_questions)}'.replace(',', '.'),
            'other_questions_percentage': f'{to_percentage(other_questions, requested_questions)}'.replace(',', '.'),
            'missing_questions_percentage': f'{to_percentage(missing_questions, requested_questions)}'.replace(',', '.'),
        }

    def get_initials_subjects(self):
        Subject = apps.get_model('subjects', 'Subject')
        subjects = list(Subject.objects.filter(
            pk__in=self.examteachersubject_set.values_list('teacher_subject__subject_id', flat=True).order_by('teacher_subject__subject_id').distinct('teacher_subject__subject_id')
        ).distinct())
        return [
            {
                "name": subject.name, 
                "initial": (words[0][0] + words[1][0]) if len(subject.name.replace("-", "").split(' ')) >= 2 else subject.name.replace(" - ", "")[0:2]
            }
            for subject in subjects for words in [subject.name.replace("-", "").split()]
        ]

    @cached_property
    def get_initials_subjects_cached(self):
        return self.get_initials_subjects()
    
    @property
    def ordered_exam_questions(self):
        return ExamQuestion.objects.using('default').filter(
            exam=self, question__number_is_hidden=False
        ).availables().order_by(
            'exam_teacher_subject__order', 'order'
        ).values('pk')

    def number_print_question(self, question, randomization_version=None, application_randomization_version=None):
        if question.number_is_hidden:
            return "-"
        
        cache_key = f'numberquestion_{self.pk}-{question.pk}'
        if randomization_version:
            cache_key += f'_randomization_version_{randomization_version.version_number}'

        if (question_number := cache.get(cache_key)) and not (randomization_version or application_randomization_version):
            return question_number

        if randomization_version or application_randomization_version:
            exam_json = randomization_version.exam_json if randomization_version else application_randomization_version.exam_json
            from fiscallizeon.exams.json_utils import convert_json_to_exam_questions_list
            exam_question_list = convert_json_to_exam_questions_list(exam_json)
            all_exam_questions = [uuid.UUID(question['pk']) for question in exam_question_list]
        else:
            all_exam_questions = self.ordered_exam_questions
            all_exam_questions = [question['pk'] for question in all_exam_questions]

        active_exam_question = ExamQuestion.objects.filter(
            question=question,
            exam=self
        ).using('default').availables().first()

        if not active_exam_question:
            return False
        
        active_exam_question = active_exam_question.pk

        if self.has_foreign_languages:
            if self.is_abstract:
                questions = list(self.get_foreign_exam_questions().values_list('pk', flat=True))
                first_foreign_language_questions = questions[:len(questions)//2]
                last_foreign_language_questions = questions[len(questions)//2:]

            elif foreign_subjects := self.get_foreign_exam_teacher_subjects():
                first_foreign_language_questions = list(foreign_subjects[0].examquestion_set.all().values_list('pk', flat=True))
                last_foreign_language_questions = list(foreign_subjects[1].examquestion_set.all().values_list('pk', flat=True))
            
            if randomization_version or application_randomization_version:
                first_foreign_language_questions = [q for q in all_exam_questions if q in first_foreign_language_questions]
                last_foreign_language_questions = [q for q in all_exam_questions if q in last_foreign_language_questions]
            
            all_exam_questions = [q for q in all_exam_questions if q not in last_foreign_language_questions]

            if active_exam_question in last_foreign_language_questions:
                active_exam_question = first_foreign_language_questions[
                    last_foreign_language_questions.index(active_exam_question)
                ]

        question_number = all_exam_questions.index(active_exam_question) + self.start_number

        if not application_randomization_version:
            cache.set(cache_key, question_number, 600)
        return question_number
    
    def total_unanswered(self, user_pk=None):
        return  self.number_of_discursives_unanswered(user_pk) + self.number_of_file_unanswered(user_pk)

    def number_of_discursives_unanswered(self, user_pk=None):

        user = User.objects.get(pk=user_pk) if user_pk else None

        TextualAnswer = apps.get_model('answers', 'TextualAnswer')

        number_of_discursives_unanswered = TextualAnswer.objects.filter(
            question__examquestion__in=self.examquestion_set.availables().filter(
                question__category=Question.TEXTUAL
            ),
            teacher_grade__isnull=True,
            student_application__application__exam=self,
        )

        if user and user.user_type == settings.TEACHER:
            number_of_discursives_unanswered = number_of_discursives_unanswered.filter(
                question__examquestion__exam_teacher_subject__teacher_subject__subject__in=user.inspector.subjects.all()
            )

        return number_of_discursives_unanswered.count()

    def number_of_file_unanswered(self, user_pk=None):
        FileAnswer = apps.get_model('answers', 'FileAnswer')

        user = User.objects.get(pk=user_pk) if user_pk else None

        number_of_file_unanswered = FileAnswer.objects.filter(
            question__examquestion__in=self.examquestion_set.availables().filter(
                question__category=Question.FILE
            ),
            teacher_grade__isnull=True,
            student_application__application__exam=self,
        )

        if user and user.user_type == settings.TEACHER:
            number_of_file_unanswered = number_of_file_unanswered.filter(
                question__examquestion__exam_teacher_subject__teacher_subject__subject__in=user.inspector.subjects.all()
            )

        return number_of_file_unanswered.count()

    def wrongs_count(self):
        total_opened_wrongs_count = Wrong.objects.filter(
            exam_question__in=self.examquestion_set.availables(),
            status=Wrong.AWAITING_REVIEW
        ).count()

        return total_opened_wrongs_count

    def count_empty_feedbacks(self):
        questions_availables = self.examquestion_set.availables()
        total_questions = questions_availables.filter(
            question__category=Question.CHOICE
        ).count()

        total_questions_with_feedback = questions_availables.filter(
            question__category=Question.CHOICE,
            question__alternatives__is_correct=True
        ).count()

        return total_questions - total_questions_with_feedback

    def generate_exam_questions_cache(self):
        questions =  self.questions       
            
        questions =  questions.prefetch_related("alternatives").all().order_by(
            'examquestion__exam_teacher_subject__order', 'examquestion__order'
        ).distinct()

        questions = questions.annotate(
            knowledge_area_name=F('subject__knowledge_area__name'),
            subject_name=F('subject__name')
        )

        questions = questions.availables(self)

        cache.set(
            f'QUESTIONS_{str(self.pk)}',
            list(questions),
            300
        )

        return questions

    def clear_questions_numbers_cache(self):
        for exam_question in self.questions.all():
            cache.delete(f'numberquestion_{self.pk}-{exam_question.pk}')

    def count_applications_count(self):
        return self.application_set.all().count()

    def get_application_students(self, coordinations=None):
        from fiscallizeon.applications.models import ApplicationStudent
        return ApplicationStudent.objects.filter(
            Q(application__exam=self),
            Q(
                Q(student__classes__isnull=True) |
                Q(student__classes__coordination__in=coordinations)
            ) if coordinations else Q(),
        ).distinct()
        
    def get_application_students_started(self, coordinations=None):
        return self.get_application_students(coordinations=coordinations).filter(
            Q(
                Q(start_time__isnull=False) |
                Q(is_omr=True)
            )
        )

    def get_application_students_started_count(self):
        return self.get_application_students_started().count()

    def get_answers(self, is_correct=True):
        from fiscallizeon.answers.models import OptionAnswer
        return OptionAnswer.objects.filter(
            status=OptionAnswer.ACTIVE,
            student_application__in=self.get_application_students(),
            question_option__is_correct=is_correct
        ).distinct()

    def get_average_duration(self):
        return self.get_application_students().filter(
            start_time__isnull=False, 
            end_time__isnull=False
        ).aggregate(
            average=Avg(F('end_time') - F('start_time'))
        ).get('average', 0)

    def get_questions(self):
        from fiscallizeon.answers.models import OptionAnswer
        answers = OptionAnswer.objects.filter(
            question_option__question__pk=OuterRef('pk'),
            question_option__question__exams__pk=self.pk,
            question_option__is_correct=True,
            status=OptionAnswer.ACTIVE
        ).distinct()

        return self.questions.all().annotate(
            total_students=Value(self.get_application_students_started_count(), output_field=IntegerField()),
            total_correct_answers=Subquery(
                answers.values('question_option__question').annotate(c=Count('pk')).values('c')[:1]
            )
        ).order_by(
            'created_at'
        )

    def get_ordered_questions(self):
        return self.questions.availables(self).order_by(
            'examquestion__exam_teacher_subject__order', 'examquestion__order', 'created_at'
        )

    def has_file_answers(self):
        from fiscallizeon.answers.models import FileAnswer
        return FileAnswer.objects.filter(
            student_application__application__exam=self
        ).exists()
    
    @property
    def get_elaboration_release_date(self):
        return self.release_elaboration_teacher if self.release_elaboration_teacher else self.created_at.date()

    def get_personalized_header(self, exam_header_pk, remove_student_data=True):

        header = ExamHeader.objects.get(pk=exam_header_pk)
        # CLIENT
        if '#NomeDaEscola' in header.content or '#LogoEscola' in header.content:    
            client = self.coordinations.all()[0].unity.client
            
            if client.logo:
                header.content = header.content.replace("#LogoEscola", f'<img style="max-width:90%" src="{client.logo.url}"/>')
            
            header.content = header.content.replace("#NomeDaEscola", client.name)

        if '#CodigoDaProva' in header.content:
            header.content = header.content.replace("#CodigoDaProva", str(self.external_code))
            
        if '#NomeDaProva' in header.content:
            header.content = header.content.replace("#NomeDaProva", self.name)
            
        if '#NomeDasDisciplinas' in header.content:
            subjects = ""
            for teacher_subject in self.teacher_subjects.all().distinct('subject__name'):
                subjects += f'{teacher_subject.subject.name}, '
            header.content = header.content.replace("#NomeDasDisciplinas", f'{subjects[:-2]}')
            
        if '#QuantidadeQuestoes' in header.content:
            header.content = header.content.replace("#QuantidadeQuestoes", f'{self.questions.all().count()}')
        
        if '#Serie' in header.content and self.examteachersubject_set.all().first():
            header.content = header.content.replace("#Serie", self.examteachersubject_set.all().first().grade.get_complete_name())
        
        #ALUNO
        if remove_student_data:
            header.content = header.content.replace("#NomeDoAluno", '')
            header.content = header.content.replace("#Matricula", '')
            header.content = header.content.replace("#Turma", '')
            header.content = header.content.replace("#Unidade", '')


        # DATAS
        if (
            '#DiaDaAplicacao' in header.content or 
            '#MesDaAplicacao' in header.content or 
            '#AnoDaAplicacao' in header.content
        ):
            application = self.application_set.all().first()
            if application:
                header.content = header.content.replace("#DiaDaAplicacao", f'{application.date.day}')
                header.content = header.content.replace("#MesDaAplicacao", f'{application.date.month}')
                header.content = header.content.replace("#AnoDaAplicacao", f'{application.date.year}')
            
        return header
    
    def get_foreign_exam_teacher_subjects(self):
        foreign_subjects = ExamTeacherSubject.objects.filter(
            exam=self, is_foreign_language=True
        ).using('default').order_by('order')

        if foreign_subjects.count() != 2:
            return ExamTeacherSubject.objects.none()

        if foreign_subjects[0].examquestion_set.using('default').availables().count() != foreign_subjects[1].examquestion_set.using('default').availables().count():
            return ExamTeacherSubject.objects.none()

        return foreign_subjects

    def get_foreign_exam_questions(self):
        return ExamQuestion.objects.filter(
            exam=self,
            is_foreign_language=True
        ).using('default')

    @property
    def has_foreign_languages(self):
        if self.is_abstract:
            foreign_questions_count = self.get_foreign_exam_questions().count()
            return foreign_questions_count > 0 and foreign_questions_count % 2 == 0

        return self.get_foreign_exam_teacher_subjects().exists()

    @property
    def has_commented_questions(self):
        questions = self.questions.filter(
           Q(
               Q(commented_awnser__isnull=False) |
               Q(feedback__isnull=False)
           ) &
           Q(
               ~Q(commented_awnser="") |
               ~Q(feedback="")
           ) 
        )

        return questions.exists()
    
    @property
    def has_opened_applications(self):
        from django.db.models import ExpressionWrapper, DateTimeField
        now = timezone.localtime(timezone.now())
        
        applications = self.application_set.annotate(
            datetime_end = ExpressionWrapper(F('date') + F('end') + timedelta(hours=3), output_field=DateTimeField()),
            date_end_time_end = ExpressionWrapper(F('date_end') + F('end') + timedelta(hours=3), output_field=DateTimeField())
        ).filter(
            Q(
                Q(date_end_time_end__isnull=False, date_end_time_end__gte=now) |
                Q(date_end_time_end__isnull=True, datetime_end__gte=now)
            )
        )
        return applications.exists()
    
    def get_total_weight(self, extra_filters=None):
        return self.examquestion_set.filter(Q(extra_filters) if extra_filters else Q()).availables(exclude_annuleds=True, include_give_score=True).aggregate(
            total_weight=Coalesce(Sum('weight'), Decimal('0')),
        )['total_weight']
    
    def generate_performances(self, only_students=None, only_classes=None, only_bnccs=None, only_unities=None, only_exam=None, only_subjects=None, recalculate=False):
        all = not only_students and not only_classes and not only_bnccs and not only_unities and not only_exam and not only_subjects

        if all or only_students:
            self.generate_students_performances(recalculate=recalculate)
        
        if all or only_bnccs:
            self.get_or_generate_students_performances_bnccs(recalculate=recalculate)
        
        if all or only_subjects:
            self.get_or_generate_students_performances_subjects(recalculate=recalculate)
        
        if all or only_classes:
            self.generate_classes_performances(recalculate=False if all else True)
        
        if all or only_unities:
            self.generate_unities_performances(recalculate=False if all else True)
        
        if all or only_exam:
            self.generate_exam_performance(recalculate=False if all else True)
    
    def generate_students_performances(self, recalculate=False):        
        applications_student = self.get_application_students_started()
        
        for application_student in applications_student:
            application_student.get_performance(recalculate=recalculate)    
        
    def generate_classes_performances(self, classe=None, recalculate=False):
        from fiscallizeon.exams.api.exams import ExamHistograms
        start_process = time.time()
        
        classes = self.get_classes().filter(
            Q(pk=classe.pk) if classe else Q(),
        ).distinct()

        performances = []
        
        for classe in classes:
            
            classe_performance = classe.last_performance(exam=self)
            
            if not classe_performance or recalculate:
                
                applications_student = self.get_application_students_started().filter(student__in=classe.students.all(), application__exam=self).distinct()
                
                for application_student in applications_student:
                    student_performance = application_student.get_performance(recalculate=recalculate)
                    
                    performances.append(student_performance if student_performance else 0)
                
                process_time = time.time() - start_process

                exam_hostigram = ExamHistograms().generate_histogram(exam_pk=self.pk, school_classes=[str(classe.id)])
                if classe_performance:
                    classe_performance.using('default').update(performance=fmean(performances) if performances else 0, weight=applications_student.count(), histogram=exam_hostigram.get('data'), process_time=timedelta(seconds=process_time))
                else:
                    classe.performances.create(
                        exam=self, 
                        performance=fmean(performances), 
                        histogram=exam_hostigram.get('data'),
                        process_time=timedelta(seconds=process_time), 
                        weight=applications_student.count()
                    )
                    
    def get_topics(self):
        from fiscallizeon.subjects.models import Topic
        return Topic.objects.filter(pk__in=self.examquestion_set.all().values_list('question__topics')).distinct()
    
    def get_abilities(self):
        from fiscallizeon.bncc.models import Abiliity
        return Abiliity.objects.filter(pk__in=self.examquestion_set.availables().values_list('question__abilities')).distinct()
    
    def get_competences(self):
        from fiscallizeon.bncc.models import Competence
        return Competence.objects.filter(pk__in=self.examquestion_set.availables().values_list('question__competences')).distinct()
    
    def get_applications_student_bnccs_details(self, applications_student, bncc_id, type='Topic'): 
        from fiscallizeon.answers.models import OptionAnswer

        questions = self.questions.availables(self, exclude_annuleds=True).annotate(
            correct_objetive_answers=Count('alternatives__optionanswer', filter=Q(
                Q(alternatives__optionanswer__status=OptionAnswer.ACTIVE), 
                Q(alternatives__optionanswer__question_option__is_correct=True),
                Q(alternatives__optionanswer__student_application__in=applications_student),
            ), distinct=True),
            incorrect_objetive_answers=Count('alternatives__optionanswer', filter=Q(
                Q(alternatives__optionanswer__status=OptionAnswer.ACTIVE), 
                Q(alternatives__optionanswer__question_option__is_correct=False),
                Q(alternatives__optionanswer__student_application__in=applications_student),
            ), distinct=True),
            total_answers=F('correct_objetive_answers') + F('incorrect_objetive_answers'),
        )

        if type == 'Topic':
            questions = questions.filter(topics=bncc_id)
        elif type == 'Abiliity':
            questions = questions.filter(topics=bncc_id)
        elif type == 'Competence':
            questions = questions.filter(topics=bncc_id)
        
        answers_aggregates = questions.aggregate( 
            total_correct_objetive_answers=Sum('correct_objetive_answers'),
            total_incorrect_objetive_answers=Sum('incorrect_objetive_answers'),
            total=Sum('total_answers'),
        )
        
        corrects = answers_aggregates['total_correct_objetive_answers'] or 0
        total = answers_aggregates['total'] or 0

        return {
            'corrects': corrects,
            'incorrects': answers_aggregates['total_incorrect_objetive_answers'] or 0,
            'total_answers': total,
            'performance': corrects / total * 100 if total else 0,
            'total_questions': questions.count(),
        }

    def get_or_generate_students_performances_bnccs(self, recalculate=False, coordinations=None):
        from fiscallizeon.subjects.models import Topic
        from fiscallizeon.bncc.models import Abiliity, Competence
        from fiscallizeon.exams.api.exams import ExamHistograms

        start_process = time.time()
        
        applications_student = self.get_application_students_started(
            coordinations=coordinations
        )

        exam_questions = self.examquestion_set.availables(exclude_annuleds=True)
        topics = Topic.objects.filter(pk__in=exam_questions.values_list('question__topics')).distinct()
        abilities = Abiliity.objects.filter(pk__in=exam_questions.values_list('question__abilities')).distinct()
        competences = Competence.objects.filter(pk__in=exam_questions.values_list('question__competences')).distinct()
        
        for topic in topics:
        
            topic_performance = topic.last_performance(exam=self)
            
            if not topic_performance or recalculate:

                details = self.get_applications_student_bnccs_details(
                    applications_student=applications_student,
                    bncc_id=topic.id, 
                    type='Topic'
                ) 

                performance = details['performance']

                exam_hostigram = ExamHistograms().generate_histogram(exam_pk=self.pk, bncc_pk=topic.pk)

                if topic_performance:
                    topic_performance.using('default').update(
                        performance=performance, 
                        weight=applications_student.count(), 
                        process_time=timedelta(seconds=(time.time() - start_process)),
                        histogram=exam_hostigram.get('data')
                    )
                else:
                    topic.performances.create(
                        exam=self, 
                        performance=performance,
                        weight=applications_student.count(),
                        process_time=timedelta(seconds=(time.time() - start_process)),
                        histogram=exam_hostigram.get('data')
                    )
                    
                for classe in self.get_classes():
                    topic_classe_performance = topic.last_performance(exam=self, classe=classe)
                    applications_student_performances = [application_student.get_performance(bncc_pk=topic.pk) for application_student in applications_student.filter(student__classes=classe, application__exam=self)]

                    exam_hostigram = ExamHistograms().generate_histogram(exam_pk=self.pk, bncc_pk=topic.pk, school_classes=[str(classe.pk)])
                    
                    if topic_classe_performance:
                        topic_classe_performance.using('default').update(
                            performance=fmean(applications_student_performances) if applications_student_performances else 0, 
                            histogram=exam_hostigram.get('data'),
                        )
                    else:
                        topic_classe_performance = topic.performances.create(
                            exam=self,
                            school_class=classe,
                            performance=fmean(applications_student_performances) if applications_student_performances else 0,
                            process_time=timedelta(seconds=(time.time() - start_process)),
                            weight=classe.students.count(),
                            histogram=exam_hostigram.get('data'),
                        )

        for ability in abilities:
            ability_performance = ability.last_performance(exam=self)
            if not ability_performance or recalculate:

                exam_hostigram = ExamHistograms().generate_histogram(exam_pk=self.pk, bncc_pk=ability.pk)

                details = self.get_applications_student_bnccs_details(
                    applications_student=applications_student,
                    bncc_id=topic.id, 
                    type='Abiliity'
                ) 

                performance = details['performance']

                if ability_performance:
                    ability_performance.using('default').update(
                        performance=performance, 
                        weight=applications_student.count(), 
                        histogram=exam_hostigram.get('data')
                    )
                else:
                    ability.performances.create(
                        exam=self, 
                        performance=performance,
                        weight=applications_student.count(),
                        process_time=timedelta(seconds=(time.time() - start_process)),
                        histogram=exam_hostigram.get('data')
                    )
                for classe in self.get_classes():
                    ability_classe_performance = ability.last_performance(exam=self, classe=classe)
                    applications_student_performances = [application_student.get_performance(bncc_pk=ability.pk) for application_student in applications_student.filter(student__classes=classe, application__exam=self)]

                    exam_hostigram = ExamHistograms().generate_histogram(exam_pk=self.pk, bncc_pk=ability.pk, school_classes=[str(classe.pk)])
                    
                    if ability_classe_performance:
                        ability_classe_performance.using('default').update(
                            performance=fmean(applications_student_performances) if applications_student_performances else 0, 
                            histogram=exam_hostigram.get('data'),
                        )
                    else:
                        ability_classe_performance = ability.performances.create(
                            exam=self,
                            school_class=classe,
                            performance=fmean(applications_student_performances) if applications_student_performances else 0,
                            process_time=timedelta(seconds=(time.time() - start_process)),
                            weight=classe.students.count(),
                            histogram=exam_hostigram.get('data'),
                        )
          
        for competence in competences:
            competence_performance = competence.last_performance(exam=self)
            if not competence_performance or recalculate:

                exam_hostigram = ExamHistograms().generate_histogram(exam_pk=self.pk, bncc_pk=competence.pk)

                details = self.get_applications_student_bnccs_details(
                    applications_student=applications_student,
                    bncc_id=topic.id, 
                    type='Competence'
                ) 

                performance = details['performance']

                if competence_performance:
                    competence_performance.using('default').update(
                        performance=performance, 
                        weight=applications_student.count(), 
                        histogram=exam_hostigram.get('data'),
                    )
                else:
                    competence.performances.create(
                        exam=self, 
                        performance=performance,
                        weight=applications_student.count(),
                        process_time=timedelta(seconds=(time.time() - start_process)),
                        histogram=exam_hostigram.get('data'),
                    )
                for classe in self.get_classes():
                    competence_classe_performance = competence.last_performance(exam=self, classe=classe)
                    applications_student_performances = [application_student.get_performance(bncc_pk=competence.pk) for application_student in applications_student.filter(student__classes=classe, application__exam=self)]

                    exam_hostigram = ExamHistograms().generate_histogram(exam_pk=self.pk, bncc_pk=competence.pk, school_classes=[str(classe.pk)])
                    
                    if competence_classe_performance:
                        competence_classe_performance.using('default').update(
                            performance=fmean(applications_student_performances) if applications_student_performances else 0, 
                            histogram=exam_hostigram.get('data'),
                        )
                    else:
                        competence_classe_performance = competence.performances.create(
                            exam=self,
                            school_class=classe,
                            performance=fmean(applications_student_performances) if applications_student_performances else 0,
                            process_time=timedelta(seconds=(time.time() - start_process)),
                            weight=classe.students.count(),
                            histogram=exam_hostigram.get('data'),
                        )

        process_time = time.time() - start_process
        
        return {
            "topics": topics,
            "abilities": abilities,
            "competences": competences,
            "mensage": f"O processo para a prova: {self.name} demorou: {process_time} segundos",
            "process_time": process_time
        }
        
    def get_or_generate_students_performances_subjects(self, recalculate=False, coordinations=None):
        from fiscallizeon.subjects.models import Subject
        from fiscallizeon.exams.api.exams import ExamHistograms

        start_process = time.time()
        
        applications_student = self.get_application_students_started(coordinations=coordinations)        
        
        subjects = Subject.objects.filter(pk__in=self.examquestion_set.availables().values_list(
            'question__subject' if self.is_abstract else 'exam_teacher_subject__teacher_subject__subject'
        )).distinct()
        
        for subject in subjects:
            subject_performance = subject.last_performance(exam=self)
            if not subject_performance or recalculate:
                
                applications_student_performances = [application_student.get_performance(subject=subject, recalculate=recalculate) for application_student in applications_student]
                
                process_time = time.time() - start_process
                exam_hostigram = ExamHistograms().generate_histogram(exam_pk=self.pk, subjects=[str(subject.id)])

                if subject_performance:
                    subject_performance.using('default').update(
                        performance=fmean(applications_student_performances) if applications_student_performances else 0, 
                        weight=applications_student.count(), 
                        process_time=timedelta(seconds=process_time),
                        histogram=exam_hostigram.get('data'),
                    )
                else:
                    subject.performances.create(
                        exam=self,
                        performance=fmean(applications_student_performances) if applications_student_performances else 0,
                        process_time=timedelta(seconds=process_time),
                        weight=applications_student.count(),
                        histogram=exam_hostigram.get('data'),
                    )
                
                for classe in self.get_classes():
                    subject_classe_performance = subject.last_performance(exam=self, classe=classe)
                    applications_student_performances = [application_student.get_performance(subject=subject) for application_student in applications_student.filter(student__in=classe.students.all(), application__exam=self)]

                    exam_hostigram = ExamHistograms().generate_histogram(exam_pk=self.pk, subject_pk=subject.pk, classe_pk=classe.pk)
                    
                    if subject_classe_performance:
                        subject_classe_performance.using('default').update(
                            school_class=classe,
                            performance=fmean(applications_student_performances) if applications_student_performances else 0, 
                            weight=applications_student.count(), 
                            process_time=timedelta(seconds=process_time),
                            histogram=exam_hostigram.get('data'),
                        )
                    else:
                        subject_performance = subject.performances.create(
                            exam=self,
                            school_class=classe,
                            performance=fmean(applications_student_performances) if applications_student_performances else 0,
                            process_time=timedelta(seconds=process_time),
                            weight=applications_student.count(),
                            histogram=exam_hostigram.get('data'),
                        )
        
        return subjects
    
    def generate_unities_performances(self, unity=None, recalculate=False):
        start_process = time.time()
        
        unities = self.get_unities().filter(
            Q(pk=unity.pk) if unity else Q(),
        ).distinct()
        
        for unity in unities:
            
            unity_performance = unity.last_performance(exam=self)
            
            if not unity_performance or recalculate:
                applications_student = self.get_application_students_started().filter(student__client__unities=unity, application__exam=self)
                
                classes = SchoolClass.objects.filter(students__in=applications_student.values_list('student', flat=True)).distinct()
                
                performances = []
                weights = []
                
                for classe in classes:
                    classe_performance = classe.last_performance(exam=self)
                    if classe_performance and not recalculate:
                        performances.append(classe_performance.first().performance if classe_performance.first().performance else 0)
                        weights.append(classe_performance.first().weight if classe_performance.first().weight > 0 else 1)
                    else:
                        self.generate_classes_performances(classe=classe, recalculate=recalculate)
                
                if performances and weights:
                    process_time = time.time() - start_process
                    
                    if unity_performance:
                        unity_performance.using('default').update(performance=np.average(performances, weights=weights), weight=classes.count(), process_time=timedelta(seconds=process_time))
                    else:
                        unity.performances.create(
                            exam=self,
                            performance=np.average(performances, weights=weights),
                            process_time=timedelta(seconds=process_time),
                            weight=classes.count(),
                        )
    
    def generate_exam_performance(self, recalculate=False):
        from fiscallizeon.exams.api.exams import ExamHistograms
        start_process = time.time()
        
        if not recalculate and self.last_performance:
            return self.last_performance.first().performance
        
        unities = Unity.objects.filter(
            Q(coordinations__in=self.coordinations.all()),
        ).distinct()
        
        
        unities_performances = []
        unities_weights = []
        
        for unity in unities:
            
            unity_performance = unity.last_performance(exam=self)
            
            if unity_performance and not recalculate:
                unities_performances.append(unity_performance.first().performance)
                unities_weights.append(unity_performance.first().weight)
            else:
                self.generate_unities_performances(unity=unity, recalculate=True)
                
            unities_performances.append(unity_performance.first().performance if unity_performance else 0)
            unities_weights.append(unity_performance.first().weight if unity_performance else 1)
                
        if unities_performances and unities_weights:
            exam_hostigram = ExamHistograms().generate_histogram(exam_pk=self.pk)

            process_time = time.time() - start_process
            if self.last_performance:
                self.last_performance.using('default').update(
                    performance=np.average(unities_performances, weights=unities_weights), 
                    weight=self.questions.count(), 
                    process_time=timedelta(seconds=process_time),
                    histogram=exam_hostigram.get('data')
                )
            else:
                self.performances.create(
                    performance=np.average(unities_performances, weights=unities_weights), 
                    process_time=timedelta(seconds=process_time), 
                    weight=self.questions.count(),
                    histogram=exam_hostigram.get('data')
                )
        
        return self.last_performance.first().performance if self.last_performance else Decimal(0)
    
    @property
    def last_performance(self):
        return self.performances.using('default').filter(application_student__isnull=True, exam__isnull=True).order_by('-created_at')
    
    def run_recalculate_task(self, only_students=None, only_classes=None, only_bnccs=None, only_unities=None, only_subjects=None):
        from fiscallizeon.analytics.tasks import generate_student_performances_after_exam_finished
        task = generate_student_performances_after_exam_finished
        result = task.apply_async(task_id=f'RECALCULATE_EXAM_{str(self.pk)}', kwargs={
            "especific_exam_pk": self.pk,
            "only_students": only_students,
            "only_classes": only_classes,
            "only_bnccs": only_bnccs,
            "only_unities": only_unities,
            "only_subjects": only_subjects,
        }).forget()

    def get_filters_to_print(self):
        if not self.exam_print_config:
            client = self.coordinations.all().first().unity.client
            copy_exam_print_config = client.get_exam_print_config()
            copy_exam_print_config.pk = None
            copy_exam_print_config.name = f'Configuração {self.name}'
            copy_exam_print_config.is_default = False
            copy_exam_print_config.save()
            self.exam_print_config = copy_exam_print_config
            self.save(skip_hooks=True)
        return {
            'header': f'{self.exam_print_config.header.pk}' if self.exam_print_config.header else '',
            'header_full': self.exam_print_config.header_format,
            'two_columns': self.exam_print_config.column_type,
            'separate_subjects': self.exam_print_config.kind,
            'line_textual': self.exam_print_config.text_question_format,
            'text_question_format': int(self.exam_print_config.text_question_format),
            'hide_discipline_name': 0 if int(not self.exam_print_config.print_subjects_name) else 1,
            'hide_knowledge_area_name': int(self.exam_print_config.hide_knowledge_areas_name),
            'hide_questions_referencies': int(self.exam_print_config.hide_alternatives_indicator),
            'print_images_with_grayscale': int(self.exam_print_config.print_black_and_white_images),
            'hyphenate_text': int(self.exam_print_config.hyphenate),
            'line_spacing': self.exam_print_config.line_height,
            # 'font_size': "".join([ch for ch in self.exam_print_config.get_font_size_display() if ch.isdigit()]),
            'font_size': self.exam_print_config.font_size,
            'font_family': self.exam_print_config.font_family,
            'print_correct_answers': int(self.exam_print_config.print_with_correct_answers),
            'show_question_score': int(self.exam_print_config.show_question_score),
            'show_question_board': int(self.exam_print_config.show_question_board),
            'margin_top': float(self.exam_print_config.margin_top),
            'margin_bottom': float(self.exam_print_config.margin_bottom),
            'margin_right': float(self.exam_print_config.margin_right),
            'margin_left': float(self.exam_print_config.margin_left),
            'margin_left': float(self.exam_print_config.margin_left),
            'uppercase_letters': int(self.exam_print_config.uppercase_letters),
            'discursive_line_height': float(self.exam_print_config.discursive_line_height),
            'show_footer': int(self.exam_print_config.show_footer),
            'add_page_number': int(self.exam_print_config.add_page_number),
            'economy_mode': int(self.exam_print_config.economy_mode),
            'force_choices_with_statement': int(self.exam_print_config.force_choices_with_statement),
            'hide_numbering': int(self.exam_print_config.hide_numbering),
            'break_enunciation': int(self.exam_print_config.break_enunciation),
            'break_all_questions': int(self.exam_print_config.break_all_questions),
            'discursive_question_space_type': int(self.exam_print_config.discursive_question_space_type),
            'background_image': f'{self.exam_print_config.background_image.id}' if self.exam_print_config.background_image else '',
            'language': self.exam_print_config.language if self.exam_print_config.language else 0,
            'break_alternatives': int(self.exam_print_config.break_alternatives),
        }

    def get_subjects(self):
        Subject = apps.get_model('subjects', 'Subject')
        return Subject.objects.filter(
            pk__in=self.examquestion_set.availables().values_list(
                'question__subject' if self.is_abstract else 'exam_teacher_subject__teacher_subject__subject'
            )
        ).distinct()
    
    def get_subject_questions_count(self):
        questions = ExamQuestion.objects.filter(
            exam=self,
            question__number_is_hidden=False,
        ).availables().order_by()

        if self.is_abstract:
            questions = questions.annotate(
                subject=F('question__subject')
            )
        else:
            questions = questions.annotate(
                subject=F('exam_teacher_subject__teacher_subject__subject')
            )

        return questions.values(
                'question__subject',
            ).annotate(total=Count('pk')).values(
                'question__subject', 'total'
            )
    
    def get_classes(self, all=False):
        classes = SchoolClass.objects.filter(
            Q(students__in=self.get_application_students().values_list('student') if all else self.get_application_students_started().values_list('student')),
            Q(school_year=self.created_at.year)
        ).distinct()
        return classes
    
    def get_unities(self, coordinations=None):
        unities = Unity.objects.filter(
            Q(coordinations__school_classes__students__in=self.get_application_students_started().values_list('student')),
            Q(coordinations__in=coordinations) if coordinations else Q(),
        ).distinct()
        return unities
    
    @cached_property
    def get_status(self):
        exam_questions = self.examquestion_set.only("pk")
        status_question_query = StatusQuestion.objects.filter(exam_question__in=exam_questions).only('pk', 'status', 'active').values('status', 'active').distinct()
        
        openeds = exam_questions.count()
        
        actived_status_question_query = status_question_query.filter(active=True).values_list('status', flat=True)
        
        aproveds_count =  len([l for l in actived_status_question_query if l == StatusQuestion.APPROVED])
        reproveds_count =  len([l for l in actived_status_question_query if l == StatusQuestion.REPROVED])
        openeds_count =  len([l for l in actived_status_question_query if l == StatusQuestion.OPENED])
        correction_pending_count =  len([l for l in actived_status_question_query if l == StatusQuestion.CORRECTION_PENDING])
        correcteds_count =  len([l for l in actived_status_question_query if l == StatusQuestion.CORRECTED])
        seens_count =  status_question_query.filter(status=StatusQuestion.SEEN).count()
        annuleds_count =  len([l for l in actived_status_question_query if l == StatusQuestion.ANNULLED])
        use_later_count =  len([l for l in actived_status_question_query if l == StatusQuestion.USE_LATER])
        
        status = {}
        
        if aproveds_count:
            status['Aprovada(s)'] = {"number": aproveds_count, "color": "success"}
            openeds -= aproveds_count
            
        if reproveds_count:
            status['Reprovada(s)'] = {"number": reproveds_count, "color": "danger"}
            openeds -= reproveds_count
            
        if openeds_count:
            status['Em aberto(s)'] = {"number": openeds_count, "color": "primary"}
            openeds -= openeds_count
            
        if correction_pending_count:
            status['Aguardando correção'] = {"number": correction_pending_count, "color": "warning"}
            openeds -= correction_pending_count
            
        if correcteds_count:
            status['Corrigida(s)'] = {"number": correcteds_count, "color": "primary"}
            openeds -= correcteds_count
            
        if seens_count:
            status['Visto(s)'] = {"number": seens_count, "color": "primary"}
            
        if annuleds_count:
            status['Anulada(s)'] = {"number": annuleds_count, "color": "danger"}
            openeds -= annuleds_count
            
        if use_later_count:
            status['Usar depois'] = {"number": use_later_count, "color": "info"}
            openeds -= use_later_count
        
        # if openeds:
        #     status['Sem status'] = openeds
        
        return status

    @cached_property
    def get_status_only_value(self):
        return {key: value['number'] for key, value in self.get_status.items()}

    @property
    def can_print(self):
        from fiscallizeon.omr.models import OMRUpload
        if self.is_printed:
            return False
        return True
    
    def get_availables_questions(self):
        return self.examquestion_set.availables(exclude_annuleds=True)
    
    @property
    def get_blocked_weights(self):
        
        examquestions = self.examquestion_set.using('default').availables(exclude_annuleds=True)    
        blocked_weights = examquestions.filter(block_weight=True).aggregate(Sum('weight')).get('weight__sum') or 0
        
        # Pega todas as questões que não estão travadas e que estão em um exam_teacher_subject travado para levar em consideração na soma das notas que estão travadas.
        blocked_weights += examquestions.filter(exam_teacher_subject__block_subject_note=True).exclude(block_weight=True).aggregate(Sum('weight')).get('weight__sum') or 0
            
        return blocked_weights 
    
    def get_application_is_finished(self):
        if application := self.application_set.all().order_by('created_at').first():
            return application.is_time_finished
        return False
    
    def exam_questions_availables_subquery(self, question_type = Question.CHOICE):
        return ExamQuestion.objects.filter(
            question__category=question_type,
            exam=OuterRef('application__exam')
        ).availables(exclude_annuleds=True).annotate(
            count=Count('pk')
        )
        
    def last_performance_followup(self, deadline, coordination=None, unity=None, school_class=None, inspector=None):
        try:
            return self.performances_followup.using('default').filter(
                Q(deadline=deadline),
                Q(school_class=school_class) if school_class else Q(school_class__isnull=True),
                Q(coordination=coordination) if coordination else Q(coordination__isnull=True),
                Q(unity=unity) if unity else Q(unity__isnull=True),
                Q(inspector=inspector) if inspector else Q(inspector__isnull=True),
            ).first()
        except:
            pass
        
        return None
        
    def get_answers_awaiting_response(self, school_class=None, get_cards=False):
        OptionAnswer = apps.get_model('answers', 'OptionAnswer')
        Application = apps.get_model('applications', 'Application')
        
        object = {}
        
        exam_questions = self.examquestion_set.using('readonly2').filter(weight__gt=0).availables(exclude_annuleds=True).values_list('pk', flat=True)
        
        questions_pk = list(exam_questions.values_list('question'))
        
        discursive_questions = exam_questions.exclude(question__category=Question.CHOICE)
        
        exam_questions_discursives_count = int(discursive_questions.count())
        exam_questions_objectives_count = int(exam_questions.filter(question__category=Question.CHOICE).count())
        
        applications = Application.objects.using('readonly2').filter(
            Q(
                exam=self, 
                applicationstudent__missed=False
            ),
        ).applieds().distinct()
        
        if school_class:
            applications = applications.using('readonly2').filter(applicationstudent__student__classes=school_class)
        
        applications = applications.annotate(
            application_students_count=Count('applicationstudent', filter=Q(
                Q(applicationstudent__missed=False),
                Q(applicationstudent__student__classes=school_class) if school_class else Q(), 
            ), distinct=True)
        )
        
        if not get_cards:
            
            applications = applications.annotate(
                
                total_discursives_answers_count=F('application_students_count') * exam_questions_discursives_count,
                total_objectives_answers_count=F('application_students_count') * exam_questions_objectives_count,
                
                file_answered_count=Count('applicationstudent__file_answers', filter=Q(
                    Q(applicationstudent__student__classes=school_class) if school_class else Q(),
                    Q(applicationstudent__file_answers__question__in=questions_pk, applicationstudent__missed=False),
                    Q(
                        Q(applicationstudent__file_answers__empty=True) | Q(applicationstudent__file_answers__teacher_grade__isnull=False)
                    )
                ), distinct=True),
                
                textual_answered_count=Count('applicationstudent__textual_answers', filter=Q(
                    Q(applicationstudent__student__classes=school_class) if school_class else Q(),
                    Q(applicationstudent__textual_answers__question__in=questions_pk, applicationstudent__missed=False), 
                    Q(
                        Q(applicationstudent__textual_answers__empty=True) | Q(applicationstudent__textual_answers__teacher_grade__isnull=False)
                    )
                ), distinct=True),
                
                option_answered_count=Count('applicationstudent__option_answers', filter=Q(
                    Q(applicationstudent__student__classes=school_class) if school_class else Q(),
                    Q(
                        applicationstudent__option_answers__question_option__question__in=questions_pk, 
                        applicationstudent__option_answers__status=OptionAnswer.ACTIVE, 
                        applicationstudent__option_answers__isnull=False,
                        applicationstudent__missed=False,
                    )
                ), distinct=True),
                
                empty_options_objectives_questions_count=Count('applicationstudent__empty_option_questions', filter=Q(
                    Q(applicationstudent__student__classes=school_class) if school_class else Q(),
                    Q(applicationstudent__missed=False, applicationstudent__empty_option_questions__in=questions_pk)
                ), distinct=True),
                
                total_discursives_pending=F('total_discursives_answers_count') - F('file_answered_count') - F('textual_answered_count'),
                total_objectives_pending=F('total_objectives_answers_count') - F('option_answered_count') - F('empty_options_objectives_questions_count'),
            )
            aggregations = applications.aggregate(
                total_discursives_pending_sum=Sum('total_discursives_pending'),
                total_discursives_answers_sum=Sum('total_discursives_answers_count'),
                total_objectives_pending_sum=Sum('total_objectives_pending'),
                total_objectives_answers_sum=Sum('total_objectives_answers_count'),
            )
            
            object = {
                "discursive_quantity": aggregations.get('total_discursives_pending_sum') or 0, 
                "discursive_total": aggregations.get('total_discursives_answers_sum') or 0, 
                "objective_quantity": aggregations.get('total_objectives_pending_sum') or 0, 
                "objective_total": aggregations.get('total_objectives_answers_sum') or 0,
                "objective_examquestions_pks": exam_questions.filter(question__category=Question.CHOICE).values_list('pk', flat=True),
                "discursive_examquestions_pks": exam_questions.exclude(question__category=Question.CHOICE).values_list('pk', flat=True),
            }
        else:
            # ANNOTATIONS PARA CALCULAR A QUANTIDADE DE CARTÕES QUE NÃO SUBIRAM
            quantity_discursive_lines_count = discursive_questions.aggregate(count=Sum('question__quantity_lines')).get('count') or 0
            
            total_files_predict = math.ceil(quantity_discursive_lines_count / 30) # ESSA VARIÁVEL FAZ UMA PREVISÃO DE PÁGINAS QUE DEVEM TER QUE DISCURSIVAS
            
            has_objectives = exam_questions_objectives_count > 0
            has_discursives = exam_questions_discursives_count > 0
            
            applications = applications.annotate(
                total_objectives_cards_count_predict=F('application_students_count') if has_objectives else Value(0),
                
                total_discursives_cards_count_predict=F('application_students_count') * total_files_predict if has_discursives else Value(0),
                
                sended_objective_cards=Count('applicationstudent', filter=Q(
                    Q(applicationstudent__student__classes=school_class) if school_class else Q(),
                    Q(applicationstudent__omrstudents__scan_image__isnull=False),
                    Q(applicationstudent__missed=False),
                ), distinct=True),
                
                sended_discursive_cards=Count('applicationstudent__omrstudents__omrdiscursivescan', filter=Q(
                    Q(applicationstudent__student__classes=school_class) if school_class else Q(),
                    Q(applicationstudent__omrstudents__omrdiscursivescan__upload_image__isnull=False),
                    Q(applicationstudent__missed=False),
                ), distinct=True),
                sended_discursive_cards_count=Case(
                    When(sended_discursive_cards__gt=F('total_discursives_cards_count_predict'), then=F('total_discursives_cards_count_predict')),
                    default=F('sended_discursive_cards')
                ),                
                total_objectives_cards_pending=F('total_objectives_cards_count_predict') - F('sended_objective_cards'),
                total_discursives_cards_pending=F('total_discursives_cards_count_predict') - F('sended_discursive_cards_count'),
            )
            # Cartões de resposta 
            aggregations = applications.aggregate(
                total_discursives_cards_pending_sum=Sum('total_discursives_cards_pending'),
                total_discursives_cards_count_predict_sum=Sum('total_discursives_cards_count_predict'),
                total_objectives_cards_pending_sum=Sum('total_objectives_cards_pending'),
                total_objectives_cards_count_predict_sum=Sum('total_objectives_cards_count_predict'),
            )
            # Fim
            object['discursive_cards_quantity'] = aggregations.get('total_discursives_cards_pending_sum') or 0
            object['discursive_cards_total'] = aggregations.get('total_discursives_cards_count_predict_sum') or 0
            object['objective_cards_quantity'] = aggregations.get('total_objectives_cards_pending_sum') or 0
            object['objective_cards_total'] = aggregations.get('total_objectives_cards_count_predict_sum') or 0
        
        return object

    def get_exam_teacher_subject_questions_pending_followup(self, exam_teacher_subject):
        
        object = {}
        
        exam_questions = self.examquestion_set.using('readonly2').filter(exam_teacher_subject=exam_teacher_subject).availables(exclude_annuleds=False, exclude_use_later=False).values_list('pk', flat=True)
        
        object = {
            "quantity": exam_questions.count(), 
            "total": exam_teacher_subject.quantity,
        }
        
        return object
    
    def get_cards_await_send(self, school_class=None):        
        Application = apps.get_model('applications', 'Application')
        
        exam_questions = self.examquestion_set.filter(weight__gt=0).availables(exclude_annuleds=True).values_list('pk', flat=True)
        
        discursive_questions = exam_questions.exclude(question__category=Question.CHOICE)
        
        quantity_lines_count = discursive_questions.aggregate(count=Sum('question__quantity_lines')).get('count') or 0
        
        total_files = math.ceil(quantity_lines_count / 30)
        
        has_objectives = exam_questions.filter(question__category=Question.CHOICE).exists()
        has_discursives = exam_questions.exclude(question__category=Question.CHOICE).exists()
        
        applications = Application.objects.filter(
            Q(
                exam=self, 
                applicationstudent__missed=False,
            )
        ).applieds().distinct()
        
        if school_class:
            applications = applications.filter(applicationstudent__student__classes=school_class)
        
        applications = applications.annotate(
            application_students_count=Count('applicationstudent', filter=Q(
                Q(applicationstudent__missed=False),
                Q(applicationstudent__student__classes=school_class) if school_class else Q(), 
            ), distinct=True),
            
            total_objectives_answers=F('application_students_count') if has_objectives else Value(0),
            
            total_discursives_answers_count=F('application_students_count') * total_files if has_discursives else Value(0),
            
            sended_objective_cards=Count('applicationstudent__omrstudents', filter=Q(
                Q(applicationstudent__student__classes=school_class) if school_class else Q(),
                Q(applicationstudent__omrstudents__scan_image__isnull=False),
            ), distinct=True),
            sended_discursive_cards=Count('applicationstudent__omrstudents__omrdiscursivescan', filter=Q(
                Q(applicationstudent__student__classes=school_class) if school_class else Q(),
                Q(applicationstudent__omrstudents__omrdiscursivescan__upload_image__isnull=False)
            ),
            sended_discursive_cards_count=Case(
                    When(sended_discursive_cards__gt=total_files, then=Value(total_files)),
                    default=F('sended_discursive_cards_count')
                )
            ),
            total_objectives_pending=F('total_objectives_answers') - F('sended_objective_cards'),
            total_discursives_pending=F('total_discursives_answers_count') - F('sended_discursive_cards_count'),
        )
        
        discursives_quantity = applications.aggregate(count=Sum('total_discursives_pending')).get('count') or 0
        discursives_total = applications.aggregate(count=Sum('total_discursives_answers_count')).get('count') or 0
        
        objectives_quantity = applications.aggregate(count=Sum('total_objectives_pending')).get('count') or 0
        objectives_total = applications.aggregate(count=Sum('total_objectives_answers')).get('count') or 0
        
        return {
            "discursive_quantity": discursives_quantity, 
            "discursive_total": discursives_total, 
            "objective_quantity": objectives_quantity, 
            "objective_total": objectives_total,
            "total": objectives_total + discursives_total,
            "quantity": objectives_quantity + discursives_quantity,
        }
        
    def run_recalculate_sisu_tri_cache(self):
        try:
            auth_token = get_service_account_oauth2_token(settings.ANALYTICS_SERVICE_URL)
            
            token = auth_token
            
            if last_application := self.application_set.order_by('date').last():
            
                year = last_application.date.year
                
                IgnoreCacheTriDataThread(exam=self, token=token, url=settings.ANALYTICS_SERVICE_URL, year=year).start()
            else:
                ValueError("O caderno ainda não foi aplicado.")
            
        except Exception as e:
            ValueError('Não foi possível recalcular o caderno selecionado', repr(e))
            
    def recalculate_questions_followup_dashboard(self):
        """
            TASK PARA RECALCULAR O DASH
        """
        return
        #task aparentemten não é mais útil
        # from fiscallizeon.analytics.tasks import generate_data_exam_followup_questions_task
        # task = generate_data_exam_followup_questions_task
        
        # result = task.apply_async(task_id=f'RECALCULATE_APPLICATION_FOLLOWUP_DASHBOARD_QUESTIONS_{str(self.pk)}', kwargs={
        #     "exam_pk": str(self.pk),
        # }).forget()

    @cached_property
    def get_quality_values(self):
        return self.has_topic + self.has_ability + self.has_competence
    
    @cached_property
    def questions_give_score_sum(self):
        questions_give_score = self.examquestion_set.filter(
            statusquestion__isnull=False,
            statusquestion__annuled_give_score=True,
        )
        
        return sum(questions_give_score.values_list('weight', flat=True))

    def count_choice_and_sum_questions(self):
        CACHE_KEY = f'exam-{self.pk}-count-questions-choice'
        if cache.get(CACHE_KEY):
            return cache.get(CACHE_KEY)
        
        count_questions_choice = self.examquestion_set.availables(
            exclude_annuleds=True
        ).filter(
            question__category__in=[Question.CHOICE, Question.SUM_QUESTION]
        ).count()

        if self.has_foreign_languages:
            quantity_foreign_language_questions = self.examquestion_set.availables(exclude_annuleds=True
            ).filter(
            is_foreign_language=True,
            ).count()
            
            count_questions_choice = count_questions_choice - int(quantity_foreign_language_questions/2)
    
        cache.set(CACHE_KEY, count_questions_choice, timeout=300)


        return count_questions_choice
    
    def count_file_and_textual_questions(self): 
        CACHE_KEY = f'exam-{self.pk}-count-questions-discursive'
        if cache.get(CACHE_KEY):
            return cache.get(CACHE_KEY)
        
        count_questions_discursive = self.questions.availables(
            self, exclude_annuleds=True
        ).filter(
            category__in=[Question.FILE, Question.TEXTUAL]
        ).count()

        cache.set(CACHE_KEY, count_questions_discursive, timeout=300)

        return count_questions_discursive
    
    def count_answer_sum(self, student_application):
        from fiscallizeon.answers.models import SumAnswer
        return SumAnswer.objects.filter(student_application=student_application).count()
   
    def count_answer_choice(self, student_application): 
        from fiscallizeon.answers.models import OptionAnswer

        return OptionAnswer.objects.filter(
            student_application=student_application,
            status=OptionAnswer.ACTIVE,
            student_application__empty_questions=False
        ).count()
   
    def count_answer_file(self, student_application):
        from fiscallizeon.answers.models import FileAnswer

        return FileAnswer.objects.filter(
            student_application=student_application,
            # student_application__application__exam__total_grade__isnull=False,
            ).filter(
                Q(teacher_grade__isnull=False) | Q(empty=True)
        ).count()

    def count_answer_textual(self, student_application):
        from fiscallizeon.answers.models import TextualAnswer
        
        return TextualAnswer.objects.filter(
            student_application=student_application,
            # student_application__application__exam__total_grade__isnull=False,
            ).filter(
                Q(teacher_grade__isnull=False) | Q(empty=True)
        ).count()
    
    def total_discursive_pendence(self, student_application):
        count_questions_discursive = self.count_file_and_textual_questions()
        count_answer_file = self.count_answer_file(student_application)
        count_answer_textual = self.count_answer_textual(student_application)

        return count_questions_discursive - count_answer_file - count_answer_textual
    
    def total_choice_pendence(self, student_application):
        count_questions_choice = self.count_choice_and_sum_questions()
        count_total_blank = student_application.empty_option_questions.all().count()
        count_answer_choice = self.count_answer_choice(student_application)
        count_answer_sum = self.count_answer_sum(student_application)

        return count_questions_choice - count_total_blank - count_answer_choice - count_answer_sum

    def has_questions_created_with_ia(self):
        return self.questions.filter(created_with_ai=True).exists()

    def check_is_bag_exist(self):
        from fiscallizeon.applications.models import Application
        """
        Verifica se existem aplicações com answer_sheet para este exame
        """
        condition = (
            Q(
                Q(answer_sheet__isnull=False) & ~Q(answer_sheet="")
            ) | 
            Q(
                Q(room_distribution__exams_bag__isnull=False) & ~Q(room_distribution__exams_bag="")
            )
        )
        exists = Application.objects.filter(exam_id=self.pk).filter(condition).exists()

        return exists
    
    def check_started_applications_exist(self):
        now = timezone.localtime(timezone.now())
        
        applications = self.application_set.annotate(
            datetime_start = models.ExpressionWrapper(F('date') + F('start') + timedelta(hours=3), output_field=models.DateTimeField()),
        ).filter(
            datetime_start__lte=now
        )
        
        return applications.exists()
    
    def get_last_application(self):
        return self.application_set.order_by('created_at').last()
    
    @property
    def min_available_total_grade(self):
        """
            Essa função vai calcular qual o valor minimo para o total_grade do caderno
            Não pode ser menor que a soma dos valores travados das solicitações e dos examquestions
        """
        total_weight_unavailable = 0

        for exam_teacher_subject in self.examteachersubject_set.all():
            
            subject_note = exam_teacher_subject.subject_note
            
            blocked_exam_questions_weights = (
                exam_teacher_subject.examquestion_set.availables()
                .filter(block_weight=True)
                .aggregate(
                    models.Sum('weight')
                )
                .get('weight__sum') or 0
            )

            if exam_teacher_subject.block_subject_note and subject_note:

                total_weight_unavailable += subject_note

            else:

                total_weight_unavailable += blocked_exam_questions_weights
        
        return total_weight_unavailable
    
class ExamTeacherSubject(BaseModel):
    teacher_subject = models.ForeignKey(TeacherSubject, on_delete=models.PROTECT)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.SmallIntegerField(verbose_name="Quantidade de questões")
    note = models.TextField(verbose_name="Observações", null=False, blank=True, default="")
    order = models.SmallIntegerField(verbose_name="Ordem na prova", default=0)
    teacher_note = models.TextField(verbose_name="Anotações do professor", null=True, blank=True, default="", help_text="Digite aqui alguma informação importante para sua coordenação")
    subject_note = models.DecimalField("Nota da disciplina", max_digits=10, decimal_places=6, blank=True, null=True)
    block_subject_note = models.BooleanField("Bloquear nota do professor", default=False)
    is_foreign_language = models.BooleanField("É língua estrangeira", default=False)
    id_erp = models.CharField('Código no ERP', max_length=255, blank=True, null=True)

    history = HistoricalRecords(excluded_fields=['created_at', 'updated_at'])
    
    block_quantity_limit = models.BooleanField("Limitar a quantidade de questão inseridas", help_text="Ao ativar essa opção você limitará a quantidade de questões que podem ser inseridas por este professor", default=False)

    block_questions_quantity = models.BooleanField("Definir quantidade de questões objetivas/discursivas", default=False)
    
    distribute_scores_freely = models.BooleanField("Permitir o professor distribuir pontuação livremente", default=False)   

    objective_quantity = models.IntegerField("Objetivas", help_text="Quantidade de questões objetivas que poderão ser adicionada ao caderno", default=0)
    discursive_quantity = models.IntegerField("Discursivas", help_text="Quantidade de questões discursivas que poderão ser adicionada ao caderno", default=0)
    
    elaboration_email_sent = models.BooleanField("O email de elaboração foi enviado", default=False)
    
    reviewed_by = models.ManyToManyField("inspectors.Inspector", blank=True)

    reviewer_email_sent = models.BooleanField("Envio do email de revisão para o revisor", default=False)
    
    objects = ExamTeacherSubjectManager()
    
    has_error_create_exam_question_ia =  models.BooleanField("Erro ao gerar ExamQuestion com IA", default=False)
    
    support_image_generate_question = models.ImageField(upload_to='question/ia/', null=True, blank=True, storage=PrivateMediaStorage())

    WAITING, GENERATING, FINISHED, ERROR = range(4)
    QUESTION_GENERATE_STATUS = (
        (WAITING, "Inicial"),
        (GENERATING, "Gerando"),
        (FINISHED, "Finalizado"),
        (ERROR, "Erro"),
    )
    question_generation_status_with_ai = models.PositiveSmallIntegerField(
        'Status da geração de questão com ia', 
        choices=QUESTION_GENERATE_STATUS, 
        default=WAITING
    )
    
    def __str__(self):
        return f'{self.teacher_subject.teacher.name} - {self.teacher_subject.subject.name}'
    
    class Meta:
        verbose_name = 'Professor na prova'
        verbose_name_plural = 'Professores na prova'
        ordering = ('order', )
        unique_together = (
            ('exam', 'order')
        )
    
    @property
    def object_serialized(self):
        from fiscallizeon.exams.serializers.exams import ExamTeacherSubjectSerializer
        return ExamTeacherSubjectSerializer(self).data
    
    @hook("after_create")
    @hook("after_update")
    def send_email_to_teacher(self):
        """
        Envia email para o professor caso ele não seja um professor abstrato e a data de liberação seja igual a hoje e ele ainda não tenha recebido email
        
        -- Se a data de liberação dos resultados for igual a hoje ele irá enviar um email para o professor
        -- Se não ele só iniciará a thread quando for solicitado no command: send_email_to_teachers_after_release_elaboration
            que deve rodar todo dia após as 00:00h
        """
        today = timezone.now().date()
        if self.teacher_subject and self.teacher_subject.teacher.is_inspector_ia:
            self.elaboration_email_sent = True
            return

        if self.teacher_subject.teacher.user == self.exam.created_by:
            self.elaboration_email_sent = True
            return
        
        if self.has_changed('teacher_subject'):
            self.elaboration_email_sent = False
        
        if not self.teacher_subject.teacher.is_abstract and (self.exam.get_elaboration_release_date <= today and not self.elaboration_email_sent):
            template = get_template('inspectors/mail_template/default.html')
            html = template.render({ "object": self, "BASE_URL": settings.BASE_URL })
            subject = 'Solicitação para elaboração de quest' + ('ões' if self.quantity > 1 else 'ão')
            to = [self.teacher_subject.teacher.email]
            EmailThread(subject, html, to).start()
            
            self.elaboration_email_sent = True
        
        self.save(skip_hooks=True)

    def send_email_to_teacher_reviewer(self):

        """
        O email que será enviado para o reviewed_by desse exam_teacher_subject
        """

        data_review = {
            "name_teacher_elaboration": self.teacher_subject.teacher.name,
            "name_exam": self.exam.name,
            "subject": self.teacher_subject.subject.name,
            "grade": self.grade.full_name,
            "deadline": self.exam.review_deadline,
            "link": f'{settings.BASE_URL}{reverse("exams:exam_review", kwargs={"pk": self.exam.pk})}?exam_teacher_subject={self.pk}',
        }
            
        reviewed_by_data = self.reviewed_by.all().values_list('name',"email")
        
        for review_name,review_email in reviewed_by_data:

            data_review["name_teacher"] = review_name

            template = get_template('inspectors/mail_template/send_teacher_to_teacher_review_questions.html')
            html = template.render(data_review)
            subject = f'{data_review["name_exam"]} - Você possui uma pendência de revisão nesse caderno'
            to = [review_email]
            EmailThread(subject, html, to).start()

        # Salva como enviado os email de revisores desse exam_teacher_subject
        self.reviewer_email_sent = True

        self.save(skip_hooks=True)

    def send_recurrent_notification_to_teacher(self):
        """
            Envia email recorrente para o professor baseado na configuração de notificação do cliente,
            avisando que existem cadernos (sem questões) que ele deve finalizar.
            Esse método é chamado no command 'send_recurrent_notification_to_teacher'.
        """
        if self.teacher_subject and self.teacher_subject.teacher.is_inspector_ia:
            return

        if self.teacher_subject.teacher.user == self.exam.created_by:
            return
        
        template = get_template('inspectors/mail_template/send_notification_to_teacher.html')
        html = template.render({ "object": self, "BASE_URL": settings.BASE_URL })
        subject = 'Lembrete de solicitação de elaboração de prova'
        to = [self.teacher_subject.teacher.email]
        EmailThread(subject, html, to).start()

    @hook("after_save")
    @hook("after_delete")
    def clear_exam_questions_cache(self):
        self.exam.clear_questions_numbers_cache()

    @hook("after_update", when="exam", has_changed=True)
    def change_exam_hook(self):
        self.examquestion_set.all().update(exam=self.exam)

    @hook("after_update", when="subject_note", has_changed=True)
    def update_questions_weight(self):
        """
            DOC_KWTZH4EQ
        """ 
        exam = self.exam
        exam.distribute_weights(exam_teacher_subject=self)
            
    @hook("before_update", when="block_subject_note", has_changed=True, is_now=False)
    def remove_subject_note(self):
        self.subject_note = None
        
    def get_status(self):
        """
            Aguardando correção: Qualquer momento que tenha questões aguardando correção
            Aberto: no prazo sem questão
            Atrasada: fora do prazo && ((sem questão) || (Menos questão do que o solicitado) || (com sugerir correção)) 
            Análise: Qualquer momento que a quantidade de questões >= solicitado
            Elaborando: no prazo && qualquer qtd de questão
        """
        
        STATUS = {
            "AWAIT_CORRECTION": {
                "class": "bg-warning-soft text-warning-soft",
                "label": "Aguardando correção"
            },
            "OPENED": {
                "class": "bg-secondary-soft text-secondary",
                "label": "Revisão de itens"
            },
            "LATE": {
                "class": "bg-danger-soft text-danger",
                "label": "Atrasada"
            },
            "IN_REVIEW": {
                "class": "bg-success-soft text-success",
                "label": "Análise"
            },
            "ELABORATING": {
                "class": "bg-primary-soft text-primary",
                "label": "Elaborando"
            }
        }
        if self.status == 'Aguardando correção':
            return STATUS['AWAIT_CORRECTION']
        if self.status == 'Análise':
            return STATUS['IN_REVIEW']
        elif self.status == 'Revisão de itens':
            return STATUS['OPENED']
        elif self.status == 'Elaborando':    
            return STATUS['ELABORATING']
        elif self.is_late:
            return STATUS['LATE']
        
        return STATUS['OPENED']
    
    def get_reviews_details(self):
        
        exam_questions = self.examquestion_set.all().distinct()
        user = self.teacher_subject.teacher.user
        
        count = exam_questions.count()
        count_reviewed_questions = exam_questions.filter(statusquestion__user=user).distinct().count()
        count_seen_questions = exam_questions.filter(Q(statusquestion__status=StatusQuestion.SEEN), statusquestion__user=user).distinct().count()
        count_approved_questions = exam_questions.filter(Q(statusquestion__status=StatusQuestion.APPROVED), statusquestion__user=user).distinct().count()
        count_reproved_questions = exam_questions.filter(Q(statusquestion__status=StatusQuestion.REPROVED), statusquestion__user=user).distinct().count()
        count_correction_pending_questions = exam_questions.filter(Q(statusquestion__status=StatusQuestion.CORRECTION_PENDING), statusquestion__user=user).distinct().count()
        count_question_choices = exam_questions.filter(question__category=Question.CHOICE).distinct().count()
        count_feedbacks = exam_questions.filter(question__category=Question.CHOICE, question__alternatives__is_correct=True).distinct().count()
        count_empty_feedbacks = count_question_choices - count_feedbacks
        
        count_peding_questions = exam_questions.filter(statusquestion__status=StatusQuestion.CORRECTION_PENDING, statusquestion__active=True).distinct().count()
        count_corrected_questions = exam_questions.filter(statusquestion__status=StatusQuestion.CORRECTED, statusquestion__active=True).distinct().count()
        count_opened_questions =  count - (count_approved_questions + count_reproved_questions + count_peding_questions + count_corrected_questions)

        return {
            "count": count,
            "count_reviewed_questions": count_reviewed_questions, 
            "count_seen_questions": count_seen_questions, 
            "count_approved_questions": count_approved_questions, 
            "count_reproved_questions": count_reproved_questions, 
            "count_correction_pending_questions": count_correction_pending_questions, 
            "count_question_choices": count_question_choices, 
            "count_feedbacks": count_feedbacks, 
            "count_empty_feedbacks": count_empty_feedbacks, 
            
            "count_peding_questions": count_peding_questions, 
            "count_corrected_questions": count_corrected_questions, 
            "count_opened_questions": count_opened_questions, 
        }
        
    def can_add_questions(self):
        exam_questions = self.examquestion_set.availables()
        if self.block_questions_quantity:
            discursive_limit_hit = exam_questions.filter(question__category__in=[Question.TEXTUAL, Question.FILE]).count() >= self.discursive_quantity
            objective_limit_hit = exam_questions.filter(question__category=Question.CHOICE).count() >= self.objective_quantity
            total_limit_hit = exam_questions.count() >= self.quantity

            if self.quantity > self.discursive_quantity + self.objective_quantity:
                if discursive_limit_hit and objective_limit_hit and total_limit_hit:
                    return False
            elif discursive_limit_hit and objective_limit_hit:
                return False
        if self.block_quantity_limit and exam_questions.count() >= self.quantity:
            return False
        return True
    
    @property
    def elaboration_expired(self):
        return self.exam.elaboration_deadline and self.exam.elaboration_deadline < timezone.localtime(timezone.now()).date()
    
    @hook('after_create')
    @hook('after_delete')
    @hook('after_update', when='quantity', has_changed=True)
    def hook_recalculate_questions_followup_dashboard(self):
        self.exam.recalculate_questions_followup_dashboard()
    
    @hook('after_create', when='teacher_subject.teacher.is_inspector_ia', is_now=True)
    def created_exam_questions_ia(self):
        from fiscallizeon.exams.tasks.create_exam_question_with_ia import create_exam_question_ia
    
        user = self.teacher_subject.teacher.user
        user_prompt = self.note 
        exam_id = self.exam.pk
        quantity = self.quantity
        self.question_generation_status_with_ai = ExamTeacherSubject.GENERATING
        self.save()

        create_exam_question_ia.apply_async(
            args=[user.pk ,exam_id, self.pk, user_prompt, quantity],
            task_id=f'AI_QUESTION_CREATION_{str(self.pk)}'
        )    

    @property
    def urls(self):
        return {
            "api_update": reverse('exams:examteachersubject-detail', kwargs={ "pk": self.pk }),
            "api_distribute_weights": reverse('exams:api-exam-distribute-weights', kwargs={ "pk": self.pk }),
            "api_create_exam_question": reverse('exams:api-exam-create-exam-question', kwargs={ "pk": self.pk }),
            "can_add_examquestion": reverse('exams:examteachersubject-can-add-examquestion', kwargs={ "pk": self.pk }),
            "api_examquestions_weights": reverse('exams:examteachersubject-examquestions-weights', kwargs={ "pk": self.pk }),
            "add_questions": reverse('exams:exam_teacher_subject_before_edit_questions', kwargs={ "pk": self.pk }),
            "api_freemium_update": reverse('exams:freemium-update-exam-teacher-subject', kwargs={ "pk": self.pk }),
        }
    
    @property
    def exam_questions_outside_ets(self):
        exam_questions_outside_ets = ExamQuestion.objects.filter(
            source_exam_teacher_subject=self.pk
        ).exclude(exam_teacher_subject=self.pk)
        return exam_questions_outside_ets.count()
    
    def has_questions_generate_or_modified_by_ia(self):
        questions = self.exam.questions
        quetion = questions.filter(created_with_ai=True).exists()
        print(quetion)
        return quetion

class ExamQuestion(BaseModel):
    question = models.ForeignKey(Question, verbose_name="Questão", on_delete=models.PROTECT)
    exam = models.ForeignKey(Exam, verbose_name="Prova", on_delete=models.CASCADE)
    exam_teacher_subject = models.ForeignKey(ExamTeacherSubject, verbose_name="Disciplina/Professor", on_delete=models.CASCADE, null=True, blank=True)
    source_exam_teacher_subject = models.ForeignKey(ExamTeacherSubject, related_name="exam_questions", on_delete=models.CASCADE, verbose_name="Solicitação original", blank=True, null=True)
    order = models.SmallIntegerField(verbose_name="Ordem na prova", default=0)
    weight = models.DecimalField("Nota da questão na prova", max_digits=10, decimal_places=6, default=Decimal(1.0000))
    block_weight = models.BooleanField("Bloquear peso da questão", default=False)
    is_abstract = models.BooleanField("O exame é abstrato, usada apenas na geração de gabarito avulso", default=False)
    is_foreign_language = models.BooleanField("É língua estrangeira", default=False)
    is_late = models.BooleanField("Foi adicionada em uma solicitação atrasada", default=False)
    short_code = models.CharField("Código de indetificação curto", max_length=10, blank=True, null=True)
    id_erp = models.CharField('Código no ERP', max_length=255, blank=True, null=True)
    
    objects = ExamQuestionManager()

    history = HistoricalRecords(excluded_fields=['created_at', 'updated_at'])
    
    class Meta:
        verbose_name = 'Questão na prova'
        verbose_name_plural = 'Questões na prova'
        unique_together = (
            ('question', 'exam', 'exam_teacher_subject'),
            ('exam', 'exam_teacher_subject', 'order'),
        )
        ordering = ("order", )

    @property
    def has_duplicate_enunciation(self):

        from django.contrib.postgres.search import TrigramSimilarity

        return ExamQuestion.objects.filter(
            exam=self.exam
        ).exclude(
            pk=self.pk
        ).annotate(
            similarity=TrigramSimilarity('question__enunciation', self.question.enunciation),
        ).filter(similarity__gt=0.8).exists()

    @hook("after_create")
    def set_source_exam_teacher_subject(self):
        self.source_exam_teacher_subject = self.exam_teacher_subject

    @hook("after_update", when='weight', has_changed=True)
    def update_answers_grades(self):
        from fiscallizeon.exams.tasks.update_answers_grade import update_answers_grade

        initial_weight = self.initial_value('weight')

        if initial_weight <= 0:
            return
        
        proportion = round((Decimal(self.weight) / initial_weight), 2)

        update_answers_grade.apply_async(
            args=[str(self.pk), proportion],
        )
        if self.block_weight:
            self.exam.distribute_weights(exam_teacher_subject=self.exam_teacher_subject)
    
    @hook("after_update", when="block_weight", is_now=False)
    def recalculate_exam(self):
        if (self.exam_teacher_subject and self.exam_teacher_subject.subject_note) or self.exam.total_grade:
            self.exam.distribute_weights(exam_teacher_subject=self.exam_teacher_subject)

    @hook("after_create")
    @hook("after_delete")
    def update_questions_weight(self):
        if not self.exam.total_grade:
            if self.exam_teacher_subject and self.exam_teacher_subject.subject_note:
                self.exam_teacher_subject.update_questions_weight()
        else:
            self.exam.distribute_weights(exam_teacher_subject=self.exam_teacher_subject)

    @hook("before_create")
    def create_short_code(self):
        self.short_code = generate_random_string(4).upper()

    @hook("after_save")
    @hook("after_delete")
    def clear_exam_questions_number_cache(self):
        self.exam.clear_questions_numbers_cache()

    @hook("before_delete")
    def delete_erp(self):
        Integration = apps.get_model('integrations', 'Integration')
        client = self.exam.coordinations.first().unity.client
        if not client:
            return
        
        integration = Integration.objects.filter(
            client=client,
            erp=Integration.REALMS,
        ).first()

        if not integration:
            return

        if self.id_erp:
            body = {
                'task_author': integration.username,
                'question_ids': [self.id_erp],
            }
            result = realms.delete_questions_batch(client, self.exam, body)

    def question_is_completed(self):
        question = self.question
        user = self.exam_teacher_subject.teacher_subject.teacher.user
        required_fields = user.client_teacher_configuration(level=self.exam_teacher_subject.grade.level)
        
        if required_fields:
            if required_fields.template and question.category in [Question.CHOICE, Question.SUM_QUESTION] and not question.alternatives.using('default').filter(is_correct=True).exists():
                return False
            if required_fields.topics and not question.topics.exists():
                return False
            if required_fields.abilities and not question.abilities.exists():
                return False
            if required_fields.competences and not question.competences.exists():
                return False
            if required_fields.difficult and not question.level != Question.UNDEFINED:
                return False
            if required_fields.pedagogical_data and not question.subject:
                return False
            if required_fields.commented_response and not question.commented_awnser:
                return False
        return True
        
    @hook("after_create")
    def create_status(self):
        if self.exam.is_abstract:
            return
        
        teacher = self.exam_teacher_subject.teacher_subject.teacher
        user = teacher.user

        status = StatusQuestion.OPENED
        
        if (user.client_has_new_teacher_experience or teacher.has_new_teacher_experience) or self.question.created_with_ai:
            if not self.question_is_completed():
                status = StatusQuestion.DRAFT

        if (user.client_has_new_teacher_experience or teacher.has_new_teacher_experience) and self.question.category in [Question.CHOICE, Question.SUM_QUESTION] and self.exam.quantity_alternatives and self.exam.quantity_alternatives != len(self.question.alternatives.using('default').all()):
            status = StatusQuestion.DRAFT

        StatusQuestion.objects.create(
            exam_question=self,
            status=status
        )

    @property
    def last_status(self):
        last_status = self.statusquestion_set.filter(
            active=True
        ).last()

        return last_status.get_status_display() if last_status else "Em aberto" 
   
    @property
    def last_status_v2(self):
        return self.statusquestion_set.exclude(status__in=[StatusQuestion.SEEN, StatusQuestion.RESPONSE]).filter(
            active=True,
        ).order_by('created_at').last()

    @property
    def status_list(self):
        import json
        from fiscallizeon.exams.serializers.exams import StatusQuestionSerializer

        return json.loads(json.dumps(StatusQuestionSerializer(
            StatusQuestion.objects.filter(
                exam_question=self,
                exam_question__exam_teacher_subject=self.exam_teacher_subject,
            ).exclude(
                status=StatusQuestion.RESPONSE
            ).distinct(), 
            many=True
        ).data))
    
    @property
    def exam_question_number(self):
        if number := self.exam.number_print_question(self.question):
            return number
        return None
    
    @property
    def can_be_remove(self):
        """
            DEFINE SE O EXAMQUESTION PODE OU NÃO SER DELETADO
        """
        last_status_is_approved = self.statusquestion_set.filter(active=True, status=StatusQuestion.APPROVED).exclude(status__in=[StatusQuestion.SEEN, StatusQuestion.RESPONSE]).last()
        user = self.exam_teacher_subject.teacher_subject.teacher.user
        if user.questions_configuration:
            if last_status_is_approved and user.questions_configuration.block_edit_question_aproveds:
                return False
            return True
        
        return True
    
    def send_email_to_coordination_after_AI_generates_questions(self):
        if not self.exam_teacher_subject.teacher_subject.teacher.is_inspector_ia:
            return
        
        subject = self.exam_teacher_subject.teacher_subject.subject
        teacher = self.exam_teacher_subject.history.all().order_by('history_date').first().history_user

        template = get_template('mail_template/send_to_teachers_coordinator.html')
        html = template.render({ "object": self })
        subject = 'Existem cadernos para você revisar'
        to = [teacher.email]
        EmailThread(subject, html, to).start()

    # @hook('after_create')
    def send_email_to_teachers_coordinator(self):
        if self.exam.is_abstract:
            return

        from fiscallizeon.inspectors.models import Inspector
        teacher = self.exam_teacher_subject.teacher_subject.teacher
        subject = self.exam_teacher_subject.teacher_subject.subject
        quantity = self.exam_teacher_subject.quantity
        examquestions_count = self.exam_teacher_subject.examquestion_set.all().count()
        
        if examquestions_count == quantity:
            
            discipline_coordinators = Inspector.objects.filter(
                is_discipline_coordinator=True,
                subjects__subject=subject,
                coordinations__in=teacher.user.get_coordinations_cache()
            )
            
            emails = discipline_coordinators.values_list('email', flat=True)
            
            template = get_template('mail_template/send_to_teachers_coordinator.html')
            html = template.render({ "object": self })
            subject = 'Existem cadernos para você revisar'
            to = emails
            EmailThread(subject, html, to).start()
    
    def send_notification_to_teacher_after_reprove_question(self):
        """
            Envia email para o professor quando uma questão é reprovada.
        """
        if self.exam_teacher_subject and self.exam_teacher_subject.teacher_subject  and self.exam_teacher_subject.teacher_subject.teacher.is_inspector_ia:
            return
        
        template = get_template('inspectors/mail_template/send_notification_to_teacher_after_reprove_question.html')
        html = template.render({ "object": self.exam_teacher_subject, "BASE_URL": settings.BASE_URL, "examquestion": self })
        subject = 'Que pena, o seu coordenador reprovou 1 de suas questões.'
        to = [self.exam_teacher_subject.teacher_subject.teacher.email]
        EmailThread(subject, html, to).start()
        
    def send_notification_to_teacher_after_correction_pending(self):
        """
            Envia email para o professor quando é sugerida uma correção.
        """
        if self.exam_teacher_subject and self.exam_teacher_subject.teacher_subject  and self.exam_teacher_subject.teacher_subject.teacher.is_inspector_ia:
            return
        
        template = get_template('inspectors/mail_template/send_notification_to_teacher_after_correction_pending.html')
        html = template.render({ "object": self.exam_teacher_subject, "BASE_URL": settings.BASE_URL, "examquestion": self })
        subject = 'Tem uma questão necessitando correção na sua avaliação.'
        to = [self.exam_teacher_subject.teacher_subject.teacher.email]
        EmailThread(subject, html, to).start()
        
    @hook('after_create')
    @hook('after_delete')
    def hook_recalculate_questions_followup_dashboard(self):
        self.exam.recalculate_questions_followup_dashboard()

    @property
    def has_answer(self):
        from fiscallizeon.answers.models import TextualAnswer, FileAnswer, OptionAnswer, SumAnswer

        textual_answers = TextualAnswer.objects.filter(question=self.question, student_application__application__exam=self.exam).exists()
        file_answers = FileAnswer.objects.filter(question=self.question, student_application__application__exam=self.exam).exists()
        option_answers = OptionAnswer.objects.filter(question_option__question=self.question, student_application__application__exam=self.exam).exists()
        sum_answers = SumAnswer.objects.filter(question=self.question, student_application__application__exam=self.exam).exists()
        
        if textual_answers or file_answers or option_answers or sum_answers:
            return True
        
        return False

class StatusQuestion(BaseModel):
    exam_question = models.ForeignKey(ExamQuestion, verbose_name="Questão na prova", on_delete=models.CASCADE)
    source_status_question = models.ForeignKey('exams.StatusQuestion', verbose_name="Status fonte", on_delete=models.CASCADE, null=True, blank=True)
    APPROVED, REPROVED, OPENED, CORRECTION_PENDING, CORRECTED, SEEN, ANNULLED, USE_LATER, DRAFT, RESPONSE = range(10)
    STATUS_CHOICES = (
        (APPROVED, "Aprovada"),
        (REPROVED, "Reprovada"),
        (OPENED, "Em aberto"),
        (CORRECTION_PENDING, "Aguardando correção"),
        (CORRECTED, "Corrigido"),
        (SEEN, "Visto"),
        (ANNULLED, "Anulada"),
        (USE_LATER, "Usar depois"),
        (DRAFT, "Rascunho"),
        (RESPONSE, "Resposta do professor"),
    )
    status = models.PositiveSmallIntegerField("Situação", choices=STATUS_CHOICES, default=OPENED)
    note = models.TextField(verbose_name="Observação", null=False, blank=True, default="")
    question_fragment = models.TextField(verbose_name="Fragmento da questão", null=False, blank=True, default="")
    user = models.ForeignKey(User, verbose_name="Usuário", null=True, blank=True, on_delete=models.CASCADE, related_name="user")
    annuled_give_score = models.BooleanField("Questão anulada e pontuação dada", default=False)
    annuled_distribute_exam_teacher_subject = models.BooleanField("Anulada e pontuação distribuída apenas na solicitação", default=False)
    is_checked_by = models.ForeignKey(User, verbose_name="Verificado por", null=True, blank=True, on_delete=models.CASCADE, related_name='is_checked_by')
    active = models.BooleanField("Está ativo", default=True)

    class Meta:
        ordering = ["-created_at", ]

    @hook("after_create", when="status", is_now=REPROVED)
    @hook("after_create", when="status", is_now=APPROVED)
    @hook("after_create", when="status", is_now=ANNULLED)
    @hook("after_create", when="status", is_now=USE_LATER)
    @hook("after_create", when="status", is_now=OPENED)
    def update_questions_weight(self):
        
        force_distribute_weights = 0

        if self.status == self.ANNULLED and not self.annuled_give_score or self.annuled_distribute_exam_teacher_subject:
            force_distribute_weights = self.exam_question.weight
            
        self.exam_question.exam.distribute_weights(exam_teacher_subject=self.exam_question.exam_teacher_subject if self.exam_question else None, force_distribute_weights=force_distribute_weights, distribute_exam_teacher_subject=self.annuled_distribute_exam_teacher_subject)
        self.exam_question.exam.recalculate_questions_followup_dashboard()

    @hook("after_delete", when="status", is_now=ANNULLED)
    def hook_update_questions_weight_after_delete_annuled(self):
        self.exam_question.exam.distribute_weights(exam_teacher_subject=self.exam_question.exam_teacher_subject if self.exam_question else None)
        self.exam_question.exam.recalculate_questions_followup_dashboard()

    @hook("after_create")
    def deactive_before_status(self):
        if not self.status in [self.SEEN, self.RESPONSE]:
            self.exam_question.statusquestion_set.update(active=False)
            self.exam_question.statusquestion_set.values('active')
            self.active = True
            self.save()
            
    @hook("before_create", when="status", is_now=CORRECTED)
    def send_before_correction_pending(self):
        last_status_question = StatusQuestion.objects.filter(exam_question=self.exam_question).order_by('created_at').last()
        if last_status_question.status == self.CORRECTION_PENDING:
            template = get_template('mail_template/send_before_correction_pending.html')
            html = template.render({"object":self, "email":True})
            subject = 'Questão Corrigida'
            to = [f'{last_status_question.user.email}']
            EmailThread(subject, html, to).start()
    
    @hook('after_create', when='status', is_now=REPROVED)
    def send_email_to_teacher_after_reprove_question(self):
        self.exam_question.send_notification_to_teacher_after_reprove_question()

    @hook('after_create', when='status', is_now=CORRECTION_PENDING)
    def send_email_to_teacher_after_correction_pending(self):
        self.exam_question.send_notification_to_teacher_after_correction_pending()

    @hook('after_save')
    def clear_exam_questions_number_cache(self):
        self.exam_question.exam.clear_questions_numbers_cache()
        
    @staticmethod
    def get_unavailables_status():
        return [StatusQuestion.REPROVED, StatusQuestion.DRAFT, StatusQuestion.USE_LATER]

    @staticmethod
    def get_unavailables_status():
        return [StatusQuestion.ANNULLED, StatusQuestion.USE_LATER, StatusQuestion.REPROVED, StatusQuestion.DRAFT]

class QuestionTagStatusQuestion(BaseModel):
    status = models.ForeignKey(StatusQuestion, verbose_name="Situação da questão", on_delete=models.CASCADE)
    tags = models.ManyToManyField(QuestionTag, verbose_name="Tags da questão", blank=True)

    class Meta:
        ordering = ["-created_at", ]
        verbose_name = "Tags em status de questão"
        verbose_name_plural = "Tags em status de questões"

class ExamHeader(BaseModel):
    name = models.CharField("Nome do cabeçalho", max_length=100, default="Cabeçalho")
    content = HTMLField()
    user = models.ForeignKey(User, verbose_name="Usuário", on_delete=models.CASCADE)
    main_header = models.BooleanField("Você quer usar esse template como padrão?", default=False)
    
    @hook("before_save", when="main_header", is_now=True)
    def add_defaults(self):
        ExamHeader.objects.filter(user__coordination_member__coordination__unity__client__in=self.user.get_clients()).exclude(pk=self.pk).update(main_header=False)

    class Meta:
        ordering = ('-main_header', '-created_at')


    def __str__(self):
        return self.name
class ExamOrientation(BaseModel):
    title = models.CharField("Título", max_length=100, default="Orientações Padrão")
    content = HTMLField()
    user = models.ForeignKey(User, verbose_name="Usuário", on_delete=models.CASCADE, blank=True)
    
    class Meta:
        ordering = ('-created_at',)


    def __str__(self):
        return self.title
    
class Wrong(BaseModel):
    student = models.ForeignKey('students.Student', related_name="wrongs", verbose_name=("Aluno"), on_delete=models.CASCADE)
    exam_question = models.ForeignKey(ExamQuestion, verbose_name=("Questão no Exame"), related_name="wrongs", on_delete=models.CASCADE)
    student_description = models.TextField("Descrição do aluno")
    AWAITING_REVIEW, ACCEPTED, REFUSED, REOPENED  = range(4)
    STATUS_CHOICES = (
        (AWAITING_REVIEW, "Aguardando revisão"),
        (ACCEPTED, "Aceita"),
        (REFUSED, "Recusada"),
        (REOPENED, "Reaberta"),
    )
    status = models.PositiveSmallIntegerField("Situação", choices=STATUS_CHOICES, default=AWAITING_REVIEW)
    response = models.TextField("Resposta ao aluno", null=True, blank=True)
    user = models.ForeignKey(User, verbose_name="Usuário", on_delete=models.CASCADE, null=True, blank=True)
    response_date = models.DateTimeField("Data da resposta", null=True, blank=True)
    
    class Meta:
        ordering = ('-created_at', )


    def __str__(self):
        return f'{self.student.name}'


def directory_path_file(instance, filename):
    return f'exams-teacher-subject/{instance.exam_teacher_subject.pk}/files/{filename}'


class ExamTeacherSubjectFile(BaseModel):
    file = models.FileField(
        'arquivo', upload_to=directory_path_file, null=True, blank=True
    )
    exam_teacher_subject = models.ForeignKey(
        ExamTeacherSubject, verbose_name='professor na prova', on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'arquivo do professor na prova'
        verbose_name_plural = 'arquivos dos professores nas provas'
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.exam_teacher_subject} - {self.file.name}'

class ClientCustomPage(BaseModel):
    client = models.ForeignKey("clients.Client", verbose_name=("Cliente"), on_delete=models.CASCADE)
    name = models.CharField("Nome da página", max_length=255, default="Página customizada")
    STUDENT_EXAM, SIGNATURE_SHEET, OBJECTIVE_ANSWER_SHEET, DISCURSIVE_ANSWER_SHEET, AFTER_STUDENT_EXAM = range(5)
    LOCATION_CHOICES = (
		(STUDENT_EXAM, "Antes do caderno do aluno"),
		(AFTER_STUDENT_EXAM, "Após o caderno do aluno"),
		(SIGNATURE_SHEET, "Antes da lista de presença"),
		(OBJECTIVE_ANSWER_SHEET, "Antes da folha de respostas objetivas"),
		(DISCURSIVE_ANSWER_SHEET, "Antes da folha de respostas discursivas"),
	)
    location = models.SmallIntegerField("Local", choices=LOCATION_CHOICES, default=STUDENT_EXAM)
    HTML, PDF = range(2)
    TYPE_CHOICES = (
		(HTML, "HTML"),
		(PDF, "PDF"),
	)
    type = models.SmallIntegerField("Tipo de arquivo", choices=TYPE_CHOICES, default=HTML, blank=True)
    file = models.FileField("Arquivo HTML", upload_to="custom_pages", max_length=10000, blank=True, null=True)
    content = HTMLField("Conteúdo HTML", blank=True, null=True)
    
    def get_content(self, application_student=None, school_classe=None, application=None):
        classe = school_classe
        content = str(self.content)
        
        if application_student:
            if "#Unidade" in content or "#Turma" in content or "#Segmento" in content or "#Serie" in content:
                if classe := application_student.get_last_class_student():
                    content = content.replace("#NomeDaTurma", classe.name)
                    content = content.replace("#Segmento", classe.grade.get_level_display())
                    content = content.replace("#Serie", classe.grade.name_grade)
                    content = content.replace("#Unidade", classe.coordination.unity.name)
                    
            if "#Disciplina" in content:
                subjects_names = application_student.application.exam.get_subjects().values_list('name', flat=True)
                content = content.replace("#Disciplina", ", ".join(subjects_names))
                
            if "#NomeDoAluno" in content:
                content = content.replace("#NomeDoAluno", application_student.student.name)
        
        if classe:
            if "#Unidade" in content or "#NomeDaTurma" in content or "#Segmento" in content or "#Serie" in content:
                content = content.replace("#NomeDaTurma", classe.name)
                content = content.replace("#Segmento", classe.grade.get_level_display())
                content = content.replace("#Serie", classe.grade.name_grade)
                content = content.replace("#Unidade", classe.coordination.unity.name)
        
        if application:
            if "#Disciplina" in content:
                subjects_names = application.exam.get_subjects().values_list('name', flat=True)
                content = content.replace("#Disciplina", ", ".join(subjects_names))
            
        if not application_student and not classe and not application:
            content = content.replace("#NomeDaTurma", "")
            content = content.replace("#Unidade", "")
            content = content.replace("#Turma", "")
            content = content.replace("#Segmento", "")
            content = content.replace("#Serie", "")
            content = content.replace("#Disciplina", "")
            content = content.replace("#NomeDoAluno", "")
            
        return content
    
class ExamBackgroundImage(BaseModel):
    client = models.ForeignKey("clients.Client", verbose_name=("Cliente"), related_name='exams_backgrounds', on_delete=models.CASCADE)
    name = models.CharField("Identificador", max_length=255)
    image = models.ImageField("Imagem de fundo", upload_to="exams_backgrounds/", max_length=10000)
    
    class Meta:
        verbose_name = 'Imagem de fundo'
        verbose_name_plural = 'Imagens de fundo'