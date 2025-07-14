import uuid

from django.db import models
from django_lifecycle import LifecycleModelMixin
from tinymce.models import HTMLField


class BaseModel(LifecycleModelMixin, models.Model):
	id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
	created_at  = models.DateTimeField(verbose_name='Registrado em', auto_now_add=True, db_index=True)
	updated_at = models.DateTimeField(verbose_name='Atualizado em', auto_now=True)

	class Meta:
		abstract = True

class Config(BaseModel):
	privacy = HTMLField('Política de Privacidade')
	terms_of_use = HTMLField('Termos de uso')
	terms_of_use_inspectors = HTMLField('Termos de uso para fiscais')