# Generated by Django 4.0.6 on 2023-11-06 18:04

from django.db import migrations, models
import django_lifecycle.mixins
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='OpenAIQuery',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Registrado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('user_prompt', models.TextField(verbose_name='Prompt do usuário')),
                ('gpt_model', models.CharField(max_length=128, verbose_name='Modelo GPT')),
                ('input_tokens', models.PositiveIntegerField(verbose_name='Número de tokens de entrada')),
                ('output_tokens', models.PositiveIntegerField(verbose_name='Número de tokens de saída')),
                ('finish_reason', models.PositiveSmallIntegerField(choices=[('stop', 'Sucesso'), ('length', 'Incompleto'), ('function_call', 'Chamada de função'), ('content_filter', 'Filtro de conteúdo'), ('null', 'Desconhecido')], verbose_name='Status de finalização')),
            ],
            options={
                'abstract': False,
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
    ]
