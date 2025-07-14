import re
from django.db import models

from fiscallizeon.core.models import BaseModel
from fiscallizeon.help.managers import HelpLinkManager, TutorialManager
from django.conf import settings
from tinymce.models import HTMLField
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import strip_tags
from fiscallizeon.core.utils import ChoiceArrayField

class HelpLink(BaseModel):
    url_path = models.CharField('URL da página', max_length=255, help_text='Utilize "namespace:name"')
    article_url = models.URLField('URL do artigo')
    article_name = models.CharField('Título do artigo', max_length=255)
    article_description = models.CharField('Descrição do link de ajuda', max_length=255)
    is_student = models.BooleanField('Para alunos', default=False)
    is_teacher = models.BooleanField('Para professores', default=False)
    is_inspector = models.BooleanField('Para fiscais', default=False)
    is_coordination = models.BooleanField('Para coordenadores', default=False)

    objects = HelpLinkManager()

    def __str__(self):
        return self.article_name

    class Meta:
        verbose_name = 'Link de ajuda'
        verbose_name_plural = 'Links de ajuda'
    
class Tutorial(BaseModel):
    SEGMENTS_TARGET_TYPES = (
        (settings.COORDINATION, 'Coordenações'),
        (settings.STUDENT, 'Alunos'),
        (settings.INSPECTOR, 'Fiscais'),
        (settings.TEACHER, 'Professores'),
        (settings.PARTNER, 'Parceiro'),
    )
    
    url_path = models.CharField('URL da página', max_length=255, help_text='Utilize "namespace:name"', blank=True, null=True)
    segments = ChoiceArrayField(models.CharField("Segmento", max_length=50, choices=SEGMENTS_TARGET_TYPES), blank=True, null=True)
    clients = models.ManyToManyField("clients.Client", verbose_name='Clientes', blank=True)
    title = models.CharField('Título', max_length=255)
    content = HTMLField('Conteúdo', blank=True, null=True)
    thumbnail = models.ImageField("Imagem de capa do tutorial", upload_to="tutorial/thumbnail/", blank=True, null=True)
    youtube_url = models.URLField("Url do vídeo", max_length=255, blank=True, null=True)
    views = models.IntegerField("Visualizações", default=0, blank=True)
    categories = models.ManyToManyField("TutorialCategory", verbose_name=("Categoria"))
    
    DRAFT, PUBLISHED = range(2)
    STATUS_CHOICES = (
        (DRAFT, 'Rescunho'),
        (PUBLISHED, 'Publicado'),
    )
    status = models.SmallIntegerField("Status do tutorial", default=DRAFT, choices=STATUS_CHOICES)
    
    objects = TutorialManager()

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = 'Tutorial'
        verbose_name_plural = 'Tutoriais'
        
        
    def get_content_str(self):
        return strip_tags(self.content)
        
    def clean(self):
        
        if not self.youtube_url and not self.content:
            raise ValidationError({ 'youtube_url': 'É obrigatório informar o link do vídeo ou o conteúdo' })
        
        if not self.thumbnail and not self.youtube_url:
            raise ValidationError({ 'thumbnail': 'Se você não informar o a URL do vídeo do youtube você precisa informar a imagem de capa' })
        
        return self
    
    def get_emmbbeded_video(self, is_modal=False):
        
        if youtube_url := self.youtube_url:
        
            if "watch?v=" in youtube_url:
                youtube_url = youtube_url.replace("watch?v=", "embed/")
            elif "youtu.be" in youtube_url:
                youtube_url = youtube_url.replace("youtu.be/", "youtube.com/embed/")
                
            src = re.split(r'\b[&]+.*$', youtube_url)
            src = re.split(r'\b[=]+.*$', src[0])[0]
            
            if is_modal:
                
                return f"""<iframe style="top: 0; left: 0; bottom: 0; right: 0; width: 100%; min-height: 460px; border:none; overflow:hidden;" src="{src}" title="Resposta comentada em vídeo" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>"""
            
            return f"""<iframe style="position: absolute; top: 0; left: 0; bottom: 0; right: 0; width: 100%; height: 100%; border:none; overflow:hidden;" src="{src}" title="Resposta comentada em vídeo" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>"""
        
        return None
    
    def get_emmbbeded_video_modal(self):
        return self.get_emmbbeded_video(is_modal=True)
    
    def get_urls(self):
        return {
            "detail": reverse('help:tutorial-detail', kwargs={ "pk": self.pk }),
            "api_detail": reverse('api:clients:tutoriais-detail', kwargs={ "pk": self.pk })
        }
        
class TutorialCategory(BaseModel):
    name = models.CharField("Nome da categoria", max_length=50)
    icon = models.CharField("Icone da categoria", max_length=200, blank=True, null=True, help_text="""Geralmente utilizado: https://fontawesome.com/icons, adicionar a tag <i></i> completa como no exemplo: <i class="fas fa-times"></i>""")
    description = models.TextField("Descriçao", blank=True, null=True)
    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        
    def __str__(self):
        return self.name
    
    def get_description_str(self):
        return strip_tags(self.description)
    
    def get_urls(self):
        return {
            "detail": reverse('help:tutorial-category-detail', kwargs={ "pk": self.pk }),
        }
        
    def get_segments(self):
        
        
        segments_list = self.tutorial_set.filter(segments__isnull=False).values_list('segments', flat=True).distinct()
        
        segments = []
        if segments_list:
            for segment in segments_list[0]:
                
                if segment == settings.COORDINATION:
                    segments.append("Coordenações")
                elif segment == settings.STUDENT:
                    segments.append("Alunos")
                elif segment == settings.TEACHER:
                    segments.append("Professores")
                elif segment == settings.INSPECTOR:
                    segments.append("Fiscais")
                elif segment == settings.PARTNER:
                    segments.append("Parceiros")
        
        else:
            segments.append("Todos")
        
        return segments
    
    def get_tutoriais(self):
        return self.tutorial_set.filter(
            status__in=[Tutorial.PUBLISHED]
        )


class TutorialFeedback(BaseModel):
    POSITIVE = 'P'
    NEGATIVE = 'N'

    VALUES = (
        (POSITIVE, 'Positivo'),
        (NEGATIVE, 'Negativo'),
    )

    tutorial = models.ForeignKey(
        Tutorial, on_delete=models.CASCADE, verbose_name='tutorial', related_name='feedbacks'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='usuário',
        related_name='tutorial_feedbacks',
    )
    date = models.DateField('data', auto_now_add=True)
    value = models.CharField('valor', max_length=1, choices=VALUES)

    class Meta:
        verbose_name = 'feedback do tutorial'
        verbose_name_plural = 'feedbacks dos tutoriais'
        ordering = ('-created_at',)
        unique_together = ('tutorial', 'user', 'date')

    def __str__(self):
        return f'{self.tutorial} - {self.user} - {self.date} - {self.value}'
