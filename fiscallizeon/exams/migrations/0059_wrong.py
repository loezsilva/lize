# Generated by Django 3.2.4 on 2022-02-01 20:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_lifecycle.mixins
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0005_alter_student_options'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('exams', '0058_auto_20220117_2022'),
    ]

    operations = [
        migrations.CreateModel(
            name='Wrong',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Registrado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('student_description', models.TextField(verbose_name='Descrição do aluno')),
                ('status', models.PositiveSmallIntegerField(choices=[(0, 'Aguardando correção'), (1, 'Aceito'), (2, 'Recusado'), (3, 'Reaberto')], default=0, verbose_name='Situação')),
                ('response', models.TextField(blank=True, null=True, verbose_name='Resposta do aluno')),
                ('response_date', models.DateTimeField(blank=True, null=True, verbose_name='Data da resposta')),
                ('exam_question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='exams.examquestion', verbose_name='Questão no Exame')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='students.student', verbose_name='Aluno')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Usuário')),
            ],
            options={
                'ordering': ('-created_at',),
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
    ]
