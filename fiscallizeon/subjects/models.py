import time
from regex import D
from datetime import timedelta

import numpy as np
import pandas as pd
from django_lifecycle import hook
from sentry_sdk import capture_message

from django.apps import apps
from django.conf import settings
from django.db.models import Q
from django.db import models
from django.core.cache import cache
from django.contrib.contenttypes.fields import GenericRelation

from fiscallizeon.core.models import BaseModel
from fiscallizeon.classes.models import Grade
from fiscallizeon.subjects.managers import KnowledgeAreaManager, SubjectManager, TopicManager, MainTopicManager
from fiscallizeon.clients.models import Client
from fiscallizeon.accounts.models import User
from fiscallizeon.bncc.utils import get_bncc
from fiscallizeon.core.utils import round_half_up


class KnowledgeArea(BaseModel):
    name = models.CharField('Título', max_length=255)
    grades = models.ManyToManyField(Grade, verbose_name="Séries")

    objects = KnowledgeAreaManager()
    class Meta:
        verbose_name = 'Área de conhecimento'
        verbose_name_plural = 'Áreas de conhecimento'

    def __str__(self):
        return f'{self.name}'


class Subject(BaseModel):
    knowledge_area = models.ForeignKey(KnowledgeArea, on_delete=models.CASCADE)
    name = models.CharField('Nome da disciplina', max_length=255)
    parent_subject = models.ForeignKey('subjects.Subject', verbose_name="Disciplina de referência", on_delete=models.PROTECT, null=True, blank=True, help_text="A disciplina de referência será a fonte para geração das competências e habilidades da BNCC.")
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True)
    created_by = models.ForeignKey(User, verbose_name="Criado por", null=True, blank=True, on_delete=models.PROTECT)
    is_foreign_language_subject =  models.BooleanField("Disciplina de língua estrangeira", default=False, blank=True)

    objects = SubjectManager()
    
    performances = GenericRelation('analytics.GenericPerformances', related_query_name="subject_performances")

    class Meta:
        verbose_name = 'Disciplina'
        verbose_name_plural = 'Disciplinas'
        ordering = ['name']

    @hook("before_save")
    def check_is_parent_subject_is_the_same(self):
        if self.parent_subject == self:
            raise ValueError("A disciplina de referência não pode ser a própria disciplina.")
        

    def __str__(self):
        return f'({self.client if self.client else "Lize"}) - {self.name} - {self.knowledge_area} - {self.created_by.name if self.created_by else ""}'
    
    def last_performance(self, exam=None, application_student=None, student=None, classe=None):
        generic_performance = self.performances.using('default').filter(
            Q(exam=exam) if exam else Q(exam__isnull=True),
            Q(application_student=application_student) if application_student else Q(application_student__isnull=True),
            Q(student=student) if student else Q(student__isnull=True),
            Q(school_class=classe) if classe else Q(school_class__isnull=True),
        ).order_by('-created_at')
        
        return generic_performance

    def get_performance(self, student=None, bncc_pk=None, recalculate=False):
        from fiscallizeon.applications.models import ApplicationStudent
        
        start_process = time.time()
        
        applications_student = ApplicationStudent.objects.filter(
            Q(end_time__isnull=False),
            Q(student=student) if student else Q(),
        )
        
        if bncc_pk:
            
            bncc = get_bncc(bncc_pk)
            
            bncc_performance = bncc.last_performance(subject=self, student=student)
            
            if not recalculate and bncc_performance:
                return bncc_performance.first().performance
            
            weights = []
            performances = []
            
            for application_student in applications_student:
                
                total_weight = application_student.get_total_weight(subject=self, bncc_pk=bncc_pk)
                score = round_half_up(application_student.get_score(subject=self, bncc_pk=bncc_pk), 2)
                
                total_questions = total_weight['questions_count'] if total_weight['questions_count'] > 0 else 1

                performance = (score / round_half_up(total_weight['performance'], 2)) * 100 if total_weight['performance'] > 0 else 0
                
                weights.append(total_questions)
                performances.append(performance)
                
            process_time = time.time() - start_process
            
            if bncc_performance:
                bncc_performance.using('default').update(
                    student=student, 
                    subject=self, 
                    performance=np.average(performances, weights=weights), 
                    process_time=timedelta(seconds=process_time)
                )                
            else:
                bncc.performances.create(
                    student=student,  
                    subject=self,
                    performance=np.average(performances, weights=weights),
                    weight=1,
                    process_time=timedelta(seconds=process_time),
                )
                
            return np.average(performances, weights=weights)
        
        weights = []
        performances = []
        
        for application_student in applications_student:
            
            total_weight = application_student.get_total_weight(subject=self)
            score = round_half_up(application_student.get_score(subject=self), 2)
            
            performance = (score / round_half_up(total_weight, 2)) * 100 if total_weight > 0 else 0
            
            exam_questions = application_student.application.exam.examquestion_set.availables().filter(
                Q(question__subject=self) |
                Q(exam_teacher_subject__teacher_subject__subject=self)
            )
            
            weights.append(exam_questions.count())
            performances.append(performance)

        process_time = time.time() - start_process
        
        performance = np.average(performances, weights=weights) if sum(weights) > 0 else 0
        
        last_performance = self.last_performance(student=student)
        if last_performance:
            last_performance.using('default').update(
                student=student,
                performance=performance, 
                process_time=timedelta(seconds=process_time)
            )
        else:
            self.performances.create(
                student=student,
                performance=performance, 
                process_time=timedelta(seconds=process_time), 
                weight=1,
            )
        
        return performance

    def get_max_score(self, exam):
        max_score = 0
        if exam.is_abstract:
            max_score = exam.examquestion_set.availables().filter(question__subject=self).aggregate(max_score=models.Sum('weight')).get('max_score') or 0
        else:
            max_score = exam.examquestion_set.availables().filter(exam_teacher_subject__teacher_subject__subject=self).aggregate(max_score=models.Sum('weight')).get('max_score') or 0

        return max_score
    
    
class SubjectRelation(BaseModel):
    client = models.ForeignKey("clients.Client", verbose_name=("Cliente"), on_delete=models.CASCADE)
    name = models.CharField("Nome da relação", max_length=80)
    SUM, AVG = range(2)
    RELATION_CHOICES_TYPES = (
        (SUM, "Somar pesos das disciplinas"),
        (AVG, "Média dos pesos"),
    )
    relation_type = models.SmallIntegerField("Tipo de relação", choices=RELATION_CHOICES_TYPES, default=SUM)
    subjects = models.ManyToManyField(Subject, verbose_name=("Disciplinas relacionadas"))
    created_by = models.ForeignKey("accounts.User", related_name="relations", verbose_name=("Criado por"), on_delete=models.CASCADE)
    updated_by = models.ForeignKey("accounts.User", verbose_name=("Atualizado por"), on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Relação entre disciplinas'
        verbose_name_plural = 'Relações entre disciplinas'


class Theme(BaseModel):
    name = models.CharField("Nome do Tema", max_length=4096)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True)
    created_by = models.ForeignKey(User, verbose_name="Criado por", null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Tema"
        verbose_name_plural = "Temas"

    def __str__(self):
        return self.name

class MainTopic(BaseModel):
    name = models.CharField("Nome do Tópico Principal", max_length=4096)
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True)
    created_by = models.ForeignKey(User, verbose_name="Criado por", null=True, blank=True, on_delete=models.PROTECT)

    objects = MainTopicManager()

    class Meta:
        verbose_name = "Tópico Principal"
        verbose_name_plural = "Tópicos Principais"

    def __str__(self):
        return self.name

class Topic(BaseModel):
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, null=True, blank=True)
    main_topic = models.ForeignKey(MainTopic, on_delete=models.CASCADE, null=True, blank=True)
    grade = models.ForeignKey(Grade, verbose_name="Série", on_delete=models.CASCADE, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    name = models.CharField('Título', max_length=4096)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True)
    created_by = models.ForeignKey(User, verbose_name="Criado por", null=True, blank=True, on_delete=models.PROTECT)
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

    performances = GenericRelation('analytics.GenericPerformances', related_query_name="topic_performance")
    
    objects = TopicManager()

    class Meta:
        verbose_name = 'Assunto'
        verbose_name_plural = 'Assuntos'

    def __str__(self):
        return self.name
    
    def last_performance(self, exam=None, application_student=None, classe=None, student=None, subject=None):
        
        generic_performance = self.performances.using('default').filter(
            Q(exam=exam) if exam else Q(exam__isnull=True),
            Q(student=student) if student else Q(student__isnull=True),
            Q(subject=subject) if subject else Q(subject__isnull=True),
            Q(application_student=application_student) if application_student else Q(application_student__isnull=True),
            Q(school_class=classe) if classe else Q(school_class__isnull=True),
        ).order_by('-created_at')
        
        return generic_performance
    
    @classmethod
    def check_client(cls, client_pk):
        CACHE_KEY = f'TOPICS_CLIENT_{client_pk}'
        if not cache.get(CACHE_KEY): 
            cache.set(CACHE_KEY, cls.objects.filter(client=client_pk).exists(), 600)

        return cache.get(CACHE_KEY) 
    
    @hook("after_save")
    def update_erp(self, subject=None):
        from fiscallizeon.integrations import realms

        Integration = apps.get_model('integrations', 'Integration')
        SubjectCode = apps.get_model('integrations', 'SubjectCode')
        TopicCode = apps.get_model('integrations', 'TopicCode')

        if not self.client:
            return
        
        has_realms_integration = Integration.objects.filter(
            client=self.client,
            erp=Integration.REALMS
        ).exists()

        if not has_realms_integration:
            return

        subject_code = SubjectCode.objects.filter(
            client=self.client,
            subject=subject or self.subject,
        ).first()
        
        if not subject_code:
            message = f"{subject or self.subject} não encontrada em SubjectCode"
            print(message)
            capture_message(message)
            return
        
        try:
            df = pd.read_csv('assets/subjects-seduc-sp.csv')
            if settings.DEBUG:
                df = pd.read_csv('assets/subjects-seduc-sp.csv.dev')
            df['id'] = df['id'].astype(str)
            subject_realms = df[df['id'] == subject_code.code].head(1)
        except Exception as e:
            print(e)
            capture_message(f'Erro no cadastro de assunto no Realms: {e}')
            return

        if subject_realms.empty:
            message = f"{subject_code.code} não encontrado no CSV"
            print(message)
            capture_message(f'Erro no cadastro de assunto no Realms: {message}')
            return

        body = {
            'name': self.name,
            'parent_id': str(subject_realms.iloc[0]['id_pai_conteudo']),
            'external_id': str(self.pk),
            'task': {
                "enabled": False,
                "required": False,
                "selectable": False,
                "show_in_list": False,
                "show_in_navegation": False,
                "allow_multi_selection": False
            },
            'question': {
                "enabled": False,
                "required": False,
                "selectable": True, 
                "show_in_list": False,
                "show_in_navegation": False,
                "allow_multi_selection": False
            }
        }

        if integration_code := self.codes.first():
            realms.update_category(integration_code, body)
        else:
            response = realms.create_category(self.client, body)
            if response.get('errors', False):
                capture_message(f'Erro no cadastro de assunto no Realms: {response}')
                return

            TopicCode.objects.create(
                client=self.client,
                code=response.get('id', None),
                topic=self,
                created_by=self.created_by
            )

    @hook("before_delete")
    def delete_erp(self):
        from fiscallizeon.integrations import realms

        Integration = apps.get_model('integrations', 'Integration')

        if not self.client:
            return
        
        has_realms_integration = Integration.objects.filter(
            client=self.client,
            erp=Integration.REALMS
        ).exists()

        if not has_realms_integration:
            return
        
        if integration_code := self.codes.first():
            realms.delete_category(integration_code)

    def name_escaped(self):
        return self.name.replace("\\", "\\\\").replace('&quot;', '"').replace('"', '\\"')
