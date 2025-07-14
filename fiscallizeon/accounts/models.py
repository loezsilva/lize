from django.urls import reverse
import uuid
import jwt
import random
import string

from django.contrib import admin
from django.apps import apps
from django.conf import settings 
from django.db import models
from django.db.models.functions import Concat
from django.core.cache import cache
from django.contrib.auth.models import AbstractBaseUser, UserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
from django.template.loader import get_template
from fiscallizeon.core.models import BaseModel
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from fiscallizeon.core.models import BaseModel
from fiscallizeon.core.threadings.sendemail import EmailThread

from simple_history.models import HistoricalRecords

from django.utils.functional import cached_property

class CustomGroup(BaseModel):
	name = models.CharField(_("name"), max_length=150)
	client = models.ForeignKey('clients.Client', related_name='custom_groups', on_delete=models.CASCADE, blank=True, null=True)
	SEGMENTS_TARGET_TYPES = (
		(settings.COORDINATION, 'Coordenações'),
		(settings.STUDENT, 'Alunos'),
		(settings.INSPECTOR, 'Fiscais'),
		(settings.TEACHER, 'Professores'),
		(settings.PARTNER, 'Parceiro'),
		(settings.PARENT, 'Responsáveis'),
	)
	permissions = models.ManyToManyField(
		Permission,
		verbose_name=_("permissions"),
		blank=True,
	)
	segment = models.CharField("Segmentos de usuários", max_length=50, choices=SEGMENTS_TARGET_TYPES)
	default = models.BooleanField("Grupo padrão", blank=True, default=False)

	class Meta:
		verbose_name = "Grupo personalizado"
		verbose_name_plural = "Grupos personalizados"
		unique_together = (
			('name', 'client')
		)

	def __str__(self):
		return self.name if self.client else f'{self.name} - (Padrão Lize)'

	def natural_key(self):
		return (self.name,)
	
	def get_absolute_url(self):
		return reverse("accounts:groups_update", kwargs={"pk": self.pk})
	
	@property
	def urls(self):
		return {
			"update": self.get_absolute_url(),
			"api_detail": reverse('api2:permissions-group', kwargs={ 'pk': self.pk }),
			"api_delete": reverse('api2:permissions-delete-group', kwargs={ 'pk': self.pk }),
			"api_get_users": reverse('api2:permissions-users', kwargs={ 'pk': self.pk }),
		}
		
	@property
	def can_be_removed(self):
		return not self.users.exists()
	
class CustomPermissionMixin(PermissionsMixin):    
	class Meta:
		abstract = True
	
	def get_custom_group_permissions(self):
		return list(str(i[0]) for i in self.custom_groups.annotate(permission_name=Concat(models.F("permissions__content_type__app_label"), models.Value("."), models.F("permissions__codename"))).values_list('permission_name'))

	@cached_property
	def get_group_permissions(self):
		permissions = super().get_group_permissions()
		permissions_list = set(self.get_custom_group_permissions())
		return permissions.union(permissions_list)

	def has_perms(self, perm_list, obj=None):
		"""
		Return True if the user has each of the specified permissions. If
		object is passed, check if the user has all required perms for it.
		"""
		return all(self.has_perm(perm) for perm in perm_list)
	
	@cached_property
	def get_all_permissions(self):
		permissions = super().get_all_permissions()
		permissions_list = set(self.get_custom_group_permissions())
		return permissions.union(permissions_list)
	
	def has_perm(self, perm):
		""" A backend can raise `PermissionDenied` to short-circuit permission checking. """
		# Active superusers have all permissions.
		if self.is_active and self.is_superuser:
			return True
		
		try:
			if perm in self.get_all_permissions:
				return True
		except PermissionDenied:
			return False
		
	def has_module_perms(self, app_label):
		"""
		Return True if the user has any permissions in the given app label.
		Use similar logic as has_perm(), above.
		"""
		# Active superusers have all permissions.
		if self.is_active and self.is_superuser:
			return True
		
		return self.is_active and any(
			perm[: perm.index(".")] == app_label
			for perm in self.get_all_permissions
		)

class User(AbstractBaseUser, CustomPermissionMixin):
	id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
	username = models.CharField(
		_('username'),
		max_length=150,
		unique=True,
		help_text=('150 caracteres ou menos. Letras, números e @/./+/-/_ apenas.'),
		error_messages={
			'unique': _("A user with that username already exists."),
		},
		null=True,
		blank=True
	)
	name = models.CharField(_('name'), max_length=100, blank=True)

	email = models.EmailField(_('email address'), unique=True)
	
	must_change_password = models.BooleanField('Deve mudar a senha no próximo acesso', default=False)

	two_factor_enabled = models.BooleanField('Habilitação da autenticação de dois fatores', default=False)

	is_staff = models.BooleanField(
		_('staff status'),
		default=False,
		help_text=_('Designates whether the user can log into this admin site.'),
	)
	temporarily_inactive = models.BooleanField('temporariamente inativo', default=False)
	is_active = models.BooleanField(
		_('active'),
		default=True,
		help_text=_(
			'Designates whether this user should be treated as active. '
			'Unselect this instead of deleting accounts.'
		),
	)
	date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
	FEMALE = 'F'
	MALE = 'M'
	GENRES = (
		(FEMALE, 'Feminino'),
		(MALE, 'Masculino'),
	)
	genre = models.CharField('gênero', max_length=1, choices=GENRES, null=True, blank=True, default=MALE)
	phone = models.CharField('número para contato', max_length=15,
		validators=[
			RegexValidator(
				regex='^\([1-9]{2}\)\ [2-9]{1}[0-9]{3,4}-[0-9]{4}$',
				message='O número para contato não está no formato correto.',
				code='invalid_phone'
			),
		], blank=True, null=True, default=None)

	objects = UserManager()

	accept_terms_of_question_import = models.BooleanField("Aceitou os termos da importação de questão", default=False, blank=True)

	schools = models.CharField("Escola(as)", max_length=254, blank=True, null=True)

	INTERNET, SOCIAL_MEDIA, FRIENDS, OTHERS = 'internet', 'social_media', 'friends', 'others'

	HOW_DID_YOU_MEET_US_CHOICES = (
		(INTERNET, 'Busca da internet'),
		(SOCIAL_MEDIA, 'Nas redes sociais'),
		(FRIENDS, 'Amigos ou familiares'),
		(OTHERS, 'Outros')
	)

	how_did_you_meet_us = models.CharField("Como você nos conheceu?", max_length=40, choices=HOW_DID_YOU_MEET_US_CHOICES, blank=True)
	how_did_you_meet_us_form = models.CharField("Você poderia especificar? (Opcional)", max_length=254, blank=True)

	accepted_terms_of_intellectual_rights_of_questions = models.BooleanField("Aceitou os termos da importação de questão", default=False, blank=True)
	
	is_freemium = models.BooleanField("Esta no ambiente freemium", default=False, blank=True)

	default_ai_credits = models.SmallIntegerField("Crédito mensal", default=15, blank=True)

	interested_in_purchasing_more_credits = models.BooleanField("Tem interesse em comprar mais créditos", default=False, blank=True)
	custom_groups = models.ManyToManyField(CustomGroup, verbose_name=("Grupos de permissão"), related_name="users", blank=True)
	onboarding_responsible = models.BooleanField('responsável pela integração?', default=False)
	can_request_ai_questions = models.BooleanField('Pode solicitar questão à IA', default=False)

	nickname = models.CharField('como gostaria de ser chamado(a)?', max_length=50, blank=True, null=True)
	avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, storage=PrivateMediaStorage())
	GRAY, GREEN, BLUE, PURPLE, PINK, RED, ORANGE, YELLOW = range(8)
	THEMES = (
		(GRAY, 'Cinza'),
		(GREEN, 'Verde'),
		(BLUE, 'Azul'),
		(PURPLE, 'Roxo'),
		(PINK, 'Rosa'),
		(RED, 'Vermelho'),
		(ORANGE, 'Laranja'),
		(YELLOW, 'Amarelo'),
	)
	color_mode_theme = models.PositiveSmallIntegerField('cor do tema', choices=THEMES, blank=True, default=GRAY)
	has_viewed_starter_onboarding = models.BooleanField('já visualizou a integração inicial?', default=False)
	can_access_app = models.BooleanField('Pode acessar o APP', default=False)

	AFFECTIONATE, RADIANT, AMUSING, HILARIOUS, PLAYFUL, HAPPY, GRATEFUL, SATISFIED, CONTENT, INNOCENT, IN_LOVE, ENCHANTED, EMBARRASSED, BORED, EXHAUSTED, SAD, DESOLATE, IRRITATED, CONFUSED, TENSE, SKULL, ALIEN, CHILLY, CAT, ROBOT = range(25)
	MOODS = (
		(HAPPY, 'Feliz'),
		(GRATEFUL, 'Grato'),
		(CONTENT, 'Contente'),
		(BORED, 'Entediado'),
		(EMBARRASSED, 'Envergonhado'),
		(SAD, 'Triste'),
		(IRRITATED, 'Irritado'),
		(CONFUSED, 'Confuso'),
		(RADIANT, 'Radiante'),
		(AMUSING, 'Divertido'),
		(HILARIOUS, 'Hilariante'),
		(PLAYFUL, 'Brincalhão'),
		(SATISFIED, 'Satisfeito'),
		(INNOCENT, 'Inocente'),
		(IN_LOVE, 'Encantado'),
		(AFFECTIONATE, 'Afetuoso'),
		(ENCHANTED, 'Encantado'),
		(EXHAUSTED, 'Exausto'),
		(DESOLATE, 'Desolado'),
		(TENSE, 'Tenso'),
		(SKULL, 'Caveira'),
		(ALIEN, 'Alienígena'),
		(CHILLY, 'Com frio'),
		(CAT, 'Gato'),
		(ROBOT, 'Robô'),
	)
	
	mood = models.PositiveSmallIntegerField('humor', choices=MOODS, null=True, blank=True)
	background = models.PositiveSmallIntegerField('background', default=0, blank=True)

	EMAIL_FIELD = 'email'
	USERNAME_FIELD = 'username'
	REQUIRED_FIELDS = ['email']

	history = HistoricalRecords()

	class Meta:
		verbose_name = 'usuário'
		verbose_name_plural = 'usuários'
		ordering = ['-date_joined']
		permissions = (
			('can_change_permissions', 'Pode alterar permissões'),
			('view_grade_map_dashboard', 'Pode visualizar o mapão de notas'),
			('view_tri_dashboard', 'Pode visualizar o dashboard de TRI'),
			('view_followup_dashboard', 'Pode visualizar dashboard de acompanhamento'),
			('view_administration_dashboard', 'Pode visualizar o dashboard administrativo'),
			('view_dashboards', 'Pode visualizar o novo dashboard de acompanhamento'),
			('can_use_hijack', 'Pode usar o hijack na listagem de professores/membros/alunos e etc...'),
		)

	def __str__(self):
		return self.name or self.username or self.email

	def get_mood_changes(self):
		historical_records = self.history.order_by('history_date')

		mood_changes = []
		previous_mood = None

		for record in historical_records:
			if previous_mood is None and record.mood is not None:
				change_entry = {
					'date': record.history_date,
					'old_mood': None,
					'new_mood': record.mood,
					'change_type': 'Initial Mood',
					'changed_by': record.history_user.username if record.history_user else 'System'
				}
				mood_changes.append(change_entry)
				previous_mood = record.mood
				continue

			if record.mood != previous_mood and previous_mood is not None:
				change_entry = {
					'date': record.history_date,
					'old_mood': previous_mood,
					'new_mood': record.mood,
					'change_type': 'Mood Updated',
					'changed_by': record.history_user.username if record.history_user else 'System'
				}
				mood_changes.append(change_entry)
				previous_mood = record.mood

		for change in mood_changes:
			print(f"On {change['date']}:")
			print(f"  Change Type: {change['change_type']}")
			print(f"  Old Mood: {change['old_mood']}")
			print(f"  New Mood: {change['new_mood']}")
			print(f"  Changed by: {change['changed_by']}")

		return mood_changes

	def get_unities_data(self):
		"""
			Obtém informações de unidades dos membros da coordenação
		"""
		coordinations = self.get_coordinations()
		unities_names = coordinations.values_list('unity__name', flat=True)
		
		return [
			{
				"name": unity, 
				"initials": (words[0][0] + words[1][0]) if len(unity.replace("-", "").split(' ')) >= 2 else unity.replace(" - ", "")[0:2],
				"coordinations_in_unity": coordinations.filter(unity__name=unity).count(),
			}
			for unity in unities_names for words in [unity.replace("-", "").split()]
		]

	def get_clients(self, db_alias=None):
		Client = apps.get_model('clients', 'Client')
		clients = None

		if self.user_type == settings.TEACHER:
			clients = Client.objects.filter(
				unities__coordinations__in=self.get_coordinations_cache()
			).distinct()

		elif self.user_type == settings.COORDINATION:
			clients = Client.objects.filter(
				unities__coordinations__members__user=self
			).distinct()

		elif self.user_type == settings.STUDENT:
			clients = Client.objects.filter(pk=self.student.client.pk).distinct()
			
		elif self.user_type == settings.PARTNER:
			if self.partner:
				clients = Client.objects.filter(pk=self.partner.client.pk).distinct()
			else:
				clients = Client.objects.none()

		elif self.user_type == settings.PARENT:
			student = self.parent.students.all().first()
			if student and student.client:
				clients = Client.objects.filter(
					pk=student.client.pk
				).distinct()

		if not clients:
			return Client.objects.none()

		return clients.using(db_alias) if db_alias else clients

	@property
	def client_pk(self):
		return str(self.client.pk)

	@admin.display(description="Clientes")
	def get_clients_display(self):
		return list(self.get_clients().values_list('name', flat=True))

	def can_see_all(self):
		return self.get_coordinations().filter(can_see_all=True).exists()

	@property
	def client(self):
		CACHE_KEY = f'USER_CLIENTS_OBJ_{self.pk}'
		if not cache.get(CACHE_KEY):
			cache.set(CACHE_KEY, self.get_clients().first(), 4 * 60 * 60)
		return cache.get(CACHE_KEY)

	@cached_property
	def client_uncached(self):
		return self.get_clients().first()

	def get_clients_cache(self):
		CACHE_KEY = f'USER_CLIENTS_{self.pk}'
		if not cache.get(CACHE_KEY):
			if self.is_freemium:
				cache.set(CACHE_KEY, [self.pk], 4 * 60 * 60)
			else:
				clients = list(self.get_clients(db_alias='default').values_list('pk', flat=True))
				cache.set(CACHE_KEY, clients, 4 * 60 * 60)

		return cache.get(CACHE_KEY)

	def get_coordinations(self, year=None, db_alias=None):
		TeacherSubject = apps.get_model('inspectors', 'TeacherSubject')
		SchoolCoordination = apps.get_model('clients', 'SchoolCoordination')
		SchoolClass = apps.get_model('classes', 'SchoolClass')

		coordinations = None

		if self.user_type == settings.COORDINATION:
			coordinations = SchoolCoordination.objects.filter(members__user=self).distinct()

			if self.can_navigate_between_profiles and hasattr(self, 'inspector'):
				coordinations.union(self.inspector.coordinations.all().distinct())

		elif self.user_type == settings.TEACHER or self.user_type == settings.INSPECTOR:
			coordinations = self.inspector.coordinations.all().distinct()
			
			subjects = self.inspector.teachersubject_set.filter(
				active=True,
				school_year=year or timezone.now().year
			)

			if subjects:
				coordinations.union(SchoolCoordination.objects.filter(
						pk__in=subjects.values('classes__coordination_id')
					)
				)

			if self.can_navigate_between_profiles:
				coordinations.union(SchoolCoordination.objects.filter(members__user=self).distinct())


		elif self.user_type == settings.STUDENT:
			coordinations = SchoolCoordination.objects.filter(
				school_classes__students__user=self,
				school_classes__school_year=year or timezone.now().year,
			).distinct()

		if not coordinations:
			return SchoolCoordination.objects.none()

		return coordinations.using(db_alias) if db_alias else coordinations

	@property
	def get_user_classes(self):
		if self.user_type == settings.STUDENT:
			classes_names = list(self.student.classes.filter(
				school_year=timezone.now().year
			).values_list("name", flat=True).distinct())

			return ', '.join(classes_names)

		return ''

	@property
	def get_type_client(self):
		if client := self.client:
			return client.type_client
		return None

	@property
	def get_base_url(self):
		client = self.client
		return 'mentorize/base.html' if client and client.type_client == 3 else None


	@property
	def get_user_ra(self):
		if self.user_type == settings.STUDENT:
			return self.student.enrollment_number

		return ''
	
	@property
	def get_user_coordinations(self):
		coordinations = list(self.get_coordinations().values('name', 'unity__name'))
		return ', '.join([f'{c["name"]} - {c["unity__name"]}' for c in coordinations])

	def get_coordinations_cache(self):
		CACHE_KEY = f'USER_COORDINATIONS_{self.pk}'
		if not cache.get(CACHE_KEY):
			coordinations = list(self.get_coordinations(db_alias='default').values_list('pk', flat=True))
			cache.set(CACHE_KEY, coordinations, 4 * 60 * 60)
		return cache.get(CACHE_KEY)

	@property
	def can_navigate_between_profiles(self):
		from fiscallizeon.clients.models import CoordinationMember
		from fiscallizeon.inspectors.models import Inspector

		if self.user_type == settings.TEACHER:
			is_member_of_coordination = CoordinationMember.objects.filter(user=self).exists()
			return is_member_of_coordination
		elif self.user_type == settings.COORDINATION:
			coordinator_email = self.email 
			has_matching_inspector_email = Inspector.objects.filter(
				email=coordinator_email,
				user__email=coordinator_email
			).exists()
			return has_matching_inspector_email
		return False
		# CACHE_KEY = f'USER_CAN_NAVIGATE_BETWEEN_PROFILES_{self.pk}'
		# result = cache.get(CACHE_KEY)
		# if not result:
		# 	CoordinationMember = apps.get_model("clients", "CoordinationMember")
		# 	Inspector = apps.get_model("inspectors", "Inspector")

		# 	if self.user_type == settings.TEACHER:
		# 		is_member_of_coordination = CoordinationMember.objects.using('default').filter(
		# 			user=self,
		# 			coordination__unity__client=self.client,
		# 		).exists()
		# 		cache.set(CACHE_KEY, is_member_of_coordination, 4 * 60 * 60)

		# 	elif self.user_type == settings.COORDINATION:
		# 		coordinator_email = self.email 
		# 		has_matching_inspector_email = Inspector.objects.using('default').filter(
		# 			email=coordinator_email,
		# 			coordinations__unity__client=self.client
		# 		).exists()
		# 		cache.set(CACHE_KEY, has_matching_inspector_email, 4 * 60 * 60)

		# 	cache.set(CACHE_KEY, False, 4 * 60 * 60)
		# return result

	@property
	def user_type(self):
		Inspector = apps.get_model("inspectors", "Inspector")

		CACHE_KEY = f'USER_TYPE_{self.pk}'
		
		if not cache.get(CACHE_KEY): 
			if hasattr(self, 'inspector') and not self.inspector.can_access_coordinator_profile:
				if self.inspector.inspector_type == Inspector.TEACHER:
					cache.set(CACHE_KEY, settings.TEACHER)
				else: 
					cache.set(CACHE_KEY, settings.INSPECTOR)
			elif self.coordination_member.exists():
				cache.set(CACHE_KEY, settings.COORDINATION) 
			elif hasattr(self, 'student'):
				cache.set(CACHE_KEY, settings.STUDENT)
			elif hasattr(self, 'parent'):
				cache.set(CACHE_KEY, settings.PARENT)
			elif hasattr(self, 'partner'):
				cache.set(CACHE_KEY, settings.PARTNER)
			else:
				return None
		
		return cache.get(CACHE_KEY)

	@admin.display(description="Tipo")
	def user_type_display(self):
		if self.user_type == "student":
			return "Aluno"
		elif self.user_type == "teacher":
			return "Professor"
		elif self.user_type == "inspector":
			return "Fiscal"
		elif self.user_type == "parent":
			return "Responsável"
		elif self.user_type == "coordination":
			return "Coordenação"
		elif self.user_type == "partner":
			return "Parceiro"

	@property
	def get_user_first_name(self):
		if self.user_type == settings.COORDINATION:
			return self.coordination_member.first().user.first_name
		elif self.user_type in [settings.INSPECTOR, settings.TEACHER]:
			return self.inspector.first_name
		elif self.user_type == settings.STUDENT:
			return self.student.first_name
		elif self.user_type == settings.PARTNER:
			return self.name

		return None

	@property
	def get_student(self):
		if self.user_type == settings.STUDENT:
			return self.student
		return ''

	@property
	def get_user_full_name(self):
		if self.user_type == settings.COORDINATION:
			return self.coordination_member.first().user.name
		elif self.user_type in [settings.INSPECTOR, settings.TEACHER]:
			return self.inspector.name
		elif self.user_type == settings.STUDENT:
			return self.student.name

		return ""

	@property
	def get_user_function(self):
		if self.user_type == settings.COORDINATION:
			return 'Coordenação'
		elif self.user_type == settings.INSPECTOR or self.user_type == settings.TEACHER:
			return self.inspector.get_inspector_type_display()
		elif self.user_type == settings.STUDENT:
			return 'Aluno'

		return None

	def natural_key(self):
		url = ''
		if self.avatar:
			url = self.avatar.url
		return (self.name, url, self.genre)

	def get_short_name(self):
		return self.username

	def get_full_name(self):
		return str(self)

	def get_url_avatar(self):
		return self.avatar.url

	@property
	def first_name(self):
		return self.name.split(" ")[0]
	
	@property
	def some_name(self):
		if self.user_type == settings.TEACHER:
			return self.inspector.first_name
		return self.name or self.username or self.email

	@property
	def has_high_school_coordinations(self):

		SchoolCoordination = apps.get_model('clients', 'SchoolCoordination')

		CACHE_KEY = F"USER-HAS-HIGH-SCHOOL-COORDINATION-{self.pk}"
		
		if not cache.get(CACHE_KEY):
			coordinations = SchoolCoordination.objects.filter(pk__in=self.get_coordinations_cache()).distinct()
			
			high_school_coordinations = coordinations.filter(
				high_school=True
			)

			cache.set(CACHE_KEY, high_school_coordinations.exists(), 4 * 60 * 60)
		
		return cache.get(CACHE_KEY)

	@property
	def has_elementary_school_coordinations(self):

		SchoolCoordination = apps.get_model('clients', 'SchoolCoordination')

		CACHE_KEY = F"USER-HAS-ELEMENTARY-SCHOOL-COORDINATION-{self.pk}"
		
		if not cache.get(CACHE_KEY):
			coordinations = SchoolCoordination.objects.filter(pk__in=self.get_coordinations_cache()).distinct()
			
			elementary_school_coordinations = coordinations.filter(
				models.Q(
					models.Q(elementary_school=True) | models.Q(elementary_school2=True)
				)
			)

			cache.set(CACHE_KEY, elementary_school_coordinations.exists(), 4 * 60 * 60)
		
		return cache.get(CACHE_KEY)

	@property
	def has_elementary_school_only_coordinations(self):

		SchoolCoordination = apps.get_model('clients', 'SchoolCoordination')

		CACHE_KEY = F"USER-HAS-ELEMENTARY-SCHOOL-ONLY-COORDINATION-{self.pk}"

		if not cache.get(CACHE_KEY):
			coordinations = SchoolCoordination.objects.filter(pk__in=self.get_coordinations_cache()).distinct()

			elementary_school_coordinations = coordinations.filter(
				elementary_school=True
			)

			cache.set(CACHE_KEY, elementary_school_coordinations.exists(), 4 * 60 * 60)

		return cache.get(CACHE_KEY)

	@property
	def has_elementary_school2_coordinations(self):

		SchoolCoordination = apps.get_model('clients', 'SchoolCoordination')

		CACHE_KEY = F"USER-HAS-ELEMENTARY-SCHOOL2-COORDINATION-{self.pk}"

		if not cache.get(CACHE_KEY):
			coordinations = SchoolCoordination.objects.filter(pk__in=self.get_coordinations_cache()).distinct()

			elementary_school2_coordinations = coordinations.filter(
				elementary_school2=True
			)

			cache.set(CACHE_KEY, elementary_school2_coordinations.exists(), 4 * 60 * 60)

		return cache.get(CACHE_KEY)

	@property
	def client_modules(self):
		CACHE_KEY = f'CLIENT_MODULES_{self.pk}'
		if not cache.get(CACHE_KEY): 
			Client = apps.get_model("clients", "Client")
			OMRCategory = apps.get_model('omr', 'OMRCategory')
			Integration = apps.get_model("integrations", "Integration")

			clients = Client.objects.filter(
				pk__in=self.get_clients_cache()
			)
			modules = {
				'has_omr': any(client.has_omr for client in clients),
				'has_omrnps': any(client.has_omrnps for client in clients),
				'has_distribution': any(client.has_distribution for client in clients),
				'has_dashboard': any(client.has_dashboard for client in clients),
				'has_followup_dashboard': any(client.has_followup_dashboard for client in clients),
				'use_only_own_subjects': any(client.use_only_own_subjects for client in clients),
				'use_only_own_topics': any(client.use_only_own_topics for client in clients),
				'allow_student_notifications': any(client.allow_student_notifications for client in clients),
				'show_previews_template_student': any(client.show_previews_template_student for client in clients),
				'has_template': any(client.has_template for client in clients),
				'has_exam_elaboration': any(client.has_exam_elaboration for client in clients),
				'has_public_questions': any(client.has_public_questions for client in clients),
				'has_diagramation': any(client.has_diagramation for client in clients),
				'has_dashboards': any(client.has_dashboards for client in clients),
				'has_study_material': any(client.has_study_material for client in clients),
				'has_wrongs': any(client.has_wrongs for client in clients),
				'has_automatic_creation': any(client.has_automatic_creation for client in clients),
				'has_integration': any(client.has_integration for client in clients),
				'has_superpro_integration': any(client.has_superpro_integration for client in clients),
				'has_discursive_answers': any(client.has_discursive_answers for client in clients),
				'teachers_can_elaborate_exam': any(client.teachers_can_elaborate_exam for client in clients),
				'allow_add_same_teacher_subject_in_exam': any(client.allow_add_same_teacher_subject_in_exam for client in clients),
				'show_id_erp_in_exam': any(client.show_id_erp_in_exam for client in clients),
				'has_partners': any(client.has_partners for client in clients),
				'has_tri': any(client.has_tri for client in clients),
				'has_sisu_simulator': any(client.has_sisu_simulator for client in clients),
				'has_ia_creation': any(client.has_ia_creation for client in clients),
				'has_new_teacher_experience': any(client.has_new_teacher_experience for client in clients),
				'has_late_questions': any(client.has_late_questions for client in clients),
				'allow_online_abstract_application': any(client.allow_online_abstract_application for client in clients),
				'allow_add_exception_deadline_correction_response': any(client.allow_add_exception_deadline_correction_response for client in clients),
				'send_email_to_student_after_create': any(client.send_email_to_student_after_create for client in clients),
				'has_question_formatter': any(client.has_question_formatter for client in clients),
				'has_sum_question': any(client.has_sum_question for client in clients),
				'has_cloze_question': any(client.has_cloze_question for client in clients),
				'allow_login_only_google': any(client.allow_login_only_google for client in clients),
				'has_hybrid_omr': any(client.omr_categories.filter(sequential=OMRCategory.HYBRID_025).exists() for client in clients),
				'has_reduced_model': any(client.omr_categories.filter(sequential=OMRCategory.REDUCED_MODEL).exists() for client in clients),
				'client_has_offset_answer_sheet': any(client.omr_categories.filter(sequential__in=[OMRCategory.OFFSET_1, OMRCategory.OFFSET_SCHOOLCLASS]).exists() for client in clients),
				'client_has_salta_answer_sheet': any(client.omr_categories.filter(sequential=OMRCategory.SALTA_DEFAULT).exists() for client in clients),
				'client_has_subjects_answer_sheet': any(client.omr_categories.filter(sequential=OMRCategory.SUBJECTS_1).exists() for client in clients),
				'allow_login_only_google': any(client.allow_login_only_google for client in clients),
				'can_select_header_in_create_or_update_exam': any(client.can_select_header_in_create_or_update_exam for client in clients),
				'enabled_new_answer_sheet_experience': any(client.enabled_new_answer_sheet_experience for client in clients),
				'can_request_ai_questions': any(client.can_request_ai_questions for client in clients),
				'can_disable_multiple_correct_options': any(client.can_disable_multiple_correct_options for client in clients),
				'has_filtered_layout_for_today_student_applications': any(client.has_filtered_layout_for_today_student_applications for client in clients),
				'has_review_system': any(client.has_review_system for client in clients),
				'has_customize_application': any(client.has_customize_application for client in clients),
				'has_essay_system': any(client.has_essay_system for client in clients),
				'has_metabase_dashboard': any(client.has_metabase_dashboard for client in clients),
				'has_discursive_ai_correction': any(client.has_discursive_ai_correction for client in clients),
				'can_access_app': any(client.can_access_app for client in clients),
				'has_realms_integration': any(hasattr(client, 'integration') and client.integration.erp == Integration.REALMS for client in clients),
				'enabled_new_answer_correction': any(client.enabled_new_answer_correction for client in clients),
			}
			cache.set(CACHE_KEY, modules, 600)
		return cache.get(CACHE_KEY)
	
	@property
	def client_can_disable_multiple_correct_options(self):
		return self.client_modules.get('can_disable_multiple_correct_options', False)
	
	@property
	def client_has_omr(self):
		return self.client_modules.get('has_omr', False)

	@property
	def client_has_omrnps(self):
		return self.client_modules.get('has_omrnps', False)

	@property
	def client_has_distribution(self):
		return self.client_modules.get('has_distribution', False)

	@property
	def client_has_dashboard(self):
		return self.client_modules.get('has_dashboard', False)

	@property
	def client_has_followup_dashboard(self):
		return self.client_modules.get('has_followup_dashboard', False)

	@property
	def client_use_only_own_subjects(self):
		return self.client_modules.get('use_only_own_subjects', False)

	@property
	def client_use_only_own_topics(self):
		return self.client_modules.get('use_only_own_topics', False)
	
	@property
	def client_allow_student_notification(self):
		return self.client_modules.get('allow_student_notifications', False)

	@property
	def client_show_previews_template_student(self):
		return self.client_modules.get('show_previews_template_student', False)
	
	@property
	def client_has_template(self):
		return self.client_modules.get('has_template', False)
	
	@property
	def client_has_exam_elaboration(self):
		return self.client_modules.get('has_exam_elaboration', False)

	@property
	def client_has_public_questions(self):
		return self.client_modules.get('has_public_questions', False)
	
	@property
	def client_has_diagramation(self):
		return self.client_modules.get('has_diagramation', False)
	
	@property
	def client_has_dashboards(self):
		return self.client_modules.get('has_dashboards', False)

	@property
	def client_has_study_material(self):
		return self.client_modules.get('has_study_material', False)

	@property
	def client_has_wrongs(self):
		return self.client_modules.get('has_wrongs', False)

	@property
	def client_has_automatic_creation(self):
		return self.client_modules.get('has_automatic_creation', False)
	
	@property
	def client_has_allow_login_only_google(self):
		return self.client_modules.get('allow_login_only_google', False)

	@property
	def client_has_access_token(self):
		return self.get_clients().filter(
			integration__isnull=False
		).exists()

	@property
	def client_has_integration(self):
		return self.client_modules.get('has_integration', False)

	@property
	def client_has_superpro_integration(self):
		return self.client_modules.get('has_superpro_integration', False)
	
	@property
	def client_has_realms_integration(self):
		return self.client_modules.get('has_realms_integration', False)

	@property
	def client_has_discursive_omr(self):
		return self.client_modules.get('has_discursive_answers', False)

	@property
	def client_has_hybrid_omr(self):
		return self.client_modules.get('has_hybrid_omr', False)

	@property
	def client_teachers_can_elaborate_exam(self):
		return self.client_modules.get('teachers_can_elaborate_exam', False)

	@property
	def client_allow_same_teacher_subject(self):
		return self.client_modules.get('allow_add_same_teacher_subject_in_exam', False)

	@property
	def client_show_id_erp_in_exam(self):
		return self.client_modules.get('show_id_erp_in_exam', False)
	
	@property
	def client_has_sum_questions(self):
		return self.client_modules.get('has_sum_question', False)
	
	@property
	def client_has_cloze_questions(self):
		return self.client_modules.get('has_cloze_question', False)
	
	@property
	def client_has_reduced_model(self):
		return self.client_modules.get('has_reduced_model', False)
	
	@property
	def client_has_offset_answer_sheet(self):
		return self.client_modules.get('client_has_offset_answer_sheet', False)
	
	@property
	def client_has_salta_answer_sheet(self):
		return self.client_modules.get('client_has_salta_answer_sheet', False)
	
	@property
	def client_has_subjects_answer_sheet(self):
		return self.client_modules.get('client_has_subjects_answer_sheet', False)

	@property
	def client_allow_online_abstract_application(self):
		return self.client_modules.get('allow_online_abstract_application', False)
	
	@property
	def client_has_question_formatter(self):
		return self.client_modules.get('has_question_formatter', False)

	@property
	def client_allow_add_exception_deadline_correction_response(self):
		return self.client_modules.get('allow_add_exception_deadline_correction_response', False)

	@property
	def client_send_email_to_student_after_create(self):
		return self.client_modules.get('send_email_to_student_after_create', False)

	@property
	def client_has_tri(self):		
		return self.client_modules.get('has_tri', False)

	@property
	def client_has_sisu_simulator(self):
		return self.client_modules.get('has_sisu_simulator', False)

	@property
	def client_has_ia_creation(self):
		return self.client_modules.get('has_ia_creation', False)

	@property
	def client_has_new_teacher_experience(self):
		return self.client_modules.get('has_new_teacher_experience', False)
	
	@property
	def client_can_request_ai_questions(self):
		return self.client_modules.get('can_request_ai_questions', False)
	
	@property
	def client_has_review_system(self):
		return self.client_modules.get('has_review_system', False)
	
	@property
	def client_has_customize_application(self):
		return self.client_modules.get('has_customize_application', False)

	@property
	def client_has_essay_system(self):
		return self.client_modules.get('has_essay_system', False)
	
	@property
	def client_has_metabase_dashboard(self):
		return self.client_modules.get('has_metabase_dashboard', False)
	
	@property
	def client_has_discursive_ai_correction(self):
		return self.client_modules.get('has_discursive_ai_correction', False)

	@property
	def client_can_select_header_in_create_or_update_exam(self):
		return self.client_modules.get('can_select_header_in_create_or_update_exam', False)
	
	@property
	def client_has_filtered_layout_for_today_student_applications(self):
		return self.client_modules.get('has_filtered_layout_for_today_student_applications', False)
	@property
	def client_can_access_app(self):
		return self.client_modules.get('can_access_app', False) or self.can_access_app

	def client_teacher_configuration(self, level=None):
		from fiscallizeon.clients.models import ClientTeacherObligationConfiguration
		return ClientTeacherObligationConfiguration.objects.filter(client=self.client, level=level).first() if level is not None else None
		
	@property
	def client_omr_categories_sequentials(self):
		Client = apps.get_model("clients", "Client")
		clients = Client.objects.filter(
			pk__in=self.get_clients_cache()
		)

		if clients:
			return list(clients.first().omr_categories.filter(enabled=True).values_list('sequential', flat=True))
		return []
	
	@property
	def client_session_timeout_minutes(self):
		Client = apps.get_model("clients", "Client")
		clients = Client.objects.filter(
			pk__in=self.get_clients_cache()
		)
		if client := clients.first():
			return client.session_timeout_minutes

	@property
	def generate_sleekplan_token(self):
		private_key = settings.SLEEKPLAN_PRIVATE_KEY

		username = f'{self.user_type[0]}_{"_".join(self.get_user_full_name.lower().split(" "))}'

		user_data = {
			'mail': self.email,
			'id': str(self.pk),
			'name': username,
			'full_name': self.get_user_full_name,
			'meta': {
				'companyName': self.client.name if self.client else "Fiscallize",
			}
		}

		return jwt.encode(user_data, private_key, algorithm='HS256')

	@property
	def get_exam_headers(self):
		from fiscallizeon.exams.models import ExamHeader

		return ExamHeader.objects.filter(
			user__coordination_member__coordination__unity__client__in=self.get_clients_cache()
		).distinct()

	@property
	def questions_configuration(self):
		client = self.get_clients().first()
		if client and hasattr(client, 'questions_configuration'):
			return client.questions_configuration
		return None

	def get_questions_database_cache(self, include_public_questions=True):
		from fiscallizeon.questions.models import Question

		CACHE_KEY = f'USER_QUESTIONS_DATABASE_{self.get_clients_cache()[0]}'

		if not cache.get(CACHE_KEY): 
			questions = questions = Question.objects.filter(is_abstract=False)

			if include_public_questions:
				questions = questions.filter(
					models.Q(
						models.Q(coordinations__unity__client__in=self.get_clients_cache()) |
						models.Q(is_public=True),
					)
				)
			else:
				questions = questions.filter(
					coordinations__unity__client__in=self.get_clients_cache()
				)

			questions = list(questions.distinct().values_list('pk', flat=True))
			cache.set(CACHE_KEY, questions, 4 * 60 * 60)

		return cache.get(CACHE_KEY)

	@property
	def client_confignotification(self):
		from fiscallizeon.clients.models import ConfigNotification
		return ConfigNotification.objects.filter(client__in=self.get_clients_cache()).first()

	def get_availables_subjects(self):
		from fiscallizeon.subjects.models import Subject

		queryset = Subject.objects.filter(
				models.Q(client__in=self.get_clients_cache()) |
				models.Q(client__isnull=True) |
				models.Q(parent_subject__isnull=True, client__isnull=True) |
				models.Q(parent_subject__isnull=False, client__in=self.get_clients_cache())
			).distinct()
		
		return queryset.exclude(client__isnull=True) if self.client_use_only_own_subjects else queryset
		
	@cached_property
	def get_availables_subjects_cached(self):
		return self.get_availables_subjects()
	

	@property
	def get_current_groups(self):
		queryset_groups = self.custom_groups.all().values_list('name', flat=True)
		queryset_groups = [str(group).title() for group in queryset_groups if isinstance(group, str)]

		return ', '.join(queryset_groups)


	@property
	def client_has_partners(self):
		return self.client_modules.get('has_partners', False)
		
	@property
	def client_has_late_questions(self):
		return self.client_modules.get('has_late_questions', False)

	@property
	def availables_credits(self):
		today = timezone.localtime(timezone.now()).today()
		return self.default_ai_credits - self.utilized_credits.filter(created_at__month=today.month).count()

	@property
	def can_create_ai_question(self):
		return self.availables_credits > 0

	@property
	def client_enabled_new_answer_sheet_experience(self):
		return self.client_modules.get('enabled_new_answer_sheet_experience', False)

	@property
	def client_enabled_new_answer_correction(self):
		return self.client_modules.get('enabled_new_answer_correction', False)

	def create_ai_credit_use(self):
		from fiscallizeon.ai.models import AICredit, OpenAIQuery

		prompt = OpenAIQuery.objects.using('default').filter(user=self).order_by('created_at').last()

		AICredit.objects.create(
			user=self,
			prompt=prompt
		)

	def create_teacher(self):
		from django.apps import apps
		Inspector = apps.get_model('inspectors', 'Inspector')

		Inspector.objects.create(
			user=self,
			name=self.name,
			email=self.email,
			has_ia_creation=True,
			has_new_teacher_experience=True,
		)

	def get_exams(self):
		exams = self.exams_created.order_by('-created_at').distinct()
		return exams
	def add_permission(self, app_label, codename):
		permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
		self.user_permissions.add(permission)

	def remove_permission(self, app_label, codename):
		permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
		self.user_permissions.remove(permission)

	def get_dashboards(self):
		from fiscallizeon.dashboards.models import Dashboard
		return Dashboard.objects.filter(
			models.Q(client__isnull=True) |
			models.Q(created_by=self) |
			models.Q(client=self.client) |
			models.Q(client=self.client, is_public=True)
		)

	@staticmethod
	def get_default_groups(user_type):
		return CustomGroup.objects.filter(client__isnull=True, segment=user_type)

	@property
	def urls(self):
		return {
			"permissions": reverse('accounts:user_permissions', kwargs={ 'pk': self.pk }),
		}
	
	@property
	def last_import(self):
		from fiscallizeon.exports.models import Import
		return Import.objects.filter(created_by=self).order_by('created_at').last()
	
	@property
	def last_import_exam(self):
		from fiscallizeon.exports.models import Import
		return Import.objects.filter(type=Import.EXAMS, created_by=self).order_by('created_at').last()

	@property
	def last_import_application_students(self):
		from fiscallizeon.exports.models import Import
		return Import.objects.filter(type=Import.APPLICATION_STUDENTS, created_by=self).order_by('created_at').last()
	
	@property
	def last_import_elaboration_request(self):
		from fiscallizeon.exports.models import Import
		return Import.objects.filter(type=Import.ELABORATION_REQUEST, created_by=self).order_by('created_at').last()
	
	@property
	def last_import_essay_grades(self):
		from fiscallizeon.exports.models import Import
		return Import.objects.filter(type=Import.ESSAY_GRADES, created_by=self).order_by('created_at').last()

	def add_custom_groups(self, segment):
        # Se o cliente tiver algum grupo padrão para um segmento específico, eu seto esses grupos
        # se não eu pego os grupos padrões da Lize
		user = self
		client = self.client
		
		if client:
			if client.has_default_groups(segment):
				groups = client.get_groups(with_annotations=False).filter(client__isnull=False, segment=segment, default=True)
				for group in groups:
					user.custom_groups.add(group)
			else:
				groups = client.get_groups(with_annotations=False).filter(client__isnull=True, segment=segment, default=True)
				for group in groups:
					user.custom_groups.add(group)
	
	def get_coordinations_school_classes(self, year: int = timezone.now().year):
		
		from fiscallizeon.clients.models import SchoolCoordination
		from fiscallizeon.classes.models import SchoolClass

		coordinations = self.get_coordinations_cache()

		coordination_subquery = SchoolCoordination.objects.only('pk').filter(
            pk__in=coordinations    
        ).values('pk')

		return SchoolClass.objects.only(
            'pk', 'name', 'coordination__unity__name'
        ).select_related(
            'coordination__unity'
        ).filter(
            coordination__in=models.Subquery(coordination_subquery),
            school_year=year
        ).annotate(
			full_name=Concat(
				models.F('name'),
				models.Value(' - '),
				models.F('coordination__unity__name'),
				models.Value(' - '),
				models.F('school_year'),
				output_field=models.CharField()
			)
		).values(
			'pk',
			'name',
			'full_name',
		)

class SSOTokenUser(BaseModel):
	access_token = models.UUIDField(default=uuid.uuid4, editable=False)
	refresh_token = models.UUIDField(default=uuid.uuid4, editable=False)
	user = models.OneToOneField(User, verbose_name="Usuário", on_delete=models.CASCADE)
	expire_in = models.DateTimeField("Expira em", auto_now=False, auto_now_add=False)


class TwoFactorAuth(BaseModel):
	user = models.OneToOneField(User, verbose_name="Usuário", on_delete=models.CASCADE)
	two_factor_code = models.CharField(max_length=6)
	expire_in = models.DateTimeField("Expira em", null=True, blank=True) 
	is_verified = models.BooleanField(default=False)

	def generate_code(self):
		self.two_factor_code = ''.join(random.choices(string.digits, k=6))
		self.expire_in = timezone.now() + timedelta(minutes=5)
		self.save()

	def send_code_email(self):
		template = get_template('accounts/email_template/send_email_two_factor.html')
		html = template.render({
			'inspector': self,
			'code': self.two_factor_code,
			"BASE_URL": settings.BASE_URL
		})
		subject = 'Codigo disponivel'
		to = [self.user.email]
		EmailThread(subject, html, to).start()
