# Generated by Django 4.0.6 on 2023-04-23 23:26

from django.db import migrations, models
import django.db.models.deletion
import django_lifecycle.mixins
import tinymce.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0088_rename_competencies_clientteacherobligationconfiguration_competences'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientCustomPage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Registrado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('location', models.SmallIntegerField(blank=True, choices=[(0, 'Prova do aluno'), (1, 'Folha de assinatura'), (2, 'Folha de resposta')], default=0, verbose_name='Local')),
                ('type', models.SmallIntegerField(blank=True, choices=[(0, 'HTML'), (1, 'PDF')], default=0, verbose_name='Tipo de arquivo')),
                ('file', models.FileField(blank=True, max_length=10000, null=True, upload_to='custom_pages', verbose_name='Arquivo HTML')),
                ('content', tinymce.models.HTMLField(blank=True, null=True, verbose_name='Conteúdo HTML')),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='clients.client', verbose_name='Cliente')),
            ],
            options={
                'abstract': False,
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
    ]
