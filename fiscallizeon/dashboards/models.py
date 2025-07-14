from django.db import models
from django.conf import settings
from ..core.models import BaseModel
from django.core.exceptions import ValidationError
from django.urls import reverse
from django_lifecycle import hook

"""
class DashboardChart(BaseModel):

    SCHOOL, SUBJECT, EXAM, CLASSE = 'school', 'subject', 'exam', 'classe'
    GENERAL = 'general'
    
    WHO_CHOICES = (
        (SCHOOL, 'Instituição'),
        (SUBJECT, 'Disciplina'),
        (settings.COORDINATION, 'Coordenação'),
        (settings.STUDENT, 'Aluno'),
        (settings.TEACHER, 'Professores'),
    )

    WHAT_CHOICES = (
        (GENERAL, 'Geral'),
        (EXAM, 'Cadernos'),
        (SUBJECT, 'Disciplinas'),
        (CLASSE, 'Turmas'),
        (settings.COORDINATION, 'Coordenações'),
        (settings.STUDENT, 'Alunos'),
    )
    NUMBER, LINE, BAR, HORIZONTAL_BAR, PIE, DONUT = 'radialBar', 'line', 'bar', 'horizontal_bar', 'pie', 'donut'
    
    TYPE_CHOICES = (
        (NUMBER, 'Grafico de valor único'),
        (LINE, 'Grafico de linha'),
        (BAR, 'Gráfico de barras'),
        (HORIZONTAL_BAR, 'Gráfico de barras horizontais'),
        (PIE, 'Gráfico de pizza'),
        (DONUT, 'Gráfico de donut'),
    )
    dashboard = models.ForeignKey("Dashboard", verbose_name=("Dashboard"), related_name="charts", on_delete=models.CASCADE)
    order = models.SmallIntegerField("Ordem", default=1, blank=True)
    who = models.CharField("Quem será analisado", max_length=50, choices=WHO_CHOICES, default=SCHOOL)
    who_id = models.UUIDField("ID analizado", blank=True, null=True)
    what = models.CharField("O que será analisado", max_length=50, choices=WHAT_CHOICES, default=EXAM, null=True, blank=True)
    what_id = models.UUIDField(null=True, blank=True)
    operation = models.CharField("Operação", max_length=50)
    columns = models.SmallIntegerField("Colunas")
    type = models.CharField("Tipo de gráfico", max_length=50, choices=TYPE_CHOICES)

    class Meta:
        ordering = ('order', )

    @property
    def urls(self):
        return {
            "api_detail": reverse('api2:dashboards-chart-detail', kwargs={"pk": self.id})
        }

    @staticmethod
    def get_availables_what(who):
        return [value[1] for value in Dashboard.WHAT_CHOICES]
    
    def clean(self):
        if not self.dashboard.who_id:
            raise ValidationError({"who_id": "Este campo é obrigatório"})

    @hook('before_create')
    def populate_data(self):
        if who := self.dashboard.who:
            self.who = who
        if who_id := self.dashboard.who_id:
            self.who_id = who_id

class Dashboard(BaseModel):
    name = models.CharField("Nome do dashboard", max_length=70)
    created_by = models.ForeignKey("accounts.User", verbose_name=("Quem criou"), related_name="dashboards", on_delete=models.CASCADE, blank=True, null=True)
    client = models.ForeignKey("clients.Client", verbose_name=("Client"), related_name="dashboards", on_delete=models.CASCADE, blank=True, null=True)
    is_public = models.BooleanField("Tornar publico para minha instituição", default=False, blank=True)
    who = models.CharField("Quem será analisado", max_length=50, choices=DashboardChart.WHO_CHOICES, default=DashboardChart.SCHOOL, blank=True, null=True)
    who_id = models.UUIDField("ID analizado", blank=True, null=True)
    
    @property
    def urls(self):
        return {
            "api_detail": reverse('api2:dashboards-get-charts', kwargs={"pk": self.id})
        }
    
    def __str__(self):
        return self.name
    
    def clean(self):
        if self.who == DashboardChart.SCHOOL:
            if not self.created_by and not self.client:
                raise ValidationError({ "who_id": f"Você deve informar o client" })
            print("aqui 1")
        else:
            print("aqui 2")
            if self.who and not self.who_id:
                raise ValidationError({ "who_id": f"Você deve informar o ID do {self.who}" })
    
    @hook('after_update', when_any=["who", "who_id"], has_changed=True)
    def update_who(self):
        self.charts.update(who=self.who, who_id=self.who_id)

    @hook('before_create')
    def populate_who_id(self):
        if self.created_by or self.client and self.who == DashboardChart.SCHOOL:
            if self.client:
                self.who_id = self.client.id
            elif self.created_by:
                self.who_id = self.created_by.client.id

"""