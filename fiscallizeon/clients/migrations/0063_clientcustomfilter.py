# Generated by Django 4.0.6 on 2022-12-08 16:02

from django.db import migrations, models
import django.db.models.deletion
import django_lifecycle.mixins
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0062_remove_clientquestionsconfiguration_can_delete_question_aproveds'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientCustomFilter',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Registrado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('name', models.CharField(max_length=200)),
                ('active', models.BooleanField(default=True, verbose_name='Filtro ativo')),
                ('url', models.CharField(max_length=50)),
                ('params', models.TextField()),
                ('user', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='custom_filters', to='clients.client', verbose_name='Cliente')),
            ],
            options={
                'verbose_name': 'Filtro personalizados',
                'verbose_name_plural': 'Filtros personalizados',
                'ordering': ['created_at'],
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
    ]
