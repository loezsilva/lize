from fiscallizeon.core.threadings.sendemail import EmailThread
from django.db import models
from django.template.loader import get_template
from fiscallizeon.core.models import BaseModel

from fiscallizeon.accounts.models import User
from fiscallizeon.classes.models import Grade
from fiscallizeon.subjects.models import Subject
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from django_lifecycle import hook

from django.conf import settings

def material_file_directory_path(instance, filename):
    return 'diagramation/file/{0}/{1}'.format(str(instance.pk), filename)

class DiagramationRequest(BaseModel):
    exam_file = models.FileField(verbose_name='Arquivo das questões objetivas', upload_to=material_file_directory_path, storage=PrivateMediaStorage(), null=False, blank=False, help_text="Envie o arquivos com as questẽos que serão diagramadas. Arquivo: .pdf, .doc ou .docx")

    exam_file_discursive = models.FileField(verbose_name='Arquivo das questões dicursivas', upload_to=material_file_directory_path, storage=PrivateMediaStorage(), null=True, blank=True, help_text="Envie o arquivos com as questẽos que serão diagramadas. Arquivo: .pdf, .doc ou .docx")

    template_file = models.FileField(verbose_name='Arquivo de gabarito', upload_to=material_file_directory_path, storage=PrivateMediaStorage(), help_text="Você pode enviar o gabarito juntamente com a prova no campo anterior, se preferir.", null=True, blank=True)
    application_date = models.DateField("Data que a prova será aplicada aos alunos")
    subjects = models.ManyToManyField(Subject, verbose_name='Disciplinas do caderno de provas')
    grade = models.ForeignKey(Grade, verbose_name='Série que será aplicada este caderno', on_delete=models.PROTECT, null=True, blank=True)
    question_weight = models.TextField('Descreva como será a distribuição das notas para essa prova', null=True, blank=True)
    orientations = models.TextField('Descreva detalhes sobre a elaboração da prova e aplicação', null=True, blank=True)
    CREATED, ELABORATING, FINISHED = range(3)
    STATUS_CHOICES = (
        (CREATED, "Solicitado"),
        (ELABORATING, "Elaborando"),
        (FINISHED, "Finalizado")
    )
    status = models.PositiveSmallIntegerField('Status da solicitação', default=CREATED, choices=STATUS_CHOICES)
    created_by = models.ForeignKey(User, verbose_name='Criado por', on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        verbose_name = "Solicitação de diagramação"
        verbose_name_plural = "Solicitações de Diagramação"
        ordering = ('-application_date', 'created_at', )

    def __str__(self):
        return f'{self.created_by}'

    @hook('after_create')
    def send_email_to_staff(self):
        if not settings.DEBUG:
            template = get_template('diagramations/mail_template/default.html')
            html = template.render({"object":self, "email":True})
            subject = 'Solicitação de diagramação'
            to = ['provas@fiscallize.com.br', 'pedro@fiscallize.com.br', 'thaina@fiscallize.com.br']
            EmailThread(subject, html, to).start()
