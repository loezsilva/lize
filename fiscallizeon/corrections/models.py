from django.db import models

from fiscallizeon.core.models import BaseModel
from fiscallizeon.clients.models import Client

class TextCorrection(BaseModel):
    name = models.CharField(max_length=255)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name = 'Correção de texto'
        verbose_name_plural = 'Correções de texto'
        ordering = ('created_at', )

    def __str__(self):
        return self.name

class CorrectionCriterion(BaseModel):
    text_correction = models.ForeignKey(TextCorrection, verbose_name='Correção de texto', on_delete=models.CASCADE)
    name = models.CharField('Nome', max_length=255)
    order = models.PositiveSmallIntegerField('Ordem',default=0)
    maximum_score = models.FloatField('Pontuação máxima', default=0)
    color = models.CharField("Cor", default="#FAC515", blank=True, max_length=10)
    short_name = models.CharField('Nome abreviado', max_length=255, blank=True, null=True)
    description = models.TextField("Descrição", blank=True, null=True)
    step = models.FloatField(default=40)

    class Meta:
        verbose_name = 'Critério de correção'
        verbose_name_plural = 'Critérios de correção'
        ordering = ('created_at', )

    def __str__(self):
        return self.name

class CorrectionDeviation(BaseModel):
    client = models.ForeignKey('clients.Client', related_name='deviations', on_delete=models.CASCADE, blank=True, null=True)
    criterion = models.ForeignKey(CorrectionCriterion, verbose_name='Critério de correção', on_delete=models.CASCADE)
    short_name = models.CharField('Nome', max_length=255)
    description = models.TextField("Descrição", blank=True, null=True)
    score = models.FloatField('Pontuação máxima', default=0)

    class Meta:
        verbose_name = 'Desvio de correção'
        verbose_name_plural = 'Desvios de correção'
        ordering = ('created_at', )

    def __str__(self):
        return self.short_name
    
    @property
    def color(self):
        return self.criterion.color



class CorrectionTextualAnswer(BaseModel):
    textual_answer = models.ForeignKey("answers.TextualAnswer", on_delete=models.CASCADE, related_name="textual_answers")
    correction_criterion = models.ForeignKey(CorrectionCriterion, on_delete=models.CASCADE)
    point = models.FloatField(default=0)

    class Meta:
        verbose_name = 'Resposta de correção Answer'
        verbose_name_plural = 'Respostas de correção Answer'
        ordering = ('created_at', )

class CorrectionFileAnswer(BaseModel):
    file_answer = models.ForeignKey("answers.FileAnswer", on_delete=models.CASCADE, related_name="file_answers")
    correction_criterion = models.ForeignKey(CorrectionCriterion, on_delete=models.CASCADE)
    point = models.FloatField(default=0)

    class Meta:
        verbose_name = 'Resposta de correção FileAnswer'
        verbose_name_plural = 'Respostas de correção FileAnswer'
        ordering = ('created_at', )