from django.db import models
from django.apps import apps
from django.db.models import Q
from django.conf import settings

class HelpLinksQuerySet(models.QuerySet):
    def get_for_path(self, url_path, user_type):
        HelpLink = apps.get_model('help', 'HelpLink')

        return HelpLink.objects.filter(
            Q(url_path=url_path),
            Q(is_student=user_type == settings.STUDENT) |
            Q(is_teacher=user_type == settings.TEACHER) |
            Q(is_inspector=user_type == settings.INSPECTOR) |
            Q(is_coordination=user_type == settings.COORDINATION)
        )
        
class TutorialQuerySet(models.QuerySet):
    
    def get_for_path(self, url_path, user_type):
        Tutorial = apps.get_model('help', 'Tutorial')

        return Tutorial.objects.filter(
            Q(url_path=url_path, status=Tutorial.PUBLISHED),
            Q(
                Q(segments__isnull=True) |
                Q(segments__len__lte=0) |
                Q(segments__contains=[user_type])
            )
        )

HelpLinkManager = models.Manager.from_queryset(HelpLinksQuerySet)
TutorialManager = models.Manager.from_queryset(TutorialQuerySet)
