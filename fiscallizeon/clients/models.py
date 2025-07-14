import re

from django.db import models

from fiscallizeon.core.models import BaseModel
from fiscallizeon.accounts.models import CustomGroup, User
from django.db.models import Q, Case, When, BooleanField, Count

from fiscallizeon.core.storage_backends import PublicMediaStorage

from django.contrib.contenttypes.fields import GenericRelation
from django_lifecycle import hook

# Create your models here.
class Client(BaseModel):
	TYPE_CLIENT_CHOICES = (
		(1, "Escola"),
		(2, "Outro"),
		(3, "Mentorizze"),
	)
	name = models.CharField("Nome do cliente", max_length=255)
	short_name = models.CharField("Nome simpleficado", max_length=255, blank=True, null=True)
	type_client = models.SmallIntegerField("Tipo de cliente", choices=TYPE_CLIENT_CHOICES)
	cnpj = models.CharField("CNPJ (somente números)", max_length=20, blank=True, null=True)
	logo = models.ImageField('Logo da escola', upload_to='clients/logos/', blank=True, null=True, storage=PublicMediaStorage())
	small_logo = models.ImageField('Logo pequena', upload_to='clients/logos/', blank=True, null=True, storage=PublicMediaStorage())
	social_name = models.CharField("Razão Social", max_length=255, blank=True, null=True)
	two_factor_enabled = models.BooleanField('Habilitação da autenticação de dois fatores', default=False)
	
	omr_categories = models.ManyToManyField('omr.OMRCategory', verbose_name='Formatos de gabarito habilitados', related_name='clients')

	can_audio_receive = models.BooleanField("Pode ouvir o audio do aluno", default=False)
	has_omr = models.BooleanField('Tem gabarito', default=False)
	has_dashboard = models.BooleanField('Tem acesso aos dashboards antigos', default=False)
	has_followup_dashboard = models.BooleanField('Tem acesso ao dashboard de acompanhamento', default=False)
	has_dashboards = models.BooleanField('Tem acesso aos dashboards novos', default=False)
	has_diagramation = models.BooleanField('Tem acesso ao sistema de solicitação de diagramação', default=False)
	has_distribution = models.BooleanField('Tem acesso ao sistema de ensalamento', default=False)
	has_public_questions = models.BooleanField('Tem acesso as questões públicas', default=False) 
	show_previews_template_student = models.BooleanField('Tem acesso ao gabarito prévio', default=False)
	has_template = models.BooleanField('Tem acesso a criação de gabarito avulso', default=False) 
	has_exam_elaboration = models.BooleanField('Tem acesso a elaboração de prova', default=False)
	has_study_material = models.BooleanField('Tem acesso a material de estudos', default=False)
	has_wrongs = models.BooleanField('Tem acesso ao sistema de erratas', default=False)
	has_automatic_creation = models.BooleanField('Tem acesso a criação automática de listas', default=False)
	has_discursive_answers = models.BooleanField('Tem acesso a correção de discursivas', default=False)
	has_discursive_auto_correction = models.BooleanField(
		'Tem acesso a correção automática de discursivas', 
		help_text='O sistema deve corrigir as questões discursivas com tecnologia OMR?',
		default=False,
	)
	has_hybrid_omr = models.BooleanField(
		'Tem acesso ao modelo de gabarito híbrido', 
		help_text="Modelo de gabarito onde, na parte inferior, existem campos para correção manual do professor",
		default=False
	)
	has_question_formatter = models.BooleanField('Tem acesso ao formatador de questões', default=False)
	has_partners = models.BooleanField('Tem acesso ao cadastro de parceiros.', default=False)
	has_tri = models.BooleanField('Tem acesso ao TRI', default=False)
	has_sisu_simulator = models.BooleanField('Os alunos tem acesso ao simulador SISU', default=False)
	has_late_questions = models.BooleanField('Tem acesso a adição de questões atrasadas', default=False)
	allow_login_only_google = models.BooleanField('Permitir login apenas com o google', default=False)
	can_request_ai_questions = models.BooleanField('Pode solicitar questão à IA', default=False)

	disable_stripped_answer_sheet = models.BooleanField(
		'Desativar tabela zebrada na folha de respostas', 
		help_text='Marque esta opção se o cliente tiver problemas com o contraste da impressora', 
		default=False
	)
	enable_omr_ocr = models.BooleanField('Ativar OCR na leitura de cartões resposta', default=False)
	allow_add_same_teacher_subject_in_exam = models.BooleanField('Permitir cadastrar várias soclitações para o mesmo professor/disciplina no mesmo caderno', default=False)
	use_only_own_subjects = models.BooleanField('Utilizar apenas disciplinas próprias cadastradas no sistema', default=False)
	teachers_can_elaborate_exam = models.BooleanField('Os professores podem elaborar listas de exercício', default=False)
	allow_student_notifications = models.BooleanField('Permitir notificações para alunos', default=False)
	can_disable_multiple_correct_options = models.BooleanField('Pode escolher bloquear a criação de questões objetivas com mais de uma alternativa correta', default=False)
	
	orientations_candidates_file = models.FileField('Arquivo de orientações para candidatos', upload_to='clients/orientations/', blank=True, null=True, storage=PublicMediaStorage())

	id_backend = models.UUIDField("Identificador no fiscallize presenial", max_length=255, blank=True, null=True)

	has_integration = models.BooleanField('Tem acesso a integrações', default=False)
	
	has_superpro_integration = models.BooleanField('Tem acesso a integrações com super professor', default=False)

	has_ia_creation = models.BooleanField('Pode criar questão com IA', default=False)
	has_new_teacher_experience = models.BooleanField('Tem acesso a nova experiência de professor', default=True)
	
	has_omrnps = models.BooleanField('Tem acesso a nps de avaliações', default=False)
	
	has_sum_question = models.BooleanField('Tem acesso a questões de somatória', default=False)
	has_cloze_question = models.BooleanField('Tem acesso a questões de preencher lacunas', default=False)

	can_access_app = models.BooleanField('Tem acesso ao APP', default=False)

	orientations_candidates_file = models.FileField('Arquivo de orientações para candidatos', upload_to='clients/orientations/', blank=True, null=True, storage=PublicMediaStorage())
	
	use_only_own_topics = models.BooleanField('Utiliza apenas assuntos próprios cadastradas no sistema', default=True)

	ACTIVED, DEACTIVED, PAUSED, IN_POC = range(1, 5)
	STATUS_CHOICES = (
		(ACTIVED, "Ativado"),
		(DEACTIVED, "Desativado"),
		(PAUSED, "Pausado"),
		(IN_POC, "Em POC"),
		)
	status = models.SmallIntegerField("Situação", choices=STATUS_CHOICES, default=ACTIVED)

	
	CORRECTION, MANAGEMENT, STREAMING, PREP_SCHOOL, SEPARATE_PLAN = range(1, 6)
	PLAN_CHOICES = (
		(CORRECTION, "Correção"),
		(MANAGEMENT, "Gestão"),
		(STREAMING, "Streaming"),
		(PREP_SCHOOL, "Cursinho"),
		(SEPARATE_PLAN, "Plano avulso"),
	)
	plan = models.SmallIntegerField("Plano", choices=PLAN_CHOICES, blank=True, null=True)

	monthly_ticket = models.DecimalField("Ticket mensal", max_digits=7, decimal_places=2, blank=True, null=True)

	code = models.CharField("Código do cliente", unique=True, help_text="Código que será inserido no início do usuário do aluno no momento do cadastro", max_length=255, blank=True, null=True)

	id_erp = models.CharField("ID ERP", max_length=255, null=True, blank=True)
	show_id_erp_in_exam = models.BooleanField(
		'mostrar código de exportação no caderno?', default=False,
	)
	allow_online_abstract_application = models.BooleanField(
		'permitir aplicação online de gabarito avulso?', default=False,
	)
	last_update_followup_dashboard = models.DateTimeField("Última atualização do dashboard followup", blank=True, null=True)

	max_students_quantity = models.SmallIntegerField("Quantidade máxima de alunos", blank=True, null=True)
	allow_add_exception_deadline_correction_response = models.BooleanField(
		'permitir adicionar exceção da data limite para professores corrigirem respostas?', default=False,
	)
	
	BAG_DEFAULT, BAG_SEPARATED_FILES = 'default', 'separated'
	OMR_PRINT_SEPARATION_CHOICES = (
		(BAG_DEFAULT, "Padrão (Arquivos juntos)"),
		(BAG_SEPARATED_FILES, "Arquivos separados"),
	)

	omr_print_file_separation = models.CharField("Separação de arquivos na geração de malote", choices=OMR_PRINT_SEPARATION_CHOICES, default=BAG_DEFAULT, max_length=12, blank=True)
	send_email_to_student_after_create = models.BooleanField(
		'enviar e-mail para aluno após cadastro?', default=False
	)
	can_select_header_in_create_or_update_exam = models.BooleanField(
		'Pode selecionar cabeçalho na criação/atualização de caderno', default=False
	)
	has_filtered_layout_for_today_student_applications = models.BooleanField(
		'Possui layout com filtros e divisão para aplicações do dia no painel de aluno', default=False
	)
	enabled_new_answer_sheet_experience = models.BooleanField('habilitado nova experiência de gabarito?', default=True)

	session_timeout_minutes = models.PositiveIntegerField(
		'Tempo em minutos para expiração de sessão dos usuários',
		help_text='Após esse tempo de inatividade o usuário deverá fazer login novamente. O valor 0 (zero) impede que a sessão expire.',
		default=0,
	)
	already_onboarded_coordinators = models.BooleanField('coordenadores já integrados?', default=False)
	already_onboarded_teachers = models.BooleanField('professores já integrados?', default=False)
	already_onboarded_students = models.BooleanField('alunos já integrados?', default=False)
 
	has_review_system = models.BooleanField('Tem acesso ao sistema de revisão', help_text='Essa opção ta relacionada ao campo review_deadline de exam e o card de revisão que fica no novo dash de acompanhamento', default=False, blank=True)
	has_customize_application = models.BooleanField('tem customização de tipo de aplicação', help_text='Essa opção adiciona um novo campo no cadastro de uma aplicação que permite criar novas nomenclaturas para aplicações', default=False, blank=True)
	has_essay_system = models.BooleanField('Tem acesso ao sistema de correção de redação', default=False, blank=True)
	has_discursive_ai_correction = models.BooleanField('Possui correção automática de questões discursivas', default=False, blank=True)
	enabled_new_answer_correction = models.BooleanField('habilitado novo layout de correção?', default=True)

	last_generation_followup_dashboard = models.DateTimeField('Última geração de dashboard de acompanhamento', blank=True, null=True)
	last_generation_dashboard = models.DateTimeField('Última geração dos novos dashboards', blank=True, null=True)

	class Meta:
		verbose_name = "Cliente"
		verbose_name_plural = "Clientes"

	def __str__(self):
		return self.name
	
	@property
	def teachers_coordinations_can_edit_questions(self):
		if client_questions_configuration := ClientQuestionsConfiguration.objects.filter(client=self).first():
			return client_questions_configuration.teachers_coordinations_can_edit_questions
		return False

	@property
	def already_onboarded_users(self):
		return self.already_onboarded_coordinators and self.already_onboarded_teachers and self.already_onboarded_students

	@property
	def already_onboarded_segments(self):
		return True

	@property
	def already_onboarded_permissions(self):
		return True

	@property
	def already_full_onboarded(self):
		return self.already_onboarded_users and self.already_onboarded_segments and self.already_onboarded_permissions
	
	@property
	def has_metabase_dashboard(self):
		return self.metabasedashboard_set.exists()

	def get_last_application_date(self):
		from fiscallizeon.applications.models import Application
		if last_application :=  Application.objects.filter(exam__coordinations__unity__client=self).last():
			return last_application.date
	get_last_application_date.__name__ = 'data da última aplicação'

	def get_exam_print_config(self):
		from fiscallizeon.exams.models import ExamHeader

		# DEFAULT CONFIGURATION
		exam_print_config_default = ExamPrintConfig.objects.filter(
			client=self, is_default=True,
		).last()
		if exam_print_config_default:
			return exam_print_config_default

		# LAST CONFIGURATION CREATED
		exam_print_config_last = ExamPrintConfig.objects.filter(client=self).last()
		if exam_print_config_last:
			return exam_print_config_last

		# CREATE A NEW CONFIGURATION
		exam_header = ExamHeader.objects.filter(
			user__coordination_member__coordination__unity__client=self,
			main_header=True,
		).distinct().first()

		exam_print_config_new = ExamPrintConfig.objects.create(
			header=exam_header, client=self, is_default=False
		)
		return exam_print_config_new
	
	@hook("after_update", has_changed=True, when="status", is_now=DEACTIVED)
	def deactivate_client_users(self):
		from django.apps import apps
		User = apps.get_model("accounts", "User")

		User.objects.filter(
			Q(
				is_active=True
			),
			Q(
				Q(student__client=self)|
				Q(inspector__coordinations__unity__client=self)|
				Q(coordination_member__coordination__unity__client=self)
			)
		).distinct().update(is_active=False, temporarily_inactive=True)

	@hook("after_update", has_changed=True, when="status", is_now=ACTIVED)
	def activate_client_users(self):
		from django.apps import apps
		User = apps.get_model("accounts", "User")

		User.objects.filter(
			Q(
				is_active=False,
				temporarily_inactive=True
			),
			Q(
				Q(student__client=self)|
				Q(inspector__coordinations__unity__client=self)|
				Q(coordination_member__coordination__unity__client=self)
			)
		).distinct().update(is_active=True, temporarily_inactive=False)
	
	def run_recalculate_followup_task(self):
		from fiscallizeon.analytics.tasks import generate_data_followup_dashboard_task
		task = generate_data_followup_dashboard_task
		result = task.apply_async(task_id=f'RECALCULATE_FOLLOWUP_DASHBOARD_{str(self.pk)}', kwargs={
			"client_pk": self.pk,
		}).forget()

	def get_groups(self, with_annotations=True):
		
		custom_groups = CustomGroup.objects.filter(
			Q(client__isnull=True) |
			Q(client=self)
		)
		
		if with_annotations:
			return custom_groups.annotate(
				can_update=Case(
					When(Q(client__isnull=False), then=True),
					default=False,
					output_field=BooleanField()
				),
			)
		
		return custom_groups
		
	def has_default_groups(self, segment):
		return self.get_groups().filter(client__isnull=False, segment=segment, default=True).exists()

	def get_unities(self):
		return self.unities.all().distinct()

	def get_coordinations(self):
		return SchoolCoordination.objects.filter(unity__client=self).distinct()

	def get_teachers(self):
		return User.objects.filter(
			coordination_member__coordination__unity__client=self
		).distinct()

	def get_students(self):
		return User.objects.filter(
			student__client=self
		).distinct()

class Unity(BaseModel):
	client = models.ForeignKey(Client, verbose_name="Escola", on_delete=models.CASCADE, related_name="unities")
	name = models.CharField("Nome da Unidade", max_length=255)
	timezone = models.CharField("Qual timezone?", default="America/Recife", max_length=255)
	
	PARENT, SUBSIDIARY, OTHER = range(3)
	UNITY_TYPE_CHOICES = (
		(PARENT, "Matriz"),
		(SUBSIDIARY, "Filial"),
		(OTHER, "Outro")
	)
	unity_type = models.SmallIntegerField(choices=UNITY_TYPE_CHOICES, default=PARENT)
	
	id_erp = models.CharField("ID ERP", max_length=255, blank=True, null=True)
	
	performances = GenericRelation('analytics.GenericPerformances', related_query_name="unity_performance")
 
	integration_token = models.ForeignKey('integrations.IntegrationToken', verbose_name="Token utilizado para integração", on_delete=models.CASCADE, related_name="unities", blank=True, null=True)

	def __str__(self):
		return f'{self.name} - {self.client.name}'

	def last_performance(self, exam):
		return self.performances.using('default').filter(exam=exam).order_by('-created_at')

	class Meta:
		verbose_name = "Unidade"
		verbose_name_plural = "Unidades"
  
class SchoolCoordination(BaseModel):
	# comentar essa linha depois do migrate
	# client = models.ForeignKey(Client, verbose_name="Escola", on_delete=models.CASCADE, related_name="coordinations")
	unity = models.ForeignKey(Unity, verbose_name="Unidade Escolar", on_delete=models.CASCADE, null=True, blank=True, related_name="coordinations")
	name = models.CharField("Nome da coordenação", max_length=255)
	responsible_name = models.CharField("Nome do responsável", max_length=255)
	responsible_email = models.EmailField("Email do responsável", max_length=255)
	responsible_phone = models.CharField("Telefone do responsável", max_length=15)
	
	high_school = models.BooleanField("Responsável pelo ensino médio?", default=True)
	elementary_school = models.BooleanField("Responsável pelo ensino fundamental 1?", default=True)
	elementary_school2 = models.BooleanField("Responsável pelo ensino fundamental 2?", default=False)

	can_see_all = models.BooleanField("Pode ver tudo?", default=False)
	can_see_finances = models.BooleanField("Pode ver o financeiro?", default=False)
	
	def __str__(self):
		return f'{self.unity} - {self.name}'

	class Meta:
		verbose_name = "Coordenação"
		verbose_name_plural = "Coordenações"
		ordering = ['created_at']


class CoordinationMember(BaseModel):
	coordination = models.ForeignKey(SchoolCoordination, verbose_name="Membro da coordenação", on_delete=models.PROTECT, related_name="members")
	user = models.ForeignKey(User, verbose_name="Usuário do membro da coordenação", on_delete=models.PROTECT, related_name="coordination_member")
	is_coordinator = models.BooleanField("É coordenador", default=False)
	is_reviewer = models.BooleanField("É revisor", default=False)
	is_pedagogic_reviewer = models.BooleanField("É revisor pedagógico", default=False)


	def __str__(self):
		return f'{self.coordination.name} - {self.user.name}'

	class Meta:
		verbose_name = "Membro da coordenação"
		verbose_name_plural = "Membros da coordenação"
		ordering = ['created_at']
		unique_together = ('coordination', 'user', )
		permissions = (
	  		('can_export_coodinator', 'Pode exportar coordenadores'),
		)

class ClientTeacherObligationConfiguration(BaseModel):
	client = models.ForeignKey(Client, verbose_name="Cliente", on_delete=models.PROTECT, related_name="teacher_configuration")
	template = models.BooleanField("Gabarito", help_text="Ao marcar esta opção, o professor será obrigado a marcar pelo menos um gabarito", default=False)
	topics = models.BooleanField("Assuntos abordados", help_text="Ao marcar esta opção, o professor será obrigado escolher pelo menos um assunto abordado", default=False)
	abilities = models.BooleanField("Habilidades", help_text="Ao marcar esta opção, o professor será obrigado a marcar pelo menos uma habilidade", default=False)
	competences = models.BooleanField("Competências", help_text="Ao marcar esta opção, o professor será obrigado a marcar pelo menos uma competência", default=False)
	difficult = models.BooleanField("Dificuldade", help_text="Ao marcar esta opção, o professor será obrigado a escolher a dificuldade das questões", default=False)
	pedagogical_data = models.BooleanField("Dados pedagógicos", help_text="Ao marcar esta opção, o professor será obrigado a selecionar pelo menos um dos dados pedagógicos.", default=False)
	commented_response = models.BooleanField("Resposta comentada", help_text="Ao marcar esta opção, o professor será obrigado a adicionar a resposta comentada da questão.", default=False)
	apply_on_homework = models.BooleanField("Aplicar para lista de exercícios", help_text="Ao marcar esta opção, as configurações serão aplicas nas listas de exercícios..", default=False) 
	HIGHT_SCHOOL, ELEMENTARY_SCHOOL, ELEMENTARY_SCHOOL_2 = range(3)
	LEVEL_CHOICES = (
		(ELEMENTARY_SCHOOL, "Anos iniciais"),
		(ELEMENTARY_SCHOOL_2, "Anos finais"),
		(HIGHT_SCHOOL, "Ensino Médio"),
	)
	level = models.PositiveIntegerField("Sigmento", choices=LEVEL_CHOICES, default=ELEMENTARY_SCHOOL)
	
	def __str__(self):
		return f'{self.client.name}'

	class Meta:
		verbose_name = "Configuração de obrigatóriedade"
		verbose_name_plural = "Configurações de obrigatóriedade"
		ordering = ['created_at']


class ConfigNotification(BaseModel):
	DAYS_BEFORE_OPT1, DAYS_BEFORE_OPT2, DAYS_BEFORE_OPT3, DAYS_BEFORE_OPT4, DAYS_BEFORE_OPT5 = range(5)

	FIRST_DATE_CHOICES = (
		(DAYS_BEFORE_OPT1, "Um dia antes de expirar"),
		(DAYS_BEFORE_OPT2, "Dois dias antes expirar"),
		(DAYS_BEFORE_OPT3, "Três dias antes expirar"),
		(DAYS_BEFORE_OPT4, "Quatro dias antes expirar"),
		(DAYS_BEFORE_OPT5, "Cinco dias antes expirar"),
	)
	SECOND_DATE_CHOICES = (
		(DAYS_BEFORE_OPT1, "Um dia antes de expirar"),
		(DAYS_BEFORE_OPT2, "Dois dias antes expirar"),
		(DAYS_BEFORE_OPT3, "Três dias antes expirar"),
		(DAYS_BEFORE_OPT4, "Quatro dias antes expirar"),
	)

	AFTER_EXPIRATION_DATE_CHOICES = (
		(DAYS_BEFORE_OPT1, "Um dia após de expirar"),
		(DAYS_BEFORE_OPT2, "Dois dias após expirar"),
		(DAYS_BEFORE_OPT3, "Três dias após expirar"),
		(DAYS_BEFORE_OPT4, "Quatro dias após expirar"),
		(DAYS_BEFORE_OPT5, "Cinco dias após expirar"),
	)

	CANDENCY_CHOICES = (
		(0,"Diariamente"),
		(1,"1 dia antes"),
		(2,"2 dias antes"),
		(3,"3 dias antes"),
	)

	client = models.OneToOneField(Client, verbose_name="Cliente", on_delete=models.PROTECT)

	send_notification = models.BooleanField("Notificações de Elaboração de Itens", help_text="Ao marcar esta opção, os professores serão notificados alguns dias antes da data de entrega dos cadernos.", default=False)
	first_notification = models.SmallIntegerField("Primeira notificação", choices=FIRST_DATE_CHOICES, default=DAYS_BEFORE_OPT1, help_text="Quantos dias antes da data de entrega a primeira notificação será enviada.")
	second_notification = models.SmallIntegerField("Segunda notificação", choices=SECOND_DATE_CHOICES, help_text="Quantos dias antes da data de entrega a segunda notificação será enviada.", blank=True, null=True)
	after_expiration = models.SmallIntegerField("Notificação pós-expiração", choices=AFTER_EXPIRATION_DATE_CHOICES, default=DAYS_BEFORE_OPT1, help_text="Este campo define a quantidade de dias após a expiração da data de entrega dos cadernos para notificar os coordenadores.")
	
	response_correction_notification = models.BooleanField("Notificar correção de respostas", help_text="Ao marcar esta opção, os professores serão notificados sobre as suas correções de respostas pendentes.", default=False)
	cadence_send_email = models.SmallIntegerField("Cadência de envio de e-mail", choices=CANDENCY_CHOICES, default=0, help_text="Define a cadência para o envio de e-mails de cobrança aos professores a partir da data de expiração.")
	
	coordination_send_notification = models.BooleanField("Notificar Coordenadores", help_text="Ao marcar esta opção, os coordenadores serão notificados alguns dias antes da data de entrega dos cadernos.", default=False)
	coordination_first_notification = models.SmallIntegerField("Primeira notificação", choices=FIRST_DATE_CHOICES, default=DAYS_BEFORE_OPT1, help_text="Quantos dias antes da data de entrega a primeira notificação será enviada.")
	coordination_second_notification = models.SmallIntegerField("Segunda notificação", choices=SECOND_DATE_CHOICES, help_text="Quantos dias antes da data de entrega a segunda notificação será enviada.", blank=True, null=True)
	coordination_after_expiration = models.SmallIntegerField("Notificação pós-expiração para os coordenadores", choices=AFTER_EXPIRATION_DATE_CHOICES, default=DAYS_BEFORE_OPT1, help_text="Este campo define a quantidade de dias após a expiração da data de entrega dos cadernos para notificar os coordenadores.")
	
	def __str__(self):
		return f'{self.client.name}'

	def get_absolute_url(self):
		from django.urls import reverse
		return reverse('clients:config_notifications_update', kwargs={'pk': self.pk})

	class Meta:
		verbose_name = "Configuração de notificação"
		verbose_name_plural = "Configurações de notificação"
		ordering = ['created_at']

class ClientQuestionsConfiguration(BaseModel):
	client = models.OneToOneField(Client, verbose_name="Cliente", on_delete=models.PROTECT, related_name="questions_configuration")
	block_edit_question_aproveds = models.BooleanField("Bloquear edição após aprovação", help_text="Ao marcar esta opção, os professores não poderão alterar a questão após ela ser aprovada para uso.", default=False)
	can_edit_and_change_position = models.BooleanField("Permitir edição e ordenação por coordenador e coordenador de área", help_text="Ao marcar esta opção, os coordenadores ou coordenadores de disciplina poderão alterar a ordem e editar as questões enquanto às analisa", default=False)
	can_swap_questions_groups = models.BooleanField("Permitir troca de questões entre solicitações", help_text="Ao marcar esta opção, os coordenadores ou coordenadores de disciplina poderão trocar questões entre solicitações de questões para fins de diagramação.", default=False)
	can_add_support_content_discursive_questions = models.BooleanField("Permitir adicionar conteúdo de apoio para resposta do aluno em questões discursivas", help_text="Ao marcar esta opção, os professores poderão adicionar um conteudo extra no gabarito das questões discursivas.", default=False)
	can_change_subject_with_existing_questions = models.BooleanField("Permitir trocar a disciplina da solicitação quando já existir questões.", help_text="Ao marcar esta opção, os coordenadores poderão alterar a disciplina da solicitação de questões, mesmo se já houver questões existentes.", default=False)
	can_not_add_multiple_correct_options_question = models.BooleanField(default=False, help_text='Ao marcar esta opção, os professores não poderão criar questões objetivas com mais de uma alternativa correta.', verbose_name='Não permitir duas alternativas corretas para questões objetivas')
	can_add_revision_after_closing_exam = models.BooleanField(default=False, help_text='Ao marcar esta opção, o elaborador  poderá revisar o PDF após o seu fechamento do caderno.', verbose_name='Permitir revisão do elaborador após fechamento do caderno.')
	teachers_coordinations_can_edit_questions = models.BooleanField(default=False, help_text='Ao marcar esta opção, os professores coordenadores poderão editar questões de outros professores.', verbose_name='Professores coordenadores podem editar questões de outros professores.')
	can_change_grade_with_existing_questions = models.BooleanField('Permitir trocar a série da solicitação quando já existir questões.', help_text='Ao marcar esta opção, os coordenadores poderão alterar a série da solicitação de questões, mesmo se já houver questões existentes.', default=False)

	def __str__(self):
		return f'{self.client.name}'

	class Meta:
		verbose_name = "Configuração de questões"
		verbose_name_plural = "Configurações de questões"
		ordering = ['created_at']

class ClientCustomFilter(BaseModel):
	user = models.ForeignKey('accounts.User', verbose_name="Usuário", on_delete=models.PROTECT, related_name="custom_filters", blank=True)
	name = models.CharField(max_length=200)
	active = models.BooleanField("Filtro ativo", default=True)
	url = models.CharField(max_length=50)
	params = models.TextField()

	def __str__(self):
		return f'{self.name} {self.url}'

	class Meta:
		verbose_name = "Filtro personalizados"
		verbose_name_plural = "Filtros personalizados"
		ordering = ['created_at']

	@property
	def urls(self):
		from django.urls import reverse
		return {
			"api_detail": reverse("api:clients:custom-filters-detail", kwargs={"pk": self.pk})
		}
	


class ExamPrintConfig(BaseModel):
	ONLY_STUDENT_NAME, HEADER_FULL = range(2)

	HEADER_FORMATS = (
		(HEADER_FULL, 'Completo'),
		(ONLY_STUDENT_NAME, 'Apenas o nome do aluno'),
	)

	ONE_COLUMN, TWO_COLUMNS = range(2)

	COLUMN_TYPES = (
		(ONE_COLUMN, 'Uma coluna'),
		(TWO_COLUMNS, 'Duas colunas'),
	)

	SINGLE, PER_SUBJECT, PER_TYPE_QUESTION = range(3)

	KINDS = (
		(SINGLE, 'Único'),
		(PER_SUBJECT, 'Por disciplina'),
		(PER_TYPE_QUESTION, 'Por tipo de questão'),
	)

	PRINT_SPACES, NOT_PRINT_SPACE = range(2)

	TEXT_QUESTION_FORMATS = (
		(PRINT_SPACES, 'Imprimir espaços'),
		(NOT_PRINT_SPACE, 'Não imprimir'),
	)
	
	ACCORDING_TO_QUESTION, BLANK_SPACE, LINES_SPACE = range(3)
 
	DISCURSIVE_QUESTION_SPACE_TYPES = (
		(ACCORDING_TO_QUESTION, 'De acordo com a questão'),
		(BLANK_SPACE, 'Espaço em branco'),
		(LINES_SPACE, 'Linhas'),
	)

	HEIGHT_NORMAL, HEIGHT_MEDIUM, HEIGHT_LARGE, HEIGHT_EXTRA_LARGE = range(4)

	LINE_HEIGHTS = (
		(HEIGHT_NORMAL, 'Normal'),
		(HEIGHT_MEDIUM, 'Médio'),
		(HEIGHT_LARGE, 'Grande'),
		(HEIGHT_EXTRA_LARGE, 'Extra grande'),
	)

	SIZE_12, SIZE_14, SIZE_18, SIZE_22, SIZE_32, SIZE_8, SIZE_10, SIZE_11 = range(8)
	
	# Tamanhos de fonte alterados para atender aos padrões solicitados pelos clientes
	FONT_SIZES = (
		(SIZE_12, '12pt'),
		(SIZE_14, '14pt'),
		(SIZE_18, '18pt'),
		(SIZE_22, '22pt'),
		(SIZE_32, '32pt'),
		(SIZE_8, '8pt'),
		(SIZE_10, '10pt'),
		(SIZE_11, '11pt'),
	)
	
	PLEX_SANS, VERDANA, TIMES, ARIAL, NUNITO = range(5)

	FONT_FAMILIES = (
		(PLEX_SANS, 'Plex Sans'),
		(VERDANA, 'Verdana'),
		(TIMES, 'Times'),
		(ARIAL, 'Arial'),
		(NUNITO, 'Nunito Sans'),
	)

	PORTUGUESE, ENGLISH, SPANISH = range(3)
	LANGUAGES = (
		(PORTUGUESE, 'Português'),
		(ENGLISH, 'Inglês'),
		(SPANISH, 'Espanhol'),
	)

	name = models.CharField('nome', max_length=255, default='Configuração base')
	header = models.ForeignKey(
		'exams.ExamHeader',
		verbose_name='cabeçalho',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
	)
	background_image = models.ForeignKey(
		'exams.ExamBackgroundImage',
		verbose_name='Imagem de fundo',
		on_delete=models.PROTECT,
		null=True,
		blank=True,
	)
	custom_pages = models.ManyToManyField(
		'exams.ClientCustomPage',
		verbose_name='Página customizadas',
		blank=True,
	)
	header_format = models.PositiveSmallIntegerField(
		'formato do cabeçalho', choices=HEADER_FORMATS, default=HEADER_FULL,
	)
	column_type = models.PositiveSmallIntegerField(
		'formato', choices=COLUMN_TYPES, default=ONE_COLUMN,
	)
	kind = models.PositiveSmallIntegerField(
		'tipo', choices=KINDS, default=SINGLE,
	)
	text_question_format = models.PositiveSmallIntegerField(
		'estilo das questões discursivas',
		choices=TEXT_QUESTION_FORMATS,
		default=PRINT_SPACES,
	)
	line_height = models.PositiveSmallIntegerField(
		'espaçamento entre as linhas', choices=LINE_HEIGHTS, default=HEIGHT_NORMAL,
	)
	font_size = models.PositiveSmallIntegerField(
		'tamanho da fonte', choices=FONT_SIZES, default=SIZE_12,
	)
	font_family = models.PositiveSmallIntegerField(
		'tipo da fonte', choices=FONT_FAMILIES, default=PLEX_SANS,
	)
	print_subjects_name = models.BooleanField(
		'imprimir nome das disciplinas?',
		default=False,
		help_text='Designa se o caderno deve imprimir o nome das disciplinas.',
	)
	print_with_correct_answers = models.BooleanField(
		'imprimir caderno gabaritado?',
		default=False,
		help_text='Designa se o caderno deve ser impressa junto com o gabarito inserido.',
	)

	margin_top = models.FloatField(
		'Margem Superior (cm)',
		default=0.6,
		help_text='Margem superior em centímetros.'
	)

	margin_bottom = models.FloatField(
		'Margem Inferior (cm)',
		default=0.6,
		help_text='Margem inferior em centímetros.'
	)
	
	margin_right = models.FloatField(
		'Margem Direita (cm)',
		default=0.6,
		help_text='Margem direita em centímetros.'
	)
	
	margin_left = models.FloatField(
		'Margem Esquerda (cm)',
		default=0.6,
		help_text='Margem esquerda em centímetros.'
	)

	# NEW OPTIONS
	hide_alternatives_indicator = models.BooleanField(
		'ocultar indicador das alternativas?',
		default=False,
		help_text='Designa se o caderno deve ocultar o indicador das alternativas.',
	)
	hide_knowledge_areas_name = models.BooleanField(
		'ocultar nome das áreas de conhecimento?',
		default=False,
		help_text='Designa se o caderno deve ocultar o nome das áreas de conhecimento.',
	)
	print_black_and_white_images = models.BooleanField(
		'imprimir imagens em preto e branco?',
		default=False,
		help_text='Designa se o caderno deve imprimir as imagens em preto e branco.',
	)
	hide_questions_referencies = models.BooleanField(
		'ocultar texto de referência das alternativas',
		default=False,
		help_text='Designa se a caderno ocultar os textos referências das questões.',
	)
	hyphenate = models.BooleanField(
		'hifenizar?',
		default=False,
		help_text='Designa se deve hifenizar os textos do caderno.',
	)
	discursive_line_height = models.FloatField(
		"espaçamento entre linhas de respostas",
		default=1,
		help_text='Designa ao espaçamento entre linhas das respostas discursivas.'
	)

	show_question_score = models.BooleanField(
		'mostrar a pontuação das questões?',
		default=False,
		help_text='Designa se o caderno deve mostrar a pontuação das questões.',
	)
	show_question_board = models.BooleanField(
		'mostrar a banca das questões?',
		default=False,
		help_text='Designa se o caderno deve mostrar a banca das questões.',
	)

	is_default = models.BooleanField(
		'é a configuração de impressão padrão?',
		default=False,
		help_text='Designa se a configuração deve ser usada como padrão nos cadernos.',
	)
	
	uppercase_letters = models.BooleanField(
		'imprimir tudo maiúsculo?',
		default=False,
		help_text='Designa se o caderno deve ter todas as letras maiúscula.',
	)

	show_footer = models.BooleanField(
		'Imprimir nome do caderno no rodapé.',
		default=False,
		help_text='Designa se o caderno deve ter o título no rodapé de todas as páginas.',
	)

	add_page_number = models.BooleanField(
		'Adicionar numeração em todas as páginas.',
		default=False,
		help_text='Designa se o número da página deve ser adicionado ao rodapé do caderno.',
	)
 
	economy_mode = models.BooleanField(
		'Modo econômico.',
		default=False,
		help_text='Com ele, os enunciados são quebrados automaticamente e a prova é exibida em duas colunas.',
	)
 
	force_choices_with_statement = models.BooleanField(
		'Forçar alternativas junto ao enunciado.',
		default=False,
		help_text='As alternativas de cada questão serão exibidas imediatamente junto ao enunciado. (Quebra de enunciado será desconsiderado.)',
	)
 
	hide_numbering = models.BooleanField(
		'Esconder numerações das questões',
		default=False,
		help_text='Remove a numeração das questões, deixando o enunciado e as alternativas sem identificação numérica.',
	)
 
	break_enunciation = models.BooleanField(
		'Quebra de enunciado',
  		default=False,
		help_text='Se ativado, quebra o enunciado em partes menores para facilitar a leitura e organização das questões.',
	)


	break_alternatives = models.BooleanField(
		'Quebra de alternativas',
		default=False,
		help_text='Se ativado, quebra as alternativas entre páginas'
  )
  
	break_all_questions = models.BooleanField(
		'Força quebra de página em todas as questões',
		default=False,
		help_text='Se ativado, força a quebra de página em todas as questões exceto a primeira.',

	)
 
	discursive_question_space_type = models.SmallIntegerField(
		'Tipo de espaço para questão discursiva',
		choices=DISCURSIVE_QUESTION_SPACE_TYPES,
  		default=0,
		help_text='Define o tipo de espaço disponível para respostas discursivas, como linhas ou caixas de texto.',
	)

	language = models.SmallIntegerField(
		'Idioma dos textos do caderno',
		choices=LANGUAGES,
  		default=0,
		help_text='Define o idioma padrão do caderno. Termos como "questão", "texto base" dados do cabeçalho padrão serão traduzidos',
	) 
	
	client = models.ForeignKey(
		'Client',
		verbose_name='cliente',
		on_delete=models.PROTECT,
		related_name='exam_print_configs',
	)

	class Meta:
		ordering = ('-created_at',)
		verbose_name = 'configuração de impressão'
		verbose_name_plural = 'configurações de impressão'

	def __str__(self):
		return f'{self.client} - {self.name}'

	@classmethod
	def get_font_size(cls, size_choice):	
		filtered = [t for t in cls.FONT_SIZES if t[0] == size_choice]
		if len(filtered) == 0:
			return 12
		return int(re.sub('[^0-9]','', filtered[0][1]))
	
	@classmethod
	def get_new_default_font_value(self, size):
		SIZE_12, SIZE_14, SIZE_18, SIZE_22, SIZE_32, SIZE_8, SIZE_10, SIZE_11 = range(8)

		font_dict = {
			SIZE_12: '15',
			SIZE_14: '17',
			SIZE_18: '23',
			SIZE_22: '26',
			SIZE_32: '38',
			SIZE_8: '10',
			SIZE_10: '12',
			SIZE_11: '13'
		}

		return font_dict[size]
	
	@property
	def urls(self):
		from django.urls import reverse
		return {
			"detail": reverse("clients:print-configs-update", kwargs={ "pk": self.pk }),
			"api_detail": reverse("api:clients:print-configs-detail", kwargs={ "pk": self.pk }),
			"get_config": reverse("api:clients:print-configs-get-config", kwargs={ "pk": self.pk }),
		}

class TeachingStage(BaseModel):
	client = models.ForeignKey(
		'Client',
		verbose_name='cliente',
		on_delete=models.PROTECT,
	)
	name = models.CharField('nome da etapa', max_length=255)
	code_export = models.CharField('código para exportação', max_length=255, null=True, blank=True)

	def __str__(self):
		return f'{self.name}'

	class Meta:
		verbose_name = "Etapa do ensino"
		verbose_name_plural = "Etapas do ensino"
		ordering = ['created_at']

	@property
	def urls(self):
		from django.urls import reverse
		return {
			"detail": reverse("clients:teaching-stage-update", kwargs={ "pk": self.pk }),
			"api_detail": reverse("api:clients:teaching-stage-detail", kwargs={ "pk": self.pk }),
		}


class EducationSystem(BaseModel):
	client = models.ForeignKey(
		'Client',
		verbose_name='cliente',
		on_delete=models.PROTECT,
	)
	name = models.CharField('nome do sistema de ensino', max_length=255)
	unities = models.ManyToManyField(Unity, verbose_name=("Unidades"), blank=True)

	def __str__(self):
		return f'{self.name}'

	class Meta:
		verbose_name = "Sistema de ensino"
		verbose_name_plural = "Sistemas de ensino"
		ordering = ['created_at']

	@property
	def urls(self):
		from django.urls import reverse
		return {
			"detail": reverse("clients:education-system-update", kwargs={ "pk": self.pk }),
			"api_detail": reverse("api:clients:education-system-detail", kwargs={ "pk": self.pk }),
		}
	
class Mensality(BaseModel):
	client = models.ForeignKey('Client', verbose_name='cliente', on_delete=models.PROTECT,)

	billing_date = models.DateField('data de cobrança', null=True, blank=True) 

	value = models.DecimalField('valor', max_digits=10, decimal_places=2)

	OPEN, PAID, CANCELED = range(1, 4)
	STATUS_CHOICES = (
		(OPEN, 'Em aberto'),
		(PAID, 'Pago'),
		(CANCELED, 'Cancelada'),
	)
	status = models.PositiveSmallIntegerField('status', choices=STATUS_CHOICES, default=OPEN)

	class Meta:
		verbose_name = 'mensalidade'
		verbose_name_plural = 'mensalidades'
		ordering = ['created_at']

	def get_client_plan(self):
		return self.client.get_plan_display()
	get_client_plan.__name__ = 'Plano'
	

class QuestionTag(BaseModel):
	client = models.ForeignKey(Client, verbose_name="cliente", blank=True, null=True, on_delete=models.PROTECT)
	name = models.CharField("Nome", max_length=255)
	
	REVIEW, EDIT = range(2)
	TYPE_CHOICES = (
		(REVIEW, 'Para revisão'),
		(EDIT, 'Para edição')
	)
	
	type = models.PositiveIntegerField('tipo', choices=TYPE_CHOICES, default=REVIEW)

	class Meta:
		verbose_name = 'Tag de questão'
		ordering = ("name", )
		verbose_name_plural = 'Tags de questão'

	def get_absolute_url(self):
		from django.urls import reverse
		return reverse('clients:question_tag_list')

class Partner(BaseModel):
	user = models.OneToOneField(User, verbose_name='Usuário', on_delete=models.PROTECT, related_name='partner')
	client = models.ForeignKey(Client, verbose_name='Cliente', on_delete=models.PROTECT)
	email = models.EmailField("Endereço de email", null=False, blank=False)
	name = models.CharField("Nome do parceiro", max_length=100, blank=False, null=False)
	is_printing_staff = models.BooleanField("É da equipe de impressão", help_text="Tem acesso à tela de impressões de aplicação", default=False)

	def __str__(self):
		return f'{self.client.name} - {self.user.name}'

	def create_user(self):
		if self.email:
			user = User.objects.filter(username=self.email).first()
			if user:
				self.user = user
				user.must_change_password = True
				self.save(skip_hooks=True)
				return

			user = User.objects.create_user(
				email=self.email.lower(),
				name=self.name,
				username=self.email.lower(),
				password=self.email.lower(),
			)
			user.must_change_password = True
			user.save()
			self.user = user
			self.save(skip_hooks=True)
	
	@hook("before_create")
	def create_user_signal(self):
		self.create_user()

	class Meta:
		verbose_name = "Parceiro"
		verbose_name_plural = "Parceiros"
		ordering = ['created_at']