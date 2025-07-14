import pandas as pd
from django_lifecycle import hook
from sentry_sdk import capture_message

from django.apps import apps
from django.conf import settings
from django.db import models
from django.core.cache import cache
from django.contrib.contenttypes.fields import GenericRelation
from django.db.models import Q

from fiscallizeon.core.models import BaseModel
from fiscallizeon.subjects.models import KnowledgeArea, Subject
from fiscallizeon.classes.models import Grade
from fiscallizeon.clients.models import Client
from fiscallizeon.accounts.models import User
from fiscallizeon.integrations import realms



class Abiliity(BaseModel):
    grades = models.ManyToManyField(Grade, verbose_name='Anos/Séries', related_name="abilities")
    code = models.CharField("Código da habilidade", max_length=150)
    text = models.TextField("Habilidade", max_length=4096)
    knowledge_area = models.ForeignKey(KnowledgeArea, on_delete=models.CASCADE, verbose_name='Área de conhecimento', null=True, blank=True)
    subject = models.ForeignKey(Subject, verbose_name="Componente", on_delete=models.CASCADE, null=True, blank=True)
    knowledge_object = models.ForeignKey("KnowledgeObject", verbose_name="Objeto de conhecimento", on_delete=models.CASCADE, null=True, blank=True)
    thematic_unit = models.ForeignKey("ThematicUnit", verbose_name="Unidade temática", on_delete=models.CASCADE, null=True, blank=True)
    language_practice = models.ForeignKey("LanguagePractice", verbose_name="Prática de linguagem", on_delete=models.CASCADE, null=True, blank=True)
    acting_field = models.ForeignKey("ActingField", verbose_name="Campo de atuação", on_delete=models.CASCADE, null=True, blank=True)
    axis = models.ForeignKey("Axis", verbose_name="Eixo", on_delete=models.CASCADE, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True)
    created_by = models.ForeignKey(User, verbose_name="Criado por", null=True, blank=True, on_delete=models.PROTECT)
    
    performances = GenericRelation('analytics.GenericPerformances', related_query_name="ability_performance")

    def __str__(self):
        return f'{self.text}'
    
    def last_performance(self, exam=None, application_student=None, classe=None, student=None, subject=None):
        generic_performance = self.performances.using('default').filter(
            Q(exam=exam) if exam else Q(exam__isnull=True),
            Q(subject=subject) if subject else Q(subject__isnull=True),
            Q(student=student) if student else Q(student__isnull=True),
            Q(application_student=application_student) if application_student else Q(application_student__isnull=True),
            Q(school_class=classe) if classe else Q(school_class__isnull=True),
        ).order_by('-created_at')
        
        return generic_performance

    class Meta:
        verbose_name = "Habilidade"
        verbose_name_plural = "Habilidades"
        ordering = ("-created_at", )

    def text_escaped(self):
        return self.text.replace("\\", "\\\\").replace('&quot;', '"').replace('"', '\\"')

    @classmethod
    def check_client(cls, client_pk):
        CACHE_KEY = f'BNCC_ABILITIES_{client_pk}'
        if not cache.get(CACHE_KEY): 
            cache.set(CACHE_KEY, cls.objects.filter(client=client_pk).exists(), 600)

        return cache.get(CACHE_KEY) 

    @hook("after_save")
    def update_erp(self, subject=False):
        Integration = apps.get_model('integrations', 'Integration')
        SubjectCode = apps.get_model('integrations', 'SubjectCode')
        AbilityCode = apps.get_model('integrations', 'AbilityCode')

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
            message = f"{subject.pk or self.subject} não encontrada em SubjectCode"
            print(message)
            capture_message(f'Erro no cadastro de habilidade no Realms: {message}')
            return
        
        try:
            df = pd.read_csv('assets/subjects-seduc-sp.csv')
            if settings.DEBUG:
                df = pd.read_csv('assets/subjects-seduc-sp.csv.dev')

            df['id'] = df['id'].astype(str)
            subject_realms = df[df['id'] == subject_code.code].head(1)
        except Exception as e:
            print(e)
            capture_message(f'Erro no cadastro de habilidade no Realms: {e}')

        if subject_realms.empty:
            message = f"{subject_code.code} não encontrado no CSV"
            print(message)
            capture_message(f'Erro no cadastro de habilidade no Realms: {message}')
            return

        body = {
            'name': self.text,
            'parent_id': str(subject_realms.iloc[0]['id_pai_habilidade']),
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
                capture_message(f'Erro no cadastro de habilidade no Realms: {response}')
                return

            AbilityCode.objects.create(
                client=self.client,
                code=response.get('id', None),
                ability=self,
                created_by=self.created_by
            )

    @hook("before_delete")
    def delete_erp(self):
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

class Competence(BaseModel):
    code = models.CharField("Código da competência", max_length=150, null=True, blank=True)
    text = models.TextField("Competência", help_text="Descreva a competência acima", max_length=4096)
    subject = models.ForeignKey(Subject, help_text="Será mostrado para esta disciplina e as disciplinas filhas", verbose_name="Componente", on_delete=models.CASCADE, null=True, blank=True)
    knowledge_area = models.ForeignKey(KnowledgeArea, on_delete=models.CASCADE, verbose_name='Área de conhecimento', null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True)
    created_by = models.ForeignKey(User, verbose_name="Criado por", null=True, blank=True, on_delete=models.PROTECT)
    
    performances = GenericRelation('analytics.GenericPerformances', related_query_name="competence_performance")


    def __str__(self):
        return f'{self.text}'
    
    def last_performance(self, exam=None, application_student=None, classe=None, student=None, subject=None):
        generic_performance = self.performances.using('default').filter(
            Q(exam=exam) if exam else Q(exam__isnull=True),
            Q(student=student) if student else Q(student__isnull=True),
            Q(subject=subject) if subject else Q(subject__isnull=True),
            Q(application_student=application_student) if application_student else Q(application_student__isnull=True),
            Q(school_class=classe) if classe else Q(school_class__isnull=True),
        ).order_by('-created_at')
        
        return generic_performance

    class Meta:
        verbose_name = "Competência"
        verbose_name_plural = "Competências"
        ordering = ("-created_at", )

    @classmethod
    def check_client(cls, client_pk):
        CACHE_KEY = f'BNCC_COMPETENCES_{client_pk}'
        if not cache.get(CACHE_KEY): 
            cache.set(CACHE_KEY, cls.objects.filter(client=client_pk).exists(), 600)
            
        return cache.get(CACHE_KEY)
    
    def text_escaped(self):
        return self.text.replace("\\", "\\\\").replace('&quot;', '"').replace('"', '\\"')

    @hook("after_save")
    def update_erp(self, subject=None):
        Integration = apps.get_model('integrations', 'Integration')
        SubjectCode = apps.get_model('integrations', 'SubjectCode')
        CompetenceCode = apps.get_model('integrations', 'CompetenceCode')

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
            capture_message(f'Erro no cadastro de competência no Realms: {message}')
            return
        
        try:
            df = pd.read_csv('assets/subjects-seduc-sp.csv')
            if settings.DEBUG:
                df = pd.read_csv('assets/subjects-seduc-sp.csv.dev')
            df['id'] = df['id'].astype(str)
            subject_realms = df[df['id'] == subject_code.code].head(1)
        except Exception as e:
            print(e)
            capture_message(f'Erro no cadastro de competência no Realms: {e}')

        if subject_realms.empty:
            message = f"{subject_code.code} não encontrado no CSV"
            print(message)
            capture_message(f'Erro no cadastro de competência no Realms: {message}')
            return

        body = {
            'name': self.text,
            'parent_id': str(subject_realms.iloc[0]['id_pai_descritor']),
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
                capture_message(f'Erro no cadastro de competência no Realms: {response}')
                return

            CompetenceCode.objects.create(
                client=self.client,
                code=response.get('id', None),
                competence=self,
                created_by=self.created_by
            )

    @hook("before_delete")
    def delete_erp(self):
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

class KnowledgeObject(BaseModel):
    text = models.CharField("Objecto de Conhecimento", max_length=1024)

    def __str__(self):
        return f'{self.text}'
    class Meta:
        verbose_name = "Objeto de Conhecimento"
        verbose_name_plural = "Objetos de Conhecimento"


class ThematicUnit(BaseModel):
    text = models.CharField("Unidade Temática", max_length=1024)

    def __str__(self):
        return f'{self.text}'
    class Meta:
        verbose_name = "Unidade Temática"
        verbose_name_plural = "Unidades Temáticas"
        
class LanguagePractice(BaseModel):
    text = models.CharField("Prática de Linguagem", max_length=1024)

    def __str__(self):
        return f'{self.text}'
    class Meta:
        verbose_name = "Prática de Linguagem"
        verbose_name_plural = "Práticas de Linguagem"

class ActingField(BaseModel):
    text = models.CharField("Campo de Atuação", max_length=1024)

    def __str__(self):
        return f'{self.text}'
    class Meta:
        verbose_name = "Campo de Atuação"
        verbose_name_plural = "Campos de Atuação"

class Axis(BaseModel):
    text = models.CharField("Eixo", max_length=1024)

    def __str__(self):
        return f'{self.text}'
    class Meta:
        verbose_name = "Eixo"
        verbose_name_plural = "Eixos"