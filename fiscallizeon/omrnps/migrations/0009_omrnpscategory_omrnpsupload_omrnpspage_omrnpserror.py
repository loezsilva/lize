# Generated by Django 4.0.6 on 2023-11-17 19:02

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_lifecycle.mixins
import fiscallizeon.core.storage_backends
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('omrnps', '0008_npsapplication_name_npsapplication_show_teahcer_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='OMRNPSCategory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Registrado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('name', models.CharField(max_length=255, verbose_name='Nome')),
                ('template', models.JSONField(verbose_name='JSON de mapeamento')),
                ('marker_image', models.ImageField(blank=True, null=True, storage=fiscallizeon.core.storage_backends.PublicMediaStorage(), upload_to='omr_static/', verbose_name='Imagem de marcador')),
                ('sequential', models.PositiveSmallIntegerField(choices=[(0, 'Outro'), (1, 'Professores (5 eixos)')], default=0, verbose_name='Sequencial interno')),
                ('enabled', models.BooleanField(default=True, verbose_name='Habilitado')),
            ],
            options={
                'verbose_name': 'Categoria de NPS',
                'verbose_name_plural': 'Categorias de NPS',
                'ordering': ('sequential',),
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='OMRNPSUpload',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Registrado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('status', models.PositiveSmallIntegerField(choices=[(0, 'Em fila'), (1, 'Processando'), (2, 'Finalizado'), (3, 'Erro'), (4, 'Desconhecido'), (5, 'Reprocessando')], default=0, verbose_name='Status')),
                ('filename', models.TextField(blank=True, null=True, verbose_name='Arquivo enviado')),
                ('processing_log', models.TextField(blank=True, default='', null=True, verbose_name='Resultado da operação')),
                ('error_pages_count', models.PositiveSmallIntegerField(default=0, verbose_name='Folhas com erro')),
                ('total_pages', models.PositiveSmallIntegerField(default=0, verbose_name='Páginas lidas com sucesso')),
                ('raw_pdf', models.FileField(blank=True, null=True, storage=fiscallizeon.core.storage_backends.PrivateMediaStorage(), upload_to='omrnps/raw_uploads/', verbose_name='Arquivo original')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, verbose_name='Usuário')),
            ],
            options={
                'verbose_name': 'Upload de NPS',
                'verbose_name_plural': 'Upload de NPS',
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='OMRNPSPage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Registrado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('successful_answers_count', models.PositiveSmallIntegerField(default=0, verbose_name='Número de respostas contabilizadas')),
                ('scan_image', models.ImageField(blank=True, null=True, storage=fiscallizeon.core.storage_backends.PrivateMediaStorage(), upload_to='omrnps/scans/', verbose_name='Imagem do escaneamento')),
                ('upload', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='omrnps.omrnpsupload', verbose_name='Upload')),
            ],
            options={
                'verbose_name': 'Página escaneada de NPS',
                'verbose_name_plural': 'Páginas escaneadas de NPS',
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='OMRNPSError',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Registrado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('error_image', models.ImageField(storage=fiscallizeon.core.storage_backends.PrivateMediaStorage(), upload_to='omr/scans/', verbose_name='Imagem do escaneamento')),
                ('category', models.PositiveSmallIntegerField(choices=[(0, 'Outro'), (1, 'QRCode não identificado'), (2, 'Marcações não identificadas')], default=0, verbose_name='Categoria')),
                ('page_number', models.PositiveSmallIntegerField(default=0, verbose_name='Página no documento')),
                ('is_solved', models.BooleanField(default=False, verbose_name='Reolvido')),
                ('omr_category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='omrnps.omrnpscategory', verbose_name='Categoria do upload')),
                ('upload', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='omrnps.omrnpsupload', verbose_name='Upload')),
            ],
            options={
                'verbose_name': 'Erro de leitura de NPS',
                'verbose_name_plural': 'Erros de leitura de NPS',
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
    ]
