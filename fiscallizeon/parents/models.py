import datetime
from django.db import models
from django.utils import  timezone
from fiscallizeon.core.models import BaseModel
from django_lifecycle import hook
from fiscallizeon.accounts.models import User
from django.utils.crypto import get_random_string
from django.conf import settings
from django.template.loader import get_template
from fiscallizeon.core.threadings.sendemail import EmailThread

# Create your models here.
class Parent(BaseModel):
    user = models.OneToOneField(User, verbose_name="Usuário", on_delete=models.CASCADE, blank=True, null=True)
    email = models.EmailField("Email do responsável", max_length=254)
    hash = models.CharField("Hash para criação do usuário", max_length=200, blank=True)
    hash_validate = models.DateTimeField("Validade do hash", blank=True)
    students = models.ManyToManyField("students.Student", verbose_name=("Filhos"), blank=True)
    
    def __str__(self):
        if self.user:
            return self.user.name
        return self.email
    
    class Meta:
        verbose_name = 'Responsável'
        verbose_name_plural = 'Responsáveis'
    
    @property
    def urls(self):
        from django.urls import reverse
        return {
			"user_creation": reverse('parents:parent_signup', kwargs={ 'hash': self.hash })
		}
    
    @hook('before_save')
    def set_childrens(self):
        from fiscallizeon.students.models import Student
        self.students.set(Student.objects.filter(models.Q(responsible_email=self.email) | models.Q(responsible_email_two=self.email)).values_list('pk', flat=True))
    
    @hook('before_create')
    def create_hash(self):
        self.hash = get_random_string(80)
        self.hash_validate = timezone.now() + datetime.timedelta(days=15)
        
    @hook('after_create')
    def send_email_to_parent(self):
        self.send_mail_to_first_access()
        
    @property
    def hash_is_valid(self):
        if not self.user and self.hash_validate >= timezone.now():
            return True
        return False
    
    def send_mail_to_first_access(self):
        template = get_template('mail_template/send_notify_parent_user_creation.html')
        html = template.render({ 
            "parent": self,
            "BASE_URL": settings.BASE_URL,
        })
        subject = f'Convite para acessar a plataforma de resultados escolares'
        to = [self.email]
        EmailThread(subject, html, to).start()
        
        self.hash_validate = timezone.now() + datetime.timedelta(days=15)
        self.save(skip_hooks=True)
            
    def notify_parent_when_result_is_open(self):
        if self.user:
            
            template = get_template('mail_template/send_notify_parent_when_result_open_new.html')
            html = template.render({
                "parent": self,
                "BASE_URL": settings.BASE_URL,
            })
            subject = f'Consulte agora os resultados das provas do(s) seu(s) filhos(as)'
            
            to = [self.email]
            
            EmailThread(subject, html, to).start()