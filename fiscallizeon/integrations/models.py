from django.db import models
from django.apps import apps
from django.conf import settings

from fiscallizeon.accounts.models import User
from fiscallizeon.clients.models import Client
from fiscallizeon.core.models import BaseModel
from fiscallizeon.subjects.models import Subject, Topic
from django.core.exceptions import ValidationError

# Create your models here.
class Integration(BaseModel):
    client = models.OneToOneField(Client, on_delete=models.CASCADE)
    TOTVS, ACTIVESOFT, ISCHOLAR, ATHENAWEB, SOPHIA, REALMS = range(6)
    ERP_CHOICES = (
        (ACTIVESOFT, 'Activesoft'),
        # (TOTVS, 'Totvs'),
        (ISCHOLAR, 'Ischolar'),
        (ATHENAWEB, 'AthenaWeb'),
        (REALMS, 'Realms'),
        (SOPHIA, 'Sophia'),
    )
    erp = models.PositiveSmallIntegerField('ERP', choices=ERP_CHOICES, default=ACTIVESOFT)
    school_code = models.CharField("Código da escola", max_length=50, blank=True, null=True)
    username = models.CharField("Usuário de autenticação", max_length=100, blank=True, null=True)
    token = models.TextField('Token de acesso', blank=True, null=True)
    

    def __str__(self):
        return self.client.name + ' - ' + self.get_erp_display()
    
    class Meta:
        verbose_name = 'Integração'
        verbose_name_plural = 'Integrações'
    
    @property
    def base_url(self):
        if self.erp == self.ACTIVESOFT:
            return 'https://siga.activesoft.com.br'
        elif self.erp == self.ISCHOLAR:
            return 'https://api.ischolar.app'
        elif self.erp == self.ATHENAWEB:
            return 'https://api.athenaweb.com.br'
        elif self.erp == self.REALMS:
            return 'https://school-api.ip.tv/tms/v1' if settings.DEBUG else 'https://edusp-api.ip.tv/tms/v1'
        elif self.erp == self.SOPHIA:
            # A integração com o SOPHIA é via Multi Tenant
            return f'https://portal.sophia.com.br/SophiAWebApi/{self.school_code}' if self.school_code else 'https://portal.sophia.com.br/SophiAWebApi'
    
    def clean(self):
        if not self.token and self.erp not in [self.ACTIVESOFT, self.SOPHIA]:
            raise ValidationError({ 'token': 'Esse campo é obrigatório' })
    
    def headers(self, token=None):
        if not token:
            token = self.token
                
        if self.erp == self.ACTIVESOFT:
            return {
                'Authorization': f'Bearer {token}',
                'accept': 'application/json',
            }
        elif self.erp == self.ISCHOLAR:
            return {
                'X-Autorizacao': token,
                'X-Codigo-Escola': self.school_code,
            }
        elif self.erp == self.ATHENAWEB:
            return {
                'Authorization': f'Bearer {token}',
                'accept': 'application/json',
            }
        elif self.erp == self.SOPHIA:
            return {
                'token': self.token,
                'accept': 'application/json',
            }
        elif self.erp == self.REALMS:
            return {
                'x-api-key': self.token,
                'accept': 'application/json',
            }
    
    @property
    def urls(self):
        if self.erp == self.ACTIVESOFT:
            return {
                "unities_list": f'{self.base_url}/api/v0/lista_unidades/',
                "boletins": f'{self.base_url}/api/v0/detalhe_boletim/',
                "classes_list": f'{self.base_url}/api/v0/lista_turmas/',
                "intership_with_details": f'{self.base_url}/api/v0/enturmacao_com_detalhes/',
                "students_list": f'{self.base_url}/api/v0/lista_alunos/',
                # Envio de notas
                "send_notes": f'{self.base_url}/api/v0/correcao_prova/',
            }
        if self.erp == self.ISCHOLAR:
            return {
                "unities_list": f'{self.base_url}/unidades/listar_unidades',
                "classes_list": f'{self.base_url}/turma/lista',
                "students_list": f'{self.base_url}/aluno/lista_v2',
                "intership_with_details": f'{self.base_url}/matricula/listar',
                "send_notes": f'{self.base_url}/notas/lanca_nota',
                
                # Lançamento de notas
                "student_diary": f'{self.base_url}/diario/notas',
                "evaluation_system": f'{self.base_url}/turma/sistema_avaliativo',
                "classe_subjects": f'{self.base_url}/turma/disciplinas',
            }
        if self.erp == self.ATHENAWEB:
            return {
                "unities_list": f'{self.base_url}/api/v1/escola',
                "classes_list": f'{self.base_url}/api/v1/turmas',
                "students_list": f'{self.base_url}/api/v1/alunos',
                "intership_with_details": f'{self.base_url}/api/v1/matriculas',
                "periods_list": f'{self.base_url}/api/v1/periodos',
                "applications": f'{self.base_url}/api/v1/avaliacoes',
                
                # Lançamento de notas
                "send_notes": f'{self.base_url}/api/v1/notas',
                "application_subjects": f'{self.base_url}/api/v1/disciplinas',
            }
        if self.erp == self.SOPHIA:
            return {
                "authentication": f'{self.base_url}/api/v1/Autenticacao',
                "unities_list": f'{self.base_url}/api/v1/Unidades',
                "classes_list": f'{self.base_url}/api/v1/Turmas',
                "students_list": f'{self.base_url}/api/v1/Alunos?Inativos=false',
                "enrrolment": f'{self.base_url}/api/v1/alunos/idAluno/Matriculas',
                "periods_list": f'{self.base_url}/api/v1/periodos',
                "applications": f'{self.base_url}/api/v1/avaliacoes',
                
                # Lançamento de notas
                "avaliation_notes": f'{self.base_url}/api/v1/alunos/Matriculas/idMatricula/NotasAvaliacoesCompleto',
                "atas": f'{self.base_url}/api/v1/AtaNota',
                "send_notes": f'{self.base_url}/api/v1/AtaNota/idAta/NotaAlunos',
            }
    
    def get_current_token(self):
        if self.erp == Integration.ACTIVESOFT:
            if token := self.tokens.order_by('created_at').first():
                return token.token
        return self.token
    
class IntegrationToken(BaseModel):
    name = models.CharField('Identificador', max_length=70, default='Token padrão', blank=True)
    integration = models.ForeignKey('Integration', related_name='tokens', on_delete=models.CASCADE)
    expiration_date = models.DateField('Data em que expira', auto_now=False, auto_now_add=False, blank=True, null=True)
    token = models.TextField('Token de acesso')
    
    class Meta:
        ordering = ('created_at',)
        verbose_name = 'Tokens de integração'
        verbose_name_plural = 'Tokens de integraçãos'
    
    @property
    def fake(self):
        return f"{str(self.token[:4])}****"
    
    @property
    def can_delete(self):
        return not any([self.unities.exists(), self.school_classes.exists(), self.students.exists()])

class SuperProfIntegration(BaseModel):
    user = models.ForeignKey("accounts.User", verbose_name=("Usuário"), on_delete=models.CASCADE, blank=True)
    login = models.CharField("Usuário do super professor", max_length=255) # Email do super professor
    password = models.CharField("Senha do super professor", max_length=50) # Senha do super professor
    
    authorization_code = models.CharField("Ultimo código de autorização" ,max_length=100, null=True, blank=True)
    authorization_expires_at = models.DateTimeField("Data em que o a autorização expira", null=True, blank=True)
    
    access_token = models.TextField("Ultimo token de acesso", null=True, blank=True)
    access_token_expires_at = models.DateTimeField("Data em que o token expira", null=True, blank=True)
    
    sso_token = models.CharField("Ultimo SSO token", max_length=100, null=True, blank=True)
    sso_token_expires_at = models.DateTimeField("Data em que o SSO token expira", null=True, blank=True)


class SubjectCode(BaseModel):
    client = models.ForeignKey(Client, verbose_name="Cliente", on_delete=models.CASCADE)
    code = models.CharField('Código', max_length=50)
    subject = models.ForeignKey(Subject, verbose_name=("Disciplina"), related_name="codes", on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, verbose_name="Criado por", null=True, blank=True, on_delete=models.PROTECT)

    def __str__(self):
        return self.client.name + ' - ' + self.code + ' - ' + self.subject.name

    class Meta:
        verbose_name = 'Código de disciplina'
        verbose_name_plural = 'Códigos das disciplinas'


class TopicCode(BaseModel):
    client = models.ForeignKey(Client, verbose_name="Cliente", on_delete=models.CASCADE)
    code = models.CharField('Código', max_length=50)
    topic = models.ForeignKey(Topic, verbose_name=("Assunto"), related_name="codes", on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, verbose_name="Criado por", null=True, blank=True, on_delete=models.PROTECT)

    def __str__(self):
        return self.client.name + ' - ' + self.code + ' - ' + self.topic.name

    class Meta:
        verbose_name = 'Código de assunto'
        verbose_name_plural = 'Códigos das assuntos'


class AbilityCode(BaseModel):
    client = models.ForeignKey(Client, verbose_name="Cliente", on_delete=models.CASCADE)
    code = models.CharField('Código', max_length=50)
    ability = models.ForeignKey("bncc.Abiliity", verbose_name=("Habilidade"), related_name="codes", on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, verbose_name="Criado por", null=True, blank=True, on_delete=models.PROTECT)

    def __str__(self):
        return self.client.name + ' - ' + self.code + ' - ' + self.ability.text

    class Meta:
        verbose_name = 'Código de habilidade'
        verbose_name_plural = 'Códigos das habilidades'


class CompetenceCode(BaseModel):
    client = models.ForeignKey(Client, verbose_name="Cliente", on_delete=models.CASCADE)
    code = models.CharField('Código', max_length=50)
    competence = models.ForeignKey("bncc.Competence", verbose_name=("Competência"), related_name="codes", on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, verbose_name="Criado por", null=True, blank=True, on_delete=models.PROTECT)

    def __str__(self):
        return self.client.name + ' - ' + self.code + ' - ' + self.competence.text

    class Meta:
        verbose_name = 'Código de competência'
        verbose_name_plural = 'Códigos das competências'

class NotesMigrationProof(BaseModel):
    code = models.CharField("Código do comprovante de migração", max_length=8)
    created_by = models.ForeignKey(User, verbose_name="Criado por", on_delete=models.PROTECT)
    exam = models.ForeignKey("exams.Exam", verbose_name="Prova", on_delete=models.PROTECT, related_name="notes_migration_proofs")
    students = models.ManyToManyField("students.Student", verbose_name="Alunos")
    migration_json = models.JSONField("Dados aidiconais da migração") # notas migradas, relações entre disciplinas e possíveis erros na migração

    class Meta:
        verbose_name = 'Comprovante de migração de notas'
        verbose_name_plural = 'Comprovantes de migração de notas'
