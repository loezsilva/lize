from tinymce.models import HTMLField

from django.db import models
from django.conf import settings

from django.urls import reverse

from fiscallizeon.core.models import BaseModel
from fiscallizeon.accounts.models import User
from django.utils.functional import lazy
from fiscallizeon.notifications.managers import NotificationManager
from django.apps import apps
from django_lifecycle import hook
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError
from fiscallizeon.core.fields import ChoiceArrayField

def get_apps_labels():
    choices = (
        ('exams.Exam', 'Cadernos'),
        ('applications.Application', 'Aplicação'),
        ('ApplicationMultiple', 'Múltiplas Aplicações'),
        ('ExamTemplate', 'Gabarito avulso'),
        ('questions.Question', 'Questions'),
        ('students.Student', 'Alunos'),
        ('inspectors.Inspector', 'Professor'),
        ('Inspector', 'Fiscais'),
    )

    return choices

class Notification(BaseModel):    
    FEATURE, ANNOUNCEMENT, SEARCH, ONBOARDING, IA = range(5)
    CATEGORY_TYPES = (
        (FEATURE, 'Função'),
        (ANNOUNCEMENT, 'Aviso'),
        (SEARCH, 'Pesquisa'),
        (IA, 'IA'),
        (ONBOARDING, 'Onboarding'),
    )

    TARGET_TYPES = (
        (settings.COORDINATION, 'Coordenações'),
        (settings.STUDENT, 'Alunos'),
        (settings.INSPECTOR, 'Fiscais'),
        (settings.TEACHER, 'Professores'),
        (settings.PARENT, 'Responsáveis'),
        (settings.PARTNER, 'Parceiros'),
    )

    AUTO, SMALL, MEDIO, BIG,  = 'auto', '40vh', '60vh', '85vh' 
    HEIGHT_CHOICES = (
        (AUTO, "Automático"),
        (SMALL, "Pequeno"),
        (MEDIO, "Médio"),
        (BIG, "Grande (form)")
    )

    SM, MD, LG = 'sm', 'md', 'lg'
    WIDTH_CHOICES = (
        (SM, "Pequeno"),
        (MD, "Médio"),
        (LG, "Grande (form)")
    )
    MODAL, COMPONENT = 'modal', 'component'
    NPS_TYPES = (
        (MODAL, 'Em Modal'),
        (COMPONENT, 'Componente em baixo da página'),
    )
    
    DEFAULT, NPS, CSAT = 'default', 'nps', 'csat'
    
    TYPES_CHOICES = (
        (DEFAULT, 'Padrão'),
        (NPS, 'NPS'),
        (CSAT, 'CSAT'),
    )

    urls = models.TextField("Lista de urls (Separada por virgula)", help_text="Separe por virgula todas as urls onde você deseja chamar essa notificação", blank=True, null=True)
    
    modal_height = models.CharField("Altura da modal", max_length=10, choices=HEIGHT_CHOICES, default=MEDIO)
    modal_width = models.CharField("Largura da modal", max_length=10, choices=WIDTH_CHOICES, default=MD)

    clients = models.ManyToManyField('clients.Client', verbose_name='Clientes', blank=True)
    users = models.ManyToManyField(User, verbose_name='Usuários', related_name='received_notifications', blank=True)

    display_until_end_date = models.BooleanField("Mostrar contador de notificação até a data de fim definida", default=True, blank=True)
    high_school = models.BooleanField('Ensino médio', default=False)
    elementary_school = models.BooleanField('Ensino fundamental', default=False)
    title = models.CharField('Título', max_length=255)
    description = models.CharField('Descrição', max_length=255)
    content = HTMLField('Texto da notificação')
    viewed_by = models.ManyToManyField('accounts.User', through='NotificationUser')
    start_date = models.DateTimeField('Data de início')
    end_date = models.DateTimeField('Data de fim')
    segments = ChoiceArrayField(models.CharField("Segmentos de usuário", choices=TARGET_TYPES, max_length=50), verbose_name="Segmento de usuários", blank=True, null=True)
    category = models.PositiveSmallIntegerField('Categoria', choices=CATEGORY_TYPES, default=ANNOUNCEMENT)
    show_modal = models.BooleanField('Mostrar notificação automaticamente', default=False)
    type = models.CharField("Tipo de notificação", choices=TYPES_CHOICES, default=DEFAULT, max_length=30, blank=True)
    nps_type = models.CharField('Como mostrar a pesquisa', choices=NPS_TYPES, max_length=30, blank=True, default=MODAL)
    
    AFTER_CREATE, AFTER_DELETE, AFTER_UPDATE, BEFORE_CREATE, BEFORE_DELETE, BEFORE_UPDATE, IN_LIST = range(7)
    TRIGGERS_CHOICES = (
        (AFTER_CREATE, "Depois de criar"),
        (AFTER_DELETE, "Depois de deletar"),
        (AFTER_UPDATE, "Depois de atualizar"),
        (BEFORE_CREATE, "Antes de criar"),
        (BEFORE_DELETE, "Antes de deletar"),
        (BEFORE_UPDATE, "Antes de atualizar"),
        (IN_LIST, "Na listagem"),
    )
    AFTER_DIAGRAMATION, AFTER_VIEW_EXAM_RESULTS, AFTER_SEND_NOTE_FOR_ACTIVE, AFTER_VIEW_STUDENT_APPLICATION_RESULTS, AFTER_STUDENT_REVIEW_QUESTIONS, IN_VIEW_EXAM_RESULTS = range(6)
    
    ESPECIAL_TRIGGERS_CHOICES = (
        (AFTER_DIAGRAMATION, "Depois de diagramar uma prova"),
        (AFTER_VIEW_EXAM_RESULTS, "Depois ver resultados de um caderno (Coordenação)"),
        (AFTER_SEND_NOTE_FOR_ACTIVE, "Depois de enviar notas para Activesoft"),
        (AFTER_VIEW_STUDENT_APPLICATION_RESULTS, "Depois de ver resultados de uma aplicação (Aluno)"),
        (AFTER_STUDENT_REVIEW_QUESTIONS, "Depois que o aluno revisar uma questão"),
        (IN_VIEW_EXAM_RESULTS, "Enquanto ver resultado de um caderno (Coordenação)"),
    )
    
    trigger = models.SmallIntegerField("Quando criar a notificação", choices=TRIGGERS_CHOICES, blank=True, null=True)
    especial_trigger = models.SmallIntegerField("Ações específicas para quando criar a notificação", choices=ESPECIAL_TRIGGERS_CHOICES, blank=True, null=True)
    MODEL_CHOICES = (
        ('exams.Exam', 'Cadernos'),
        ('applications.Application', 'Aplicação'),
        ('ApplicationMultiple', 'Multiplas Aplicações'),
        ('ExamTemplate', 'Gabarito avulso'),
        ('questions.Question', 'Questions'),
        ('students.Student', 'Alunos'),
        ('inspectors.Inspector', 'Professor'),
        ('Inspector', 'Fiscais'),
    )
    model = models.CharField("Para qual modelo?", max_length=100, choices=MODEL_CHOICES, blank=True, null=True)
    
    show_rating = models.BooleanField('Mostrar as estrelinhas', default=False)
    answer_is_required = models.BooleanField('O Feedback é obrigatório', default=False)
    show_form = models.BooleanField('Mostrar o campo para digitar o feedback', default=False)
    delay = models.SmallIntegerField('Delay para mostrar a modal (segundos)', default=1)
    persist = models.BooleanField('Mostrar modal até o usuário visualizar ou enviar o feedback', default=False)
    
    repeat_days = models.SmallIntegerField("Em quanto tempo essa mensagem se repete? (em dias)", blank=True, null=True, help_text="Deixe 0 (zero) para que a mensagem não seja repetida.")

    objects = NotificationManager()

    class Meta:
        verbose_name = 'Notificação ou NPS'
        verbose_name_plural = "Notificações ou NPS's"
        
    def __str__(self):
        return self.title
    
    @property
    def is_finished(self):
        value = self.end_date < timezone.now()

        if value:
            return 'Sim'
        return 'Não'
    is_finished.fget.short_description = 'Encerrada?'
    
    @property
    def to_show(self):
        return self.show_modal or self.trigger
    
    def get_target_clients(self):
        clients = self.clients.all()

        if clients:
            return list(clients.values_list('name', flat=True))
    get_target_clients.__name__ = 'Clientes alvo'


    def save_on_localstorage(self):
        if (self.trigger and self.model) or (self.repeat_days and self.repeat_days > 0):
            return False
        return True
    
    def create_notificationuser(self, user):
        now = timezone.localtime(timezone.now())
        
        notifications_user = user.notificationuser_set.filter(notification=self).order_by('next_nps_date')
        
        if last_notification := notifications_user.last():
            
            if repeat_days := last_notification.notification.repeat_days:
                
                last_notification_date = last_notification.created_at + timedelta(days=repeat_days)
                
                if last_notification_date.date() <= now.date():

                    notify, created = NotificationUser.objects.get_or_create(
                        user=user,
                        notification=self,
                        next_nps_date=last_notification_date,
                    )
                    
                    notifications_user.filter(notification=self, next_nps_date__lte=now.date()).exclude(id=notify.id).update(viewed=True)
            
        else:
            notify, created = NotificationUser.objects.get_or_create(
                notification=self,
                user=user,
            )
    
    @property
    def get_is_nps(self):
        return self.repeat_days > 0 and self.category == Notification.SEARCH if self.repeat_days else False
    
    @property
    def is_active(self):
        now = timezone.localtime(timezone.now())
        return self.get_is_nps and self.start_date < now < self.end_date
    
    def clean(self):
        
        if self.category == Notification.SEARCH and not self.repeat_days:
            raise ValidationError({ 'repeat_days': 'Para notificações do tipo "Pesquisa" este campo não pode ser vazio' })
        
        if not self.elementary_school and not self.high_school:
            raise ValidationError({ 'elementary_school': 'Você pode escolher pelo menos um segmento (Fundamental ou médio)' })
        
        if not self.trigger is None and not self.model:
            raise ValidationError({ 'model': 'Ao selecionar "Quando chamar a modal" você pode selecionar um modelo' })
            
        if self.model and self.trigger is None:
            raise ValidationError({ 'trigger': 'Ao selecionar "Para qual modelo" você deve especificar em qual momento a modal deve ser chamada' })
        
        if self.urls and (not self.trigger is None or not self.model is None):
            self.trigger = None
            self.model = None
            self.especial_trigger = None
            
        if self.especial_trigger:
            self.trigger = None
            self.model = None
        
        if (self.repeat_days and self.repeat_days > 0 and self.category != Notification.SEARCH) or (self.show_form or self.show_rating):
            self.category == Notification.SEARCH
            
        if self.category == Notification.SEARCH:
            self.show_form = True
            self.show_rating = True
   
    @classmethod
    def create_single_notification_for_user(self, urls, title, description, user):
        """
        Método de classe para criar uma notificação e associar um usuário.
        """

        notification = self.objects.create(
            urls=urls,
            high_school=True,  
            elementary_school=False,  
            title=title,
            description=description,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=1), 
            show_modal=False,
            display_until_end_date=False,
            category=self.IA,           
        )

        notification.users.add(user)
        
        return notification
        
class NotificationUser(BaseModel):
    notification = models.ForeignKey(Notification, verbose_name='Notificação', on_delete=models.CASCADE)
    user = models.ForeignKey('accounts.User', verbose_name='Usuário', on_delete=models.CASCADE)
    rating = models.SmallIntegerField("Qual nota você da para esta experiência?", blank=True, default=0)
    feedback = models.TextField("Como podemos melhorar esta experiência?", blank=True, null=True)
    viewed = models.BooleanField("Foi visualizado", default=False, blank=False)
    feedback_sent = models.BooleanField("Enviou o feedback", default=False, blank=False)
    solved = models.BooleanField("Atendido", default=False, blank=True)
    next_nps_date = models.DateField("Data da pesquisa", blank=True)

    class Meta:
        verbose_name = 'Feedback de notificação'
        verbose_name_plural = 'Feedbacks de notificações'
        unique_together = (
            ('notification', 'user', 'next_nps_date')
        )
    
    @hook("before_create")
    def set_default_next_nps_date(self):
        now = timezone.localtime(timezone.now())
        if not self.next_nps_date:
            self.next_nps_date = now.date()
    
    """
    @hook('before_update', when='viewed', has_changed=True, is_now=True)
    def create_new_nps(self):
        now = timezone.localtime(timezone.now())
        
        if repeat_days := self.notification.repeat_days:
            
            # Calculate new date
            notification_end_date = self.notification.end_date.date()
            next_nps_date = (now + timedelta(days=repeat_days)).date()
            
            # Certifica-se de que a data da última pesquisa não será maior do que a data final da notificação
            if next_nps_date >= notification_end_date:
                next_nps_date = notification_end_date

            NotificationUser.objects.get_or_create(
                notification=self.notification,
                user=self.user,
                next_nps_date=next_nps_date,
            )
    """
    
    @staticmethod
    def filter_is_nps():
        return models.Q(
            notification__repeat_days__isnull=False,
            notification__repeat_days__gt=0,
            notification__category=Notification.SEARCH
        )
    
    @property
    def urls(self):
        return {
            "api_update": reverse("notifications:api-user-feedback-update", kwargs={ "pk": self.pk }) 
        }

    @property
    def get_notification_display(self):
        return self.notification.title
    get_notification_display.fget.short_description = 'Notificação'

    @property
    def notification_client(self):
        from fiscallizeon.clients.models import Client
        client = Client.objects.get(pk=self.user.get_clients_cache()[0])
        return client.name
    notification_client.fget.short_description = 'Cliente'
