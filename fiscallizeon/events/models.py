from django.db import models

from fiscallizeon.core.models import BaseModel
from fiscallizeon.accounts.models import User
from fiscallizeon.applications.models import ApplicationStudent, Application
from fiscallizeon.questions.models import Question


class Event(BaseModel):
    OTHER, BATHROOM, LEAVE_TAB  = range(3)
    EVENT_TYPE_CHOICES = (
        (OTHER, "Outro"),
        (BATHROOM, "Banheiro"),
        (LEAVE_TAB, "Saída da aba de aplicação"),
    )
    event_type = models.PositiveIntegerField("Tipo de evento", choices=EVENT_TYPE_CHOICES, default=BATHROOM)
    student_application = models.ForeignKey(ApplicationStudent, on_delete=models.CASCADE, related_name="events")
    start = models.DateTimeField("Hora de início", auto_now=False, auto_now_add=False, blank=True, null=True)
    end = models.DateTimeField("Horário final", auto_now=False, auto_now_add=False, blank=True, null=True)

    APPROVED, REJECT, PENDING = range(3)
    RESPONSE_CHOICES = (
        (APPROVED, "Aprovado"),
        (REJECT, "Rejeitado"),
        (PENDING, "Pendente")
    )
    inspector = models.ForeignKey(User, verbose_name="Fiscal", on_delete=models.CASCADE, blank=True, null=True)
    response = models.PositiveIntegerField("Resposta do fiscal", choices=RESPONSE_CHOICES, default=PENDING)
    response_datetime = models.DateTimeField("Hora da resposta", blank=True, null=True)

    def __str__(self):
        return self.get_event_type_display()

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        ordering = ('-created_at',)
        


class TextMessage(BaseModel):
    sender = models.ForeignKey(User, verbose_name='Usuário', on_delete=models.CASCADE)
    application_student = models.ForeignKey(ApplicationStudent, verbose_name='Usuário', on_delete=models.CASCADE, related_name="messages")
    content = models.TextField('Conteúdo da mensagem')

    class Meta:
        verbose_name = 'Mensagem de aluno'
        verbose_name_plural = 'Mensagens de alunos'
        ordering = ("created_at", )

    def get_escaped_content(self):
        return self.content.replace("\\", "\\\\").replace('&quot;', '\\"').replace('"', '\\"')


class ApplicationMessage(BaseModel):
    application = models.ForeignKey(Application, verbose_name="Aplicação", on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, verbose_name="Fiscal", on_delete=models.CASCADE)
    content = models.TextField("Conteúdo da mensagem", max_length=255)

    class Meta:
        verbose_name = 'Mensagem de aplicação'
        verbose_name_plural = 'Mensagens de aplicação'
        ordering = ("created_at", )


class QuestionErrorReport(BaseModel):
    application = models.ForeignKey(Application, verbose_name="Aplicação", on_delete=models.CASCADE, related_name="error_reports")
    question = models.ForeignKey(Question, verbose_name="Questão", on_delete=models.CASCADE, related_name="error_reports")
    sender = models.ForeignKey(User, verbose_name="Aluno", on_delete=models.CASCADE, related_name="error_reports")
    content = models.TextField("Conteúdo da mensagem", max_length=255)
    RESOLVED, PENDING = range(2)
    STATUS_CHOICES = (
        (RESOLVED, "Resolvido"),
        (PENDING, "Pendente")
    )
    status = models.SmallIntegerField("Situação", choices=STATUS_CHOICES, default=PENDING)

    class Meta:
        verbose_name = 'Erro em questão'
        verbose_name_plural = 'Erros em questões'
        ordering = ("-created_at", )